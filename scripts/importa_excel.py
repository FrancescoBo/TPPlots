"""
Importazione una-tantum dai file Excel storici.

  python scripts/importa_excel.py TargetPrice.xlsx TargetPrice_Plots.xlsx

- TargetPrice.xlsx, foglio "Dati": le celle "Titolo" sono tipi di dati Azioni di
  Excel; il ticker viene letto dai metadati interni del file (xl/richData).
- TargetPrice_Plots.xlsx: dai fogli per titolo prende lo storico prezzi
  (colonne A-B); dal foglio Recap nome, settore e numero di azioni
  (capitalizzazione / prezzo).
Scrive data/raccomandazioni.csv, data/prezzi/<TICKER>.csv, config/titoli.csv.
Se config/titoli.csv esiste gia', mantiene la colonna "attivo" (1 = sempre, 0 = mai, vuoto = automatico).
"""
import csv, datetime as dt, re, sys, zipfile
from pathlib import Path
from lxml import etree
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'rd': 'http://schemas.microsoft.com/office/spreadsheetml/2017/richdata',
      'xlrd': 'http://schemas.microsoft.com/office/spreadsheetml/2017/richdata'}


def leggi_dati(path):
    z = zipfile.ZipFile(path)
    md = etree.fromstring(z.read('xl/metadata.xml'))
    types = [mt.get('name') for mt in md.find('m:metadataTypes', NS)]
    fm = [f for f in md.findall('m:futureMetadata', NS) if f.get('name') == 'XLRICHVALUE'][0]
    rvb = [int(b.find('.//xlrd:rvb', NS).get('i')) for b in fm.findall('m:bk', NS)]
    vmeta = []
    for bk in md.find('m:valueMetadata', NS).findall('m:bk', NS):
        rc = bk.find('m:rc', NS)
        vmeta.append((types[int(rc.get('t')) - 1], int(rc.get('v'))))
    rv = etree.fromstring(z.read('xl/richData/rdrichvalue.xml'))
    rv_list = rv.findall('rd:rv', NS)
    rvs = [[v.text for v in r.findall('rd:v', NS)] for r in rv_list]
    rv_s = [int(r.get('s')) for r in rv_list]
    st = etree.fromstring(z.read('xl/richData/rdrichvaluestructure.xml'))
    structs = [[k.get('n') for k in s.findall('rd:k', NS)] for s in st.findall('rd:s', NS)]

    def nome(i, depth=0):
        d = dict(zip(structs[rv_s[i]], rvs[i]))
        if '_DisplayString' in d:
            return d['_DisplayString']
        if '%cvi' in d and depth < 3:
            return nome(int(d['%cvi']), depth + 1)
        return None

    # primo foglio del workbook
    wbx = etree.fromstring(z.read('xl/workbook.xml'))
    rels = etree.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rid = wbx.find('m:sheets', NS)[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
    target = [r.get('Target') for r in rels if r.get('Id') == rid][0].lstrip('/')
    sheet_path = target if target.startswith('xl/') else 'xl/' + target
    sh = etree.fromstring(z.read(sheet_path))
    sst = [''.join(si.itertext()) for si in etree.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS)]
    rows = {}
    for c in sh.iter('{%s}c' % NS['m']):
        ref = c.get('r'); col = re.match(r'[A-Z]+', ref).group(); r = int(ref[len(col):])
        if col not in 'AEFGH':
            continue
        v = c.find('m:v', NS); val = v.text if v is not None else None
        if c.get('t') == 's' and val is not None:
            val = sst[int(val)]
        if col == 'A' and c.get('vm'):
            t, idx = vmeta[int(c.get('vm')) - 1]
            if t == 'XLRICHVALUE':
                val = nome(rvb[idx])
        rows.setdefault(r, {})[col] = val
    out = []
    for r in sorted(rows):
        d = rows[r]
        if r == 1 or not d.get('A') or not d.get('G'):
            continue
        try:
            data = (dt.date(1899, 12, 30) + dt.timedelta(days=float(d['G']))).isoformat()
        except ValueError:
            continue
        out.append({'titolo_excel': d['A'], 'emittente': (d.get('E') or '').strip(),
                    'raccomandazione': (d.get('F') or '').replace('\xa0', ' ').strip(),
                    'data': data, 'target': d.get('H')})
    return pd.DataFrame(out)


