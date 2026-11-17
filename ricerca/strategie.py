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


# ================================================================================================ fasi 4-6
# Strategie di DECISIONI_FASE3: rotazione (famiglia A) ed eventi (famiglia B), regole di uscita, dimensionamento,
# e strategie casuali che replicano il calendario di ingressi di ciascuna combinazione.
from dataclasses import dataclass, replace

import dati as D
import riferimenti as RF
import segnali as S

LIQUIDITA = (1e6, 5e6)
INF = 10 ** 6


class Mercato:
    """Dati e segnali (fino al 2026-04-30) in forma numpy, costruiti una volta sola."""

    def __init__(self, fine=D.DATA_FINE):
        self.pr = D.carica_prezzi(fine)
        rac, self.esclusi = D.carica_raccomandazioni(self.pr, fine)
        self.an = D.carica_anagrafica()
        self.ix = D.carica_indice(fine)
        self.sg = S.calcola_segnali(self.pr, rac, self.an, self.ix)
        self.dpan = S.dividendi_pannello(self.pr, D.carica_dividendi(fine))
        self.esenti = D.carica_tobin_esenti()
        self.liq = M.pannello_liquidita(self.pr)
        self.cx = M.Contesto(self.pr, self.dpan, self.liq)
        self.cal, self.tickers, self.col = self.cx.cal, self.cx.tickers, self.cx.col
        self.n = len(self.cal)
        self.i0 = int(self.cal.searchsorted(D.INIZIO_SCELTA))
        self.idec = self.i0 - 1
        self.i1 = self.n - 1
        assert self.cal[self.i0] == D.INIZIO_SCELTA and self.cal[self.i1] == fine
        v = self.sg.variabili
        arr = lambda df: df.reindex(columns=self.tickers).values.astype(float)
        self.seg = {'MOM': arr(v['momentum_120']), 'REV': arr(v['saldo_rev_60']), 'POT': arr(v['potenziale'])}
        self.atr = arr(v['atr_14_pct'])
        self.tp = arr(self.sg.consenso['tp'])
        self.eventi = {'ALZ5': self.sg.eventi['alzata_5'].reindex(columns=self.tickers).values.astype(bool),
                       'ALZ10': self.sg.eventi['alzata_10'].reindex(columns=self.tickers).values.astype(bool)}
        self.univ = self.sg.universo.reindex(columns=self.tickers).values.astype(bool)
        liq = self.cx.liq
        self.elig = {L: self.univ & (np.nan_to_num(liq, nan=-1.0) >= L) for L in LIQUIDITA}
        self.comp = {}
        for L in LIQUIDITA:
            ok = self.elig[L] & ~np.isnan(self.seg['MOM']) & ~np.isnan(self.seg['REV'])
            r = lambda X: pd.DataFrame(np.where(ok, X, np.nan)).rank(axis=1, pct=True).values
            self.comp[L] = (r(self.seg['MOM']) + r(self.seg['REV'])) / 2
        self._rank = {}
        # rendimento da dividendo e pesi del FTSE MIB (solo dati fino a idec per i pesi)
        cff = self.pr.chiusura_ff()
        self.pesi = RF.pesi_componenti(cff, self.an.azioni_circolazione, self.idec)
        self.y_div = RF.rendimento_dividendo_giornaliero(cff, self.dpan, self.pesi)
        self.cff = self.cx.cff

    def segnale(self, nome, L):
        return self.comp[L] if nome == 'COMP' else self.seg[nome]

    def ranghi(self, nome, L):
        """(rank, ordine): rank[t, k] = posizione (0 = migliore) tra i titoli ammessi in t, INF se non ammesso;
        ordine[t] = colonne ordinate. Parita': prima il titolo piu' liquido."""
        key = (nome, L)
        if key not in self._rank:
            X = self.segnale(nome, L)
            valido = self.elig[L] & ~np.isnan(X)
            liqv = np.nan_to_num(self.cx.liq)
            rank = np.full(X.shape, INF, dtype=np.int64)
            ordine = [None] * self.n
            for t in range(self.idec, self.n):
                idx = np.flatnonzero(valido[t])
                o = idx[np.lexsort((-liqv[t, idx], -X[t, idx]))]
                ordine[t] = o
                rank[t, o] = np.arange(len(o))
            self._rank[key] = (rank, ordine)
        return self._rank[key]

    def sim(self, config=None):
        return M.Simulatore(self.pr, None, None, self.esenti, config or M.Config(), contesto=self.cx)

    def patrimonio(self, sim, i):
        return sim.cash + sum(pz.azioni * self.cff[i, self.col[tk]] for tk, pz in sim.pos.items())


