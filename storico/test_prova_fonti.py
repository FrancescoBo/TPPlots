"""Test di prova_fonti.py con risposte finte (nessuna rete). Lancio:  python3 -I -m pytest storico/test_prova_fonti.py"""
import io
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prova_fonti as pf  # noqa: E402


# ------------------------------------------------------------------ finti
class Risp:
    def __init__(self, testo='', status=200, url='', contenuto=None, j=None):
        self.text, self.status_code, self.url = testo, status, url
        self.content = contenuto if contenuto is not None else testo.encode()
        self._j = j

    def json(self):
        return self._j if self._j is not None else json.loads(self.text)


class Sessione:
    """GET -> risposta da una tabella url->Risp o funzione; registra le chiamate e gli istanti."""

    def __init__(self, mappa=None, funzione=None, orologio=None):
        self.headers, self.mappa, self.funzione, self.chiamate = {}, mappa or {}, funzione, []
        self.orologio = orologio

    def get(self, url, timeout=None, **kw):
        self.chiamate.append((url, self.orologio() if self.orologio else None))
        if self.funzione:
            r = self.funzione(url)
        else:
            r = self.mappa.get(url)
        if isinstance(r, Exception):
            raise r
        if r is None:
            return Risp('', 404, url)
        if not r.url:
            r.url = url
        return r


class Tempo:
    def __init__(self):
        self.t = 0.0
        self.dormite = []

    def orologio(self):
        return self.t

    def dormi(self, s):
        self.dormite.append(s)
        self.t += s


def rete_con(sessione, tempo=None):
    tempo = tempo or Tempo()
    sessione.orologio = tempo.orologio
    return pf.Rete(sessione, dormi=tempo.dormi, orologio=tempo.orologio), tempo


def tabella(righe):
    return '<table>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in righe) + '</table>'


# ------------------------------------------------------------------ utilita' e rete
def test_cerca_data_formati():
    assert pf.cerca_data('del 05/03/2019 ok') == pf.cerca_data('2019-03-05')
    assert str(pf.cerca_data('5 marzo 2019')) == '2019-03-05'
    assert str(pf.cerca_data('Pubblicato il 31-12-2020')) == '2020-12-31'
    assert str(pf.cerca_data('12 Dec 2021')) == '2021-12-12'
    assert pf.cerca_data('31/02/2020') is None
    assert pf.cerca_data('nulla') is None


def test_pausa_per_host_e_user_agent():
    s = Sessione({'https://a.it/1': Risp('x'), 'https://a.it/2': Risp('x'), 'https://b.it/1': Risp('x')})
    rete, t = rete_con(s)
    rete.get('https://a.it/1')
    rete.get('https://b.it/1')          # altro sito: nessuna attesa
    assert t.dormite == []
    rete.get('https://a.it/2')          # stesso sito: attende 1,5 s
    assert t.dormite == [1.5]
    assert 'TPPlots' in s.headers['User-Agent'] and 'github.com/francescobo/TPPlots' in s.headers['User-Agent']
    # tra due richieste allo stesso sito passano almeno 1,5 s
    istanti = [i for u, i in s.chiamate if 'a.it' in u]
    assert istanti[1] - istanti[0] >= 1.5


def test_un_solo_nuovo_tentativo_su_errore_di_rete():
    seq = [ConnectionError('giu'), Risp('ok')]
    s = Sessione(funzione=lambda u: seq.pop(0))
    rete, t = rete_con(s)
    assert rete.get('https://a.it/x').text == 'ok'
    s2 = Sessione(funzione=lambda u: ConnectionError('sempre'))
    rete2, _ = rete_con(s2)
    try:
        rete2.get('https://a.it/x')
        assert False
    except ConnectionError:
        pass
    assert len(s2.chiamate) == 2


def test_errore_in_un_elemento_non_ferma_gli_altri():
    def fn(u):
        if 'IT0000072618' in u:
            return ConnectionError('boom')
        return Risp(tabella([['01/02/2020', 'Banca', 'Buy', '10']]))
    rete, _ = rete_con(Sessione(funzione=fn))
    s = pf.prova_soldionline(rete)
    assert s.esiti[0] is False and any(s.esiti[1:])
    assert 'NON FUNZIONA' in s.righe[0] and 'boom' in s.righe[0]


