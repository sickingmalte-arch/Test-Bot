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
    buecher = dict(GRUND, short="immer", max_long=3, max_short=2, ueberspringen=21, rangfolge="hoch_52w",
                   groesse="volatilitaet", saison="nov_bis_apr", rueckblick=60, volaziel=12, bremse=8)
    for genom in (g, buecher, dict(g, groesse="atr_risiko")):
        a = labor.simuliere(labor.Markt(daten, BRANCHE), genom, 300, x, glattstellen=False)
        b = labor.simuliere(labor.Markt(zukunft, BRANCHE), genom, 300, x, glattstellen=False)
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
    assert "Bibliothek" in (tmp_path / "a" / "WISSEN.md").read_text(encoding="utf-8")
    assert len(a["wissen"]) == len(labor.lade_bibliothek(WURZEL / "labor" / "bibliothek.json")["hypothesen"])


def test_gewichte_lernen_aus_verlusten():
    """Gen-Werte, die im Testjahr hinter dem Nasdaq-100 lagen, werden seltener gezogen, aber nie gar nicht."""
    belege = [{"genom": dict(GRUND, short="immer"), "ueberschuss": -30.0} for _ in range(20)]
    belege += [{"genom": dict(GRUND, short="aus"), "ueberschuss": 10.0} for _ in range(20)]
    w = labor.gewichte_aus(belege)["short"]
    assert w['"immer"'] == 0.3
    assert w['"aus"'] > 1


def test_alte_bauplaene_rechnen_wie_vorher():
    """Fehlen die Gene aus der Bibliothek (alter Bauplan im Gedächtnis), gilt das Verhalten ohne die Lehren."""
    m = labor.Markt(labor.lade_ordner(WURZEL / "tests" / "daten" / "kurse"), BRANCHE)
    alt = dict(GRUND, max_long=3)
    neu = dict(alt, ueberspringen=0, rangfolge="momentum", groesse="gleich", saison="immer")
    assert np.array_equal(labor.simuliere(m, alt, 300, 900)["werte"], labor.simuliere(m, neu, 300, 900)["werte"])


def test_saison_kauft_nur_von_november_bis_april():
    m = labor.Markt(labor.lade_ordner(WURZEL / "tests" / "daten" / "kurse"), BRANCHE)
    erg = labor.simuliere(m, dict(GRUND, saison="nov_bis_apr", max_long=3), 300, 1800)
    assert erg["trades"]
    for t in erg["trades"]:
        assert int(t["kauf"][5:7]) in (11, 12, 1, 2, 3, 4, 5)  # Kauf zur Eröffnung nach einem Signal bis Ende April
        if int(t["kauf"][5:7]) == 5:
            assert int(t["kauf"][8:10]) <= 3


def test_bibliothek_passt_zum_bauplan(tmp_path):
    bib = labor.lade_bibliothek(WURZEL / "labor" / "bibliothek.json")
    quellen = {q["id"] for q in bib["quellen"]}
    assert len(bib["hypothesen"]) >= 10 and len(quellen) >= 10
    for q in bib["quellen"]:
        assert q["link"].startswith("https://") and q["kernaussagen"] and q["vorsicht"]
    kaputt = tmp_path / "bibliothek.json"
    kaputt.write_text(json.dumps(dict(bib, hypothesen=[dict(bib["hypothesen"][0], test=999)])), encoding="utf-8")
    try:
        labor.lade_bibliothek(kaputt)
    except ValueError:
        return
    raise AssertionError("eine Hypothese mit unbekanntem Wert muss abgelehnt werden")


def test_urteile_streng_wie_harvey_liu_zhu():
    assert labor.urteil_fuer(5.0, 0.0, 3.5, 0.0) == "bestaetigt"
    assert labor.urteil_fuer(5.0, 0.0, 2.5, 0.0) == "tendenz"
    assert labor.urteil_fuer(0.5, 0.1, 0.5, 0.2) == "unklar"
    assert labor.urteil_fuer(-17.9, -2.7, -3.9, -2.4) == "verworfen"  # viel Rendite für wenig Ruhe
    assert labor.urteil_fuer(-0.3, -5.0, -0.2, -3.5) == "bestaetigt"  # deutlich ruhiger, kaum Rendite verloren
    assert labor.urteil_fuer(1.0, 6.0, 0.5, 3.0) == "verworfen"       # tieferer Rückgang ohne mehr Rendite


def test_deflated_sharpe_wird_mit_mehr_versuchen_strenger():
    rng = np.random.default_rng(1)
    werte = 10_000 * np.cumprod(1 + rng.normal(0.0008, 0.01, 750))
    sharpes = list(rng.normal(0.5, 0.6, 200))
    einer = labor.deflated_sharpe(werte, [1.0])
    viele = labor.deflated_sharpe(werte, sharpes)
    assert einer["schwelle"] == 0.0
    assert viele["schwelle"] > 1.0 and viele["dsr"] < einer["dsr"]


def test_verlustbremse_begrenzt_den_absturz():
    """Fällt das Depot 8 % unter seinen Höchststand, schließt es alles und kauft erst nach der Pause wieder."""
    steigend = 50 * 1.004 ** np.arange(320)
    schluss = np.r_[steigend, steigend[-1] * 0.985 ** np.arange(1, 41), np.full(40, steigend[-1] * 0.985 ** 40)]
    m = markt(AAPL=kerzen(schluss, spanne=0.002))
    langsam = dict(GRUND, rueckblick=250, trendlinie=200, umschichten=20)  # steigt selbst erst spät aus
    ohne = labor.simuliere(m, langsam, 300, 399)
    mit = labor.simuliere(m, dict(langsam, bremse=8), 300, 399)
    assert labor.kennzahlen(ohne["werte"])["rueckgang"] > 20
    assert labor.kennzahlen(mit["werte"])["rueckgang"] < 12
    assert any(t["grund"] == "Verlustbremse" for t in mit["trades"])
