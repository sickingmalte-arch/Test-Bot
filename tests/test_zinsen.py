"""Zinsen aufs freie Geld im Bot-Papierdepot (Wunsch des Besitzers vom 24.11.2026): EZB-Einlagesatz minus 0,5 Punkte,
nie unter 0, auf das Bargeld vom Vorabend nach Kalendertagen. Ohne Netz: die Antwort der EZB ist nachgebaut."""
import io
import pathlib
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hilfe  # noqa: E402

sw = hilfe.bot()


def test_zins_satz_ohne_blick_in_die_zukunft():
    reihe = pd.Series([0.25, -0.5, 4.0, 2.0],
                      index=pd.DatetimeIndex(["2011-12-14", "2019-09-18", "2023-09-20", "2025-06-11"]))
    assert sw.zins_satz(reihe, "2011-12-13") == 0.0  # vor der ersten Angabe
    assert sw.zins_satz(reihe, "2012-01-02") == 0.0  # 0,25 − 0,5 wäre negativ
    assert sw.zins_satz(reihe, "2020-05-05") == 0.0  # negative Zinsen: nie unter 0
    assert sw.zins_satz(reihe, "2025-06-10") == pytest.approx(3.5)  # die Senkung am 11.06. zählt noch nicht
    assert sw.zins_satz(reihe, pd.Timestamp("2025-06-11", tz="America/New_York")) == pytest.approx(1.5)
    assert sw.zins_satz(None, "2025-06-11") == 0.0


def test_ezb_antwort_wird_gelesen_und_ohne_persoenliche_kennung_abgerufen(monkeypatch):
    csv = ("KEY,FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE,OBS_STATUS\n"
           "FM.D.U2.EUR.4F.KR.DFR.LEV,D,U2,2024-06-12,3.75,A\n"
           "FM.D.U2.EUR.4F.KR.DFR.LEV,D,U2,2023-09-20,4.0,A\n")
    gesehen = {}

    class Antwort(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def urlopen(anfrage, timeout=None):
        gesehen["url"], gesehen["kennung"] = anfrage.full_url, anfrage.get_header("User-agent")
        return Antwort(csv.encode())
    monkeypatch.setattr(sw.urllib.request, "urlopen", urlopen)
    reihe = sw.ezb_einlagesatz()
    assert list(reihe) == [4.0, 3.75] and reihe.index[0] == pd.Timestamp("2023-09-20")
    assert gesehen["url"].startswith("https://data-api.ecb.europa.eu/")
    assert gesehen["kennung"] == "Swing-Bot (GitHub Actions)"


def test_ersatz_wenn_die_ezb_fehlt(monkeypatch):
    monkeypatch.setattr(sw, "ezb_einlagesatz", lambda: None)
    reihe, hinweis = sw.zins_reihe({"zinsen": 1.0, "ezb_satz": 2.0})
    assert sw.zins_satz(reihe, "2026-11-25") == pytest.approx(1.5) and "zuletzt" in hinweis
    reihe, hinweis = sw.zins_reihe(None)
    assert reihe is None and "keine Zinsen" in hinweis
    assert sw.gespeicherter_zins({"ezb_satz": 2.0}) is None  # ohne Zinsen-Feld (Claude-Depot): keine Zinsen


def test_zinsen_im_papier_depot_nur_mit_zins():
    einst = hilfe.einstellungen()
    daten, alle_tage = hilfe.vorbereiten(einst)
    stand = sw.neues_papier(einst)
    stand["bis"] = hilfe.tag(alle_tage[-31])  # vor 30 Kurstagen, nur Bargeld
    reihe = pd.Series([2.5], index=pd.DatetimeIndex(["2000-01-01"]))  # 2,5 − 0,5 = 2 % im Jahr
    ohne, _, _ = sw.papier_fortschreiben(stand, daten, {}, einst, set())  # keine neuen Aufträge
    mit, erg, _ = sw.papier_fortschreiben(stand, daten, {}, einst, set(), zins=reihe)
    assert ohne["bargeld"] == stand["bargeld"] and "zinsen" not in ohne
    wert, vor = stand["bargeld"], pd.Timestamp(alle_tage[-31])
    for tag in erg["tage"]:  # Zinseszins Tag für Tag nach Kalendertagen
        wert *= 1 + 0.02 * (pd.Timestamp(tag) - vor).days / 365
        vor = pd.Timestamp(tag)
    assert mit["zinsen"] == pytest.approx(wert - stand["bargeld"]) and mit["zinsen"] > 0
    assert mit["bargeld"] == pytest.approx(stand["bargeld"] + mit["zinsen"])
    assert mit["depotwert"] == pytest.approx(mit["bargeld"]) and mit["ezb_satz"] == 2.5
    weiter, _, _ = sw.papier_fortschreiben(mit, daten, {}, einst, set(), zins=reihe)  # nichts Neues: nichts doppelt
    assert weiter["zinsen"] == pytest.approx(mit["zinsen"])
