# Target price analisti – azioni italiane

Raccolta delle raccomandazioni e dei target price degli analisti sulle azioni
italiane, con pagina web di recap e grafici per titolo.

## Struttura

```
config/
  titoli.csv                 elenco titoli: ticker, nome, settore, simbolo Yahoo,
                             azioni in circolazione, attivo (vuoto = automatico,
                             1 = mostra sempre, 0 = non mostrare mai)
  classi_raccomandazioni.csv raccomandazione -> classe (Buy/Overweight/Neutral/Underweight/Sell)
  alias_emittenti.csv        varianti dei nomi degli emittenti (UBS -> Ubs, ...)
  alias_ticker.csv           codici non milanesi dell'Excel -> ticker (XNYS:RACE -> RACE)
data/
  raccomandazioni.csv        ticker, data, emittente, raccomandazione, target (tutti i titoli)
  prezzi/<TICKER>.csv        data, chiusura
scripts/
  importa_excel.py           import una-tantum dai file Excel
  aggiorna_prezzi.py         scarica le nuove chiusure da Yahoo Finance
  comune.py                  scelta dei titoli da mostrare
  costruisci.py              calcola TP medio, conteggi, Pareto -> docs/data/dati.json
docs/                        la pagina web (GitHub Pages)
.github/workflows/aggiorna.yml  aggiornamento automatico
```

## Messa online (una volta sola)

1. Crea un repository su GitHub e carica tutto il contenuto di questa cartella
   (anche le cartelle nascoste `.github` e il file `docs/.nojekyll`).
2. *Settings → Pages*: Source = "Deploy from a branch", branch `main`, cartella `/docs`.
3. *Settings → Actions → General → Workflow permissions*: "Read and write permissions".
4. Scheda *Actions* → "Aggiorna prezzi e pagina" → *Run workflow* per il primo giro.
   Questo primo giro scarica anche lo storico (dal 2025) dei titoli che non erano
   nel file Plots e completa numero di azioni e settore in `config/titoli.csv`.

La pagina sara' su `https://<utente>.github.io/<repository>/`.
Con l'account gratuito GitHub Pages richiede un repository pubblico.

## Uso quotidiano

- **Quali titoli compaiono**: in automatico quelli con almeno 10 target price
  negli ultimi 365 giorni (`MIN_TARGET_ANNO` in `scripts/comune.py`). Per forzare
  un titolo dentro o fuori metti `1` o `0` nella colonna `attivo` di `config/titoli.csv`.
- **Colori dei target nel grafico**: verde = target alzato rispetto al precedente
  dello stesso emittente, rosso = abbassato, nero = invariato, cerchio vuoto = primo target.
- **Nuove raccomandazioni**: aggiungi righe a `data/raccomandazioni.csv`
  (anche dal sito di GitHub, "Edit"). Al salvataggio il workflow ricalcola la pagina.
- **Prezzi**: il workflow gira nei giorni feriali verso le 18:15 e aggiunge le chiusure.
- **Parametri** (in cima a `scripts/costruisci.py`): `VALIDITA_TP` = giorni per cui
  un target conta nel TP medio (120), `FINESTRA_GRAFICO`, `STORICO_TP_MEDIO`.

## In locale

```
pip install -r requirements.txt
python scripts/aggiorna_prezzi.py
python scripts/costruisci.py
python -m http.server -d docs     # poi apri http://localhost:8000
```

## Raccolta automatica dei target (ogni notte)

`scripts/aggiorna_raccomandazioni.py` gira ogni giorno intorno a mezzanotte (workflow *Aggiorna raccomandazioni, prezzi e pagina*),
legge le fonti elencate in `config/fonti.csv`, elimina i doppioni e aggiunge le righe nuove a `data/raccomandazioni.csv`; poi aggiorna prezzi e pagina.
Ogni domenica (o con *Run workflow → storico*) recupera anche lo storico dalle pagine per titolo di Soldionline.

| Fonte | Modalità iniziale | Note |
|---|---|---|
| `ubs` | attiva | storico data/prezzo/target/rating per titolo (pagine pubbliche UBS) |
| `soldionline` | attiva | articoli giornalieri "Le raccomandazioni del …" + pagine per titolo nel recupero storico |
| `equita`, `intesa` | prova | PDF/archivi pubblici: formato non verificato, le righe finiscono in `data/in_verifica.csv` |
| `4trading` | prova | metti gli URL in `config/url_4trading.csv` |
| `teleborsa` | prova | estrazione da testo libero |

**Modalità** (`config/fonti.csv`): `attiva` = scrive nel dataset · `prova` = scrive solo in `data/in_verifica.csv` · `off` = ignorata.
Quando le righe in verifica risultano corrette, cambia la modalità in `attiva`.

**Deduplica** (stesso titolo + stesso emittente): stessa data = doppione (se il target è diverso resta il primo e il caso va in `data/conflitti.csv`);
date entro 4 giorni con stesso target e stesso giudizio = doppione; a parità vince la fonte con priorità più alta (numero più basso).

**File di controllo** (tutti in `data/`): `raccomandazioni_fonti.csv` (da quale fonte arriva ogni riga aggiunta), `quarantena.csv` (target fuori scala rispetto alla mediana del titolo),
`non_riconosciuti.csv` (nomi di società non associati a un ticker: aggiungili in `config/alias_societa.csv`), `in_verifica.csv`, `conflitti.csv`.
`docs/data/stato_raccolta.json` riassume l'ultimo giro (righe lette/nuove/doppioni/errori per fonte). Nuovi nomi di istituti vanno uniformati in `config/alias_emittenti.csv`.

Prova offline del codice: `python tests/test_raccolta.py`.
