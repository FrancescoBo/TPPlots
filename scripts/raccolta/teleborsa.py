"""Teleborsa Consensus: testo libero ('<broker> ... target price ... a X euro'). Estrazione prudente: serve broker, giudizio e target nella stessa frase."""
import re
import pandas as pd
from . import comune as c

BASE = 'https://www.teleborsa.it'


def raccogli(ana, oggi, giorni=7):
    html = c.scarica(f'{BASE}/News/Consensus')
    if not html:
        return []
    out = []
    for href, titolo in re.findall(r'<a[^>]+href=["\']([^"\']*/news/[^"\']+)["\'][^>]*>(.*?)</a>', html, flags=re.S | re.I)[:60]:
        t = c.pulisci(re.sub(r'<[^>]+>', ' ', titolo))
        m = re.search(r'(?P<soc>[A-Z][\w&\.\' ]{2,40}?):\s*(?P<broker>[A-Z][\w\.& ]{2,30}?)\s.*?(?P<rat>buy|hold|sell|outperform|neutral|overweight|underweight|accumulate|add|reduce)\b.*?(?P<tp>\d+[.,]?\d*)\s*euro', t, re.I)
        if not m:
            continue
        tk = ana.ticker(m['soc'], 'teleborsa')
        if not tk:
            continue
        out.append(c.record(tk, oggi, ana.emittente(m['broker']), m['rat'].capitalize(), c.numero(m['tp']), 'teleborsa'))
    return out
