"""Nacht-Forschung 05.11.2026, Nachtest mit Stichtag: halb Swing-Bot, halb Momentum 12 Monate Top 10."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rotation as ROT  # noqa: E402

NAME = "Kombi: halb Swing-Bot, halb Momentum (10 stärkste Aktien, 12 Monate) – mit Stichtag (nur Aktien, die damals schon im S&P 500 waren)"
QUELLE = "Jegadeesh & Titman (1993); Asness, Moskowitz & Pedersen (2013) „Value and Momentum Everywhere“"
BESCHREIBUNG = ("Nachtest gegen eine Verzerrung: Eine Aktie zählt nur, solange sie wirklich im S&P 500 war (Aufnahme- und Austrittsdatum aus der öffentlichen Liste github.com/fja05680/sp500). Umbenennungen wie FB → META zählen erst ab dem neuen Kürzel. Ohne Stichtag kaufte Momentum rückblickend Aktien, die erst wegen ihres Anstiegs in den Index kamen. Das Startgeld liegt zur Hälfte im jetzigen Swing-Bot und zur Hälfte im Momentum-Depot (10 Aktien, 12 Monate, monatlich, mit Marktfilter), ohne Umschichten zwischen beiden. Idee: zwei verschiedene Strategien schwanken nicht gleichzeitig, der Rückgang wird kleiner. Gegenprobe: halb Swing-Bot, halb zufällige 10 Aktien.")

VERMUTUNG = ("Diese Monats-Regel bringt in allen drei Zeiträumen mehr Rendite pro Rückgang als der Swing-Bot und ist besser als zufällig gewählte Aktien aus derselben Liste.")
WIDERLEGT_WENN = ("In einem der drei Zeiträume weniger Rendite pro Rückgang als der Swing-Bot, tiefer gefallen als der "
                  "Nasdaq-100 beim Halten, oder mehr als 1 von 20 Zufallsdepots gleich gut oder besser.")
VARIANTEN = ("Bereinigung der Varianten 1, 2, 3 und 6, keine neue Idee. Ursprünglich 7, alle vor dem Rechnen am 05.11.2026 festgelegt: Momentum 12 Monate Top 10, Momentum 6 Monate Top 10, "
             "Momentum 12 Monate Top 20, Branchen-ETFs Top 3, Nasdaq-100 nur über der 200-Tage-Linie, halb Swing-Bot "
             "halb Momentum, geringe Schwankung Top 20. Besteht eine von sieben, bleibt Vorsicht nötig (Glückstreffer).")


KOMBI_BOT = 0.5


def depot(cache, von, bis):
    return ROT.depot(cache, von, bis, "momentum", 10, lang=252, stichtag=True)


def zufall(cache, von, bis, seed):
    return ROT.depot(cache, von, bis, "momentum", 10, lang=252, seed=seed, stichtag=True)

# Stichtag aus der Liste fja05680/sp500 (Wikipedia führt die Tabelle der Index-Änderungen nicht mehr auf der Seite).
