"""Nacht-Forschung 05.11.2026: die 20 ruhigsten Aktien."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rotation as ROT  # noqa: E402

NAME = "Geringe Schwankung: die 20 ruhigsten Aktien des letzten Jahres, monatlich umschichten"
QUELLE = "Baker, Bradley & Wurgler (2011) „Benchmarks as Limits to Arbitrage: The Low-Volatility Anomaly“"
BESCHREIBUNG = ("Einmal im Monat kauft das Depot die 20 Aktien aus S&P 500 und Nasdaq-100, deren Tageskurse im letzten Jahr am wenigsten geschwankt haben, zu gleichen Teilen. Liegt der S&P 500 (SPY) am Monatsende unter seiner 200-Tage-Linie, hält das Depot nur Geld. Gegenprobe: 20-mal zufällige 20 Aktien aus denselben Kandidaten.")

VERMUTUNG = ("Diese Monats-Regel bringt in allen drei Zeiträumen mehr Rendite pro Rückgang als der Swing-Bot und ist besser als zufällig gewählte Aktien aus derselben Liste.")
WIDERLEGT_WENN = ("In einem der drei Zeiträume weniger Rendite pro Rückgang als der Swing-Bot, tiefer gefallen als der "
                  "Nasdaq-100 beim Halten, oder mehr als 1 von 20 Zufallsdepots gleich gut oder besser.")
VARIANTEN = ("7, alle vor dem Rechnen am 05.11.2026 festgelegt: Momentum 12 Monate Top 10, Momentum 6 Monate Top 10, "
             "Momentum 12 Monate Top 20, Branchen-ETFs Top 3, Nasdaq-100 nur über der 200-Tage-Linie, halb Swing-Bot "
             "halb Momentum, geringe Schwankung Top 20. Besteht eine von sieben, bleibt Vorsicht nötig (Glückstreffer).")


def depot(cache, von, bis):
    return ROT.depot(cache, von, bis, "schwankung", 20, lang=252)


def zufall(cache, von, bis, seed):
    return ROT.depot(cache, von, bis, "schwankung", 20, lang=252, seed=seed)
