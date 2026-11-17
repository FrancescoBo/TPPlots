"""Genera RIASSUNTO_FASE4-6.md dai file in risultati/."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / 'risultati'
f4 = pd.read_csv(R / 'fase4.csv'); f5 = pd.read_csv(R / 'fase5.csv'); f6 = pd.read_csv(R / 'fase6.csv')
e4 = json.load(open(R / 'fase4_esito.json')); fin = json.load(open(R / 'finaliste.json'))
pc = lambda x, d=1: 'n.d.' if pd.isna(x) else f'{100 * x:.{d}f}%'


def etichetta(r):
    if r.famiglia == 'A':
        s = f"A {r.segnale} R{int(r.R)} K{int(r.K)} B{int(r.B)} L{r.L / 1e6:g}M"
    else:
        s = f"B {r.evento} {r.filtro} N{int(r.N)} L{r.L / 1e6:g}M {r.uscita}"
    if 'regole' in r and isinstance(r.get('regole'), str) and r.regole != 'base':
        s += f" +{r.regole}"
    if 'N_blocchi' in r and not pd.isna(r.get('N_blocchi')):
        d = json.loads(r.dim)
        s += f" | N{int(r.N_blocchi)} {'reinvest' if d['reinvest'] else 'fissi'}{' 1/ATR' if d['inv_atr'] else ''}"
    return s


def tabella(df, n=10, fase6=False):
    d = df.copy()
    d['ok'] = d.vincoli_ok.astype(int)
    d = d.sort_values(['ok', 'rendimento_netto'], ascending=[False, False]).head(n)
    righe = ['| # | Combinazione | Netto | Lordo | Eccesso su FTSE MIB div. | Percentile | Max drawdown | Operazioni | Ordini/sett. | Titolo migliore | Vincoli |',
             '|---|---|---|---|---|---|---|---|---|---|---|']
    for k, r in enumerate(d.itertuples(), 1):
        righe.append(f"| {k} | {etichetta(pd.Series(r._asdict()))} | {pc(r.rendimento_netto)} | {pc(r.rendimento_lordo)} | {pc(r.eccesso_ftse_tr)} | "
                     f"{r.percentile_casuali:.1f} | {pc(r.max_drawdown)} | {r.n_operazioni} | {r.ordini_a_settimana:.1f} | {pc(r.quota_titolo_migliore, 0)} | {'sì' if r.vincoli_ok else 'no'} |")
    return '\n'.join(righe)


nonpot = f4[~f4.controllo]
pot = f4[f4.controllo]
n_comb = len(f4) + len(f5) + len(f6)
n_sim = n_comb * (2 + 500)
t1 = pd.read_csv(R / 'finalista1_operazioni.csv'); t2 = pd.read_csv(R / 'finalista2_operazioni.csv')


def conc(t):
    tot = t.risultato_netto.sum()
    top3 = t.risultato_netto.nlargest(3)
    pt = t.groupby('ticker').risultato_netto.sum().sort_values(ascending=False)
    return tot, top3.sum() / tot, pt.index[0], pt.iloc[0] / tot, list(pt.index[:3])


c1, c2 = conc(t1), conc(t2)
sens = f6[f6.sensibilita_tobin04]
base_sens = {int(r.id) - 5000: r for r in sens.itertuples()}
f6n = f6[~f6.sensibilita_tobin04]


def vicini(sid, N):
    g = f6n[(f6n.sorgente_id == sid)]
    out = []
    for r in g.itertuples():
        if json.loads(r.dim) == {'reinvest': True, 'inv_atr': False}:
            out.append(f"N={int(r.N_blocchi)}: {pc(r.rendimento_netto)}")
    return ', '.join(out)


def parola(i, f):
    p = f['params']
    return (f"ogni 21 sedute (alla chiusura, dal 29/8/2025) calcola per ogni titolo con almeno 5 target e almeno {p['L'] / 1e6:g} mln € di controvalore "
            f"giornaliero mediano (60 sedute) la media dei ranghi percentuali (0–1) di momentum a 120 sedute e saldo revisioni a 60 giorni; "
            f"tiene i primi {p['K']} e vende un titolo solo se scende oltre la posizione {p['K'] + p['B']}; gli ordini vanno all'apertura del giorno dopo; "
            f"ogni acquisto vale il patrimonio corrente diviso {p['K']} (reinvestimento); nessuna regola di uscita oltre alla classifica")


md = f"""# Riassunto fasi 4–6 (periodo di scelta, in-sample)

