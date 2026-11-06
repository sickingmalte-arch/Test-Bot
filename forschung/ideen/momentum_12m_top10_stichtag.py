"""Nacht-Forschung 05.11.2026, Nachtest mit Stichtag: Momentum-Rotation, 12 Monate, 10 Aktien."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rotation as ROT  # noqa: E402

NAME = "Momentum: die 10 stärksten Aktien der letzten 12 Monate, monatlich umschichten – mit Stichtag (nur Aktien, die damals schon im S&P 500 waren)"
QUELLE = "Jegadeesh & Titman (1993); Asness, Moskowitz & Pedersen (2013) „Value and Momentum Everywhere“"
BESCHREIBUNG = ("Nachtest gegen eine Verzerrung: Eine Aktie zählt nur, solange sie wirklich im S&P 500 war (Aufnahme- und Austrittsdatum aus der öffentlichen Liste github.com/fja05680/sp500). Umbenennungen wie FB → META zählen erst ab dem neuen Kürzel. Ohne Stichtag kaufte Momentum rückblickend Aktien, die erst wegen ihres Anstiegs in den Index kamen. Einmal im Monat kauft das Depot die 10 Aktien aus S&P 500 und Nasdaq-100 mit dem größten Anstieg über 12 Monate (der letzte Monat zählt nicht mit), zu gleichen Teilen. Liegt der S&P 500 (SPY) am Monatsende unter seiner 200-Tage-Linie, hält das Depot nur Geld. Gegenprobe: 20-mal zufällige 10 Aktien aus denselben Kandidaten, sonst gleich.")

VERMUTUNG = ("Diese Monats-Regel bringt in allen drei Zeiträumen mehr Rendite pro Rückgang als der Swing-Bot und ist besser als zufällig gewählte Aktien aus derselben Liste.")
WIDERLEGT_WENN = ("In einem der drei Zeiträume weniger Rendite pro Rückgang als der Swing-Bot, tiefer gefallen als der "
                  "Nasdaq-100 beim Halten, oder mehr als 1 von 20 Zufallsdepots gleich gut oder besser.")
VARIANTEN = ("Bereinigung der Varianten 1, 2, 3 und 6, keine neue Idee. Ursprünglich 7, alle vor dem Rechnen am 05.11.2026 festgelegt: Momentum 12 Monate Top 10, Momentum 6 Monate Top 10, "
             "Momentum 12 Monate Top 20, Branchen-ETFs Top 3, Nasdaq-100 nur über der 200-Tage-Linie, halb Swing-Bot "
             "halb Momentum, geringe Schwankung Top 20. Besteht eine von sieben, bleibt Vorsicht nötig (Glückstreffer).")


def depot(cache, von, bis):
    return ROT.depot(cache, von, bis, "momentum", 10, lang=252, stichtag=True)


def zufall(cache, von, bis, seed):
    return ROT.depot(cache, von, bis, "momentum", 10, lang=252, seed=seed, stichtag=True)

# Stichtag aus der Liste fja05680/sp500 (Wikipedia führt die Tabelle der Index-Änderungen nicht mehr auf der Seite).
