"""Fase 7 (DECISIONI_FASE6.md): verifica sul periodo 2026-05-01 .. ultima seduta e robustezza della Finalista 2.
Regole di simulazione e strategie casuali identiche alle fasi 4-6 (nessuna modifica).

Uso:  python3 -I ricerca/fase7.py
"""
import itertools
import json
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # il flag -I toglie la cartella dello script
import dati as D
import esperimenti as E
import motore as M
import riferimenti as RF
import strategie as ST

OUT = Path(__file__).resolve().parent / 'risultati'
MK = None
MKX = {}
BENCH = {}
FINE_VERIFICA_INIZIO = pd.Timestamp('2026-04-30')       # giorno del primo segnale della verifica
RIF12_INIZIO = pd.Timestamp('2025-11-17')               # primo giorno del riferimento a 12 mesi (apertura)
FIN = {1: dict(K=4, B=4, L=5e6), 2: dict(K=6, B=0, L=1e6)}   # Finaliste 1 e 2 (fase 6): COMP, R 21, reinvestimento, N = K


def mercato_pieno():
    global MK
    ultima = pd.Timestamp(pd.read_csv(D.RICERCA / 'indice_ftsemib.csv', parse_dates=['data']).data.max())
    MK = ST.Mercato(ultima)
    return MK


def bench(i_dec, i_fine, prezzo=False):
    k = (i_dec, i_fine, prezzo)
    if k not in BENCH:
        BENCH[k] = RF.ftsemib_bh(MK.ix, MK.y_div, i_dec + 1, i_fine, con_dividendi=not prezzo)
    return BENCH[k]


def strategia(mk, S, R, K, B, L, rein, ancora):
    return ST.Rotazione(mk, S, R, K, B, L, ST.Regole(), ST.Dim(K, reinvest=rein), ancora=ancora)


def corri(job):
    """Esegue un job: strategia netta e lorda sulla finestra, KPI, bench e percentile contro 500 casuali."""
    mk = MK
    if job.get('escludi'):
        mk = MKX.setdefault(job['escludi'], MK.escludi(job['escludi']))
    i_dec, i_fine = job['i_dec'], job['i_fine']
    cfg = M.Config(mult_costi=job.get('mult_costi', 1.0), mult_slittamento=job.get('mult_slitt', 1.0))
    rit = job.get('ritardo', 0)
    ancora = job.get('ancora', i_dec)

    def crea():
        st = strategia(mk, job['S'], job['R'], job['K'], job['B'], job['L'], job['rein'], ancora)
        return ST.Ritardata(st) if rit else st

    rn = mk.sim(cfg).esegui(crea(), inizio=i_dec, fine=i_fine)
    rl = mk.sim(M.Config(lordo=True)).esegui(crea(), inizio=i_dec, fine=i_fine)
    k, kl = rn.kpi(), rl.kpi()
    t = rn.trades
    top3, best = E.concentrazione(t)
    bt, bp = bench(i_dec, i_fine), bench(i_dec, i_fine, prezzo=True)
    pct = med = np.nan
    if len(t):
        pct, rend = ST.percentile_casuali(mk, cfg, t, job['L'], ST.Regole(), k['rendimento'], job['id'], i_inizio=i_dec,
                                          i_fine=i_fine, ritardo=rit)
        med = float(np.median(rend))
    out = dict(nome=job['nome'], gruppo=job['gruppo'], id=job['id'], S=job['S'], R=job['R'], K=job['K'], B=job['B'], L=job['L'],
               rein=job['rein'], ancora=ancora, inizio=str(mk.cal[i_dec + 1].date()), fine=str(mk.cal[i_fine].date()),
               guadagno_netto=k['guadagno'], rendimento_netto=k['rendimento'], rendimento_lordo=kl['rendimento'],
               ftse_tr_netto=bt['rendimento'], ftse_tr_guadagno=bt['patrimonio_finale'] - M.CAPITALE, ftse_prezzo_netto=bp['rendimento'],
               eccesso_ftse_tr=k['rendimento'] - bt['rendimento'], percentile_casuali=pct, mediana_casuali=med,
               max_drawdown=k['max_drawdown'], n_operazioni=k['n_operazioni'], quota_titolo_migliore=best,
               quota_3_trade_migliori=top3, commissioni=k['commissioni'], tobin=k['tobin'], slittamento=k['slittamento'],
               tasse=k['tasse'], esposizione=k['esposizione'])
    if job.get('salva'):
        t.to_csv(OUT / f"fase7_{job['salva']}_operazioni.csv", index=False)
        rn.equity.to_csv(OUT / f"fase7_{job['salva']}_patrimonio.csv", header=['patrimonio'])
    return out