# ------------------------------------------------------------------ 1 Soldionline
def test_soldionline_paginazione_righe_anni():
    base = 'https://www.soldionline.it/raccomandazioni/IT0000072618.html'
    p1 = tabella([['10/05/2024', 'Equita', 'Buy', '5,0'], ['01/02/2024', 'Intesa', 'Hold', '4,0'], ['Data', 'x', 'y', 'z']]) \
        + '<a href="/raccomandazioni/IT0000072618.html?pagina=2">2</a>'
    p2 = tabella([['03/03/2023', 'Equita', 'Buy', '3,5']]) + '<a href="/raccomandazioni/IT0000072618.html?pagina=3">3</a>' \
        + '<a href="/raccomandazioni/IT0000072618.html?pagina=1">1</a>'
    p3 = tabella([['15/01/2019', 'Mediobanca', 'Sell', '2,0']])
    mappa = {base: Risp(p1), base + '?pagina=2': Risp(p2), base + '?pagina=3': Risp(p3)}
    rete, _ = rete_con(Sessione(mappa))
    ok, det = pf.prova_soldionline_titolo(rete, 'ISP', 'IT0000072618', 'grande')
    assert ok
    assert '3 pagine' in det and '4 righe' in det and '2019-01-15' in det
    assert '2024: 2' in det and '2023: 1' in det and '2019: 1' in det
    assert det.count(' // ') == 2        # 3 esempi


def test_soldionline_limite_80_pagine():
    def fn(u):
        n = int(u.split('=')[-1]) if '=' in u else 1
        return Risp(tabella([['01/01/2020', 'B', 'Buy', '1']]) + f'<a href="/raccomandazioni/IT0000072618.html?pagina={n + 1}">x</a>')
    rete, _ = rete_con(Sessione(funzione=fn))
    ok, det = pf.prova_soldionline_titolo(rete, 'ISP', 'IT0000072618', 'grande')
    assert ok and '80 pagine' in det and 'limite' in det


def test_soldionline_pagina_inesistente():
    rete, _ = rete_con(Sessione({}))
    ok, det = pf.prova_soldionline_titolo(rete, 'ATL', 'IT0003506190', 'non quotato')
    assert not ok and '404' in det


# ------------------------------------------------------------------ 2 4trading
def art(titolo, data):
    return f'<html><title>x</title><h1>{titolo}</h1><p>Pubblicato il {data}</p></html>'


def test_quattro_id_e_scansione():
    def fn(u):
        id_ = int(u.rsplit('/', 1)[-1])
        if id_ == 150738:
            return Risp(art('Raccomandazioni analisti - 12 novembre', '12/11/2026'), url=u + '/raccomandazioni-analisti-12-novembre')
        if id_ == 140000:
            return None
        if 109990 <= id_ <= 110010 and id_ % 2 == 0:
            return Risp(art('Raccomandazioni analisti - giorno', '03/04/2023'))
        if 110011 <= id_ <= 110020:
            return Risp(art('Altro articolo', '03/04/2023'))
        return None
    rete, _ = rete_con(Sessione(funzione=fn))
    ok, det = pf.prova_quattro_id(rete, 150738)
    assert ok and 'HTTP 200' in det and 'raccomandazioni-analisti-12-novembre' in det and '2026-11-12' in det
    ok, det = pf.prova_quattro_id(rete, 140000)
    assert not ok and 'HTTP 404' in det
    ok, det = pf.prova_quattro_scan(rete, 110000)
    # id 109925..110074: pari tra 109990 e 110010 = 11 articoli; 10 "Altro"
    assert ok and '21 pagine raggiunte' in det and '11 articoli' in det and 'primo trovato id 109990' in det


def test_quattro_sezione_completa_chiama_tutto():
    rete, _ = rete_con(Sessione(funzione=lambda u: None))
    s = pf.prova_quattro(rete)
    assert not s.ok and len(s.esiti) == 6 + 3
    # 6 aperture + 3 scansioni da 150 numeri
    assert len(rete.s.chiamate) == 6 + 3 * 150


# ------------------------------------------------------------------ 3 UBS
def test_ubs():
    html = tabella([['Date', 'Price', 'Price Target (EUR)', 'Rating'], ['15-Jan-2021', '6', '7', 'Buy'], ['10/03/2016', '5', '6', 'Neutral']])
    mappa = {pf.UBS_PAGINE[0][1]: Risp(html)}
    rete, _ = rete_con(Sessione(mappa))
    s = pf.prova_ubs(rete)
    assert s.esiti == [True, False]
    assert '2 righe' in s.righe[0] and '2016-03-10' in s.righe[0]


# ------------------------------------------------------------------ 4 Consob
def excel_finto():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        pd.DataFrame({'Emittente': ['A', 'B'], 'Posizione': [0.6, 0.7]}).to_excel(w, sheet_name='Posizioni attuali', index=False)
        pd.DataFrame({'Data': pd.to_datetime(['2012-11-01', '2020-05-04', '2026-11-10']), 'Posizione': [1, 2, 3]}).to_excel(
            w, sheet_name='Storico', index=False)
    return buf.getvalue()


