"""Segnale di oggi per la Finalista 2 (prova dal vivo sulla carta).

Strategia: classifica COMP (media dei ranghi percentuali di momentum a 120 sedute e saldo revisioni a 60 giorni) tra i titoli
con almeno 5 target validi e controvalore mediano giornaliero (60 sedute) >= 1 milione di euro; si tengono i primi 6
(K = 6, B = 0); ribilanciamento ogni 21 sedute a partire dal 2025-08-29; ordini all'apertura della seduta dopo il
giorno di ribilanciamento; ogni acquisto = patrimonio / 6 (reinvestimento).

Uso:  python3 -I ricerca/segnale_oggi.py [percorso_portafoglio.csv] [--liquidita EURO]
Il portafoglio ha colonne ticker, azioni, prezzo_carico (puo' essere vuoto). Senza portafoglio il patrimonio di
riferimento e' 20.000 euro in contanti; con un portafoglio e' il valore dei titoli piu' l'eventuale --liquidita.
Non e' un consiglio di investimento: e' lo strumento per seguire la regola sulla carta.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

sys.path.insert(0, str(Path(__file__).resolve().parent))  # il flag -I toglie la cartella dello script
import dati as D
import motore as M
import strategie as ST

K, B, R, L = 6, 0, 21, 1e6
ANCORA = pd.Timestamp('2025-08-29')           # primo giorno di decisione


# ------------------------------------------------------------------------------ calendario
def festivi_borsa(anno: int) -> set:
    """Giorni di chiusura ordinari di Borsa Italiana: 1/1, Venerdi' Santo, Lunedi' dell'Angelo, 1/5, 15/8, 24, 25, 26 e 31/12."""
    pasqua = easter(anno)
    return {date(anno, 1, 1), pasqua - timedelta(days=2), pasqua + timedelta(days=1), date(anno, 5, 1), date(anno, 8, 15),
            date(anno, 12, 24), date(anno, 12, 25), date(anno, 12, 26), date(anno, 12, 31)}


def sedute_future(ultima: pd.Timestamp, n: int) -> list:
    """Le prossime `n` sedute dopo `ultima` (giorni feriali non festivi; il calendario reale puo' avere chiusure straordinarie)."""
    out, d = [], ultima.date()
    while len(out) < n:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in festivi_borsa(d.year):
            out.append(pd.Timestamp(d))
    return out


def prossimo_ribilanciamento(cal: pd.DatetimeIndex, ancora: pd.Timestamp = ANCORA, passo: int = R):
    """(oggi_e_giorno_di_ribilanciamento, data del prossimo giorno di decisione, e' una data stimata?)."""
    i_anc = int(cal.searchsorted(ancora))
    i = len(cal) - 1
    resto = (i - i_anc) % passo
    if resto == 0:
        return True, cal[i], False
    manca = passo - resto
    return False, sedute_future(cal[i], manca)[-1], True


# ------------------------------------------------------------------------------ proposte
def proposte(ordine, tickers, portafoglio: pd.DataFrame, k: int = K, b: int = B):
    """Dato l'ordine (colonne dei titoli, dal migliore) e il portafoglio, ritorna (da_tenere, da_vendere, da_comprare, restano)."""
    top = [tickers[c] for c in ordine]
    tenere = top[:k]
    pos = {t: i for i, t in enumerate(top)}
    held = list(portafoglio.ticker) if len(portafoglio) else []
    vendere = [t for t in held if pos.get(t, 10 ** 6) >= k + b]
    restano = [t for t in held if t not in vendere]
    comprare = [t for t in tenere if t not in held][:max(0, k - len(restano))]
    return tenere, vendere, comprare, restano


