"""Fasi 4, 5 e 6 (DECISIONI_FASE3.md). Dati fino al 2026-04-30; periodo di scelta 2025-09-01 .. 2026-04-30.

Uso:  python3 -I ricerca/esperimenti.py fase4 | fase5 | fase6
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
import motore as M
import riferimenti as RF
import strategie as ST

OUT = Path(__file__).resolve().parent / 'risultati'
MK = None          # Mercato condiviso (ereditato dai processi figli con fork)
BENCH = {}


def inizializza():
    global MK, BENCH
    MK = ST.Mercato()
    f = RF.ftsemib_bh(MK.ix, MK.y_div, MK.i0, MK.i1)
    fp = RF.ftsemib_bh(MK.ix, MK.y_div, MK.i0, MK.i1, con_dividendi=False)
    BENCH = dict(tr=f['rendimento'], prezzo=fp['rendimento'], eq_tr=f['equity'], eq_prezzo=fp['equity'],
                 dettagli=dict(dividendi_incassati=f['dividendi_incassati'], tassa_tr=f['tassa'], commissioni=f['commissioni']))


# ------------------------------------------------------------------------------------------ KPI
def concentrazione(tr: pd.DataFrame):
    if not len(tr):
        return np.nan, np.nan
    tot = tr.risultato_netto.sum()
    if tot <= 0:
        return np.nan, np.nan
    top3 = tr.risultato_netto.nlargest(3).sum() / tot
    per_titolo = tr.groupby('ticker').risultato_netto.sum()
    return float(top3), float(per_titolo.max() / tot)


def kpi_completi(mk, strategia, config_netto=None, L=None, regole=ST.Regole(), id_comb=0, n_casuali=ST.N_RIPETIZIONI, casuali=True):
    """Esegue la strategia netta e lorda, calcola tutti i KPI del piano, l'eccesso sul FTSE MIB con dividendi e
    il percentile contro le proprie strategie casuali. Ritorna (dict, Risultato netto)."""
    cfg = config_netto or M.Config()
    rn = mk.sim(cfg).esegui(strategia, inizio=mk.idec, fine=mk.i1)
    rl = mk.sim(M.Config(lordo=True)).esegui(strategia, inizio=mk.idec, fine=mk.i1)
    k, kl = rn.kpi(), rl.kpi()
    t = rn.trades
    top3, best = concentrazione(t)
    settimane = (mk.cal[mk.i1] - mk.cal[mk.i0]).days / 7.0
    costi = k['commissioni'] + k['tobin'] + k['slittamento']
    out = dict(rendimento_netto=k['rendimento'], guadagno_netto=k['guadagno'], ann_netto=k['rendimento_annualizzato'],
               rendimento_lordo=kl['rendimento'], ann_lordo=kl['rendimento_annualizzato'],
               eccesso_ftse_tr=k['rendimento'] - BENCH['tr'], eccesso_ftse_prezzo=k['rendimento'] - BENCH['prezzo'],
               max_drawdown=k['max_drawdown'], sharpe=k['sharpe'], sortino=k['sortino'],
               n_operazioni=k['n_operazioni'], commissioni=k['commissioni'], tobin=k['tobin'], slittamento=k['slittamento'],
               tasse=k['tasse'], costi_su_guadagno_lordo=(costi / kl['guadagno']) if kl['guadagno'] > 0 else np.nan,
               quota_vincenti=k.get('quota_vincenti', np.nan), guadagno_medio=k.get('guadagno_medio', np.nan),
               perdita_media=k.get('perdita_media', np.nan),
               rapporto_guad_perd=(k.get('guadagno_medio', np.nan) / abs(k['perdita_media'])) if k.get('perdita_media', 0) else np.nan,
               durata_media_sedute=k.get('durata_media_sedute', np.nan), esposizione=k['esposizione'],
               quota_3_trade_migliori=top3, quota_titolo_migliore=best,
               ordini_a_settimana=2 * k['n_operazioni'] / settimane)
    if casuali and L is not None:
        pct, rend = ST.percentile_casuali(mk, cfg, t, L, regole, k['rendimento'], id_comb, n=n_casuali)
        out.update(percentile_casuali=pct, mediana_casuali=float(np.median(rend)), media_casuali=float(rend.mean()),
                   p95_casuali=float(np.percentile(rend, 95)))
    out['vincolo_eccesso'] = out['eccesso_ftse_tr'] > 0
    out['vincolo_percentile'] = out.get('percentile_casuali', np.nan) >= 90
    out['vincolo_drawdown'] = out['max_drawdown'] >= -0.20
    out['vincolo_titolo_migliore'] = bool(best <= 0.40) if not np.isnan(best) else False
    out['vincoli_ok'] = bool(out['vincolo_eccesso'] and out['vincolo_percentile'] and out['vincolo_drawdown'] and out['vincolo_titolo_migliore'])
    return out, rn


# ------------------------------------------------------------------------------------------ fase 4
def griglia_fase4():
    g = []
    for S, R, K, B, L in itertools.product(['MOM', 'REV', 'COMP', 'POT'], [10, 21], [4, 5, 6], [0, 'K'], [1e6, 5e6]):
        b = K if B == 'K' else 0
        g.append(dict(famiglia='A', segnale=S, R=R, K=K, B=b, L=L, controllo=(S == 'POT')))
    for ev, fl, N, L, us in itertools.product(['ALZ5', 'ALZ10'], ['nessuno', 'MOM>0', 'COMP>=0.5'], [4, 5, 6], [1e6, 5e6],
                                              ['60', '60+stop12']):
        g.append(dict(famiglia='B', evento=ev, filtro=fl, N=N, L=L, uscita=us, controllo=False))
    for i, c in enumerate(g):
        c['id'] = i
    return g


def costruisci(c, mk):
    if c['famiglia'] == 'A':
        r = ST.Regole(**c.get('regole', {}))
        return ST.Rotazione(mk, c['segnale'], c['R'], c['K'], c['B'], c['L'], r, ST.Dim(c['K'], **c.get('dim', {}))), r
    base = dict(tempo=60, stop=0.12 if c.get('uscita') == '60+stop12' else None)
    base.update({k: v for k, v in c.get('regole', {}).items() if k != 'tempo'})      # per B il tempo e' sempre 60
    r = ST.Regole(**base)
    return ST.Eventi(mk, c['evento'], c['filtro'], c['N'], c['L'], r, ST.Dim(c['N'], **c.get('dim', {}))), r


def lavora(c):
    st, r = costruisci(c, MK)
    cfg = M.Config(tobin_dal_2026=c['tobin_2026']) if 'tobin_2026' in c else None
    k, _ = kpi_completi(MK, st, config_netto=cfg, L=c['L'], regole=r, id_comb=c['id'])
    flat = {kk: vv for kk, vv in c.items() if kk not in ('regole', 'dim')}
    flat['regole'] = r.nome()
    flat['dim'] = json.dumps(c.get('dim', {}))
    return {**flat, **k}


def esegui_griglia(griglia, nome):
    with mp.get_context('fork').Pool(2) as pool:
        righe = []
        for n, r in enumerate(pool.imap(lavora, griglia, chunksize=1), 1):
            righe.append(r)
            if n % 20 == 0:
                print(nome, n, '/', len(griglia), flush=True)
    return pd.DataFrame(righe)


def fase4():
    inizializza()
    g = griglia_fase4()
    df = esegui_griglia(g, 'fase4')
    df.to_csv(OUT / 'fase4.csv', index=False)
    # condizione di arresto (POT escluso)
    ok = df[~df.controllo & (df.percentile_casuali >= 90) & (df.eccesso_ftse_tr > 0)]
    info = dict(combinazioni=len(df), famiglia_A=int((df.famiglia == 'A').sum()), famiglia_B=int((df.famiglia == 'B').sum()),
                ftse_tr_netto=BENCH['tr'], ftse_prezzo_netto=BENCH['prezzo'],
                superano_condizione=int(len(ok)), arresto=bool(len(ok) == 0),
                superano_tutti_i_vincoli=int(df[~df.controllo].vincoli_ok.sum()),
                ultimo_dato=str(D.DATA_FINE.date()), seme=ST.SEME)
    json.dump(info, open(OUT / 'fase4_esito.json', 'w'), indent=1)
    print(json.dumps(info, indent=1))



# ------------------------------------------------------------------------------------------ scelte
VERSO_SU = {'R': [10, 21], 'K': [4, 5, 6], 'L': [1e6, 5e6], 'N': [4, 5, 6]}


def vicine(df, riga):
    """Righe che differiscono dalla riga per un solo parametro di un passo (stessa famiglia e stesso segnale/evento/filtro)."""
    if riga.famiglia == 'A':
        chiave = ['famiglia', 'segnale']
        par = {'R': riga.R, 'K': riga.K, 'bk': riga.B > 0, 'L': riga.L}
        d = df[(df.famiglia == 'A') & (df.segnale == riga.segnale)].assign(bk=lambda x: x.B > 0)
        scal = {'R': VERSO_SU['R'], 'K': VERSO_SU['K'], 'L': VERSO_SU['L'], 'bk': [False, True]}
    else:
        par = {'N': riga.N, 'L': riga.L, 'uscita': riga.uscita}
        d = df[(df.famiglia == 'B') & (df.evento == riga.evento) & (df.filtro == riga.filtro)]
        scal = {'N': VERSO_SU['N'], 'L': VERSO_SU['L'], 'uscita': ['60', '60+stop12']}
    out = []
    for p, lista in scal.items():
        j = lista.index(par[p])
        for jj in (j - 1, j + 1):
            if 0 <= jj < len(lista):
                m = d
                for q in scal:
                    m = m[m[q] == (lista[jj] if q == p else par[q])]
                out.extend(m.index.tolist())
    return out


def aggiungi_vicine(df):
    df = df.copy()
    medie, quote = [], []
    for ix, r in df.iterrows():
        v = vicine(df, r)
        medie.append(df.loc[v, 'rendimento_netto'].mean() if v else np.nan)
        quote.append((df.loc[v, 'rendimento_netto'] > BENCH['tr']).mean() if v else np.nan)
    df['vicine_rend_medio'] = medie
    df['vicine_quota_sopra_ftse'] = quote
    return df


def scegli_fase4(df, n=3):
    """Migliori = vincoli rispettati (esclusa POT), vicine in media sopra il FTSE MIB con dividendi, poi rendimento netto."""
    d = aggiungi_vicine(df)
    ok = d[~d.controllo & d.vincoli_ok & (d.vicine_rend_medio >= BENCH['tr'])]
    return d, ok.sort_values('rendimento_netto', ascending=False).head(n)


def riga_a_comb(r):
    c = {k: r[k] for k in ('id', 'famiglia', 'L', 'controllo') if k in r}
    if r['famiglia'] == 'A':
        c.update(segnale=r['segnale'], R=int(r['R']), K=int(r['K']), B=int(r['B']))
    else:
        c.update(evento=r['evento'], filtro=r['filtro'], N=int(r['N']), uscita=r['uscita'])
    return c


# ------------------------------------------------------------------------------------------ fase 5
def regole_fase5(famiglia):
    tp = [dict(take_profit=x) for x in (0.08, 0.12, 0.20)]
    stop = [dict(stop=0.08), dict(stop=0.12), dict(stop_atr=2.5)]
    tr = [dict(trailing=x) for x in (0.12, 0.20)]
    tempo = [dict(tempo=x) for x in (60, 120)] if famiglia == 'A' else []
    tpm = [dict(tp_medio=0.9)]
    cat = [c for c in (tp, stop, tr, tempo, tpm) if c]
    out = [{}]
    for c in cat:
        out.extend(c)
    for c1, c2 in itertools.combinations(cat, 2):
        for a, b in itertools.product(c1, c2):
            out.append({**a, **b})
    return out


def fase5():
    inizializza()
    f4 = pd.read_csv(OUT / 'fase4.csv')
    d4, base = scegli_fase4(f4, 3)
    print('base fase 5:\n', base[['id', 'famiglia', 'segnale', 'R', 'K', 'B', 'L', 'rendimento_netto', 'percentile_casuali', 'vicine_rend_medio']])
    if len(base) == 0:
        print('Nessuna combinazione adatta alla fase 5'); return
    griglia, nid = [], 10000
    for _, b in base.iterrows():
        for reg in regole_fase5(b.famiglia):
            c = riga_a_comb(b)
            c.update(base_id=int(b.id), id=nid, regole=reg)
            griglia.append(c); nid += 1
    df = esegui_griglia(griglia, 'fase5')
    df.to_csv(OUT / 'fase5.csv', index=False)
    json.dump(dict(basi=[int(x) for x in base.id], combinazioni=len(df)), open(OUT / 'fase5_esito.json', 'w'))
    print(len(df), 'combinazioni fase 5')


# ------------------------------------------------------------------------------------------ fase 6
def sorgente_fase6(df5, tolleranza=0.005):
    """Le 2 migliori della fase 5: una per ciascuna combinazione di base (altrimenti la seconda sarebbe quasi la copia
    della prima). Per ogni base: vincoli rispettati, poi rendimento netto piu' alto; a parita' (entro `tolleranza`
    = 0,5 punti) vince chi ha meno regole di uscita aggiunte (criterio del piano: meno regole)."""
    ok = df5[df5.vincoli_ok].copy()
    ok['n_regole'] = ok.regole.map(lambda x: 0 if x == 'base' else x.count('+') + 1)
    scelte = []
    for bid, g in ok.groupby('base_id'):
        mx = g.rendimento_netto.max()
        v = g[g.rendimento_netto >= mx - tolleranza].sort_values(['n_regole', 'rendimento_netto'], ascending=[True, False])
        scelte.append(v.iloc[0])
    return pd.DataFrame(scelte).sort_values('rendimento_netto', ascending=False).head(2)


def regole_da_nome(nome):
    mappa = {'TP': ('take_profit', 0.01), 'SLATR': ('stop_atr', 1.0), 'SL': ('stop', 0.01), 'TR': ('trailing', 0.01),
             'TPM': ('tp_medio', 1.0), 'T': ('tempo', 1)}
    out = {}
    if nome == 'base':
        return out
    for part in nome.split('+'):
        for pref in ('SLATR', 'TPM', 'TP', 'SL', 'TR', 'T'):
            if part.startswith(pref):
                k, f = mappa[pref]
                v = float(part[len(pref):]) * f
                out[k] = int(round(v)) if k == 'tempo' else round(v, 6)
                break
    return out


def fase6():
    inizializza()
    f5 = pd.read_csv(OUT / 'fase5.csv')
    f4 = pd.read_csv(OUT / 'fase4.csv')
    src = sorgente_fase6(f5)
    print('sorgenti fase 6:\n', src[['id', 'base_id', 'regole', 'rendimento_netto', 'percentile_casuali']])
    griglia, nid = [], 20000
    for _, b in src.iterrows():
        r4 = f4[f4.id == b.base_id].iloc[0]
        for N, rein, inv in itertools.product([4, 5, 6, 8], [False, True], [False, True]):
            c = riga_a_comb(r4)
            if c['famiglia'] == 'A':
                c['B'] = N if int(r4.B) > 0 else 0
                c['K'] = N
            else:
                c['N'] = N
            c.update(id=nid, base_id=int(b.base_id), sorgente_id=int(b.id), regole=regole_da_nome(b.regole),
                     dim=dict(reinvest=rein, inv_atr=inv), N_blocchi=N)
            griglia.append(c); nid += 1
    df = esegui_griglia(griglia, 'fase6')
    df['sensibilita_tobin04'] = False
    # sensibilita' Tobin 0,4% dal 2026 sulle scelte migliori di ciascuna sorgente (non serve alla scelta)
    sens = []
    for sid, g in df.groupby('sorgente_id'):
        ok = g[g.vincoli_ok].sort_values('rendimento_netto', ascending=False)
        best = (ok if len(ok) else g.sort_values('rendimento_netto', ascending=False)).iloc[0]
        c = [x for x in griglia if x['id'] == best.id][0]
        c = {**c, 'id': best.id + 5000, 'tobin_2026': 0.004}
        sens.append(c)
    ds = esegui_griglia(sens, 'fase6-tobin04')
    ds['sensibilita_tobin04'] = True
    pd.concat([df, ds], ignore_index=True).to_csv(OUT / 'fase6.csv', index=False)
    print(len(df), 'combinazioni fase 6 +', len(ds), 'sensibilita')



# ------------------------------------------------------------------------------------------ finaliste
def comb_da_riga6(r6, f4):
    r4 = f4[f4.id == r6.base_id].iloc[0]
    c = riga_a_comb(r4)
    N = int(r6.N_blocchi)
    if c['famiglia'] == 'A':
        c['B'] = N if int(r4.B) > 0 else 0
        c['K'] = N
    else:
        c['N'] = N
    c.update(id=int(r6.id), dim=json.loads(r6.dim), regole=regole_da_nome(r6.regole))
    return c


def finali():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    inizializza()
    f4 = pd.read_csv(OUT / 'fase4.csv'); f6 = pd.read_csv(OUT / 'fase6.csv')
    f6 = f6[~f6.sensibilita_tobin04]
    fin = []
    for sid, g in f6.groupby('sorgente_id'):
        ok = g[g.vincoli_ok].sort_values('rendimento_netto', ascending=False)
        fin.append((ok if len(ok) else g.sort_values('rendimento_netto', ascending=False)).iloc[0])
    fin = sorted(fin, key=lambda r: -r.rendimento_netto)
    colori = ['#2a78d6', '#eb6834']
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor='#fcfcfb')
    ax.set_facecolor('#fcfcfb')
    eq_ftse = BENCH['eq_tr']
    ax.plot(eq_ftse.index, eq_ftse.values, color='#52514e', lw=2, label=f"FTSE MIB con dividendi stimati (netto {100 * BENCH['tr']:.1f}%)")
    info = {}
    for n, (r6, col) in enumerate(zip(fin, colori), 1):
        c = comb_da_riga6(r6, f4)
        st, rg = costruisci(c, MK)
        cfg = M.Config()
        res = MK.sim(cfg).esegui(st, inizio=MK.idec, fine=MK.i1)
        t = res.trades.copy()
        t.to_csv(OUT / f'finalista{n}_operazioni.csv', index=False)
        res.equity.to_csv(OUT / f'finalista{n}_patrimonio.csv', header=['patrimonio'])
        # equity delle 500 casuali (stessi semi di percentile_casuali)
        piano = ST.piano_da_trades(t)
        ss = np.random.SeedSequence([ST.SEME, int(c['id'])])
        curve = []
        for fig_ in ss.spawn(ST.N_RIPETIZIONI):
            sim = MK.sim(cfg)
            r_ = sim.esegui(ST.Casuale(MK, c['L'], piano, rg, np.random.default_rng(fig_)), inizio=MK.idec, fine=MK.i1)
            curve.append(r_.equity.values)
        curve = np.array(curve)
        med = np.median(curve, axis=0)
        ax.fill_between(res.equity.index, np.percentile(curve, 5, axis=0), np.percentile(curve, 95, axis=0), color=col, alpha=0.10, lw=0)
        ax.plot(res.equity.index, med, color=col, lw=1.5, ls='--', label=f'Finalista {n}: mediana delle 500 casuali (banda 5°–95°)')
        ax.plot(res.equity.index, res.equity.values, color=col, lw=2.2, label=f"Finalista {n} (netto {100 * res.kpi()['rendimento']:.1f}%)")
        info[n] = dict(id=int(c['id']), params={k: (v if not isinstance(v, (np.integer, np.floating)) else v.item()) for k, v in c.items()},
                       rendimento_netto=res.kpi()['rendimento'], mediana_casuali_finale=float(np.median(curve[:, -1]) / 20000 - 1),
                       ordini_a_settimana=float(r6.ordini_a_settimana), n_operazioni=int(r6.n_operazioni))
    ax.set_title('Patrimonio netto di costi e tasse, 29/8/2025 – 30/4/2026 (solo periodo di scelta)', loc='left', fontsize=12, color='#0b0b0b')
    ax.set_ylabel('Euro', color='#52514e')
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
    ax.grid(axis='y', color='#e4e3df', lw=0.8)
    ax.tick_params(colors='#52514e')
    ax.legend(frameon=False, fontsize=9, loc='upper left')
    fig.tight_layout()
    fig.savefig(OUT / 'patrimonio_finaliste.png', dpi=150)
    json.dump(info, open(OUT / 'finaliste.json', 'w'), indent=1, default=str)
    print(json.dumps(info, indent=1, default=str))


if __name__ == '__main__':
    {'fase4': fase4, 'fase5': fase5, 'fase6': fase6, 'finali': finali}[sys.argv[1]]()
