"""Kleine Tests für einzelne Kaufregeln: Positionsgröße, Stop/Ziel/Limit, Quartalszahlen-Sperre, Marktfilter und
höchstens 2 Positionen je Branche. Sie laufen mit den festen Kursdaten aus tests/daten."""
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hilfe  # noqa: E402

sw = hilfe.bot()


@pytest.fixture(scope="module")
def ablauf():
    einst = hilfe.einstellungen()
    daten, alle_tage = hilfe.vorbereiten(einst)
    tagebuch = sw.strategie_tagebuch(daten, einst)
    pausen, _ = sw.lernverlauf(tagebuch, alle_tage, einst)
    depot = sw.simuliere_depot(daten, pausen, einst, einst.lernen)
    return einst, daten, tagebuch, depot


# ---------------------------------------------------------------- Positionsgröße
def test_positionsgroesse_ein_prozent_risiko():
    # 10.000 € Konto, 1 % Risiko = 100 €; Kurs 100, Stop 95 -> 5 € Risiko je Aktie -> 20 Stück
    assert sw.positionsgroesse(100, 95, 10_000, 1, False) == 20


def test_positionsgroesse_grenzen():
    # Stop sehr nah: nach Risiko 200 Stück, aber höchstens 25 % des Kontos = 2.500 € -> 25 Stück
    assert sw.positionsgroesse(100, 99.5, 10_000, 1, False) == 25
    # nicht mehr als das freie Geld
    assert sw.positionsgroesse(100, 95, 10_000, 1, False, bargeld=500) == 5
    # nicht mehr als das noch freie Gesamtrisiko
    assert sw.positionsgroesse(100, 95, 10_000, 1, False, risiko_frei=50) == 10
    # Bruchstücke auf 2 Nachkommastellen abgerundet
    assert sw.positionsgroesse(100, 97, 10_000, 1, True) == pytest.approx(25.0)
    assert sw.positionsgroesse(100, 94, 10_000, 1, True) == pytest.approx(16.66)
    # ohne Abstand zum Stop oder ohne Geld: nichts
    assert sw.positionsgroesse(100, 100, 10_000, 1, False) == 0
    assert sw.positionsgroesse(100, 95, 10_000, 1, False, bargeld=0) == 0


# ---------------------------------------------------------------- Stop, Ziel, Limit
def test_stop_und_ziel_im_abstand_der_atr(ablauf):
    _, daten, _, _ = ablauf
    geprueft = 0
    for d in daten.values():
        for k, (ok, stop, ziel) in d["signale_roh"].items():
            i = np.flatnonzero(ok)
            if not len(i):
                continue
            gegen = sw.STRATEGIEN[k]["art"] == "gegen"
            s_atr = sw.STOP_GEGEN_ATR if gegen else sw.STOP_TREND_ATR
            z_atr = sw.ZIEL_GEGEN_ATR if gegen else sw.ZIEL_TREND_ATR
            r = sw.STRATEGIEN[k]["richtung"]
            assert np.allclose(stop[i], d["C"][i] - r * s_atr * d["ATR"][i]), k
            assert np.allclose(ziel[i], d["C"][i] + r * z_atr * d["ATR"][i]), k
            geprueft += len(i)
    assert geprueft > 500


def test_limit_halber_weg_zum_ziel():
    # Schluss 100, ATR 4: Limit 100 + 0,5 × 4 = 102 – aber höchstens der halbe Weg zum Ziel
    assert sw.limit_kurs(1, 100, 4, 88, 112) == pytest.approx(102)
    assert sw.limit_kurs(1, 100, 4, 88, 103) == pytest.approx(101.5)


def test_einstieg_nur_bis_zum_limit_und_ueber_dem_stop():
    d = {"O": np.array([101.0, 103.0, 90.0])}
    assert sw.einstieg_moeglich(d, 0, 1, 95, 102)          # Eröffnung unter dem Limit: Kauf
    assert not sw.einstieg_moeglich(d, 1, 1, 95, 102)      # Eröffnung über dem Limit: kein Kauf
    assert not sw.einstieg_moeglich(d, 2, 1, 95, 102)      # Eröffnung unter dem Stop: kein Kauf


