"""Nacht-Forschung 05.11.2026: Branchen-ETFs mit dem stärksten Momentum."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rotation as ROT  # noqa: E402

NAME = "Branchen-Rotation: die 3 stärksten Branchen-ETFs der letzten 12 Monate, monatlich"
QUELLE = "Moskowitz & Grinblatt (1999) „Do Industries Explain Momentum?“; Faber (2010) Sektor-Rotation"
BESCHREIBUNG = ("Einmal im Monat kauft das Depot die 3 Branchen-ETFs des S&P 500 (Technik, Banken, Gesundheit, Energie, Konsum, Industrie, Rohstoffe, Versorger, Immobilien, Kommunikation) mit dem größten Anstieg über 12 Monate (ohne den letzten Monat). Liegt der S&P 500 (SPY) am Monatsende unter seiner 200-Tage-Linie, hält das Depot nur Geld. Ohne Verzerrung durch verschwundene Firmen. Gegenprobe: 20-mal zufällige 3 Branchen.")

VERMUTUNG = ("Diese Monats-Regel bringt in allen drei Zeiträumen mehr Rendite pro Rückgang als der Swing-Bot und ist besser als zufällig gewählte Branchen.")
WIDERLEGT_WENN = ("In einem der drei Zeiträume weniger Rendite pro Rückgang als der Swing-Bot, tiefer gefallen als der "
                  "Nasdaq-100 beim Halten, oder mehr als 1 von 20 Zufallsdepots gleich gut oder besser.")
VARIANTEN = ("7, alle vor dem Rechnen am 05.11.2026 festgelegt: Momentum 12 Monate Top 10, Momentum 6 Monate Top 10, "
             "Momentum 12 Monate Top 20, Branchen-ETFs Top 3, Nasdaq-100 nur über der 200-Tage-Linie, halb Swing-Bot "
             "halb Momentum, geringe Schwankung Top 20. Besteht eine von sieben, bleibt Vorsicht nötig (Glückstreffer).")


def depot(cache, von, bis):
    return ROT.depot(cache, von, bis, "sektor", 3, lang=252)


def zufall(cache, von, bis, seed):
    return ROT.depot(cache, von, bis, "sektor", 3, lang=252, seed=seed)
