"""Prova delle fonti storiche: per ogni fonte misura se risponde e quanto indietro nel tempo arriva.

Si lancia da GitHub Actions (workflow "prova-fonti"), ma funziona anche a mano:
    python storico/prova_fonti.py [--solo 1,3,7] [--out data/storico/prova_fonti_esito.md]

Scrive data/storico/prova_fonti_esito.md (una sezione per prova) e lo stampa nel log.
Regole di buona educazione: 1,5 s di pausa tra due richieste allo stesso sito, User-Agent descrittivo,
nessun errore ferma le altre prove (ogni prova e ogni elemento sono isolati).

Prove: 1 Soldionline, 2 4trading, 3 UBS, 4 Consob (posizioni corte nette), 5 filings.xbrl.org,
       6 Yahoo (yfinance), 7 FRED.
"""
import argparse
import io
import json
import re
import sys
import time
import traceback
import urllib.parse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USCITA = ROOT / 'data/storico/prova_fonti_esito.md'
UA = ('Mozilla/5.0 (compatible; TPPlots-prova-fonti/1.0; +https://github.com/francescobo/TPPlots; '
      'verifica occasionale della disponibilita di dati storici)')
PAUSA = 1.5          # secondi tra due richieste allo stesso sito
TIMEOUT = 30

# --- scelte documentate -------------------------------------------------------------------------
# Soldionline: un titolo grande, uno medio, uno piccolo (da config/isin_soldionline.csv) + due non piu' quotati.
SOLDI_TITOLI = [('ISP', 'IT0000072618', 'grande'), ('MAIRE', 'IT0004931058', 'medio'),
                ('SIAV', 'IT0005504128', 'piccolo'),
                ('ATL (Atlantia)', 'IT0003506190', 'non piu quotato'),
                ('MS (Mediaset)', 'IT0001063210', 'non piu quotato')]
SOLDI_MAX_PAGINE = 80
QUATTRO_IDS = [150738, 140000, 125000, 110000, 95000, 80000]
QUATTRO_SCAN_CENTRI = [150738, 110000, 80000]
QUATTRO_SCAN_N = 150
UBS_PAGINE = [('Enel', 'https://research.ibb.ubs.com/openaccess/compliance/226741_1_new.html'),
              ('Eni', 'https://research.ibb.ubs.com/openaccess/compliance/114073_1_new.html')]
CONSOB_PAGINA = 'https://www.consob.it/web/area-pubblica/pnc'
XBRL_API = 'https://filings.xbrl.org/api/filings'
XBRL_BASE = 'https://filings.xbrl.org'
YAHOO_ENI = ('ENI.MI', '2015-01-01')
YAHOO_DELISTED = ['ATL.MI', 'MS.MI', 'CERV.MI', 'AGL.MI', 'TOD.MI', 'SRS.MI']
YAHOO_INDICI = ['FTSEMIB.MI', '^STOXX50E', '^VIX', '^V2TX', 'EURUSD=X', 'BZ=F']
YAHOO_MIDCAP = ['FTITLMS.MI', 'FTSEMC.MI', 'FTMIDCAP.MI']
FRED = [('Italia 10 anni', 'IRLTLT01ITM156N'), ('Germania 10 anni', 'IRLTLT01DEM156N')]
FRED_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id='


