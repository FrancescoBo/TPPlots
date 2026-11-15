"""Strumenti condivisi dai raccoglitori: HTTP, parsing HTML/numeri/date, riconoscimento di titoli ed emittenti."""
import difflib
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
UA = 'Mozilla/5.0 (compatible; TPPlots/1.0; +https://github.com/francescobo/TPPlots)'
MESI = {'gen': 1, 'gennaio': 1, 'feb': 2, 'febbraio': 2, 'mar': 3, 'marzo': 3, 'apr': 4, 'aprile': 4,
        'mag': 5, 'maggio': 5, 'giu': 6, 'giugno': 6, 'lug': 7, 'luglio': 7, 'ago': 8, 'agosto': 8,
        'set': 9, 'settembre': 9, 'ott': 10, 'ottobre': 10, 'nov': 11, 'novembre': 11, 'dic': 12, 'dicembre': 12,
        'jan': 1, 'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
        'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9, 'oct': 10,
        'october': 10, 'november': 11, 'dec': 12, 'december': 12}
COLONNE = ['ticker', 'data', 'emittente', 'raccomandazione', 'target']


# ---------------------------------------------------------------- rete
SCADENZA = [None]      # istante (time.time()) oltre il quale non si scarica più: impostato per ogni fonte
FALLIMENTI = {}        # host -> errori di rete consecutivi
MAX_FALLIMENTI = 4     # dopo tanti errori di fila l'host viene considerato irraggiungibile


def scarica(url, tentativi=2, pausa=1.0, binario=False, timeout=12):
    """Scarica un URL. Ritorna testo (o bytes) oppure None se 404/errore persistente/tempo esaurito."""
    host = urllib.parse.urlparse(url).netloc
    if FALLIMENTI.get(host, 0) >= MAX_FALLIMENTI or (SCADENZA[0] and time.time() > SCADENZA[0]):
        return None
    ultimo = None
    for i in range(tentativi):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'it,en;q=0.8'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dati = r.read()
            FALLIMENTI[host] = 0
            return dati if binario else dati.decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            ultimo = e
            if e.code in (404, 410):
                FALLIMENTI[host] = 0
                return None
        except Exception as e:  # rete, timeout, TLS
            ultimo = e
        time.sleep(pausa * (i + 1))
    FALLIMENTI[host] = FALLIMENTI.get(host, 0) + 1
    print(f'    ! {url}: {ultimo}' + (' (host sospeso)' if FALLIMENTI[host] >= MAX_FALLIMENTI else ''))
    return None


def pdf_testo(url):
    """Scarica un PDF e lo converte in testo con pdftotext (poppler)."""
    dati = scarica(url, binario=True)
    if not dati:
        return None
    tmp = ROOT / '.tmp_download.pdf'
    tmp.write_bytes(dati)
    try:
        out = subprocess.run(['pdftotext', '-layout', str(tmp), '-'], capture_output=True, text=True, timeout=120)
        return out.stdout if out.returncode == 0 else None
    finally:
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------- HTML
class _Tabelle(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tabelle, self._riga, self._cella, self._link = [], None, None, []
        self._prof = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self._prof += 1
            self.tabelle.append([])
        elif tag == 'tr' and self._prof:
            self._riga = []
        elif tag in ('td', 'th') and self._riga is not None:
            self._cella, self._link = [], []
        elif tag == 'a' and self._cella is not None:
            self._link.append(dict(attrs).get('href', ''))
        elif tag == 'br' and self._cella is not None:
            self._cella.append(' ')

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._cella is not None and self._riga is not None:
            self._riga.append((' '.join(''.join(self._cella).split()), list(self._link)))
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
    """Tutte le righe di tutte le tabelle: lista di righe, ogni riga = lista di (testo, [href])."""
    p = _Tabelle()
    p.feed(html)
    return [r for t in p.tabelle for r in t]


def link_pagina(html, contiene):
    return sorted(set(m for m in re.findall(r'href=["\']([^"\']+)["\']', html) if contiene in m))


def testo_pagina(html):
    html = re.sub(r'(?is)<(script|style).*?</\1>', ' ', html)
    html = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|li|h\d)>', '\n', html)
    html = re.sub(r'(?s)<[^>]+>', ' ', html)
    import html as h
    return h.unescape(html)


# ---------------------------------------------------------------- valori
SIMBOLI = '▲▼⬤•●◆■□▲▼⬤'


def pulisci(s):
    s = (s or '').translate({ord(c): ' ' for c in SIMBOLI})
    return ' '.join(s.split())


def numero(s):
    s = pulisci(str(s)).replace('€', '').replace('EUR', '').replace('\xa0', '')
    s = re.sub(r'[^\d,.\-]', '', s)
    if not re.search(r'\d', s):
        return None
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


