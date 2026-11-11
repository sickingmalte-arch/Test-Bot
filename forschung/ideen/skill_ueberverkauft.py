"""Prüfung „day-trader-skill“ (Wunsch vom 11.11.2026), Scanner-Setup 'ueberverkauft' aus trader-scanner/scan.py
(find_setups) als zusätzliche Kauf-Strategie des Swing-Bots. Gemeinsame Bausteine: forschung/skill_hilfe.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skill_hilfe as H  # noqa: E402

KEY = "skill_ueberverkauft_long"
NAME = "Day-Trader-Skill: Überverkauft (RSI 14 unter 30) als neue Kauf-Strategie"
QUELLE = H.QUELLE
BESCHREIBUNG = ("Kauf-Signal, solange der RSI 14 (Wilder) unter 30 liegt. Regel wörtlich aus dem Scanner des Skills (nur Schlusskurse), dazu wie im Skill Kurs mindestens "
                "5 $ und 1 Mio. Stück Umsatz. Kein eigener Trendfilter (der Skill hat keinen), aber wie bei allen "
                "Long-Strategien des Bots der Marktfilter. Stop und Ziel wie die Bot-Strategien derselben Art: Stop −2,5 ATR, Ziel +2 ATR (wie Gegenbewegung und RSI-2). "
                "Gegenprobe: gleich viele Käufe je Aktie an zufälligen erlaubten Tagen mit denselben Abständen.")
VERMUTUNG = ("Überverkauft (RSI 14 unter 30) als zusätzliche Strategie macht den Bot in allen drei Zeiträumen besser und schlägt zufällige "
             "Zusatz-Käufe.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben mit Zufall.")
VARIANTEN = ("1 je Setup (5 Setups des Scanners, je 1 Datei), Regeln und Abstände vor dem Rechnen festgelegt. Insgesamt "
             "prüfe ich aus dem Skill 9 Ideen auf dem Prüfstand – eine davon kann zufällig gut aussehen; was besteht, "
             "muss vor einer Empfehlung noch auf neuen Zufallslisten bestehen.")


def anpassen(sw):
    H.setup_strategie(sw, KEY, "ueberverkauft", "Überverkauft", "gegen", BESCHREIBUNG)


def gegenprobe(sw, seed):
    H.setup_strategie(sw, KEY, "ueberverkauft", "Überverkauft", "gegen", BESCHREIBUNG, zufall_seed=seed)
