"""
Calcola grafici e recap a partire dai CSV e scrive docs/data/dati.json,
letto dalla pagina docs/index.html.

  python scripts/costruisci.py [--oggi AAAA-MM-GG]

Logica (replica dei fogli di TargetPrice_Plots.xlsx):
- TP medio a una data D: per ogni emittente si prende il target piu' recente
  con data <= D; se e' piu' vecchio di VALIDITA_TP giorni viene escluso;
  poi media semplice sugli emittenti rimasti.
- Conteggio raccomandazioni: ultima raccomandazione di ciascun emittente,
  raggruppata nelle 5 classi di config/classi_raccomandazioni.csv.
- Delta rec: target / prezzo alla data della raccomandazione - 1.
- Giorni al target: giorni di calendario finche' il prezzo supera il target
  (0 se il target era gia' sotto il prezzo, vuoto se mai raggiunto).
- Variazione del target: confronto con il target precedente dello stesso
  emittente sullo stesso titolo (su / giu / invariato / primo).
- Titoli mostrati: quelli con almeno MIN_TARGET_ANNO target nell'ultimo anno
  (scripts/comune.py), salvo forzature nella colonna 'attivo'.
- Pareto: un titolo e' "Dominato" se un altro ha capitalizzazione e delta TP
  entrambi maggiori o uguali.
"""
import argparse, datetime as dt, json, math, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comune import ROOT, MIN_TARGET_ANNO, titoli_selezionati
VALIDITA_TP = 120          # giorni oltre i quali un target non conta piu' nel TP medio
FINESTRA_GRAFICO = 365     # giorni mostrati di default nei grafici
STORICO_TP_MEDIO = 730     # giorni per cui calcolare la serie del TP medio
CLASSI = ['Buy', 'Overweight', 'Neutral', 'Underweight', 'Sell']


def num(x, nd=4):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), nd)


def carica(oggi):
    titoli = titoli_selezionati(oggi)
    rac = pd.read_csv(ROOT / 'data/raccomandazioni.csv', parse_dates=['data'])
    mappa = pd.read_csv(ROOT / 'config/classi_raccomandazioni.csv')
    mappa = {k.strip().lower(): v for k, v in zip(mappa.raccomandazione, mappa.classe)}
    alias = pd.read_csv(ROOT / 'config/alias_emittenti.csv')
    alias = dict(zip(alias.nome_variante.str.strip(), alias.nome_standard.str.strip()))
    rac['emittente'] = rac.emittente.fillna('').astype(str).str.strip().replace(alias)
    rac['raccomandazione'] = rac.raccomandazione.fillna('').astype(str).str.strip()
    rac['classe'] = rac.raccomandazione.str.lower().map(mappa)
    # variazione rispetto al target precedente dello stesso emittente
    rac['_ord'] = range(len(rac))
    rac = rac.sort_values(['ticker', 'emittente', 'data', '_ord'], ascending=[True, True, True, False], kind='stable')
    prec = rac.dropna(subset=['target']).groupby(['ticker', 'emittente']).target.shift(1)
    rac['target_prec'] = prec
    def var(x):
        if pd.isna(x.target):
            return None
        if pd.isna(x.target_prec):
            return 'primo'
        if abs(x.target - x.target_prec) < 1e-9 * max(1, abs(x.target)):
            return 'invariato'
        return 'su' if x.target > x.target_prec else 'giu'
    rac['variazione'] = rac.apply(var, axis=1)
    rac = rac.sort_values('_ord').drop(columns='_ord')
    return titoli, rac


def ultimo_per_emittente(r, giorno):
    """Riga piu' recente (data <= giorno) per ciascun emittente."""
    r = r[r.data <= giorno]
    return r.sort_values('data', ascending=False, kind='stable').drop_duplicates('emittente')


def tp_medio(r_target, giorno):
    u = ultimo_per_emittente(r_target, giorno)
    u = u[(giorno - u.data).dt.days <= VALIDITA_TP]
    return (u.target.mean() if len(u) else None), len(u)


