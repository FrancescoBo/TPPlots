"""Equita SIM: storico pubblico delle raccomandazioni azionarie (PDF). Formato da verificare al primo giro."""
from . import generico

URL = 'https://www.equita.eu/static/public/raccomandazioni/StoricoRaccomandazioni_Equity.pdf'


def raccogli(ana, oggi, giorni=45):
    return generico.pdf(URL, 'equita', ana, 'Equita', oggi, giorni)