def test_consob_excel():
    pagina = '<a href="/docs/altro.pdf">pdf</a><a href="/documents/pnc/posizioni_corte.xlsx">xls</a>'
    mappa = {pf.CONSOB_PAGINA: Risp(pagina, url=pf.CONSOB_PAGINA),
             'https://www.consob.it/documents/pnc/posizioni_corte.xlsx': Risp('', contenuto=excel_finto())}
    rete, _ = rete_con(Sessione(mappa))
    s = pf.prova_consob(rete)
    testo = s.markdown()
    assert s.ok and '2 fogli' in testo
    assert 'foglio "Storico": 3 righe, 2 colonne' in testo and '2012-11-01 .. 2026-11-10' in testo
    assert 'foglio "Posizioni attuali": 2 righe' in testo


def test_consob_senza_link():
    rete, _ = rete_con(Sessione({pf.CONSOB_PAGINA: Risp('<p>nulla</p>')}))
    s = pf.prova_consob(rete)
    assert not s.ok and 'nessun link' in s.markdown()


# ------------------------------------------------------------------ 5 XBRL
def pagina_api(ids_anni, nxt=None):
    data = [{'type': 'filing', 'id': str(i), 'attributes': {'period_end': f'{a}-12-31', 'json_url': f'/eni/{a}.json' if nome == 'Eni S.p.A.' else None},
             'relationships': {'entity': {'data': {'type': 'entity', 'id': e}}}} for i, a, e, nome in ids_anni]
    inc = [{'type': 'entity', 'id': e, 'attributes': {'name': nome, 'country': 'IT'}} for _, _, e, nome in ids_anni]
    return {'data': data, 'included': inc, 'links': {'next': nxt}}


def xbrl_json():
    def fatto(c, v, **extra):
        return {'value': v, 'dimensions': {'concept': c, 'period': '2023-01-01T00:00:00/2024-01-01T00:00:00', **extra}}
    return {'facts': {'f1': fatto('ifrs-full:Revenue', '93000'), 'f2': fatto('ifrs-full:ProfitLoss', '5000'),
                      'f3': fatto('ifrs-full:Equity', '50000'),
                      'f4': fatto('ifrs-full:Equity', '1', **{'ifrs-full:ComponentsOfEquityAxis': 'x'}),
                      'f5': fatto('eni:DividendsPerShare', '0.94')}}


def test_xbrl_conteggio_e_eni():
    p1 = pagina_api([(1, 2022, 'e1', 'Eni S.p.A.'), (2, 2023, 'e2', 'Altra SpA')], nxt='/api/filings?page=2')
    p2 = pagina_api([(3, 2023, 'e1', 'Eni S.p.A.'), (4, 2023, 'e3', 'Terza')])

    def fn(u):
        if u.startswith(pf.XBRL_API) and 'page=2' not in u and 'page%5Bnumber%5D' not in u:
            return Risp(json.dumps(p1))
        if 'page=2' in u:
            return Risp(json.dumps(p2))
        if u.endswith('/eni/2023.json'):
            return Risp(json.dumps(xbrl_json()))
        return None
    rete, _ = rete_con(Sessione(funzione=fn))
    s = pf.prova_xbrl(rete)
    t = s.markdown()
    assert s.esiti == [True, True]
    assert '4 filings in 2 pagine' in t and '2022: 1, 2023: 3' in t
    assert 'ricavi: PRESENTE - ifrs-full:Revenue' in t and 'es. 93000' in t
    assert 'utile netto: PRESENTE' in t and 'patrimonio netto: PRESENTE - ifrs-full:Equity (x2' in t
    assert 'dividendo per azione: PRESENTE - eni:DividendsPerShare' in t


def test_xbrl_secondo_filtro_se_il_primo_fallisce():
    j = pagina_api([(1, 2023, 'e1', 'Eni S.p.A.')])

    def fn(u):
        if 'entity.country' in urllib_unquote(u):
            return Risp('err', 400)
        return Risp(json.dumps(j)) if u.startswith(pf.XBRL_API) else None
    rete, _ = rete_con(Sessione(funzione=fn))
    s = pf.prova_xbrl(rete)
    assert s.esiti[0] is True and '"name": "country"' in s.markdown()


def urllib_unquote(u):
    import urllib.parse
    return urllib.parse.unquote(u)


def test_xbrl_api_giu():
    rete, _ = rete_con(Sessione(funzione=lambda u: Risp('x', 503)))
    s = pf.prova_xbrl(rete)
    assert s.esiti == [False, False] and not s.ok


def test_concetti_dividendo_assente():
    ris, n = pf.concetti_json({'facts': {'a': {'value': '1', 'dimensions': {'concept': 'ifrs-full:Revenue'}}}})
    assert ris['ricavi'] and not ris['dividendo per azione'] and n == 1


