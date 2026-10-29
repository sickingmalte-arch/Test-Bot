"""Der Bot wendet das Ergebnis des Lern-Laufs an: Punktzahl je Signal im Bericht, nur Signale mit guter Punktzahl
kaufen, Fehler-Analyse im Gehirn."""
import json
import os
import sys
import types

import pandas as pd

import merkmale as M

sw = M.sw
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tests"))
import hilfe  # noqa: E402  (Hilfen der Bot-Tests: feste Kurse 2017–2024)

PUNKTE = {"tag": "2026-10-28", "anteil": 0.3, "schwelle": 0.57, "tage": {"2026-10-28": {
    "NOW": {"strategie": "ruecksetzer_long", "punkte": 0.61, "rang": 82, "beste": True, "watchlist": True},
    "SOFI": {"strategie": "ausbruch_long", "punkte": 0.44, "rang": 12, "beste": False, "watchlist": True},
    "CSCO": {"strategie": "rsi2_long", "punkte": 0.65, "rang": 95, "beste": True, "watchlist": False}}}}
LERNSTAND = {
    "monat": "2026-10", "training": 412345, "anteil": 0.3, "warnungen": ["Keine Kurse für 1 Aktien: XYZ."],
    "guete": {"auc": 0.541, "n": 30000, "fuenftel": []},
    "gelernt": [{"name": "Momentum 6 Monate", "wichtigkeit": 0.01, "richtung": 0.4},
                {"name": "Angst-Index VIX", "wichtigkeit": 0.005, "richtung": -0.3},
                {"name": "RSI (2 Tage)", "wichtigkeit": -0.001, "richtung": 0.0}],
    "fehler": {"n_alle": 30000, "n_ausgewaehlt": 9000, "verlust_alle": 0.48, "verlust_ausgewaehlt": 0.44,
               "tabelle": [{"grund": "markt", "text": "Absturz des Gesamtmarkts", "alle": 0.12, "ausgewaehlt": 0.08},
                           {"grund": "zahlen", "text": "Quartalszahlen", "alle": 0.1, "ausgewaehlt": 0.1}]},
    "bot_trades": [
        {"ticker": "LLY", "kauf_tag": "2026-10-21", "verkauf_tag": "2026-10-28", "R": 0.47, "grund": "Ziel",
         "fehler": [], "fehler_text": [], "fertig": False},
        {"ticker": "INTU", "kauf_tag": "2026-10-21", "verkauf_tag": "2026-10-27", "R": -1.02, "grund": "Stop",
         "fehler": ["markt", "stop_eng"], "fehler_text": ["Absturz des Gesamtmarkts", "Stop zu eng"], "fertig": True}]}
ZEILEN = [{"Ticker": "NOW", "Signal": sw.KAUFEN, "_strategie": "ruecksetzer_long", "_stand": pd.Timestamp("2026-10-28")},
          {"Ticker": "SOFI", "Signal": sw.WARTEN, "_strategie": "squeeze_long", "_stand": pd.Timestamp("2026-10-28")},
          {"Ticker": "AAPL", "Signal": "BEOBACHTEN", "_stand": pd.Timestamp("2026-10-28")}]


def test_bericht_zeigt_punktzahl_je_signal():
    vorne, tabelle, hinten = sw.lernmodell_teil(PUNKTE, LERNSTAND, ZEILEN, "lernen", kauft=True)
    assert "Gekauft werden nur Signale mit ✅" in vorne[0]
    assert "Nur zur Anzeige" in sw.lernmodell_teil(PUNKTE, LERNSTAND, ZEILEN, "lernen")[0][0]
    assert list(tabelle["Ticker"]) == ["NOW", "SOFI"]  # nur Watchlist-Signale, beste Punktzahl zuerst
    assert tabelle.iloc[0]["Lernmodell"].startswith("✅") and tabelle.iloc[1]["Lernmodell"] == "–"
    assert "(bewertet: " in tabelle.iloc[1]["Strategie"]  # der Bot handelt dort eine andere Strategie
    text = " ".join(hinten)
    assert "Momentum 6 Monate (je höher, desto besser)" in text and "RSI (2 Tage)" not in text
    assert "Absturz des Gesamtmarkts 12 %" in text
    assert "INTU -1,0 R: Absturz des Gesamtmarkts, Stop zu eng" in text.replace("−", "-")
    assert "XYZ" in text and "lernen/LERNEN.md" in text


