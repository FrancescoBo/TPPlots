# Strategia di trading sui target price – piano degli esperimenti

Versione del 17/11/2026. Copia di lavoro del documento "Strategia di trading sui target price – piano degli esperimenti": è vincolante per chi esegue gli esperimenti.

## In breve

L'obiettivo è trovare poche regole di acquisto e vendita su titoli italiani coperti dagli analisti che, dopo commissioni, Tobin tax e tasse, battano il semplice "compra e tieni" del FTSE MIB su 12 mesi. Il piano procede per gradi: prima si verifica quali dati degli analisti anticipano davvero i rendimenti, poi si costruiscono le regole solo su quelli.

Le aspettative vanno tenute basse. Ci sono circa 14 mesi di dati utilizzabili, in un periodo di forte rialzo della Borsa italiana: quasi ogni regola sembrerà profittevole. Il confronto con il mercato, con strategie casuali e con un periodo di verifica tenuto da parte è quindi la vera prova.

Scelte di partenza:

- 20.000 € divisi in 4–6 blocchi da 3.300–5.000 €.
- Solo acquisti, niente vendite allo scoperto, niente leva.
- Segnali calcolati sulla chiusura del giorno, operazioni il giorno dopo; minimi e massimi usati per ordini limite, take profit e stop.
- Tobin tax dello 0,1% come quella vera; tassa del 26% sulle plusvalenze con compensazione delle minusvalenze; dividendi incassati al netto.

## Dati

Periodo di test utile: dal 1 settembre 2025 al 17 novembre 2026. Prima di settembre 2025 i target raccolti sono troppo pochi.

| Dato | File | Contenuto | Note |
| --- | --- | --- | --- |
| Prezzi completi | `data/ricerca/prezzi/<TICKER>.csv` | data, apertura, massimo, minimo, chiusura, volume dal 2025-01-01, tutti i titoli di `config/titoli.csv` | Non rettificati per dividendi. Usare questi, non `data/prezzi/` (che servono al sito) |
| Dividendi | `data/ricerca/dividendi.csv` | ticker, data di stacco, dividendo lordo per azione | |
| Frazionamenti Yahoo | `data/ricerca/frazionamenti.csv` | ticker, data, rapporto | Confrontare con `config/frazionamenti.csv` |
| Indice | `data/ricerca/indice_ftsemib.csv` | FTSE MIB giornaliero | Termine di confronto |
| Esito download | `data/ricerca/esito_download.csv` | righe e date per titolo, errori | Titoli senza dati = fuori dall'universo |
| Raccomandazioni | `data/raccomandazioni.csv` | ticker, data, emittente, raccomandazione, target | 6.400 righe circa dal 2025-01; primo semestre 2025 scarso |
| Anagrafica | `config/titoli.csv` | nome, settore, simbolo Yahoo, azioni in circolazione | Capitalizzazione = azioni × prezzo (approssimata, azioni solo attuali) |
| Normalizzazione | `config/alias_emittenti.csv`, `config/classi_raccomandazioni.csv`, `config/frazionamenti.csv`, `config/ticker_estinti.csv` | Come li usa `scripts/costruisci.py` | Applicarli allo stesso modo |

TP medio (come nel sito): per ogni emittente l'ultimo target con data ≤ D e età ≤ 120 giorni, media semplice; target precedenti a un raggruppamento moltiplicati per il fattore in `config/frazionamenti.csv`.

Universo del giorno D: titoli con almeno 5 target nei 120 giorni precedenti D e prezzo disponibile in D (circa 68 titoli al 1/9/2025, 87 al 1/11/2025).

Tobin tax: va creato `ricerca/tobin_esenti.csv` (ticker, motivo, fonte): esenti le società con sede legale all'estero (es. Ferrari, STMicroelectronics, Exor, Stellantis, Campari) e quelle nella lista MEF delle società sotto 500 milioni di capitalizzazione per l'anno in corso.

## Regole di simulazione

Ogni operazione costa circa lo 0,7% del valore tra andata e ritorno con blocchi da 4.000–5.000 €.

Tempi ed esecuzione:

- I segnali usano solo dati fino alla chiusura del giorno t. Una raccomandazione datata t si usa da t+1.
- Ordine al meglio: eseguito in t+1 all'apertura.
- Ordine limite di acquisto a prezzo L: eseguito in t+1 se il minimo è ≤ L, al prezzo più basso tra L e l'apertura.
- Take profit a livello P: eseguito se il massimo è ≥ P, al prezzo più alto tra P e l'apertura. Stop a livello S: eseguito se il minimo è ≤ S, al prezzo più basso tra S e l'apertura.
- Se nella stessa seduta si toccano sia take profit sia stop, vale lo stop.

Costi per singola operazione (acquisto o vendita): 6,40 € + 0,24% della parte oltre 1.460 €.