def data(s, anno_default=None):
    """Interpreta date come '2026-11-13', '13/11/2026', '19 Ottobre 2026', '27 Nov 25', '2026-Nov-13'."""
    s = pulisci(str(s)).lower().replace(',', ' ')
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return pd.Timestamp(int(m[1]), int(m[2]), int(m[3]))
    m = re.search(r'(\d{4})[- ]([a-z]{3,9})[- ](\d{1,2})', s)
    if m and m[2] in MESI:
        return pd.Timestamp(int(m[1]), MESI[m[2]], int(m[3]))
    m = re.search(r'(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})', s)
    if m:
        a = int(m[3]) + (2000 if int(m[3]) < 100 else 0)
        return pd.Timestamp(a, int(m[2]), int(m[1]))
    m = re.search(r'(\d{1,2})\s+([a-zà-ù]{3,9})\.?\s+(\d{2,4})', s)
    if m and m[2] in MESI:
        a = int(m[3]) + (2000 if int(m[3]) < 100 else 0)
        return pd.Timestamp(a, MESI[m[2]], int(m[1]))
    return None


# ---------------------------------------------------------------- anagrafiche
def _norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()
    s = re.sub(r'\b(S\.?\s?P\.?\s?A\.?|N\.?\s?V\.?|S\.?\s?A\.?|S\.?\s?E\.?|A\.?\s?G\.?|PLC|SOCIETA PER AZIONI)\b', ' ', s)
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return ' '.join(s.split())


class Anagrafica:
    """Associa nomi di società ed emittenti a ticker e nomi standard del progetto."""

    def __init__(self):
        t = pd.read_csv(ROOT / 'config/titoli.csv', dtype=str).fillna('')
        self.estinti = ticker_estinti()
        self.per_nome = {}
        for tk, nome in zip(t.ticker, t.nome):
            if tk in self.estinti:
                continue
            # più titoli con lo stesso nome (es. ordinarie / risparmio): vince il primo dell'elenco (l'ordinaria)
            self.per_nome.setdefault(_norm(nome), tk)
        self.ticker_validi = set(t.ticker)
        self.per_yahoo = {s: tk for tk, s in zip(t.ticker, t.simbolo_yahoo) if s}
        self.nomi = {tk: nome for tk, nome in zip(t.ticker, t.nome)}
        p = ROOT / 'config/alias_societa.csv'
        if p.exists():
            a = pd.read_csv(p, dtype=str).fillna('')
            for nome, tk in zip(a.nome, a.ticker):
                self.per_nome[_norm(nome)] = tk
        e = pd.read_csv(ROOT / 'config/alias_emittenti.csv', dtype=str).fillna('')
        self.alias_emittenti = {k.strip().lower(): v.strip() for k, v in zip(e.nome_variante, e.nome_standard)}
        ex = pd.read_csv(ROOT / 'data/raccomandazioni.csv', dtype=str).fillna('')
        self.emittenti_noti = {}
        for x in ex.emittente.map(lambda z: self.alias_emittenti.get(z.strip().lower(), z.strip())).unique():
            self.emittenti_noti[x.lower()] = x
        c = pd.read_csv(ROOT / 'config/classi_raccomandazioni.csv', dtype=str).fillna('')
        self.classi = {k.strip().lower(): v for k, v in zip(c.raccomandazione, c.classe)}
        self.non_riconosciuti = {}

    def ticker(self, nome, fonte=''):
        n = _norm(nome)
        if not n:
            return None
        if n in self.per_nome:
            return self.per_nome[n]
        if nome.strip() in self.ticker_validi:
            return nome.strip()
        vicini = difflib.get_close_matches(n, list(self.per_nome), n=1, cutoff=0.93)
        if vicini:
            return self.per_nome[vicini[0]]
        self.non_riconosciuti[(nome.strip(), fonte)] = self.non_riconosciuti.get((nome.strip(), fonte), 0) + 1
        return None

    def emittente(self, nome):
        n = pulisci(nome)
        n = re.sub(r'(?i)\b(sim|s\.i\.m\.|securities|equity research)\b$', '', n).strip() if n.lower() not in self.emittenti_noti else n
        n = self.alias_emittenti.get(n.lower(), n)
        return self.emittenti_noti.get(n.lower(), n)

    def rating(self, testo):
        t = pulisci(testo)
        return '' if t.lower() in ('n.d.', 'nd', 'n.a.', '-', 'na') else t


def ticker_estinti():
    """{ticker: data di revoca} da config/ticker_estinti.csv: titoli non più quotati (le righe successive sono errate)."""
    p = ROOT / 'config/ticker_estinti.csv'
    if not p.exists():
        return {}
    d = pd.read_csv(p, dtype=str).fillna('')
    return {tk.strip(): pd.Timestamp(x) for tk, x in zip(d.ticker, d.data_revoca) if tk.strip()}


def frazionamenti():
    """Lista (ticker, data, fattore) da config/frazionamenti.csv."""
    p = ROOT / 'config/frazionamenti.csv'
    if not p.exists():
        return []
    d = pd.read_csv(p, dtype=str).fillna('')
    return [(t.strip(), pd.Timestamp(x), float(f)) for t, x, f in zip(d.ticker, d.data, d.fattore) if t.strip()]


def fattore_target(ticker, data):
    """Moltiplicatore da applicare a un target dato `data` per riportarlo alla scala attuale del titolo
    (raggruppamenti/frazionamenti: i target precedenti alla data dell'operazione vanno moltiplicati per il fattore)."""
    f = 1.0
    for t, d, k in frazionamenti():
        if t == ticker and data < d:
            f *= k
    return f


def record(ticker, d, emittente, rating, target, fonte):
    return dict(ticker=ticker, data=d, emittente=emittente, raccomandazione=rating, target=target, fonte=fonte)
