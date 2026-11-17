# Riassunto fasi 4–6 (periodo di scelta, in-sample)

Ultimo dato usato: **2026-04-30**. Nessun calcolo sul periodo dopo questa data (la fase 7 è per un'altra sessione). Periodo simulato: acquisti dall'apertura del 2025-09-01 (segnale alla chiusura del 2025-08-29), liquidazione finale alla chiusura del 2026-04-30, capitale 20.000 €. Seme fisso 20260430.

## 1. Risultato in breve
- **La condizione di arresto dopo la fase 4 non è scattata**: 53 combinazioni su 144 (POT escluso) hanno percentile ≥ 90 contro le proprie 500 strategie casuali **e** eccesso positivo sul FTSE MIB con dividendi stimati (11.5% netto; solo prezzo 9.7%). 11 rispettano tutti i vincoli (eccesso > 0, percentile ≥ 90, drawdown ≤ 20%, titolo migliore ≤ 40% del guadagno).
- Le regole di uscita (fase 5) **non migliorano** niente: la migliore per ciascuna base è la sola classifica, senza altre regole. Il dimensionamento (fase 6) con reinvestimento aggiunge qualche punto; il peso ∝ 1/ATR peggiora.
- Il segnale che regge è **COMP** (media dei ranghi di momentum a 120 sedute e saldo revisioni a 60 giorni), in rotazione ogni 21 sedute. Gli eventi (famiglia B) sono più deboli e molto più concentrati (il titolo migliore pesa in media 85% del guadagno contro 61% delle rotazioni).
- **POT (controllo, direzione originale)**: media -15.2% netto, migliore -5.0%, percentile medio 6: seguire l'idea iniziale (potenziale alto = comprare) ha perso in tutte le 24 combinazioni.
- **Prudenza**: i rendimenti netti delle finaliste (circa 39%) sono **in-sample, in 8 mesi di forte rialzo, scelti tra 379 combinazioni provate sugli stessi dati**. Il percentile contro il caso non corregge per le prove multiple, quindi parte di questo risultato è fortuna di selezione. Il vero esame è la fase 7.

## 2. Regole applicate (DECISIONI_FASE3)
Tobin 0,1% fino al 31/12/2025 e 0,2% dal 1/1/2026; filtro di liquidità (mediana a 60 sedute di chiusura × volume, solo dati passati) a 1 o 5 mln €; slittamento 0,05% (≥ 5 mln), 0,10% (1–5 mln), 0,20% (sotto 1 mln o ignota), calcolato con la liquidità del giorno prima; 27 righe duplicate di raccomandazioni tolte; FTSE MIB con dividendi stimati (pesi dei 40 titoli più capitalizzati al 29/8, dividendo incassato al 74% come per le azioni, commissione e slittamento 0,05%, niente Tobin, 26% sulla plusvalenza di prezzo): **11.5%** netto; solo prezzo **9.7%**. Ogni combinazione ha le proprie 500 strategie casuali (stesse date di ingresso, importi, numero di operazioni e regole di prezzo/tempo; uscite per classifica alle stesse date; titoli a caso tra quelli dell'universo che passano lo stesso filtro di liquidità); il percentile è la quota di casuali con rendimento netto inferiore.

## 3. Fase 4 – le 10 migliori (168 combinazioni: 96 rotazioni + 72 eventi)
Ordine: vincoli rispettati, poi rendimento netto; POT escluso (è solo un controllo). Etichette: A = rotazione (segnale, R sedute, K blocchi, B margine, L liquidità minima); B = evento, filtro, N blocchi, uscita.

| # | Combinazione | Netto | Lordo | Eccesso su FTSE MIB div. | Percentile | Max drawdown | Operazioni | Ordini/sett. | Titolo migliore | Vincoli |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A COMP R21 K6 B0 L1M | 36.1% | 52.9% | 24.6% | 100.0 | -9.2% | 25 | 1.5 | 22% | sì |
| 2 | A COMP R21 K4 B4 L5M | 35.7% | 51.7% | 24.2% | 99.6 | -11.2% | 15 | 0.9 | 37% | sì |
| 3 | A COMP R21 K5 B5 L1M | 31.6% | 45.8% | 20.1% | 98.0 | -13.9% | 15 | 0.9 | 33% | sì |
| 4 | A COMP R21 K4 B0 L1M | 31.6% | 47.2% | 20.1% | 99.0 | -11.0% | 20 | 1.2 | 38% | sì |
| 5 | A COMP R21 K5 B0 L1M | 27.4% | 41.2% | 15.9% | 98.8 | -10.1% | 22 | 1.3 | 35% | sì |
| 6 | A COMP R21 K4 B4 L1M | 26.2% | 38.5% | 14.7% | 96.0 | -13.8% | 14 | 0.8 | 26% | sì |
| 7 | A COMP R21 K5 B5 L5M | 26.2% | 39.2% | 14.7% | 98.8 | -10.6% | 15 | 0.9 | 40% | sì |
| 8 | A COMP R21 K6 B0 L5M | 25.4% | 37.9% | 13.9% | 99.0 | -9.3% | 23 | 1.3 | 31% | sì |
| 9 | A COMP R21 K6 B6 L1M | 25.2% | 37.1% | 13.7% | 97.2 | -14.3% | 19 | 1.1 | 35% | sì |
| 10 | A COMP R21 K5 B0 L5M | 24.1% | 36.2% | 12.6% | 98.0 | -9.1% | 20 | 1.2 | 40% | sì |

Per segnale (media delle combinazioni): COMP 24.7%, MOM 17.5%, REV 14.9%, eventi 11.7%. Le tre combinazioni portate in fase 5 (vincoli rispettati, vicine in media sopra il FTSE MIB con dividendi, poi rendimento netto) sono tutte COMP con R = 21: 68, 63, 66 (id della tabella `fase4.csv`).

## 4. Fase 5 – uscite (177 combinazioni su 3 basi)
| # | Combinazione | Netto | Lordo | Eccesso su FTSE MIB div. | Percentile | Max drawdown | Operazioni | Ordini/sett. | Titolo migliore | Vincoli |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A COMP R21 K6 B0 L1M | 36.1% | 52.9% | 24.6% | 100.0 | -9.2% | 25 | 1.5 | 22% | sì |
| 2 | A COMP R21 K6 B0 L1M +SL12 | 36.1% | 52.9% | 24.6% | 100.0 | -9.2% | 25 | 1.5 | 22% | sì |
| 3 | A COMP R21 K4 B4 L5M | 35.7% | 51.7% | 24.2% | 99.2 | -11.2% | 15 | 0.9 | 37% | sì |
| 4 | A COMP R21 K4 B4 L5M +SL12 | 35.3% | 51.2% | 23.8% | 99.2 | -10.1% | 15 | 0.9 | 37% | sì |
| 5 | A COMP R21 K6 B0 L1M +T120 | 35.2% | 51.8% | 23.7% | 100.0 | -10.3% | 26 | 1.5 | 23% | sì |
| 6 | A COMP R21 K6 B0 L1M +SL12+T120 | 35.2% | 51.8% | 23.7% | 99.8 | -10.3% | 26 | 1.5 | 23% | sì |
| 7 | A COMP R21 K6 B0 L1M +TR20 | 35.1% | 51.6% | 23.6% | 100.0 | -9.6% | 25 | 1.5 | 23% | sì |
| 8 | A COMP R21 K6 B0 L1M +SL12+TR20 | 35.1% | 51.6% | 23.6% | 99.8 | -9.6% | 25 | 1.5 | 23% | sì |
| 9 | A COMP R21 K4 B4 L5M +TR20 | 34.7% | 50.3% | 23.2% | 99.2 | -10.4% | 15 | 0.9 | 38% | sì |
| 10 | A COMP R21 K4 B4 L5M +SL12+TR20 | 34.3% | 49.8% | 22.8% | 98.2 | -9.8% | 15 | 0.9 | 38% | sì |

Nessuna delle 177 varianti batte la sola rotazione di più di 0,5 punti (5 sono identiche alla base). Effetto medio sul rendimento netto rispetto alla base, per regola singola: stop 12% −0,1 punti (per due basi su tre non scatta mai), trailing 20% −1,1, tempo massimo 120 sedute −2,6, tempo 60 −4,4, stop 2,5×ATR −8,1, take profit 20% −8,7 (8% −16,1), trailing 12% −14,4, stop 8% −14,5; la regola «prezzo ≥ 0,9 × TP medio» (quella del recap) costa circa −38 punti. I titoli che salgono sono quelli da tenere: ogni uscita anticipata taglia i vincenti. Per scegliere le 2 da portare in fase 6 ho preso la migliore per ciascuna base (a parità entro 0,5 punti, meno regole): in entrambi i casi la rotazione semplice.

## 5. Fase 6 – dimensionamento (32 combinazioni + 2 prove di sensibilità)
| # | Combinazione | Netto | Lordo | Eccesso su FTSE MIB div. | Percentile | Max drawdown | Operazioni | Ordini/sett. | Titolo migliore | Vincoli |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A COMP R21 K4 B4 L5M | N4 reinvest | 39.6% | 57.9% | 28.1% | 99.6 | -12.2% | 15 | 0.9 | 38% | sì |
| 2 | A COMP R21 K6 B0 L1M | N6 reinvest | 38.6% | 59.2% | 27.1% | 100.0 | -9.3% | 25 | 1.5 | 27% | sì |
| 3 | A COMP R21 K6 B0 L1M | N6 fissi | 36.1% | 52.9% | 24.6% | 99.8 | -9.2% | 25 | 1.5 | 22% | sì |
| 4 | A COMP R21 K4 B4 L5M | N4 fissi | 35.7% | 51.7% | 24.2% | 99.4 | -11.2% | 15 | 0.9 | 37% | sì |
| 5 | A COMP R21 K6 B0 L1M | N6 reinvest 1/ATR | 34.1% | 51.5% | 22.6% | 100.0 | -8.6% | 25 | 1.5 | 26% | sì |
| 6 | A COMP R21 K4 B4 L5M | N4 reinvest 1/ATR | 33.7% | 50.1% | 22.2% | 99.4 | -9.2% | 15 | 0.9 | 39% | sì |
| 7 | A COMP R21 K4 B0 L1M | N4 fissi | 31.6% | 47.2% | 20.1% | 99.4 | -11.0% | 20 | 1.2 | 38% | sì |
| 8 | A COMP R21 K8 B0 L1M | N8 reinvest | 30.9% | 47.6% | 19.4% | 99.6 | -11.5% | 31 | 1.8 | 24% | sì |
| 9 | A COMP R21 K4 B4 L5M | N4 fissi 1/ATR | 30.4% | 44.9% | 18.9% | 98.2 | -8.8% | 15 | 0.9 | 37% | sì |
| 10 | A COMP R21 K5 B0 L1M | N5 reinvest | 30.1% | 47.0% | 18.6% | 98.6 | -11.5% | 22 | 1.3 | 39% | sì |

Sensibilità Tobin 0,4% dal 2026 (non usata per scegliere): A COMP R21 K6 B0 L1M | N6 reinvest 38.3% (con 0,2%: 38.6%); A COMP R21 K4 B4 L5M | N4 reinvest 39.3% (con 0,2%: 39.6%). L'effetto è di circa 0,3 punti: il raddoppio della Tobin pesa poco su strategie con poche operazioni (15–25 in 8 mesi).

## 6. Le due finaliste
Grafico del patrimonio contro FTSE MIB con dividendi e contro la mediana delle loro 500 casuali: `risultati/patrimonio_finaliste.png`. Registri delle operazioni: `risultati/finalista1_operazioni.csv`, `finalista2_operazioni.csv` (patrimonio giornaliero in `finalista*_patrimonio.csv`). L'ultimo punto del grafico è dopo vendita finale, costi e tasse (da qui il calo dell'ultimo giorno).

**Finalista 1** (id 20018): ogni 21 sedute (alla chiusura, dal 29/8/2025) calcola per ogni titolo con almeno 5 target e almeno 5 mln € di controvalore giornaliero mediano (60 sedute) la media dei ranghi percentuali (0–1) di momentum a 120 sedute e saldo revisioni a 60 giorni; tiene i primi 4 e vende un titolo solo se scende oltre la posizione 8; gli ordini vanno all'apertura del giorno dopo; ogni acquisto vale il patrimonio corrente diviso 4 (reinvestimento); nessuna regola di uscita oltre alla classifica. Netto 39.6%, mediana delle sue casuali 5.5%, 15 operazioni, **0.9 ordini a settimana**. Tre trade migliori = 83% del guadagno; titolo migliore STMMI = 38% (limite 40%). Sensibilità al numero di blocchi (reinvestimento): N=4: 39.6%, N=5: 28.9%, N=6: 20.6%, N=8: 25.2%: il risultato cade molto passando da 4 a 5–6 blocchi, quindi è fragile.

**Finalista 2** (id 20010): ogni 21 sedute (alla chiusura, dal 29/8/2025) calcola per ogni titolo con almeno 5 target e almeno 1 mln € di controvalore giornaliero mediano (60 sedute) la media dei ranghi percentuali (0–1) di momentum a 120 sedute e saldo revisioni a 60 giorni; tiene i primi 6 e vende un titolo solo se scende oltre la posizione 6; gli ordini vanno all'apertura del giorno dopo; ogni acquisto vale il patrimonio corrente diviso 6 (reinvestimento); nessuna regola di uscita oltre alla classifica. Netto 38.6%, mediana delle sue casuali 4.8%, 25 operazioni, **1.5 ordini a settimana**. Tre trade migliori = 56% del guadagno; titolo migliore STMMI = 27%. Per blocchi: N=4: 35.5%, N=5: 30.1%, N=6: 38.6%, N=8: 30.9%: più stabile della prima.

Le due finaliste usano lo stesso segnale (COMP): tutti i 15 titoli della prima compaiono anche nella seconda (che ne ha 23), quindi non sono due idee indipendenti. Il guadagno è concentrato: per entrambe i tre titoli migliori sono STMMI, PRY e TPRO, e il 84% (finalista 1) e il 76% (finalista 2) del guadagno netto viene da operazioni chiuse da marzo 2026 in poi (di cui la liquidazione finale al 30/4); nel grafico il patrimonio sale e scende molto nell'ultimo mese.

## 7. Cautele e dati
- **Prove multiple**: 379 combinazioni distinte (168 + 177 + 32, più 2 di sensibilità), ciascuna con una simulazione netta, una lorda e 500 casuali: circa 190,258 simulazioni. La scelta delle finaliste è un uso dei dati in-sample.
- **Un solo regime** (mercato in rialzo, FTSE MIB sempre sopra la media a 200 sedute) e solo 8 mesi: nulla dice come COMP si comporti in un ribasso.
- Il rendimento di 8 mesi non è annualizzato nelle tabelle; `fase4.csv`, `fase5.csv`, `fase6.csv` hanno anche rendimento annualizzato, Sharpe, Sortino, costi, % vincenti, durata, esposizione.
- Il termine di confronto usa dividendi **stimati** (40 titoli più capitalizzati con azioni note; quanto realmente incassato da un ETF può differire).
- Tobin: lista di esenti da fonti secondarie (vedi riassunto fase 3). Mi sono tenuto alle aliquote del file decisioni.
- I file `fase3_*`, `RIASSUNTO_FASE3.md` e `fase2*` sono quelli della sessione precedente (prima di liquidità, duplicati e Tobin 0,2%) e non sono stati rigenerati; `fase2.py` va usato solo con il motore di allora.
- Scelte mie dove il testo lascia margine: percentile = quota di casuali con rendimento netto inferiore; parità di rango risolta dal titolo più liquido; blocchi non rimpiazzati tra due ribilanciamenti restano vuoti; peso ∝ 1/ATR limitato tra 0,5 e 1,5 volte il blocco; «vicine» = un parametro spostato di un passo; stima delle uscite per classifica nelle casuali = stessa data di uscita.
- Riproduzione: `python3 -I ricerca/esperimenti.py fase4|fase5|fase6|finali`, poi `python3 -I ricerca/riassunto46.py`; test: `python3 -I -m pytest ricerca/test_motore.py -q -p no:cacheprovider` (56 test).
