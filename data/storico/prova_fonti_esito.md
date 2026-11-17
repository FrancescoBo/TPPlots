# Prova delle fonti storiche

Eseguita il 2026-11-17 23:01 UTC. Per ogni fonte: risponde? fin dove arriva nel passato?
Una sezione e' OK se almeno un elemento funziona; ogni elemento ha il proprio esito.

| Prova | Esito |
|---|---|
| 1. Soldionline (pagine /raccomandazioni/<ISIN>.html) | NON FUNZIONA |
| 2. 4trading (articoli per numero) | NON FUNZIONA |
| 3. UBS (research disclosures) | OK |
| 4. Consob - posizioni corte nette | NON FUNZIONA |
| 5. filings.xbrl.org | OK |
| 6. Yahoo Finance (yfinance) | OK |
| 7. FRED (rendimenti a 10 anni, senza chiave) | OK |

## 1. Soldionline (pagine /raccomandazioni/<ISIN>.html): NON FUNZIONA

- **ISP IT0000072618**: NON FUNZIONA - grande: 39 pagine, 0 righe con data
- **MAIRE IT0004931058**: NON FUNZIONA - medio: 10 pagine, 0 righe con data
- **SIAV IT0005504128**: NON FUNZIONA - piccolo: 1 pagine, 0 righe con data
- **ATL (Atlantia) IT0003506190**: NON FUNZIONA - non piu quotato: 16 pagine, 0 righe con data
- **MS (Mediaset) IT0001063210**: NON FUNZIONA - non piu quotato: 28 pagine, 0 righe con data
_durata: 190 s_

## 2. 4trading (articoli per numero): NON FUNZIONA

Apertura degli articoli per numero, senza la parte finale dell'URL:
- **articolo 150738**: NON FUNZIONA - HTTP 404, URL finale https://4trading.it/articoli/150738, titolo "", data non trovata
- **articolo 140000**: NON FUNZIONA - HTTP 404, URL finale https://4trading.it/articoli/140000, titolo "", data non trovata
- **articolo 125000**: NON FUNZIONA - HTTP 404, URL finale https://4trading.it/articoli/125000, titolo "", data non trovata
- **articolo 110000**: NON FUNZIONA - HTTP 404, URL finale https://4trading.it/articoli/110000, titolo "", data non trovata
- **articolo 95000**: NON FUNZIONA - HTTP 404, URL finale https://4trading.it/articoli/95000, titolo "", data non trovata
- **articolo 80000**: NON FUNZIONA - HTTP 404, URL finale https://4trading.it/articoli/80000, titolo "", data non trovata

Scansione di 150 numeri consecutivi attorno a tre id:
- **scansione attorno a 150738**: NON FUNZIONA - ids 150663-150812: 0 pagine raggiunte, 0 articoli "Raccomandazioni analisti", primo trovato id None
- **scansione attorno a 110000**: NON FUNZIONA - ids 109925-110074: 0 pagine raggiunte, 0 articoli "Raccomandazioni analisti", primo trovato id None
- **scansione attorno a 80000**: NON FUNZIONA - ids 79925-80074: 0 pagine raggiunte, 0 articoli "Raccomandazioni analisti", primo trovato id None
_durata: 688 s_

## 3. UBS (research disclosures): OK

- **Enel**: OK - 8 righe, data piu vecchia 2023-08-17, piu recente 2026-11-04; per anno: 2023: 1, 2024: 2, 2025: 2, 2026: 3; esempio: 2026-11-04 | 9.68 | 10.35 | Buy
- **Eni**: OK - 24 righe, data piu vecchia 2023-08-17, piu recente 2026-10-23; per anno: 2023: 2, 2024: 6, 2025: 7, 2026: 9; esempio: 2026-10-23 | 27.65 | 32.00 | Buy
_durata: 3 s_

## 4. Consob - posizioni corte nette: NON FUNZIONA

- **pagina PNC e file Excel**: NON FUNZIONA - pagina scaricata (326218 caratteri) ma nessun link a file Excel
_durata: 2 s_

## 5. filings.xbrl.org: OK