def main(argv):
    percorso = Path(__file__).resolve().parent / 'portafoglio_prova.csv'
    liquidita = None
    a = list(argv)
    if '--liquidita' in a:
        j = a.index('--liquidita'); liquidita = float(a[j + 1]); del a[j:j + 2]
    if a:
        percorso = Path(a[0])
    ptf = pd.read_csv(percorso) if percorso.exists() else pd.DataFrame(columns=['ticker', 'azioni', 'prezzo_carico'])
    ultima = pd.Timestamp(pd.read_csv(D.RICERCA / 'indice_ftsemib.csv', parse_dates=['data']).data.max())
    mk = ST.Mercato(ultima)
    i = mk.n - 1
    rank, ordine = mk.ranghi('COMP', L)
    o = ordine[i]
    nomi = mk.an.set_index('ticker').nome if 'ticker' in mk.an.columns else mk.an.nome
    n_prezzi = int(mk.pr.chiusura.iloc[i].notna().sum())
    print(f"Segnale COMP del {mk.cal[i].date()} (ultima seduta nei dati; {n_prezzi} titoli con prezzo quel giorno)")
    print(f"Filtri: almeno 5 target validi negli ultimi 120 giorni, controvalore mediano 60 sedute >= {L / 1e6:g} mln EUR; "
          f"{len(o)} titoli ammessi con COMP calcolabile\n")
    tenere, vendere, comprare, restano = proposte(o, mk.tickers, ptf)
    cff = mk.cff[i]
    righe = []
    for pos_, c in enumerate(o[:15], 1):
        tk = mk.tickers[c]
        righe.append((pos_, tk, str(nomi.get(tk, ''))[:28], mk.comp[L][i, c], mk.seg['MOM'][i, c], mk.seg['REV'][i, c],
                      mk.cx.liq[i, c] / 1e6, cff[c], 'TENERE' if pos_ <= K else ''))
    print('Classifica (prime 15)')
    print(pd.DataFrame(righe, columns=['#', 'ticker', 'nome', 'COMP', 'MOM120', 'REV60', 'mln/giorno', 'ultimo', '']).to_string(
        index=False, float_format=lambda x: f'{x:.3f}'))
    oggi_giorno, prossimo, stimata = prossimo_ribilanciamento(mk.cal)
    print()
    if oggi_giorno:
        print(f"OGGI ({mk.cal[i].date()}) E' GIORNO DI RIBILANCIAMENTO: gli ordini vanno dati per l'apertura della seduta successiva.")
    else:
        print(f"Oggi NON e' giorno di ribilanciamento: le liste sotto mostrano cosa si farebbe oggi, ma la regola le applica solo il "
              f"{prossimo.date()}{' (data stimata con il calendario di Borsa Italiana)' if stimata else ''}, ordini all'apertura della seduta dopo.")
    # patrimonio di riferimento
    if len(ptf):
        valore = sum(float(r.azioni) * float(cff[mk.col[r.ticker]]) for r in ptf.itertuples() if r.ticker in mk.col)
        pat = valore + (liquidita or 0.0)
    else:
        pat = liquidita if liquidita is not None else M.CAPITALE
    blocco = pat / K
    print(f"\nPatrimonio di riferimento {pat:,.2f} EUR -> blocco per titolo {blocco:,.2f} EUR (patrimonio / {K})")
    print('Da tenere (primi 6):', ', '.join(tenere))
    if len(ptf):
        print('Portafoglio attuale:', ', '.join(f'{r.ticker} ({int(r.azioni)} azioni, carico {r.prezzo_carico})' for r in ptf.itertuples()))
        print('Da VENDERE (scesi oltre il 6o posto o non piu\' ammessi):', ', '.join(vendere) or 'nessuno')
    else:
        print('Portafoglio: vuoto')
    print('Da COMPRARE:', ', '.join(f"{t} (~{int(blocco // cff[mk.col[t]])} azioni a {cff[mk.col[t]]:.3f})" for t in comprare) or 'nessuno')
    print('\nCosti e tasse reali (commissione, Tobin 0,2%, slittamento, 26%) non inclusi nelle quantita'' indicate.')


if __name__ == '__main__':
    main(sys.argv[1:])
