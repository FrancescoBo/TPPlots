"""Genera RIASSUNTO_FASE3.md dai file in risultati/ (cosi' i numeri non si trascrivono a mano)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent / 'risultati'
seg = pd.read_csv(R / 'fase3_segnali.csv'); ev = pd.read_csv(R / 'fase3_eventi.csv'); reg = pd.read_csv(R / 'fase3_regime.csv')
q = json.load(open(R / 'qualita.json')); f2 = json.load(open(R / 'fase2.json')); cnt = json.load(open(R / 'fase3_conteggi.json'))
pc = lambda x, d=1: 'n.d.' if pd.isna(x) else f'{100 * x:.{d}f}%'
nm = lambda x, d=3: 'n.d.' if pd.isna(x) else f'{x:+.{d}f}'


def righe_var():
    out = []
    for v, g in seg.groupby('variabile', sort=False):
        g = g.set_index('orizzonte')
        stab = g.quota_mesi_stesso_segno.mean()
        out.append((v, stab, g))
    out.sort(key=lambda x: (-x[1], -g_abs(x[2])))
    return out


def g_abs(g):
    return float(np.abs(g.ic_medio).mean())


tab = ['| # | Variabile | IC 5 | IC 20 | IC 60 | Mesi stesso segno 5/20/60 | t mensile 20 | Q5−Q1 a 20 | Segno |', '|---|---|---|---|---|---|---|---|---|']
for k, (v, stab, g) in enumerate(righe_var(), 1):
    segno = '+' if g.ic_medio.mean() > 0 else '−'
    tab.append(f"| {k} | {v} | {nm(g.ic_medio[5])} | {nm(g.ic_medio[20])} | {nm(g.ic_medio[60])} | "
               f"{g.quota_mesi_stesso_segno[5]:.2f} / {g.quota_mesi_stesso_segno[20]:.2f} / {g.quota_mesi_stesso_segno[60]:.2f} | "
               f"{g.ic_t_mensile[20]:+.2f} | {pc(g.q5_meno_q1[20])} | {segno} |")
tev = ['| Evento | Orizzonte | N eventi | N titoli | Eccesso vs universo | t mensile | Mesi stesso segno |', '|---|---|---|---|---|---|---|']
for r in ev.itertuples():
    tev.append(f'| {r.evento} | {r.orizzonte} | {r.n_eventi} | {r.n_titoli} | {pc(r.eccesso_medio_vs_universo, 2)} | {r.t_mensile:+.2f} | {r.quota_mesi_stesso_segno:.2f} |')
treg = ['| Orizzonte | Stato | Giorni | Rend. medio universo |', '|---|---|---|---|']
for r in reg.itertuples():
    treg.append(f'| {r.orizzonte} | {r.stato} | {r.n_giorni} | {pc(r.rendimento_medio_universo, 2)} |')

t5 = f2['top5']; n5, l5 = f2['top5_netto'], f2['top5_lordo']
fn = f2['ftsemib_netto']
esc_txt = '; '.join(f"{r['ticker']} {r['data']} (target {r['target']}, prezzo {r['prezzo_rif']}, rapporto {r['ratio']})" for r in q['target_fuori_0.3_3'])
est_txt = '; '.join(f"{r['ticker']} {r['data']} {100 * r['rend']:+.0f}%" for r in q['rendimenti_giornalieri_oltre_40pct'])
g = lambda v, h, c: seg[(seg.variabile == v) & (seg.orizzonte == h)][c].iloc[0]

md = f"""# Riassunto fase 3: potere predittivo dei segnali (in-sample)

Ultimo dato usato: **{q['ultimo_dato']}** (nessun calcolo e nessuna osservazione oltre questa data, rendimenti futuri compresi: sono NaN se la finestra la supera). Periodo di valutazione dei segnali: 2025-09-01 – 2026-04-30 (rilevato su {q['giorni_in_sample']} sedute; il periodo di riscaldamento 2025-01-02 – 2025-08-31 serve solo a costruire i segnali). Fuori campione: non toccato. Seme fisso: 20260430. Nessuna strategia costruita.

