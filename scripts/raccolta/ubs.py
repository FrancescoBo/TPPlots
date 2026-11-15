"""UBS Investment Bank - 'Research Disclosures': storico data / prezzo / target / rating per emittente."""
import html as htmllib
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
    mappa, pagine_ok, link = {}, 0, 0
    for lettera in string.ascii_uppercase + '0':
        html = c.scarica(f'{BASE}browse{lettera}_new.html', tentativi=1)
        if not html:
            continue
        pagine_ok += 1
        if lettera in 'E0':   # diagnostica: cosa riceviamo davvero dal server
            n_a = len(re.findall(r'<a\b', html))
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)[:4]
            visibile = c.pulisci(re.sub(r'(?s)<[^>]+>', ' ', re.sub(r'(?is)<(script|style).*?</\1>', ' ', html)))[:200]
            print(f'    ubs diag [{lettera}]: {len(html)} caratteri, {n_a} tag <a>, {html.count("_new.html")} occorrenze di _new.html')
            print(f'    ubs diag href: {hrefs}')
            print(f'    ubs diag testo: {visibile}')
        for href, testo in re.findall(r'<a\b[^>]*?href=["\']?([^"\'\s>]*\d+_\d+_new\.html)["\']?[^>]*>(.*?)</a>', html, flags=re.S):
            link += 1
            nome = c.pulisci(re.sub(r'<[^>]+>', ' ', htmllib.unescape(testo))).rstrip('* ')
            tk = ana.ticker(nome, 'ubs-indice')
            if tk:
                mappa[tk] = href if href.startswith('http') else BASE + href.split('/')[-1]
    print(f'    ubs: indice letto in {pagine_ok} pagine, {link} link, {len(mappa)} titoli nostri riconosciuti')
    if mappa:
        pd.DataFrame(sorted(mappa.items()), columns=['ticker', 'pagina']).to_csv(CACHE, index=False)
    return mappa


def raccogli(ana, oggi, giorni=45):
    fonte = 'ubs'
    out, limite = [], oggi - pd.Timedelta(days=giorni)
    pagine = _mappa_pagine(ana)
    scaricate = con_tabella = 0
    for tk, url in pagine.items():
        html = c.scarica(url, tentativi=2)
        if not html:
            continue
        scaricate += 1
        testo = htmllib.unescape(html)
        if not re.search(r'Price Target\s*\((€|EUR)\)', testo):   # solo pagine con target in euro
            continue
        con_tabella += 1
        for r in c.righe_tabelle(html):
            if len(r) < 4:
                continue
            d = c.data(r[0][0])
            if d is None or d < limite:
                continue
            out.append(c.record(tk, d, 'Ubs', ana.rating(r[3][0]), c.numero(r[2][0]), fonte))
    print(f'    ubs: pagine titolo scaricate {scaricate}/{len(pagine)}, con tabella target in euro {con_tabella}')
    return out
