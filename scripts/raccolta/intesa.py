"""Intesa Sanpaolo: archivio pubblico delle raccomandazioni (ultimi 12 mesi). Formato dei file da verificare al primo giro."""
import re
from . import comune as c, generico

PAGINA = 'https://group.intesasanpaolo.com/it/research/RegulatoryDisclosures/archivio-raccomandazioni'


def raccogli(ana, oggi, giorni=45):
    html = c.scarica(PAGINA)
    if not html:
        return []
    out = []
    for l in c.link_pagina(html, '.pdf') + c.link_pagina(html, '.xls'):
        url = l if l.startswith('http') else 'https://group.intesasanpaolo.com' + l
        if re.search(r'equity|azion', url, re.I):
            if url.lower().endswith('.pdf'):
                out += generico.pdf(url, 'intesa', ana, 'Intesa SanPaolo', oggi, giorni)
    return out
