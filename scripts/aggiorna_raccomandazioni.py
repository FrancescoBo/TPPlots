"""Raccolta quotidiana delle raccomandazioni da più fonti, deduplica e aggiornamento di data/raccomandazioni.csv.

Uso:  python scripts/aggiorna_raccomandazioni.py [--oggi YYYY-MM-DD] [--giorni N] [--storico] [--solo fonte1,fonte2]

Modalità di ogni fonte (config/fonti.csv):  attiva = scrive nel dataset;  prova = scrive in data/in_verifica.csv;  off = ignorata.
Regole di deduplica (stesso ticker + stesso emittente):
  - stessa data                               -> doppione (se il target differisce: conflitto, resta il primo e viene registrato);
  - date entro 4 giorni, stesso target e stesso giudizio -> doppione (la stessa notizia riportata da fonti diverse);
  - la fonte con priorità più alta (numero più basso) passa per prima.
"""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raccolta import comune as c                                   # noqa: E402
from raccolta import equita, intesa, quattro_trading, soldionline, teleborsa, ubs   # noqa: E402

ROOT = c.ROOT
FINESTRA_DOPPIONI = 4      # giorni
SOLO_VARIAZIONI = {'intesa'}   # fonti che ripetono giudizio e target a ogni pubblicazione: si tiene solo ciò che cambia
DATA_MINIMA = pd.Timestamp('2025-01-01')   # prima di questa data non si importa nulla (le quotazioni partono da lì)
MINUTI_PER_FONTE = 12      # tempo massimo per ogni fonte
SCARTO_MAX = 4.0           # un target fuori da [1/4, 4] volte la mediana storica del titolo va in quarantena


def raccoglitori(oggi, giorni, storico):
    r = {
        'ubs': lambda a: ubs.raccogli(a, oggi, max(giorni, 45) if not storico else 400),
        'soldionline': lambda a: soldionline.giornaliero(a, oggi, giorni) + (soldionline.storico(a, oggi, 400) if storico else []),
        'equita': lambda a: equita.raccogli(a, oggi, giorni if not storico else 400),
        'intesa': lambda a: intesa.raccogli(a, oggi, giorni if not storico else 400),
        '4trading': lambda a: quattro_trading.raccogli(a, oggi, giorni if not storico else 400, 14 if storico else 0),
        'teleborsa': lambda a: teleborsa.raccogli(a, oggi, giorni),
    }
    return r


def df_da_record(rec):
    d = pd.DataFrame(rec, columns=c.COLONNE + ['fonte'])
    if d.empty:
        return d
    d['data'] = pd.to_datetime(d.data).dt.normalize()
    d['raccomandazione'] = d.raccomandazione.fillna('')
    return d


def ripete_precedente(r, per_chiave, classi):
    """True se l'ultimo giudizio dello stesso emittente sul titolo (data <= r.data) ha già stesso target e stessa classe."""
    prec = [e for e in per_chiave.get((r.ticker, r.emittente), []) if e['data'] <= r.data]
    if not prec:
        return False
    e = max(prec, key=lambda x: x['data'])
    stesso_t = pd.notna(r.target) and pd.notna(e['target']) and abs(r.target - e['target']) < 1e-9
    cl = lambda v: classi.get(str(v).lower(), str(v).lower())
    return bool(stesso_t and (not r.raccomandazione or not e['raccomandazione'] or cl(r.raccomandazione) == cl(e['raccomandazione'])))


