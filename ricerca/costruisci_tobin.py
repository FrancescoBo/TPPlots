"""Costruisce ricerca/tobin_esenti.csv (ticker, motivo, fonte + colonne di servizio).

Due tipi di esenzione dalla Tobin tax (imposta sulle transazioni finanziarie):
  1. societa' con sede legale all'estero (verificata sul web, vedi SEDE_ESTERA);
  2. societa' nella lista MEF delle societa' con capitalizzazione media di novembre < 500 milioni,
     una lista per anno (2025: cap. di novembre 2024; 2026: cap. di novembre 2025), che vale per l'intero anno solare.
     Il nome in lista e' abbinato al ticker con una normalizzazione dei nomi + poche correzioni manuali (ABBINAMENTI).

Colonne: ticker, nome, motivo, fonte, valido_dal, valido_al, affidabilita (alta/media/bassa).
Il motore usa valido_dal/valido_al: per il 2025 e il 2026 la lista cambia.
"""
import re
import sys
from pathlib import Path

import pandas as pd

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI))
import tobin_liste_mef as L  # noqa: E402

RADICE = QUI.parent

# Sede legale all'estero: ticker -> (paese, affidabilita, nota, fonti)
LISTE_ESTERO = ('Elenco "sede legale estera" nella lista Tobin 2025: https://www.bellelli.biz/azioni-che-non-pagano-la-tobin-tax-nel-2025/ ; '
                'nella lista 2026: https://www.orafinanza.it/it/tobin-tax-2023-le-azioni-che-non-la-pagheranno')
TELEBORSA = 'https://www.borsaitaliana.it/borsa/notizie/teleborsa/finanza/tobin-tax-nessun-crollo-dopo-il-primo-raddoppio-ma-il-secondo-e-una-scommessa-117_2026-11-02_TLB.html'
SEDE_ESTERA = {
    'RACE': ('Paesi Bassi (Ferrari N.V.)', 'alta', '', f'{LISTE_ESTERO} ; {TELEBORSA}'),
    'STLAM': ('Paesi Bassi (Stellantis N.V.)', 'alta', '', f'{LISTE_ESTERO} ; {TELEBORSA}'),
    'STMMI': ('Paesi Bassi (STMicroelectronics N.V.)', 'alta', '', f'{LISTE_ESTERO} ; {TELEBORSA}'),
    'CPR': ('Paesi Bassi (Davide Campari-Milano N.V.)', 'alta', '', f'{LISTE_ESTERO} ; {TELEBORSA}'),
    'IVG': ('Paesi Bassi (Iveco Group N.V.)', 'alta', '', f'{LISTE_ESTERO} ; {TELEBORSA}'),
    'TEN': ('Lussemburgo (Tenaris S.A.)', 'alta', '', f'{LISTE_ESTERO} ; {TELEBORSA}'),
    'CEM': ('Paesi Bassi (Cementir Holding N.V.)', 'alta', '', LISTE_ESTERO),
    'DIS': ("Lussemburgo (d'Amico International Shipping S.A.)", 'alta', '', LISTE_ESTERO),
    'MFEA': ('Paesi Bassi (MFE-MediaForEurope N.V.)', 'alta', '', LISTE_ESTERO),
    'MFEB': ('Paesi Bassi (MFE-MediaForEurope N.V.)', 'alta', '', LISTE_ESTERO),
    'EXO': ('Paesi Bassi (Exor N.V., sede legale Amsterdam)', 'alta',
            'delisted da Euronext Milan il 27/09/2022: la serie prezzi e\' quella di Amsterdam (righe in giorni di chiusura di Milano)',
            'https://exor.com/pages/frequently-asked-questions ; https://exor.com/press-releases/2022-09-27/delisting-exors-ordinary-shares-euronext-milan ; ' + LISTE_ESTERO),
    'ECMPM': ('Paesi Bassi (Eurocommercial Properties N.V.)', 'alta',
              'azione di societa\' estera in doppia quotazione a Milano dal 16/05/2023: fuori dal perimetro dell\'imposta (emittente non residente)',
              'https://www.borsaitaliana.it/borsaitaliana/ufficio-stampa/comunicati-stampa/2023/eurocommercial.en.htm'),
    'BRE': ('Paesi Bassi (Brembo N.V., sede legale Amsterdam dal 24/04/2024)', 'media',
            'residenza fiscale mantenuta in Italia; compare tra le esenti "sede estera" nelle liste 2024 e 2026 ma non in quella 2025 delle fonti usate',
            'https://www.marketscreener.com/quote/stock/BREMBO-N-V-35054164/news/Brembo-N-FIRST-QUARTER-REPORT-2024-46679104 ; '
            'https://in.marketscreener.com/quote/stock/BREMBO-N-V-35054164/news/Brembo-S-p-A-Cross-Border-Conversion-46514323/ ; '
            'https://www.orafinanza.it/it/tobin-tax-2023-le-azioni-che-non-la-pagheranno'),
    'ARIS': ('Paesi Bassi (Ariston Holding N.V., sede legale Amsterdam)', 'bassa',
             'regola del piano (sede legale estera); ma residenza fiscale in Italia e NON compare tra le esenti delle liste 2025/2026: la Tobin potrebbe essere dovuta',
             'https://financialreports.eu/filings/ariston-holding/proxy-solicitation-information-statement/2026/36128984/ ; https://fiscoinvestimenti.it/?p=16813'),
}