@dataclass(frozen=True)
class Regole:
    """Regole di uscita aggiunte a quella di base (rotazione per A, tempo per B). Percentuali come frazioni."""
    take_profit: float | None = None
    stop: float | None = None
    stop_atr: float | None = None          # multiplo dell'ATR% alla data del segnale
    trailing: float | None = None
    tempo: int | None = None               # sedute
    tp_medio: float | None = None          # esci se prezzo >= tp_medio * TP medio

    def nome(self):
        v = [f'TP{100 * self.take_profit:g}' if self.take_profit else '', f'SL{100 * self.stop:g}' if self.stop else '',
             f'SLATR{self.stop_atr:g}' if self.stop_atr else '', f'TR{100 * self.trailing:g}' if self.trailing else '',
             f'T{self.tempo}' if self.tempo else '', f'TPM{self.tp_medio:g}' if self.tp_medio else '']
        return '+'.join(x for x in v if x) or 'base'

    def uscite(self, mk, i, k) -> M.Uscite:
        stop = self.stop
        if self.stop_atr is not None:
            a = mk.atr[i, k]
            if not np.isnan(a):
                s2 = min(self.stop_atr * a, 0.95)
                stop = s2 if stop is None else min(stop, s2)
        return M.Uscite(take_profit_pct=self.take_profit, stop_pct=stop, trailing_pct=self.trailing, max_sedute=self.tempo)

    def vendite(self, mk, i, sim):
        if self.tp_medio is None:
            return []
        out = []
        for tk in sim.pos:
            k = mk.col[tk]
            tp = mk.tp[i, k]
            if not np.isnan(tp) and mk.cff[i, k] >= self.tp_medio * tp:
                out.append(M.Vendita(tk, 'tp_medio'))
        return out


@dataclass(frozen=True)
class Dim:
    """Dimensionamento: n blocchi; blocchi fissi (capitale/n) o reinvestimento (patrimonio corrente/n); peso ~ 1/ATR."""
    n: int
    reinvest: bool = False
    inv_atr: bool = False

    def importo(self, mk, sim, i, k, L):
        base = (mk.patrimonio(sim, i) if self.reinvest else sim.capitale) / self.n
        if self.inv_atr and not np.isnan(mk.atr[i, k]) and mk.atr[i, k] > 0:
            ok = mk.elig[L][i] & ~np.isnan(mk.atr[i]) & (mk.atr[i] > 0)
            ref = np.median(1.0 / mk.atr[i][ok]) if ok.any() else np.nan
            if ref and not np.isnan(ref):
                base *= float(np.clip((1.0 / mk.atr[i, k]) / ref, 0.5, 1.5))
        return base


class Rotazione(M.Strategia):
    """Famiglia A: ogni R sedute (dal giorno di scelta) ordina i titoli ammessi per il segnale S e tiene i primi K;
    vende solo i titoli scesi oltre la posizione K + B (o non piu' ammessi)."""

    def __init__(self, mk: Mercato, S: str, R: int, K: int, B: int, L: float, regole: Regole = Regole(), dim: Dim | None = None):
        self.mk, self.S, self.R, self.K, self.B, self.L, self.regole = mk, S, R, K, B, L, regole
        self.dim = dim or Dim(K)
        self.rank, self.ordine = mk.ranghi(S, L)

    def decidi(self, i, sim):
        mk = self.mk
        if i < mk.idec:
            return []
        ordini = list(self.regole.vendite(mk, i, sim))
        venduti = {o.ticker for o in ordini}
        if (i - mk.idec) % self.R == 0:
            for tk in sim.pos:
                if self.rank[i, mk.col[tk]] >= self.K + self.B and tk not in venduti:
                    ordini.append(M.Vendita(tk, 'strategia'))
                    venduti.add(tk)
            restano = [tk for tk in sim.pos if tk not in venduti]
            liberi = self.dim.n - len(restano)
            for k in self.ordine[i][:self.K]:
                if liberi <= 0:
                    break
                tk = mk.tickers[k]
                if tk in sim.pos or tk in venduti:
                    continue
                ordini.append(M.Acquisto(tk, self.dim.importo(mk, sim, i, k, self.L), uscite=self.regole.uscite(mk, i, k)))
                liberi -= 1
        else:
            # fuori dai ribilanciamenti i blocchi liberi (uscite per regola) restano vuoti fino al prossimo
            pass
        return ordini


