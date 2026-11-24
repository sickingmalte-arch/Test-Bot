"""Wunsch des Nutzers vom 24.11.2026 („Kaufen nach guten Zahlen“): Post-Earnings-Drift, Variante 2 – in jeder Marktlage."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import zahlen_hilfe as Z  # noqa: E402

NAME = "Kaufen nach guten Zahlen 2: in jeder Marktlage"
QUELLE = Z.QUELLE
BESCHREIBUNG = ("Neue Kauf-Strategie: Steigt eine Aktie am Tag, an dem ihre Quartalszahlen wirken, um mindestens 2 ATR "
                "über den Vortagesschluss, kauft der Bot zur nächsten Eröffnung (Stop −3 ATR, Ziel +3 ATR, Zeitstopp wie "
                "immer), in jeder Marktlage – die Drift nach guten Zahlen hängt laut Forschung nicht vom Markt ab. Alle übrigen Regeln wie im Bot. Gegenprobe: je Aktie gleich viele Käufe an zufälligen "
                "erlaubten Tagen.")
VERMUTUNG = ("Nach einem Kurssprung auf gute Zahlen steigt die Aktie weiter; die Käufe machen den Bot in allen drei "
             "Zeiträumen besser als heute und besser als zufällige Zusatz-Käufe.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = "2, vor dem Rechnen festgelegt: (1) nur außerhalb des Abwärtsmarkts (zahlen_kauf_markt.py), (2) in jeder Marktlage (diese Datei); Sprung-Grenze 2 ATR in beiden fest."


def anpassen(sw):
    Z.lang_strategie(sw, "zahlen_sprung_long", "Zahlen-Sprung", Z.zahlen_sprung, marktfilter=False)


def gegenprobe(sw, seed):
    Z.lang_strategie(sw, "zahlen_sprung_long", "Zahlen-Sprung", Z.zahlen_sprung, marktfilter=False, zufall_seed=seed)


def pruefen(P, a, watch, sektor_von):
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG)
    return Z.pruefen(P, a, watch, sektor_von, idee, "zahlen_sprung_long", anpassen, gegenprobe)
