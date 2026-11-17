"""Rapporto sui problemi dei dati (fino al 2026-04-30) e correlazioni tra segnali. Scrive risultati/qualita.json e fase3_correlazioni.csv."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dati as D
import segnali as S

OUT = Path(__file__).resolve().parent / 'risultati'


def main():
    pr = D.carica_prezzi(); rac, esc = D.carica_raccomandazioni(pr)
    an = D.carica_anagrafica(); ix = D.carica_indice()
    sg = S.calcola_segnali(pr, rac, an, ix)
    q = {}
    q['ultimo_dato'] = str(D.DATA_FINE.date())
    q['target_fuori_0.3_3'] = esc[['ticker', 'data', 'emittente', 'target', 'prezzo_rif', 'ratio']].assign(
        data=lambda d: d.data.dt.strftime('%Y-%m-%d')).round(3).to_dict('records')
    q['titoli_senza_prezzi'] = list(pr.senza_dati)
    q['righe_prezzo_fuori_calendario'] = {k: [str(pd.Timestamp(x).date()) for x in v] for k, v in pr.righe_fuori_calendario.items()}
    az = an.azioni_circolazione
    q['titoli_con_prezzi_senza_azioni'] = int(az.reindex(pr.tickers).isna().sum())
    q['titoli_con_prezzi'] = len(pr.tickers)
    cf = pr.chiusura
    r1 = cf.ffill().pct_change(fill_method=None)
    est = r1.abs().stack()
    est = est[est > 0.4]
    q['rendimenti_giornalieri_oltre_40pct'] = [dict(ticker=a, data=str(d.date()), rend=round(float(r1.loc[d, a]), 3)) for (d, a), v in est.items()]
    allrec = rac
    q['righe_rac_valide'] = len(rac)
    q['righe_rac_duplicate_ticker_data_emittente'] = int(rac.duplicated(['ticker', 'data', 'emittente', 'raccomandazione', 'target']).sum())
    q['righe_senza_classe'] = int(rac.classe.isna().sum())
    q['righe_senza_target'] = int(rac.target.isna().sum())
    q['rac_su_ticker_senza_prezzi'] = int((~rac.ticker.isin(pr.tickers)).sum())
    q['emittenti_distinti'] = int(rac.emittente.nunique())
    u = sg.universo
    q['universo_titoli_per_data'] = {d: int(u.loc[d].sum()) for d in ('2025-08-29', '2025-09-30', '2025-12-30', '2026-04-30')}
    q['universo_titoli_distinti_in_sample'] = int(u.loc[D.INIZIO_SCELTA:].any().sum())
    q['regime_giorni_in_sample'] = {str(k): int(v) for k, v in sg.regime.loc[D.INIZIO_SCELTA:].value_counts().items()}
    neg = pr.negoziabile()
    q['giorni_in_sample'] = int((pr.calendario >= D.INIZIO_SCELTA).sum())
    q['quota_celle_universo_non_negoziabili'] = float((u & ~neg).values.sum() / max(u.values.sum(), 1))
    json.dump(q, open(OUT / 'qualita.json', 'w'), indent=1, ensure_ascii=False)
    # correlazioni di rango medie tra segnali (cross-section giornaliera, in-sample)
    nomi = ['potenziale', 'saldo_rev_60', 'saldo_rev_30', 'momentum_120', 'momentum_60', 'ritracciamento_60', 'n_target',
            'capitalizzazione_mld', 'atr_14_pct', 'dispersione_target', 'rev_tp_90', 'dist_tp_meno10']
    giorni = pr.calendario[(pr.calendario >= D.INIZIO_SCELTA)]
    rk = {k: sg.variabili[k].loc[giorni].rank(axis=1) for k in nomi}
    C = pd.DataFrame(index=nomi, columns=nomi, dtype=float)
    for a in nomi:
        for b in nomi:
            C.loc[a, b] = rk[a].corrwith(rk[b], axis=1).mean()
    C.round(3).to_csv(OUT / 'fase3_correlazioni.csv')
    print(json.dumps(q, indent=1, ensure_ascii=False)[:6000]); print(C.round(2).to_string())


if __name__ == '__main__':
    main()