def test_bericht_wenn_punktzahlen_fehlen_oder_alt_sind():
    vorne, tabelle, _ = sw.lernmodell_teil(None, None, ZEILEN, "lernen")
    assert tabelle is None and "Noch kein Ergebnis des Lern-Laufs" in vorne[0]
    alt = dict(PUNKTE, tag="2026-10-27", tage={"2026-10-27": {}})
    vorne, tabelle, _ = sw.lernmodell_teil(alt, LERNSTAND, ZEILEN, "lernen")
    assert tabelle is None and any("noch keine Punktzahlen" in z for z in vorne)


def test_zeige_lernmodell_liest_die_dateien(tmp_path, capsys):
    (tmp_path / "punkte.json").write_text(json.dumps(PUNKTE), encoding="utf-8")
    (tmp_path / "lernstand.json").write_text(json.dumps(LERNSTAND), encoding="utf-8")
    einst = types.SimpleNamespace(lernmodell=str(tmp_path))
    vorher = len(sw.BERICHT)
    sw.zeige_lernmodell(einst, ZEILEN)
    teil = sw.BERICHT[vorher]
    del sw.BERICHT[vorher:]
    assert teil.startswith("## 🧠 LERNMODELL") and "NOW" in teil and "61 %" in teil
    assert einst.lern_stand["monat"] == "2026-10"
    assert "LERNMODELL" in capsys.readouterr().out


def test_lehren_seite_im_gehirn():
    text = "\n".join(sw.lernmodell_lehren(types.SimpleNamespace(lern_stand=LERNSTAND)))
    assert "## 🔎 Fehler-Analyse und Lernmodell" in text
    assert "INTU" in text and "Stop zu eng" in text and "LLY" not in text  # nur Verluste
    assert "Absturz des Gesamtmarkts: 12 % aller Signale · bei den besten 8 %" in text
    assert sw.lernmodell_lehren(types.SimpleNamespace()) == []


def _zeilen():
    return [{"Ticker": "NOW", "Signal": sw.KAUFEN, "_strategie": "ruecksetzer_long", "Stop": 1.0, "Stück": 3,
             "_stand": pd.Timestamp("2026-10-28")},
            {"Ticker": "SOFI", "Signal": sw.KAUFEN, "_strategie": "ausbruch_long", "Stop": 1.0, "Stück": 3,
             "_stand": pd.Timestamp("2026-10-28")},
            {"Ticker": "AAPL", "Signal": sw.KAUFEN, "_strategie": "macd_long", "Stop": 1.0, "Stück": 3,
             "_stand": pd.Timestamp("2026-10-28")}]


def _einst(ordner, *optionen):
    einst = hilfe.einstellungen("--lernmodell", str(ordner), *optionen)
    return einst


def test_nur_signale_mit_guter_punktzahl_werden_gekauft(tmp_path):
    (tmp_path / "punkte.json").write_text(json.dumps(dict(PUNKTE, sperre={"2026-09-01": ["AAPL"]})), encoding="utf-8")
    (tmp_path / "lernstand.json").write_text(json.dumps(LERNSTAND), encoding="utf-8")
    zeilen, einst = _zeilen(), _einst(tmp_path)
    sw.lernmodell_anwenden(einst, zeilen)
    now, sofi, aapl = zeilen
    assert now["Signal"] == sw.KAUFEN  # ✅
    assert sofi["Signal"] == sw.WARTEN and "Lernmodell: Punktzahl 44 %" in sofi["Strategie"] and "Stop" not in sofi
    assert aapl["Signal"] == sw.KAUFEN  # ohne Punktzahl: Regeln ohne Lernmodell
    assert einst.lern_sperre[pd.Timestamp("2026-10-28")] == {"SOFI"}
    assert einst.lern_sperre[pd.Timestamp("2026-09-01")] == {"AAPL"}  # auch für den Rückblick der letzten Monate
    # nur anzeigen: nichts gesperrt
    zeilen, einst = _zeilen(), _einst(tmp_path, "--lernmodell-nur-anzeigen")
    sw.lernmodell_anwenden(einst, zeilen)
    assert all(z["Signal"] == sw.KAUFEN for z in zeilen) and einst.lern_sperre == {}


