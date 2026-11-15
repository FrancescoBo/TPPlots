"""Prova offline: simula Soldionline e UBS con HTML nel formato osservato e verifica parsing, deduplica e quarantena.
Uso: python tests/test_raccolta.py   (lavora su una copia temporanea del repository)"""
import shutil, sys, tempfile, subprocess, textwrap
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp())
shutil.copytree(SRC, tmp / 'r', ignore=shutil.ignore_patterns('.git', 'docs', '__pycache__'))
(tmp / 'r/docs').mkdir()
R = tmp / 'r'

SOLDI = """<html><body><h1>Le raccomandazioni del 13 novembre 2026</h1><p>13 Novembre 2026 alle 17:41</p><table>
<tr><th>SOCIETÀ</th><th>BANCA D'AFFARI</th><th>GIUDIZIO</th><th>TARGET PRICE</th></tr>
<tr><td><a href="/raccomandazioni/IT0003128367.html"><b>ENEL</b></a></td><td><b>Equita sim</b></td><td>Buy</td><td>▲ 7.5000</td></tr>
<tr><td><a href="/raccomandazioni/IT0003132476.html"><b>ENI</b></a></td><td><b>Banca Akros</b></td><td>▼ Hold</td><td>▼ 14.0000</td></tr>
<tr><td><b>ENI</b></td><td><b>Jefferies</b></td><td>Buy</td><td>⬤ 900.0000</td></tr>
<tr><td><b>SOCIETA INESISTENTE XYZ</b></td><td>Kepler</td><td>Buy</td><td>1.0000</td></tr>
</table></body></html>"""
UBSIDX = '<a href="226741_1_new.html">Enel SpA</a><a href="114073_1_new.html">Eni SpA</a>'
UBSPAG = """<table><tr><th>Date</th><th>Stock Price (€)</th><th>Price Target (€)</th><th>Rating</th></tr>
<tr><td>2026-11-12</td><td>6.80</td><td>7.60</td><td>Buy</td></tr></table> Price Target (€)"""

driver = textwrap.dedent(f"""
import sys
sys.path.insert(0, {str(R/'scripts')!r})
from raccolta import comune as c
def fake(url, **k):
    if 'le-raccomandazioni-del-13-novembre-2026' in url and 'azioni-italia/raccomandazioni/' not in url: return {SOLDI!r}
    if url.endswith('browseE_new.html'): return {UBSIDX!r}
    if url.endswith('226741_1_new.html') or url.endswith('114073_1_new.html'): return {UBSPAG!r}
    return None
c.scarica = fake
import aggiorna_raccomandazioni as m
sys.argv = ['x', '--oggi', '2026-11-15', '--solo', 'soldionline,ubs']
m.main()
""")
(tmp / 'drv.py').write_text(driver)
p = subprocess.run([sys.executable, str(tmp / 'drv.py')], cwd=R, capture_output=True, text=True)
print(p.stdout, p.stderr[-1500:])
import pandas as pd
d = pd.read_csv(R / 'data/raccomandazioni.csv')
for tk, em in (('ENEL', 'Equita'), ('ENI', 'Akros'), ('ENI', 'Ubs')):
    print(tk, em); print(d[(d.ticker == tk) & (d.emittente == em)].head(2).to_string())
for f in ('quarantena', 'non_riconosciuti', 'conflitti'):
    q = R / f'data/{f}.csv'; print(f, q.read_text() if q.exists() else '-')

print('--- secondo giro (devono risultare solo doppioni)')
p = subprocess.run([sys.executable, str(tmp / 'drv.py')], cwd=R, capture_output=True, text=True)
print(p.stdout, p.stderr[-800:])
p = subprocess.run([sys.executable, str(R / 'scripts/costruisci.py'), '--oggi', '2026-11-15'], cwd=R, capture_output=True, text=True)
print('--- costruisci:', p.returncode, (p.stdout + p.stderr)[-300:])
