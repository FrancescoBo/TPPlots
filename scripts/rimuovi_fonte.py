"""Rimuove da data/raccomandazioni.csv le righe aggiunte da una fonte (elenco in data/raccomandazioni_fonti.csv).
Uso: python scripts/rimuovi_fonte.py --fonte intesa [--da AAAA-MM-GG] [--prima AAAA-MM-GG]
  --da: solo righe dalla data in poi;  --prima: solo righe PRECEDENTI alla data (es. pulizia dello storico troppo vecchio)."""
import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def chiave(d):
    t = pd.to_numeric(d.target, errors='coerce').map(lambda v: '' if pd.isna(v) else f'{v:.4f}')
    return (d.ticker.astype(str) + '|' + pd.to_datetime(d.data).dt.strftime('%Y-%m-%d') + '|' + d.emittente.fillna('').astype(str)
            + '|' + d.raccomandazione.fillna('').astype(str) + '|' + t)


ap = argparse.ArgumentParser()
ap.add_argument('--fonte', required=True)
ap.add_argument('--da')
ap.add_argument('--prima')
a = ap.parse_args()
aud_p = ROOT / 'data/raccomandazioni_fonti.csv'
aud = pd.read_csv(aud_p)
sel = aud[aud.fonte == a.fonte]
if a.da:
    sel = sel[pd.to_datetime(sel.data) >= pd.Timestamp(a.da)]
if a.prima:
    sel = sel[pd.to_datetime(sel.data) < pd.Timestamp(a.prima)]
rac = pd.read_csv(ROOT / 'data/raccomandazioni.csv')
da_togliere = set(chiave(sel))
k = chiave(rac)
mask = k.isin(da_togliere)
print(f'Righe di "{a.fonte}" registrate: {len(sel)}; rimosse dal dataset: {int(mask.sum())}')
rac[~mask].to_csv(ROOT / 'data/raccomandazioni.csv', index=False)
aud[~aud.index.isin(sel.index)].to_csv(aud_p, index=False)
