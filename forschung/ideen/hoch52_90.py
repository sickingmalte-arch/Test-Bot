"""Forschung 27.11.2026 (Forschungs-Bot, Freitags-Idee, nachgeholt am 28.11.): 52-Wochen-Hoch, Variante 1 – Kauf-
Signale nur, wenn der Schlusskurs mindestens 90 % des 52-Wochen-Hochs erreicht. Ablauf: forschung/hoch52_hilfe.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hoch52_hilfe as W  # noqa: E402
import skill_hilfe as H  # noqa: E402

NAME = "52-Wochen-Hoch 1: nur kaufen ab 90 % des 52-Wochen-Hochs"
QUELLE = W.QUELLE
BESCHREIBUNG = ("Wie der Bot, aber ein Kauf-Signal fällt weg, wenn der Schlusskurs am Signaltag unter 90 % des höchsten "
                "Kurses der letzten 52 Wochen liegt. Stop, Ziel, Größe und alle übrigen Regeln bleiben gleich. "
                "Gegenprobe: je Aktie gleich viele Signale weglassen, aber zufällig.")
VERMUTUNG = ("Kauf-Signale nahe am 52-Wochen-Hoch laufen besser (Anker-Effekt); ohne die Signale weit darunter ist der "
             "Bot in allen drei Zeiträumen besser als heute und als zufälliges Weglassen gleich vieler Signale.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = "2, vor dem Rechnen festgelegt: (1) mindestens 90 % des 52-Wochen-Hochs (diese Datei), (2) mindestens 95 % (hoch52_95.py)."


def anpassen(sw):
    H.filtern(sw, W.weg_unter(0.90))


def gegenprobe(sw, seed):
    H.filtern(sw, W.weg_unter(0.90), zufall_seed=seed)