def analizza(t, rac, oggi):
    tk = t.ticker
    prezzi = pd.read_csv(ROOT / f'data/prezzi/{tk}.csv', parse_dates=['data']).dropna().sort_values('data')
    r = rac[rac.ticker == tk].copy()
    r = r.sort_values('data', ascending=False, kind='stable')
    r_target = r.dropna(subset=['target'])

    # delta alla data della raccomandazione e giorni per raggiungere il target
    s = prezzi.set_index('data').chiusura
    deltas, giorni = [], []
    for _, x in r.iterrows():
        p0 = s[:x.data]
        if pd.isna(x.target) or p0.empty:
            deltas.append(None); giorni.append(None); continue
        d = x.target / p0.iloc[-1] - 1
        deltas.append(d)
        if d < 0:
            giorni.append(0)
        else:
            dopo = s[(s.index > x.data) & (s > x.target)]
            giorni.append((dopo.index[0] - x.data).days if len(dopo) else None)
    r['delta_rec'] = deltas
    r['giorni_target'] = giorni

    # serie del TP medio sulle date di quotazione
    da = prezzi.data.max() - pd.Timedelta(days=STORICO_TP_MEDIO)
    serie = []
    for g in prezzi.data[prezzi.data >= da]:
        v, n = tp_medio(r_target, g)
        serie.append([g.date().isoformat(), num(v), n])

    # situazione attuale per emittente
    ult = ultimo_per_emittente(r, oggi)
    ult_t = ultimo_per_emittente(r_target, oggi)
    n_rac = r.groupby('emittente').size()
    emittenti = []
    for _, x in ult.iterrows():
        tt = ult_t[ult_t.emittente == x.emittente]
        tgt, dtgt = (tt.target.iloc[0], tt.data.iloc[0]) if len(tt) else (None, None)
        valido = dtgt is not None and (oggi - dtgt).days <= VALIDITA_TP
        emittenti.append({'emittente': x.emittente, 'data': x.data.date().isoformat(),
                          'raccomandazione': x.raccomandazione, 'classe': x.classe if isinstance(x.classe, str) else None,
                          'target': num(tgt), 'data_target': dtgt.date().isoformat() if dtgt is not None else None,
                          'target_valido': bool(valido), 'n_raccomandazioni': int(n_rac[x.emittente])})
    tp, n_tp = tp_medio(r_target, oggi)
    prezzo = s.iloc[-1]
    conteggi = {c: int((ult.classe == c).sum()) for c in CLASSI}
    azioni = int(t.azioni_circolazione) if not pd.isna(t.azioni_circolazione) else None

    recap = {'ticker': tk, 'nome': t.nome, 'settore': t.settore,
             'prezzo': num(prezzo), 'data_prezzo': s.index[-1].date().isoformat(),
             'tp_medio': num(tp), 'tp_meno_10': num(tp / 1.1 if tp else None), 'n_target_validi': n_tp,
             'delta_tp': num(tp / prezzo - 1 if tp else None),
             'capitalizzazione': num(prezzo * azioni, 0) if azioni else None,
             'ultima_raccomandazione': r.data.max().date().isoformat() if len(r) else None,
             **conteggi}
    dettaglio = {
        'ticker': tk, 'nome': t.nome,
        'prezzi': [[d.date().isoformat(), num(v)] for d, v in s.items()],
        'tp_medio': serie,
        'raccomandazioni': [{'data': x.data.date().isoformat(), 'emittente': x.emittente,
                             'raccomandazione': x.raccomandazione,
                             'classe': x.classe if isinstance(x.classe, str) else None,
                             'target': num(x.target), 'target_prec': num(x.target_prec),
                             'variazione': x.variazione if isinstance(x.variazione, str) else None, 'delta_rec': num(x.delta_rec),
                             'giorni_target': None if x.giorni_target is None or pd.isna(x.giorni_target) else int(x.giorni_target)}
                            for _, x in r.iterrows()],
        'emittenti': sorted(emittenti, key=lambda e: e['emittente'].lower()),
    }
    return recap, dettaglio


def pareto(recap):
    for a in recap:
        if a['capitalizzazione'] is None or a['delta_tp'] is None:
            a['pareto'] = None; continue
        dominato = any(b is not a and b['capitalizzazione'] is not None and b['delta_tp'] is not None
                       and b['capitalizzazione'] >= a['capitalizzazione'] and b['delta_tp'] >= a['delta_tp']
                       for b in recap)
        a['pareto'] = 'Dominato' if dominato else 'Pareto'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--oggi', help='data di riferimento (default: oggi)')
    a = ap.parse_args()
    oggi = pd.Timestamp(a.oggi) if a.oggi else pd.Timestamp(dt.date.today())
    titoli, rac = carica(oggi)
    recap, dettagli, mancanti = [], {}, []
    for t in titoli.itertuples():
        if not (ROOT / f'data/prezzi/{t.ticker}.csv').exists():
            print(f'! {t.ticker}: manca data/prezzi/{t.ticker}.csv (lancia aggiorna_prezzi.py), salto')
            mancanti.append(t.ticker); continue
        rc, de = analizza(t, rac, oggi)
        recap.append(rc); dettagli[t.ticker] = de
    pareto(recap)
    recap.sort(key=lambda x: (-x['Buy'], -(x['delta_tp'] or -9)))
    out = {'generato': dt.datetime.now().isoformat(timespec='minutes'), 'data_riferimento': oggi.date().isoformat(),
           'parametri': {'validita_tp_giorni': VALIDITA_TP, 'finestra_grafico_giorni': FINESTRA_GRAFICO,
                         'min_target_anno': MIN_TARGET_ANNO}, 'senza_prezzi': mancanti,
           'classi': CLASSI, 'recap': recap, 'titoli': dettagli}
    (ROOT / 'docs/data').mkdir(parents=True, exist_ok=True)
    (ROOT / 'docs/data/dati.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'ok: {len(recap)} titoli -> docs/data/dati.json')


if __name__ == '__main__':
    main()
