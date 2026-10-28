"""Laden und Speichern des Papier-Depots: Die echte Datei im Repository und eine alte Fassung vom ersten Tag
(21.10.2026) müssen lesbar bleiben – sonst würde der Vorwärtstest abbrechen."""
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hilfe  # noqa: E402

sw = hilfe.bot()
ALT = hilfe.DATEN / "papier_depot_2026-10-21.json"
ECHT = hilfe.WURZEL / "papier" / "papier_depot.json"


def test_echtes_papier_depot_ist_lesbar():
    stand, fehler = sw.lade_papier(str(ECHT), False)
    assert fehler is None and stand is not None
    assert stand["startkapital"] > 0 and stand["verlauf"]
    for p in stand["positionen"]:
        assert set(sw.POSITION_FELDER) <= set(p), p
    for t in stand["trades"]:
        assert set(sw.TRADE_FELDER) <= set(t), t


def test_alte_datei_vom_ersten_tag_ist_lesbar(tmp_path):
    datei = tmp_path / "papier_depot.json"
    shutil.copyfile(ALT, datei)
    stand, fehler = sw.lade_papier(str(datei), False)
    assert fehler is None and stand["bis"] == "2026-10-20"
    ok, verfallen, nach = sw.ausfuehrbare_auftraege(stand)
    assert len(ok) + sum(len(v) for v in verfallen.values()) + len(nach) == len(stand["auftraege"])


def test_speichern_und_wieder_laden(tmp_path):
    stand, _ = sw.lade_papier(str(ECHT), False)
    datei = tmp_path / "papier" / "papier_depot.json"
    sw.speichere_papier(str(datei), stand)
    sw.speichere_papier(str(datei), stand)  # zweites Mal: der vorige Stand bleibt als .bak
    wieder, fehler = sw.lade_papier(str(datei), False)
    assert fehler is None and wieder == stand
    assert (tmp_path / "papier" / "papier_depot.json.bak").exists()


def test_kaputte_oder_fremde_datei_bleibt_unangetastet(tmp_path):
    datei = tmp_path / "papier_depot.json"
    datei.write_text(json.dumps({"version": 99}), encoding="utf-8")
    stand, fehler = sw.lade_papier(str(datei), False)
    assert stand is None and "nicht lesbar" in fehler
    assert json.loads(datei.read_text(encoding="utf-8")) == {"version": 99}
    assert sw.lade_papier(str(tmp_path / "gibt_es_nicht.json"), False) == (None, None)


def test_grund_fuer_nicht_gekaufte_auftraege():
    """Live-Vorschau: Warum ein Auftrag zur Eröffnung nicht gekauft wurde (Anzeige auf der Seite)."""
    import numpy as np
    import pandas as pd

    idx = pd.to_datetime(["2026-10-27", "2026-10-28"])

    def kurse(eroeffnung):
        return {"idx": idx, "n_fertig": 2, "O": np.array([100.0, eroeffnung]), "FX": np.array([1.0, 1.0])}

    def auftrag(t):
        return {"ticker": t, "richtung": 1, "stop": 90.0, "limit": 105.0, "strategie": "test"}

    daten = {"HOCH": kurse(110.0), "TIEF": kurse(85.0), "PASST": kurse(100.0)}
    leer = {"bis": "2026-10-27", "positionen": [], "auftraege": [auftrag(t) for t in daten]}
    gruende = sw.nicht_gekauft_gruende(leer, daten, list(daten))
    assert "über dem Limit von 105,00 €" in gruende["HOCH"]
    assert "hinter dem Stop von 90,00 €" in gruende["TIEF"]
    assert gruende["PASST"] == "zu wenig freies Geld oder Risiko-Spielraum"

    voll = dict(leer, positionen=[{"ticker": f"P{i}", "richtung": 1} for i in range(sw.MAX_POSITIONEN)],
                auftraege=[auftrag("PASST")])
    assert sw.nicht_gekauft_gruende(voll, daten, ["PASST"]) == {
        "PASST": f"zur Eröffnung Depot voll, {sw.MAX_POSITIONEN}/{sw.MAX_POSITIONEN} Positionen"}
