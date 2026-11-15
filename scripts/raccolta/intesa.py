"""Intesa Sanpaolo: archivio pubblico delle raccomandazioni (ultimi 12 mesi). Formato dei file da verificare al primo giro."""
import re
from . import comune as c, generico

PAGINA = 'https://group.intesasanpaolo.com/it/research/RegulatoryDisclosures/archivio-raccomandazioni'
MAX_FILE = 15      # si leggono solo i file più recenti per nome (ordine decrescente)


def raccogli(ana, oggi, giorni=45):
    html = c.scarica(PAGINA)
    if not html:
        print('    intesa: pagina archivio non raggiungibile')
        return []
    link = c.link_pagina(html, '.pdf') + c.link_pagina(html, '.xls')
    url = [l if l.startswith('http') else 'https://group.intesasanpaolo.com' + l for l in link]
    url = sorted({u for u in url if u.lower().endswith('.pdf') and re.search(r'equity|azion', u, re.I)}, reverse=True)
    print(f'    intesa: {len(link)} link a file trovati, {len(url)} PDF equity; ne leggo {min(len(url), MAX_FILE)}')
    for u in url[:3]:
        print('      esempio:', u)
    out = []
    for u in url[:MAX_FILE]:
        out += generico.pdf(u, 'intesa', ana, 'Intesa SanPaolo', oggi, giorni)
    return out
