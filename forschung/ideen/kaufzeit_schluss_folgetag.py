"""Kaufzeit 2 (Wunsch des Nutzers für Fr 06.11.2026): Kauf zum Schlusskurs am nächsten Tag statt zur Eröffnung."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kaufzeit as K  # noqa: E402

NAME = "Kaufzeit 2: Kauf zum Schlusskurs am nächsten Tag (statt zur Eröffnung), Limit wie heute"
QUELLE = "Wunsch des Nutzers (Chat vom 05.11.2026): sollten wir die Kaufzeit ändern?"
BESCHREIBUNG = ("Der Auftrag vom Signaltag wird erst zum Schlusskurs des nächsten Tages ausgeführt (mit Spread), nur wenn "
                "dieser Schluss zwischen Stop und Limit liegt. Stop und Ziel gelten ab dem Tag danach. Idee: Die oft "
                "unruhige Eröffnung vermeiden.")
VERMUTUNG = "Kauf zum Schluss des nächsten Tages bringt in allen drei Zeiträumen mehr Rendite als Kauf zur Eröffnung."
WIDERLEGT_WENN = "In einem Zeitraum weniger Rendite oder deutlich mehr Rückgang als der jetzige Bot."
VARIANTEN = "3 Kaufzeiten (Schluss Signaltag, Schluss nächster Tag, Eröffnung ohne Lücke nach oben), vorher festgelegt."


def anpassen(sw):
    K.kaufzeit(sw, lambda d, j: d["C"][j], start_off=0, versatz=1)
