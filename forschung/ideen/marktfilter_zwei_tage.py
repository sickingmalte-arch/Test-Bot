"""Wunsch des Nutzers vom 24.11.2026 („Marktfilter feiner“): Variante 2 – Ampel schaltet erst nach 2 Tagen um. Ablauf: forschung/ampel_hilfe.py."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ampel_hilfe as AM  # noqa: E402

NAME = "Marktfilter 2: Ampel schaltet erst nach 2 Tagen um"
QUELLE = AM.QUELLE
BESCHREIBUNG = ("Die Ampel (Nasdaq-100 und 200-Tage-Linie wie heute) schaltet erst um, wenn der Nasdaq-100 an 2 Tagen in Folge auf der anderen Seite der Linie schließt – in beide Richtungen. Alle übrigen Regeln bleiben gleich. Gegenprobe: dieselbe Zahl roter Tage in gleich langen "
                "Blöcken an zufälligen Stellen.")
VERMUTUNG = "Ein einzelner Schlusskurs knapp über oder unter der Linie ist oft Rauschen; erst nach 2 Tagen umzuschalten spart unnötige Pausen, und der Bot ist in allen drei Zeiträumen besser als heute und als zufällige Kaufpausen gleicher Länge."
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = "2, vor dem Rechnen festgelegt: (1) S&P 500 als Ampel (marktfilter_spy.py), (2) Nasdaq-100 mit 2 Tagen Bestätigung (diese Datei)."


def pruefen(P, a, watch, sektor_von):
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG)
    return AM.pruefen(P, a, watch, sektor_von, idee, "zwei_tage")
