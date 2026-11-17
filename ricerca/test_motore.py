"""Test automatici della fase 1: costi, Tobin, tasse, esecuzione degli ordini, dividendi, assenza di look-ahead.

Eseguire:  python -m pytest ricerca/test_motore.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

QUI = Path(__file__).resolve().parent
if str(QUI) not in sys.path:
    sys.path.insert(0, str(QUI))

import dati as D          # noqa: E402
import motore as M        # noqa: E402
import segnali as S       # noqa: E402


# ============================================================ commissioni
@pytest.mark.parametrize('valore, atteso', [(1460, 6.40), (1460.0, 6.40), (2500, 8.90), (3300, 10.82),
                                           (4000, 12.50), (5000, 14.90), (6700, 18.98), (10000, 26.90)])
def test_commissione_tabella_del_piano(valore, atteso):
    assert M.commissione(valore) == pytest.approx(atteso, abs=1e-9)


def test_commissione_sotto_soglia_e_zero():
    assert M.commissione(500) == 6.40          # fisso anche sotto 1.460
    assert M.commissione(0) == 0.0


def test_costo_andata_ritorno_con_tobin_come_nel_piano():
    # tabella del piano: 4.000 EUR -> 0,72%; 10.000 EUR -> 0,64%; 1.460 -> 0,98%
    for v, pct in ((4000, 0.72), (10000, 0.64), (1460, 0.98)):
        tot = 2 * M.commissione(v) + M.tobin(v, 'A2A')
        assert 100 * tot / v == pytest.approx(pct, abs=0.006)


# ============================================================ Tobin
def test_tobin_titolo_italiano_e_ferrari():
    esenti = {'RACE'}
    assert M.tobin(4000, 'A2A', esenti=esenti) == pytest.approx(4.00)
    assert M.tobin(10000, 'ENI', esenti=esenti) == pytest.approx(10.00)
    assert M.tobin(4000, 'RACE', esenti=esenti) == 0.0       # Ferrari: sede legale nei Paesi Bassi


def test_tobin_esenzione_a_date():
    esenti = {'XYZ': [(pd.Timestamp('2025-01-01'), pd.Timestamp('2025-12-31'))]}
    assert M.tobin(5000, 'XYZ', '2025-06-01', esenti) == 0.0
    assert M.tobin(5000, 'XYZ', '2026-02-01', esenti) == pytest.approx(10.00)   # fuori dalla lista del 2025; dal 2026 aliquota 0,2%


def test_slittamento_per_capitalizzazione():
    assert M.slittamento(5.0) == 0.0005
    assert M.slittamento(0.4) == 0.0020
    assert M.slittamento(float('nan')) == 0.0020
    assert M.slittamento(None) == 0.0020


# ============================================================ tasse
def test_tassa_26_per_cento_semplice():
    f = M.RegistroFiscale()
    assert f.realizza(1000.0, 2026) == pytest.approx(260.0)


def test_tassa_con_credito_da_minusvalenze_riportato():
    f = M.RegistroFiscale()
    assert f.realizza(-1000.0, 2025) == 0.0                 # perdita: credito di 1.000
    assert f.credito_disponibile(2026) == pytest.approx(1000.0)
    assert f.realizza(1500.0, 2026) == pytest.approx(0.26 * 500)   # imponibile 500
    assert f.credito_disponibile(2026) == pytest.approx(0.0)
    assert f.realizza(200.0, 2026) == pytest.approx(52.0)   # credito esaurito


def test_credito_parziale_e_scadenza_quattro_anni():
    f = M.RegistroFiscale()
    f.realizza(-1000.0, 2021)
    assert f.credito_disponibile(2025) == pytest.approx(1000.0)   # 2021 + 4 = 2025: ancora valido
    assert f.credito_disponibile(2026) == 0.0                     # scaduto
    assert f.realizza(1000.0, 2026) == pytest.approx(260.0)       # tassa piena
    g = M.RegistroFiscale()
    g.realizza(-300.0, 2024)
    assert g.realizza(1000.0, 2025) == pytest.approx(0.26 * 700)
    assert g.credito_disponibile(2025) == 0.0


def test_crediti_usati_dal_piu_vecchio():
    f = M.RegistroFiscale()
    f.realizza(-100.0, 2022)
    f.realizza(-100.0, 2025)
    assert f.realizza(150.0, 2026) == pytest.approx(0.0)    # usa 100 (2022, scade fine 2026? 2022+4=2026) + 50 del 2025
    assert f.credito_disponibile(2026) == pytest.approx(50.0)


def test_pareggio_non_genera_credito_ne_tassa():
    f = M.RegistroFiscale()
    assert f.realizza(0.0, 2026) == 0.0 and f.crediti == []


# ============================================================ regole di esecuzione
def test_limite_acquisto():
    assert M.prezzo_limite_acquisto(10.0, apertura=10.5, minimo=9.8) == 10.0     # toccato: prezzo L
    assert M.prezzo_limite_acquisto(10.0, apertura=9.7, minimo=9.5) == 9.7       # apertura in gap sotto L: apertura
    assert M.prezzo_limite_acquisto(10.0, apertura=10.5, minimo=10.1) is None    # mai toccato
    assert M.prezzo_limite_acquisto(10.0, apertura=10.5, minimo=10.0) == 10.0    # tocco esatto


def test_take_profit():
    assert M.prezzo_take_profit(11.0, apertura=10.0, massimo=11.2) == 11.0
    assert M.prezzo_take_profit(11.0, apertura=11.4, massimo=11.6) == 11.4       # gap sopra P: apertura
    assert M.prezzo_take_profit(11.0, apertura=10.0, massimo=10.9) is None


def test_stop_con_gap_in_apertura():
    assert M.prezzo_stop(9.0, apertura=9.5, minimo=8.9) == 9.0
    assert M.prezzo_stop(9.0, apertura=8.5, minimo=8.2) == 8.5                   # gap sotto S: apertura
    assert M.prezzo_stop(9.0, apertura=9.5, minimo=9.1) is None


def test_stop_e_take_profit_nella_stessa_seduta_vale_lo_stop():
    es = M.esito_uscita(take_profit=11.0, stop=9.0, apertura=10.0, massimo=11.5, minimo=8.8)
    assert es == ('stop', 9.0)
    es = M.esito_uscita(take_profit=11.0, stop=9.0, apertura=10.0, massimo=11.5, minimo=9.5)
    assert es == ('take_profit', 11.0)
    es = M.esito_uscita(take_profit=11.0, stop=9.0, apertura=10.0, massimo=10.5, minimo=9.5)
    assert es is None
    # gap sopra il take profit E minimo sotto lo stop: vale lo stop
    es = M.esito_uscita(take_profit=11.0, stop=9.0, apertura=11.5, massimo=12.0, minimo=8.0)
    assert es[0] == 'stop'


# ============================================================ simulatore su dati sintetici
def sintetico(aperture, massimi, minimi, chiusure, volumi=None, ticker='AAA', inizio='2026-01-05'):
    n = len(aperture)
    cal = pd.bdate_range(inizio, periods=n)
    mk = lambda v: pd.DataFrame({ticker: np.array(v, dtype=float)}, index=cal)
    vol = mk(volumi if volumi is not None else [1000] * n)
    return D.Prezzi(cal, mk(aperture), mk(massimi), mk(minimi), mk(chiusure), vol, {}, [])


def pan_div(prezzi, dividendi):
    p = pd.DataFrame(0.0, index=prezzi.calendario, columns=prezzi.tickers)
    for i, v in dividendi.items():
        p.iloc[i, 0] = v
    return p


class CompraAlGiorno(M.Strategia):
    """Decide alla chiusura del giorno i0 di comprare (esecuzione i0+1) e alla chiusura di i1 di vendere."""

    def __init__(self, i0, importo, i1=None, ticker='AAA', uscite=None, limite=None):
        self.i0, self.i1, self.importo, self.tk, self.uscite, self.limite = i0, i1, importo, ticker, uscite, limite

    def decidi(self, i, sim):
        if i == self.i0:
            return [M.Acquisto(self.tk, self.importo, limite=self.limite, uscite=self.uscite or M.Uscite())]
        if self.i1 is not None and i == self.i1:
            return [M.Vendita(self.tk)]
        return []


def test_ordine_eseguito_il_giorno_dopo_il_segnale_non_lo_stesso():
    # apertura 10 in tutti i giorni tranne il giorno 2 (apertura 12): decisione alla chiusura del giorno 1 -> acquisto all'apertura del giorno 2
    p = sintetico([10, 10, 12, 12, 12], [10.5] * 2 + [12.5] * 3, [9.5] * 2 + [11.5] * 3, [10, 10, 12, 12, 12])
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(lordo=True, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(1, 4000))
    pz = sim.pos['AAA']
    assert pz.i_ingresso == 2 and pz.prezzo_base == 12.0          # non 10 (chiusura/apertura del giorno del segnale)


def test_dividendo_netto_74_per_cento_solo_se_in_portafoglio_il_giorno_prima():
    n = 8
    p = sintetico([10] * n, [10.2] * n, [9.8] * n, [10] * n)
    div = pan_div(p, {4: 0.50})                                   # stacco alla seduta 4
    # (a) acquisto eseguito alla seduta 1 -> in portafoglio il giorno prima dello stacco: incassa 74%
    sim = M.Simulatore(p, div, config=M.Config(lordo=False, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000))
    az = sim.pos['AAA'].azioni
    assert sim.pos['AAA'].dividendi_netti == pytest.approx(az * 0.50 * 0.74)
    assert sim.pos['AAA'].dividendi_lordi == pytest.approx(az * 0.50)
    # (b) acquisto eseguito proprio alla seduta dello stacco -> niente dividendo
    sim = M.Simulatore(p, div, config=M.Config(lordo=False, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(3, 4000))
    assert sim.pos['AAA'].i_ingresso == 4 and sim.pos['AAA'].dividendi_netti == 0.0
    # (c) vendita eseguita alla seduta dello stacco: il titolo era in portafoglio il giorno prima -> incassa
    sim = M.Simulatore(p, div, config=M.Config(lordo=False, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000, i1=3))
    tr = sim.trades[0]
    assert tr['data_uscita'] == p.calendario[4]
    assert tr['dividendi_netti'] == pytest.approx(tr['azioni'] * 0.50 * 0.74)


def test_dividendo_lordo_al_100_per_cento_in_modalita_lorda():
    n = 6
    p = sintetico([10] * n, [10.2] * n, [9.8] * n, [10] * n)
    sim = M.Simulatore(p, pan_div(p, {4: 0.50}), config=M.Config(lordo=True, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000))
    az = sim.pos['AAA'].azioni
    assert sim.pos['AAA'].dividendi_netti == pytest.approx(az * 0.50)


def test_acquisto_costi_tobin_e_vendita_con_tassa_tornano_al_centesimo():
    p = sintetico([10, 10, 10, 10, 12, 12], [10.1, 10.1, 10.1, 10.1, 12.1, 12.1], [9.9, 9.9, 9.9, 9.9, 11.9, 11.9],
                  [10, 10, 10, 10, 12, 12])
    sim = M.Simulatore(p, pan_div(p, {}), tobin_esenti=None, config=M.Config(liquida_a_fine=True))
    res = sim.esegui(CompraAlGiorno(0, 4000))
    # atteso: slittamento 0,20% (cap ignota), commissione e Tobin sul valore effettivo
    pe = 10 * 1.002
    n = int(4000 // pe)
    while n * pe + M.commissione(n * pe) + M.tobin(n * pe, 'AAA', p.calendario[1]) > 4000:
        n -= 1
    costo = n * pe + M.commissione(n * pe) + M.tobin(n * pe, 'AAA', p.calendario[1])
    pv = 12 * 0.998
    incasso = n * pv - M.commissione(n * pv)
    tassa = round(0.26 * (incasso - costo), 2)
    atteso = 20000 - costo + incasso - tassa
    t = res.trades.iloc[0]
    assert t.azioni == n
    assert t.tassa == pytest.approx(tassa, abs=0.011)
    assert sim.cash == pytest.approx(atteso, abs=0.011)
    assert res.equity.iloc[-1] == pytest.approx(atteso, abs=0.011)
    assert t.tobin == pytest.approx(M.tobin(n * pe, 'AAA', p.calendario[1]))
    # identita': patrimonio finale = capitale + somma dei risultati netti dei trade
    assert sim.cash == pytest.approx(20000 + res.trades.risultato_netto.sum(), abs=0.011)


def test_ferrari_esente_dal_tobin_nel_simulatore():
    p = sintetico([10] * 5, [10.1] * 5, [9.9] * 5, [10] * 5, ticker='RACE')
    sim = M.Simulatore(p, pan_div(p, {}), tobin_esenti={'RACE'}, config=M.Config(liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000, ticker='RACE'))
    assert sim.costi['tobin'] == 0.0
    sim2 = M.Simulatore(p, pan_div(p, {}), tobin_esenti=None, config=M.Config(liquida_a_fine=False))
    sim2.esegui(CompraAlGiorno(0, 4000, ticker='RACE'))
    assert sim2.costi['tobin'] > 3.9


def test_perdita_poi_guadagno_usa_il_credito_nel_simulatore():
    # due titoli in sequenza non servono: stesso titolo, due round-trip: -  poi +
    n = 14
    ap = [10] * 4 + [8] * 4 + [8] * 2 + [12] * 4
    p = sintetico(ap, [x + .1 for x in ap], [x - .1 for x in ap], ap)

    class Doppio(M.Strategia):
        def decidi(self, i, sim):
            return {0: [M.Acquisto('AAA', 4000)], 3: [M.Vendita('AAA')], 7: [M.Acquisto('AAA', 4000)],
                    9: [M.Vendita('AAA')]}.get(i, [])

    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(liquida_a_fine=False))
    res = sim.esegui(Doppio())
    t = res.trades
    assert len(t) == 2 and t.risultato_fiscale.iloc[0] < 0
    # il secondo trade e' in positivo ma stesso anno: l'imponibile e' ridotto dalla perdita precedente
    perdita, guad = t.risultato_fiscale.iloc[0], t.risultato_fiscale.iloc[1]
    assert guad > -perdita > 0                                   # il guadagno supera la perdita: credito usato per intero
    assert t.tassa.iloc[0] == 0.0
    assert t.tassa.iloc[1] == pytest.approx(0.26 * (guad + perdita), abs=0.011)
    assert t.tassa.iloc[1] < 0.26 * guad - 1                      # la tassa e' davvero inferiore a quella senza credito


def test_take_profit_stop_e_stop_con_gap_nel_simulatore():
    # entrata a 10 alla seduta 1; stop 5% = 9,5; take profit 10% = 11
    base = dict(ticker='AAA')
    # a) toccato il TP alla seduta 2
    p = sintetico([10, 10, 10.5, 10.5], [10.1, 10.1, 11.3, 10.6], [9.9, 9.9, 10.2, 10.4], [10, 10, 11, 10.5])
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(lordo=True, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000, uscite=M.Uscite(take_profit_pct=0.10, stop_pct=0.05)))
    assert sim.trades[0]['motivo'] == 'take_profit' and sim.trades[0]['prezzo_uscita'] == pytest.approx(11.0)
    # b) apertura in gap sotto lo stop: eseguito all'apertura, non a 9,5
    p = sintetico([10, 10, 9.0, 9.0], [10.1, 10.1, 9.2, 9.1], [9.9, 9.9, 8.8, 8.9], [10, 10, 9, 9])
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(lordo=True, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000, uscite=M.Uscite(take_profit_pct=0.10, stop_pct=0.05)))
    assert sim.trades[0]['motivo'] == 'stop' and sim.trades[0]['prezzo_uscita'] == pytest.approx(9.0)
    # c) TP e stop toccati nella stessa seduta: vale lo stop
    p = sintetico([10, 10, 10, 10], [10.1, 10.1, 11.5, 10.1], [9.9, 9.9, 9.4, 9.9], [10, 10, 10, 10])
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(lordo=True, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000, uscite=M.Uscite(take_profit_pct=0.10, stop_pct=0.05)))
    assert sim.trades[0]['motivo'] == 'stop' and sim.trades[0]['prezzo_uscita'] == pytest.approx(9.5)


def test_ordine_limite_nel_simulatore():
    # limite 9,5; la seduta 1 non lo tocca (minimo 9,8), la seduta 2 si' (minimo 9,4) -> prezzo 9,5; validita' 2 sedute
    p = sintetico([10, 10, 10, 10], [10.2] * 4, [9.9, 9.8, 9.4, 9.9], [10, 10, 10, 10])
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(lordo=True, liquida_a_fine=False))

    class Lim(M.Strategia):
        def __init__(self, val):
            self.val = val

        def decidi(self, i, sim):
            return [M.Acquisto('AAA', 4000, limite=9.5, validita=self.val)] if i == 0 else []

    sim.esegui(Lim(2))
    assert sim.pos['AAA'].prezzo_base == 9.5 and sim.pos['AAA'].i_ingresso == 2
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(lordo=True, liquida_a_fine=False))
    sim.esegui(Lim(1))                                           # valido solo la seduta 1: non eseguito
    assert 'AAA' not in sim.pos


def test_nessun_ordine_con_volume_zero():
    p = sintetico([10, 10, 10, 10], [10.2] * 4, [9.8] * 4, [10] * 4, volumi=[1000, 0, 1000, 1000])
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(lordo=True, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000))                          # eseguirebbe alla seduta 1, ma il volume e' zero: salta
    assert 'AAA' not in sim.pos


def test_titolo_uscito_dalla_borsa_chiuso_all_ultimo_prezzo():
    cal = pd.bdate_range('2026-01-05', periods=8)
    nan = np.nan
    mk = lambda v: pd.DataFrame({'AAA': v, 'BBB': [10.0] * 8}, index=cal)
    aa = [10, 10, 10, 10, nan, nan, nan, nan]
    p = D.Prezzi(cal, mk(aa), mk([x + .1 for x in aa]), mk([x - .1 for x in aa]), mk(aa), mk([1000] * 8), {}, [])
    sim = M.Simulatore(p, pd.DataFrame(0.0, index=cal, columns=['AAA', 'BBB']), config=M.Config(lordo=True, liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000))
    assert 'AAA' not in sim.pos and sim.trades[0]['motivo'] == 'fine_quotazione' and sim.trades[0]['prezzo_uscita'] == 10


def test_il_patrimonio_non_cambia_con_costi_zero_in_modalita_lorda():
    p = sintetico([10] * 5, [10.2] * 5, [9.8] * 5, [10] * 5)
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(lordo=True))
    res = sim.esegui(CompraAlGiorno(0, 4000))
    assert res.equity.iloc[-1] == pytest.approx(20000.0, abs=1e-6)
    assert sim.costi == {'commissioni': 0.0, 'tobin': 0.0, 'slittamento': 0.0}


def test_cassa_mai_negativa_e_numero_intero_di_azioni():
    p = sintetico([37.3] * 5, [38] * 5, [37] * 5, [37.3] * 5)
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 3300))
    pz = sim.pos['AAA']
    assert isinstance(pz.azioni, int) and sim.cash >= 20000 - 3300 - 1e-9
    assert pz.costo_base <= 3300 + 1e-9


# ============================================================ look-ahead nei segnali (dati reali)
@pytest.fixture(scope='module')
def dati_reali():
    pr = D.carica_prezzi()
    rac, esclusi = D.carica_raccomandazioni(pr)
    return pr, rac, esclusi


def test_nessun_dato_oltre_la_data_di_fine(dati_reali):
    pr, rac, esclusi = dati_reali
    assert pr.calendario.max() <= D.DATA_FINE
    assert rac.data.max() <= D.DATA_FINE and esclusi.data.max() <= D.DATA_FINE
    assert D.carica_dividendi().data.max() <= D.DATA_FINE
    assert D.carica_indice().index.max() <= D.DATA_FINE


def _tronca(pr, taglio):
    cal = pr.calendario[pr.calendario <= taglio]
    f = lambda df: df.loc[cal]
    return D.Prezzi(cal, f(pr.apertura), f(pr.massimo), f(pr.minimo), f(pr.chiusura), f(pr.volume), {}, [])


def test_i_segnali_di_t_non_cambiano_togliendo_i_dati_successivi(dati_reali):
    pr, rac, _ = dati_reali
    an, ix = D.carica_anagrafica(), D.carica_indice()
    taglio = pd.Timestamp('2025-12-15')
    completo = S.calcola_segnali(pr, rac, an, ix)
    pr_t = _tronca(pr, taglio)
    # i dati di raccomandazioni dopo il taglio vengono tolti (data > taglio)
    parziale = S.calcola_segnali(pr_t, rac[rac.data <= taglio], an, ix[ix.index <= taglio])
    giorni = pr_t.calendario[pr_t.calendario >= '2025-09-01']
    for nome, df in parziale.variabili.items():
        a = df.loc[giorni]
        b = completo.variabili[nome].loc[giorni, a.columns]
        pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-9, atol=1e-12, obj=nome)
    for nome, df in parziale.eventi.items():
        pd.testing.assert_frame_equal(df.loc[giorni], completo.eventi[nome].loc[giorni, df.columns], obj=nome)
    pd.testing.assert_frame_equal(parziale.universo.loc[giorni], completo.universo.loc[giorni, parziale.universo.columns])


def test_raccomandazione_datata_t_non_e_usabile_prima_di_t_piu_1(dati_reali):
    pr, rac, _ = dati_reali
    cal = pr.calendario
    # con ritardo 1 una raccomandazione datata in una seduta t diventa visibile solo dalla seduta successiva
    t = pd.Timestamp('2025-10-14')
    i = int(np.flatnonzero(cal == t)[0])
    pos1 = S.indice_disponibilita(cal, pd.Series([t]), 1)[0]
    pos0 = S.indice_disponibilita(cal, pd.Series([t]), 0)[0]
    assert pos1 == i + 1 and pos0 == i
    # una datata di sabato e' usabile dal lunedi' in entrambi i casi
    sab = pd.Timestamp('2025-10-11')
    assert cal[S.indice_disponibilita(cal, pd.Series([sab]), 1)[0]] == pd.Timestamp('2025-10-13')


def test_rendimenti_futuri_non_superano_la_data_di_fine(dati_reali):
    pr, _, _ = dati_reali
    div = S.dividendi_pannello(pr, D.carica_dividendi())
    rf = S.rendimenti_futuri(pr, div)
    n = len(pr.calendario)
    for h, df in rf.items():
        assert df.iloc[n - h:].isna().all().all()          # l'ultima finestra utile finisce alla chiusura dell'ultima seduta
        assert df.iloc[:n - h].notna().any().any()
    # controllo manuale su un titolo: acquisto all'apertura di t+1, vendita alla chiusura di t+5
    tk, t = 'A2A', pr.calendario[100]
    i = 100
    manuale = (pr.chiusura[tk].iat[i + 5] + div[tk].iloc[i + 2:i + 6].sum()) / pr.apertura[tk].iat[i + 1] - 1
    assert rf[5][tk].iat[i] == pytest.approx(manuale)


def test_tobin_esenti_csv_ferrari_si_a2a_no():
    import dati as D
    e = D.carica_tobin_esenti()
    assert 'RACE' in e and 'A2A' not in e


# ============================================================ regole di DECISIONI_FASE3
def test_tobin_01_fino_al_2025_e_02_dal_2026():
    assert M.aliquota_tobin('2025-12-31') == 0.001
    assert M.aliquota_tobin('2026-01-01') == 0.002
    assert M.tobin(10000, 'A2A', '2025-12-31') == pytest.approx(10.0)
    assert M.tobin(10000, 'A2A', '2026-01-02') == pytest.approx(20.0)
    assert M.tobin(10000, 'RACE', '2026-01-02', esenti={'RACE'}) == 0.0
    # sensibilita' 0,4% dal 2026: non tocca il 2025
    assert M.tobin(10000, 'A2A', '2026-01-02', aliquota=0.004) == pytest.approx(40.0)
    assert M.aliquota_tobin('2025-06-01', dal_2026=0.004) == 0.001


def test_tobin_nel_simulatore_a_cavallo_del_capodanno():
    # sedute: 29,30,31 dic 2025 e 1(festa),2,5 gen: il 31/12 e' in 2025 (0,1%), il 2/1 in 2026 (0,2%)
    cal = pd.DatetimeIndex(['2025-12-29', '2025-12-30', '2025-12-31', '2026-01-02', '2026-01-05', '2026-01-06'])
    mk = lambda v: pd.DataFrame({'AAA': np.array(v, dtype=float)}, index=cal)
    p = D.Prezzi(cal, mk([10] * 6), mk([10.1] * 6), mk([9.9] * 6), mk([10] * 6), mk([1000] * 6), {}, [])
    for dec, aliq in ((1, 0.001), (3, 0.002)):          # decisione il 30/12 -> acquisto il 31/12; il 2/1 -> il 5/1
        sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(liquida_a_fine=False))
        sim.esegui(CompraAlGiorno(dec, 4000))
        pz = sim.pos['AAA']
        assert pz.tobin_in == pytest.approx(M.arrotonda(aliq * pz.azioni * pz.prezzo_eff))
    sim = M.Simulatore(p, pan_div(p, {}), config=M.Config(liquida_a_fine=False, tobin_dal_2026=0.004))
    sim.esegui(CompraAlGiorno(3, 4000))
    assert sim.pos['AAA'].tobin_in == pytest.approx(M.arrotonda(0.004 * sim.pos['AAA'].azioni * sim.pos['AAA'].prezzo_eff))


@pytest.mark.parametrize('cv, atteso', [(5e6, 0.0005), (2e7, 0.0005), (4.99e6, 0.0010), (1e6, 0.0010), (9.9e5, 0.0020),
                                        (0.0, 0.0020), (float('nan'), 0.0020), (None, 0.0020)])
def test_slittamento_per_liquidita(cv, atteso):
    assert M.slittamento_liquidita(cv) == atteso


def test_pannello_liquidita_mediana_60_sedute_solo_dati_passati():
    n = 100
    cal = pd.bdate_range('2025-01-02', periods=n)
    ch = pd.DataFrame({'AAA': np.full(n, 10.0)}, index=cal)
    vol = pd.DataFrame({'AAA': np.arange(1, n + 1) * 1000.0}, index=cal)
    p = D.Prezzi(cal, ch, ch, ch, ch, vol, {}, [])
    L = M.pannello_liquidita(p)
    t = 80
    atteso = np.median(10.0 * vol['AAA'].iloc[t - 59:t + 1])
    assert L['AAA'].iloc[t] == pytest.approx(atteso)
    assert np.isnan(L['AAA'].iloc[28])                    # meno di 30 sedute di storia
    # cambiare i volumi futuri non cambia la mediana di oggi
    vol2 = vol.copy(); vol2.iloc[t + 1:] = 1e12
    L2 = M.pannello_liquidita(D.Prezzi(cal, ch, ch, ch, ch, vol2, {}, []))
    assert L2['AAA'].iloc[t] == L['AAA'].iloc[t]


def test_slittamento_del_simulatore_usa_la_liquidita_del_giorno_prima():
    p = sintetico([10] * 5, [10.1] * 5, [9.9] * 5, [10] * 5)
    liq = pd.DataFrame({'AAA': [6e6, 6e6, 0.0, 0.0, 0.0]}, index=p.calendario)    # giorno 1 liquido; dal giorno 2 illiquido
    sim = M.Simulatore(p, pan_div(p, {}), liquidita=liq, config=M.Config(liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000))                  # acquisto nel giorno 1: usa la liquidita' del giorno 0 (6 mln)
    assert sim.pos['AAA'].prezzo_eff == pytest.approx(10 * 1.0005)
    sim = M.Simulatore(p, pan_div(p, {}), liquidita=liq, config=M.Config(liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(2, 4000))                  # acquisto nel giorno 3: usa la liquidita' del giorno 2 (0)
    assert sim.pos['AAA'].prezzo_eff == pytest.approx(10 * 1.0020)
    liq2 = pd.DataFrame({'AAA': [2e6] * 5}, index=p.calendario)
    sim = M.Simulatore(p, pan_div(p, {}), liquidita=liq2, config=M.Config(liquida_a_fine=False))
    sim.esegui(CompraAlGiorno(0, 4000))
    assert sim.pos['AAA'].prezzo_eff == pytest.approx(10 * 1.0010)


def test_rimozione_righe_duplicate_di_raccomandazioni():
    r = pd.DataFrame({'ticker': ['A', 'A', 'A', 'B'], 'data': pd.to_datetime(['2025-10-01'] * 3 + ['2025-10-01']),
                      'emittente': ['X', 'X', 'Y', 'X'], 'raccomandazione': ['Buy'] * 4, 'target': [10.0, 10.0, 10.0, 10.0],
                      'ordine': [0, 1, 2, 3]})
    out = D.rimuovi_duplicati(r)
    assert list(out.ordine) == [0, 2, 3]
    # sui dati reali non resta nessun duplicato
    pr = D.carica_prezzi()
    rac, _ = D.carica_raccomandazioni(pr)
    assert not rac.duplicated(D.CHIAVE_DUPLICATI).any()


def test_ftsemib_con_dividendi_stimati():
    import riferimenti as RF
    n = 6
    cal = pd.bdate_range('2026-01-05', periods=n)
    ix = pd.DataFrame({'apertura': [100.0] * n, 'massimo': [101.0] * n, 'minimo': [99.0] * n, 'chiusura': [100.0] * n}, index=cal)
    y = pd.Series([0, 0, 0.0, 0.0, 0.01, 0.0], index=cal)          # 1% di dividendo lordo il giorno 4
    # lordo: niente costi, dividendi al 100%, nessuna tassa: 20000 * 1% = 200
    g = RF.ftsemib_bh(ix, y, 0, n - 1, lordo=True)
    assert g['patrimonio_finale'] == pytest.approx(20200.0)
    # netto: dividendo al 74%, commissioni 2 x 6,40+..., slittamento 0,05% per lato, tassa sulla sola plusvalenza di prezzo (negativa: nessuna)
    f = RF.ftsemib_bh(ix, y, 0, n - 1)
    v0 = (20000 - 6.40 + 0.0024 * 1460) / 1.0024
    unita = v0 / (100 * 1.0005)
    div = unita * 0.01 * 100 * 0.74
    v1 = unita * 100 * 0.9995
    atteso = 20000 - v0 - M.commissione(v0) + v1 - M.commissione(v1) + div
    assert f['patrimonio_finale'] == pytest.approx(atteso, rel=1e-9)
    assert f['tassa'] == 0.0                                       # perdita di prezzo per i costi: nessuna imposta
    # senza dividendi e' piu' basso
    assert RF.ftsemib_bh(ix, y, 0, n - 1, con_dividendi=False)['patrimonio_finale'] == pytest.approx(atteso - div, rel=1e-9)


@pytest.fixture(scope='module')
def mercato():
    import strategie as ST
    return ST.Mercato()


def test_strategie_casuali_stesso_calendario_e_filtro_di_liquidita(mercato):
    import strategie as ST
    mk = mercato
    L = 5e6
    reale = mk.sim().esegui(ST.Rotazione(mk, 'MOM', 10, 5, 0, L), inizio=mk.idec, fine=mk.i1)
    tr = reale.trades
    piano = ST.piano_da_trades(tr)
    assert sum(len(v) for v in piano.values()) == len(tr)
    runs = []
    for seme in (1, 1, 2):
        sim = mk.sim()
        sim.esegui(ST.Casuale(mk, L, piano, ST.Regole(), np.random.default_rng(seme)), inizio=mk.idec, fine=mk.i1)
        runs.append(sim)
    # stesso seme -> stessi trade; seme diverso -> titoli diversi
    tk = lambda sim: [x['ticker'] for x in sim.trades]
    assert tk(runs[0]) == tk(runs[1])
    assert tk(runs[0]) != tk(runs[2])
    for sim in runs:
        t = pd.DataFrame(sim.trades)
        assert len(t) == len(tr)                                           # stesso numero di operazioni
        assert sorted(t.i_ingresso) == sorted(tr.i_ingresso)               # stesse date di ingresso
        # uscite 'strategia' alle stesse date della strategia reale
        assert sorted(t.i_uscita) == sorted(tr.i_uscita)
        # tutti i titoli scelti passano l'universo e il filtro di liquidita' il giorno della decisione
        for r in t.itertuples():
            k = mk.col[r.ticker]
            assert mk.elig[L][r.i_ingresso - 1, k]
            assert mk.cx.liq[r.i_ingresso - 1, k] >= L


def test_rotazione_e_eventi_senza_sguardi_al_futuro(mercato):
    import strategie as ST
    mk = mercato
    R, K = 10, 5
    r = mk.sim().esegui(ST.Rotazione(mk, 'COMP', R, K, 0, 1e6), inizio=mk.idec, fine=mk.i1)
    t = r.trades
    assert (t.i_ingresso >= mk.i0).all()                                   # primo acquisto: apertura del 1/9/2025
    assert ((t.i_ingresso - 1 - mk.idec) % R == 0).all()                   # solo nei giorni di ribilanciamento + 1
    for x in t.itertuples():
        assert mk.elig[1e6][x.i_ingresso - 1, mk.col[x.ticker]]
        assert not np.isnan(mk.comp[1e6][x.i_ingresso - 1, mk.col[x.ticker]])
    e = mk.sim().esegui(ST.Eventi(mk, 'ALZ5', 'MOM>0', 5, 1e6, ST.Regole(tempo=60, stop=0.12)), inizio=mk.idec, fine=mk.i1)
    for x in e.trades.itertuples():
        k = mk.col[x.ticker]
        assert mk.eventi['ALZ5'][x.i_ingresso - 1, k] and mk.seg['MOM'][x.i_ingresso - 1, k] > 0   # evento e filtro in t, acquisto in t+1
        assert x.sedute <= 60
    assert (e.trades.motivo.isin(['stop', 'tempo', 'liquidazione_finale'])).all()


def test_il_segnale_composito_usa_ranghi_percentuali_dello_stesso_giorno(mercato):
    mk = mercato
    L = 1e6
    t = mk.idec + 20
    ok = mk.elig[L][t] & ~np.isnan(mk.seg['MOM'][t]) & ~np.isnan(mk.seg['REV'][t])
    k = np.flatnonzero(ok)
    rm = pd.Series(mk.seg['MOM'][t, k]).rank(pct=True).values
    rr = pd.Series(mk.seg['REV'][t, k]).rank(pct=True).values
    assert np.allclose(mk.comp[L][t, k], (rm + rr) / 2)
    assert np.isnan(mk.comp[L][t, ~ok]).all()
