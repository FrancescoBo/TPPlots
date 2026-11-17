# Rapporto finale – strategia di rotazione COMP sui titoli italiani con target price

Ultima seduta dei dati: **2026-11-17** (il 17/11/2026 hanno prezzo 204 titoli su 216: l'ultima chiusura può essere parziale). Seme fisso 20260430. Tutte le regole di simulazione sono quelle delle fasi 4–6, senza modifiche.

## 1. Esito della verifica: **NON SUPERA**

I criteri erano stati fissati prima di guardare il periodo di verifica (DECISIONI_FASE6.md) e valgono tutti insieme. Ne manca **ognuno dei quattro**:

| # | Criterio | Risultato | Esito |
|---|---|---|---|
| 1 | Finalista 2, periodo di verifica: netto > FTSE MIB con dividendi stimati | -28.9% contro +4.9% | **NON SUPERA** |
| 2 | Finalista 2, verifica: percentile ≥ 80 contro le sue 500 casuali | 0.0 | **NON SUPERA** |
| 3 | Zona di parametri (24 combinazioni COMP, R 21): mediana > FTSE MIB con dividendi | mediana -27.4% (min -33.9%, max -20.4%); sopra il FTSE MIB: 0% | **NON SUPERA** |
| 4 | Robustezza: con i 4 spostamenti del giorno di ribilanciamento, netto sull'intero periodo sopra il FTSE MIB con dividendi in almeno 3 casi su 4 | 0 su 4 | **NON SUPERA** |

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

| Voce | Netto | Guadagno | Lordo | Eccesso su FTSE MIB div. | Percentile | Max drawdown | Operazioni |
|---|---|---|---|---|---|---|---|
| finalista1_verifica | -24.5% | -4.901 € | -22.4% | -29.4% | 0.8 | -34.1% | 11 |
| finalista2_verifica | -28.9% | -5.784 € | -25.5% | -33.8% | 0.0 | -36.9% | 26 |

Termine di confronto sullo stesso periodo: FTSE MIB con dividendi stimati +4.9% netto (+979 €); solo prezzo +3.3%. Mediana delle 500 casuali della Finalista 2: -1.2%.

**Zona di parametri** (24 combinazioni COMP, R 21): netto mediano -27.4%, minimo -33.9%, massimo -20.4%; nessuna batte il FTSE MIB con dividendi; percentile massimo 1.6. Il problema non è un parametro sfortunato: tutta la zona che in fase 4 occupava le prime 10 posizioni è andata male.

**Controlli** (24 combinazioni ciascuno, blocchi fissi, come in fase 4), medie sul periodo di verifica:

| Segnale | Netto medio | Eccesso medio su FTSE MIB div. | Percentile medio |
|---|---|---|---|
| MOM | -10.5% | -15.3% | 14.1 |
| REV | -13.8% | -18.7% | 9.2 |
| POT | -0.9% | -5.8% | 47.4 |

POT (il «potenziale alto»), che nel periodo di scelta era un controllo negativo (media −15%), nella verifica perde molto meno dei segnali che avevano funzionato: i segnali si sono ribaltati. Questo non cambia il giudizio, ma dice che l'effetto trend + revisioni non era stabile.

### Diagnosi descrittiva: i segnali nei due periodi
Correlazione di rango media (IC) con il rendimento a 20 sedute e differenza tra quintile migliore e peggiore, tra i titoli ammessi (liquidità ≥ 1 mln €). Calcolato a posteriori, non entra nei criteri.

| Segnale | IC medio a 20 sedute, scelta | IC medio a 20 sedute, verifica | Q5−Q1 a 20 sedute, scelta | Q5−Q1 a 20 sedute, verifica |
|---|---|---|---|---|
| MOM | +0.084 | -0.054 | +3.9% | -2.1% |
| REV | +0.044 | +0.001 | +2.7% | -0.2% |
| COMP | +0.070 | -0.029 | +2.6% | -1.0% |
| POT | -0.066 | +0.005 | -3.1% | +0.8% |
| Rendimento medio a 20 sedute dell'universo | +1.8% | +0.1% | | |

## 4. Riferimento a 12 mesi (17/11/2025 – 17/11/2026), 20.000 € iniziali

| Voce | Netto | Guadagno | Lordo | Eccesso su FTSE MIB div. | Percentile | Max drawdown | Operazioni |
|---|---|---|---|---|---|---|---|
| finalista1_12mesi | +6.0% | +1.193 € | +17.7% | -8.5% | 51.4 | -33.1% | 18 |
| finalista2_12mesi | -5.5% | -1.103 € | +4.7% | -19.9% | 24.6 | -35.0% | 38 |

| Voce | Guadagno netto |
|---|---|
| Finalista 1, partendo il 17/11/2025 | +1.193 € |
| Finalista 2, partendo il 17/11/2025 | -1.103 € |
| FTSE MIB con dividendi stimati | +2.885 € (+14.4%) |
| FTSE MIB solo prezzo | +11.0% |

Convenzione: nuova partenza con 20.000 € in contanti; primo segnale alla chiusura del 14/11/2025, poi ribilanciamenti ogni 21 sedute da quel giorno. Il riferimento contiene sei mesi e mezzo di scelta (nov 2025 – apr 2026) e sei e mezzo di verifica. Se invece si guarda la variazione di patrimonio della corsa continua iniziata il 29/8/2025, tra la chiusura del 14/11/2025 e il 17/11/2026 (dopo liquidazione e imposte): Finalista 1 -186 €, Finalista 2 -1.106 €. In ogni lettura **le finaliste stanno sotto il FTSE MIB con dividendi**.

## 5. Robustezza della Finalista 2 sull'intero periodo (1/9/2025 – 17/11/2026)

| Prova | Netto | FTSE MIB div. | Eccesso | Percentile | Max drawdown | Operazioni |
|---|---|---|---|---|---|---|
| rob_spostamento_0 | +4.6% | +17.9% | -13.3% | 51.8 | -37.6% | 46 |
| rob_spostamento_5 | +9.5% | +17.9% | -8.4% | 68.6 | -31.9% | 49 |
| rob_spostamento_10 | -5.2% | +17.9% | -23.1% | 25.6 | -32.4% | 48 |
| rob_spostamento_15 | -11.3% | +17.9% | -29.1% | 12.2 | -38.9% | 45 |
| rob_costi1.5_slitt2 | +1.1% | +17.9% | -16.8% | 55.2 | -38.5% | 46 |
| rob_esecuzione_ritardata | +4.8% | +17.9% | -13.1% | 28.0 | -37.1% | 46 |
| rob_senza_STMMI | -3.4% | +17.9% | -21.2% | 32.4 | -29.6% | 48 |

Sull'intero periodo la Finalista 2 (spostamento 0) rende +4.6% netto contro +17.9% del FTSE MIB con dividendi. Il risultato dipende molto dal giorno di ribilanciamento (da -11.3% a +9.5%); togliendo STMMI diventa -3.4%; con costi ×1,5 e slittamento ×2 resta +1.1%; l'esecuzione ritardata di un giorno non cambia molto (+4.8%). La prova «Tobin 0,4% dal 2027» non è pertinente (nessuna seduta nel 2027) e non è stata eseguita.

### Finestre mobili di 6 mesi (partenza il primo giorno di ogni mese)
| Partenza | Finestra | Netto | FTSE MIB div. | Eccesso | Percentile |
|---|---|---|---|---|---|
| 2025-09 | 2025-09-01 → 2026-02-27 | +24.6% | +9.0% | +15.6% | 98.8 |
| 2025-10 | 2025-10-01 → 2026-03-31 | +19.1% | +3.4% | +15.7% | 100.0 |
| 2025-11 | 2025-11-03 → 2026-04-30 | +26.5% | +9.9% | +16.6% | 100.0 |
| 2025-12 | 2025-12-01 → 2026-05-29 | +24.8% | +13.4% | +11.4% | 98.4 |
| 2026-01 | 2026-01-02 → 2026-06-30 | +31.7% | +12.8% | +18.9% | 97.8 |
| 2026-02 | 2026-02-02 → 2026-07-31 | +5.7% | +13.3% | -7.6% | 62.8 |
| 2026-03 | 2026-03-02 → 2026-08-31 | -0.0% | +11.8% | -11.8% | 29.8 |
| 2026-04 | 2026-04-01 → 2026-09-30 | -1.5% | +11.9% | -13.4% | 23.8 |
| 2026-05 | 2026-05-04 → 2026-10-30 | -27.7% | +2.9% | -30.5% | 0.0 |

Rendimento netto: mediana +19.1%, peggiore -27.7%. Eccesso sul FTSE MIB con dividendi: mediana +11.4%, peggiore -30.5%. Le cinque finestre iniziate tra settembre e gennaio battono il FTSE MIB (le prime tre stanno interamente nel periodo di scelta, le altre due includono mesi di verifica); le quattro iniziate da febbraio in poi no. Una nuova partenza da febbraio 2026 in poi non avrebbe battuto il FTSE MIB con dividendi.

## 6. Grafico dell'intero periodo
`risultati/patrimonio_intero_periodo.png`: patrimonio netto delle due finaliste, mediana e banda 5°–95° delle 500 casuali della Finalista 2 e FTSE MIB con dividendi stimati, 29/8/2025 – 17/11/2026, con la linea verticale al 30/4/2026 tra scelta e verifica. A fine periodo: Finalista 1 +6.9%, Finalista 2 +4.6%, mediana delle casuali +4.1%, FTSE MIB con dividendi +17.9%. L'ultimo punto di ogni linea è dopo vendita finale, costi e imposte (da qui il salto dell'ultimo giorno).

