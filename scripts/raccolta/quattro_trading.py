"""4trading.it: articoli giornalieri 'Raccomandazioni analisti - <giorno> <mese>'.

Le pagine di categoria elencano gli articoli:  .../categoria/analisi/raccomandazioni-analisti?d=0  (ultimi giorni)
e ?mx=1, ?mx=2, ... (mesi precedenti, usati nel recupero esteso).
Ogni articolo ha una tabella: Titolo | Emittente | Raccomandazione | Variazione | Target | Variazione
con valori nuovi e, tra parentesi, i precedenti:  'Buy (Accumulate)',  '105 (90)'.
La data della raccomandazione è quella di pubblicazione dell'articolo."""
import re
import pandas as pd
from . import comune as c

BASE = 'https://4trading.it'
CATEGORIA = BASE + '/categoria/analisi/raccomandazioni-analisti'
ART_RE = re.compile(r'(/articoli/\d+/raccomandazioni-analisti[^"\'\s<>]*)')


def _articoli(html):
    return sorted({BASE + m if m.startswith('/') else m for m in ART_RE.findall(html)})


def _data_articolo(html, url):
    t = c.testo_pagina(html)
    m = re.search(r'Pubblicato il\s+(\d{1,2}/\d{1,2}/\d{4})', t)
    if m:
        return c.data(m[1])
    m = re.search(r'Raccomandazioni analisti\s*-\s*(\d{1,2})\s+([a-zà-ù]+)', t, re.I)
    if m and m[2].lower() in c.MESI:       # senza anno: si assume quello corrente
        return pd.Timestamp(pd.Timestamp.today().year, c.MESI[m[2].lower()], int(m[1]))
    return None


def _prima_parte(s):
    """'Buy (Accumulate)' -> 'Buy';  '105 (90)' -> '105'."""
    return c.pulisci(re.split(r'\(', s or '')[0])


def _righe(html, d, ana, fonte):
    out = []
    for r in c.righe_tabelle(html):
        t = [x[0] for x in r]
        if len(t) < 5 or t[0].strip().lower() in ('titolo', 'società', 'societa', ''):
            continue
        tk = ana.ticker(t[0], fonte)
        if not tk:
            continue
        rating = ana.rating(_prima_parte(t[2]))
        target = c.numero(_prima_parte(t[4])) if len(t) > 4 else None
        if not rating and target is None:
            continue
        out.append(c.record(tk, d, ana.emittente(t[1]), rating, target, fonte))
    return out


def raccogli(ana, oggi, giorni=14, mesi=0):
    fonte = '4trading'
    pagine = [CATEGORIA + '?d=0'] + [f'{CATEGORIA}?mx={i}' for i in range(1, mesi + 1)]
    urls = []
    for p in pagine:
        h = c.scarica(p)
        if h:
            urls += _articoli(h)
    out, limite = [], oggi - pd.Timedelta(days=giorni)
    for u in dict.fromkeys(urls):
        html = c.scarica(u, tentativi=2)
        if not html:
            continue
        d = _data_articolo(html, u)
        if d is None or d < limite or d > oggi + pd.Timedelta(days=1):
            continue
        out += _righe(html, d, ana, fonte)
    return out
