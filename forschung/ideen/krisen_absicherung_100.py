"""Wunsch des Nutzers vom 17.11.2026 („Short reinbringen, damit er profitabel wird“): Absicherung nur in Krisen,
Variante 2 – Nasdaq-100-Short über 100 % des Depotwerts."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import absicherung_hilfe as A  # noqa: E402

NAME = "Krisen-Absicherung 2: Nasdaq-100-Short über 100 % nur bei VIX über 30 und Nasdaq unter der 200-Tage-Linie"
QUELLE = A.QUELLE
BESCHREIBUNG = ("Der Bot handelt ganz normal. Dazu kommt ein Nasdaq-100-Short (QQQ) über 100 % des Depotwerts – aber "
                "nur an Tagen, an denen am Abend vorher der Angst-Index VIX über 30 schloss und der Nasdaq-100 unter "
                "seiner 200-Tage-Linie lag, also in echten Krisen. 0,1 % Spread bei Ein- und Ausstieg, 0,5 % "
                "Leihgebühr pro Jahr. Gegenprobe: gleich viele Short-Tage in gleich langen Blöcken an zufälligen Stellen.")
VERMUTUNG = ("In Krisen fallen die Kurse weiter; der Short fängt die Verluste ab und bringt in allen drei Zeiträumen "
             "mehr Rendite bei höchstens 1 Punkt mehr Rückgang als der Bot allein – und mehr als derselbe Short an "
             "zufälligen Tagen.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: Short über 50 % (krisen_absicherung_50.py) und über 100 % des Depotwerts "
             "(diese Datei); Grenzen VIX 30 und 200-Tage-Linie fest.")


def pruefen(P, a, watch, sektor_von):
    return A.pruefen(P, a, watch, sektor_von, types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG), 1.0)
