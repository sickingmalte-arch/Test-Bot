"""Forschung 13.11.2026 (Forschungs-Bot, Freitags-Idee): Monatswechsel-Effekt, Variante 1 – nur kurz vor dem
Monatswechsel kaufen."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kalender_hilfe as K  # noqa: E402
import skill_hilfe as H  # noqa: E402

NAME = "Monatswechsel 1: nur an den letzten 4 Handelstagen des Monats kaufen"
QUELLE = ("McConnell & Xu (2008), „Equity Returns at the Turn of the Month“, Financial Analysts Journal 64(2), 49–64; "
          "zuerst Lakonishok & Smidt (1988). Laut der Studie kam von 1926 bis 2005 fast die ganze Rendite des "
          "US-Aktienmarkts am letzten und an den ersten drei Handelstagen eines Monats zustande.")
BESCHREIBUNG = ("Wie der Bot, aber ein Kauf (zur Eröffnung am Tag nach dem Signal) ist nur an den letzten 4 Handelstagen "
                "des Monats erlaubt – so liegt der Monatswechsel (letzter und erste drei Handelstage) in der Haltezeit. "
                "Alle anderen Signale fallen weg. Stop, Ziel, Größe und alle übrigen Regeln bleiben gleich. Gegenprobe: je "
                "Aktie gleich viele Signale weglassen, aber zufällig.")
VERMUTUNG = ("Käufe kurz vor dem Monatswechsel laufen besser als Käufe in der Monatsmitte; der Bot ist damit in allen "
             "drei Zeiträumen besser als heute und als zufälliges Weglassen gleich vieler Signale.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: (1) nur an den letzten 4 Handelstagen kaufen (diese Datei), (2) zusätzlich "
             "an den ersten 3 Handelstagen des Monats (monatswechsel_rund.py).")


def fenster(nr, rest):
    return rest <= 3


def anpassen(sw):
    H.filtern(sw, K.nur_kauftage(fenster))


def gegenprobe(sw, seed):
    H.filtern(sw, K.nur_kauftage(fenster), zufall_seed=seed)
