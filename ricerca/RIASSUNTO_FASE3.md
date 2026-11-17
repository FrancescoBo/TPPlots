# Riassunto fase 3: potere predittivo dei segnali (in-sample)

Ultimo dato usato: **2026-04-30** (nessun calcolo e nessuna osservazione oltre questa data, rendimenti futuri compresi: sono NaN se la finestra la supera). Periodo di valutazione dei segnali: 2025-09-01 – 2026-04-30 (rilevato su 167 sedute; il periodo di riscaldamento 2025-01-02 – 2025-08-31 serve solo a costruire i segnali). Fuori campione: non toccato. Seme fisso: 20260430. Nessuna strategia costruita.

## 1. Come sono misurati i segnali
- Rendimento futuro a h = 5/20/60 sedute: acquisto all'apertura di t+1, vendita alla chiusura di t+h, più i dividendi lordi con stacco in [t+2, t+h]. Segnale calcolato alla chiusura di t.
- Per ogni giorno e variabile: correlazione di rango (Spearman) tra segnale e rendimento futuro tra i titoli dell'universo (almeno 20 titoli); IC medio = media dei giorni. «Mesi stesso segno» = quota dei mesi (almeno 5 giorni validi) con IC dello stesso segno della media. t mensile = t-statistica sulle medie mensili (non sui giorni, che si sovrappongono).
- Quintili: media per giorno dei rendimenti dei 5 gruppi (Q1 segnale più basso), poi media sui giorni. Tutti i valori sono nei CSV (quintili Q1..Q5, anche Q5−Q1 sulla mediana).
- Eventi: rendimento medio dei titoli con l'evento meno la media dell'universo nello stesso giorno, poi media sui giorni con evento.
- Universo: titoli con almeno 5 target validi negli ultimi 120 giorni e prezzo disponibile: 67 titoli al 2025-08-29, 80 al 2025-12-30, 101 distinti in totale nel periodo.

## 2. Variabili ordinate per stabilità dell'effetto
Ordine: media su 5/20/60 sedute della quota di mesi con lo stesso segno, a parità |IC| medio. IC = correlazione di rango media.

| # | Variabile | IC 5 | IC 20 | IC 60 | Mesi stesso segno 5/20/60 | t mensile 20 | Q5−Q1 a 20 | Segno |
|---|---|---|---|---|---|---|---|---|
| 1 | n_target | +0.047 | +0.086 | +0.099 | 0.75 / 1.00 / 1.00 | +3.95 | 2.4% | + |
| 2 | momentum_120 | +0.044 | +0.077 | +0.122 | 0.75 / 0.86 / 1.00 | +2.82 | 3.6% | + |
| 3 | saldo_rev_60 | +0.027 | +0.049 | +0.142 | 0.75 / 0.86 / 1.00 | +1.31 | 3.0% | + |
| 4 | dispersione_target | -0.030 | -0.038 | -0.098 | 0.62 / 0.71 / 1.00 | -1.32 | -0.5% | − |
| 5 | saldo_rev_60_norm | +0.013 | +0.027 | +0.110 | 0.62 / 0.86 / 0.80 | +0.78 | 2.3% | + |
| 6 | potenziale | -0.035 | -0.068 | -0.145 | 0.75 / 0.71 / 0.80 | -1.08 | -2.9% | − |
| 7 | dist_tp_meno10 | +0.035 | +0.068 | +0.145 | 0.75 / 0.71 / 0.80 | +1.08 | 2.8% | + |
| 8 | saldo_rev_30 | +0.022 | +0.033 | +0.077 | 0.75 / 0.71 / 0.80 | +0.93 | 2.1% | + |
| 9 | ritracciamento_60 | +0.033 | +0.055 | +0.155 | 0.62 / 0.57 / 1.00 | +0.77 | 3.0% | + |
| 10 | rev_tp_90 | +0.031 | +0.065 | +0.074 | 0.88 / 0.71 / 0.60 | +1.65 | 1.5% | + |
| 11 | rev_tp_60 | +0.009 | +0.029 | +0.069 | 0.62 / 0.71 / 0.80 | +0.76 | 0.9% | + |
| 12 | saldo_rev_30_norm | +0.016 | +0.028 | +0.057 | 0.62 / 0.71 / 0.80 | +0.90 | 1.8% | + |
| 13 | momentum_60 | +0.006 | +0.028 | +0.115 | 0.50 / 0.57 / 1.00 | +0.71 | 2.1% | + |
| 14 | atr_14_pct | -0.039 | -0.044 | -0.166 | 0.62 / 0.43 / 1.00 | -0.67 | -1.0% | − |
| 15 | delta_quota_positivi_60 | -0.035 | -0.052 | -0.077 | 0.88 / 0.57 / 0.60 | -1.24 | -0.7% | − |
| 16 | capitalizzazione_mld | +0.041 | +0.065 | +0.088 | 0.62 / 0.57 / 0.80 | +1.48 | 1.4% | + |
| 17 | momentum_20 | +0.032 | +0.039 | +0.026 | 0.75 / 0.57 / 0.60 | +0.92 | 2.3% | + |
| 18 | quota_positivi | -0.006 | +0.007 | +0.016 | 0.50 / 0.57 / 0.60 | +0.28 | -0.1% | + |
| 19 | rev_tp_30 | +0.006 | +0.011 | +0.039 | 0.38 / 0.43 / 0.40 | +0.34 | 0.6% | + |

