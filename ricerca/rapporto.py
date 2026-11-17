"""Genera risultati/diagnosi_fase7.csv, il grafico dell'intero periodo e RAPPORTO.md dai risultati della fase 7.
Uso: python3 -I ricerca/rapporto.py   (dopo fase7.py)"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dati as D
import fase3 as F3
import fase7 as F7
import motore as M
import riferimenti as RF
import segnali as S
import strategie as ST

QUI = Path(__file__).resolve().parent
OUT = QUI / 'risultati'
pc = lambda x, d=1: 'n.d.' if pd.isna(x) else f'{100 * x:+.{d}f}%'.replace('+-', '-')
pcs = lambda x, d=1: 'n.d.' if pd.isna(x) else f'{100 * x:.{d}f}%'
eur = lambda x: 'n.d.' if pd.isna(x) else f'{x:+,.0f} €'.replace(',', '.')


def diagnosi(mk):
    """IC di rango (h = 20) di MOM, REV, COMP, POT: periodo di scelta contro verifica. Solo descrittivo."""
    dpan = S.dividendi_pannello(mk.pr, D.carica_dividendi(mk.cal[-1]))
    fut = S.rendimenti_futuri(mk.pr, dpan, (20,))[20]
    cal = mk.cal
    righe = []
    per = {'scelta (t da 1/9/2025 al 30/4/2026)': (pd.Timestamp('2025-09-01'), pd.Timestamp('2026-04-30')),
           'verifica (t da 4/5/2026)': (pd.Timestamp('2026-05-04'), cal[-21])}
    for nome, (a, b) in per.items():
        giorni = cal[(cal >= a) & (cal <= b)]
        for S_ in ('MOM', 'REV', 'POT', 'COMP'):
            X = pd.DataFrame(mk.segnale(S_, 1e6), index=cal, columns=mk.tickers).where(pd.DataFrame(mk.elig[1e6], index=cal, columns=mk.tickers))
            R = fut.where(pd.DataFrame(mk.elig[1e6], index=cal, columns=mk.tickers))
            ic, med, mdn, n = F3.analisi_continua(X, R, giorni)
            q = np.nanmean(med, axis=0)
            righe.append(dict(periodo=nome, segnale=S_, giorni=int(ic.notna().sum()), ic_medio_20=float(ic.mean()),
                              q1=float(q[0]), q5=float(q[4]), q5_meno_q1=float(q[4] - q[0])))
        Rm = fut.where(pd.DataFrame(mk.elig[1e6], index=cal, columns=mk.tickers)).loc[giorni].mean(axis=1).mean()
        righe.append(dict(periodo=nome, segnale='UNIVERSO_medio', giorni=len(giorni), ic_medio_20=np.nan, q1=np.nan, q5=np.nan,
                          q5_meno_q1=float(Rm)))
    d = pd.DataFrame(righe)
    d.to_csv(OUT / 'diagnosi_fase7.csv', index=False)
    return d


def grafico(mk, df):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    F7.MK = mk
    ult = mk.n - 1
    ftse = RF.ftsemib_bh(mk.ix, mk.y_div, mk.idec + 1, ult)['equity']
    ftse = pd.concat([pd.Series([20000.0], index=[mk.cal[mk.idec]]), ftse])
    fig, ax = plt.subplots(figsize=(11, 5.8), facecolor='#fcfcfb')
    ax.set_facecolor('#fcfcfb')
    ax.plot(ftse.index, ftse.values, color='#52514e', lw=2, label='FTSE MIB con dividendi stimati (netto)')
    # mediana delle 500 casuali della Finalista 2 (stessi semi del percentile)
    r2 = df[df.nome == 'finalista2_intero'].iloc[0]
    tr2 = pd.read_csv(OUT / 'fase7_finalista2_intero_operazioni.csv')
    piano = ST.piano_da_trades(tr2)
    curve = []
    for fig_ in np.random.SeedSequence([ST.SEME, int(r2.id)]).spawn(ST.N_RIPETIZIONI):
        sim = mk.sim()
        res = sim.esegui(ST.Casuale(mk, 1e6, piano, ST.Regole(), np.random.default_rng(fig_)), inizio=mk.idec, fine=ult)
        curve.append(res.equity.values)
    curve = np.array(curve)
    idx = mk.cal[mk.idec:]
    ax.fill_between(idx, np.percentile(curve, 5, axis=0), np.percentile(curve, 95, axis=0), color='#eb6834', alpha=0.10, lw=0)
    ax.plot(idx, np.median(curve, axis=0), color='#eb6834', lw=1.5, ls='--', label='Finalista 2: mediana delle 500 casuali (banda 5°–95°)')
    for n, col, nome in ((1, '#2a78d6', 'Finalista 1'), (2, '#eb6834', 'Finalista 2')):
        e = pd.read_csv(OUT / f'fase7_finalista{n}_intero_patrimonio.csv', index_col=0, parse_dates=True).patrimonio
        fin = df[df.nome == f'finalista{n}_intero'].iloc[0]
        ax.plot(e.index, e.values, color=col, lw=2.2, label=f'{nome} (a fine periodo {pc(fin.rendimento_netto)} netto)')
    sep = pd.Timestamp('2026-04-30')
    ax.axvline(sep, color='#0b0b0b', lw=1.2, ls=':')
    ymax = ax.get_ylim()[1]
    ax.text(sep - pd.Timedelta(days=4), ymax * 0.99, 'scelta', ha='right', va='top', color='#52514e', fontsize=10)
    ax.text(sep + pd.Timedelta(days=4), ymax * 0.99, 'verifica', ha='left', va='top', color='#52514e', fontsize=10)
    ax.set_title('Patrimonio netto di costi e tasse, 29/8/2025 – 17/11/2026 (20.000 € iniziali)', loc='left', fontsize=12, color='#0b0b0b')
    ax.set_ylabel('Euro', color='#52514e')
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
    ax.grid(axis='y', color='#e4e3df', lw=0.8)
    ax.tick_params(colors='#52514e')
    ax.legend(frameon=False, fontsize=9, loc='lower left')
    fig.tight_layout()
    fig.savefig(OUT / 'patrimonio_intero_periodo.png', dpi=150)
    return float(np.median(curve[:, -1]) / 20000 - 1)


def tab(df, cols, nomi):
    h = '| ' + ' | '.join(nomi) + ' |\n|' + '---|' * len(nomi) + '\n'
    for _, r in df.iterrows():
        h += '| ' + ' | '.join(f(r) for f in cols) + ' |\n'
    return h


def main():
    mk = F7.mercato_pieno()
    df = pd.read_csv(OUT / 'fase7.csv')
    ev = json.load(open(OUT / 'fase7_esito.json'))
    diag = diagnosi(mk)
    mediana_casuali_intero = grafico(mk, df)
    g = lambda n: df[df.nome == n].iloc[0]
    esiti = lambda b: 'SUPERA' if b else 'NON SUPERA'

    col_std = [lambda r: r.nome, lambda r: pc(r.rendimento_netto), lambda r: eur(r.guadagno_netto), lambda r: pc(r.rendimento_lordo),
               lambda r: pc(r.eccesso_ftse_tr), lambda r: 'n.d.' if pd.isna(r.percentile_casuali) else f'{r.percentile_casuali:.1f}',
               lambda r: pcs(r.max_drawdown), lambda r: str(int(r.n_operazioni))]
    n_std = ['Voce', 'Netto', 'Guadagno', 'Lordo', 'Eccesso su FTSE MIB div.', 'Percentile', 'Max drawdown', 'Operazioni']
    ver = df[df.gruppo == '1_finaliste_verifica']
    zona = df[df.gruppo == '2_zona']
    ctrl = {s: df[df.gruppo == f'3_controllo_{s}'] for s in ('MOM', 'REV', 'POT')}
    rob = df[df.gruppo == '5_robustezza']
    fin6 = df[df.gruppo == '5_finestre6m']
    m12 = df[df.gruppo == '4_12mesi']
    intero = df[df.gruppo == '5_intero']
    f2v, f1v = g('finalista2_verifica'), g('finalista1_verifica')
    ftse_v = f2v.ftse_tr_netto
    # alternativa: variazione di patrimonio nella corsa continua tra il 14/11/2025 e il 17/11/2026
    alt = {}
    for n in (1, 2):
        e = pd.read_csv(OUT / f'fase7_finalista{n}_intero_patrimonio.csv', index_col=0, parse_dates=True).patrimonio
        alt[n] = float(e.iloc[-1] - e.loc['2025-11-14'])
    tot_prec = 379 + 81
    ev2 = pd.read_csv(OUT / 'fase7_finalista2_verifica_patrimonio.csv', index_col=0, parse_dates=True).patrimonio
    vpicco, vfin, vdata = float(ev2.max()), float(ev2.iloc[-1]), ev2.idxmax().date().strftime('%d/%m/%Y')
    picco = {}
    for n in (1, 2):
        e = pd.read_csv(OUT / f'fase7_finalista{n}_intero_patrimonio.csv', index_col=0, parse_dates=True).patrimonio
        picco[n] = (f'{e.idxmax().date().strftime("%d/%m/%Y")}', float(e.max()))
    comb_f7 = len(df)
    d_sc = diag[diag.periodo.str.startswith('scelta')].set_index('segnale')
    d_ve = diag[diag.periodo.str.startswith('verifica')].set_index('segnale')
    tdiag = '| Segnale | IC medio a 20 sedute, scelta | IC medio a 20 sedute, verifica | Q5−Q1 a 20 sedute, scelta | Q5−Q1 a 20 sedute, verifica |\n|---|---|---|---|---|\n'
    for s in ('MOM', 'REV', 'COMP', 'POT'):
        tdiag += f"| {s} | {d_sc.loc[s, 'ic_medio_20']:+.3f} | {d_ve.loc[s, 'ic_medio_20']:+.3f} | {pc(d_sc.loc[s, 'q5_meno_q1'])} | {pc(d_ve.loc[s, 'q5_meno_q1'])} |\n"
    tdiag += f"| Rendimento medio a 20 sedute dell'universo | {pc(d_sc.loc['UNIVERSO_medio', 'q5_meno_q1'])} | {pc(d_ve.loc['UNIVERSO_medio', 'q5_meno_q1'])} | | |\n"
    c = ev
    md = f"""# Rapporto finale – strategia di rotazione COMP sui titoli italiani con target price

