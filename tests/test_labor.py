"""Tests für das Strategie-Labor (labor/strategie_labor.py): kein Blick in die Zukunft, Kosten, Stop mit Kurslücke,
Shorts und ein reproduzierbarer Walk-Forward mit den festen Testdaten. Der Swing-Bot wird dabei nicht verändert."""
import importlib.util
import json
import pathlib

import numpy as np
import pandas as pd

WURZEL = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("strategie_labor", WURZEL / "labor" / "strategie_labor.py")
labor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(labor)

BRANCHE = labor.swing_bot().BRANCHE
GEBUEHR, SPREAD = labor.KOSTEN

GRUND = {"familie": "momentum", "rueckblick": 20, "trendlinie": 50, "marktfilter": "aus", "markt_ausstieg": False,
         "short": "aus", "max_long": 1, "max_short": 1, "stop_atr": None, "zeitstopp": None, "umschichten": 5,
         "rsi_grenze": 10, "hebel": 1.0}


def kerzen(schluss, oeffnung=None, spanne=0.01):
    schluss = np.asarray(schluss, dtype=float)
    tage = pd.bdate_range("2015-01-01", periods=len(schluss), name="Date")
    oeffnung = np.r_[schluss[0], schluss[:-1]] if oeffnung is None else np.asarray(oeffnung, dtype=float)
    hoch = np.maximum(oeffnung, schluss) * (1 + spanne)
    tief = np.minimum(oeffnung, schluss) * (1 - spanne)
    return pd.DataFrame({"Open": oeffnung, "High": hoch, "Low": tief, "Close": schluss}, index=tage)


def markt(**aktien):
    erste = next(iter(aktien.values()))
    return labor.Markt({"QQQ": erste, **aktien}, BRANCHE)


def test_kein_blick_in_die_zukunft():
    """Ändern sich die Kurse nach Tag x, bleibt alles bis Tag x gleich: Wertverlauf und Trades."""
    daten = labor.lade_ordner(WURZEL / "tests" / "daten" / "kurse")
    x = 1500
    zukunft = {}
    rng = np.random.default_rng(7)
    for t, df in daten.items():
        df = df.copy()
        faktor = np.r_[np.ones(x + 1), rng.uniform(0.5, 1.5, len(df) - x - 1)]
        zukunft[t] = df.mul(faktor, axis=0)
    g = dict(GRUND, familie="ausbruch", short="immer", max_long=3, max_short=2, stop_atr=3.0, zeitstopp=20,
             marktfilter="beides", markt_ausstieg=True, hebel=1.5)
    a = labor.simuliere(labor.Markt(daten, BRANCHE), g, 300, x, glattstellen=False)
    b = labor.simuliere(labor.Markt(zukunft, BRANCHE), g, 300, x, glattstellen=False)
    assert len(a["trades"]) > 5
    assert np.allclose(a["werte"], b["werte"])
    assert a["trades"] == b["trades"]


def test_kosten_bei_seitwaerts():
    """Kauf und Verkauf zum gleichen Kurs: Verlust genau 2 × Gebühr + 2 × Spread."""
    steigend = 50 * 1.004 ** np.arange(300)
    schluss = np.r_[steigend, np.full(60, steigend[-1])]
    df = kerzen(schluss)
    m = markt(AAPL=df)
    g = dict(GRUND, zeitstopp=10)
    erg = labor.simuliere(m, g, 300, 330)
    trade = erg["trades"][0]
    kurs = steigend[-1]
    erwartet = trade["einstieg"] / (1 + SPREAD)
    assert abs(erwartet - kurs) < 0.01
    stueck = round(-(trade["ergebnis"] + 2 * GEBUEHR) / (kurs * 2 * SPREAD))
    assert stueck >= 1
    assert abs(trade["ergebnis"] - (-stueck * kurs * 2 * SPREAD - 2 * GEBUEHR)) < 0.05
    assert trade["grund"] == "Zeitstopp"


def test_stop_mit_kursluecke():
    """Öffnet die Aktie unter dem Stop, wird zum Eröffnungskurs verkauft, nicht zum Stop."""
    schluss = 50 * 1.004 ** np.arange(320)
    oeffnung = np.r_[schluss[0], schluss[:-1]]
    schluss[310:], oeffnung[310] = schluss[310:] * 0.8, schluss[309] * 0.8
    df = kerzen(schluss, oeffnung)
    m = markt(AAPL=df)
    g = dict(GRUND, stop_atr=2.0)
    erg = labor.simuliere(m, g, 300, 315)
    stop = [t for t in erg["trades"] if t["grund"].startswith("Stop")]
    assert stop and stop[0]["grund"] == "Stop (Kurslücke)"
    assert abs(stop[0]["ausstieg"] - oeffnung[310] * (1 - SPREAD)) < 0.01


def test_short_verdient_bei_fallendem_kurs():
    schluss = 100 * 0.997 ** np.arange(450)
    m = markt(AAPL=kerzen(schluss, spanne=0.003))
    g = dict(GRUND, marktfilter="qqq", short="nur_baerenmarkt")
    erg = labor.simuliere(m, g, 300, 449)
    k = labor.kennzahlen(erg["werte"], erg["trades"])
    assert k["short_trades"] >= 1 and k["short"] > 0 and k["long"] == 0
    assert erg["werte"][-1] > labor.START_KAPITAL


def test_walk_forward_reproduzierbar(tmp_path):
    """Gleicher Zufallsstart, gleiche Daten: gleiches Ergebnis. Testjahre 2021–2024, Gedächtnis zählt nichts doppelt."""
    args = ["--daten", str(WURZEL / "tests" / "daten" / "kurse"), "--budget", "klein", "--seed", "3"]
    a = labor.main(args + ["--ausgabe", str(tmp_path / "a")])
    b = labor.main(args + ["--ausgabe", str(tmp_path / "b")])
    assert a["walk_forward"] == b["walk_forward"]
    assert [s["jahr"] for s in a["walk_forward"]["schritte"]] == [2021, 2022, 2023, 2024]
    for s in a["walk_forward"]["schritte"]:
        assert set(s["genom"]) == set(labor.GENE)
    belege = json.loads((tmp_path / "a" / "gedaechtnis.json").read_text(encoding="utf-8"))["belege"]
    labor.main(args + ["--ausgabe", str(tmp_path / "a")])
    wieder = json.loads((tmp_path / "a" / "gedaechtnis.json").read_text(encoding="utf-8"))["belege"]
    assert len(wieder) == len(belege)
    assert (tmp_path / "a" / "BERICHT.md").read_text(encoding="utf-8").startswith("# 🧪 Strategie-Labor")


def test_gewichte_lernen_aus_verlusten():
    """Gen-Werte, die im Testjahr hinter dem Nasdaq-100 lagen, werden seltener gezogen, aber nie gar nicht."""
    belege = [{"genom": dict(GRUND, short="immer"), "ueberschuss": -30.0} for _ in range(20)]
    belege += [{"genom": dict(GRUND, short="aus"), "ueberschuss": 10.0} for _ in range(20)]
    w = labor.gewichte_aus(belege)["short"]
    assert w['"immer"'] == 0.3
    assert w['"aus"'] > 1