- **filings italiani per anno**: OK - 874 filings in 5 pagine API (filtro [{"name": "country", "op": "eq", "val": "IT"}]); entita distinte 225
  - per anno (di fine periodo): 2021: 189, 2022: 187, 2023: 170, 2024: 199, 2025: 125, 2026: 4
- **Eni, file xBRL JSON**: OK - filing Eni analizzato (su 5 filings di Eni trovati)
  ENI S.P.A., fine periodo 2025-12-31: https://filings.xbrl.org/BUCRF72VH5RBN7X3VL35/2025-12-31/ESEF/IT/0/BUCRF72VH5RBN7X3VL35-2025-12-31-1-it.json (16568370 byte, 1004 fatti)
    - ricavi: PRESENTE - ifrs-full:RevenueFromContractsWithCustomers (x6, es. 82151000000.0 (2025-01-01T00:00:00/2026-01-01T00:00:00))
    - utile netto: PRESENTE - ifrs-full:ProfitLoss (x21, es. 2758000000.0 (2025-01-01T00:00:00/2026-01-01T00:00:00)); ifrs-full:ProfitLossAttributableToOwnersOfParent (x3, es. 2608000000.0 (2025-01-01T00:00:00/2026-01-01T00:00:00))
    - patrimonio netto: PRESENTE - ifrs-full:Equity (x56, es. 52787000000.0 (2026-01-01T00:00:00)); ifrs-full:EquityAttributableToOwnersOfParent (x2, es. 47940000000.0 (2026-01-01T00:00:00))
    - dividendo per azione: PRESENTE - ifrs-full:DividendsRecognisedAsDistributionsToOwnersPerShare (x1, es. 1.05 (2025-01-01T00:00:00/2026-01-01T00:00:00))
_durata: 13 s_

## 6. Yahoo Finance (yfinance): OK

ENI.MI dal 2015-01-01:
- **ENI.MI**: OK - 3020 righe, prima data 2015-01-02, ultima 2026-11-17

Titoli usciti dalla Borsa (storia massima):
- **ATL.MI**: NON FUNZIONA - nessun dato
- **MS.MI**: OK - 584 righe, prima data 2024-07-29, ultima 2026-11-17
- **CERV.MI**: NON FUNZIONA - nessun dato
- **AGL.MI**: NON FUNZIONA - nessun dato
- **TOD.MI**: NON FUNZIONA - nessun dato
- **SRS.MI**: NON FUNZIONA - nessun dato

Indici e cambi (storia massima):
- **FTSEMIB.MI**: OK - 7377 righe, prima data 1997-12-31, ultima 2026-11-17
- **^STOXX50E**: OK - 4922 righe, prima data 2007-03-30, ultima 2026-11-16
- **^VIX**: OK - 9290 righe, prima data 1990-01-02, ultima 2026-11-17
- **^V2TX**: NON FUNZIONA - nessun dato
- **EURUSD=X**: OK - 5958 righe, prima data 2003-12-01, ultima 2026-11-17
- **BZ=F**: OK - 4806 righe, prima data 2007-07-30, ultima 2026-11-17

Candidati per il FTSE Italia Mid Cap (storia massima):
- **FTITLMS.MI**: NON FUNZIONA - nessun dato
- **FTSEMC.MI**: NON FUNZIONA - nessun dato
- **FTMIDCAP.MI**: NON FUNZIONA - nessun dato
- ricerca Yahoo "FTSE Italia Mid Cap": ITMC.MI (FTSE Italia Mid Cap Index), 0XCK.IL (LYXOR FTSE ITALIA MID CAP PIR (), DE000SLA6MS7.SG (), ITMCN.FGI (FTSE Italia Mid Cap Net Tax Ind), ITMC.FGI (FTSE Italia Mid Cap Index), ITMCN.MI (FTSE Italia Mid Cap Net Tax Ind)
_durata: 33 s_

## 7. FRED (rendimenti a 10 anni, senza chiave): OK

- **Italia 10 anni (IRLTLT01ITM156N)**: OK - 428 righe (428 con valore), dal 1991-03-01 al 2026-10-01, ultimo valore 4.68
- **Germania 10 anni (IRLTLT01DEM156N)**: OK - 846 righe (846 con valore), dal 1956-05-01 al 2026-10-01, ultimo valore 3.4159090909
_durata: 2 s_
