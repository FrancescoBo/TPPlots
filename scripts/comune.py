"""Funzioni condivise: elenco titoli e scelta di quelli da mostrare."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MIN_TARGET_ANNO = 10   # un titolo compare nella pagina se ha almeno tanti target negli ultimi 365 giorni


def titoli_selezionati(oggi=None):
    """Titoli con >= MIN_TARGET_ANNO target nell'ultimo anno.
    In config/titoli.csv la colonna 'attivo' forza: 1 = sempre, 0 = mai, vuoto = automatico."""
    oggi = pd.Timestamp(oggi) if oggi is not None else pd.Timestamp.today().normalize()
    titoli = pd.read_csv(ROOT / 'config/titoli.csv', dtype={'attivo': str, 'azioni_circolazione': 'Int64'})
    titoli['attivo'] = titoli.attivo.fillna('').str.strip()
    rac = pd.read_csv(ROOT / 'data/raccomandazioni.csv', parse_dates=['data'])
    rac = rac[(rac.data > oggi - pd.Timedelta(days=365)) & (rac.data <= oggi) & rac.target.notna()]
    n = rac.groupby('ticker').size()
    titoli['target_anno'] = titoli.ticker.map(n).fillna(0).astype(int)
    scelti = titoli[(titoli.attivo == '1') | ((titoli.attivo != '0') & (titoli.target_anno >= MIN_TARGET_ANNO))]
    return scelti.reset_index(drop=True)
