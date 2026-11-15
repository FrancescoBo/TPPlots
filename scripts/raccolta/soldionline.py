"""Soldionline: articoli giornalieri 'Le raccomandazioni del <data>' e pagine storiche per titolo (ISIN)."""
import re
import pandas as pd
from . import comune as c

BASE = 'https://www.soldionline.it'
MESI_IT = ['', 'gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto',
           'settembre', 'ottobre', 'novembre', 'dicembre']
ISIN_RE = re.compile(r'\b([A-Z]{2}[A-Z0-9]{9}\d)\b')
FILE_ISIN = c.ROOT / 'config/isin_soldionline.csv'


def _leggi_isin():
    if FILE_ISIN.exists():
        d = pd.read_csv(FILE_ISIN, dtype=str).fillna('')
        return dict(zip(d['isin'], d['ticker']))
    return {}


def _salva_isin(m):
    pd.DataFrame(sorted(m.items()), columns=['isin', 'ticker']).to_csv(FILE_ISIN, index=False)


def _url_giorno(d):
    s = f'le-raccomandazioni-del-{d.day}-{MESI_IT[d.month]}-{d.year}'
    return [f'{BASE}/notizie/azioni-italia/raccomandazioni/{s}', f'{BASE}/notizie/azioni-italia/{s}']


def _data_articolo(url, html):
    m = re.search(r'raccomandazioni-del-(\d{1,2})-([a-z]+)-(\d{4})', url)
    if m and m[2] in c.MESI:
        return pd.Timestamp(int(m[3]), c.MESI[m[2]], int(m[1]))
    t = c.testo_pagina(html)
    m = re.search(r'(\d{1,2})\s+([A-Za-zà-ù]+)\s+(20\d\d)', t)
    if m and m[2].lower() in c.MESI:
        return pd.Timestamp(int(m[3]), c.MESI[m[2].lower()], int(m[1]))
    return None


def _tabella_giornaliera(html, d, ana, isin_map, fonte):
    out = []
    for r in c.righe_tabelle(html):
        if len(r) < 4:
            continue
        soc, banca, giud, tp = r[0][0], r[1][0], r[2][0], r[3][0]
        if not soc or soc.upper() in ('SOCIETÀ', 'SOCIETA', 'TITOLO'):
            continue
        tk = ana.ticker(soc, fonte)
        for h in r[0][1]:
            m = ISIN_RE.search(h)
            if m and tk:
                isin_map[m[1]] = tk
            elif m and m[1] in isin_map and not tk:
                tk = isin_map[m[1]]
        if not tk:
            continue
        out.append(c.record(tk, d, ana.emittente(banca), ana.rating(giud), c.numero(tp), fonte))
    return out


def giornaliero(ana, oggi, giorni=14):
    """Raccoglie gli articoli degli ultimi `giorni` giorni (indovinando gli URL + pagina indice)."""
    fonte = 'soldionline'
    isin_map = _leggi_isin()
    visti, out = set(), []
    urls = []
    for i in range(giorni):
        urls += _url_giorno(oggi - pd.Timedelta(days=i))
    for idx in (f'{BASE}/notizie/azioni-italia/raccomandazioni', f'{BASE}/raccomandazioni'):
        h = c.scarica(idx)
        if h:
            for l in c.link_pagina(h, 'le-raccomandazioni-del'):
                urls.append(l if l.startswith('http') else BASE + l)
    for u in urls:
        if u in visti:
            continue
        visti.add(u)
        html = c.scarica(u, tentativi=1)
        if not html:
            continue
        d = _data_articolo(u, html)
        if d is None or d > oggi + pd.Timedelta(days=1):
            continue
        out += _tabella_giornaliera(html, d, ana, isin_map, fonte)
    _salva_isin(isin_map)
    return out


def storico(ana, oggi, giorni=400, titoli=None):
    """Pagine per titolo (ISIN appresi dagli articoli giornalieri). Percorre le pagine fino a `giorni` fa."""
    fonte = 'soldionline'
    isin_map = _leggi_isin()
    out = []
    limite = oggi - pd.Timedelta(days=giorni)
    for isin, tk in isin_map.items():
        if titoli and tk not in titoli:
            continue
        coda, visti = [f'{BASE}/raccomandazioni/{isin}.html'], set()
        while coda and len(visti) < 12:
            u = coda.pop(0)
            if u in visti:
                continue
            visti.add(u)
            html = c.scarica(u, tentativi=2)
            if not html:
                continue
            piu_vecchia = None
            for r in c.righe_tabelle(html):
                if len(r) < 4:
                    continue
                d = c.data(r[0][0])
                if d is None:
                    continue
                piu_vecchia = d if piu_vecchia is None or d < piu_vecchia else piu_vecchia
                out.append(c.record(tk, d, ana.emittente(r[1][0]), ana.rating(r[2][0]), c.numero(r[3][0]), fonte))
            if piu_vecchia is not None and piu_vecchia > limite:
                for l in c.link_pagina(html, f'{isin}'):
                    if re.search(r'pag', l):
                        coda.append(l if l.startswith('http') else BASE + l)
    return out