# ---------------------------------------------------------------- Quartalszahlen
def test_quartalszahlen_sperre_der_tage(ablauf):
    _, daten, _, _ = ablauf
    d = daten["AAPL"]
    reak = np.flatnonzero(d["reak"][:d["n"]])
    assert len(reak) > 20
    for pos in reak[2:-2]:
        # in den 3 Handelstagen vor dem Tag, an dem die Zahlen wirken, kein Einstieg; am Abend davor raus
        assert d["gesperrt"][pos - sw.ZAHLEN_SPERRE_TAGE:pos].all()
        assert d["morgen"][pos - 1]


def test_kein_kauf_vor_quartalszahlen_und_kein_halten_durch_die_zahlen(ablauf):
    _, daten, tagebuch, depot = ablauf
    for e in tagebuch:
        d = daten[e["ticker"]]
        assert not d["gesperrt"][d["pos"][e["signal_tag"]]], e
    for x in depot["trades"]:
        d = daten[x["ticker"]]
        kauf, verkauf = d["pos"][pd.Timestamp(x["kauf_tag"])], d["pos"][pd.Timestamp(x["verkauf_tag"])]
        # der Tag, an dem Zahlen wirken, liegt nie zwischen Kauf und Verkauf
        assert not d["reak"][kauf + 1:verkauf + 1].any(), x


# ---------------------------------------------------------------- Marktfilter
def test_marktfilter_keine_kaeufe_unter_der_200_tage_linie(ablauf):
    _, daten, _, _ = ablauf
    trend = sw.markt_trend(hilfe.kurse("QQQ"))
    gesperrt = 0
    for d in daten.values():
        lage = sw.markt_vortag(trend, d["idx"])
        unten = lage == 0
        for k, (ok, _, _) in d["signale"].items():
            if sw.STRATEGIEN[k]["richtung"] > 0:
                assert not (ok & unten).any(), k
        gesperrt += sum(int((roh & unten).sum()) for roh, _, _ in d["signale_roh"].values())
    assert gesperrt > 0, "die Testdaten sollten Signale enthalten, die der Marktfilter sperrt (z. B. 2022)"


# ---------------------------------------------------------------- Grenzen im Depot
def _gleichzeitig(trades, offen, filter_):
    """Für jeden Kauf: wie viele andere Positionen (nach filter_) liegen am Kauftag im Depot?"""
    alle = [(pd.Timestamp(x["kauf_tag"]), pd.Timestamp(x["verkauf_tag"]), x["ticker"]) for x in trades] + \
           [(pd.Timestamp(p["kauf_tag"]), pd.Timestamp.max, p["ticker"]) for p in offen]
    alle = [a for a in alle if filter_(a[2])]
    # Gekauft wird zur Eröffnung, verkauft erst danach: Eine Position, die am Kauftag verkauft wird, zählt noch mit
    return max((sum(1 for b in alle if b is not a and b[0] <= a[0] <= b[1]) for a in alle), default=0)


def test_hoechstens_5_positionen_und_2_je_branche(ablauf):
    _, _, _, depot = ablauf
    assert _gleichzeitig(depot["trades"], depot["offen"], lambda t: True) <= sw.MAX_POSITIONEN - 1
    tech = _gleichzeitig(depot["trades"], depot["offen"], lambda t: sw.BRANCHE.get(t) == "Technologie")
    assert tech <= sw.MAX_JE_BRANCHE - 1


def test_auftraege_hoechstens_2_je_branche():
    auftrag = lambda t: {"ticker": t, "richtung": 1, "strategie": "ausbruch_long"}
    position = lambda t: {"ticker": t, "richtung": 1}
    # 2 Technologie-Werte im Depot: ein dritter verfällt sicher
    ok, verfallen, nach = sw.ausfuehrbare_auftraege({"positionen": [position("AAPL"), position("NVDA")],
                                                     "auftraege": [auftrag("MSFT"), auftrag("XOM")]})
    assert [a["ticker"] for a in ok] == ["XOM"] and list(verfallen.values()) == [["MSFT"]] and not nach
    # 1 Technologie-Wert im Depot: der erste neue passt, der zweite rückt nur nach
    ok, verfallen, nach = sw.ausfuehrbare_auftraege({"positionen": [position("AAPL")],
                                                     "auftraege": [auftrag("NVDA"), auftrag("MSFT"), auftrag("XOM")]})
    assert [a["ticker"] for a in ok] == ["NVDA", "XOM"] and [a["ticker"] for a in nach] == ["MSFT"]
