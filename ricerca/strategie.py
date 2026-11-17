"""Strategie di base per le fasi 2+ e generatore di strategie casuali (da usare dalla fase 4).

Nessuna strategia vera e propria: solo buy-and-hold di un paniere e il confronto con scelte casuali.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import motore as M

SEME = 20260430          # seme fisso di tutto lo studio
N_RIPETIZIONI = 500


class BuyAndHold(M.Strategia):
    """Compra all'apertura della seduta `i_ingresso` i titoli indicati (importo uguale per ciascuno) e tiene."""

    def __init__(self, tickers, importo, i_ingresso, uscite: M.Uscite | None = None):
        self.tickers, self.importo, self.i_ingresso = list(tickers), float(importo), int(i_ingresso)
        self.uscite = uscite or M.Uscite()

    def decidi(self, i, sim):
        if i != self.i_ingresso - 1:
            return []
        return [M.Acquisto(tk, self.importo, uscite=self.uscite) for tk in self.tickers]


class StrategiaCasuale(M.Strategia):
    """Replica il calendario di ingressi di una strategia (stesse date, stesso numero di operazioni, stesse uscite)
    ma sceglie i titoli a caso tra quelli ammessi del giorno (e non gia' in portafoglio).

    ingressi: dict {i_decisione: numero di acquisti}; ammessi: DataFrame bool seduta x titolo (universo al giorno i)."""

    def __init__(self, ingressi: dict, ammessi: pd.DataFrame, importo: float, uscite: M.Uscite, rng: np.random.Generator):
        self.ingressi, self.ammessi, self.importo, self.uscite, self.rng = ingressi, ammessi, float(importo), uscite, rng

    def decidi(self, i, sim):
        n = self.ingressi.get(i, 0)
        if not n:
            return []
        riga = self.ammessi.iloc[i]
        cand = [tk for tk in riga.index[riga.values] if tk not in sim.pos and sim.negoziabile(tk, i + 1)]
        if not cand:
            return []
        scelti = self.rng.choice(cand, size=min(n, len(cand)), replace=False)
        return [M.Acquisto(str(tk), self.importo, uscite=self.uscite) for tk in scelti]


def ripeti_casuale(crea_sim, ingressi, ammessi, importo, uscite, inizio, fine, n=N_RIPETIZIONI, seme=SEME):
    """Esegue `n` repliche casuali. crea_sim() deve restituire un Simulatore nuovo. Ritorna la lista dei KPI
    (rendimento netto = patrimonio finale / capitale - 1)."""
    rng = np.random.default_rng(seme)
    out = []
    for _ in range(n):
        sim = crea_sim()
        ris = sim.esegui(StrategiaCasuale(ingressi, ammessi, importo, uscite, rng), inizio=inizio, fine=fine)
        out.append(ris.kpi())
    return out
