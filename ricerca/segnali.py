"""Calcolo delle variabili (segnali) del piano, per ogni titolo e seduta, con i soli dati disponibili fino a quella seduta.

Convenzioni (vedi anche RIASSUNTO_FASE3.md):
  * Una raccomandazione datata t diventa utilizzabile nei segnali calcolati alla chiusura della prima seduta
    STRICTAMENTE successiva a t (RITARDO=1, scelta prudente). Con RITARDO=0 e' utilizzabile dalla chiusura della
    prima seduta >= t. In entrambi i casi gli ordini partono dalla seduta dopo il segnale.
  * TP medio: per ogni emittente l'ultimo target disponibile con eta' <= 120 giorni (come costruisci.py); media semplice.
  * Universo del giorno D: titoli con almeno 5 righe di target (valide) con data nei 120 giorni precedenti D
    (tra quelle gia' utilizzabili) e prezzo di chiusura in D.
  * Giorni di calendario per le finestre in "giorni", sedute per quelle in "sedute".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import dati as D

RITARDO = 1
MIN_TARGET_UNIVERSO = 5
MIN_N_TP_RIFERIMENTO = 3    # revisione del consenso: il TP medio "di partenza" deve avere almeno 3 emittenti
CLASSI_POSITIVE = ('Buy', 'Overweight')

EVENTI = {
    'verso_buy': 'Passaggio di un emittente a classe Buy',
    'alzata_5': 'Target alzato >= 5% da un emittente',
    'alzata_10': 'Target alzato >= 10% da un emittente',
    'alzata_20': 'Target alzato >= 20% da un emittente',
    'due_alzate_5g': '>= 2 emittenti con target alzato negli ultimi 5 giorni (primo giorno)',
    'due_alzate_10g': '>= 2 emittenti con target alzato negli ultimi 10 giorni (primo giorno)',
}


@dataclass
class Segnali:
    calendario: pd.DatetimeIndex
    universo: pd.DataFrame                   # bool, seduta x titolo
    variabili: dict = field(default_factory=dict)   # nome -> DataFrame seduta x titolo
    eventi: dict = field(default_factory=dict)      # nome -> DataFrame bool
    regime: pd.Series | None = None          # 1 FTSE MIB sopra media 200 sedute, 0 sotto, NaN se non calcolabile
    consenso: dict = field(default_factory=dict)    # tp, n_tp, std_tp, n_righe (pannelli intermedi)


# ----------------------------------------------------------------------------------------- disponibilita'
def indice_disponibilita(cal: pd.DatetimeIndex, date: pd.Series, ritardo: int) -> np.ndarray:
    """Posizione (nel calendario) della prima seduta in cui una raccomandazione con data `date` e' utilizzabile."""
    lato = 'left' if ritardo == 0 else 'right'
    return np.searchsorted(cal.values, date.values.astype('datetime64[ns]'), side=lato)


def _tieni(stato: dict, chiave, riga):
    """Aggiorna lo stato 'ultima riga per emittente': vince la data piu' recente, a parita' la riga piu' in alto nel file."""
    corr = stato.get(chiave)
    if corr is None or (riga[0], -riga[1]) > (corr[0], -corr[1]):
        stato[chiave] = riga