class Eventi(M.Strategia):
    """Famiglia B: compra il giorno dopo un evento se c'e' un blocco libero; a parita' il COMP piu' alto."""

    def __init__(self, mk: Mercato, evento: str, filtro: str, N: int, L: float, regole: Regole, dim: Dim | None = None):
        self.mk, self.evento, self.filtro, self.N, self.L, self.regole = mk, evento, filtro, N, L, regole
        self.dim = dim or Dim(N)
        self.E = mk.eventi[evento]

    def decidi(self, i, sim):
        mk = self.mk
        if i < mk.idec:
            return []
        ordini = list(self.regole.vendite(mk, i, sim))
        venduti = {o.ticker for o in ordini}
        liberi = self.dim.n - (len(sim.pos) - len(venduti))
        if liberi <= 0:
            return ordini
        cand = np.flatnonzero(self.E[i] & mk.elig[self.L][i])
        if self.filtro == 'MOM>0':
            cand = cand[mk.seg['MOM'][i, cand] > 0]
        elif self.filtro == 'COMP>=0.5':
            cand = cand[mk.comp[self.L][i, cand] >= 0.5]
        if len(cand) == 0:
            return ordini
        c = np.nan_to_num(mk.comp[self.L][i, cand], nan=-1.0)
        lq = np.nan_to_num(mk.cx.liq[i, cand])
        for k in cand[np.lexsort((-lq, -c))]:
            tk = mk.tickers[k]
            if tk in sim.pos or tk in venduti:
                continue
            ordini.append(M.Acquisto(tk, self.dim.importo(mk, sim, i, k, self.L), uscite=self.regole.uscite(mk, i, k)))
            liberi -= 1
            if liberi <= 0:
                break
        return ordini


# ------------------------------------------------------------------------------------------ casuali
def piano_da_trades(trades: pd.DataFrame):
    """Calendario degli ingressi di una simulazione: {giorno_decisione: [(importo, seduta_uscita_forzata | None)]}.
    L'uscita e' forzata alla stessa data solo se la strategia vendeva per sua regola ('strategia', cioe' la
    classifica); le uscite di prezzo e di tempo si ripetono con le stesse regole."""
    piano = {}
    for r in trades.itertuples():
        forzata = int(r.i_uscita) if r.motivo == 'strategia' else None
        piano.setdefault(int(r.i_ingresso) - 1, []).append((float(r.importo_ordine), forzata))
    return piano


class Casuale(M.Strategia):
    """Replica il calendario di una strategia con titoli a caso tra quelli ammessi (universo e liquidita' >= L)."""

    def __init__(self, mk: Mercato, L: float, piano: dict, regole: Regole, rng):
        self.mk, self.L, self.piano, self.regole, self.rng = mk, L, piano, regole, rng
        self.forzate = {}

    def decidi(self, i, sim):
        mk = self.mk
        ordini = list(self.regole.vendite(mk, i, sim))
        venduti = {o.ticker for o in ordini}
        for tk, ex in list(self.forzate.items()):
            if tk not in sim.pos:
                del self.forzate[tk]
            elif ex - 1 == i and tk not in venduti:
                ordini.append(M.Vendita(tk, 'strategia'))
                venduti.add(tk)
        acq = self.piano.get(i)
        if acq:
            cand = [k for k in np.flatnonzero(mk.elig[self.L][i]) if mk.tickers[k] not in sim.pos and mk.tickers[k] not in venduti]
            if cand:
                scelti = self.rng.choice(cand, size=min(len(acq), len(cand)), replace=False)
                for k, (importo, forzata) in zip(scelti, acq):
                    tk = mk.tickers[int(k)]
                    ordini.append(M.Acquisto(tk, importo, uscite=self.regole.uscite(mk, i, int(k))))
                    if forzata is not None:
                        self.forzate[tk] = forzata
        return ordini


def percentile_casuali(mk: Mercato, config: M.Config, trades: pd.DataFrame, L: float, regole: Regole, rendimento_strategia: float,
                       id_comb: int, n: int = N_RIPETIZIONI, seme: int = SEME):
    """500 strategie casuali con lo stesso calendario di ingressi, importi, regole di uscita e filtro di liquidita'.
    Ritorna (percentile del rendimento netto della strategia tra i casuali, rendimenti casuali)."""
    piano = piano_da_trades(trades)
    ss = np.random.SeedSequence([seme, int(id_comb)])
    rend = np.empty(n)
    for j, fig in enumerate(ss.spawn(n)):
        sim = mk.sim(config)
        sim.esegui(Casuale(mk, L, piano, regole, np.random.default_rng(fig)), inizio=mk.idec, fine=mk.i1)
        rend[j] = sim.equity[-1] / sim.capitale - 1
    pct = 100.0 * ((rend < rendimento_strategia).sum() + 0.5 * (rend == rendimento_strategia).sum()) / n
    return pct, rend