Ultima seduta dei dati: **{ev['ultima_seduta']}** (il 17/11/2026 hanno prezzo 204 titoli su 216: l'ultima chiusura può essere parziale). Seme fisso {ST.SEME}. Tutte le regole di simulazione sono quelle delle fasi 4–6, senza modifiche.

## 1. Esito della verifica: **NON SUPERA**

I criteri erano stati fissati prima di guardare il periodo di verifica (DECISIONI_FASE6.md) e valgono tutti insieme. Ne manca **ognuno dei quattro**:

| # | Criterio | Risultato | Esito |
|---|---|---|---|
| 1 | Finalista 2, periodo di verifica: netto > FTSE MIB con dividendi stimati | {pc(c['criterio1']['finalista2_netto'])} contro {pc(c['criterio1']['ftse_tr_netto'])} | **{esiti(c['criterio1']['supera'])}** |
| 2 | Finalista 2, verifica: percentile ≥ 80 contro le sue 500 casuali | {c['criterio2']['percentile']:.1f} | **{esiti(c['criterio2']['supera'])}** |
| 3 | Zona di parametri (24 combinazioni COMP, R 21): mediana > FTSE MIB con dividendi | mediana {pc(c['criterio3']['mediana'])} (min {pc(c['criterio3']['minimo'])}, max {pc(c['criterio3']['massimo'])}); sopra il FTSE MIB: {int(round(100 * c['criterio3']['quota_sopra_ftse']))}% | **{esiti(c['criterio3']['supera'])}** |
| 4 | Robustezza: con i 4 spostamenti del giorno di ribilanciamento, netto sull'intero periodo sopra il FTSE MIB con dividendi in almeno 3 casi su 4 | {c['criterio4']['casi_sopra']} su {c['criterio4']['di']} | **{esiti(c['criterio4']['supera'])}** |

Verifica = 4/5/2026 (il 1/5 è festivo; primo segnale alla chiusura del 30/4) – 17/11/2026, 20.000 € in contanti all'inizio. **Non si usa la strategia con denaro vero.** Nessuna regola è stata cambiata dopo aver visto i risultati; le idee di modifica sono nella sezione 8 come proposte separate.

In parole povere: nei sei mesi e mezzo successivi alla scelta la regola ha perso più di un quarto del capitale mentre il FTSE MIB con dividendi guadagnava circa il 5%, ed ha fatto peggio di quasi tutte le scelte casuali. Il vantaggio visto in passato non si è ripetuto.

## 2. Le regole (cosa si è verificato)
Questa è la Finalista 2, la candidata principale; le due finaliste differiscono solo per numero di titoli e liquidità minima.

- **Cosa comprare**: ogni 21 sedute, alla chiusura, si guardano i titoli italiani con almeno 5 target price validi negli ultimi 120 giorni e almeno 1 milione di euro di controvalore giornaliero mediano (ultime 60 sedute). Per ciascuno si calcolano due graduatorie (0–1): il rendimento delle ultime 120 sedute (momentum) e il saldo tra target alzati e abbassati dagli analisti negli ultimi 60 giorni (revisioni). Il punteggio COMP è la media delle due. Si scelgono i **6 titoli** con COMP più alto.
- **Quando**: ribilanciamento ogni 21 sedute a partire dal 29/8/2025; gli ordini vanno all'apertura della seduta successiva. Il primo acquisto è il 1/9/2025.
- **Quanto**: ogni titolo riceve un sesto del patrimonio corrente (reinvestimento); numero intero di azioni; niente leva né vendite allo scoperto.
- **Quando vendere**: solo quando un titolo non è più tra i primi 6 (o non passa più i filtri); si vende all'apertura del giorno dopo il ribilanciamento. Nessuno stop e nessun take profit: la fase 5 ha mostrato che tutte le uscite anticipate peggiorano il risultato.
- **Finalista 1**: stessa idea con 4 titoli, margine di uscita fino alla 8ª posizione e almeno 5 milioni di euro di controvalore giornaliero.
- Costi simulati: commissione 6,40 € + 0,24% oltre 1.460 €, Tobin 0,1% nel 2025 e 0,2% dal 2026 (esenti i titoli in `tobin_esenti.csv`), slittamento 0,05%–0,20% secondo la liquidità, dividendi al 74%, imposta 26% con compensazione delle perdite.

## 3. Risultati della verifica

{tab(ver, col_std, n_std)}
Termine di confronto sullo stesso periodo: FTSE MIB con dividendi stimati {pc(ftse_v)} netto ({eur(f2v.ftse_tr_guadagno)}); solo prezzo {pc(f2v.ftse_prezzo_netto)}. Mediana delle 500 casuali della Finalista 2: {pc(f2v.mediana_casuali)}.

**Zona di parametri** (24 combinazioni COMP, R 21): netto mediano {pc(c['criterio3']['mediana'])}, minimo {pc(c['criterio3']['minimo'])}, massimo {pc(c['criterio3']['massimo'])}; nessuna batte il FTSE MIB con dividendi; percentile massimo {zona.percentile_casuali.max():.1f}. Il problema non è un parametro sfortunato: tutta la zona che in fase 4 occupava le prime 10 posizioni è andata male.

**Controlli** (24 combinazioni ciascuno, blocchi fissi, come in fase 4), medie sul periodo di verifica:

| Segnale | Netto medio | Eccesso medio su FTSE MIB div. | Percentile medio |
|---|---|---|---|
""" + ''.join(f"| {s} | {pc(x.rendimento_netto.mean())} | {pc(x.eccesso_ftse_tr.mean())} | {x.percentile_casuali.mean():.1f} |\n" for s, x in ctrl.items()) + f"""
POT (il «potenziale alto»), che nel periodo di scelta era un controllo negativo (media −15%), nella verifica perde molto meno dei segnali che avevano funzionato: i segnali si sono ribaltati. Questo non cambia il giudizio, ma dice che l'effetto trend + revisioni non era stabile.

### Diagnosi descrittiva: i segnali nei due periodi
Correlazione di rango media (IC) con il rendimento a 20 sedute e differenza tra quintile migliore e peggiore, tra i titoli ammessi (liquidità ≥ 1 mln €). Calcolato a posteriori, non entra nei criteri.

{tdiag}
## 4. Riferimento a 12 mesi (17/11/2025 – 17/11/2026), 20.000 € iniziali

{tab(m12, col_std, n_std)}
| Voce | Guadagno netto |
|---|---|
| Finalista 1, partendo il 17/11/2025 | {eur(g('finalista1_12mesi').guadagno_netto)} |
| Finalista 2, partendo il 17/11/2025 | {eur(g('finalista2_12mesi').guadagno_netto)} |
| FTSE MIB con dividendi stimati | {eur(g('finalista2_12mesi').ftse_tr_guadagno)} ({pc(g('finalista2_12mesi').ftse_tr_netto)}) |
| FTSE MIB solo prezzo | {pc(g('finalista2_12mesi').ftse_prezzo_netto)} |

Convenzione: nuova partenza con 20.000 € in contanti; primo segnale alla chiusura del 14/11/2025, poi ribilanciamenti ogni 21 sedute da quel giorno. Il riferimento contiene sei mesi e mezzo di scelta (nov 2025 – apr 2026) e sei e mezzo di verifica. Se invece si guarda la variazione di patrimonio della corsa continua iniziata il 29/8/2025, tra la chiusura del 14/11/2025 e il 17/11/2026 (dopo liquidazione e imposte): Finalista 1 {eur(alt[1])}, Finalista 2 {eur(alt[2])}. In ogni lettura **le finaliste stanno sotto il FTSE MIB con dividendi**.

## 5. Robustezza della Finalista 2 sull'intero periodo (1/9/2025 – 17/11/2026)

{tab(rob, [lambda r: r.nome, lambda r: pc(r.rendimento_netto), lambda r: pc(r.ftse_tr_netto), lambda r: pc(r.eccesso_ftse_tr), lambda r: 'n.d.' if pd.isna(r.percentile_casuali) else f'{r.percentile_casuali:.1f}', lambda r: pcs(r.max_drawdown), lambda r: str(int(r.n_operazioni))], ['Prova', 'Netto', 'FTSE MIB div.', 'Eccesso', 'Percentile', 'Max drawdown', 'Operazioni'])}
Sull'intero periodo la Finalista 2 (spostamento 0) rende {pc(g('rob_spostamento_0').rendimento_netto)} netto contro {pc(g('rob_spostamento_0').ftse_tr_netto)} del FTSE MIB con dividendi. Il risultato dipende molto dal giorno di ribilanciamento (da {pc(rob[rob.nome.str.startswith('rob_spost')].rendimento_netto.min())} a {pc(rob[rob.nome.str.startswith('rob_spost')].rendimento_netto.max())}); togliendo STMMI diventa {pc(g('rob_senza_STMMI').rendimento_netto)}; con costi ×1,5 e slittamento ×2 resta {pc(g('rob_costi1.5_slitt2').rendimento_netto)}; l'esecuzione ritardata di un giorno non cambia molto ({pc(g('rob_esecuzione_ritardata').rendimento_netto)}). La prova «Tobin 0,4% dal 2027» non è pertinente (nessuna seduta nel 2027) e non è stata eseguita.

### Finestre mobili di 6 mesi (partenza il primo giorno di ogni mese)
{tab(fin6, [lambda r: r.nome.replace('finestra_', ''), lambda r: f'{r.inizio} → {r.fine}', lambda r: pc(r.rendimento_netto), lambda r: pc(r.ftse_tr_netto), lambda r: pc(r.eccesso_ftse_tr), lambda r: 'n.d.' if pd.isna(r.percentile_casuali) else f'{r.percentile_casuali:.1f}'], ['Partenza', 'Finestra', 'Netto', 'FTSE MIB div.', 'Eccesso', 'Percentile'])}
Rendimento netto: mediana {pc(fin6.rendimento_netto.median())}, peggiore {pc(fin6.rendimento_netto.min())}. Eccesso sul FTSE MIB con dividendi: mediana {pc(fin6.eccesso_ftse_tr.median())}, peggiore {pc(fin6.eccesso_ftse_tr.min())}. Le cinque finestre iniziate tra settembre e gennaio battono il FTSE MIB (le prime tre stanno interamente nel periodo di scelta, le altre due includono mesi di verifica); le quattro iniziate da febbraio in poi no. Una nuova partenza da febbraio 2026 in poi non avrebbe battuto il FTSE MIB con dividendi.

## 6. Grafico dell'intero periodo
`risultati/patrimonio_intero_periodo.png`: patrimonio netto delle due finaliste, mediana e banda 5°–95° delle 500 casuali della Finalista 2 e FTSE MIB con dividendi stimati, 29/8/2025 – 17/11/2026, con la linea verticale al 30/4/2026 tra scelta e verifica. A fine periodo: Finalista 1 {pc(g('finalista1_intero').rendimento_netto)}, Finalista 2 {pc(g('finalista2_intero').rendimento_netto)}, mediana delle casuali {pc(mediana_casuali_intero)}, FTSE MIB con dividendi {pc(g('finalista2_intero').ftse_tr_netto)}. L'ultimo punto di ogni linea è dopo vendita finale, costi e imposte (da qui il salto dell'ultimo giorno).

