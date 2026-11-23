"""Forschung 20.11.2026 (Forschungs-Bot, Freitags-Idee, nachgeholt am 23.11.): MAX-Effekt, Variante 2 – Kauf-Signal
weglassen nach einem Tagesplus von mindestens 3 ATR im letzten Monat."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import max_hilfe as M  # noqa: E402
import skill_hilfe as H  # noqa: E402

NAME = "MAX-Effekt 2: kein Kauf nach einem Tagesplus von 3 ATR oder mehr im letzten Monat"
QUELLE = M.QUELLE
BESCHREIBUNG = ("Wie der Bot, aber ein Kauf-Signal fällt weg, wenn die Aktie in den letzten 21 Börsentagen (bis zum "
                "Signaltag) an einem Tag um mindestens 3 ATR gestiegen ist – gemessen an ihrer eigenen üblichen "
                "Schwankung ein extremer Sprung. Stop, Ziel, Größe und alle übrigen Regeln bleiben gleich. Gegenprobe: "
                "je Aktie gleich viele Signale weglassen, aber zufällig.")
VERMUTUNG = ("Nach einem für die Aktie extremen Tagessprung läuft sie schlechter; ohne diese Käufe ist der Bot in allen "
             "drei Zeiträumen besser als heute und als zufälliges Weglassen gleich vieler Signale.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: (1) Grenze 10 % Tagesplus (max_effekt_10.py), (2) Grenze 3 ATR (diese "
             "Datei).")


def anpassen(sw):
    H.filtern(sw, M.weg_relativ(3.0))


def gegenprobe(sw, seed):
    H.filtern(sw, M.weg_relativ(3.0), zufall_seed=seed)