def _serie_titolo(cal, rac_t, ritardo):
    """Serie giornaliere di consenso e conteggi per un titolo. rac_t: righe valide del titolo."""
    n = len(cal)
    out = {k: np.full(n, np.nan) for k in ('tp', 'n_tp', 'std_tp', 'n_righe', 'quota_pos', 'n_class')}
    if rac_t.empty:
        return out, [], []
    rac_t = rac_t.copy()
    rac_t['pos'] = indice_disponibilita(cal, rac_t.data, ritardo)
    rac_t = rac_t[rac_t.pos < n]
    if rac_t.empty:
        return out, [], []
    # righe con target / righe con classe, raggruppate per posizione di disponibilita'
    tg = rac_t[rac_t.target.notna()]
    cl = rac_t[rac_t.classe.notna()]
    tg_per_pos = {p: g for p, g in tg.groupby('pos')}
    cl_per_pos = {p: g for p, g in cl.groupby('pos')}
    stato_t, stato_c, date_righe = {}, {}, []
    date_cal = cal.values
    primo = int(min(rac_t.pos.min(), n - 1))
    for i in range(primo, n):
        d = cal[i]
        if i in tg_per_pos:
            for r in tg_per_pos[i].itertuples():
                _tieni(stato_t, r.emittente, (r.data, r.ordine, r.target))
                date_righe.append(r.data)
        if i in cl_per_pos:
            for r in cl_per_pos[i].itertuples():
                _tieni(stato_c, r.emittente, (r.data, r.ordine, r.classe))
        validi = [v[2] for v in stato_t.values() if (d - v[0]).days <= D.VALIDITA_TP]
        if validi:
            out['tp'][i] = float(np.mean(validi))
            out['n_tp'][i] = len(validi)
            out['std_tp'][i] = float(np.std(validi, ddof=1)) if len(validi) > 1 else np.nan
        out['n_righe'][i] = sum(1 for x in date_righe if 0 <= (d - x).days <= D.VALIDITA_TP)
        rec = [v[2] for v in stato_c.values() if (d - v[0]).days <= D.FINESTRA_CONTEGGIO]
        if rec:
            out['n_class'][i] = len(rec)
            out['quota_pos'][i] = sum(1 for c in rec if c in CLASSI_POSITIVE) / len(rec)
    return out, tg, cl


def _eventi_titolo(cal, rac_t, ritardo):
    """Revisioni di target e passaggi di classe di un titolo, con posizione di disponibilita'.
    Ritorna dict con DataFrame: 'rev' (pos, data, emittente, pct) per le variazioni di target (su/giu),
    'verso_buy' (pos, data, emittente)."""
    n = len(cal)
    rev = rac_t[rac_t.variazione.isin(['su', 'giu'])].copy()
    rev['pos'] = indice_disponibilita(cal, rev.data, ritardo)
    rev['pct'] = rev.target / rev.target_prec - 1
    rev = rev[rev.pos < n][['pos', 'data', 'emittente', 'pct']]
    # passaggi di classe: sequenza dei giudizi classificati di ciascun emittente
    cl = rac_t[rac_t.classe.notna()].sort_values(['emittente', 'data', 'ordine'], ascending=[True, True, False], kind='stable')
    cl = cl.assign(classe_prec=cl.groupby('emittente').classe.shift(1))
    vb = cl[(cl.classe == 'Buy') & cl.classe_prec.notna() & (cl.classe_prec != 'Buy')].copy()
    vb['pos'] = indice_disponibilita(cal, vb.data, ritardo)
    vb = vb[vb.pos < n][['pos', 'data', 'emittente']]
    return rev, vb



def _finestre_revisioni(cal, rev, j, saldo, ev):
    """Riempie, per il titolo di colonna j, i conteggi di rialzi/ribassi del target negli ultimi 30 e 60 giorni
    e i fronti di salita dei gruppi di >= 2 rialzi (emittenti distinti) in 5 e 10 giorni."""
    n = len(cal)
    pos = rev.pos.to_numpy()
    dat = rev.data.to_numpy().astype('datetime64[ns]')
    pct = rev.pct.to_numpy()
    emi = pd.factorize(rev.emittente)[0]
    cald = cal.values.astype('datetime64[ns]')
    su = pct > 1e-9
    giu = pct < -1e-9
    prec = {5: 0, 10: 0}
    for i in range(int(pos.min()), n):
        vis = pos <= i
        eta = (cald[i] - dat) / np.timedelta64(1, 'D')
        for w in (30, 60):
            m = vis & (eta <= w)
            saldo[f'su_{w}'].iat[i, j] = (su & m).sum()
            saldo[f'giu_{w}'].iat[i, j] = (giu & m).sum()
        for w, nome in ((5, 'due_alzate_5g'), (10, 'due_alzate_10g')):
            ne = len(set(emi[su & vis & (eta <= w)]))
            if ne >= 2 and prec[w] < 2:
                ev[nome].iat[i, j] = True
            prec[w] = ne