**Attenzione al percorso**: nella corsa continua, che tiene in portafoglio i titoli scelti prima del 30/4, il patrimonio ha continuato a salire dopo la linea di separazione fino al massimo di {eur(picco[2][1] - 20000)} sul capitale iniziale per la Finalista 2 ({picco[2][0]}) e {eur(picco[1][1] - 20000)} per la Finalista 1 ({picco[1][0]}), poi ha restituito quasi tutto. La verifica richiesta (nuova partenza il 4/5/2026 con 20.000 € in contanti e acquisto dei titoli che il segnale indicava quel giorno) sale molto meno, fino a {vpicco:.0f} € il {vdata} (Finalista 2), e finisce a {vfin:.0f} €: i due modi di guardare la stessa regola dicono che dipende molto da *quali* titoli si hanno in portafoglio quando il vento cambia. Il giudizio resta quello fissato: nuova partenza.

## 7. Limiti
- **Il risultato è negativo e va preso come tale**: la strategia scelta sul periodo 1/9/2025 – 30/4/2026 non ha retto fuori campione. Il guadagno in-sample (circa +39%) era in gran parte selezione tra 379 combinazioni su 8 mesi di rialzo, concentrato su pochi titoli (STMMI, PRY, TPRO).
- Un solo periodo di verifica (6 mesi e mezzo) e un solo regime; i quattro criteri sono duri ma sono quelli fissati prima.
- Termine di confronto: dividendi del FTSE MIB **stimati** con i 40 titoli più capitalizzati noti al 29/8/2025 (pesi fissi) e incassati al 74%; un ETF reale può differire.
- Dati: il 17/11/2026 hanno prezzo 204 titoli su 216 (chiusura parziale); i titoli senza riga mantengono l'ultimo prezzo; lista Tobin 2026 da fonti secondarie; nel mercato pieno compaiono 8 titoli quotati solo dopo il 30/4 (non cambiano i segnali precedenti: verificato da un test).
- La classifica di `segnale_oggi.py` parte da prezzi di oggi e usa un calendario di Borsa stimato per le date future.
- Il filtro di liquidità usa il controvalore medio giornaliero passato; gli ordini reali su titoli poco liquidi potrebbero costare di più dello slittamento simulato.