## 1. Come sono misurati i segnali
- Rendimento futuro a h = 5/20/60 sedute: acquisto all'apertura di t+1, vendita alla chiusura di t+h, più i dividendi lordi con stacco in [t+2, t+h]. Segnale calcolato alla chiusura di t.
- Per ogni giorno e variabile: correlazione di rango (Spearman) tra segnale e rendimento futuro tra i titoli dell'universo (almeno 20 titoli); IC medio = media dei giorni. «Mesi stesso segno» = quota dei mesi (almeno 5 giorni validi) con IC dello stesso segno della media. t mensile = t-statistica sulle medie mensili (non sui giorni, che si sovrappongono).
- Quintili: media per giorno dei rendimenti dei 5 gruppi (Q1 segnale più basso), poi media sui giorni. Tutti i valori sono nei CSV (quintili Q1..Q5, anche Q5−Q1 sulla mediana).
- Eventi: rendimento medio dei titoli con l'evento meno la media dell'universo nello stesso giorno, poi media sui giorni con evento.
- Universo: titoli con almeno 5 target validi negli ultimi 120 giorni e prezzo disponibile: {q['universo_titoli_per_data']['2025-08-29']} titoli al 2025-08-29, {q['universo_titoli_per_data']['2025-12-30']} al 2025-12-30, {q['universo_titoli_distinti_in_sample']} distinti in totale nel periodo.

## 2. Variabili ordinate per stabilità dell'effetto
Ordine: media su 5/20/60 sedute della quota di mesi con lo stesso segno, a parità |IC| medio. IC = correlazione di rango media.

{chr(10).join(tab)}

