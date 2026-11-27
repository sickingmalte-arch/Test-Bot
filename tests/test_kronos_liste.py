"""Kronos-Versuch: Fächer für jede Aktie der Watchlist (Wunsch des Besitzers vom 27.11.2026). Ohne Kronos-Modell und
ohne Netz – die 50 Zukünfte sind hier ausgedacht, geprüft wird nur, was gespeichert und an die Webseite gegeben wird."""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "forschung"))
import kronos_versuch as K  # noqa: E402

TAG = "2026-11-25"


def kerzen(n, start=100.0, seed=1, ab=None):
    rng = np.random.default_rng(seed)
    c = start * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    idx = pd.bdate_range(end=TAG, periods=n) if ab is None else pd.bdate_range(ab, periods=n)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1e6}, index=idx)


def test_faecher_fuer_jede_aktie(monkeypatch):
    zuk = [kerzen(K.TAGE, seed=s, ab="2026-11-26") for s in range(K.PFADE)]
    monkeypatch.setattr(K, "kronos_zukuenfte", lambda *a, **k: zuk)
    daten = {"daten_bis": TAG, "signale": [{"ticker": "AAA"}, {"ticker": "BBB"}]}
    liste = [{"signal_tag": "2026-11-24", "ticker": "AAA", "stop_abstand": -4.0, "ziel_abstand": 4.0,
              "p_ziel_zufall": 0.5, "letzte_20_tage": {"tagesspanne_prozent": 2.0, "vola_prozent": 1.5},
              "kronos": {n: {"p_ziel": 0.5, "p_stop": 0.4, "tagesspanne_prozent": 2.0, "vola_prozent": 1.0,
                             "mitte_20": 0.1, "faecher": {"q10": [0.0], "mitte": [0.0], "q90": [0.0]}}
                         for n in K.LISTE_VARIANTEN}}]
    n = K.liste_vorhersage(daten, liste, predictor_fn=lambda modell: None, kurse_fn=lambda t, s, e: kerzen(300))
    assert n == 2
    neu = [e for e in liste if e["signal_tag"] == TAG]
    for e in neu:
        for name in K.LISTE_VARIANTEN:
            f = e["kronos"][name]["faecher"]
            assert set(f) == {"q10", "mitte", "q90"} and all(len(f[k]) == K.TAGE for k in f)
            assert f["q10"][-1] <= f["mitte"][-1] <= f["q90"][-1]
    K.nur_neueste_faecher(liste)  # im Log bleibt der Fächer nur beim neuesten Tag
    assert all("faecher" not in v for v in liste[0]["kronos"].values())
    assert all("faecher" in v for e in neu for v in e["kronos"].values())
    heute = K.webseite([], liste)["liste"]["heute"]
    assert [e["ticker"] for e in heute] == ["AAA", "BBB"] and all(e["signal_tag"] == TAG for e in heute)
    v = heute[0]["kronos"][K.LISTE_VARIANTEN[0]]
    assert v["nach_20_tagen_prozent"]["mitte"] == neu[0]["kronos"][K.LISTE_VARIANTEN[0]]["mitte_20"]
    assert len(v["faecher"]["mitte"]) == K.TAGE


def test_ohne_faecher_nichts_fuer_die_seite():
    alt = [{"signal_tag": TAG, "ticker": "AAA", "kronos": {"small-64": {"p_ziel": 0.5}}}]
    assert K.liste_heute(alt) == [] and K.liste_heute([]) == []
