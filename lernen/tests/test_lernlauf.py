"""Der ganze Lern-Lauf mit festen, gespeicherten Kursen (lernen/tests/daten, 12 Aktien 2011–2018): kein Blick in
die Zukunft, Punktzahlen und Fehler-Analyse wie erwartet (Fingerabdruck), das Übungsdepot des Bots bleibt unberührt."""
import hashlib
import json
import os
import shutil

import pandas as pd
import pytest

import daten as D
import lernlauf as LL
import merkmale as M
import modell as L
from conftest import DATEN, HIER

WURZEL = os.path.dirname(os.path.dirname(HIER))
FINGERABDRUCK = os.path.join(HIER, "fingerabdruck.json")
WATCHLIST = "AAPL, MSFT, JPM, XOM, JNJ, HD"
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
    assert kurz["ueberraschung"].notna().any()


def _pruefsumme(pfad):
    with open(pfad, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _lauf(tmp, bis):
    return LL.main(["--cache", str(tmp / "cache"), "--ohne-download", "--bis", bis, "--prozesse", "2",
                    "--aus", str(tmp / "aus"), "--papier", str(tmp / "cache" / "papier_test.json"),
                    "--ticker", WATCHLIST])


@pytest.fixture(scope="module")
def lauf(tmp_path_factory):
    """Lern-Lauf am 28.12.2018, dazu ein zweiter am selben Tag (muss das gespeicherte Modell benutzen)."""
    tmp = tmp_path_factory.mktemp("lernen")
    shutil.copytree(DATEN, tmp / "cache")
    mp = pytest.MonkeyPatch()
    mp.setattr(L, "MIN_TRAINING", 300)  # 12 Aktien haben weniger gedachte Trades als der ganze Markt
    bot = os.path.join(WURZEL, "papier", "papier_depot.json")
    vorher = _pruefsumme(bot) if os.path.exists(bot) else None
    try:
        _lauf(tmp, "2018-12-28")
        erster = (tmp / "aus" / "punkte.json").read_text(encoding="utf-8")
        modelle = sorted(os.listdir(tmp / "cache" / "modell"))
        zeit = {m: os.path.getmtime(tmp / "cache" / "modell" / m) for m in modelle}
        _lauf(tmp, "2018-12-28")
    finally:
        mp.undo()
    nachher = _pruefsumme(bot) if os.path.exists(bot) else None
    return {"tmp": tmp, "erster": erster, "modelle": modelle, "zeit": zeit, "bot": (vorher, nachher)}


def _lies(lauf, name):
    return json.loads((lauf["tmp"] / "aus" / name).read_text(encoding="utf-8"))


def test_punktzahlen_fuer_den_bot(lauf):
    p = _lies(lauf, "punkte.json")
    assert p["tag"] == "2018-12-28" and p["monat"] == "2018-12" and p["anteil"] == 0.3
    assert len(p["tage"]) == LL.PUNKTE_TAGE and "2018-12-28" in p["tage"]
    alle = [z for tag in p["tage"].values() for z in tag.values()]
    assert alle and all(0 < z["punkte"] < 1 and 0 <= z["rang"] <= 100 for z in alle)
    assert {t for tag in p["tage"].values() for t, z in tag.items() if z["watchlist"]} <= set(
        D.watchlist(WATCHLIST))
    # Sperre und Verlauf für den Bot: nur Watchlist, über die letzten Monate
    assert len(p["sperre"]) > 20 and len(p["verlauf"]) > 20
    assert {t for liste in p["sperre"].values() for t in liste} <= set(D.watchlist(WATCHLIST))
    assert all(z["punkte"] >= p["schwelle"] for z in alle if z["beste"])


def test_gleicher_tag_gleiche_punktzahlen_und_gespeichertes_modell(lauf):
    ohne_stand = lambda text: {k: v for k, v in json.loads(text).items() if k != "stand"}  # noqa: E731
    assert ohne_stand(lauf["erster"]) == ohne_stand((lauf["tmp"] / "aus" / "punkte.json").read_text(encoding="utf-8"))
    ordner = lauf["tmp"] / "cache" / "modell"
    assert sorted(os.listdir(ordner)) == lauf["modelle"]  # kein neues Modell im selben Monat
    assert all(os.path.getmtime(ordner / m) == z for m, z in lauf["zeit"].items())
    assert "modell_2018-12.pkl" in lauf["modelle"]


def test_lernstand_und_fehler_analyse(lauf):
    ls = _lies(lauf, "lernstand.json")
    assert ls["gelernt"] and ls["guete"]["n"] > 100 and ls["training"] >= 300
    assert {x["grund"] for x in ls["fehler"]["tabelle"]} >= {"markt", "zahlen", "kursluecke"}
    bt = {t["ticker"]: t for t in ls["bot_trades"]}
    assert set(bt) == {"AAPL", "XOM", "JPM"}
    assert bt["XOM"]["fehler"] == [] and bt["XOM"]["R"] > 0  # Gewinner: keine Fehler
    assert bt["AAPL"]["fertig"] and "markt" in bt["AAPL"]["fehler"]  # Absturz Anfang Februar 2018
    assert bt["JPM"]["fehler"] and bt["JPM"]["fehler_text"]
    text = (lauf["tmp"] / "aus" / "LERNEN.md").read_text(encoding="utf-8")
    for teil in ("# 🧠 Lernmodell des Swing-Bots", "## ⚠️ Daten", "## 📋 Kauf-Signale vom 28.12.2018",
                 "## 🧠 Was das Modell gelernt hat", "## 🔎 Häufigste Fehler", "## 📒 Fehler-Analyse der Trades",
                 "Überlebens-Verzerrung"):
        assert teil in text, teil


def test_uebungsdepot_des_bots_bleibt_unberuehrt(lauf):
    vorher, nachher = lauf["bot"]
    assert vorher == nachher


def _fingerabdruck(lauf):
    p, ls = _lies(lauf, "punkte.json"), _lies(lauf, "lernstand.json")
    return {"schwelle": round(p["schwelle"], 4),
            "punkte": {tag: {t: z["punkte"] for t, z in sorted(liste.items())} for tag, liste in p["tage"].items()},
            "gesperrt": sum(len(v) for v in p["sperre"].values()),
            "fehler": {t["ticker"]: t["fehler"] for t in ls["bot_trades"]},
            "gelernt": [x["merkmal"] for x in ls["gelernt"][:5]],
            "auc": round(ls["guete"]["auc"], 4)}


def test_fingerabdruck(lauf):
    """Ändert sich das Ergebnis, hat sich am Lern-Teil etwas geändert. Absichtlich? Dann neu speichern mit
    LERNEN_FINGERABDRUCK_NEU=1 python -m pytest lernen/tests/test_lernlauf.py und im Pull Request erklären."""
    neu = _fingerabdruck(lauf)
    if os.environ.get("LERNEN_FINGERABDRUCK_NEU"):
        with open(FINGERABDRUCK, "w", encoding="utf-8") as f:
            json.dump(neu, f, ensure_ascii=False, indent=1)
    with open(FINGERABDRUCK, encoding="utf-8") as f:
        alt = json.load(f)
    assert neu["fehler"] == alt["fehler"] and neu["gesperrt"] == alt["gesperrt"]
    assert neu["gelernt"] == alt["gelernt"]
    for tag, liste in alt["punkte"].items():
        assert neu["punkte"][tag] == pytest.approx(liste, abs=1e-4)
    assert neu["schwelle"] == pytest.approx(alt["schwelle"], abs=1e-4)
    assert neu["auc"] == pytest.approx(alt["auc"], abs=1e-4)