**Numero di combinazioni provate in tutto lo studio**

| Fase | Combinazioni | Simulazioni (netto + lordo + 500 casuali) |
|---|---|---|
| 2 – termini di confronto | 3 panieri del top-5 (lordo, netto, Tobin) + FTSE MIB + 500 casuali | circa 505 |
| 3 – segnali | 81 (57 segnali×orizzonti + 18 eventi×orizzonti + 6 regime); 57 ripetute con ritardo 0 | analisi, non simulazioni |
| 4 | 168 (96 rotazioni + 72 eventi) | {168 * 502:,} |
| 5 | 177 | {177 * 502:,} |
| 6 | 32 + 2 sensibilità Tobin | {34 * 502:,} |
| 7 | {comb_f7} (strategia × finestra; include la Finalista 2 sull'intero periodo due volte) | {comb_f7 * 502:,} |
| **Totale** | **{81 + 168 + 177 + 34 + comb_f7} combinazioni principali** ({81 + 57 + 168 + 177 + 34 + comb_f7} contando la prova a ritardo 0 della fase 3) | **circa {(168 + 177 + 34 + comb_f7) * 502 + 505:,}** |

## 8. Proposte (separate: non applicate e non verificate)
1. **Non usare la regola con denaro vero.** Continuare la prova sulla carta con `segnale_oggi.py` solo se serve a raccogliere altri dati fuori campione.
2. Prima di qualunque nuova regola, capire perché trend e revisioni si sono ribaltati (vedi diagnosi): ipotesi da testare, per esempio un cambio di regime di mercato dopo febbraio 2026. Servirebbe un nuovo periodo di verifica non toccato: questo è ormai stato usato.
3. Allargare l'universo o i dati storici (prima del 2025) per avere più regimi, invece di aggiungere parametri.
4. Se si riprova, fissare in anticipo un numero molto più piccolo di combinazioni e un criterio che corregga per le prove multiple.

## 9. Strumento per la prova dal vivo
`ricerca/segnale_oggi.py` (con `ricerca/portafoglio_prova.csv` vuoto d'esempio) stampa la classifica COMP, i 6 titoli da tenere, cosa vendere e comprare rispetto al portafoglio e la data del prossimo ribilanciamento. Output sui dati più recenti in `risultati/segnale_oggi_output.txt`.

File dei risultati in `ricerca/risultati/`: `fase7.csv` (ogni voce, KPI completi), `fase7_esito.json`, registri delle operazioni `fase7_*_operazioni.csv` e patrimoni `fase7_*_patrimonio.csv`, `diagnosi_fase7.csv`, grafici `patrimonio_finaliste.png` (periodo di scelta) e `patrimonio_intero_periodo.png`. Riproduzione: `python3 -I ricerca/fase7.py`, poi `python3 -I ricerca/rapporto.py`; test: `python3 -I -m pytest ricerca/test_motore.py -q -p no:cacheprovider` (62 test).
"""
    (QUI / 'RAPPORTO.md').write_text(md)
    print(len(md))


if __name__ == '__main__':
    main()