def main(f_tp, f_plots):
    alias = pd.read_csv(ROOT / 'config/alias_ticker.csv', dtype=str)
    alias = dict(zip(alias.codice_excel, alias.ticker))
    df = leggi_dati(f_tp)
    codice = df.titolo_excel.str.extract(r'\((\w+:[^)]+)\)$')[0]
    df['ticker'] = [alias.get(c, c.split(':')[1] if isinstance(c, str) else None) for c in codice]
    df['borsa'] = [c.split(':')[0] if isinstance(c, str) and c not in alias else 'XMIL' for c in codice]
    df['nome_excel'] = df.titolo_excel.str.replace(r'\s*\([^()]*\)$', '', regex=True).str.strip()
    df['target'] = pd.to_numeric(df.target, errors='coerce')
    df['emittente'] = df.emittente.str.replace(r'\s+', ' ', regex=True)
    df = df.dropna(subset=['ticker'])
    df = df.sort_values(['ticker', 'data', 'emittente'], ascending=[True, False, True])
    df[['ticker', 'data', 'emittente', 'raccomandazione', 'target']].to_csv(
        ROOT / 'data/raccomandazioni.csv', index=False)
    print(f'raccomandazioni: {len(df)} righe, {df.ticker.nunique()} titoli')

    wb = openpyxl.load_workbook(f_plots, data_only=True)
    recap = {}
    for r in wb['Recap'].iter_rows(min_row=2, values_only=True):
        if r[2] and isinstance(r[2], str):
            f, j = r[5], r[9]
            azioni = round(f / j) if isinstance(f, (int, float)) and isinstance(j, (int, float)) and j else ''
            recap[r[2]] = {'nome': r[1], 'settore': r[3], 'azioni': azioni}
    (ROOT / 'data/prezzi').mkdir(parents=True, exist_ok=True)
    for tk in recap:
        if tk not in wb.sheetnames:
            continue
        p = [(r[0].date().isoformat(), r[1]) for r in wb[tk].iter_rows(min_row=2, max_col=2, values_only=True)
             if isinstance(r[0], dt.datetime) and isinstance(r[1], (int, float))]
        pd.DataFrame(p, columns=['data', 'chiusura']).drop_duplicates('data').sort_values('data').to_csv(
            ROOT / f'data/prezzi/{tk}.csv', index=False)

    # elenco titoli: tutti quelli presenti nelle raccomandazioni
    cfg_path = ROOT / 'config/titoli.csv'
    attivi = {}
    if cfg_path.exists():
        old = pd.read_csv(cfg_path, dtype=str).fillna('')
        attivi = dict(zip(old.ticker, old.attivo))
    suffisso = {'XMIL': '.MI', 'XAMS': '.AS', 'XPAR': '.PA', 'XETR': '.DE', 'XNYS': ''}
    info = df.drop_duplicates('ticker').set_index('ticker')
    rows = []
    for tk in sorted(df.ticker.unique()):
        v = recap.get(tk, {})
        rows.append({'ticker': tk, 'nome': v.get('nome') or info.nome_excel[tk], 'settore': v.get('settore') or '',
                     'simbolo_yahoo': tk + suffisso.get(info.borsa[tk], '.MI'),
                     'azioni_circolazione': v.get('azioni', ''), 'attivo': attivi.get(tk, '')})
    pd.DataFrame(rows).to_csv(cfg_path, index=False)
    print(f'titoli: {len(rows)} (prezzi per {len(recap)} in data/prezzi/)')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
