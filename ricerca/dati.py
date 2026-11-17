"""Caricamento e normalizzazione dei dati per la ricerca.

REGOLA FONDAMENTALE: nessun dato oltre DATA_FINE (fine del periodo in-sample, 2026-04-30)
esce da questo modulo. Ogni funzione taglia i dati alla data `fine` appena li legge.

Normalizzazione di emittenti, classi e raggruppamenti: si usa scripts/costruisci.carica()
(non modificato), poi si taglia alla data di fine.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

QUI = Path(__file__).resolve().parent
RADICE = QUI.parent
for p in (str(RADICE / 'scripts'), str(QUI)):
    if p not in sys.path:
        sys.path.insert(0, p)

import costruisci  # noqa: E402  (scripts/costruisci.py, non modificato)

DATA_FINE = pd.Timestamp('2026-04-30')          # ultimo giorno utilizzabile (fine in-sample)
INIZIO_RISCALDAMENTO = pd.Timestamp('2025-01-02')
INIZIO_SCELTA = pd.Timestamp('2025-09-01')       # primo giorno del periodo di scelta
RATIO_MIN, RATIO_MAX = 0.3, 3.0                  # target/prezzo ammesso
VALIDITA_TP = costruisci.VALIDITA_TP             # 120 giorni
FINESTRA_CONTEGGIO = costruisci.FINESTRA_CONTEGGIO  # 365 giorni
PREZZI = RADICE / 'data/ricerca/prezzi'
RICERCA = RADICE / 'data/ricerca'


# ------------------------------------------------------------------ calendario e prezzi
def carica_indice(fine: pd.Timestamp = DATA_FINE) -> pd.DataFrame:
    ix = pd.read_csv(RICERCA / 'indice_ftsemib.csv', parse_dates=['data'])
    ix = ix[ix.data <= fine].sort_values('data').drop_duplicates('data').set_index('data')
    return ix


@dataclass
class Prezzi:
    calendario: pd.DatetimeIndex
    apertura: pd.DataFrame
    massimo: pd.DataFrame
    minimo: pd.DataFrame
    chiusura: pd.DataFrame      # NaN nei giorni senza riga di prezzo
    volume: pd.DataFrame
    righe_fuori_calendario: dict   # ticker -> date con prezzo ma senza seduta dell'indice (scartate)
    senza_dati: list               # ticker di titoli.csv senza righe fino a `fine`

    @property
    def tickers(self):
        return list(self.chiusura.columns)

    def chiusura_ff(self) -> pd.DataFrame:
        """Chiusura con riporto in avanti dell'ultimo prezzo (solo per calcoli, non per eseguire)."""
        return self.chiusura.ffill()

    def negoziabile(self) -> pd.DataFrame:
        """True se nella seduta c'e' prezzo e volume > 0 (altrimenti: nessun ordine eseguito)."""
        return self.chiusura.notna() & (self.volume > 0) & self.apertura.notna()


def carica_prezzi(fine: pd.Timestamp = DATA_FINE) -> Prezzi:
    cal = pd.DatetimeIndex(carica_indice(fine).index)
    colonne = {k: {} for k in ('apertura', 'massimo', 'minimo', 'chiusura', 'volume')}
    fuori, senza = {}, []
    anagrafica = pd.read_csv(RADICE / 'config/titoli.csv', dtype={'azioni_circolazione': 'Int64'})
    for tk in anagrafica.ticker:
        f = PREZZI / f'{tk}.csv'
        if not f.exists():
            senza.append(tk)
            continue
        d = pd.read_csv(f, parse_dates=['data'])
        d = d[d.data <= fine].drop_duplicates('data', keep='last').set_index('data')
        if d.empty:
            senza.append(tk)
            continue
        extra = d.index.difference(cal)
        if len(extra):
            fuori[tk] = [x.date().isoformat() for x in extra]
            d = d.loc[d.index.intersection(cal)]
        for k in colonne:
            colonne[k][tk] = d[k].reindex(cal)
    frames = {k: pd.DataFrame(v, index=cal) for k, v in colonne.items()}
    return Prezzi(cal, frames['apertura'], frames['massimo'], frames['minimo'], frames['chiusura'],
                  frames['volume'], fuori, senza)


def carica_dividendi(fine: pd.Timestamp = DATA_FINE) -> pd.DataFrame:
    d = pd.read_csv(RICERCA / 'dividendi.csv', parse_dates=['data'])
    return d[d.data <= fine].sort_values(['ticker', 'data']).reset_index(drop=True)