def aggiungi_se_nuovo(r, esistenti, per_chiave, classi):
    """Ritorna (esito, motivo): esito in {'nuovo','doppione','conflitto'}."""
    for e in per_chiave.get((r.ticker, r.emittente), []):
        dd = abs((e['data'] - r.data).days)
        if dd == 0:
            tgt_diverso = pd.notna(r.target) and pd.notna(e['target']) and abs(r.target - e['target']) > 1e-9
            return ('conflitto', f"{e['target']} vs {r.target}") if tgt_diverso else ('doppione', '')
        if dd <= FINESTRA_DOPPIONI:
            stesso_t = (pd.isna(r.target) and pd.isna(e['target'])) or (
                pd.notna(r.target) and pd.notna(e['target']) and abs(r.target - e['target']) < 1e-9)
            stessa_c = classi.get(str(r.raccomandazione).lower(), r.raccomandazione) == classi.get(str(e['raccomandazione']).lower(), e['raccomandazione']) \
                or not r.raccomandazione or not e['raccomandazione']
            if stesso_t and stessa_c:
                return 'doppione', ''
    return 'nuovo', ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--oggi')
    ap.add_argument('--giorni', type=int, default=14, help='finestra di raccolta giornaliera')
    ap.add_argument('--storico', action='store_true', help='recupero esteso (pagine per titolo, ~400 giorni)')
    ap.add_argument('--solo', help='elenco fonti separate da virgola')
    a = ap.parse_args()
    oggi = pd.Timestamp(a.oggi) if a.oggi else pd.Timestamp.today().normalize()

    ana = c.Anagrafica()
    fonti = pd.read_csv(ROOT / 'config/fonti.csv', dtype=str).fillna('')
    fonti['priorita'] = fonti.priorita.astype(int)
    fonti = fonti.sort_values('priorita', kind='stable')
    if a.solo:
        fonti = fonti[fonti.fonte.isin(a.solo.split(','))]
    funzioni = raccoglitori(oggi, a.giorni, a.storico)

    rac = pd.read_csv(ROOT / 'data/raccomandazioni.csv', parse_dates=['data'])
    rac['emittente'] = rac.emittente.fillna('').astype(str).map(ana.emittente)
    rac['raccomandazione'] = rac.raccomandazione.fillna('').astype(str)
    # titoli non più quotati: si eliminano le righe successive alla revoca (errori di associazione)
    rimosse = 0
    for tk, rev in ana.estinti.items():
        m = (rac.ticker == tk) & (rac.data > rev)
        rimosse += int(m.sum())
        rac = rac[~m]
    recenti = rac[rac.data > oggi - pd.Timedelta(days=365)].copy()
    recenti['target'] = recenti.target * [c.fattore_target(t, d) for t, d in zip(recenti.ticker, recenti.data)]
    ref = recenti.groupby('ticker').target.median().to_dict()
    per_chiave = {}
    for r in rac.itertuples():
        per_chiave.setdefault((r.ticker, r.emittente), []).append({'data': r.data, 'target': r.target, 'raccomandazione': r.raccomandazione})

    nuove, verifica, quarantena, conflitti = [], [], [], []
    stato = {'eseguito_il': pd.Timestamp.now().isoformat(timespec='minutes'), 'fonti': {}}
    for f in fonti.itertuples():
        info = stato['fonti'][f.fonte] = {'modalita': f.modalita, 'lette': 0, 'nuove': 0, 'doppioni': 0, 'quarantena': 0, 'conflitti': 0, 'errore': ''}
        if f.modalita == 'off' or f.fonte not in funzioni:
            continue
        c.SCADENZA[0] = time.time() + (25 if a.storico else MINUTI_PER_FONTE) * 60
        c.FALLIMENTI.clear()
        t0 = time.time()
        try:
            d = df_da_record(funzioni[f.fonte](ana))
        except Exception:
            info['errore'] = traceback.format_exc(limit=2).strip().splitlines()[-1]
            print(f'[{f.fonte}] ERRORE: {info["errore"]}')
            continue
        d = d[(d.data <= oggi + pd.Timedelta(days=1)) & (d.data >= DATA_MINIMA)] if not d.empty else d
        info['lette'] = len(d)
        if time.time() > c.SCADENZA[0]:
            info['errore'] = 'tempo massimo raggiunto: dati parziali'
            print(f'[{f.fonte}] tempo massimo raggiunto, dati parziali')
        for r in d.itertuples(index=False):
            # controllo di plausibilità sul target
            rif = ref.get(r.ticker)
            t_conf = r.target * c.fattore_target(r.ticker, r.data) if pd.notna(r.target) else None
            if t_conf is not None and rif and not (rif / SCARTO_MAX <= t_conf <= rif * SCARTO_MAX):
                quarantena.append(dict(r._asdict(), motivo=f'target {r.target} lontano dalla mediana {rif:.2f}'))
                info['quarantena'] += 1
                continue
            if f.modalita == 'prova':
                esito, _ = aggiungi_se_nuovo(r, None, per_chiave, ana.classi)
                if esito == 'nuovo' and f.fonte in SOLO_VARIAZIONI and ripete_precedente(r, per_chiave, ana.classi):
                    esito = 'doppione'
                if esito == 'nuovo':
                    verifica.append(r._asdict())
                    info['nuove'] += 1
                else:
                    info['doppioni'] += 1
                continue
            esito, motivo = aggiungi_se_nuovo(r, None, per_chiave, ana.classi)
            if esito == 'nuovo' and f.fonte in SOLO_VARIAZIONI and ripete_precedente(r, per_chiave, ana.classi):
                esito = 'doppione'
            if esito == 'nuovo':
                nuove.append(r._asdict())
                per_chiave.setdefault((r.ticker, r.emittente), []).append({'data': r.data, 'target': r.target, 'raccomandazione': r.raccomandazione})
                info['nuove'] += 1
            elif esito == 'conflitto':
                conflitti.append(dict(r._asdict(), motivo=motivo))
                info['conflitti'] += 1
            else:
                info['doppioni'] += 1
        print(f"[{f.fonte}] {f.modalita}: lette {info['lette']}, nuove {info['nuove']}, doppioni {info['doppioni']}, "
              f"quarantena {info['quarantena']}, conflitti {info['conflitti']}")

    # --- scrittura
    adesso = pd.Timestamp.now().isoformat(timespec='minutes')
    if rimosse:
        print(f'Rimosse {rimosse} righe di titoli non più quotati (config/ticker_estinti.csv)')
    if rimosse and not nuove:
        out = rac.copy()
        out['data'] = out.data.dt.strftime('%Y-%m-%d')
        out[c.COLONNE].to_csv(ROOT / 'data/raccomandazioni.csv', index=False)
    if nuove:
        n = pd.DataFrame(nuove)
        n['acquisito_il'] = adesso
        audit = ROOT / 'data/raccomandazioni_fonti.csv'
        n[c.COLONNE + ['fonte', 'acquisito_il']].to_csv(audit, mode='a', header=not audit.exists(), index=False)
        orig = pd.read_csv(ROOT / 'data/raccomandazioni.csv', parse_dates=['data'])
        for tk, rev in ana.estinti.items():
            orig = orig[~((orig.ticker == tk) & (orig.data > rev))]
        tot = pd.concat([n[c.COLONNE], orig], ignore_index=True)
        tot = tot.sort_values(['ticker', 'data'], ascending=[True, False], kind='stable')
        tot['data'] = tot.data.dt.strftime('%Y-%m-%d')
        tot.to_csv(ROOT / 'data/raccomandazioni.csv', index=False)
    for nome, lista in (('in_verifica', verifica), ('quarantena', quarantena), ('conflitti', conflitti)):
        if lista:
            p = ROOT / f'data/{nome}.csv'
            x = pd.DataFrame(lista)
            x['acquisito_il'] = adesso
            if p.exists():
                x = pd.concat([pd.read_csv(p), x.assign(data=x.data.dt.strftime('%Y-%m-%d'))], ignore_index=True)
            else:
                x['data'] = pd.to_datetime(x.data).dt.strftime('%Y-%m-%d')
            x.drop_duplicates(subset=['ticker', 'data', 'emittente', 'target', 'fonte']).to_csv(p, index=False)
    if ana.non_riconosciuti:
        p = ROOT / 'data/non_riconosciuti.csv'
        x = pd.DataFrame([(n, f, k, adesso) for (n, f), k in ana.non_riconosciuti.items()], columns=['nome', 'fonte', 'occorrenze', 'visto_il'])
        if p.exists():
            x = pd.concat([pd.read_csv(p), x], ignore_index=True).drop_duplicates(subset=['nome', 'fonte'], keep='last')
        x.to_csv(p, index=False)
    stato['nuove_totali'] = len(nuove)
    stato['emittenti_nuovi'] = sorted({n['emittente'] for n in nuove} - set(ana.emittenti_noti.values()))
    if stato['emittenti_nuovi']:
        print('Emittenti mai visti (valuta un alias in config/alias_emittenti.csv):', stato['emittenti_nuovi'])
    stato['non_riconosciuti'] = len(ana.non_riconosciuti)
    (ROOT / 'docs/data').mkdir(parents=True, exist_ok=True)
    (ROOT / 'docs/data/stato_raccolta.json').write_text(json.dumps(stato, ensure_ascii=False, indent=1))
    print(f'Totale nuove righe nel dataset: {len(nuove)}')
    # esito: errore solo se tutte le fonti attive sono fallite
    attive = [v for v in stato['fonti'].values() if v['modalita'] == 'attiva']
    sys.exit(1 if attive and all(v['errore'] for v in attive) else 0)


if __name__ == '__main__':
    main()
