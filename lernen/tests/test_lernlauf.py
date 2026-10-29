"""Das ganze Labor mit festen, gespeicherten Kursen (labor/tests/daten, 12 Aktien 2012–2018): kein Blick in die
Zukunft, Übungsdepot und Bericht wie erwartet (Fingerabdruck), der Swing-Bot bleibt unberührt."""
import hashlib
import json
import os
import shutil

import numpy as np
import pandas as pd
import pytest

import daten as D
import labor as LAB
import merkmale as M
import modell as L
from conftest import DATEN, HIER

WURZEL = os.path.dirname(os.path.dirname(HIER))
FINGERABDRUCK = os.path.join(HIER, "fingerabdruck.json")
ERGEBNIS_SPALTEN = {"status", "einstieg_i", "einstieg", "ausstieg_i", "ausstieg", "grund", "R", "einstieg_tag",
                    "ausstieg_tag", "fehler"}


def test_merkmale_schauen_nicht_in_die_zukunft():
    t = "AAPL"
    df = D.lies_kurse(DATEN, t)
    fx = D.lies_kurse(DATEN, "EURUSD=X")["Close"]
    termine, bilanz = D.lies_termine(DATEN, t), D.lies_bilanz(DATEN, t)
    _, ganz, _ = M.merkmale_aktie(t, df, fx, termine, bilanz)
    schnitt = pd.Timestamp("2016-06-30")
    _, kurz, _ = M.merkmale_aktie(t, df[df.index <= schnitt], fx, termine, bilanz)
    a = ganz[ganz["tag"] <= schnitt].reset_index(drop=True)
    assert len(a) == len(kurz) > 20  # dieselben Signale
    spalten = [c for c in kurz.columns if c not in ERGEBNIS_SPALTEN]
    pd.testing.assert_frame_equal(a[spalten], kurz[spalten], check_dtype=False)
    assert kurz["gewinnrendite"].notna().mean() > 0.5  # Bilanzdaten sind wirklich dabei


def _lauf(tmp_path, bis):
    return LAB.main(["--cache", str(tmp_path / "cache"), "--ohne-download", "--bis", bis, "--prozesse", "2",
                     "--papier", str(tmp_path / "papier_labor.json"), "--bericht", str(tmp_path / "BERICHT.md"),
                     "--lernstand", str(tmp_path / "lernstand.json"),
                     "--rueckblick", str(tmp_path / "gibt_es_nicht.json")])


def _pruefsumme(pfad):
    with open(pfad, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture(scope="module")
def zwei_laeufe(tmp_path_factory, request):
    """Erster Lauf am 29.06.2018 (legt das Übungsdepot an), zweiter am 31.12.2018 (rechnet ein halbes Jahr weiter)."""
    tmp = tmp_path_factory.mktemp("labor")
    shutil.copytree(DATEN, tmp / "cache")
    mp = pytest.MonkeyPatch()
    mp.setattr(L, "MIN_TRAINING", 300)  # 12 Aktien haben weniger gedachte Trades als der ganze Markt
    bot = os.path.join(WURZEL, "papier", "papier_depot.json")
    vorher = _pruefsumme(bot) if os.path.exists(bot) else None
    try:
        _lauf(tmp, "2018-06-29")
        mit_depot = json.loads((tmp / "papier_labor.json").read_text(encoding="utf-8"))
        _lauf(tmp, "2018-12-31")
    finally:
        mp.undo()
    nachher = _pruefsumme(bot) if os.path.exists(bot) else None
    return tmp, mit_depot, vorher, nachher


def test_uebungsdepot_wird_angelegt_und_fortgeschrieben(zwei_laeufe):
    tmp, erster, _, _ = zwei_laeufe
    assert erster["angelegt"] == erster["bis"] == "2018-06-29"
    assert erster["depotwert"] == 10_000 and erster["positionen"] == [] and erster["verlauf"][0][1] == 10_000
    z = json.loads((tmp / "papier_labor.json").read_text(encoding="utf-8"))
    assert z["angelegt"] == "2018-06-29" and z["bis"] == "2018-12-31"
    tage = pd.bdate_range("2018-06-29", "2018-12-31")
    assert 120 <= len(z["verlauf"]) <= len(tage)  # ein Wert je Börsentag
    assert len(z["trades"]) > 0
    for t in z["trades"]:
        assert t["risiko_plan"] <= 0.01 * t["depotwert"] + 1e-6
        assert t["R"] >= 0 or t["fehler"]  # jeder Verlust hat eine Fehler-Analyse


def test_bericht_und_lernstand(zwei_laeufe):
    tmp = zwei_laeufe[0]
    text = (tmp / "BERICHT.md").read_text(encoding="utf-8")
    for teil in ("# 🧪 Lern-Labor – Bericht", "## ⚠️ Daten", "## 💼 Übungsdepot des Labors",
                 "### Abgeschlossene Trades mit Fehler-Analyse", "## 🧠 Was das Modell gelernt hat",
                 "## 🔎 Häufigste Fehler", "Überlebens-Verzerrung", "Nasdaq-100 kaufen und halten"):
        assert teil in text, teil
    ls = json.loads((tmp / "lernstand.json").read_text(encoding="utf-8"))
    assert ls["monat"] == "2018-12" and ls["gelernt"] and ls["guete"]["n"] > 100
    assert {x["grund"] for x in ls["fehler"]["tabelle"]} >= {"markt", "zahlen", "kursluecke"}


def test_swing_bot_bleibt_unberuehrt(zwei_laeufe):
    _, _, vorher, nachher = zwei_laeufe
    assert vorher == nachher


def _fingerabdruck(tmp):
    z = json.loads((tmp / "papier_labor.json").read_text(encoding="utf-8"))
    return {"depotwert": round(z["depotwert"], 4), "bargeld": round(z["bargeld"], 4),
            "trades": [[t["ticker"], t["kauf_tag"], t["verkauf_tag"], round(t["R"], 4)] for t in z["trades"]],
            "positionen": sorted(z["positionen"][i]["ticker"] for i in range(len(z["positionen"]))),
            "auftraege": [a["ticker"] for a in z["auftraege"]]}


def test_fingerabdruck(zwei_laeufe):
    """Ändert sich das Ergebnis, hat sich am Labor etwas geändert. Absichtlich? Dann neu speichern mit
    LABOR_FINGERABDRUCK_NEU=1 python -m pytest labor/tests/test_labor.py und im Pull Request erklären."""
    neu = _fingerabdruck(zwei_laeufe[0])
    if os.environ.get("LABOR_FINGERABDRUCK_NEU"):
        with open(FINGERABDRUCK, "w", encoding="utf-8") as f:
            json.dump(neu, f, ensure_ascii=False, indent=1)
    with open(FINGERABDRUCK, encoding="utf-8") as f:
        alt = json.load(f)
    assert neu["trades"] == alt["trades"]
    assert neu["positionen"] == alt["positionen"] and neu["auftraege"] == alt["auftraege"]
    assert neu["depotwert"] == pytest.approx(alt["depotwert"], abs=0.01)
    assert np.isfinite(neu["bargeld"])
