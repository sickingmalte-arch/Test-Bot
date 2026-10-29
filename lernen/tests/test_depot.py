"""Depot-Simulation des Rückblicks: Grenzen (1 % Risiko je Trade, 5 Positionen, 2 je Branche), Ausstiegs-Varianten,
Speichern und Weiterrechnen."""
import json

import numpy as np
import pandas as pd
import pytest

import depot as P
import merkmale as M
from conftest import kunst_kurse

SEKTOR = ["Information Technology", "Energy", "Health Care"]


@pytest.fixture(scope="module")
def welt():
    """8 erfundene Aktien mit echten Signalen des Bots, dazu ein erfundener S&P 500 und Euro-Kurs."""
    fx = pd.Series(1.1, index=pd.bdate_range("2014-01-01", "2020-12-31"))
    daten, kand = {}, []
    for n in range(8):
        df = kunst_kurse(seed=n, trend=0.0006)
        d, k, _ = M.merkmale_aktie(f"A{n}", df, fx, None, None)
        daten[f"A{n}"] = d
        k["sektor"] = SEKTOR[n % 3]
        kand.append(k)
    kand = pd.concat(kand, ignore_index=True)
    kand["rs63"] = kand["mom63"]
    kand["punkte"] = np.random.default_rng(7).random(len(kand))
    daten["__SPY__"] = kunst_kurse(seed=99)
    tage = daten["A0"]["idx"][250:]
    return daten, kand, tage


@pytest.mark.parametrize("variante", list(P.VARIANTEN))
def test_grenzen_werden_nie_ueberschritten(welt, variante):
    daten, kand, tage = welt
    je_tag = P.tagesliste(kand, "modell", 0, daten)
    panik = P.panik_tage(daten["__SPY__"])
    dep = P.Depot(variante)
    for tag in tage:
        vorher = set(dep.positionen)
        dep.eroeffnung(tag, daten)
        pos = list(dep.positionen.values())
        assert len(pos) <= 5
        assert max([sum(1 for p in pos if p["sektor"] == s) for s in SEKTOR]) <= 2
        if set(dep.positionen) - vorher:  # beim Kauf zusammen höchstens 5 % Risiko
            assert sum(p["risiko_plan"] for p in pos) <= 0.05 * dep.wert + 1e-6
        for p in pos:
            assert p["risiko_plan"] <= 0.01 * p["depotwert"] + 1e-6  # nie mehr als 1 % Risiko je Trade
            assert p["kosten"] - 1.0 <= 0.25 * p["depotwert"] + 1e-6  # höchstens 25 % je Position
            if p["notbremse"] is not None:  # Stop erst zum Schluss: Stückzahl nach der weiteren Notbremse
                assert p["notbremse"] < p["stop"]
        dep.ausstiege(tag, daten, bool(panik.get(tag, False)))
        dep.neue_auftraege(je_tag.get(tag, []))
        dep.bewerten(tag, daten)
    assert len(dep.trades) > 20
    # Verlust je Trade: höchstens 1 % plus Kurslücke über die Notbremse bzw. den Stop hinaus
    for t in dep.trades:
        if "Kurslücke" not in t["grund"]:
            assert t["erloes"] - t["kosten"] >= -0.01 * t["depotwert"] - 2.5 - 0.003 * t["kosten"]


def test_speichern_und_weiterrechnen_gibt_dasselbe(welt):
    daten, kand, tage = welt
    ganz = P.simuliere(daten, kand, tage, auswahl="modell", variante="panik")
    je_tag = P.tagesliste(P.auswaehlen(kand[kand["tag"].isin(tage)], "modell"), "modell", 0, daten)
    panik = P.panik_tage(daten["__SPY__"])
    dep = P.Depot("panik")
    teil = len(tage) // 2
    for tag in tage[:teil]:
        dep.tag(tag, daten, je_tag.get(tag, []), bool(panik.get(tag, False)))
    dep = P.Depot.aus_dict(json.loads(json.dumps(dep.als_dict())))  # wie im Übungsdepot gespeichert
    for tag in tage[teil:]:
        dep.tag(tag, daten, je_tag.get(tag, []), bool(panik.get(tag, False)))
    assert len(dep.trades) == len(ganz["trades"])
    assert dep.wert == pytest.approx(ganz["kurve"].iloc[-1], rel=1e-9)
    assert [t["ticker"] for t in dep.trades] == [t["ticker"] for t in ganz["trades"]]


def _tag(o, h, l, c):
    return {"O": np.array([100.0, o]), "H": np.array([101.0, h]), "L": np.array([99.0, l]),
            "C": np.array([100.0, c]), "morgen": np.zeros(2, bool), "n": 2}


POS = {"start": 0, "stop": 95.0, "ziel": 110.0, "notbremse": 92.5, "stark": True}


def test_stop_zum_schluss_und_notbremse():
    # Kurs fällt im Tag unter den Stop, schließt aber darüber: „normal“ verkauft, „schluss“ hält
    assert P._ausstieg(_tag(99, 100, 94, 96), 1, POS, "normal", False) == (95.0, "Stop")
    assert P._ausstieg(_tag(99, 100, 94, 96), 1, POS, "schluss", False) == (None, None)
    assert P._ausstieg(_tag(99, 100, 94, 94.5), 1, POS, "schluss", False) == (94.5, "Stop zum Schluss")
    assert P._ausstieg(_tag(99, 100, 92, 96), 1, POS, "schluss", False) == (92.5, "Notbremse")
    assert P._ausstieg(_tag(91, 93, 90, 92), 1, POS, "schluss", False) == (91, "Notbremse (Kurslücke)")
    # Panik-Regel nur an Panik-Tagen, „stark“ nur bei starken Aktien
    assert P._ausstieg(_tag(99, 100, 94, 96), 1, POS, "panik", False) == (95.0, "Stop")
    assert P._ausstieg(_tag(99, 100, 94, 96), 1, POS, "panik", True) == (None, None)
    assert P._ausstieg(_tag(99, 100, 94, 96), 1, dict(POS, stark=False), "stark", False) == (95.0, "Stop")


def test_panik_tage():
    tage = pd.bdate_range("2020-03-02", periods=4)
    spy = pd.DataFrame({"Open": [100, 98, 99.5, 100], "Low": [99, 97, 96, 99.5], "Close": [100, 99, 99.6, 100]},
                       index=tage)
    assert list(P.panik_tage(spy)) == [False, True, True, False]  # −2 % Eröffnung, −3 % im Tag


def test_kosten_und_kaufen_und_halten():
    tage = pd.bdate_range("2020-01-01", periods=300)
    df = pd.DataFrame({"Open": 100.0, "Close": 100.0}, index=tage)
    erg = P.kaufen_und_halten(df, pd.Series(1.0, index=tage), tage[0], tage[-1])
    assert -0.2 < erg["rendite"] < 0  # nur Gebühr und Spread
    assert erg["rueckgang"] == 0
