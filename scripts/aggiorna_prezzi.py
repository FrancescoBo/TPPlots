"""
Aggiorna data/prezzi/<TICKER>.csv con le chiusure giornaliere da Yahoo Finance
(simbolo in config/titoli.csv, colonna simbolo_yahoo, es. ENI.MI).
Se mancano, compila anche numero di azioni e settore in config/titoli.csv.

  python scripts/aggiorna_prezzi.py            # titoli mostrati nella pagina
  python scripts/aggiorna_prezzi.py --tutti    # tutti i titoli in config
  python scripts/aggiorna_prezzi.py --da 2025-01-01   # riscarica da una data
"""
import argparse, sys
from pathlib import Path
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import ROOT, titoli_selezionati


def titoli_minmax():
    """Ticker per cui salvare anche minimo e massimo giornalieri (elenco in config/minmax.csv, colonna 'ticker'; 'tutti' = tutti)."""
    p = ROOT / 'config/minmax.csv'
    if not p.exists():
        return set()
    return set(pd.read_csv(p, dtype=str).fillna('').ticker.str.strip()) - {''}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tutti', action='store_true')
    ap.add_argument('--da')
    a = ap.parse_args()
    cfg_path = ROOT / 'config/titoli.csv'
    cfg = pd.read_csv(cfg_path, dtype=str).fillna('')
    titoli = cfg if a.tutti else cfg[cfg.ticker.isin(titoli_selezionati().ticker)]
    errori = 0
    mm = titoli_minmax()
    for t in titoli.itertuples():
        f = ROOT / f'data/prezzi/{t.ticker}.csv'
        old = pd.read_csv(f, parse_dates=['data']) if f.exists() else pd.DataFrame({'data': pd.to_datetime([]), 'chiusura': []})
        vuole_mm = 'tutti' in mm or t.ticker in mm
        manca_mm = vuole_mm and ('minimo' not in old or old.minimo.notna().sum() < 0.9 * old.chiusura.notna().sum())   # primo giro: riscarica tutto lo storico con min/max
        start = pd.Timestamp(a.da) if a.da else (old.data.max() - pd.Timedelta(days=10) if len(old) and not manca_mm else pd.Timestamp('2025-01-01'))
        yt = yf.Ticker(t.simbolo_yahoo)
        try:
            h = yt.history(start=start.date().isoformat(), interval='1d', auto_adjust=False)
        except Exception as e:  # rete, simbolo errato...
            print(f'! {t.ticker}: {e}'); errori += 1; continue
        if h.empty:
            print(f'! {t.ticker} ({t.simbolo_yahoo}): nessun dato'); errori += 1; continue
        new = pd.DataFrame({'data': pd.to_datetime(h.index.tz_localize(None).date), 'chiusura': h.Close.round(4).values})
        if vuole_mm:
            new['minimo'] = h.Low.round(4).values
            new['massimo'] = h.High.round(4).values
        out = pd.concat([old[~old.data.isin(new.data)], new]).sort_values('data')
        out['data'] = out.data.dt.date.astype(str)
        out.to_csv(f, index=False)
        print(f'{t.ticker}: {len(new)} righe scaricate, ultima {out.data.iloc[-1]}')

        # dati anagrafici mancanti
        if not t.azioni_circolazione or not t.settore:
            try:
                info = yt.info
                i = cfg.index[cfg.ticker == t.ticker][0]
                if not t.azioni_circolazione and info.get('sharesOutstanding'):
                    cfg.at[i, 'azioni_circolazione'] = str(int(info['sharesOutstanding']))
                if not t.settore and info.get('industry'):
                    cfg.at[i, 'settore'] = info['industry']
            except Exception as e:
                print(f'  ({t.ticker}: anagrafica non disponibile: {e})')
    cfg.to_csv(cfg_path, index=False)
    sys.exit(1 if len(titoli) and errori == len(titoli) else 0)


if __name__ == '__main__':
    main()