# ======================================================================== rete
class Rete:
    """Richieste HTTP con pausa per sito e User-Agent. `sessione`, `dormi` e `orologio` sono sostituibili nei test."""

    def __init__(self, sessione=None, dormi=time.sleep, orologio=time.monotonic, pausa=PAUSA):
        if sessione is None:
            import requests
            sessione = requests.Session()
        self.s = sessione
        self.s.headers.update({'User-Agent': UA, 'Accept-Language': 'it,en;q=0.8'})
        self.dormi, self.orologio, self.pausa = dormi, orologio, pausa
        self.ultima = {}

    def get(self, url, **kw):
        """GET con pausa; un solo nuovo tentativo su errore di rete o 5xx. Ritorna la risposta (anche 404)."""
        host = urllib.parse.urlparse(url).netloc
        ultimo_errore = None
        for tentativo in range(2):
            t = self.ultima.get(host)
            if t is not None:
                attesa = self.pausa - (self.orologio() - t)
                if attesa > 0:
                    self.dormi(attesa)
            try:
                r = self.s.get(url, timeout=TIMEOUT, **kw)
            except Exception as e:
                self.ultima[host] = self.orologio()
                ultimo_errore = e
                continue
            self.ultima[host] = self.orologio()
            if r.status_code >= 500 and tentativo == 0:
                ultimo_errore = RuntimeError(f'HTTP {r.status_code}')
                continue
            return r
        raise ultimo_errore


# ======================================================================== utilita
MESI = {'gen': 1, 'gennaio': 1, 'feb': 2, 'febbraio': 2, 'mar': 3, 'marzo': 3, 'apr': 4, 'aprile': 4,
        'mag': 5, 'maggio': 5, 'giu': 6, 'giugno': 6, 'lug': 7, 'luglio': 7, 'ago': 8, 'agosto': 8,
        'set': 9, 'settembre': 9, 'ott': 10, 'ottobre': 10, 'nov': 11, 'novembre': 11, 'dic': 12, 'dicembre': 12,
        'jan': 1, 'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
        'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9, 'oct': 10,
        'october': 10, 'november': 11, 'dec': 12, 'december': 12}


def _valida(a, m, g):
    import datetime as dt
    try:
        return dt.date(a, m, g)
    except ValueError:
        return None


def cerca_data(s):
    """Prima data trovata in un testo: 31/12/2020, 31-12-20, 2020-12-31, '31 dicembre 2020', '31 Dec 2020'. None se manca."""
    s = s or ''
    m = re.search(r'(?<!\d)(20\d\d|19\d\d)-(\d{1,2})-(\d{1,2})(?!\d)', s)
    if m:
        d = _valida(int(m[1]), int(m[2]), int(m[3]))
        if d:
            return d
    m = re.search(r'(?<!\d)(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4}|\d{2})(?!\d)', s)
    if m:
        a = int(m[3])
        a += 2000 if a < 100 else 0
        d = _valida(a, int(m[2]), int(m[1]))
        if d:
            return d
    m = re.search(r'(?<!\d)(\d{1,2})[\s\-/.]+([A-Za-zà-ù]+)\.?,?[\s\-/.]+(\d{4})', s)
    if m and m[2].lower() in MESI:
        d = _valida(int(m[3]), MESI[m[2].lower()], int(m[1]))
        if d:
            return d
    return None


