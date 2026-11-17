"""Motore di simulazione giornaliero (regole del piano, sezione "Regole di simulazione").

Tempi: la strategia decide alla chiusura della seduta i; gli ordini sono eseguiti nella seduta i+1
(mai nella stessa seduta del segnale). Esecuzione con apertura/massimo/minimo della seduta.

Costi per operazione: commissione 6,40 EUR + 0,24% della parte oltre 1.460 EUR; Tobin 0,1% sugli acquisti
(salvo titoli esenti); slittamento 0,05% per lato sopra 1 mld di capitalizzazione, 0,20% sotto (e se ignota);
dividendi incassati al 74%; tassa 26% sul guadagno di ogni vendita con credito da minusvalenze (4 anni solari).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------------ parametri
COMM_FISSA = 6.40
COMM_PERC = 0.0024
COMM_SOGLIA = 1460.0
ALIQ_TOBIN = 0.001            # fino al 31/12/2025
ALIQ_TOBIN_2026 = 0.002       # dal 1/1/2026 (legge di bilancio 2026); DECISIONI_FASE3
DATA_TOBIN_2026 = pd.Timestamp('2026-01-01')
ALIQ_TASSA = 0.26
NETTO_DIVIDENDI = 0.74
SLITT_GRANDE = 0.0005
SLITT_PICCOLO = 0.0020
# slittamento per liquidita' (DECISIONI_FASE3): controvalore mediano giornaliero (ultime 60 sedute)
SLITT_LIQ_ALTA, SLITT_LIQ_MEDIA, SLITT_LIQ_BASSA = 0.0005, 0.0010, 0.0020
SOGLIA_LIQ_ALTA, SOGLIA_LIQ_MEDIA = 5e6, 1e6
FINESTRA_LIQUIDITA = 60
SOGLIA_CAP_MLD = 1.0
ANNI_CREDITO = 4          # il credito di un anno Y vale fino al 31/12 di Y+4
CAPITALE = 20000.0


def arrotonda(x: float) -> float:
    """Arrotonda al centesimo (mezzo verso l'alto, con tolleranza per gli errori binari)."""
    return math.floor(x * 100 + 0.5 + 1e-9) / 100


# ------------------------------------------------------------------------------ costi
def commissione(valore: float) -> float:
    """6,40 EUR + 0,24% della parte oltre 1.460 EUR."""
    if valore <= 0:
        return 0.0
    return arrotonda(COMM_FISSA + COMM_PERC * max(0.0, valore - COMM_SOGLIA))


def esente_tobin(ticker: str, data, esenti) -> bool:
    """esenti: insieme di ticker (sempre esenti) oppure dict ticker -> [(dal, al), ...]."""
    if not esenti:
        return False
    if isinstance(esenti, dict):
        if ticker not in esenti:
            return False
        d = pd.Timestamp(data) if data is not None else None
        return any(d is None or (dal <= d <= al) for dal, al in esenti[ticker])
    return ticker in esenti


def aliquota_tobin(data=None, dal_2026: float = ALIQ_TOBIN_2026) -> float:
    """0,1% fino al 31/12/2025, 0,2% dal 1/1/2026 (`dal_2026` permette la sensibilita' allo 0,4%).
    Senza data: aliquota storica 0,1%."""
    if data is not None and pd.Timestamp(data) >= DATA_TOBIN_2026:
        return dal_2026
    return ALIQ_TOBIN


def tobin(valore: float, ticker: str, data=None, esenti=None, aliquota: Optional[float] = None) -> float:
    """Tobin sul valore dell'acquisto: aliquota per data (vedi `aliquota_tobin`), 0 per i titoli esenti."""
    if esente_tobin(ticker, data, esenti) or valore <= 0:
        return 0.0
    if aliquota is None:
        aliquota = aliquota_tobin(data)
    return arrotonda(aliquota * valore)


def slittamento(cap_mld: Optional[float]) -> float:
    """Frazione di slittamento per lato: 0,05% se cap > 1 mld, 0,20% altrimenti (anche se la cap non e' nota)."""
    if cap_mld is not None and not (isinstance(cap_mld, float) and math.isnan(cap_mld)) and cap_mld > SOGLIA_CAP_MLD:
        return SLITT_GRANDE
    return SLITT_PICCOLO


def slittamento_liquidita(controvalore) -> float:
    """Slittamento per lato in base al controvalore mediano giornaliero (EUR): >= 5 mln 0,05%; 1-5 mln 0,10%;
    sotto 1 mln, o ignoto, 0,20%."""
    if controvalore is None or (isinstance(controvalore, float) and math.isnan(controvalore)):
        return SLITT_LIQ_BASSA
    if controvalore >= SOGLIA_LIQ_ALTA:
        return SLITT_LIQ_ALTA
    if controvalore >= SOGLIA_LIQ_MEDIA:
        return SLITT_LIQ_MEDIA
    return SLITT_LIQ_BASSA


def pannello_liquidita(prezzi, finestra: int = FINESTRA_LIQUIDITA, minimo: int = 30) -> pd.DataFrame:
    """Controvalore giornaliero (chiusura x volume) e sua mediana mobile sulle ultime `finestra` sedute, calcolata
    alla chiusura di ogni seduta con i soli dati fino a quel giorno. Le sedute senza riga di prezzo dopo la prima
    quotazione contano zero (nessuno scambio). Servono almeno `minimo` sedute dalla prima quotazione, altrimenti NaN."""
    cv = (prezzi.chiusura * prezzi.volume)
    primo = prezzi.chiusura.notna().cummax()
    cv = cv.where(cv.notna(), 0.0).where(primo)
    return cv.rolling(finestra, min_periods=minimo).median()


# ------------------------------------------------------------------------------ regole di esecuzione (prezzi)
def prezzo_limite_acquisto(limite: float, apertura: float, minimo: float) -> Optional[float]:
    """Acquisto a limite L: eseguito se il minimo <= L, al prezzo piu' basso tra L e l'apertura."""
    return min(limite, apertura) if minimo <= limite else None


def prezzo_take_profit(livello: float, apertura: float, massimo: float) -> Optional[float]:
    """Take profit a P: eseguito se il massimo >= P, al prezzo piu' alto tra P e l'apertura."""
    return max(livello, apertura) if massimo >= livello else None


def prezzo_stop(livello: float, apertura: float, minimo: float) -> Optional[float]:
    """Stop a S: eseguito se il minimo <= S, al prezzo piu' basso tra S e l'apertura (gap incluso)."""
    return min(livello, apertura) if minimo <= livello else None


def esito_uscita(take_profit: Optional[float], stop: Optional[float], apertura: float, massimo: float, minimo: float):
    """(motivo, prezzo) oppure None. Se nella stessa seduta si toccano sia TP sia stop, vale lo stop."""
    ps = prezzo_stop(stop, apertura, minimo) if stop is not None else None
    if ps is not None:
        return 'stop', ps
    pt = prezzo_take_profit(take_profit, apertura, massimo) if take_profit is not None else None
    if pt is not None:
        return 'take_profit', pt
    return None


# ------------------------------------------------------------------------------ tasse
class RegistroFiscale:
    """Tassa del 26% sul guadagno di ogni vendita; le minusvalenze formano un credito (consumato dal piu' vecchio)
    usabile dall'anno della perdita fino a ANNI_CREDITO anni solari dopo. Non si rimborsa l'imposta gia' pagata."""

    def __init__(self, aliquota: float = ALIQ_TASSA, anni: int = ANNI_CREDITO):
        self.aliquota, self.anni = aliquota, anni
        self.crediti: list[list] = []      # [anno_perdita, importo_residuo]
        self.tasse_pagate = 0.0

    def credito_disponibile(self, anno: int) -> float:
        return sum(c[1] for c in self.crediti if c[0] <= anno <= c[0] + self.anni)

    def realizza(self, risultato: float, anno: int) -> float:
        """Registra il risultato netto di una vendita (vendita - acquisto - commissioni - Tobin); ritorna la tassa dovuta."""
        if risultato <= 0:
            if risultato < 0:
                self.crediti.append([anno, -risultato])
            return 0.0
        imponibile = risultato
        for c in sorted(self.crediti, key=lambda c: c[0]):
            if imponibile <= 0:
                break
            if not (c[0] <= anno <= c[0] + self.anni) or c[1] <= 0:
                continue
            uso = min(c[1], imponibile)
            c[1] -= uso
            imponibile -= uso
        tassa = arrotonda(self.aliquota * imponibile)
        self.tasse_pagate += tassa
        return tassa


# ------------------------------------------------------------------------------ ordini e strategia
@dataclass
class Uscite:
    """Regole di uscita di una posizione (livelli riferiti al prezzo di esecuzione base, prima dello slittamento)."""
    take_profit_pct: Optional[float] = None
    stop_pct: Optional[float] = None
    trailing_pct: Optional[float] = None
    max_sedute: Optional[int] = None


@dataclass
class Acquisto:
    ticker: str
    importo: float
    limite: Optional[float] = None          # None = al meglio (apertura); altrimenti ordine limite
    validita: int = 1                       # sedute di validita' dell'ordine limite (a partire da i+1)
    uscite: Uscite = field(default_factory=Uscite)
    nota: str = ''


@dataclass
class Vendita:
    ticker: str
    motivo: str = 'strategia'


@dataclass
class Config:
    lordo: bool = False                     # True = niente costi, Tobin, slittamento, tasse; dividendi al 100%
    mult_costi: float = 1.0                 # commissioni e Tobin
    mult_slittamento: float = 1.0
    interesse_annuo: float = 0.0
    tobin_dal_2026: float = ALIQ_TOBIN_2026   # 0,2% dal 1/1/2026; 0,4% = sensibilita' (disegno di legge di bilancio 2027)
    dividendi_netti: float = NETTO_DIVIDENDI
    liquida_a_fine: bool = True


@dataclass
class Posizione:
    ticker: str
    azioni: int
    costo_base: float            # prezzo * azioni + commissione + tobin pagati (base fiscale)
    prezzo_base: float           # prezzo di esecuzione senza slittamento
    prezzo_eff: float
    i_ingresso: int
    commissione_in: float
    tobin_in: float
    uscite: Uscite
    massimo_da_ingresso: float
    dividendi_lordi: float = 0.0
    dividendi_netti: float = 0.0
    importo_ordine: float = 0.0


class Strategia:
    """Interfaccia: alla chiusura della seduta i restituisce gli ordini per la seduta i+1."""

    def decidi(self, i: int, sim: 'Simulatore') -> list:
        return []


# ------------------------------------------------------------------------------ simulatore
class Contesto:
    """Matrici numpy dei dati di mercato, costruite una sola volta e condivise da molte simulazioni."""

    def __init__(self, prezzi, dividendi_pan: pd.DataFrame, liquidita: Optional[pd.DataFrame] = None):
        self.cal = prezzi.calendario
        self.tickers = list(prezzi.chiusura.columns)
        self.col = {t: k for k, t in enumerate(self.tickers)}
        self.ap = prezzi.apertura.values.astype(float)
        self.mx = prezzi.massimo.values.astype(float)
        self.mn = prezzi.minimo.values.astype(float)
        self.cff = prezzi.chiusura_ff().values.astype(float)
        self.neg = prezzi.negoziabile().values.astype(bool)
        n = len(self.cal)
        self.div = np.zeros((n, len(self.tickers)))
        for t in dividendi_pan.columns:
            if t in self.col:
                self.div[:, self.col[t]] = dividendi_pan[t].values
        self.liq = None
        if liquidita is not None:
            self.liq = np.full((n, len(self.tickers)), np.nan)
            for t in liquidita.columns:
                if t in self.col:
                    self.liq[:, self.col[t]] = liquidita[t].values
        ch = prezzi.chiusura.notna().values
        self.ultima = np.array([int(np.flatnonzero(ch[:, k])[-1]) if ch[:, k].any() else -1 for k in range(len(self.tickers))])
        self.anno2026 = int(np.searchsorted(self.cal.values, np.datetime64(DATA_TOBIN_2026)))   # prima seduta con Tobin 0,2%


class Simulatore:
    def __init__(self, prezzi, dividendi_pan: pd.DataFrame, liquidita: Optional[pd.DataFrame] = None,
                 tobin_esenti=None, config: Optional[Config] = None, capitale: float = CAPITALE,
                 contesto: Optional[Contesto] = None):
        self.p = prezzi
        self.cx = contesto or Contesto(prezzi, dividendi_pan, liquidita)
        self.cal = self.cx.cal
        self.config = config or Config()
        self.cash = float(capitale)
        self.capitale = float(capitale)
        self.pos: dict[str, Posizione] = {}
        self.esenti = tobin_esenti
        self.fisco = RegistroFiscale()
        self.trades: list[dict] = []
        self.equity: list[float] = []
        self.date_eq: list = []
        self.invest: list[float] = []
        self.ordini_limite: list[tuple] = []     # (Acquisto, i_scadenza_inclusa)
        self.costi = {'commissioni': 0.0, 'tobin': 0.0, 'slittamento': 0.0}
        self.eventi: list[str] = []

    # ---- utilita'
    def _slitt(self, tk: str, i: int) -> float:
        """Slittamento per lato: dipende dal controvalore mediano noto alla chiusura del giorno prima (solo dati passati)."""
        if self.config.lordo:
            return 0.0
        liq = None
        if self.cx.liq is not None and tk in self.cx.col and i > 0:
            liq = self.cx.liq[i - 1, self.cx.col[tk]]
        return slittamento_liquidita(None if liq is None or np.isnan(liq) else float(liq)) * self.config.mult_slittamento

    def _comm(self, v: float) -> float:
        return 0.0 if self.config.lordo else arrotonda(commissione(v) * self.config.mult_costi)

    def _tobin(self, v: float, tk: str, i: int) -> float:
        if self.config.lordo:
            return 0.0
        aliq = self.config.tobin_dal_2026 if i >= self.cx.anno2026 else ALIQ_TOBIN
        return arrotonda(tobin(v, tk, self.cal[i], self.esenti, aliq) * self.config.mult_costi)

    def negoziabile(self, tk: str, i: int) -> bool:
        k = self.cx.col.get(tk)
        return k is not None and bool(self.cx.neg[i, k])

    # ---- operazioni
    def compra(self, i: int, tk: str, importo: float, prezzo_base: float, uscite: Optional[Uscite] = None,
               nota: str = '') -> Optional[Posizione]:
        """Acquisto al prezzo base (prima dello slittamento) nella seduta i, con un numero intero di azioni tale che
        prezzo*azioni + commissione + Tobin <= min(importo, liquidita')."""
        if tk in self.pos:
            return None
        budget = min(importo, self.cash)
        pe = prezzo_base * (1 + self._slitt(tk, i))
        n = int(budget // pe)

        def esborso(k):
            v = k * pe
            return v + self._comm(v) + self._tobin(v, tk, i)

        while n > 0 and esborso(n) > budget + 1e-9:
            n -= 1
        if n <= 0:
            return None
        v = n * pe
        c, t = self._comm(v), self._tobin(v, tk, i)
        self.cash -= v + c + t
        self.costi['commissioni'] += c
        self.costi['tobin'] += t
        self.costi['slittamento'] += n * (pe - prezzo_base)
        pz = Posizione(tk, n, v + c + t, prezzo_base, pe, i, c, t, uscite or Uscite(), prezzo_base)
        pz.importo_ordine = float(importo)
        self.pos[tk] = pz
        return pz

    def vendi(self, i: int, tk: str, prezzo_base: float, motivo: str) -> Optional[dict]:
        """Vendita dell'intera posizione al prezzo base (prima dello slittamento)."""
        pz = self.pos.pop(tk, None)
        if pz is None:
            return None
        pe = prezzo_base * (1 - self._slitt(tk, i))
        v = pz.azioni * pe
        c = self._comm(v)
        self.cash += v - c
        self.costi['commissioni'] += c
        self.costi['slittamento'] += pz.azioni * (prezzo_base - pe)
        risultato = v - c - pz.costo_base            # vendita - acquisto - commissioni - Tobin
        tassa = 0.0 if self.config.lordo else self.fisco.realizza(risultato, self.cal[i].year)
        self.cash -= tassa
        lordo = pz.azioni * (prezzo_base - pz.prezzo_base) + pz.dividendi_lordi
        tr = dict(ticker=tk, data_ingresso=self.cal[pz.i_ingresso], data_uscita=self.cal[i],
                  sedute=i - pz.i_ingresso, azioni=pz.azioni, prezzo_ingresso=pz.prezzo_base, prezzo_uscita=prezzo_base,
                  commissioni=pz.commissione_in + c, tobin=pz.tobin_in, risultato_lordo=lordo,
                  risultato_fiscale=risultato, tassa=tassa, dividendi_netti=pz.dividendi_netti,
                  risultato_netto=risultato - tassa + pz.dividendi_netti, motivo=motivo,
                  importo_ordine=pz.importo_ordine, i_ingresso=pz.i_ingresso, i_uscita=i)
        self.trades.append(tr)
        return tr

    # ---- giornata
    def _inizio_giornata(self, i: int):
        if i > 0 and self.config.interesse_annuo:
            giorni = (self.cal[i] - self.cal[i - 1]).days
            self.cash *= (1 + self.config.interesse_annuo) ** (giorni / 365.0)
        # dividendi: solo per le posizioni gia' in portafoglio alla chiusura del giorno prima
        for tk, pz in self.pos.items():
            if pz.i_ingresso < i:
                d = self.cx.div[i, self.cx.col[tk]]
                if d > 0:
                    lordo = d * pz.azioni
                    netto = lordo * (1.0 if self.config.lordo else self.config.dividendi_netti)
                    self.cash += netto
                    pz.dividendi_lordi += lordo
                    pz.dividendi_netti += netto

    def _esegui_acquisto(self, i: int, o: Acquisto, scaduto_dopo: Optional[int]):
        tk = o.ticker
        if tk in self.pos or not self.negoziabile(tk, i):
            return False
        k = self.cx.col[tk]
        ap, mn = self.cx.ap[i, k], self.cx.mn[i, k]
        if o.limite is None:
            pb = ap
        else:
            pb = prezzo_limite_acquisto(o.limite, ap, mn)
            if pb is None:
                return False
        return self.compra(i, tk, o.importo, pb, o.uscite, o.nota) is not None

    def _controlla_uscite(self, i: int):
        for tk in list(self.pos):
            pz = self.pos[tk]
            u = pz.uscite
            if not self.negoziabile(tk, i):
                # titolo uscito dalla Borsa: chiuso all'ultimo prezzo disponibile
                k = self.cx.col[tk]
                if i > self.cx.ultima[k] >= 0 and self.cx.ultima[k] < len(self.cal) - 1:
                    self.vendi(i, tk, float(self.cx.cff[i, k]), 'fine_quotazione')
                continue
            k = self.cx.col[tk]
            ap, mx, mn = self.cx.ap[i, k], self.cx.mx[i, k], self.cx.mn[i, k]
            tp = pz.prezzo_base * (1 + u.take_profit_pct) if u.take_profit_pct is not None else None
            st = pz.prezzo_base * (1 - u.stop_pct) if u.stop_pct is not None else None
            if u.trailing_pct is not None:
                # il massimo della seduta corrente non e' noto prima del minimo: si usa il massimo fino a ieri
                tr = pz.massimo_da_ingresso * (1 - u.trailing_pct)
                st = tr if st is None else max(st, tr)
            es = esito_uscita(tp, st, ap, mx, mn)
            if es is not None:
                self.vendi(i, tk, es[1], es[0])
                continue
            if u.max_sedute is not None and i - pz.i_ingresso >= u.max_sedute:
                self.vendi(i, tk, float(ap), 'tempo')
                continue
            pz.massimo_da_ingresso = max(pz.massimo_da_ingresso, mx)

    def _chiudi_giornata(self, i: int):
        val = self.cash
        for tk, pz in self.pos.items():
            val += pz.azioni * float(self.cx.cff[i, self.cx.col[tk]])
        self.equity.append(val)
        self.date_eq.append(self.cal[i])
        self.invest.append(1.0 if self.pos else 0.0)

    # ---- ciclo
    def esegui(self, strategia: Strategia, inizio: int = 0, fine: Optional[int] = None) -> 'Risultato':
        n = len(self.cal) if fine is None else fine + 1
        ordini_pendenti: list = []
        for i in range(inizio, n):
            self._inizio_giornata(i)
            # 1) ordini decisi ieri (esecuzione oggi): vendite, poi acquisti, poi limiti ancora validi
            for o in [x for x in ordini_pendenti if isinstance(x, Vendita)]:
                if o.ticker in self.pos and self.negoziabile(o.ticker, i):
                    self.vendi(i, o.ticker, float(self.cx.ap[i, self.cx.col[o.ticker]]), o.motivo)
            nuovi = [x for x in ordini_pendenti if isinstance(x, Acquisto)]
            for o in nuovi:
                if o.limite is not None:
                    self.ordini_limite.append((o, i + o.validita - 1))
                else:
                    self._esegui_acquisto(i, o, None)
            ancora = []
            for o, scad in self.ordini_limite:
                if o.ticker in self.pos:
                    continue
                if self._esegui_acquisto(i, o, scad):
                    continue
                if i < scad:
                    ancora.append((o, scad))
            self.ordini_limite = ancora
            # 2) uscite automatiche (anche per posizioni aperte oggi all'apertura)
            self._controlla_uscite(i)
            # 3) valore a fine seduta
            self._chiudi_giornata(i)
            # 4) decisioni alla chiusura di i: ordini per i+1
            ordini_pendenti = strategia.decidi(i, self) if i < n - 1 else []
        if self.config.liquida_a_fine:
            self.liquida(n - 1)
        return Risultato(self)

    def liquida(self, i: int):
        """Vende tutto alla chiusura dell'ultima seduta (con costi e tasse) e aggiorna l'ultimo valore di patrimonio."""
        for tk in list(self.pos):
            self.vendi(i, tk, float(self.cx.cff[i, self.cx.col[tk]]), 'liquidazione_finale')
        if self.equity:
            self.equity[-1] = self.cash


# ------------------------------------------------------------------------------ KPI
class Risultato:
    def __init__(self, sim: Simulatore):
        self.sim = sim
        self.equity = pd.Series(sim.equity, index=pd.DatetimeIndex(sim.date_eq))
        self.trades = pd.DataFrame(sim.trades)

    def kpi(self, capitale: float = CAPITALE) -> dict:
        eq = self.equity
        giorni = max((eq.index[-1] - eq.index[0]).days, 1)
        fin = float(eq.iloc[-1])
        ret = eq.pct_change().dropna()
        dd = (eq / eq.cummax() - 1).min()
        t = self.trades
        out = dict(patrimonio_finale=fin, guadagno=fin - capitale, rendimento=fin / capitale - 1,
                   rendimento_annualizzato=(fin / capitale) ** (365.0 / giorni) - 1,
                   max_drawdown=float(dd),
                   sharpe=float(ret.mean() / ret.std() * np.sqrt(252)) if ret.std() > 0 else np.nan,
                   sortino=float(ret.mean() / ret[ret < 0].std() * np.sqrt(252)) if (ret < 0).sum() > 1 else np.nan,
                   n_operazioni=int(len(t)), commissioni=self.sim.costi['commissioni'], tobin=self.sim.costi['tobin'],
                   slittamento=self.sim.costi['slittamento'], tasse=self.sim.fisco.tasse_pagate,
                   esposizione=float(np.mean(self.sim.invest)))
        if len(t):
            vinc = t[t.risultato_netto > 0].risultato_netto
            perd = t[t.risultato_netto <= 0].risultato_netto
            out.update(quota_vincenti=len(vinc) / len(t),
                       guadagno_medio=float(vinc.mean()) if len(vinc) else np.nan,
                       perdita_media=float(perd.mean()) if len(perd) else np.nan,
                       durata_media_sedute=float(t.sedute.mean()))
        return out
