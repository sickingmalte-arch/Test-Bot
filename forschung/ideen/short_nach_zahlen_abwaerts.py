"""Wunsch des Nutzers vom 17.11.2026 („Short reinbringen, damit er profitabel wird“): Short nach schlechten
Quartalszahlen, Variante 1 – nur wenn der Markt nicht im Aufwärtstrend ist (wie die alten Shorts)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import short_hilfe as S  # noqa: E402

NAME = "Short nach schlechten Zahlen 1: nur außerhalb des Aufwärtsmarkts"
QUELLE = S.QUELLE_DRIFT
BESCHREIBUNG = ("Neue Short-Strategie: Fällt eine Aktie am Tag, an dem ihre Quartalszahlen wirken, um mindestens 2 ATR "
                "unter den Vortagesschluss, setzt der Bot am nächsten Tag zur Eröffnung auf weiter fallende Kurse (Stop "
                "+3 ATR, Ziel −3 ATR, Zeitstopp wie immer). Wie bei den alten Shorts nur, wenn der Nasdaq-100 nicht im "
                "Aufwärtstrend ist; höchstens 2 Shorts gleichzeitig, alle übrigen Regeln wie im Bot. Die 8 alten "
                "Short-Strategien bleiben aus. Gegenprobe: je Aktie gleich viele Shorts an zufälligen erlaubten Tagen.")
VERMUTUNG = ("Nach einem Kursrutsch auf schlechte Zahlen fällt die Aktie weiter; die Shorts bringen den Bot in allen "
             "drei Zeiträumen weiter als heute und weiter als zufällige Shorts.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: (1) nur außerhalb des Aufwärtsmarkts (diese Datei), (2) immer "
             "(short_nach_zahlen_immer.py); Rutsch-Grenze 2 ATR in beiden fest.")


def anpassen(sw):
    S.short_strategie(sw, "zahlen_absturz_short", "Zahlen-Absturz", S.zahlen_absturz, marktfilter=True)


def gegenprobe(sw, seed):
    S.short_strategie(sw, "zahlen_absturz_short", "Zahlen-Absturz", S.zahlen_absturz, marktfilter=True, zufall_seed=seed)