# Abbinamenti manuali nome-in-lista -> ticker (la normalizzazione automatica non li trova)
ABBINAMENTI = {'CVG': 'convergenze', 'RNV': 'renovalo', 'XHS': 'xenia hotellerie solution',
               'FF': 'fine foods pharmaceuticals ntm', 'PRO': 'bca profilo', 'TCG': 'tecno', 'DHH': 'dhh',
               'ICOP': 'i co p', 'IGD': 'igd', 'FILA': 'fila'}


def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[\.\-&'’`]", ' ', s)
    s = re.sub(r"\b(s p a|spa|n v|nv|sa|s a|societa|società|per azioni|group|holding|sim)\b", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def main():
    t = pd.read_csv(RADICE / 'config/titoli.csv')
    righe = []
    for tk, (paese, aff, nota, fonte) in SEDE_ESTERA.items():
        nome = t.loc[t.ticker == tk, 'nome'].iloc[0]
        motivo = f'sede legale estera: {paese}' + (f' [{nota}]' if nota else '')
        righe.append(dict(ticker=tk, nome=nome, motivo=motivo, fonte=fonte, valido_dal='2025-01-01',
                          valido_al='2026-12-31', affidabilita=aff))
    liste = {2025: {norm(x): x for x in L.lista(2025)}, 2026: {norm(x): x for x in L.lista(2026)}}
    fonti = {2025: L.FONTE_2025, 2026: L.FONTE_2026}
    for r in t.itertuples():
        if r.ticker in SEDE_ESTERA:
            continue
        cand = {norm(r.nome)}
        if r.ticker in ABBINAMENTI:
            cand.add(ABBINAMENTI[r.ticker])
        for anno in (2025, 2026):
            hit = [liste[anno][c] for c in cand if c in liste[anno]]
            if hit:
                righe.append(dict(ticker=r.ticker, nome=r.nome, valido_dal=f'{anno}-01-01', valido_al=f'{anno}-12-31',
                                  motivo=f'capitalizzazione media di novembre {anno - 1} < 500 milioni: in lista MEF {anno} come "{hit[0]}"',
                                  fonte=fonti[anno], affidabilita='media'))
    out = pd.DataFrame(righe, columns=['ticker', 'nome', 'motivo', 'fonte', 'valido_dal', 'valido_al', 'affidabilita'])
    out = out.sort_values(['ticker', 'valido_dal']).reset_index(drop=True)
    out.to_csv(QUI / 'tobin_esenti.csv', index=False)
    return out


if __name__ == '__main__':
    o = main()
    print(len(o), 'righe;', o.ticker.nunique(), 'ticker')
    print(o.groupby('valido_dal').size())