Ultimo dato usato: **2026-04-30**. Nessun calcolo sul periodo dopo questa data (la fase 7 è per un'altra sessione). Periodo simulato: acquisti dall'apertura del 2025-09-01 (segnale alla chiusura del 2025-08-29), liquidazione finale alla chiusura del 2026-04-30, capitale 20.000 €. Seme fisso 20260430.

## 1. Risultato in breve
- **La condizione di arresto dopo la fase 4 non è scattata**: {e4['superano_condizione']} combinazioni su {len(nonpot)} (POT escluso) hanno percentile ≥ 90 contro le proprie 500 strategie casuali **e** eccesso positivo sul FTSE MIB con dividendi stimati ({pc(e4['ftse_tr_netto'])} netto; solo prezzo {pc(e4['ftse_prezzo_netto'])}). {e4['superano_tutti_i_vincoli']} rispettano tutti i vincoli (eccesso > 0, percentile ≥ 90, drawdown ≤ 20%, titolo migliore ≤ 40% del guadagno).
- Le regole di uscita (fase 5) **non migliorano** niente: la migliore per ciascuna base è la sola classifica, senza altre regole. Il dimensionamento (fase 6) con reinvestimento aggiunge qualche punto; il peso ∝ 1/ATR peggiora.
- Il segnale che regge è **COMP** (media dei ranghi di momentum a 120 sedute e saldo revisioni a 60 giorni), in rotazione ogni 21 sedute. Gli eventi (famiglia B) sono più deboli e molto più concentrati (il titolo migliore pesa in media {pc(f4[f4.famiglia == 'B'].quota_titolo_migliore.mean(), 0)} del guadagno contro {pc(f4[f4.famiglia == 'A'].quota_titolo_migliore.mean(), 0)} delle rotazioni).
- **POT (controllo, direzione originale)**: media {pc(pot.rendimento_netto.mean())} netto, migliore {pc(pot.rendimento_netto.max())}, percentile medio {pot.percentile_casuali.mean():.0f}: seguire l'idea iniziale (potenziale alto = comprare) ha perso in tutte le 24 combinazioni.
- **Prudenza**: i rendimenti netti delle finaliste (circa 39%) sono **in-sample, in 8 mesi di forte rialzo, scelti tra {n_comb} combinazioni provate sugli stessi dati**. Il percentile contro il caso non corregge per le prove multiple, quindi parte di questo risultato è fortuna di selezione. Il vero esame è la fase 7.

## 2. Regole applicate (DECISIONI_FASE3)
Tobin 0,1% fino al 31/12/2025 e 0,2% dal 1/1/2026; filtro di liquidità (mediana a 60 sedute di chiusura × volume, solo dati passati) a 1 o 5 mln €; slittamento 0,05% (≥ 5 mln), 0,10% (1–5 mln), 0,20% (sotto 1 mln o ignota), calcolato con la liquidità del giorno prima; 27 righe duplicate di raccomandazioni tolte; FTSE MIB con dividendi stimati (pesi dei 40 titoli più capitalizzati al 29/8, dividendo incassato al 74% come per le azioni, commissione e slittamento 0,05%, niente Tobin, 26% sulla plusvalenza di prezzo): **{pc(BENCH_TR := e4['ftse_tr_netto'])}** netto; solo prezzo **{pc(e4['ftse_prezzo_netto'])}**. Ogni combinazione ha le proprie 500 strategie casuali (stesse date di ingresso, importi, numero di operazioni e regole di prezzo/tempo; uscite per classifica alle stesse date; titoli a caso tra quelli dell'universo che passano lo stesso filtro di liquidità); il percentile è la quota di casuali con rendimento netto inferiore.

## 3. Fase 4 – le 10 migliori ({len(f4)} combinazioni: {e4['famiglia_A']} rotazioni + {e4['famiglia_B']} eventi)
Ordine: vincoli rispettati, poi rendimento netto; POT escluso (è solo un controllo). Etichette: A = rotazione (segnale, R sedute, K blocchi, B margine, L liquidità minima); B = evento, filtro, N blocchi, uscita.

{tabella(nonpot)}

Per segnale (media delle combinazioni): COMP {pc(nonpot[nonpot.segnale == 'COMP'].rendimento_netto.mean())}, MOM {pc(nonpot[nonpot.segnale == 'MOM'].rendimento_netto.mean())}, REV {pc(nonpot[nonpot.segnale == 'REV'].rendimento_netto.mean())}, eventi {pc(nonpot[nonpot.famiglia == 'B'].rendimento_netto.mean())}. Le tre combinazioni portate in fase 5 (vincoli rispettati, vicine in media sopra il FTSE MIB con dividendi, poi rendimento netto) sono tutte COMP con R = 21: {', '.join(str(i) for i in json.load(open(R / 'fase5_esito.json'))['basi'])} (id della tabella `fase4.csv`).

## 4. Fase 5 – uscite ({len(f5)} combinazioni su 3 basi)
{tabella(f5)}

Nessuna delle 177 varianti batte la sola rotazione di più di 0,5 punti (5 sono identiche alla base). Effetto medio sul rendimento netto rispetto alla base, per regola singola: stop 12% −0,1 punti (per due basi su tre non scatta mai), trailing 20% −1,1, tempo massimo 120 sedute −2,6, tempo 60 −4,4, stop 2,5×ATR −8,1, take profit 20% −8,7 (8% −16,1), trailing 12% −14,4, stop 8% −14,5; la regola «prezzo ≥ 0,9 × TP medio» (quella del recap) costa circa −38 punti. I titoli che salgono sono quelli da tenere: ogni uscita anticipata taglia i vincenti. Per scegliere le 2 da portare in fase 6 ho preso la migliore per ciascuna base (a parità entro 0,5 punti, meno regole): in entrambi i casi la rotazione semplice.

## 5. Fase 6 – dimensionamento ({len(f6n)} combinazioni + {len(sens)} prove di sensibilità)
{tabella(f6n)}

Sensibilità Tobin 0,4% dal 2026 (non usata per scegliere): {'; '.join(f"{etichetta(pd.Series(r._asdict()))} {pc(r.rendimento_netto)} (con 0,2%: {pc(f6n[f6n.id == r.id - 5000].rendimento_netto.iloc[0])})" for r in sens.itertuples())}. L'effetto è di circa 0,3 punti: il raddoppio della Tobin pesa poco su strategie con poche operazioni (15–25 in 8 mesi).

## 6. Le due finaliste
Grafico del patrimonio contro FTSE MIB con dividendi e contro la mediana delle loro 500 casuali: `risultati/patrimonio_finaliste.png`. Registri delle operazioni: `risultati/finalista1_operazioni.csv`, `finalista2_operazioni.csv` (patrimonio giornaliero in `finalista*_patrimonio.csv`). L'ultimo punto del grafico è dopo vendita finale, costi e tasse (da qui il calo dell'ultimo giorno).

**Finalista 1** (id {fin['1']['id']}): {parola(1, fin['1'])}. Netto {pc(fin['1']['rendimento_netto'])}, mediana delle sue casuali {pc(fin['1']['mediana_casuali_finale'])}, {fin['1']['n_operazioni']} operazioni, **{fin['1']['ordini_a_settimana']:.1f} ordini a settimana**. Tre trade migliori = {pc(c1[1], 0)} del guadagno; titolo migliore {c1[2]} = {pc(c1[3], 0)} (limite 40%). Sensibilità al numero di blocchi (reinvestimento): {vicini(10059, 4)}: il risultato cade molto passando da 4 a 5–6 blocchi, quindi è fragile.

**Finalista 2** (id {fin['2']['id']}): {parola(2, fin['2'])}. Netto {pc(fin['2']['rendimento_netto'])}, mediana delle sue casuali {pc(fin['2']['mediana_casuali_finale'])}, {fin['2']['n_operazioni']} operazioni, **{fin['2']['ordini_a_settimana']:.1f} ordini a settimana**. Tre trade migliori = {pc(c2[1], 0)} del guadagno; titolo migliore {c2[2]} = {pc(c2[3], 0)}. Per blocchi: {vicini(10000, 6)}: più stabile della prima.

Le due finaliste usano lo stesso segnale (COMP): tutti i 15 titoli della prima compaiono anche nella seconda (che ne ha 23), quindi non sono due idee indipendenti. Il guadagno è concentrato: per entrambe i tre titoli migliori sono STMMI, PRY e TPRO, e il {pc(c1[0] and 6649/7926, 0)} (finalista 1) e il {pc(5892/7722, 0)} (finalista 2) del guadagno netto viene da operazioni chiuse da marzo 2026 in poi (di cui la liquidazione finale al 30/4); nel grafico il patrimonio sale e scende molto nell'ultimo mese.

## 7. Cautele e dati
- **Prove multiple**: {n_comb} combinazioni distinte (168 + 177 + 32, più 2 di sensibilità), ciascuna con una simulazione netta, una lorda e 500 casuali: circa {n_sim:,} simulazioni. La scelta delle finaliste è un uso dei dati in-sample.
- **Un solo regime** (mercato in rialzo, FTSE MIB sempre sopra la media a 200 sedute) e solo 8 mesi: nulla dice come COMP si comporti in un ribasso.
- Il rendimento di 8 mesi non è annualizzato nelle tabelle; `fase4.csv`, `fase5.csv`, `fase6.csv` hanno anche rendimento annualizzato, Sharpe, Sortino, costi, % vincenti, durata, esposizione.
- Il termine di confronto usa dividendi **stimati** (40 titoli più capitalizzati con azioni note; quanto realmente incassato da un ETF può differire).
- Tobin: lista di esenti da fonti secondarie (vedi riassunto fase 3). Mi sono tenuto alle aliquote del file decisioni.
- I file `fase3_*`, `RIASSUNTO_FASE3.md` e `fase2*` sono quelli della sessione precedente (prima di liquidità, duplicati e Tobin 0,2%) e non sono stati rigenerati; `fase2.py` va usato solo con il motore di allora.
- Scelte mie dove il testo lascia margine: percentile = quota di casuali con rendimento netto inferiore; parità di rango risolta dal titolo più liquido; blocchi non rimpiazzati tra due ribilanciamenti restano vuoti; peso ∝ 1/ATR limitato tra 0,5 e 1,5 volte il blocco; «vicine» = un parametro spostato di un passo; stima delle uscite per classifica nelle casuali = stessa data di uscita.
- Riproduzione: `python3 -I ricerca/esperimenti.py fase4|fase5|fase6|finali`, poi `python3 -I ricerca/riassunto46.py`; test: `python3 -I -m pytest ricerca/test_motore.py -q -p no:cacheprovider` (56 test).
"""
(Path(__file__).resolve().parent / 'RIASSUNTO_FASE4-6.md').write_text(md)
print(len(md))
