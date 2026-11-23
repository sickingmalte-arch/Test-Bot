"""Forschung 20.11.2026 (Forschungs-Bot, Freitags-Idee, nachgeholt am 23.11.): MAX-Effekt, Variante 1 – Kauf-Signal
weglassen nach einem Tagesplus von mindestens 10 % im letzten Monat."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import max_hilfe as M  # noqa: E402
import skill_hilfe as H  # noqa: E402

NAME = "MAX-Effekt 1: kein Kauf nach einem Tagesplus von 10 % oder mehr im letzten Monat"
QUELLE = M.QUELLE
BESCHREIBUNG = ("Wie der Bot, aber ein Kauf-Signal fällt weg, wenn die Aktie in den letzten 21 Börsentagen (bis zum "
                "Signaltag) an einem Tag um mindestens 10 % gestiegen ist – so eine Aktie gilt als „Lotto-Aktie“. Stop, "
                "Ziel, Größe und alle übrigen Regeln bleiben gleich. Gegenprobe: je Aktie gleich viele Signale "
                "weglassen, aber zufällig.")
VERMUTUNG = ("Nach einem großen Tagessprung läuft eine Aktie schlechter; ohne diese Käufe ist der Bot in allen drei "
             "Zeiträumen besser als heute und als zufälliges Weglassen gleich vieler Signale.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: (1) Grenze 10 % Tagesplus (diese Datei), (2) Grenze 3 ATR, also an die "
             "Schwankung der Aktie angepasst (max_effekt_relativ.py).")


def anpassen(sw):
    H.filtern(sw, M.weg_absolut(0.10))


def gegenprobe(sw, seed):
    H.filtern(sw, M.weg_absolut(0.10), zufall_seed=seed)
