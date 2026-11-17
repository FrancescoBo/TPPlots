"""Fase 3: potere predittivo dei segnali sui rendimenti futuri (solo in-sample 2025-09-01 .. 2026-04-30).

Rendimento futuro: acquisto all'apertura di t+1, chiusura di t+h, piu' dividendi lordi; NaN oltre il 2026-04-30.
Nessuna strategia: solo statistiche descrittive dei segnali."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # il flag -I toglie la cartella dello script
import dati as D
import segnali as S

OUT = Path(__file__).resolve().parent / 'risultati'
ORIZZONTI = (5, 20, 60)
MIN_TITOLI = 20          # minimo di titoli con segnale e rendimento in un giorno per usarlo
MIN_GIORNI_MESE = 5      # minimo di giorni validi per contare un mese


def _mesi(serie: pd.Series, minimo=MIN_GIORNI_MESE):
    s = serie.dropna()
    g = s.groupby(s.index.to_period('M'))
    return g.mean()[g.count() >= minimo]


def stabilita(serie_giornaliera: pd.Series):
    """media, t-stat sui valori mensili, quota di mesi con lo stesso segno della media, n mesi."""
    m = _mesi(serie_giornaliera)
    if len(m) < 2:
        return np.nan, np.nan, np.nan, len(m)
    media = serie_giornaliera.dropna().mean()
    t = m.mean() / (m.std(ddof=1) / np.sqrt(len(m))) if m.std(ddof=1) > 0 else np.nan
    quota = float((np.sign(m) == np.sign(media)).mean()) if media != 0 else np.nan
    return float(media), float(t), quota, len(m)


def analisi_continua(V: pd.DataFrame, R: pd.DataFrame, giorni):
    x = V.loc[giorni].where(R.loc[giorni].notna())
    y = R.loc[giorni].where(V.loc[giorni].notna())
    n = x.notna().sum(axis=1)
    ok = n >= MIN_TITOLI
    x, y, n = x[ok], y[ok], n[ok]
    xr, yr = x.rank(axis=1), y.rank(axis=1)
    ic = xr.corrwith(yr, axis=1)
    # quintili per giorno (ranghi medi in caso di parita')
    q = np.ceil(5 * xr.values / n.values[:, None]).clip(1, 5)
    q[np.isnan(xr.values)] = np.nan
    yv = y.values
    medie = np.full((len(x), 5), np.nan); mediane = np.full((len(x), 5), np.nan)
    for k in range(5):
        mk = (q == k + 1)
        cnt = mk.sum(axis=1)
        with np.errstate(invalid='ignore', divide='ignore'):
            medie[:, k] = np.where(cnt > 0, np.nansum(np.where(mk, yv, 0), axis=1) / cnt, np.nan)
        for d in range(len(x)):
            if cnt[d]:
                mediane[d, k] = np.median(yv[d][mk[d]])
    return ic, medie, mediane, n


def analisi_eventi(E: pd.DataFrame, R: pd.DataFrame, universo: pd.DataFrame, giorni):
    Rn = R.loc[giorni].where(universo.loc[giorni])
    media_univ = Rn.mean(axis=1)
    ev = E.loc[giorni] & Rn.notna()
    rend_ev = Rn.where(ev).mean(axis=1)              # media dei titoli con evento, per giorno
    eccesso = (rend_ev - media_univ)[ev.any(axis=1)]
    n_ev = int(ev.values.sum())
    titoli = int(ev.any(axis=0).sum())
    ass = float(Rn.where(ev).stack().mean()) if n_ev else np.nan
    return eccesso, n_ev, titoli, ass, int(ev.any(axis=1).sum())


def esegui(ritardo=S.RITARDO, completo=True):
    pr = D.carica_prezzi()
    rac, esc = D.carica_raccomandazioni(pr)
    an = D.carica_anagrafica(); ix = D.carica_indice()
    sg = S.calcola_segnali(pr, rac, an, ix, ritardo=ritardo)
    dpan = S.dividendi_pannello(pr, D.carica_dividendi())
    fut = S.rendimenti_futuri(pr, dpan, ORIZZONTI)
    cal = pr.calendario
    giorni = cal[(cal >= D.INIZIO_SCELTA) & (cal <= D.DATA_FINE)]
    righe = []
    for nome, V in sg.variabili.items():
        for h in ORIZZONTI:
            R = fut[h].where(sg.universo)
            ic, med, mdn, n = analisi_continua(V, R, giorni)
            m, t, quota, nm = stabilita(ic)
            r = dict(variabile=nome, orizzonte=h, n_giorni=int(ic.notna().sum()), n_titoli_medio=float(n.mean()),
                     ic_medio=m, ic_t_mensile=t, n_mesi=nm, quota_mesi_stesso_segno=quota)
            qm = np.nanmean(med, axis=0)
            for k in range(5):
                r[f'q{k+1}'] = float(qm[k])
            r['q5_meno_q1'] = float(qm[4] - qm[0])
            qd = np.nanmean(mdn, axis=0)
            r['q5_meno_q1_mediana'] = float(qd[4] - qd[0])
            righe.append(r)
    seg = pd.DataFrame(righe)
    if not completo:
        return seg, sg, None
    ev_rows = []
    for nome, E in sg.eventi.items():
        for h in ORIZZONTI:
            ecc, n_ev, tit, ass, ng = analisi_eventi(E, fut[h], sg.universo, giorni)
            m, t, quota, nm = stabilita(ecc)
            ev_rows.append(dict(evento=nome, orizzonte=h, n_eventi=n_ev, n_titoli=tit, n_giorni_con_evento=ng,
                                rendimento_medio_eventi=ass, eccesso_medio_vs_universo=m, t_mensile=t, n_mesi=nm,
                                quota_mesi_stesso_segno=quota, eccesso_mediano_giornaliero=float(ecc.median()) if len(ecc) else np.nan))
    evd = pd.DataFrame(ev_rows)
    # regime (serie storica di mercato)
    reg = []
    for h in ORIZZONTI:
        Rn = fut[h].where(sg.universo).loc[giorni].mean(axis=1)
        g = sg.regime.loc[giorni]
        for v, lab in ((1, 'sopra_media200'), (0, 'sotto_media200')):
            s = Rn[(g == v)].dropna()
            reg.append(dict(variabile='regime_mercato', orizzonte=h, stato=lab, n_giorni=len(s),
                            rendimento_medio_universo=float(s.mean()) if len(s) else np.nan))
    return seg, sg, (evd, pd.DataFrame(reg), pr, rac, esc)


def main():
    seg, sg, extra = esegui()
    evd, reg, pr, rac, esc = extra
    seg0, _, _ = esegui(ritardo=0, completo=False)
    seg = seg.merge(seg0[['variabile', 'orizzonte', 'ic_medio']].rename(columns={'ic_medio': 'ic_medio_ritardo0'}),
                    on=['variabile', 'orizzonte'])
    seg.to_csv(OUT / 'fase3_segnali.csv', index=False)
    evd.to_csv(OUT / 'fase3_eventi.csv', index=False)
    reg.to_csv(OUT / 'fase3_regime.csv', index=False)
    n_comb = len(seg) + len(evd) + len(reg)
    print('combinazioni (variabile x orizzonte, + eventi, + regime):', len(seg), len(evd), len(reg), n_comb)
    json.dump(dict(combinazioni_segnali=len(seg), combinazioni_eventi=len(evd), combinazioni_regime=len(reg),
                   combinazioni_con_ritardo0=len(seg) * 2 + len(evd) + len(reg)),
              open(OUT / 'fase3_conteggi.json', 'w'))


if __name__ == '__main__':
    main()