def test_ohne_punktzahlen_von_heute_gelten_die_alten_regeln(tmp_path):
    alt = dict(PUNKTE, tag="2026-10-27", tage={"2026-10-27": {"NOW": dict(PUNKTE["tage"]["2026-10-28"]["SOFI"])}})
    (tmp_path / "punkte.json").write_text(json.dumps(alt), encoding="utf-8")
    zeilen, einst = _zeilen(), _einst(tmp_path)
    vorher = len(sw.BERICHT_HINWEISE)
    sw.lernmodell_anwenden(einst, zeilen)
    hinweise = sw.BERICHT_HINWEISE[vorher:]
    del sw.BERICHT_HINWEISE[vorher:]
    assert all(z["Signal"] == sw.KAUFEN for z in zeilen)
    assert any("fehlen die Punktzahlen" in h for h in hinweise)


def test_depot_kauft_gesperrte_signale_nicht():
    einst = hilfe.einstellungen()
    daten, alle_tage = hilfe.vorbereiten(einst)
    tagebuch = sw.strategie_tagebuch(daten, einst)
    pausen, _ = sw.lernverlauf(tagebuch, alle_tage, einst)
    ohne = sw.simuliere_depot(daten, pausen, einst, einst.lernen)
    erster = ohne["trades"][0]
    signal_tag = max(t for t in alle_tage if t < erster["kauf_tag"])
    einst.lern_sperre = {signal_tag: frozenset([erster["ticker"]])}
    mit = sw.simuliere_depot(daten, pausen, einst, einst.lernen)
    gekauft = {(x["ticker"], x["kauf_tag"]) for x in mit["trades"]}
    assert (erster["ticker"], erster["kauf_tag"]) not in gekauft
    einst.lern_sperre = {}
    assert len(sw.simuliere_depot(daten, pausen, einst, einst.lernen)["trades"]) == len(ohne["trades"])


def test_beste_punktzahl_wird_zuerst_gekauft():
    punkte = dict(PUNKTE, verlauf={"2026-09-01": {"AAPL": 0.52, "NOW": 0.61}})
    rang = sw.lern_rang_aus(punkte)
    assert rang[pd.Timestamp("2026-09-01")] == {"AAPL": 0.52, "NOW": 0.61}
    assert rang[pd.Timestamp("2026-10-28")]["SOFI"] == 0.44
    # im Depot: an einem Tag mit mehreren Signalen entscheidet die Punktzahl über die Reihenfolge
    einst = hilfe.einstellungen()
    daten, alle_tage = hilfe.vorbereiten(einst)
    tagebuch = sw.strategie_tagebuch(daten, einst)
    pausen, _ = sw.lernverlauf(tagebuch, alle_tage, einst)
    ohne = sw.simuliere_depot(daten, pausen, einst, einst.lernen)
    # allen Signalen eine Punktzahl geben, die die bisherige Reihenfolge umkehrt (Aktien hinten in der Liste zuerst)
    einst.lern_rang = {t: {a: 0.5 + 0.01 * n for n, a in enumerate(hilfe.AKTIEN)} for t in alle_tage}
    mit = sw.simuliere_depot(daten, pausen, einst, einst.lernen)
    assert [x["ticker"] for x in mit["trades"]] != [x["ticker"] for x in ohne["trades"]]
