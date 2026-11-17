"""Termini di confronto: FTSE MIB buy-and-hold con dividendi stimati (DECISIONI_FASE3, punto 5).

Dividendi stimati: pesi fissi = capitalizzazione dei 40 titoli piu' capitalizzati (con azioni note) alla chiusura
del giorno di scelta (idec); rendimento da dividendo di ogni giorno t = somma pesata di dividendo(t) / chiusura(t-1)
dei componenti. L'indice e' trattato come un titolo con quote frazionarie: acquisto all'apertura del primo giorno
(commissione del piano, slittamento 0,05%, niente Tobin), dividendi incassati in contanti al 74% (come per le azioni:
non reinvestiti, cosi' non si tassano due volte), vendita alla chiusura dell'ultimo giorno con commissione,
slittamento 0,05% e imposta del 26% sulla plusvalenza di prezzo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import motore as M

N_COMPONENTI = 40


def pesi_componenti(chiusura_ff: pd.DataFrame, azioni: pd.Series, idec: int, n=N_COMPONENTI) -> pd.Series:
    cap = (chiusura_ff.iloc[idec] * azioni.reindex(chiusura_ff.columns).astype(float)).dropna().sort_values(ascending=False)
    top = cap.iloc[:n]
    return top / top.sum()


def rendimento_dividendo_giornaliero(chiusura_ff: pd.DataFrame, dpan: pd.DataFrame, pesi: pd.Series) -> pd.Series:
    """Rendimento da dividendo lordo dell'indice nel giorno t (sulla chiusura di t-1), per ogni seduta."""
    cols = list(pesi.index)
    y = (dpan[cols] / chiusura_ff[cols].shift(1)).fillna(0.0)
    return (y * pesi).sum(axis=1)


def ftsemib_bh(indice: pd.DataFrame, y_div: pd.Series, i0: int, i1: int, capitale: float = M.CAPITALE,
               con_dividendi: bool = True, lordo: bool = False, netto_dividendi: float = M.NETTO_DIVIDENDI):
    """Buy-and-hold dal'apertura di i0 alla chiusura di i1. Ritorna dict con 'equity' (Series giornaliera; l'ultimo valore
    e' dopo vendita, commissione e imposta), 'rendimento' e i dettagli."""
    cal = indice.index
    p0 = float(indice.apertura.iloc[i0]); pc = indice.chiusura.values
    sl = 0.0 if lordo else M.SLITT_GRANDE
    if lordo:
        v0, c0 = capitale, 0.0
    else:
        v0 = (capitale - M.COMM_FISSA + M.COMM_PERC * M.COMM_SOGLIA) / (1 + M.COMM_PERC)   # v0 + commissione(v0) = capitale
        c0 = M.commissione(v0)
    unita = v0 / (p0 * (1 + sl))
    cash = capitale - v0 - c0
    div_cum = 0.0
    eq = []
    for t in range(i0, i1 + 1):
        if con_dividendi and t > i0:
            d = float(y_div.iloc[t]) * float(pc[t - 1]) * (1.0 if lordo else netto_dividendi)
            div_cum += unita * d
        eq.append(cash + unita * pc[t] + div_cum)
    v1 = unita * float(pc[i1]) * (1 - sl)
    c1 = 0.0 if lordo else M.commissione(v1)
    ris = v1 - c1 - (v0 + c0)
    tassa = 0.0 if lordo else M.RegistroFiscale().realizza(ris, cal[i1].year)
    finale = cash + v1 - c1 - tassa + div_cum
    eq[-1] = finale
    return dict(equity=pd.Series(eq, index=cal[i0:i1 + 1]), patrimonio_finale=finale, rendimento=finale / capitale - 1,
                dividendi_incassati=div_cum, commissioni=c0 + c1, tassa=tassa)
