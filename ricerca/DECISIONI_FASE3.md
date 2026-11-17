# Decisioni dopo la fase 3 (revisione del 17/11/2026)

Questo file integra `PIANO.md` ed è vincolante per le fasi 4–6. Dove i due file differiscono, vale questo.

## Cosa si è imparato dalla fase 3

- Controllo indipendente: IC di `momentum_120` a 20 sedute ricalcolato da zero = 0,078 (Sonnet: 0,077). Test del motore: 39/39 superati. Ritardo e rendimenti futuri senza sguardi al futuro.
- Nel periodo hanno funzionato **trend e revisioni al rialzo**, non il "potenziale" rispetto al TP medio: i titoli con potenziale alto hanno reso meno (IC −0,07 a 20 sedute). Un potenziale alto è soprattutto un prezzo sceso.
- I titoli più grandi e più seguiti hanno reso di più, e il FTSE MIB ha battuto l'universo medio: il termine di confronto è difficile da battere.
- Gli effetti sono modesti (differenza tra quintile migliore e peggiore 2–4% a 20 sedute) rispetto ai costi: andata e ritorno circa 0,8% con la Tobin 2026, più lo slittamento. Strategie con molte operazioni partono svantaggiate.
- Evidenza statistica limitata: 7–8 mesi, un solo regime di mercato (sempre in rialzo).

## Modifiche alle regole di simulazione

1. **Tobin tax**: 0,1% sugli acquisti fino al 31/12/2025, **0,2% dal 1/1/2026** (Legge di bilancio 2026). Prova di sensibilità in fase 6 con 0,4% (raddoppio proposto dal disegno di legge di bilancio 2027).
2. **Filtro di liquidità** al posto della capitalizzazione (che manca per 90 titoli): controvalore medio giornaliero (chiusura × volume, mediana delle ultime 60 sedute) ≥ L, calcolato ogni giorno con i soli dati passati. L ∈ {1, 5} milioni di €.
3. **Slittamento per liquidità**: controvalore mediano ≥ 5 mln → 0,05% per lato; 1–5 mln → 0,10%; sotto 1 mln → 0,20%.
4. Togliere le 27 righe duplicate di raccomandazioni prima di calcolare i segnali.
5. **Termine di confronto principale**: FTSE MIB con dividendi stimati (prezzo + rendimento da dividendo stimato come in fase 2, distribuito giornalmente), netto di costi e tasse. Riportare anche la versione solo prezzo.
6. Ogni strategia va confrontata con le proprie 500 strategie casuali (stesse date, stesso numero di operazioni, stesse uscite, titoli a caso tra quelli che passano lo stesso filtro di liquidità).

## Segnali da usare

| Nome | Definizione | Uso |
| --- | --- | --- |
| MOM | `momentum_120` | Segnale |
| REV | `saldo_rev_60` | Segnale |
| COMP | Media dei ranghi percentuali (0–1) di MOM e REV nello stesso giorno, tra i titoli che passano il filtro | Segnale |
| POT | `potenziale` (alto = meglio, direzione originale) | **Solo controllo**: mostra cosa succede seguendo l'idea iniziale; non può essere scelto |
| ALZ5, ALZ10 | Eventi `alzata_5`, `alzata_10` | Ingresso famiglia B |

Esclusi: famiglia C (ritracciamento con consenso forte), perché le sue premesse (potenziale alto, quota positivi) non hanno mostrato effetti o li hanno mostrati di segno opposto; evento `verso_buy`; regime di mercato (non valutabile); `n_target` e capitalizzazione come segnali (restano solo come filtro di liquidità).

## Fase 4 – griglie (solo 2025-09-01 – 2026-04-30)

Famiglia A, rotazione (uscita = fuori dalla classifica oltre K + B):

- S ∈ {MOM, REV, COMP, POT}
- R (sedute tra un ribilanciamento e l'altro) ∈ {10, 21}
- K = N blocchi ∈ {4, 5, 6}
- B ∈ {0, K}
- L ∈ {1, 5} mln
- Totale 96 combinazioni.

Famiglia B, eventi:

- Evento ∈ {ALZ5, ALZ10}
- Filtro ∈ {nessuno, MOM > 0, COMP ≥ 0,5}
- Se più eventi lo stesso giorno: precedenza al COMP più alto
- N blocchi ∈ {4, 5, 6}; L ∈ {1, 5} mln
- Uscita ∈ {60 sedute; 60 sedute o stop 12%}
- Totale 72 combinazioni.

Per ogni combinazione: tutti i KPI del piano, netto e lordo, percentile contro le proprie strategie casuali, eccesso sul FTSE MIB con dividendi. Salvare `risultati/fase4.csv`.

**Condizione di arresto**: se nessuna combinazione (esclusa POT) ha percentile ≥ 90 contro il caso **e** eccesso positivo sul FTSE MIB con dividendi, fermarsi dopo la fase 4 e scriverlo nel riassunto.

## Fase 5 – uscite (sulle 3 migliori combinazioni della fase 4, esclusa POT)

Migliori = vincoli rispettati, poi rendimento netto più alto; preferire combinazioni con vicine (stessa S, parametri adiacenti) anch'esse buone. Regole di uscita aggiunte a quella di base, al massimo 2 alla volta:

- take profit {8, 12, 20%}
- stop fisso {8, 12%} oppure 2,5 × ATR
- trailing {12, 20%}
- tempo massimo {60, 120} sedute (solo famiglia A)
- prezzo ≥ TP medio × 0,9 (una sola prova: è la regola del recap, si attende un peggioramento)

## Fase 6 – dimensionamento (sulle 2 migliori della fase 5)

- N ∈ {4, 5, 6, 8}
- Blocchi fissi oppure reinvestimento
- Peso ∝ 1/ATR
- Tobin 0,4% dal 2026 come sensibilità (non per la scelta)

## Regole generali

- Nessun dato dopo il 2026-04-30, nemmeno per controllo. La fase 7 (verifica) si fa in una sessione separata.
- Riportare il numero totale di combinazioni simulate.
- `RIASSUNTO_FASE4-6.md`: tabella delle 10 migliori per fase con KPI chiave; le 2 finaliste descritte in parole semplici (cosa comprare, quando, quanto, quando vendere); grafico del patrimonio delle finaliste contro FTSE MIB con dividendi e contro la mediana delle loro strategie casuali; registro delle operazioni delle finaliste; quante operazioni a settimana.