| Valore operazione (€) | Commissione (€) | Commissione (%) | Andata e ritorno + Tobin (%) |
| --- | --- | --- | --- |
| 1.460 | 6,40 | 0,44 | 0,98 |
| 2.500 | 8,90 | 0,36 | 0,81 |
| 3.300 | 10,82 | 0,33 | 0,76 |
| 4.000 | 12,50 | 0,31 | 0,72 |
| 5.000 | 14,90 | 0,30 | 0,70 |
| 6.700 | 18,98 | 0,28 | 0,67 |
| 10.000 | 26,90 | 0,27 | 0,64 |

- Tobin tax: 0,1% del valore di ogni acquisto, salvo titoli in `ricerca/tobin_esenti.csv`.
- Slittamento: 0,05% per lato sui titoli sopra 1 miliardo di capitalizzazione, 0,20% sotto.
- Dividendi: se il titolo è in portafoglio il giorno prima dello stacco si incassa il 74% del dividendo.
- Tasse: 26% sul guadagno di ogni vendita (vendita − acquisto − commissioni − Tobin). Le perdite formano un credito usabile per 4 anni solari successivi. Riportare sempre risultato lordo e netto.
- Capitale 20.000 €, liquidità a interesse zero (variante 2% annuo), niente leva, niente short. Numero intero di azioni.

## Variabili da investigare

Calcolate per ogni titolo e giorno con i soli dati disponibili fino a quel giorno.

| # | Variabile | Definizione |
| --- | --- | --- |
| 1 | Potenziale (Delta TP) | TP medio / prezzo − 1 |
| 2 | Revisione del consenso | Variazione % del TP medio a 30, 60, 90 giorni |
| 3 | Saldo revisioni | Target alzati meno abbassati (stesso emittente) negli ultimi 30 e 60 giorni, anche diviso per n. emittenti |
| 4 | Quota positivi | Quota Buy + Overweight tra gli ultimi giudizi di ciascun emittente (≤ 365 giorni) e sua variazione a 60 giorni |
| 5 | Eventi | Passaggio di classe verso Buy; target alzato ≥ 10% da un emittente; almeno 2 alzate in 5 giorni |
| 6 | Copertura e disaccordo | N. target validi; deviazione standard / media dei target validi |
| 7 | Distanza da TP −10% | Prezzo / (TP medio / 1,1) − 1 |
| 8 | Momentum | Rendimento a 20, 60, 120 sedute |
| 9 | Ritracciamento | Prezzo / massimo delle ultime 60 sedute − 1 |
| 10 | Volatilità (ATR%) | Media a 14 sedute del true range / prezzo |
| 11 | Capitalizzazione | Miliardi di euro |
| 12 | Regime di mercato | FTSE MIB sopra o sotto la media a 200 sedute |

## Strategie

Una strategia = una regola di ingresso + al massimo 2–3 regole di uscita + una regola di dimensionamento.

Ingresso:

| Famiglia | Come funziona | Parametri |
| --- | --- | --- |
| A. Rotazione | Ogni R sedute ordina l'universo per un segnale S e tiene i primi K; vende solo se il titolo scende oltre la posizione K + B | S: potenziale, revisione 60 gg, saldo revisioni 60 gg, punteggio composto. R: 5, 10, 21. K = n. blocchi. B: 0, K, 2K. Potenziale minimo 0%, 10% |
| B. Eventi | Compra il giorno dopo un evento se c'è un blocco libero; a parità il segnale più forte | Passaggio verso Buy; alzata ≥ 5%, 10%, 20%; ≥ 2 alzate in 5 o 10 gg. Filtro potenziale 0%, 10% |
| C. Ritracciamento con consenso forte | Compra se il prezzo è sceso del x% dal massimo a 20 sedute ma il consenso resta positivo | x: 5, 8, 12%. Quota positivi ≥ 50%, 70%. Nessun calo del TP medio a 30 gg. Potenziale ≥ 15%. Limite a chiusura − 0, 1, 2%, valido 1 o 3 sedute |
| D. Punteggio composto | Media di 2–4 variabili standardizzate nello stesso giorno, pesi uguali, usata come S in A | Variabili scelte in fase 3 |

Uscita: take profit 3, 5, 8, 12, 20%, nessuno · stop fisso 5, 8, 12%, nessuno · stop 1,5 / 2,5 / 3,5 × ATR · trailing 8, 12, 20% · prezzo ≥ TP medio × 0,9 o × 1,0 · tempo massimo 20, 60, 120 sedute · TP medio −5% dall'ingresso o ≥ 2 emittenti che abbassano la classe · per A, uscita dalla classifica.

Dimensionamento: N blocchi 3, 4, 5, 6, 8; blocchi fissi 20.000/N oppure patrimonio corrente/N; variante peso ∝ 1/ATR; un blocco per titolo, massimo 2 blocchi per settore.