def jobs():
    mk = MK
    cal = mk.cal
    ix = lambda d: int(cal.searchsorted(pd.Timestamp(d)))
    i_ver = ix(FINE_VERIFICA_INIZIO)                       # decisione alla chiusura del 30/4/2026
    assert cal[i_ver] == FINE_VERIFICA_INIZIO
    i_12 = ix(RIF12_INIZIO) - 1                            # decisione alla chiusura della seduta prima del 17/11/2025
    assert cal[i_12 + 1] == RIF12_INIZIO
    ultimo = mk.n - 1
    out, nid = [], [30000]

    def nuovo(**kw):
        kw['id'] = nid[0]; nid[0] += 1
        out.append(kw)

    # 1. finaliste sulla verifica
    for n, p in FIN.items():
        nuovo(nome=f'finalista{n}_verifica', gruppo='1_finaliste_verifica', S='COMP', R=21, rein=True, i_dec=i_ver, i_fine=ultimo,
              salva=f'finalista{n}_verifica', **p)
    # 2. zona di parametri: COMP, R 21, K 4/5/6 x B 0/K x L 1/5 mln x fissi/reinvestimento (N = K)
    for K, bk, L, rein in itertools.product([4, 5, 6], [False, True], [1e6, 5e6], [False, True]):
        nuovo(nome=f'zona_K{K}_B{K if bk else 0}_L{L / 1e6:g}_{"rein" if rein else "fissi"}', gruppo='2_zona', S='COMP', R=21,
              K=K, B=K if bk else 0, L=L, rein=rein, i_dec=i_ver, i_fine=ultimo)
    # 3. controlli: MOM, REV, POT come in fase 4 (blocchi fissi)
    for S, R, K, bk, L in itertools.product(['MOM', 'REV', 'POT'], [10, 21], [4, 5, 6], [False, True], [1e6, 5e6]):
        nuovo(nome=f'ctrl_{S}_R{R}_K{K}_B{K if bk else 0}_L{L / 1e6:g}', gruppo=f'3_controllo_{S}', S=S, R=R, K=K, B=K if bk else 0,
              L=L, rein=False, i_dec=i_ver, i_fine=ultimo)
    # 4. riferimento a 12 mesi (partenza 17/11/2025 con 20.000 euro)
    for n, p in FIN.items():
        nuovo(nome=f'finalista{n}_12mesi', gruppo='4_12mesi', S='COMP', R=21, rein=True, i_dec=i_12, i_fine=ultimo,
              salva=f'finalista{n}_12mesi', **p)
    # intero periodo continuo (per il grafico e per la robustezza)
    for n, p in FIN.items():
        nuovo(nome=f'finalista{n}_intero', gruppo='5_intero', S='COMP', R=21, rein=True, i_dec=mk.idec, i_fine=ultimo,
              salva=f'finalista{n}_intero', **p)
    # 5. robustezza della Finalista 2 sull'intero periodo
    f2 = dict(S='COMP', R=21, rein=True, **FIN[2])
    for s in (0, 5, 10, 15):
        nuovo(nome=f'rob_spostamento_{s}', gruppo='5_robustezza', i_dec=mk.idec, i_fine=ultimo, ancora=mk.idec + s, **f2)
    nuovo(nome='rob_costi1.5_slitt2', gruppo='5_robustezza', i_dec=mk.idec, i_fine=ultimo, mult_costi=1.5, mult_slitt=2.0, **f2)
    nuovo(nome='rob_esecuzione_ritardata', gruppo='5_robustezza', i_dec=mk.idec, i_fine=ultimo, ritardo=1, **f2)
    nuovo(nome='rob_senza_STMMI', gruppo='5_robustezza', i_dec=mk.idec, i_fine=ultimo, escludi='STMMI', **f2)
    # finestre mobili di 6 mesi: primo giorno di ogni mese da settembre 2025 a maggio 2026
    for m in pd.period_range('2025-09', '2026-05', freq='M'):
        primo = ix(m.start_time)                          # prima seduta del mese
        fine = int(cal.searchsorted(m.start_time + pd.DateOffset(months=6), side='left')) - 1
        nuovo(nome=f'finestra_{m}', gruppo='5_finestre6m', i_dec=primo - 1, i_fine=min(fine, ultimo), **f2)
    return out


def lavora(job):
    return corri(job)


def esito(df, info):
    g = lambda n: df[df.nome == n].iloc[0]
    f2 = g('finalista2_verifica')
    zona = df[df.gruppo == '2_zona']
    ftse = f2.ftse_tr_netto
    sp = df[df.nome.str.startswith('rob_spostamento')]
    c1 = bool(f2.rendimento_netto > ftse)
    c2 = bool(f2.percentile_casuali >= 80)
    c3 = bool(zona.rendimento_netto.median() > ftse)
    n4 = int((sp.rendimento_netto > sp.ftse_tr_netto).sum())
    c4 = n4 >= 3
    return dict(
        criterio1=dict(supera=c1, finalista2_netto=float(f2.rendimento_netto), ftse_tr_netto=float(ftse), finalista2_guadagno=float(f2.guadagno_netto),
                       ftse_tr_guadagno=float(f2.ftse_tr_guadagno)),
        criterio2=dict(supera=c2, percentile=float(f2.percentile_casuali)),
        criterio3=dict(supera=c3, mediana=float(zona.rendimento_netto.median()), minimo=float(zona.rendimento_netto.min()),
                       massimo=float(zona.rendimento_netto.max()), quota_sopra_ftse=float((zona.rendimento_netto > ftse).mean()),
                       ftse_tr_netto=float(ftse), n=int(len(zona))),
        criterio4=dict(supera=c4, casi_sopra=n4, di=int(len(sp)), dettaglio={r.nome: [float(r.rendimento_netto), float(r.ftse_tr_netto)] for r in sp.itertuples()}),
        supera_la_verifica=bool(c1 and c2 and c3 and c4), **info)


def main():
    mercato_pieno()
    js = jobs()
    with mp.get_context('fork').Pool(2) as pool:
        righe = []
        for n, r in enumerate(pool.imap(lavora, js, chunksize=1), 1):
            righe.append(r)
            if n % 10 == 0:
                print('fase7', n, '/', len(js), flush=True)
    df = pd.DataFrame(righe)
    df.to_csv(OUT / 'fase7.csv', index=False)
    info = dict(ultima_seduta=str(MK.cal[-1].date()), combinazioni_fase7=len(df), simulazioni_fase7=len(df) * 502, seme=ST.SEME)
    ev = esito(df, info)
    json.dump(ev, open(OUT / 'fase7_esito.json', 'w'), indent=1)
    print(json.dumps(ev, indent=1))


if __name__ == '__main__':
    main()
