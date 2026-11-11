"""Prüfung „day-trader-skill“ (Wunsch vom 11.11.2026), zweiter Teil von trader-timemachine („the history“): dieselbe
Regel auf den echten früheren Tagen derselben Aktie. Kaufen nur, wenn diese Geschichte nicht schlecht war."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skill_hilfe as H  # noqa: E402

NAME = "Day-Trader-Skill: Geschichte – nicht kaufen, wenn dieselbe Regel bei dieser Aktie bisher verlor"
QUELLE = H.QUELLE
BESCHREIBUNG = ("Wie „die Geschichte“ der Zeitmaschine: Für jedes Signal zählt der Bot die früheren Signale derselben "
                "Strategie bei derselben Aktie, die am Signaltag schon zu Ende waren (Kauf zur nächsten Eröffnung, raus am "
                "Stop, am Ziel oder nach 20 Tagen, nach Spread). Hatte diese Regel dort schon mindestens 5 Trades und im "
                "Schnitt höchstens 0 R, wird nicht gekauft. Gegenprobe: je Aktie gleich viele Signale weglassen, aber "
                "zufällig.")
VERMUTUNG = ("Eine Regel, die bei einer Aktie bisher verlor, verliert dort eher weiter; der Filter macht den Bot in allen "
             "drei Zeiträumen besser als heute und als zufälliges Weglassen.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = ("1 (mindestens 5 fertige Trades, Grenze 0 R), vor dem Rechnen festgelegt; Teil von 9 Skill-Ideen auf dem "
             "Prüfstand.")


def anpassen(sw):
    H.filtern(sw, H.geschichte_schlecht)


def gegenprobe(sw, seed):
    H.filtern(sw, H.geschichte_schlecht, zufall_seed=seed)
