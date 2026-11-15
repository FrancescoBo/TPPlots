"""Intesa Sanpaolo Research - 'Equity Research Publications in Last 12M'.

Ogni file giornaliero (AAAAMMGGEquity_ita.pdf) è il REGISTRO di tutte le pubblicazioni degli ultimi 12 mesi, quindi il più recente
contiene già tutto lo storico: si legge UN solo file. Ogni riga è una pubblicazione (anche se il giudizio non cambia):
  Data | Società | Motivo | Analisti | Rating (Ord.) | Target (Ord.) | Prezzo (Ord.) | [Rating/Target/Prezzo risparmio] | Valuta | 12M | Equity
Si tengono solo le righe 'Company ...' in EUR con rating e target ordinari; la regola 'solo variazioni' (vedi aggiorna_raccomandazioni.py)
scarta le pubblicazioni che ripetono giudizio e target precedenti."""
import re
from collections import Counter
import pandas as pd
from . import comune as c

PAGINA = 'https://group.intesasanpaolo.com/it/research/RegulatoryDisclosures/archivio-raccomandazioni'
RIGA = re.compile(
    r'^\s*(?P<data>\d{2}/\d{2}/\d{4})\s+(?P<soc>.+?)\s+(?P<motivo>Company\s+(?:Update|Note|Section\s+Light))\s+'
    r'(?P<analisti>.*?)\s*(?P<rating>[A-Z][A-Z.]{1,14})\s+(?P<tp>\d[\d.,]*)\s+(?P<px>\d[\d.,]*)\s+'
    r'(?:[A-Z][A-Z.]{1,14}\s+\d[\d.,]*\s+\d[\d.,]*\s+)?EUR\s+12M', re.M)
RATING = {'BUY': 'Buy', 'NEUTRAL': 'Neutral', 'UNDERP.': 'Underperform', 'UNDERP': 'Underperform', 'OUTP.': 'Outperform',
          'OUTP': 'Outperform', 'OUTPERF.': 'Outperform', 'ADD': 'Add', 'HOLD': 'Hold', 'REDUCE': 'Reduce', 'SELL': 'Sell',
          'ACC.': 'Accumulate', 'ACCUMULATE': 'Accumulate', 'OUTPERFORM': 'Outperform', 'UNDERPERFORM': 'Underperform'}


def righe_da_testo(testo, ana, oggi, giorni):
    out, limite = [], oggi - pd.Timedelta(days=giorni)
    non_rating, ignote = Counter(), Counter()
    for m in RIGA.finditer(testo or ''):
        d = c.data(m['data'])
        if d is None or d < limite:
            continue
        rt = RATING.get(m['rating'])
        if rt is None:
            non_rating[m['rating']] += 1
            continue
        tk = ana.ticker(m['soc'], 'intesa', log=False)
        if not tk:
            ignote[m['soc'].strip()] += 1
            continue
        out.append(c.record(tk, d, 'Intesa SanPaolo', rt, c.numero(m['tp']), 'intesa'))
    return out, non_rating, ignote


def raccogli(ana, oggi, giorni=45):
    html = c.scarica(PAGINA)
    if not html:
        print('    intesa: pagina archivio non raggiungibile')
        return []
    link = c.link_pagina(html, '.pdf')
    url = [l if l.startswith('http') else 'https://group.intesasanpaolo.com' + l for l in link]
    url = sorted({u for u in url if re.search(r'/\d{8}Equity_ita\.pdf$', u)}, reverse=True)
    print(f'    intesa: {len(url)} file equity trovati; leggo solo il più recente: {url[0] if url else "-"}')
    if not url:
        return []
    out, non_rating, ignote = righe_da_testo(c.pdf_testo(url[0]), ana, oggi, giorni)
    if non_rating:
        print('    intesa: rating non previsti (righe scartate):', dict(non_rating.most_common(8)))
    if ignote:
        print('    intesa: società non riconosciute (prime 15):', [f'{n} ({k})' for n, k in ignote.most_common(15)])
    return out