def ritardato(df: pd.DataFrame, cal: pd.DatetimeIndex, giorni: int, minimo_n=None) -> pd.DataFrame:
    """Valore di `df` all'ultima seduta <= (data - giorni). Se minimo_n=(pannello_n, soglia), NaN dove n < soglia."""
    n = len(cal)
    j = np.searchsorted(cal.values, (cal - pd.Timedelta(days=giorni)).values, side='right') - 1
    ok = j >= 0
    jj = np.clip(j, 0, n - 1)
    vals = df.values[jj].astype(float)
    if minimo_n is not None:
        pn, soglia = minimo_n
        vals = np.where(pn.values[jj] >= soglia, vals, np.nan)
    vals[~ok, :] = np.nan
    return pd.DataFrame(vals, index=df.index, columns=df.columns)

# ----------------------------------------------------------------------------------------- calcolo completo
def calcola_segnali(prezzi: D.Prezzi, rac: pd.DataFrame, anagrafica: pd.DataFrame, indice: pd.DataFrame,
                    ritardo: int = RITARDO) -> Segnali:
    cal = prezzi.calendario
    n = len(cal)
    tickers = prezzi.tickers
    cff = prezzi.chiusura_ff()
    pan = lambda: pd.DataFrame(np.nan, index=cal, columns=tickers)

    P = {k: pan() for k in ('tp', 'n_tp', 'std_tp', 'n_righe', 'quota_pos', 'n_class')}
    ev = {k: pd.DataFrame(False, index=cal, columns=tickers) for k in EVENTI}
    saldo = {k: pan() for k in ('su_30', 'giu_30', 'su_60', 'giu_60')}

    rac = rac[rac.ticker.isin(tickers)]
    for tk, rt in rac.groupby('ticker'):
        serie, _, _ = _serie_titolo(cal, rt, ritardo)
        for k in P:
            P[k][tk] = serie[k]
        rev, vb = _eventi_titolo(cal, rt, ritardo)
        # eventi puntuali (nel giorno di disponibilita')
        for p in vb.pos.unique():
            ev['verso_buy'].iloc[int(p), ev['verso_buy'].columns.get_loc(tk)] = True
        su = rev[rev.pct > 1e-9]
        j = ev['alzata_5'].columns.get_loc(tk)
        for soglia, nome in ((0.05, 'alzata_5'), (0.10, 'alzata_10'), (0.20, 'alzata_20')):
            for p in su[su.pct >= soglia - 1e-12].pos.unique():
                ev[nome].iloc[int(p), j] = True
        # finestre mobili su revisioni (giorni di calendario), conteggio di emittenti distinti
        if len(rev):
            _finestre_revisioni(cal, rev, j, saldo, ev)

    # universo del giorno
    chiusura_oggi = prezzi.chiusura
    universo = (P['n_righe'] >= MIN_TARGET_UNIVERSO) & chiusura_oggi.notna() & P['tp'].notna()

    # variabili
    V = {}
    prezzo = chiusura_oggi
    V['potenziale'] = P['tp'] / prezzo - 1                                   # 1
    for k in (30, 60, 90):                                                   # 2 revisione consenso
        rif = ritardato(P['tp'], cal, k, minimo_n=(P['n_tp'], MIN_N_TP_RIFERIMENTO))
        V[f'rev_tp_{k}'] = P['tp'] / rif - 1
    for w in (30, 60):                                                       # 3 saldo revisioni
        s = (saldo[f'su_{w}'] - saldo[f'giu_{w}'])
        s = s.where(P['n_tp'].notna())
        # i conteggi sono NaN dove non c'e' alcuna revisione: sono 0 per i titoli con consenso
        s = s.fillna(0).where(P['n_tp'].notna())
        V[f'saldo_rev_{w}'] = s
        V[f'saldo_rev_{w}_norm'] = s / P['n_tp']
    V['quota_positivi'] = P['quota_pos']                                     # 4
    V['delta_quota_positivi_60'] = P['quota_pos'] - ritardato(P['quota_pos'], cal, 60)
    V['n_target'] = P['n_tp']                                                # 6
    V['dispersione_target'] = P['std_tp'] / P['tp']
    V['dist_tp_meno10'] = prezzo / (P['tp'] / 1.1) - 1                       # 7
    for k in (20, 60, 120):                                                  # 8 momentum
        V[f'momentum_{k}'] = cff / cff.shift(k) - 1
    H = prezzi.massimo.where(prezzi.massimo.notna(), cff)                    # 9 ritracciamento
    V['ritracciamento_60'] = cff / H.rolling(60, min_periods=60).max() - 1
    L = prezzi.minimo.where(prezzi.minimo.notna(), cff)                      # 10 ATR%
    pc = cff.shift(1)
    tr = np.maximum(H - L, np.maximum((H - pc).abs(), (L - pc).abs()))
    V['atr_14_pct'] = tr.rolling(14, min_periods=14).mean() / cff
    azioni = anagrafica.reindex(tickers).azioni_circolazione.astype(float)   # 11 capitalizzazione
    V['capitalizzazione_mld'] = cff.mul(azioni, axis=1) / 1e9
    # tutte le variabili solo dove il titolo e' nell'universo e ha il prezzo del giorno
    for k in V:
        V[k] = V[k].where(universo)
    # 12 regime
    ic = indice.chiusura.reindex(cal)
    sma = ic.rolling(200, min_periods=200).mean()
    regime = (ic > sma).astype(float).where(sma.notna())
    return Segnali(cal, universo, V, {k: v for k, v in ev.items()}, regime, P)


