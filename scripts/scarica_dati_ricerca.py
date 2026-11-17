"""Scarica da Yahoo Finance i dati per la ricerca sulla strategia (cartella data/ricerca/, separata dal sito).

  data/ricerca/prezzi/<TICKER>.csv   data, apertura, massimo, minimo, chiusura, volume  (non rettificati)
  data/ricerca/dividendi.csv         ticker, data (stacco), dividendo (EUR per azione, lordo)
  data/ricerca/frazionamenti.csv     ticker, data, rapporto (come riportato da Yahoo)
  data/ricerca/indice_ftsemib.csv    data, apertura, massimo, minimo, chiusura
  data/ricerca/esito_download.csv    ticker, simbolo, righe, prima_data, ultima_data, errore

Tutti i titoli di config/titoli.csv, dal 2025-01-01. Ogni giro riscarica tutto (pochi minuti).
  python scripts/scarica_dati_ricerca.py [--da 2025-01-01]
"""
import argparse
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data/ricerca'
INDICE = 'FTSEMIB.MI'


def storia(simbolo, da):
    for tentativo in range(3):
        try:
            h = yf.Ticker(simbolo).history(start=da, interval='1d', auto_adjust=False, actions=True)
            if h is not None and len(h):
                h.index = pd.to_datetime(h.index.tz_localize(None).date)
                return h
            return None
        except Exception as e:  # rete o simbolo
            err = e
            time.sleep(2 * (tentativo + 1))
    raise err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--da', default='2025-01-01')
    a = ap.parse_args()
    (OUT / 'prezzi').mkdir(parents=True, exist_ok=True)
    titoli = pd.read_csv(ROOT / 'config/titoli.csv', dtype=str).fillna('')
    divid, fraz, esiti = [], [], []
    for t in titoli.itertuples():
        if not t.simbolo_yahoo:
            continue
        try:
            h = storia(t.simbolo_yahoo, a.da)
        except Exception as e:
            esiti.append((t.ticker, t.simbolo_yahoo, 0, '', '', str(e)[:200]))
            print(f'! {t.ticker}: {e}')
            continue
        if h is None:
            esiti.append((t.ticker, t.simbolo_yahoo, 0, '', '', 'nessun dato'))
            continue
        p = pd.DataFrame({'data': h.index.strftime('%Y-%m-%d'), 'apertura': h.Open.round(4).values,
                          'massimo': h.High.round(4).values, 'minimo': h.Low.round(4).values,
                          'chiusura': h.Close.round(4).values, 'volume': h.Volume.fillna(0).astype('int64').values})
        p.to_csv(OUT / f'prezzi/{t.ticker}.csv', index=False)
        if 'Dividends' in h:
            for d, v in h.Dividends[h.Dividends > 0].items():
                divid.append((t.ticker, d.strftime('%Y-%m-%d'), round(float(v), 6)))
        if 'Stock Splits' in h:
            for d, v in h['Stock Splits'][h['Stock Splits'] > 0].items():
                fraz.append((t.ticker, d.strftime('%Y-%m-%d'), float(v)))
        esiti.append((t.ticker, t.simbolo_yahoo, len(p), p.data.iloc[0], p.data.iloc[-1], ''))
        print(f'{t.ticker}: {len(p)} righe')
    pd.DataFrame(divid, columns=['ticker', 'data', 'dividendo']).to_csv(OUT / 'dividendi.csv', index=False)
    pd.DataFrame(fraz, columns=['ticker', 'data', 'rapporto']).to_csv(OUT / 'frazionamenti.csv', index=False)
    try:
        h = storia(INDICE, a.da)
        pd.DataFrame({'data': h.index.strftime('%Y-%m-%d'), 'apertura': h.Open.round(2).values, 'massimo': h.High.round(2).values,
                      'minimo': h.Low.round(2).values, 'chiusura': h.Close.round(2).values}).to_csv(OUT / 'indice_ftsemib.csv', index=False)
        print(f'{INDICE}: {len(h)} righe')
    except Exception as e:
        esiti.append(('FTSEMIB', INDICE, 0, '', '', str(e)[:200]))
        print(f'! indice: {e}')
    e = pd.DataFrame(esiti, columns=['ticker', 'simbolo', 'righe', 'prima_data', 'ultima_data', 'errore'])
    e.to_csv(OUT / 'esito_download.csv', index=False)
    print(f'Scaricati {(e.righe > 0).sum()} titoli su {len(e)}; dividendi: {len(divid)}; frazionamenti: {len(fraz)}')


if __name__ == '__main__':
    main()
