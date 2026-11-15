"""Adattatori generici: tabelle HTML con intestazioni riconoscibili (es. 4trading, Teleborsa) e PDF di storico (Equita, Intesa)."""
import re
import pandas as pd
from . import comune as c

SINONIMI = {
    'societa': ['societa', 'società', 'titolo', 'azienda', 'azione', 'nome', 'stock'],
    'emittente': ['banca', 'broker', 'istituto', 'analista', 'banca d\'affari', 'banca d’affari', 'intermediario'],
    'rating': ['giudizio', 'raccomandazione', 'rating', 'consiglio', 'recommendation'],
    'target': ['target', 'target price', 'prezzo obiettivo', 'tp', 'price target', 'obiettivo'],
    'data': ['data', 'date'],
}


def _mappa_colonne(intest):
    m = {}
    for i, t in enumerate(intest):
        t = c.pulisci(t).lower()
        for k, syn in SINONIMI.items():
            if k not in m and any(t == s or t.startswith(s) for s in syn):
                m[k] = i
    return m


def tabelle_html(url, fonte, ana, oggi, emittente_fisso=None, data_default=None):
    """Legge ogni tabella con colonne riconoscibili. La data viene dalla colonna 'data', altrimenti dal testo
    della pagina/URL, altrimenti `data_default`."""
    html = c.scarica(url)
    if not html:
        return []
    d_pag = c.data(url) or data_default
    if d_pag is None:
        m = re.search(r'(\d{1,2}\s+[A-Za-zà-ù]+\s+20\d\d|\d{1,2}[/.]\d{1,2}[/.]20\d\d)', c.testo_pagina(html))
        d_pag = c.data(m[1]) if m else None
    out, mappa = [], None
    for r in c.righe_tabelle(html):
        testi = [x[0] for x in r]
        mm = _mappa_colonne(testi)
        if 'societa' in mm and ('target' in mm or 'rating' in mm):
            mappa = mm
            continue
        if not mappa or len(testi) <= max(mappa.values()):
            continue
        tk = ana.ticker(testi[mappa['societa']], fonte)
        if not tk:
            continue
        d = c.data(testi[mappa['data']]) if 'data' in mappa else d_pag
        if d is None:
            continue
        emi = emittente_fisso or (ana.emittente(testi[mappa['emittente']]) if 'emittente' in mappa else None)
        if not emi:
            continue
        out.append(c.record(tk, d, emi, ana.rating(testi[mappa['rating']]) if 'rating' in mappa else '',
                            c.numero(testi[mappa['target']]) if 'target' in mappa else None, fonte))
    return out


def righe_pdf(testo, fonte, ana, emittente, giorni, oggi):
    """Estrae righe 'data / società / giudizio / target' da un PDF convertito in testo con layout.
    Accetta una riga solo se riconosce data, titolo, giudizio noto e almeno un numero."""
    out, limite = [], oggi - pd.Timedelta(days=giorni)
    for riga in (testo or '').splitlines():
        celle = [x.strip() for x in re.split(r'\s{2,}|\t|;', riga) if x.strip()]
        if len(celle) < 3:
            continue
        d = next((c.data(x) for x in celle if re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}[/.]\d{1,2}[/.]\d{2,4}', x)), None)
        rating = next((x for x in celle if x.lower() in ana.classi), None)
        tk = next((t for t in (ana.ticker(x, fonte) for x in celle if re.search(r'[A-Za-z]{3}', x) and x != rating) if t), None)
        nums = [c.numero(x) for x in celle if re.fullmatch(r'[\d.,]+\s*(€|EUR)?', x) and not re.search(r'\d{4}-|/', x)]
        nums = [n for n in nums if n]
        if d is None or d < limite or not rating or not tk or not nums:
            continue
        out.append(c.record(tk, d, emittente, rating, nums[-1], fonte))
    return out


def pdf(url, fonte, ana, emittente, oggi, giorni=45):
    return righe_pdf(c.pdf_testo(url), fonte, ana, emittente, giorni, oggi)