def carica_frazionamenti_yahoo(fine: pd.Timestamp = DATA_FINE) -> pd.DataFrame:
    d = pd.read_csv(RICERCA / 'frazionamenti.csv', parse_dates=['data'])
    return d[d.data <= fine].reset_index(drop=True)


def carica_anagrafica() -> pd.DataFrame:
    t = pd.read_csv(RADICE / 'config/titoli.csv', dtype={'azioni_circolazione': 'Int64', 'attivo': str})
    t['azioni_circolazione'] = t.azioni_circolazione.astype('float')
    return t.set_index('ticker')


# ------------------------------------------------------------------ raccomandazioni
def carica_raccomandazioni(prezzi: Prezzi, fine: pd.Timestamp = DATA_FINE):
    """Raccomandazioni normalizzate come costruisci.py, tagliate a `fine`.

    Aggiunge:
      ordine      posizione nel file (il file e' dal piu' recente: a parita' di data vince la riga con ordine minore)
      prezzo_rif  ultima chiusura <= data della raccomandazione (se manca, prima chiusura successiva)
      ratio       target / prezzo_rif
      escluso     True se ratio fuori da [0,3 ; 3]
    Ritorna (rac, esclusi) dove `rac` contiene SOLO le righe valide (targets con ratio ammesso e righe senza target)
    e `esclusi` le righe scartate per ratio, da segnalare.
    """
    _, rac = costruisci.carica(fine)
    rac = rac[rac.data <= fine].copy()
    rac['ordine'] = np.arange(len(rac))
    rac = rac.drop(columns=['target_prec', 'variazione'])          # si ricalcolano dopo le esclusioni
    cf = prezzi.chiusura
    prezzo_rif = []
    for tk, d in zip(rac.ticker, rac.data):
        if tk not in cf.columns:
            prezzo_rif.append(np.nan)
            continue
        s = cf[tk].dropna()
        prima = s[:d]
        prezzo_rif.append(prima.iloc[-1] if len(prima) else (s.iloc[0] if len(s) else np.nan))
    rac['prezzo_rif'] = prezzo_rif
    rac['ratio'] = (rac.target / rac.prezzo_rif).round(9)   # evita che 3,0000000000000004 risulti fuori da [0,3 ; 3]
    rac['escluso'] = rac.ratio.notna() & ((rac.ratio < RATIO_MIN) | (rac.ratio > RATIO_MAX))
    esclusi = rac[rac.escluso].copy()
    rac = rac[~rac.escluso].copy()
    rac = ricalcola_variazioni(rac)
    return rac.reset_index(drop=True), esclusi.reset_index(drop=True)


def ricalcola_variazioni(rac: pd.DataFrame) -> pd.DataFrame:
    """Stessa logica di costruisci.carica(): confronto col target precedente dello stesso emittente sullo stesso titolo.
    (su / giu / invariato / primo). Ordinamento: ticker, emittente, data crescente; a parita' di data
    le righe piu' basse del file sono le piu' recenti."""
    r = rac.copy()
    r = r.sort_values(['ticker', 'emittente', 'data', 'ordine'], ascending=[True, True, True, False], kind='stable')
    r['target_prec'] = r.dropna(subset=['target']).groupby(['ticker', 'emittente']).target.shift(1)

    def var(x):
        if pd.isna(x.target):
            return None
        if pd.isna(x.target_prec):
            return 'primo'
        if abs(x.target - x.target_prec) < 1e-9 * max(1, abs(x.target)):
            return 'invariato'
        return 'su' if x.target > x.target_prec else 'giu'

    r['variazione'] = r.apply(var, axis=1)
    return r.sort_values('ordine')


# ------------------------------------------------------------------ Tobin
def carica_tobin_esenti(percorso: Path | None = None) -> dict:
    """ticker -> lista di (valido_dal, valido_al). Se il file non c'e', nessuna esenzione."""
    percorso = percorso or (QUI / 'tobin_esenti.csv')
    if not Path(percorso).exists():
        return {}
    d = pd.read_csv(percorso, parse_dates=['valido_dal', 'valido_al'])
    out = {}
    for r in d.itertuples():
        dal = r.valido_dal if pd.notna(r.valido_dal) else pd.Timestamp.min
        al = r.valido_al if pd.notna(r.valido_al) else pd.Timestamp.max
        out.setdefault(r.ticker, []).append((dal, al))
    return out