# ----------------------------------------------------------------------------------------- rendimenti futuri
def dividendi_pannello(prezzi: D.Prezzi, dividendi: pd.DataFrame) -> pd.DataFrame:
    """Dividendo lordo per azione per stacco, seduta x titolo (0 altrove). Gli stacchi in giorni senza seduta
    dell'indice vanno alla seduta successiva."""
    pan = pd.DataFrame(0.0, index=prezzi.calendario, columns=prezzi.tickers)
    cal = prezzi.calendario
    for r in dividendi.itertuples():
        if r.ticker not in pan.columns:
            continue
        i = int(np.searchsorted(cal.values, np.datetime64(r.data), side='left'))
        if i < len(cal):
            pan.iat[i, pan.columns.get_loc(r.ticker)] += r.dividendo
    return pan


def rendimenti_futuri(prezzi: D.Prezzi, div_pan: pd.DataFrame, orizzonti=(5, 20, 60)) -> dict:
    """Rendimento (lordo di tasse, con dividendi lordi incassati) di un acquisto all'apertura della seduta t+1,
    venduto alla chiusura della seduta t+h. NaN se non negoziabile in t+1 o se t+h supera l'ultima seduta
    disponibile (DATA_FINE). Dividendi: stacco nelle sedute [t+2, t+h]."""
    cal = prezzi.calendario
    n = len(cal)
    cff = prezzi.chiusura_ff()
    ap_ok = prezzi.apertura.where(prezzi.negoziabile())
    ap_next = ap_ok.shift(-1)
    cum = div_pan.cumsum()
    out = {}
    for h in orizzonti:
        fine = cff.shift(-h)
        dsum = cum.shift(-h) - cum.shift(-1)
        r = (fine + dsum) / ap_next - 1
        r.iloc[n - h:, :] = np.nan        # finestra oltre l'ultima seduta
        out[h] = r
    return out
