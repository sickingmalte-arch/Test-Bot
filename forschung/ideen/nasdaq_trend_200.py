"""Nacht-Forschung 05.11.2026: Nasdaq-100 halten, aber nur über der 200-Tage-Linie."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rotation as ROT  # noqa: E402

NAME = "Trendfolge: Nasdaq-100 (QQQ) halten, nur wenn er am Monatsende über seiner 200-Tage-Linie liegt"
QUELLE = "Faber (2007) „A Quantitative Approach to Tactical Asset Allocation“"
BESCHREIBUNG = ("Am Monatsende: Liegt der Nasdaq-100 über seiner 200-Tage-Linie, hält das Depot den ganzen Betrag im QQQ, sonst nur Geld. Keine Einzelaktien, keine Verzerrung durch verschwundene Firmen. Ohne Gegenprobe (es wird nichts ausgewählt), dafür der Vergleich mit dem Nasdaq-100 beim einfachen Halten.")

VERMUTUNG = ("Diese Monats-Regel bringt in allen drei Zeiträumen mehr Rendite pro Rückgang als der Swing-Bot.")
WIDERLEGT_WENN = ("In einem der drei Zeiträume weniger Rendite pro Rückgang als der Swing-Bot, tiefer gefallen als der "
                  "Nasdaq-100 beim Halten.")
VARIANTEN = ("7, alle vor dem Rechnen am 05.11.2026 festgelegt: Momentum 12 Monate Top 10, Momentum 6 Monate Top 10, "
             "Momentum 12 Monate Top 20, Branchen-ETFs Top 3, Nasdaq-100 nur über der 200-Tage-Linie, halb Swing-Bot "
             "halb Momentum, geringe Schwankung Top 20. Besteht eine von sieben, bleibt Vorsicht nötig (Glückstreffer).")


def depot(cache, von, bis):
    return ROT.depot(cache, von, bis, "fest", 1, filter_ticker="QQQ", feste=["QQQ"])