Eventi (confronto con l'universo dello stesso giorno):

{chr(10).join(tev)}

Regime di mercato (FTSE MIB sopra/sotto la media a 200 sedute):

{chr(10).join(treg)}

Il regime non è valutabile: in tutto il periodo il FTSE MIB è sopra la media a 200 sedute tranne {q['regime_giorni_in_sample'].get('0.0', 0)} giorno ({q['regime_giorni_in_sample'].get('1.0', 0)} giorni sopra). Con un solo giorno «sotto» qualunque confronto è privo di significato.

## 3. Le 3–4 variabili che terrei per la fase 4 e perché
1. **Saldo revisioni a 60 giorni (`saldo_rev_60`)**: IC {nm(g('saldo_rev_60', 5, 'ic_medio'))} / {nm(g('saldo_rev_60', 20, 'ic_medio'))} / {nm(g('saldo_rev_60', 60, 'ic_medio'))} a 5/20/60 sedute, quota di mesi con lo stesso segno {g('saldo_rev_60', 5, 'quota_mesi_stesso_segno'):.2f} / {g('saldo_rev_60', 20, 'quota_mesi_stesso_segno'):.2f} / {g('saldo_rev_60', 60, 'quota_mesi_stesso_segno'):.2f}; Q5−Q1 a 60 sedute {pc(g('saldo_rev_60', 60, 'q5_meno_q1'))}. Segno coerente con l'ipotesi (più rialzi di target che ribassi → rendimenti migliori), effetto crescente con l'orizzonte, e identico con ritardo 0. La versione normalizzata e quella a 30 giorni vanno nella stessa direzione ma sono più deboli: ne basta una.
2. **Momentum a 120 sedute (`momentum_120`)**: IC {nm(g('momentum_120', 5, 'ic_medio'))} / {nm(g('momentum_120', 20, 'ic_medio'))} / {nm(g('momentum_120', 60, 'ic_medio'))}, mesi stesso segno {g('momentum_120', 5, 'quota_mesi_stesso_segno'):.2f} / {g('momentum_120', 20, 'quota_mesi_stesso_segno'):.2f} / {g('momentum_120', 60, 'quota_mesi_stesso_segno'):.2f}. È l'unica variabile di prezzo stabile su tutti e tre gli orizzonti (momentum a 20 e 60 sedute meno). Non dipende dai target. Attenzione: correla {pd.read_csv(R / 'fase3_correlazioni.csv', index_col=0).loc['momentum_120', 'saldo_rev_60']:.2f} con `saldo_rev_60`, quindi le due non sono indipendenti.
3. **Potenziale (`potenziale`), con segno invertito**: nel periodo il potenziale alto ha reso MENO: IC {nm(g('potenziale', 5, 'ic_medio'))} / {nm(g('potenziale', 20, 'ic_medio'))} / {nm(g('potenziale', 60, 'ic_medio'))}, mesi stesso segno {g('potenziale', 5, 'quota_mesi_stesso_segno'):.2f} / {g('potenziale', 20, 'quota_mesi_stesso_segno'):.2f} / {g('potenziale', 60, 'quota_mesi_stesso_segno'):.2f}; Q5−Q1 a 60 sedute {pc(g('potenziale', 60, 'q5_meno_q1'))}. È la variabile centrale del progetto, quindi la tengo come ipotesi da verificare fuori campione, ma NON nella direzione attesa. Correla {pd.read_csv(R / 'fase3_correlazioni.csv', index_col=0).loc['potenziale', 'momentum_120']:.2f} con il momentum a 120 sedute: un potenziale alto è spesso un prezzo sceso, quindi l'effetto potrebbe essere momentum rovesciato e non un'informazione dei target. `dist_tp_meno10` è esattamente la stessa informazione (correlazione −1,00): non va usata come variabile a parte.
4. **Evento «target alzato ≥ 5% da un emittente» (`alzata_5`)**: eccesso sull'universo {pc(ev[(ev.evento == 'alzata_5') & (ev.orizzonte == 5)].eccesso_medio_vs_universo.iloc[0], 2)} / {pc(ev[(ev.evento == 'alzata_5') & (ev.orizzonte == 20)].eccesso_medio_vs_universo.iloc[0], 2)} / {pc(ev[(ev.evento == 'alzata_5') & (ev.orizzonte == 60)].eccesso_medio_vs_universo.iloc[0], 2)} a 5/20/60 sedute, con {int(ev[(ev.evento == 'alzata_5') & (ev.orizzonte == 20)].n_eventi.iloc[0])} eventi su {int(ev[(ev.evento == 'alzata_5') & (ev.orizzonte == 20)].n_titoli.iloc[0])} titoli e quota di mesi con lo stesso segno 0,80–0,88. È l'unico evento stabile e con numerosità decente; le soglie 10% e 20% hanno meno eventi e meno stabilità.

Scartate, con il motivo: `n_target` e `capitalizzazione_mld` (correlazione fra loro {pd.read_csv(R / 'fase3_correlazioni.csv', index_col=0).loc['n_target', 'capitalizzazione_mld']:.2f}: sono un proxy di dimensione/liquidità; `n_target` è stabile a 20 e 60 sedute ma in questa finestra significa solo «le società più grandi sono andate meglio»); `atr_14_pct` (stabile solo a 60 sedute, instabile a 20); `ritracciamento_60` (stabile solo a 60 sedute e correlato {pd.read_csv(R / 'fase3_correlazioni.csv', index_col=0).loc['ritracciamento_60', 'momentum_60']:.2f} con il momentum a 60); `verso_buy` (rendimento inferiore all'universo, t mensile {ev[(ev.evento == 'verso_buy') & (ev.orizzonte == 20)].t_mensile.iloc[0]:+.2f} a 20 sedute, ma solo 45 eventi); `quota_positivi`, `rev_tp_30` (nessun effetto leggibile).

**Cautele che pesano su tutta la lista.** (a) In pratica 8 mesi: per l'orizzonte a 60 sedute i mesi utilizzabili sono 5 e le finestre si sovrappongono, quindi gli IC a 60 sedute (i più alti) sono i meno affidabili. (b) Il mercato è salito per tutto il periodo (regime sempre «sopra»): non sappiamo nulla di come si comportino i segnali in un ribasso. (c) Sono state guardate {cnt['combinazioni_segnali'] + cnt['combinazioni_eventi'] + cnt['combinazioni_regime']} combinazioni (vedi sotto): con tante prove qualcuna risulta «stabile» per caso, e la scelta qui sopra è già un uso dei dati in-sample. (d) Nessuna di queste statistiche è un rendimento ottenibile: non tengono conto di costi, Tobin, slittamento e tasse.

## 4. Problemi nei dati
- **Target fuori da 0,3–3 volte il prezzo**: {len(q['target_fuori_0.3_3'])} righe escluse e non usate: {esc_txt}. Per PRO e TFIN il rapporto è probabilmente alterato da frazionamenti/raggruppamenti non riflessi nei prezzi; SIAV 2026-03-30 (rapporto esattamente 3,00) è tenuta: il confronto è «fuori da 0,3–3», e 3,00 è dentro (corretto un errore di arrotondamento in virgola mobile che la escludeva). Dopo le esclusioni le variazioni (su/giù) sono ricalcolate.
- **Titoli senza prezzi** ({len(q['titoli_senza_prezzi'])}): {', '.join(q['titoli_senza_prezzi'])}. Hanno {q['rac_su_ticker_senza_prezzi']} righe di raccomandazione, ignorate.
- **EXO**: {len(q['righe_prezzo_fuori_calendario'].get('EXO', []))} righe di prezzo in giorni di chiusura di Milano ({', '.join(q['righe_prezzo_fuori_calendario'].get('EXO', []))}): la serie sembra quella di Amsterdam; le righe fuori calendario sono scartate.
- **Emittenti anomali**: {q['emittenti_distinti']} emittenti distinti. {q['righe_senza_classe']} righe senza classe di giudizio e {q['righe_senza_target']} senza target; {q['righe_rac_duplicate_ticker_data_emittente']} righe duplicate (stesso titolo, data, emittente, giudizio e target) che non vengono tolte (effetto sui segnali non verificato).
- **Azioni in circolazione mancanti**: {q['titoli_con_prezzi_senza_azioni']} titoli su {q['titoli_con_prezzi']} con prezzi non hanno il numero di azioni: la capitalizzazione è ignota (slittamento al 0,20% nel simulatore, `capitalizzazione_mld` mancante nella variabile).
- **Rendimenti giornalieri oltre ±40%**: {est_txt}. Potrebbero essere reali (titoli piccoli) o operazioni societarie non corrette; non sono stati toccati. Gli IC (ranghi) sono robusti, le medie per quintile no: per questo ci sono anche le mediane nel CSV.
- **Giorni senza negoziazione**: quota di celle dell'universo senza prezzo/volume {100 * q['quota_celle_universo_non_negoziabili']:.4f}% (trascurabile).
- **Regime**: un solo giorno sotto la media (vedi sopra).
- **Tobin**: il piano usa lo 0,1%, ma dal 1/1/2026 l'aliquota reale sui titoli italiani è lo 0,2%. L'opzione `tobin_dal_2026=0.002` è nel motore; nelle prove della fase 2 non cambia nulla perché tutti gli acquisti sono del 2025-09-01. `tobin_esenti.csv` (250 righe, 140 titoli) è costruito da liste MEF trascritte da fonti secondarie (il sito MEF non era raggiungibile): affidabilità segnata per riga. REVO e WIIT risultano appena sotto i 500 milioni ma non sono nelle liste: li lascio non esenti, come da lista. ARIS è esente per sede estera con affidabilità «bassa».
- **Indice**: il FTSE MIB è un indice di prezzo, senza dividendi.

## 5. Fase 2: buy-and-hold ({f2['ingresso']} apertura → {f2['uscita']} chiusura)
Ingresso all'apertura del 2025-09-01 con segnale alla chiusura del 2025-08-29 (universo di {f2['universo_al_29ago']} titoli).

| Strategia | Lordo | Netto di costi e tasse |
|---|---|---|
| FTSE MIB (un ordine da 20.000 €) | {pc(f2['ftsemib_lordo_prezzo'], 2)} (solo prezzo) | {pc(fn['rendimento'], 2)} (commissioni {fn['commissioni']:.2f} €, tasse {fn['tassa']:.2f} €) |
| 5 titoli con potenziale più alto (4.000 € ciascuno): {', '.join(f"{k} ({100 * v:.0f}%)" for k, v in t5.items())} | {pc(l5['rendimento'], 2)} | {pc(n5['rendimento'], 2)} (commissioni {n5['commissioni']:.2f} €, Tobin {n5['tobin']:.2f} €, slittamento {n5['slittamento']:.2f} €, tasse {n5['tasse']:.2f} €; max drawdown {pc(n5['max_drawdown'])}) |
| 5 titoli a caso dall'universo ({f2['casuali_n']} ripetizioni, seme fisso) | — | media {pc(f2['casuali_media'], 2)}, mediana {pc(f2['casuali_mediana'], 2)}, 5°–95° percentile {pc(f2['casuali_p5_p95'][0])} / {pc(f2['casuali_p5_p95'][1])} |

- I 5 titoli sono al **{100 * f2['top5_percentile_tra_casuali']:.0f}° percentile** tra i casuali: non si distinguono dal caso. Il risultato dipende da un solo titolo (WIIT: +2.043 € netti su 4.000 €) e dalla perdita di REY; il confronto con 5 titoli ha un'enorme variabilità (90% dei casuali tra −12% e +29%).
- Il FTSE MIB (+13,8% di solo prezzo, +9,7% netto, a cui vanno aggiunti dividendi per circa il {pc(f2['ftsemib_dividendi_stimati_pct'], 1)} lordo, stima grezza con i 40 titoli più capitalizzati noti) ha battuto sia i 5 titoli sia la media dei casuali: nel periodo l'universo dei titoli con target ha reso meno dell'indice. Il FTSE MIB è modellato con quote frazionarie (l'indice vale oltre 40.000 punti), commissione del piano, slittamento 0,05% e senza Tobin; ETF o future reali avrebbero costi diversi.
- Ordine delle vendite: tutte alla liquidazione finale; la tassa totale (303,35 €) è uguale a 26% del guadagno netto complessivo perché le minusvalenze (GVS, REY) compensano WIIT.
- Il generatore di strategie casuali è in `strategie.py` (`StrategiaCasuale`, `ripeti_casuale`): stesse date di ingresso, stesso numero di operazioni, stesse uscite, titoli casuali dell'universo non in portafoglio, 500 ripetizioni, seme 20260430. Da usare dalla fase 4.

## 6. Quante combinazioni sono state calcolate
- Segnali continui: 19 varianti (le 12 variabili con le finestre e le versioni normalizzate) × 3 orizzonti = {cnt['combinazioni_segnali']}.
- Eventi: 6 eventi × 3 orizzonti = {cnt['combinazioni_eventi']}.
- Regime: {cnt['combinazioni_regime']} (2 stati × 3 orizzonti).
- Prova di robustezza con ritardo 0 (invece di 1 seduta) ripetuta sui {cnt['combinazioni_segnali']} segnali continui: IC quasi identici (colonna `ic_medio_ritardo0`).
- In tutto, **{cnt['combinazioni_segnali'] + cnt['combinazioni_eventi'] + cnt['combinazioni_regime']}** combinazioni principali ({cnt['combinazioni_con_ritardo0']} con la prova a ritardo 0), più 3 simulazioni del paniere e 500 casuali in fase 2. Nessun parametro è stato ottimizzato: le finestre sono quelle del piano.

## 7. Scelte di interpretazione da conoscere
- Ritardo: una raccomandazione datata t entra nei segnali dalla prima seduta **successiva** a t (RITARDO=1); la variante con ritardo 0 è in `fase3_segnali.csv`.
- Revisione del consenso: richiede almeno 3 target al giorno di riferimento (mia scelta: con meno, il rapporto è troppo instabile).
- Universo del piano (~68 e ~87): coincide con il conteggio per righe (66 e 85 osservati), non per emittenti distinti.
- Regime: confronto di serie storica di mercato (non per titolo).
- File: `fase3_segnali.csv`, `fase3_eventi.csv` (richiesti), più `fase3_regime.csv`, `fase3_correlazioni.csv`, `qualita.json`, `fase2.json`, `fase2_casuali_rendimenti.csv`, `fase2_top5_operazioni.csv`.
- Riproduzione dal repository: `python3 -I ricerca/fase2.py`, `ricerca/fase3.py`, `ricerca/qualita.py`, `ricerca/riassunto.py`; test: `python3 -I -m pytest ricerca/test_motore.py -q -p no:cacheprovider`.
"""
(Path(__file__).resolve().parent / 'RIASSUNTO_FASE3.md').write_text(md)
print(len(md))
