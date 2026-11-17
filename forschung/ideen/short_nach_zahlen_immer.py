"""Wunsch des Nutzers vom 17.11.2026 („Short reinbringen, damit er profitabel wird“): Short nach schlechten
Quartalszahlen, Variante 2 – in jeder Marktlage."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import short_hilfe as S  # noqa: E402

NAME = "Short nach schlechten Zahlen 2: in jeder Marktlage"
QUELLE = S.QUELLE_DRIFT
BESCHREIBUNG = ("Neue Short-Strategie: Fällt eine Aktie am Tag, an dem ihre Quartalszahlen wirken, um mindestens 2 ATR "
                "unter den Vortagesschluss, setzt der Bot am nächsten Tag zur Eröffnung auf weiter fallende Kurse (Stop "
                "+3 ATR, Ziel −3 ATR, Zeitstopp wie immer) – auch im Aufwärtsmarkt, weil die Drift nach schlechten "
                "Zahlen laut Forschung nicht von der Marktlage abhängt. Höchstens 2 Shorts gleichzeitig, alle übrigen "
                "Regeln wie im Bot; die 8 alten Short-Strategien bleiben aus. Gegenprobe: je Aktie gleich viele Shorts "
                "an zufälligen erlaubten Tagen.")
VERMUTUNG = ("Nach einem Kursrutsch auf schlechte Zahlen fällt die Aktie weiter, auch im Aufwärtsmarkt; die Shorts "
             "bringen den Bot in allen drei Zeiträumen weiter als heute und weiter als zufällige Shorts.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: (1) nur außerhalb des Aufwärtsmarkts (short_nach_zahlen_abwaerts.py), "
             "(2) immer (diese Datei); Rutsch-Grenze 2 ATR in beiden fest.")


def anpassen(sw):
    S.short_strategie(sw, "zahlen_absturz_short", "Zahlen-Absturz", S.zahlen_absturz, marktfilter=False)


def gegenprobe(sw, seed):
    S.short_strategie(sw, "zahlen_absturz_short", "Zahlen-Absturz", S.zahlen_absturz, marktfilter=False,
                      zufall_seed=seed)
