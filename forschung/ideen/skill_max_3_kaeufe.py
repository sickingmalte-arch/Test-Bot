"""Prüfung „day-trader-skill“ (Wunsch vom 11.11.2026), Risiko-Regel aus trader-risk: max_trades_per_day = 3
(dazu passt das Tagesverlust-Limit 150 $ bei 50 $ Risiko je Trade – auch das sind höchstens 3 Käufe am Tag)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skill_hilfe as H  # noqa: E402

NAME = "Day-Trader-Skill: höchstens 3 neue Käufe am Tag"
QUELLE = H.QUELLE
BESCHREIBUNG = ("Wie die Risiko-Prüfung des Skills: An einem Handelstag kauft der Bot höchstens 3 neue Positionen, auch "
                "wenn mehr Aufträge möglich wären (die übrigen verfallen wie bei vollem Depot). Sonst alles wie heute. "
                "Gegenprobe: ebenfalls höchstens 3, aber in zufälliger statt in der Bot-Reihenfolge ausgewählt.")
VERMUTUNG = ("Höchstens 3 Käufe am Tag verteilen die Einstiege besser über die Zeit und machen den Bot in allen drei "
             "Zeiträumen besser, und die Bot-Reihenfolge schlägt die zufällige Auswahl.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr als 1 Punkt mehr Rückgang als der jetzige Bot, oder in "
                  "einem Zeitraum nicht besser als die beste von 6 Gegenproben.")
VARIANTEN = "1 (Grenze 3 wie im Skill), vor dem Rechnen festgelegt; Teil von 9 Skill-Ideen auf dem Prüfstand."


def anpassen(sw):
    H.max_kaeufe_am_tag(sw, 3)


def gegenprobe(sw, seed):
    H.max_kaeufe_am_tag(sw, 3, zufall_seed=seed)
