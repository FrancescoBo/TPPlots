"""UBS Investment Bank - 'Research Disclosures': storico data / prezzo / target / rating per emittente."""
import re
import string
import pandas as pd
from . import comune as c

BASE = 'https://research.ibb.ubs.com/openaccess/compliance/'
CACHE = c.ROOT / 'config/ubs_pagine.csv'


def _mappa_pagine(ana):
    """Individua le pagine UBS dei nostri titoli scorrendo l'indice alfabetico (cache 30 giorni)."""
    if CACHE.exists() and (pd.Timestamp.now() - pd.Timestamp(CACHE.stat().st_mtime, unit='s')).days < 30:
        d = pd.read_csv(CACHE, dtype=str)
        return dict(zip(d.ticker, d.pagina))
    mappa = {}
    for lettera in string.ascii_uppercase:
        html = c.scarica(f'{BASE}browse{lettera}_new.html', tentativi=1)
        if not html:
            continue
        for href, testo in re.findall(r'<a[^>]+href=["\']([^"\']*\d+_\d+_new\.html)["\'][^>]*>(.*?)</a>', html, flags=re.S):
            nome = c.pulisci(re.sub(r'<[^>]+>', ' ', testo))
            tk = ana.ticker(nome, 'ubs-indice')
            if tk:
                mappa[tk] = href if href.startswith('http') else BASE + href.split('/')[-1]
    if mappa:
        pd.DataFrame(sorted(mappa.items()), columns=['ticker', 'pagina']).to_csv(CACHE, index=False)
    return mappa


def raccogli(ana, oggi, giorni=45):
    fonte = 'ubs'
    out, limite = [], oggi - pd.Timedelta(days=giorni)
    for tk, url in _mappa_pagine(ana).items():
        html = c.scarica(url, tentativi=2)
        if not html or 'Price Target (€)' not in html:   # solo pagine con target in euro
            continue
        for r in c.righe_tabelle(html):
            if len(r) < 4:
                continue
            d = c.data(r[0][0])
            if d is None or d < limite:
                continue
            out.append(c.record(tk, d, 'Ubs', ana.rating(r[3][0]), c.numero(r[2][0]), fonte))
    return out