## Periodi

| Periodo | Date | Uso |
| --- | --- | --- |
| Riscaldamento | 2025-01-02 – 2025-08-31 | Solo calcolo segnali |
| Scelta (in-sample) | 2025-09-01 – 2026-04-30 | Prove e scelta parametri |
| Verifica (out-of-sample) | 2026-05-01 – 2026-11-17 | Solo in fase 7, una volta, senza ritocchi |
| Riferimento 12 mesi | 2025-11-17 – 2026-11-17 | Numero principale, solo in fase 7 |
| Prova dal vivo | da dicembre 2026 | Regole applicate sulla carta ai dati nuovi |

## Fasi

1. Preparazione: dati, motore di simulazione giornaliero, test automatici (costi, Tobin, tasse, esecuzione).
2. Termini di confronto: compra e tieni FTSE MIB; compra e tieni dei 5 titoli con potenziale più alto al primo giorno; generatore di strategie casuali (stesse uscite e stesso numero di operazioni, titoli a caso, 500 ripetizioni), usato dalla fase 4.
3. Studio dei segnali senza operazioni: rendimenti futuri a 5, 20, 60 sedute; per ogni variabile correlazione di rango (media e quota di mesi con lo stesso segno) e rendimento medio per quintile; per gli eventi rendimento medio dopo l'evento rispetto all'universo. Si tengono le 3–4 variabili con effetto stabile. Se nessuna supera il filtro, ci si ferma.
4. Ingressi A–D con le variabili sopravvissute e uscita semplice (rotazione per A; 60 sedute o stop 12% per B e C). Massimo qualche centinaio di combinazioni.
5. Uscite sulle 3 migliori combinazioni di ingresso.
6. Dimensionamento sulle 2 migliori strategie.
7. Robustezza: periodo di verifica; finestre mobili di 6 mesi che partono ogni mese; ogni parametro spostato di un valore; costi × 1,5 e slittamento × 2; esecuzione ritardata di un giorno; senza il titolo migliore.
8. Rapporto finale.

## KPI e criterio di scelta

| KPI | Definizione | Ruolo |
| --- | --- | --- |
| Guadagno netto (€) | Patrimonio finale − 20.000 € sui 12 mesi di riferimento | Principale |
| Rendimento annualizzato (%) | Netto e lordo, intero periodo | Principale |
| Eccesso sul FTSE MIB | Strategia − compra e tieni indice | Vincolo > 0 anche in verifica |
| Percentile contro il caso | Rispetto alle 500 strategie casuali | Vincolo ≥ 90° |
| Massima perdita dal picco | Drawdown massimo del patrimonio | Vincolo ≤ 20% |
| Sharpe, Sortino | Su rendimenti giornalieri | Confronto |
| Costi | N. operazioni, commissioni + Tobin, costi / guadagno lordo | Diagnosi |
| Qualità dei trade | % vincenti, guadagno medio / perdita media, durata media | Diagnosi |
| Esposizione | % del tempo investito | Diagnosi |
| Concentrazione | Quota del guadagno dai 3 trade migliori e dal titolo migliore | Vincolo: titolo migliore ≤ 40% |
| Stabilità | Mediana e peggiore delle finestre di 6 mesi; effetto di ±1 valore per parametro | Scelta finale |
| Impegno operativo | Ordini medi a settimana | Gestibilità |

Criterio: scartare chi viola un vincolo; tra i rimanenti la mediana più alta del guadagno netto sulle finestre di 6 mesi; preferire zone di parametri stabili; a parità, meno regole e meno operazioni.

## Trappole da evitare

- Universo ricalcolato ogni giorno, mai quello di oggi.
- Nessuna informazione del giorno t usata per eseguire in t.
- Titoli usciti dalla Borsa chiusi all'ultimo prezzo, non tolti.
- Target con rapporto target / prezzo fuori da 0,3–3: esclusi e segnalati.
- Dividendi sempre considerati.
- Contare e riportare tutte le combinazioni provate.
- Confrontare sempre con l'indice.
- Slittamento più alto sui titoli piccoli.
- Giorni senza prezzo o con volume zero: nessun ordine eseguito.

## Organizzazione

- Lavorare solo in `ricerca/`; non modificare `scripts/`, `docs/`, `data/`, `config/`.
- Codice: `ricerca/dati.py`, `segnali.py`, `motore.py`, `strategie.py`, `esperimenti.py`, `test_motore.py`.
- Risultati in `ricerca/risultati/`; rapporto per fase in `ricerca/RIASSUNTO_FASE<n>.md`, finale in `ricerca/RAPPORTO.md`.
- Seme casuale fisso; annotare la data dell'ultimo dato usato.
