"""Prüfung „day-trader-skill“ (Wunsch vom 11.11.2026), Risiko-Regel aus trader-risk: min_reward_risk = 1.0 –
kein Kauf, wenn der mögliche Gewinn bis zum Ziel kleiner ist als der mögliche Verlust bis zum Stop."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skill_hilfe as H  # noqa: E402

NAME = "Day-Trader-Skill: nur Käufe mit Chance-Risiko (CRV) mindestens 1,0"
QUELLE = H.QUELLE
BESCHREIBUNG = ("Wie die Risiko-Prüfung des Skills: Signale mit einem CRV unter 1,0 (Ziel näher als der Stop) kauft der "
                "Bot nicht. Beim Bot betrifft das die Gegenbewegungs-Strategien (Stop 2,5 ATR, Ziel 2 ATR = CRV 0,8: "
                "RSI-2-Rücksetzer und Gegenbewegung). Gegenprobe: je Aktie gleich viele Signale weglassen, aber zufällig "
                "aus allen Strategien.")
VERMUTUNG = "Ohne Signale mit CRV unter 1 ist der Bot in allen drei Zeiträumen besser und schlägt zufälliges Weglassen."
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = "1 (Grenze 1,0 wie im Skill), vor dem Rechnen festgelegt; Teil von 9 Skill-Ideen auf dem Prüfstand."


def _zu_klein(t, d, key, feuert, stop, ziel):
    return H.crv(np.asarray(d["C"], dtype=float), stop, ziel) < 1.0 - 1e-9


def anpassen(sw):
    H.filtern(sw, _zu_klein)


def gegenprobe(sw, seed):
    H.filtern(sw, _zu_klein, zufall_seed=seed)
