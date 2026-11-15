"""Intesa Sanpaolo: archivio pubblico delle raccomandazioni (ultimi 12 mesi). Formato dei file da verificare al primo giro."""
import re
import pandas as pd
from . import comune as c, generico

PAGINA = 'https://group.intesasanpaolo.com/it/research/RegulatoryDisclosures/archivio-raccomandazioni'
MAX_FILE = 400     # tetto di sicurezza sul numero di file letti per giro


def raccogli(ana, oggi, giorni=45):
    html = c.scarica(PAGINA)
    if not html:
        print('    intesa: pagina archivio non raggiungibile')
        return []
    link = c.link_pagina(html, '.pdf') + c.link_pagina(html, '.xls')
    url = [l if l.startswith('http') else 'https://group.intesasanpaolo.com' + l for l in link]
    url = sorted({u for u in url if u.lower().endswith('.pdf') and re.search(r'equity|azion', u, re.I)}, reverse=True)
    print(f'    intesa: {len(link)} link a file trovati, {len(url)} PDF equity; ne leggo {min(len(url), MAX_FILE)}')
    # i file sono giornalieri (AAAAMMGGEquity_ita.pdf): si leggono solo quelli della finestra richiesta
    limite = oggi - pd.Timedelta(days=giorni + 1)
    scelti = []
    for u in url:
        m = re.search(r'/(\d{8})Equity', u)
        if m and pd.Timestamp(m[1]) >= limite:
            scelti.append(u)
    scelti = scelti[:MAX_FILE]
    print(f'    intesa: file nella finestra di {giorni} giorni: {len(scelti)}')
    out = []
    for u in scelti:
        out += generico.pdf(u, 'intesa', ana, 'Intesa SanPaolo', oggi, giorni)
    return out