**Attenzione al percorso**: nella corsa continua, che tiene in portafoglio i titoli scelti prima del 30/4, il patrimonio ha continuato a salire dopo la linea di separazione fino al massimo di +13.270 € sul capitale iniziale per la Finalista 2 (22/06/2026) e +16.514 € per la Finalista 1 (22/06/2026), poi ha restituito quasi tutto. La verifica richiesta (nuova partenza il 4/5/2026 con 20.000 € in contanti e acquisto dei titoli che il segnale indicava quel giorno) sale molto meno, fino a 22367 € il 22/06/2026 (Finalista 2), e finisce a 14216 €: i due modi di guardare la stessa regola dicono che dipende molto da *quali* titoli si hanno in portafoglio quando il vento cambia. Il giudizio resta quello fissato: nuova partenza.

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
| 4 | 168 (96 rotazioni + 72 eventi) | 84,336 |
| 5 | 177 | 88,854 |
| 6 | 32 + 2 sensibilità Tobin | 17,068 |
| 7 | 118 (strategia × finestra; include la Finalista 2 sull'intero periodo due volte) | 59,236 |
| **Totale** | **578 combinazioni principali** (635 contando la prova a ritardo 0 della fase 3) | **circa 249,999** |

## 8. Proposte (separate: non applicate e non verificate)
1. **Non usare la regola con denaro vero.** Continuare la prova sulla carta con `segnale_oggi.py` solo se serve a raccogliere altri dati fuori campione.
2. Prima di qualunque nuova regola, capire perché trend e revisioni si sono ribaltati (vedi diagnosi): ipotesi da testare, per esempio un cambio di regime di mercato dopo febbraio 2026. Servirebbe un nuovo periodo di verifica non toccato: questo è ormai stato usato.
3. Allargare l'universo o i dati storici (prima del 2025) per avere più regimi, invece di aggiungere parametri.
4. Se si riprova, fissare in anticipo un numero molto più piccolo di combinazioni e un criterio che corregga per le prove multiple.

## 9. Strumento per la prova dal vivo
`ricerca/segnale_oggi.py` (con `ricerca/portafoglio_prova.csv` vuoto d'esempio) stampa la classifica COMP, i 6 titoli da tenere, cosa vendere e comprare rispetto al portafoglio e la data del prossimo ribilanciamento. Output sui dati più recenti in `risultati/segnale_oggi_output.txt`.

File dei risultati in `ricerca/risultati/`: `fase7.csv` (ogni voce, KPI completi), `fase7_esito.json`, registri delle operazioni `fase7_*_operazioni.csv` e patrimoni `fase7_*_patrimonio.csv`, `diagnosi_fase7.csv`, grafici `patrimonio_finaliste.png` (periodo di scelta) e `patrimonio_intero_periodo.png`. Riproduzione: `python3 -I ricerca/fase7.py`, poi `python3 -I ricerca/rapporto.py`; test: `python3 -I -m pytest ricerca/test_motore.py -q -p no:cacheprovider` (62 test).
