"""Prüfung „day-trader-skill“ (Wunsch vom 11.11.2026), trader-timemachine als Filter: vor jedem Kauf die nächsten
20 Handelstage 1.000-mal aus den eigenen letzten 60 Tageskerzen der Aktie nachspielen; kaufen nur, wenn das Urteil
mindestens „neigt zum Ziel“ lautet (wie im Skill: Ziel zuerst mindestens 5 Punkte über dem Ausgleich 1 / (1 + R))."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skill_hilfe as H  # noqa: E402

NAME = "Day-Trader-Skill: Zeitmaschine – nur kaufen, wenn 1.000 Wiederholungen zum Ziel neigen"
QUELLE = H.QUELLE
BESCHREIBUNG = ("Die Zeitmaschine des Skills mit Tageskerzen statt 5-Minuten-Kerzen: Jede der letzten 60 Kerzen wird zu "
                "Verhältnissen zum Schluss davor (Eröffnung, Hoch, Tief, Schluss); 1.000 Wiederholungen ziehen für jeden "
                "der nächsten 20 Tage zufällig eine davon (Seed 19, Stop vor Ziel am selben Tag). Gekauft wird nur, wenn "
                "unter den Wiederholungen, die Stop oder Ziel erreichen, das Ziel mindestens 5 Punkte öfter zuerst kommt, "
                "als zum Ausgleich nötig wäre. Gegenprobe: je Aktie gleich viele Signale weglassen, aber zufällig.")
VERMUTUNG = ("Der Zeitmaschinen-Filter lässt die Signale weg, die eher am Stop enden, und macht den Bot in allen drei "
             "Zeiträumen besser als heute und als zufälliges Weglassen.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = ("1 (60 Kerzen, 1.000 Wiederholungen, 20 Tage, Grenze +5 Punkte wie das Skill-Urteil „leans toward the "
             "target“), vor dem Rechnen festgelegt; Teil von 9 Skill-Ideen auf dem Prüfstand.")


def _nicht_zum_ziel(t, d, key, feuert, stop, ziel):
    c = np.asarray(d["C"], dtype=float)
    weg = np.zeros(len(feuert), bool)
    for i in np.flatnonzero(feuert):
        p_ziel, p_stop = H.zeitmaschine(t, d, i, stop[i], ziel[i])
        weg[i] = not H.neigt_zum_ziel(p_ziel, p_stop, H.crv(c[i], stop[i], ziel[i]))
    return weg


def anpassen(sw):
    H.filtern(sw, _nicht_zum_ziel)


def gegenprobe(sw, seed):
    H.filtern(sw, _nicht_zum_ziel, zufall_seed=seed)
