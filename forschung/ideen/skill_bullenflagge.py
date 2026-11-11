"""Prüfung „day-trader-skill“ (Wunsch vom 11.11.2026), Scanner-Setup 'bullenflagge' aus trader-scanner/scan.py
(find_setups) als zusätzliche Kauf-Strategie des Swing-Bots. Gemeinsame Bausteine: forschung/skill_hilfe.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skill_hilfe as H  # noqa: E402

KEY = "skill_bullenflagge_long"
NAME = "Day-Trader-Skill: Bullen-Flagge als neue Kauf-Strategie"
QUELLE = H.QUELLE
BESCHREIBUNG = ("Kauf-Signal, wenn der Kurs in den 10 Tagen vor den letzten 5 um mehr als 10 % gestiegen ist und die letzten 5 Schlusskurse in einer Spanne von unter 5 % liegen. Regel wörtlich aus dem Scanner des Skills (nur Schlusskurse), dazu wie im Skill Kurs mindestens "
                "5 $ und 1 Mio. Stück Umsatz. Kein eigener Trendfilter (der Skill hat keinen), aber wie bei allen "
                "Long-Strategien des Bots der Marktfilter. Stop und Ziel wie die Bot-Strategien derselben Art: Stop −3 ATR, Ziel +3 ATR (wie Ausbruch, Rücksetzer usw.). "
                "Gegenprobe: gleich viele Käufe je Aktie an zufälligen erlaubten Tagen mit denselben Abständen.")
VERMUTUNG = ("Bullen-Flagge als zusätzliche Strategie macht den Bot in allen drei Zeiträumen besser und schlägt zufällige "
             "Zusatz-Käufe.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben mit Zufall.")
VARIANTEN = ("1 je Setup (5 Setups des Scanners, je 1 Datei), Regeln und Abstände vor dem Rechnen festgelegt. Insgesamt "
             "prüfe ich aus dem Skill 9 Ideen auf dem Prüfstand – eine davon kann zufällig gut aussehen; was besteht, "
             "muss vor einer Empfehlung noch auf neuen Zufallslisten bestehen.")


def anpassen(sw):
    H.setup_strategie(sw, KEY, "bullenflagge", "Bullen-Flagge", "trend", BESCHREIBUNG)


def gegenprobe(sw, seed):
    H.setup_strategie(sw, KEY, "bullenflagge", "Bullen-Flagge", "trend", BESCHREIBUNG, zufall_seed=seed)
