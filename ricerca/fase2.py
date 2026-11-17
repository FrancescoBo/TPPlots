"""Fase 2: buy-and-hold FTSE MIB e top-5 potenziale al 2025-09-01 (dati fino al 2026-04-30)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # il flag -I toglie la cartella dello script
import dati as D
import motore as M
import segnali as S
import strategie as ST

OUT = Path(__file__).resolve().parent / 'risultati'


def ftsemib_bh(ix, i0, i1, capitale=M.CAPITALE, lordo=False, dividendi_stima=0.0):
    """Un unico ordine sull'indice (come ETF/future ideale): apertura di i0, chiusura di i1, costi del piano,
    senza Tobin (ETF), slittamento 0,05%. Il FTSE MIB e' un indice di prezzo (niente dividendi)."""
    p0 = float(ix.apertura.iloc[i0]); p1 = float(ix.chiusura.iloc[i1])
    if lordo:
        return capitale * (p1 / p0 - 1 + dividendi_stima)
    # quote frazionarie (l'indice vale ~42.000 punti: un ETF/future equivalente consente l'importo intero)
    pe = p0 * (1 + M.SLITT_GRANDE)
    v0 = (capitale - M.COMM_FISSA + M.COMM_PERC * M.COMM_SOGLIA) / (1 + M.COMM_PERC)   # v0 + commissione(v0) = capitale
    n = v0 / pe
    c0 = M.commissione(v0)
    ps = p1 * (1 - M.SLITT_GRANDE)
    v1 = n * ps
    c1 = M.commissione(v1)
    ris = v1 - c1 - (v0 + c0)
    fisco = M.RegistroFiscale()
    tassa = fisco.realizza(ris, ix.index[i1].year)
    cash = capitale - v0 - c0 + v1 - c1 - tassa
    return dict(patrimonio_finale=cash, rendimento=cash / capitale - 1, azioni=n, commissioni=c0 + c1, tassa=tassa)


def main():
    pr = D.carica_prezzi()
    rac, esc = D.carica_raccomandazioni(pr)
    an = D.carica_anagrafica(); ix = D.carica_indice()
    sg = S.calcola_segnali(pr, rac, an, ix)
    div = D.carica_dividendi()
    dpan = S.dividendi_pannello(pr, div)
    esenti = D.carica_tobin_esenti()
    cal = pr.calendario
    cff = pr.chiusura_ff()
    cap = cff.mul(an.reindex(pr.tickers).azioni_circolazione.astype(float), axis=1) / 1e9
    i0 = int(cal.searchsorted(D.INIZIO_SCELTA)); i1 = len(cal) - 1
    assert cal[i0] == D.INIZIO_SCELTA and cal[i1] == D.DATA_FINE
    idec = i0 - 1
    res = {'ingresso': str(cal[i0].date()), 'uscita': str(cal[i1].date()), 'ultimo_dato_usato': str(D.DATA_FINE.date())}

    # --- FTSE MIB
    pot = sg.variabili['potenziale'].iloc[idec].dropna()
    pot = pot[[t for t in pot.index if pr.negoziabile().iat[i0, pr.tickers.index(t)]]]
    top5 = list(pot.sort_values(ascending=False).index[:5])
    res['top5'] = {t: float(pot[t]) for t in top5}
    res['universo_al_29ago'] = int(sg.universo.iloc[idec].sum())
    res['ftsemib_lordo_prezzo'] = float(ix.chiusura.iloc[i1] / ix.apertura.iloc[i0] - 1)
    f = ftsemib_bh(ix, i0, i1)
    res['ftsemib_netto'] = f
    # stima dividendi indice: dividendi lordi dei componenti ~ non disponibile; stima prudente con i top-40 per cap
    cap0 = cap.iloc[idec].dropna().sort_values(ascending=False)
    comp = list(cap0.index[:40])
    w = cap0[comp] / cap0[comp].sum()
    dsum = dpan.iloc[i0 + 1:i1 + 1][comp].sum() / pr.apertura.iloc[i0][comp]
    res['ftsemib_dividendi_stimati_pct'] = float((w * dsum.fillna(0)).sum())

    def sim(cfg):
        return M.Simulatore(pr, dpan, cap, esenti, cfg)

    for nome, cfg in (('lordo', M.Config(lordo=True)), ('netto', M.Config()), ('netto_tobin_2026', M.Config(tobin_dal_2026=0.002))):
        r = sim(cfg).esegui(ST.BuyAndHold(top5, 4000, i0), inizio=idec, fine=i1)
        res['top5_' + nome] = {k: v for k, v in r.kpi().items() if not (isinstance(v, float) and np.isnan(v))}
        if nome == 'netto':
            r.trades.to_csv(OUT / 'fase2_top5_operazioni.csv', index=False)
    # --- casuali: 5 titoli a caso dall'universo al 29 ago, 500 repliche (stesso calendario, stessi importi)
    amm = sg.universo.copy()
    kp = ST.ripeti_casuale(lambda: sim(M.Config()), {idec: 5}, amm, 4000, M.Uscite(), idec, i1)
    rend = np.array([k['rendimento'] for k in kp])
    res['casuali_n'] = len(rend)
    res['casuali_media'] = float(rend.mean()); res['casuali_mediana'] = float(np.median(rend))
    res['casuali_p5_p95'] = [float(np.percentile(rend, 5)), float(np.percentile(rend, 95))]
    rt = res['top5_netto']['rendimento']
    res['top5_percentile_tra_casuali'] = float((rend < rt).mean())
    json.dump(res, open(OUT / 'fase2.json', 'w'), indent=1, ensure_ascii=False)
    pd.Series(rend).to_csv(OUT / 'fase2_casuali_rendimenti.csv', index=False, header=['rendimento_netto'])
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
