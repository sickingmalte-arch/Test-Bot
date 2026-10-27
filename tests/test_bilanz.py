"""Ehrliche Bilanz des Übungsdepots (nur Anzeige): Trefferquote, Ø R und Gewinnfaktor richtig gerechnet, und die
Bilanz klappt auch ohne abgeschlossene Trades und ohne Nasdaq-100-Kurse."""
import pathlib
import shutil
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hilfe  # noqa: E402

sw = hilfe.bot()


def trade(gewinn, risiko=100.0):
    return {"erloes": 1000.0 + gewinn, "kosten": 1000.0, "risiko_eur": risiko}


def test_trade_bilanz_rechnet_richtig():
    b = sw.trade_bilanz([trade(150), trade(-100), trade(50), trade(-50)])
    assert b["n"] == 4 and b["treffer"] == 2 and b["quote"] == pytest.approx(50)
    assert b["schnitt_r"] == pytest.approx((1.5 - 1 + 0.5 - 0.5) / 4)
    assert b["gewinnfaktor"] == pytest.approx(200 / 150)
    assert sw.trade_bilanz([]) is None
    assert sw.trade_bilanz([trade(80)])["gewinnfaktor"] is None  # noch kein Verlust: kein Gewinnfaktor


def test_bilanz_ohne_trades_und_ohne_markt(tmp_path):
    datei = tmp_path / "papier_depot.json"
    shutil.copyfile(hilfe.DATEN / "papier_depot_2026-10-21.json", datei)
    stand, _ = sw.lade_papier(str(datei), False)
    text = "\n".join(sw.ehrliche_bilanz(stand, None, "€"))
    assert "noch keine" in text and "kein Vergleich möglich" in text and "Zufall" in text


def test_bilanz_mit_trades_und_markt(tmp_path):
    datei = tmp_path / "papier_depot.json"
    shutil.copyfile(hilfe.DATEN / "papier_depot_2026-10-21.json", datei)
    stand, _ = sw.lade_papier(str(datei), False)
    stand = dict(stand, trades=[trade(150), trade(-100)], depotwert=stand["startkapital"] * 1.02)
    markt = pd.Series([stand["startkapital"], stand["startkapital"] * 1.01])
    zeilen = sw.ehrliche_bilanz(stand, markt, "€")
    text = "\n".join(zeilen)
    assert "+2,0 %" in text and "+1,0 %" in text and "liegt vorn" in text
    assert "Trefferquote 50 %" in text and "Gewinnfaktor 1,5" in text and "Spielraum des Zufalls" in text
