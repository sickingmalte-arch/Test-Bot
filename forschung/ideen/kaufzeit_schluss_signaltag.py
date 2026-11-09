"""Kaufzeit 1 (Wunsch des Nutzers für Fr 06.11.2026): Kauf zum Schlusskurs am Signaltag statt zur Eröffnung danach."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kaufzeit as K  # noqa: E402

NAME = "Kaufzeit 1: Kauf zum Schlusskurs am Signaltag (statt zur Eröffnung am nächsten Tag)"
QUELLE = "Wunsch des Nutzers (Chat vom 05.11.2026): sollten wir die Kaufzeit ändern?"
BESCHREIBUNG = ("Der Bot würde kurz vor Börsenschluss (etwa 21:45 Uhr) entscheiden und zum Schlusskurs des Signaltags kaufen "
                "(mit Spread), statt am nächsten Tag zur Eröffnung bis zum Limit. Stop und Ziel bleiben gleich, ab dem "
                "nächsten Tag gelten sie wie bisher (auch Kurslücken über den Stop). In echt kennt man den Schlusskurs erst "
                "kurz vorher – der Test ist deshalb etwas zu günstig.")
VERMUTUNG = "Kauf zum Schluss des Signaltags bringt in allen drei Zeiträumen mehr Rendite als Kauf am nächsten Morgen."
WIDERLEGT_WENN = "In einem Zeitraum weniger Rendite oder deutlich mehr Rückgang als der jetzige Bot."
VARIANTEN = "3 Kaufzeiten (Schluss Signaltag, Schluss nächster Tag, Eröffnung ohne Lücke nach oben), vorher festgelegt."


def anpassen(sw):
    K.kaufzeit(sw, lambda d, j: d["C"][j - 1], start_off=-1, versatz=1)
