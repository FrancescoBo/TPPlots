# Decisioni dopo le fasi 4–6 (revisione del 17/11/2026)

Vincolante per la fase 7. I criteri di giudizio qui sotto sono fissati **prima** di guardare il periodo di verifica e non si cambiano dopo.

## Controlli fatti sulla consegna

- Riletto `RIASSUNTO_FASE4-6.md`, grafico e registri delle operazioni.
- Verificata a mano un'operazione (FCT, 1/9/2025 – 30/9/2025): acquisto all'apertura del giorno dopo il segnale (20,06), vendita all'apertura (22,70), commissioni 22,72 € e Tobin 3,31 € esatte.
- Prezzi Yahoo rettificati per i raggruppamenti (TIT a 4,137 nel settembre 2025), coerenti con i target corretti da `config/frazionamenti.csv`.

## Valutazione

- Il segnale COMP (media dei ranghi di momentum a 120 sedute e saldo revisioni a 60 giorni) con ribilanciamento ogni 21 sedute occupa tutte le prime 10 posizioni della fase 4: è una zona di parametri, non un singolo punto fortunato. Anche MOM e REV da soli battono in media il FTSE MIB.
- I rendimenti (circa 39% netto in 8 mesi) sono gonfiati dalla scelta tra 379 combinazioni e da pochi titoli (STMMI, PRY, TPRO), con il 76–84% del guadagno da marzo 2026 in poi.
- Le uscite anticipate peggiorano sempre: si resta sulla rotazione semplice.
- **Candidata principale: Finalista 2** (COMP, R 21, K 6, B 0, L 1 mln, reinvestimento): più stabile al variare del numero di blocchi e meno concentrata. Finalista 1 resta come seconda.

## Fase 7 – cosa calcolare

Periodo di verifica: 2026-05-01 – ultima seduta disponibile (17/11/2026 o la più vicina). Riferimento 12 mesi: 2025-11-17 – 2026-11-17. Per ogni voce: netto, lordo, eccesso sul FTSE MIB con dividendi stimati, percentile contro 500 casuali, max drawdown, n. operazioni, titolo migliore.

1. **Finaliste** 1 e 2 sul periodo di verifica, partendo il 2026-05-01 con 20.000 € in liquidità (primo segnale alla chiusura del 2026-04-30).
2. **Zona di parametri**: tutte le 24 combinazioni A con COMP e R 21 (K 4/5/6 × B 0/K × L 1/5 mln × blocchi fissi/reinvestimento, N = K) sul periodo di verifica: mediana, minimo, massimo, quota che batte il FTSE MIB con dividendi.
3. **Controlli**: media delle combinazioni MOM, REV e POT della fase 4 sul periodo di verifica.
4. **Riferimento 12 mesi** per le due finaliste e per il FTSE MIB con dividendi: guadagno netto in €.
5. **Robustezza della Finalista 2**, sull'intero periodo 2025-09-01 – fine dati:
   - giorno di ribilanciamento spostato di 0, 5, 10, 15 sedute;
   - costi × 1,5 e slittamento × 2;
   - esecuzione ritardata di un giorno (apertura di t+2);
   - escludendo STMMI dall'universo;
   - Tobin 0,4% dal 2027-01-01 (nessun effetto atteso sul periodo, solo per completezza: saltare se non pertinente);
   - finestre mobili di 6 mesi che partono il primo giorno di ogni mese da settembre 2025 a maggio 2026: mediana e peggiore.

## Criteri di giudizio (fissati prima)

La strategia **supera la verifica** se valgono tutte:

1. Finalista 2 sul periodo di verifica: rendimento netto > FTSE MIB con dividendi stimati.
2. Finalista 2 sul periodo di verifica: percentile ≥ 80 contro le sue 500 casuali.
3. Zona di parametri: mediana delle 24 combinazioni > FTSE MIB con dividendi stimati.
4. Robustezza: con i quattro spostamenti del giorno di ribilanciamento il rendimento netto sull'intero periodo resta sopra il FTSE MIB con dividendi in almeno 3 casi su 4.

Se ne manca anche uno solo: **non supera**, e lo si scrive senza attenuanti. Non si modificano le regole dopo aver visto la verifica.

## Strumento per la prova dal vivo

Scrivere `ricerca/segnale_oggi.py`: con i dati più recenti del repository stampa la classifica COMP dei titoli che passano i filtri della Finalista 2, i 6 titoli da tenere, i titoli da vendere e comprare rispetto a un portafoglio indicato in `ricerca/portafoglio_prova.csv` (ticker, azioni, prezzo di carico; può essere vuoto) e la data del prossimo ribilanciamento (ogni 21 sedute a partire dal 2025-08-29). Va scritto in ogni caso, anche se la verifica non è superata: serve a seguire la strategia sulla carta.
