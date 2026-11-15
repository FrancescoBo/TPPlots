"""4trading: legge gli URL indicati in config/url_4trading.csv (colonna 'url'; può contenere {data:%Y-%m-%d} o {d}/{m}/{Y})."""
import pandas as pd
from . import comune as c, generico


def raccogli(ana, oggi, giorni=14):
    p = c.ROOT / 'config/url_4trading.csv'
    if not p.exists():
        return []
    modelli = pd.read_csv(p, dtype=str).fillna('').url.tolist()
    out = []
    for modello in modelli:
        if not modello.strip() or modello.startswith('#'):
            continue
        if '{' not in modello:
            out += generico.tabelle_html(modello, '4trading', ana, oggi)
            continue
        for i in range(giorni):
            d = oggi - pd.Timedelta(days=i)
            url = modello.format(data=d, d=d.day, m=d.month, Y=d.year)
            out += generico.tabelle_html(url, '4trading', ana, oggi, data_default=d)
    return out
