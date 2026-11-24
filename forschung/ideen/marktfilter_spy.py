"""Wunsch des Nutzers vom 24.11.2026 („Marktfilter feiner“): Variante 1 – S&P 500 statt Nasdaq-100 als Ampel. Ablauf: forschung/ampel_hilfe.py."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ampel_hilfe as AM  # noqa: E402

NAME = "Marktfilter 1: S&P 500 statt Nasdaq-100 als Ampel"
QUELLE = AM.QUELLE
BESCHREIBUNG = ("Der Bot kauft nur, wenn der S&P 500 (SPY) statt des Nasdaq-100 am Vortag über seiner 200-Tage-Linie schloss. Alle übrigen Regeln bleiben gleich. Gegenprobe: dieselbe Zahl roter Tage in gleich langen "
                "Blöcken an zufälligen Stellen.")
VERMUTUNG = "Der S&P 500 ist breiter und schwankt weniger als der Nasdaq-100; als Ampel gibt er weniger Fehlalarme, und der Bot ist in allen drei Zeiträumen besser als heute und als zufällige Kaufpausen gleicher Länge."
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = "2, vor dem Rechnen festgelegt: (1) S&P 500 als Ampel (diese Datei), (2) Nasdaq-100 mit 2 Tagen Bestätigung (marktfilter_zwei_tage.py)."


def pruefen(P, a, watch, sektor_von):
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG)
    return AM.pruefen(P, a, watch, sektor_von, idee, "spy")