# ------------------------------------------------------------------ 6 Yahoo
class FinoTicker:
    def __init__(self, s, tab):
        self.s, self.tab = s, tab

    def history(self, **kw):
        v = self.tab.get(self.s)
        if isinstance(v, Exception):
            raise v
        return v


class FinoYF:
    def __init__(self, tab, cerca=None):
        self.tab, self.cerca = tab, cerca

    def Ticker(self, s):
        return FinoTicker(s, self.tab)

    def Search(self, q):
        if self.cerca is None:
            raise RuntimeError('no search')
        return type('S', (), {'quotes': self.cerca})()


def serie(prima, n):
    idx = pd.date_range(prima, periods=n, freq='B', tz='Europe/Rome')
    return pd.DataFrame({'Close': range(n)}, index=idx)


def test_yahoo():
    tab = {'ENI.MI': serie('2015-01-02', 100), 'ATL.MI': serie('2008-01-02', 50), 'MS.MI': ConnectionError('x'),
           'FTSEMIB.MI': serie('2000-01-03', 10), 'FTITLMS.MI': serie('2010-01-04', 5)}
    rete, t = rete_con(Sessione())
    s = pf.prova_yahoo(rete, yf=FinoYF(tab, [{'symbol': 'FTSEMC.MI', 'shortname': 'Mid'}]), dormi=lambda x: None)
    testo = s.markdown()
    assert '- **ENI.MI**: OK - 100 righe, prima data 2015-01-02' in testo
    assert '- **ATL.MI**: OK - 50 righe, prima data 2008-01-02' in testo
    assert '- **MS.MI**: NON FUNZIONA' in testo      # errore di rete isolato
    assert '- **CERV.MI**: NON FUNZIONA - nessun dato' in testo
    assert '- **FTITLMS.MI**: OK' in testo and 'FTSEMC.MI (Mid)' in testo
    assert len(s.esiti) == 1 + 6 + 6 + 3


def test_yahoo_senza_libreria(monkeypatch):
    monkeypatch.setattr(pf, '_yf', lambda: (_ for _ in ()).throw(ImportError('manca')))
    rete, _ = rete_con(Sessione())
    s = pf.prova_yahoo(rete)
    assert not s.ok and 'manca' in s.markdown()


# ------------------------------------------------------------------ 7 FRED
def test_fred():
    csv = 'observation_date,IRLTLT01ITM156N\n1991-01-01,13.1\n1991-02-01,.\n2026-09-01,3.6\n'
    mappa = {pf.FRED_URL + 'IRLTLT01ITM156N': Risp(csv)}
    rete, _ = rete_con(Sessione(mappa))
    s = pf.prova_fred(rete)
    assert s.esiti == [True, False]
    assert '3 righe (2 con valore), dal 1991-01-01 al 2026-09-01, ultimo valore 3.6' in s.righe[0]


# ------------------------------------------------------------------ insieme
def test_rapporto_completo_e_file(tmp_path, monkeypatch):
    # tutte le fonti irraggiungibili: il rapporto esce comunque, con 7 sezioni NON FUNZIONA
    rete, _ = rete_con(Sessione(funzione=lambda u: ConnectionError('offline')))
    monkeypatch.setattr(pf, '_yf', lambda: FinoYF({}))
    sez = pf.esegui(rete, log=lambda *a: None)
    assert len(sez) == 7 and not any(s.ok for s in sez)
    md = pf.rapporto(sez, quando='oggi')
    assert md.count('NON FUNZIONA') >= 7 and '| 7. FRED' in md


def test_esegui_isola_eccezione_di_una_prova(monkeypatch):
    def rotta(rete):
        raise ValueError('rotta')
    monkeypatch.setitem(pf.PROVE, 3, rotta)
    rete, _ = rete_con(Sessione(funzione=lambda u: Risp('', 404)))
    sez = pf.esegui(rete, quali={3, 7}, log=lambda *a: None)
    assert len(sez) == 2 and 'rotta' in sez[0].markdown() and 'FRED' in sez[1].titolo


def test_main_scrive_file(tmp_path, monkeypatch, capsys):
    finta = rete_con(Sessione(funzione=lambda u: Risp('', 404)))[0]
    monkeypatch.setattr(pf, 'Rete', lambda: finta)
    out = tmp_path / 'sub' / 'esito.md'
    assert pf.main(['--solo', '3,7', '--out', str(out)]) == 0
    assert out.exists() and '# Prova delle fonti storiche' in out.read_text(encoding='utf-8')
    assert 'Prova delle fonti storiche' in capsys.readouterr().out