Eventi (confronto con l'universo dello stesso giorno):

| Evento | Orizzonte | N eventi | N titoli | Eccesso vs universo | t mensile | Mesi stesso segno |
|---|---|---|---|---|---|---|
| verso_buy | 5 | 55 | 34 | -0.98% | -1.44 | 0.71 |
| verso_buy | 20 | 45 | 30 | -2.41% | -3.01 | 0.83 |
| verso_buy | 60 | 30 | 21 | -2.56% | -1.42 | 0.75 |
| alzata_5 | 5 | 556 | 79 | 0.40% | +1.97 | 0.88 |
| alzata_5 | 20 | 504 | 77 | 1.38% | +2.48 | 0.86 |
| alzata_5 | 60 | 364 | 67 | 2.47% | +2.21 | 0.80 |
| alzata_10 | 5 | 364 | 71 | 0.51% | +1.46 | 0.88 |
| alzata_10 | 20 | 327 | 71 | 1.78% | +1.45 | 0.86 |
| alzata_10 | 60 | 226 | 59 | 1.55% | +0.60 | 0.60 |
| alzata_20 | 5 | 171 | 52 | 1.23% | +3.73 | 0.75 |
| alzata_20 | 20 | 147 | 51 | 2.17% | +2.08 | 0.86 |
| alzata_20 | 60 | 97 | 44 | 1.52% | +0.02 | 0.60 |
| due_alzate_5g | 5 | 188 | 67 | -0.18% | -0.60 | 0.75 |
| due_alzate_5g | 20 | 176 | 67 | 0.77% | +0.35 | 0.86 |
| due_alzate_5g | 60 | 116 | 53 | 1.95% | +1.38 | 0.80 |
| due_alzate_10g | 5 | 210 | 68 | 0.64% | +3.25 | 0.88 |
| due_alzate_10g | 20 | 197 | 68 | 0.66% | +0.38 | 0.57 |
| due_alzate_10g | 60 | 137 | 56 | 2.09% | +0.39 | 0.60 |

Regime di mercato (FTSE MIB sopra/sotto la media a 200 sedute):

| Orizzonte | Stato | Giorni | Rend. medio universo |
|---|---|---|---|
| 5 | sopra_media200 | 130 | 0.23% |
| 5 | sotto_media200 | 1 | 3.80% |
| 20 | sopra_media200 | 115 | 0.97% |
| 20 | sotto_media200 | 1 | 15.60% |
| 60 | sopra_media200 | 76 | 2.49% |
| 60 | sotto_media200 | 0 | n.d. |

Il regime non è valutabile: in tutto il periodo il FTSE MIB è sopra la media a 200 sedute tranne 1 giorno (135 giorni sopra). Con un solo giorno «sotto» qualunque confronto è privo di significato.

## 3. Le 3–4 variabili che terrei per la fase 4 e perché
1. **Saldo revisioni a 60 giorni (`saldo_rev_60`)**: IC +0.027 / +0.049 / +0.142 a 5/20/60 sedute, quota di mesi con lo stesso segno 0.75 / 0.86 / 1.00; Q5−Q1 a 60 sedute 9.0%. Segno coerente con l'ipotesi (più rialzi di target che ribassi → rendimenti migliori), effetto crescente con l'orizzonte, e identico con ritardo 0. La versione normalizzata e quella a 30 giorni vanno nella stessa direzione ma sono più deboli: ne basta una.
2. **Momentum a 120 sedute (`momentum_120`)**: IC +0.044 / +0.077 / +0.122, mesi stesso segno 0.75 / 0.86 / 1.00. È l'unica variabile di prezzo stabile su tutti e tre gli orizzonti (momentum a 20 e 60 sedute meno). Non dipende dai target. Attenzione: correla 0.58 con `saldo_rev_60`, quindi le due non sono indipendenti.
3. **Potenziale (`potenziale`), con segno invertito**: nel periodo il potenziale alto ha reso MENO: IC -0.035 / -0.068 / -0.145, mesi stesso segno 0.75 / 0.71 / 0.80; Q5−Q1 a 60 sedute -6.5%. È la variabile centrale del progetto, quindi la tengo come ipotesi da verificare fuori campione, ma NON nella direzione attesa. Correla -0.67 con il momentum a 120 sedute: un potenziale alto è spesso un prezzo sceso, quindi l'effetto potrebbe essere momentum rovesciato e non un'informazione dei target. `dist_tp_meno10` è esattamente la stessa informazione (correlazione −1,00): non va usata come variabile a parte.
4. **Evento «target alzato ≥ 5% da un emittente» (`alzata_5`)**: eccesso sull'universo 0.40% / 1.38% / 2.47% a 5/20/60 sedute, con 504 eventi su 77 titoli e quota di mesi con lo stesso segno 0,80–0,88. È l'unico evento stabile e con numerosità decente; le soglie 10% e 20% hanno meno eventi e meno stabilità.

Scartate, con il motivo: `n_target` e `capitalizzazione_mld` (correlazione fra loro 0.76: sono un proxy di dimensione/liquidità; `n_target` è stabile a 20 e 60 sedute ma in questa finestra significa solo «le società più grandi sono andate meglio»); `atr_14_pct` (stabile solo a 60 sedute, instabile a 20); `ritracciamento_60` (stabile solo a 60 sedute e correlato 0.69 con il momentum a 60); `verso_buy` (rendimento inferiore all'universo, t mensile -3.01 a 20 sedute, ma solo 45 eventi); `quota_positivi`, `rev_tp_30` (nessun effetto leggibile).

**Cautele che pesano su tutta la lista.** (a) In pratica 8 mesi: per l'orizzonte a 60 sedute i mesi utilizzabili sono 5 e le finestre si sovrappongono, quindi gli IC a 60 sedute (i più alti) sono i meno affidabili. (b) Il mercato è salito per tutto il periodo (regime sempre «sopra»): non sappiamo nulla di come si comportino i segnali in un ribasso. (c) Sono state guardate 81 combinazioni (vedi sotto): con tante prove qualcuna risulta «stabile» per caso, e la scelta qui sopra è già un uso dei dati in-sample. (d) Nessuna di queste statistiche è un rendimento ottenibile: non tengono conto di costi, Tobin, slittamento e tasse.

## 4. Problemi nei dati
- **Target fuori da 0,3–3 volte il prezzo**: 8 righe escluse e non usate: PMT 2025-08-04 (target 7.5, prezzo 2.12, rapporto 3.538); PRE 2025-03-12 (target 1.9, prezzo 0.502, rapporto 3.785); PRO 2026-04-14 (target 0.35, prezzo 1.75, rapporto 0.2); SIAV 2025-05-07 (target 6.3, prezzo 2.04, rapporto 3.088); SIAV 2025-04-23 (target 6.3, prezzo 1.79, rapporto 3.52); TFIN 2025-10-31 (target 0.42, prezzo 8.74, rapporto 0.048); TFIN 2025-08-11 (target 0.6, prezzo 8.44, rapporto 0.071); YKY 2025-03-20 (target 3.75, prezzo 1.0, rapporto 3.75). Per PRO e TFIN il rapporto è probabilmente alterato da frazionamenti/raggruppamenti non riflessi nei prezzi; SIAV 2026-03-30 (rapporto esattamente 3,00) è tenuta: il confronto è «fuori da 0,3–3», e 3,00 è dentro (corretto un errore di arrotondamento in virgola mobile che la escludeva). Dopo le esclusioni le variazioni (su/giù) sono ricalcolate.
- **Titoli senza prezzi** (15): AIM2, AIW, ALA, ALMS, AV, BPSO, DAL, DGV, ETI, ILTY, OPTS, RWY, TIME, TITR, TNXT. Hanno 44 righe di raccomandazione, ignorate.
- **EXO**: 3 righe di prezzo in giorni di chiusura di Milano (2025-08-15, 2025-12-24, 2025-12-31): la serie sembra quella di Amsterdam; le righe fuori calendario sono scartate.
- **Emittenti anomali**: 37 emittenti distinti. 178 righe senza classe di giudizio e 209 senza target; 27 righe duplicate (stesso titolo, data, emittente, giudizio e target) che non vengono tolte (effetto sui segnali non verificato).
- **Azioni in circolazione mancanti**: 90 titoli su 213 con prezzi non hanno il numero di azioni: la capitalizzazione è ignota (slittamento al 0,20% nel simulatore, `capitalizzazione_mld` mancante nella variabile).
- **Rendimenti giornalieri oltre ±40%**: UBA 2025-01-06 +49%; ESTM 2025-02-18 +43%; EGLA 2025-07-28 +53%; AEF 2025-10-03 -43%; BFF 2026-02-02 -44%; EGLA 2026-02-16 -59%; TISG 2026-03-16 -47%; BFF 2026-03-30 -55%. Potrebbero essere reali (titoli piccoli) o operazioni societarie non corrette; non sono stati toccati. Gli IC (ranghi) sono robusti, le medie per quintile no: per questo ci sono anche le mediane nel CSV.
- **Giorni senza negoziazione**: quota di celle dell'universo senza prezzo/volume 0.0057% (trascurabile).
- **Regime**: un solo giorno sotto la media (vedi sopra).
- **Tobin**: il piano usa lo 0,1%, ma dal 1/1/2026 l'aliquota reale sui titoli italiani è lo 0,2%. L'opzione `tobin_dal_2026=0.002` è nel motore; nelle prove della fase 2 non cambia nulla perché tutti gli acquisti sono del 2025-09-01. `tobin_esenti.csv` (250 righe, 140 titoli) è costruito da liste MEF trascritte da fonti secondarie (il sito MEF non era raggiungibile): affidabilità segnata per riga. REVO e WIIT risultano appena sotto i 500 milioni ma non sono nelle liste: li lascio non esenti, come da lista. ARIS è esente per sede estera con affidabilità «bassa».
- **Indice**: il FTSE MIB è un indice di prezzo, senza dividendi.

## 5. Fase 2: buy-and-hold (2025-09-01 apertura → 2026-04-30 chiusura)
Ingresso all'apertura del 2025-09-01 con segnale alla chiusura del 2025-08-29 (universo di 67 titoli).

| Strategia | Lordo | Netto di costi e tasse |
|---|---|---|
| FTSE MIB (un ordine da 20.000 €) | 13.85% (solo prezzo) | 9.74% (commissioni 108.12 €, tasse 684.19 €) |
| 5 titoli con potenziale più alto (4.000 € ciascuno): FILA (47%), ICOS (42%), GVS (40%), REY (35%), WIIT (34%) | 7.87% | 4.98% (commissioni 127.36 €, Tobin 15.86 €, slittamento 59.61 €, tasse 303.35 €; max drawdown -11.8%) |
| 5 titoli a caso dall'universo (500 ripetizioni, seme fisso) | — | media 7.84%, mediana 6.66%, 5°–95° percentile -11.7% / 29.5% |

- I 5 titoli sono al **44° percentile** tra i casuali: non si distinguono dal caso. Il risultato dipende da un solo titolo (WIIT: +2.043 € netti su 4.000 €) e dalla perdita di REY; il confronto con 5 titoli ha un'enorme variabilità (90% dei casuali tra −12% e +29%).
- Il FTSE MIB (+13,8% di solo prezzo, +9,7% netto, a cui vanno aggiunti dividendi per circa il 2.4% lordo, stima grezza con i 40 titoli più capitalizzati noti) ha battuto sia i 5 titoli sia la media dei casuali: nel periodo l'universo dei titoli con target ha reso meno dell'indice. Il FTSE MIB è modellato con quote frazionarie (l'indice vale oltre 40.000 punti), commissione del piano, slittamento 0,05% e senza Tobin; ETF o future reali avrebbero costi diversi.
- Ordine delle vendite: tutte alla liquidazione finale; la tassa totale (303,35 €) è uguale a 26% del guadagno netto complessivo perché le minusvalenze (GVS, REY) compensano WIIT.
- Il generatore di strategie casuali è in `strategie.py` (`StrategiaCasuale`, `ripeti_casuale`): stesse date di ingresso, stesso numero di operazioni, stesse uscite, titoli casuali dell'universo non in portafoglio, 500 ripetizioni, seme 20260430. Da usare dalla fase 4.

## 6. Quante combinazioni sono state calcolate
- Segnali continui: 19 varianti (le 12 variabili con le finestre e le versioni normalizzate) × 3 orizzonti = 57.
- Eventi: 6 eventi × 3 orizzonti = 18.
- Regime: 6 (2 stati × 3 orizzonti).
- Prova di robustezza con ritardo 0 (invece di 1 seduta) ripetuta sui 57 segnali continui: IC quasi identici (colonna `ic_medio_ritardo0`).
- In tutto, **81** combinazioni principali (138 con la prova a ritardo 0), più 3 simulazioni del paniere e 500 casuali in fase 2. Nessun parametro è stato ottimizzato: le finestre sono quelle del piano.

## 7. Scelte di interpretazione da conoscere
- Ritardo: una raccomandazione datata t entra nei segnali dalla prima seduta **successiva** a t (RITARDO=1); la variante con ritardo 0 è in `fase3_segnali.csv`.
- Revisione del consenso: richiede almeno 3 target al giorno di riferimento (mia scelta: con meno, il rapporto è troppo instabile).
- Universo del piano (~68 e ~87): coincide con il conteggio per righe (66 e 85 osservati), non per emittenti distinti.
- Regime: confronto di serie storica di mercato (non per titolo).
- File: `fase3_segnali.csv`, `fase3_eventi.csv` (richiesti), più `fase3_regime.csv`, `fase3_correlazioni.csv`, `qualita.json`, `fase2.json`, `fase2_casuali_rendimenti.csv`, `fase2_top5_operazioni.csv`.
- Riproduzione dal repository: `python3 -I ricerca/fase2.py`, `ricerca/fase3.py`, `ricerca/qualita.py`, `ricerca/riassunto.py`; test: `python3 -I -m pytest ricerca/test_motore.py -q -p no:cacheprovider`.
