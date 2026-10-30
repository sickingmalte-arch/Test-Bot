"""Fehler-Analyse: Warum hat ein Trade verloren?"""
import numpy as np
import pandas as pd

import fehler as F


def _aktie(n=40, kurs=100.0):
    tage = pd.bdate_range("2022-01-03", periods=n)
    c = np.full(n, kurs)
    return {"idx": tage, "n": n, "O": c.copy(), "H": c + 1, "L": c - 1, "C": c.copy(), "ATR": np.full(n, 2.0),
            "gerade": np.zeros(n, bool)}


def _markt(d, werte=None):
    return pd.Series(werte if werte is not None else np.full(d["n"], 400.0), index=d["idx"])


def _trade(**k):
    t = {"signal_i": 9, "einstieg_i": 10, "ausstieg_i": 15, "einstieg": 100.0, "grund": "Stop", "R": -1.0}
    t.update(k)
    return t


def test_gewinner_haben_keinen_fehler():
    d = _aktie()
    assert F.gruende(_trade(R=0.8, grund="Ziel"), d, _markt(d)) == []


def test_normales_auf_und_ab():
    d = _aktie()
    d["C"][16:] = 97  # nach dem Stop nicht wieder über dem Einstieg
    assert F.gruende(_trade(), d, _markt(d)) == ["normal"]


def test_kursluecke_markt_und_zahlen():
    d = _aktie()
    d["C"][16:] = 97
    spy = _markt(d)
    spy.iloc[12:] = 380  # S&P 500 −5 %
    d["gerade"][12] = True  # Quartalszahlen während des Trades
    g = F.gruende(_trade(grund="Stop (Kurslücke)"), d, spy)
    assert "kursluecke" in g and "markt" in g and "zahlen" in g


def test_branche_schwach():
    d = _aktie()
    d["C"][16:] = 97
    branche = _markt(d).copy()
    branche.iloc[12:] = 380  # Branche −5 %, Markt unverändert
    assert "branche" in F.gruende(_trade(), d, _markt(d), branche)


def test_signal_zu_spaet_und_stop_zu_eng():
    d = _aktie()
    d["O"][10] = 102  # Kauf 1 ATR über dem Signalkurs
    d["C"][16:] = 103  # nach dem Stop schnell wieder über dem Einstieg (102)
    g = F.gruende(_trade(einstieg=102.0), d, _markt(d))
    assert "zu_spaet" in g and "stop_eng" in g
    assert "zu_spaet" in F.gruende(_trade(), _aktie(), _markt(d), gelaufen=5.0)


def test_nachricht_nur_wenn_der_markt_ruhig_ist():
    d = _aktie()
    d["C"][16:] = 97
    d["C"][13] = 92  # −8 = −4 ATR an einem Tag
    assert "nachricht" in F.gruende(_trade(), d, _markt(d))
    spy = _markt(d)
    spy.iloc[13:] = 390  # an dem Tag fiel auch der Markt (−2,5 %)
    assert "nachricht" not in F.gruende(_trade(), d, spy)


def test_auswertung_und_vergleich():
    trades = [{"R": -1.0, "fehler": ["markt", "zahlen"]}, {"R": -0.5, "fehler": ["markt"]}, {"R": 1.0, "fehler": []}]
    tab = F.auswertung(trades).set_index("grund")
    assert tab.loc["markt", "anzahl"] == 2 and tab.loc["markt", "anteil"] == 1.0
    assert tab.loc["zahlen", "R"] == -1.0
    kand = pd.DataFrame({"status": ["fertig"] * 4, "R": [-1, -1, 1, 1], "fehler": ["markt", "zahlen", "", ""]})
    v = F.vergleich(kand, [True, False, True, False]).set_index("grund")
    assert v.loc["markt", "alle"] == 0.25 and v.loc["markt", "ausgewaehlt"] == 0.5
    assert v.loc["zahlen", "ausgewaehlt"] == 0.0
    assert v.attrs["verlust_alle"] == 0.5