class _Tabelle(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tabelle, self._riga, self._cella, self._prof = [], None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self._prof += 1
            self.tabelle.append([])
        elif tag == 'tr' and self._prof:
            self._riga = []
        elif tag in ('td', 'th') and self._riga is not None:
            self._cella = []
        elif tag == 'br' and self._cella is not None:
            self._cella.append(' ')

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._cella is not None and self._riga is not None:
            self._riga.append(' '.join(''.join(self._cella).split()))
            self._cella = None
        elif tag == 'tr' and self._riga is not None and self.tabelle:
            if self._riga:
                self.tabelle[-1].append(self._riga)
            self._riga = None
        elif tag == 'table' and self._prof:
            self._prof -= 1

    def handle_data(self, d):
        if self._cella is not None:
            self._cella.append(d)


def righe_tabelle(html):
    """Tutte le righe di tutte le tabelle: lista di liste di stringhe."""
    p = _Tabelle()
    p.feed(html or '')
    return [r for t in p.tabelle for r in t]


def righe_con_data(html):
    """Righe di tabella la cui prima cella e' una data: [(data, [celle...])]."""
    out = []
    for r in righe_tabelle(html):
        if len(r) >= 2:
            d = cerca_data(r[0])
            if d:
                out.append((d, r))
    return out


def titolo_pagina(html):
    m = re.search(r'(?is)<title[^>]*>(.*?)</title>', html or '')
    if m:
        return ' '.join(re.sub(r'(?s)<[^>]+>', ' ', m[1]).split())
    m = re.search(r'(?is)<h1[^>]*>(.*?)</h1>', html or '')
    return ' '.join(re.sub(r'(?s)<[^>]+>', ' ', m[1]).split()) if m else ''


def titolo_articolo(html):
    """Titolo dell'articolo: preferisce <h1>, poi og:title, poi <title>."""
    m = re.search(r'(?is)<h1[^>]*>(.*?)</h1>', html or '')
    if m:
        t = ' '.join(re.sub(r'(?s)<[^>]+>', ' ', m[1]).split())
        if t:
            return t
    m = re.search(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)', html or '')
    if m and m[1].strip():
        return m[1].strip()
    return titolo_pagina(html)


def testo(html):
    h = re.sub(r'(?is)<(script|style).*?</\1>', ' ', html or '')
    h = re.sub(r'(?s)<[^>]+>', ' ', h)
    import html as hh
    return ' '.join(hh.unescape(h).split())


def assoluto(base, href):
    return urllib.parse.urljoin(base, href.replace('&amp;', '&'))


def per_anno(date):
    c = Counter(d.year for d in date)
    return ', '.join(f'{a}: {c[a]}' for a in sorted(c)) or '-'


def f(d):
    return d.isoformat() if hasattr(d, 'isoformat') else str(d)


class Sezione:
    """Risultato di una prova: elenco di righe di testo e di sotto-esiti (ok/non ok)."""

    def __init__(self, titolo):
        self.titolo, self.righe, self.esiti = titolo, [], []

    def riga(self, s=''):
        self.righe.append(s)

    def elemento(self, nome, ok, dettaglio=''):
        self.esiti.append(ok)
        self.righe.append(f'- **{nome}**: {"OK" if ok else "NON FUNZIONA"}' + (f' - {dettaglio}' if dettaglio else ''))

    @property
    def ok(self):
        return any(self.esiti)

    def markdown(self):
        return '\n'.join([f'## {self.titolo}: {"OK" if self.ok else "NON FUNZIONA"}', ''] + self.righe + [''])


def isola(sez, nome, fn, *a):
    """Esegue fn(*a) -> (ok, dettaglio); un'eccezione diventa NON FUNZIONA con il testo dell'errore."""
    try:
        ok, det = fn(*a)
    except Exception as e:
        ok, det = False, f'errore: {type(e).__name__}: {str(e)[:300]}'
    sez.elemento(nome, ok, det)


# ======================================================================== 1. Soldionline
def _link_pagine(html, base, isin):
    """Link di paginazione della pagina di un titolo (rel=next, 'pag...', page=, /2.html...)."""
    out = []
    for h in re.findall(r'href=["\']([^"\']+)["\']', html):
        h2 = h.replace('&amp;', '&')
        if isin in h2 and re.search(r'pag|[?&]p=|[?&]page=|/\d+\.html$|_\d+\.html$', h2, re.I):
            out.append(assoluto(base, h2))
    m = re.search(r'(?is)<link[^>]+rel=["\']next["\'][^>]+href=["\']([^"\']+)', html)
    if m:
        out.append(assoluto(base, m[1]))
    m = re.search(r'(?is)<a[^>]+rel=["\']next["\'][^>]+href=["\']([^"\']+)', html)
    if m:
        out.append(assoluto(base, m[1]))
    return out


def prova_soldionline_titolo(rete, nome, isin, tipo):
    url0 = f'https://www.soldionline.it/raccomandazioni/{isin}.html'
    coda, visti, righe, pagine, campioni, errori = [url0], set(), [], 0, [], []
    while coda and pagine < SOLDI_MAX_PAGINE:
        u = coda.pop(0)
        if u in visti:
            continue
        visti.add(u)
        r = rete.get(u)
        if r.status_code != 200:
            errori.append(f'{u} -> HTTP {r.status_code}')
            if pagine == 0:
                return False, f'{tipo}: prima pagina HTTP {r.status_code} ({u})'
            continue
        pagine += 1
        rr = righe_con_data(r.text)
        righe += rr
        for d, cel in rr:
            if len(campioni) < 3:
                campioni.append(' | '.join(cel[:5]))
        for l in _link_pagine(r.text, u, isin):
            if l not in visti and l not in coda:
                coda.append(l)
    if not righe:
        return False, f'{tipo}: {pagine} pagine, 0 righe con data' + (f' ({"; ".join(errori[:2])})' if errori else '')
    date = [d for d, _ in righe]
    det = (f'{tipo}: {pagine} pagine' + (' (raggiunto il limite di 80)' if coda and pagine >= SOLDI_MAX_PAGINE else '')
           + f', {len(righe)} righe, piu vecchia {f(min(date))}, piu recente {f(max(date))}'
           + f'; righe per anno: {per_anno(date)}; esempi: ' + ' // '.join(campioni))
    return True, det


def prova_soldionline(rete):
    s = Sezione('1. Soldionline (pagine /raccomandazioni/<ISIN>.html)')
    for nome, isin, tipo in SOLDI_TITOLI:
        isola(s, f'{nome} {isin}', prova_soldionline_titolo, rete, nome, isin, tipo)
    return s


# ======================================================================== 2. 4trading
def _info_articolo(rete, id_):
    r = rete.get(f'https://4trading.it/articoli/{id_}')
    if r.status_code != 200:
        return {'id': id_, 'codice': r.status_code, 'url': r.url, 'titolo': '', 'data': None}
    return {'id': id_, 'codice': 200, 'url': r.url, 'titolo': titolo_articolo(r.text),
            'data': cerca_data(testo(r.text)[:6000]) or cerca_data(r.text)}


def prova_quattro_id(rete, id_):
    i = _info_articolo(rete, id_)
    ok = i['codice'] == 200 and bool(i['titolo'])
    return ok, f'HTTP {i["codice"]}, URL finale {i["url"]}, titolo "{i["titolo"][:90]}", data {f(i["data"]) if i["data"] else "non trovata"}'


def prova_quattro_scan(rete, centro):
    a = centro - QUATTRO_SCAN_N // 2
    conta = ok200 = 0
    primo = None
    date = []
    for id_ in range(a, a + QUATTRO_SCAN_N):
        try:
            i = _info_articolo(rete, id_)
        except Exception:
            continue
        if i['codice'] == 200:
            ok200 += 1
            if i['titolo'].lower().startswith('raccomandazioni analisti'):
                conta += 1
                if primo is None:
                    primo = i['id']
                if i['data']:
                    date.append(i['data'])
    det = (f'ids {a}-{a + QUATTRO_SCAN_N - 1}: {ok200} pagine raggiunte, {conta} articoli "Raccomandazioni analisti"'
           f', primo trovato id {primo}' + (f', date {f(min(date))} .. {f(max(date))}' if date else ''))
    return ok200 > 0, det


def prova_quattro(rete):
    s = Sezione('2. 4trading (articoli per numero)')
    s.riga('Apertura degli articoli per numero, senza la parte finale dell\'URL:')
    for id_ in QUATTRO_IDS:
        isola(s, f'articolo {id_}', prova_quattro_id, rete, id_)
    s.riga('')
    s.riga(f'Scansione di {QUATTRO_SCAN_N} numeri consecutivi attorno a tre id:')
    for c in QUATTRO_SCAN_CENTRI:
        isola(s, f'scansione attorno a {c}', prova_quattro_scan, rete, c)
    return s


# ======================================================================== 3. UBS
def prova_ubs_pagina(rete, nome, url):
    r = rete.get(url)
    if r.status_code != 200:
        return False, f'HTTP {r.status_code}'
    rr = righe_con_data(r.text)
    if not rr:
        return False, f'pagina scaricata ({len(r.text)} caratteri) ma 0 righe di tabella con data'
    date = [d for d, _ in rr]
    return True, (f'{len(rr)} righe, data piu vecchia {f(min(date))}, piu recente {f(max(date))}; '
                  f'per anno: {per_anno(date)}; esempio: ' + ' | '.join(rr[-1][1][:5]))


def prova_ubs(rete):
    s = Sezione('3. UBS (research disclosures)')
    for nome, url in UBS_PAGINE:
        isola(s, nome, prova_ubs_pagina, rete, nome, url)
    return s


# ======================================================================== 4. Consob
def trova_excel(html, base):
    link = [assoluto(base, h) for h in re.findall(r'href=["\']([^"\']+)["\']', html)]
    xl = [l for l in link if re.search(r'\.xlsx?(\?|#|$)', l, re.I)]
    xl.sort(key=lambda l: (0 if re.search(r'short|corte|posizion|pnc', l, re.I) else 1))
    return xl


def _intervallo_date(df):
    """(colonna, min, max, n) della colonna del DataFrame che contiene piu date valide, oppure None."""
    import pandas as pd
    migliore = None
    for col in df.columns:
        serie = df[col]
        if serie.dtype == object:
            d = pd.to_datetime(serie, errors='coerce', dayfirst=True)
        else:
            d = pd.to_datetime(serie, errors='coerce') if 'datetime' in str(serie.dtype) else None
        if d is None:
            continue
        d = d.dropna()
        d = d[(d.dt.year >= 1990) & (d.dt.year <= 2100)]
        if len(d) >= 2 and (migliore is None or len(d) > migliore[3]):
            migliore = (str(col), d.min().date(), d.max().date(), len(d))
    return migliore


def prova_consob_file(rete):
    import pandas as pd
    r = rete.get(CONSOB_PAGINA)
    if r.status_code != 200:
        return False, f'pagina HTTP {r.status_code}', []
    xl = trova_excel(r.text, r.url)
    if not xl:
        return False, f'pagina scaricata ({len(r.text)} caratteri) ma nessun link a file Excel', []
    url = xl[0]
    d = rete.get(url)
    if d.status_code != 200:
        return False, f'file {url}: HTTP {d.status_code}', []
    righe = [f'file: {url} ({len(d.content)} byte); altri link Excel: {len(xl) - 1}']
    fogli = pd.read_excel(io.BytesIO(d.content), sheet_name=None, header=0)
    for nome, df in fogli.items():
        iv = _intervallo_date(df)
        righe.append(f'foglio "{nome}": {len(df)} righe, {len(df.columns)} colonne ({", ".join(str(c) for c in list(df.columns)[:12])})'
                     + (f'; date in colonna "{iv[0]}": {f(iv[1])} .. {f(iv[2])} ({iv[3]} valori)' if iv else '; nessuna colonna data riconosciuta'))
    return True, f'{len(fogli)} fogli', righe


def prova_consob(rete):
    s = Sezione('4. Consob - posizioni corte nette')
    try:
        ok, det, righe = prova_consob_file(rete)
    except Exception as e:
        ok, det, righe = False, f'errore: {type(e).__name__}: {str(e)[:300]}', []
    s.elemento('pagina PNC e file Excel', ok, det)
    for r in righe:
        s.riga(f'  - {r}')
    return s


# ======================================================================== 5. filings.xbrl.org
FILTRI_IT = [
    json.dumps([{'name': 'entity.country', 'op': 'eq', 'val': 'IT'}]),
    json.dumps([{'name': 'country', 'op': 'eq', 'val': 'IT'}]),
]
CONCETTI = {
    'ricavi': r'^(ifrs-full:)?(Revenue|RevenueFromContractsWithCustomers|RevenueFromContractWithCustomerExcludingAssessedTax)$',
    'utile netto': r'^(ifrs-full:)?(ProfitLoss|ProfitLossAttributableToOwnersOfParent|ProfitLossFromContinuingOperations)$',
    'patrimonio netto': r'^(ifrs-full:)?(Equity|EquityAttributableToOwnersOfParent)$',
    'dividendo per azione': r'Dividend.*PerShare|PerShare.*Dividend',
}


def _nome_concetto(c):
    return c


def scarica_filings_it(rete, max_pagine=60):
    """Tutti i filings italiani via API JSON:API. Prova piu forme di filtro. -> (lista di filings, entita {id: attributi}, filtro usato)."""
    ultimo = 'nessun filtro provato'
    for filtro in FILTRI_IT:
        url = f'{XBRL_API}?filter={urllib.parse.quote(filtro)}&include=entity&page%5Bsize%5D=200&sort=-date_added'
        filings, entita, pagine = [], {}, 0
        while url and pagine < max_pagine:
            r = rete.get(url, headers={'Accept': 'application/vnd.api+json'})
            if r.status_code != 200:
                ultimo = f'filtro {filtro}: HTTP {r.status_code}'
                break
            j = r.json()
            filings += j.get('data', [])
            for inc in j.get('included', []):
                if inc.get('type') == 'entity':
                    entita[inc['id']] = inc.get('attributes', {})
            pagine += 1
            nxt = (j.get('links') or {}).get('next')
            url = assoluto(XBRL_BASE, nxt) if nxt else None
            if not j.get('data'):
                break
        if filings:
            return filings, entita, filtro, pagine
    raise RuntimeError(ultimo)


def _anno_filing(fl):
    a = fl.get('attributes', {})
    for k in ('period_end', 'date_added', 'processed'):
        d = cerca_data(str(a.get(k) or ''))
        if d:
            return d.year, k
    return None, None


def _fatti(j):
    """Fatti di un file xBRL-JSON: [(concetto, valore, dimensioni)]."""
    out = []
    fatti = j.get('facts', {}) if isinstance(j, dict) else {}
    it = fatti.values() if isinstance(fatti, dict) else fatti
    for ft in it:
        dim = ft.get('dimensions', {}) or {}
        out.append((dim.get('concept', ''), ft.get('value'), dim))
    return out


def concetti_json(j):
    """Per ciascuna voce cercata: {concetto: (n fatti, esempio valore+periodo)}."""
    fatti = _fatti(j)
    ris = {}
    for voce, rx in CONCETTI.items():
        trovati = {}
        for c, v, dim in fatti:
            if re.search(rx, c, re.I):
                n, es = trovati.get(c, (0, None))
                if es is None and not any(k not in ('concept', 'entity', 'period', 'unit', 'language') for k in dim):
                    es = f'{v} ({dim.get("period", "")})'
                trovati[c] = (n + 1, es)
        ris[voce] = trovati
    return ris, len(fatti)


def prova_xbrl_conteggio(rete):
    filings, entita, filtro, pagine = scarica_filings_it(rete)
    anni = Counter()
    for fl in filings:
        a, _ = _anno_filing(fl)
        anni[a] += 1
    paesi = Counter(e.get('country') for e in entita.values() if e.get('country'))
    det = (f'{len(filings)} filings in {pagine} pagine API (filtro {filtro}); entita distinte {len(entita)}'
           + (f'; paesi nelle entita: {dict(paesi)}' if paesi else ''))
    righe = ['per anno (di fine periodo): ' + ', '.join(f'{a}: {anni[a]}' for a in sorted(anni, key=lambda x: (x is None, x)))]
    return True, det, righe, filings, entita


def prova_xbrl_eni(rete, filings, entita):
    eni = []
    for fl in filings:
        eid = ((fl.get('relationships') or {}).get('entity') or {}).get('data', {}).get('id')
        nome = (entita.get(eid) or {}).get('name', '') or fl.get('attributes', {}).get('entity_name', '')
        if re.search(r'(^|\W)eni(\W|$)', nome, re.I):
            eni.append((fl, nome))
    if not eni:
        return False, 'nessun filing con "Eni" nel nome tra quelli italiani trovati', []
    eni.sort(key=lambda x: str(x[0].get('attributes', {}).get('period_end') or ''), reverse=True)
    righe = []
    for fl, nome in eni:
        a = fl['attributes']
        if a.get('json_url'):
            url = assoluto(XBRL_BASE, a['json_url'])
            r = rete.get(url)
            if r.status_code != 200:
                righe.append(f'{nome} {a.get("period_end")}: {url} HTTP {r.status_code}')
                continue
            ris, n = concetti_json(r.json())
            righe.append(f'{nome}, fine periodo {a.get("period_end")}: {url} ({len(r.content)} byte, {n} fatti)')
            for voce, tr in ris.items():
                if tr:
                    righe.append(f'  - {voce}: PRESENTE - ' + '; '.join(f'{c} (x{n}' + (f', es. {es}' if es else '') + ')' for c, (n, es) in sorted(tr.items())[:4]))
                else:
                    righe.append(f'  - {voce}: ASSENTE')
            return True, f'filing Eni analizzato (su {len(eni)} filings di Eni trovati)', righe
        righe.append(f'{nome} {a.get("period_end")}: nessun json_url')
    return False, f'{len(eni)} filings di Eni, ma nessuno con file xBRL JSON', righe


def prova_xbrl(rete):
    s = Sezione('5. filings.xbrl.org')
    filings = entita = None
    try:
        ok, det, righe, filings, entita = prova_xbrl_conteggio(rete)
    except Exception as e:
        ok, det, righe = False, f'errore: {type(e).__name__}: {str(e)[:300]}', []
    s.elemento('filings italiani per anno', ok, det)
    for r in righe:
        s.riga(f'  - {r}')
    if filings is not None:
        try:
            ok, det, righe = prova_xbrl_eni(rete, filings, entita)
        except Exception as e:
            ok, det, righe = False, f'errore: {type(e).__name__}: {str(e)[:300]}', []
        s.elemento('Eni, file xBRL JSON', ok, det)
        for r in righe:
            s.riga(f'  {r}')
    else:
        s.elemento('Eni, file xBRL JSON', False, 'non provato: elenco dei filings non disponibile')
    return s


# ======================================================================== 6. Yahoo
def _yf():
    import yfinance
    return yfinance


def storia_yahoo(yf, simbolo, da=None, dormi=time.sleep):
    """DataFrame (indice = date) oppure None. 3 tentativi."""
    err = None
    for t in range(3):
        try:
            kw = {'interval': '1d', 'auto_adjust': False}
            if da:
                kw['start'] = da
            else:
                kw['period'] = 'max'
            h = yf.Ticker(simbolo).history(**kw)
            if h is not None and len(h):
                return h
            return None
        except Exception as e:
            err = e
            dormi(2 * (t + 1))
    raise err


def _prova_yahoo_simbolo(yf, simbolo, da, dormi):
    h = storia_yahoo(yf, simbolo, da, dormi)
    if h is None:
        return False, 'nessun dato'
    idx = h.index
    try:
        idx = idx.tz_localize(None)
    except Exception:
        pass
    return True, f'{len(h)} righe, prima data {f(idx.min().date())}, ultima {f(idx.max().date())}'


def prova_yahoo(rete, yf=None, dormi=None):
    dormi = dormi or rete.dormi
    s = Sezione('6. Yahoo Finance (yfinance)')
    try:
        yf = yf or _yf()
    except Exception as e:
        s.elemento('import yfinance', False, f'{type(e).__name__}: {e}')
        return s

    def un(nome, simbolo, da=None):
        dormi(rete.pausa)
        isola(s, nome, _prova_yahoo_simbolo, yf, simbolo, da, dormi)

    s.riga(f'ENI.MI dal {YAHOO_ENI[1]}:')
    un(YAHOO_ENI[0], YAHOO_ENI[0], YAHOO_ENI[1])
    s.riga('')
    s.riga('Titoli usciti dalla Borsa (storia massima):')
    for t in YAHOO_DELISTED:
        un(t, t)
    s.riga('')
    s.riga('Indici e cambi (storia massima):')
    for t in YAHOO_INDICI:
        un(t, t)
    s.riga('')
    s.riga('Candidati per il FTSE Italia Mid Cap (storia massima):')
    for t in YAHOO_MIDCAP:
        un(t, t)
    try:                                           # ricerca facoltativa di altri simboli: solo informativa
        dormi(rete.pausa)
        q = yf.Search('FTSE Italia Mid Cap').quotes
        s.riga('- ricerca Yahoo "FTSE Italia Mid Cap": ' + (', '.join(f'{x.get("symbol")} ({x.get("shortname", "")})' for x in q[:6]) or 'nessun risultato'))
    except Exception as e:
        s.riga(f'- ricerca Yahoo "FTSE Italia Mid Cap": non disponibile ({type(e).__name__})')
    return s


# ======================================================================== 7. FRED
def prova_fred_serie(rete, nome, sid):
    import pandas as pd
    r = rete.get(FRED_URL + sid)
    if r.status_code != 200:
        return False, f'HTTP {r.status_code}'
    df = pd.read_csv(io.StringIO(r.text))
    colonna_data = df.columns[0]
    colonna_val = df.columns[1]
    df[colonna_data] = pd.to_datetime(df[colonna_data], errors='coerce')
    df[colonna_val] = pd.to_numeric(df[colonna_val], errors='coerce')
    v = df.dropna()
    if v.empty:
        return False, f'{len(df)} righe ma nessun valore numerico'
    return True, (f'{len(df)} righe ({len(v)} con valore), dal {f(v[colonna_data].min().date())} '
                  f'al {f(v[colonna_data].max().date())}, ultimo valore {v[colonna_val].iloc[-1]}')


def prova_fred(rete):
    s = Sezione('7. FRED (rendimenti a 10 anni, senza chiave)')
    for nome, sid in FRED:
        isola(s, f'{nome} ({sid})', prova_fred_serie, rete, nome, sid)
    return s


# ======================================================================== insieme
PROVE = {1: prova_soldionline, 2: prova_quattro, 3: prova_ubs, 4: prova_consob,
         5: prova_xbrl, 6: prova_yahoo, 7: prova_fred}


def esegui(rete, quali=None, log=print):
    sezioni = []
    for n, fn in PROVE.items():
        if quali and n not in quali:
            continue
        log(f'... prova {n}: {fn.__name__}')
        t0 = time.time()
        try:
            sez = fn(rete)
        except Exception as e:                       # rete di sicurezza: nessuna prova ferma le altre
            sez = Sezione(f'{n}. {fn.__name__}')
            sez.elemento('prova', False, f'errore imprevisto: {type(e).__name__}: {str(e)[:300]}')
            traceback.print_exc()
        sez.righe.append(f'_durata: {time.time() - t0:.0f} s_')
        sezioni.append(sez)
    return sezioni


def rapporto(sezioni, quando=None):
    quando = quando or time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())
    testa = ['# Prova delle fonti storiche', '',
             f'Eseguita il {quando}. Per ogni fonte: risponde? fin dove arriva nel passato?',
             'Una sezione e\' OK se almeno un elemento funziona; ogni elemento ha il proprio esito.', '',
             '| Prova | Esito |', '|---|---|']
    testa += [f'| {s.titolo} | {"OK" if s.ok else "NON FUNZIONA"} |' for s in sezioni]
    return '\n'.join(testa + [''] + [s.markdown() for s in sezioni])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', default='', help='numeri delle prove, es. 1,3,7 (default: tutte)')
    ap.add_argument('--out', default=str(USCITA))
    a = ap.parse_args(argv)
    quali = {int(x) for x in a.solo.split(',') if x.strip()} or None
    rete = Rete()
    md = rapporto(esegui(rete, quali))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding='utf-8')
    print(md)
    return 0


if __name__ == '__main__':
    sys.exit(main())
