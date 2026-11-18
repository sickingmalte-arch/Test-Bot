"""Wunsch des Nutzers vom 17.11.2026 („Es muss doch einen Weg geben, Shorts profitabel zu machen“ – gewählt: „Fairer
Test mit S&P 500“): die schon geprüften Short-Ideen noch einmal, aber mit Aktien, die man damals ohne Rückblick hätte
wählen können. Ablauf, Urteil und verbleibende Verzerrung: forschung/short_fair_hilfe.py."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import short_fair_hilfe as F  # noqa: E402
import short_hilfe as S  # noqa: E402

NAME = "Fairer Short-Test: alte Shorts und Short nach schlechten Zahlen mit zufälligen damaligen S&P-500-Aktien"
QUELLE = "Ehrlicher Bot-Check vom 06.11.2026 (Verzerrung durch die heutige Watchlist); " + S.QUELLE_DRIFT
BESCHREIBUNG = ("Bisher liefen alle Short-Tests mit der heutigen Watchlist – lauter Aktien, die im Rückblick stark "
                "gestiegen sind. Hier handelt der Bot mit denselben 8 Zufallslisten aus dem damaligen S&P 500 wie im "
                "ehrlichen Bot-Check vom 06.11. (je Zeitraum am Abend vor dem Start gezogen). Je Liste: der Bot nur mit "
                "Long gegen denselben Bot mit Shorts. Höchstens 2 Shorts gleichzeitig, Stop und Ziel wie im Bot, mit "
                "Gebühr und Spread. Gegenprobe: je Aktie gleich viele Shorts an zufälligen erlaubten Tagen.")
VERMUTUNG = ("Shorts haben bisher nur verloren, weil die heutige Watchlist aus späteren Gewinnern besteht. Mit Aktien, "
             "die man damals ohne Rückblick hätte wählen können, macht mindestens eine Short-Variante den Bot in allen "
             "drei Zeiträumen besser.")
WIDERLEGT_WENN = ("Keine Variante schafft in jedem Zeitraum alles davon: Mitte der 8 Listen mehr Rendite als der Bot nur "
                  "mit Long, mindestens 6 von 8 Listen besser, höchstens 1 Punkt mehr Rückgang (Mitte), mindestens 30 "
                  "Short-Trades und mehr Rendite als die beste von 6 Zufalls-Gegenproben.")
VARIANTEN = ("3, vor dem Rechnen festgelegt: (A) die 8 alten Short-Strategien wie im Bot (nur außerhalb des "
             "Aufwärtsmarkts), (B) Short nach schlechten Zahlen nur außerhalb des Aufwärtsmarkts, (C) Short nach "
             "schlechten Zahlen in jeder Marktlage – B und C genau wie am 17.11. (Rutsch ab 2 ATR am Zahlen-Tag).")


def _zahlen(marktfilter, seed=None):
    return lambda sw: S.short_strategie(sw, "zahlen_absturz_short", "Zahlen-Absturz", S.zahlen_absturz,
                                        marktfilter=marktfilter, zufall_seed=seed)


def pruefen(P, a, watch, sektor_von):
    zr = F.listen(P, a, len(watch))
    varianten = [
        {"key": "alte_shorts", "kurz": "A", "name": "+ die 8 alten Short-Strategien",
         "anpassen": F.alte_shorts, "zufall": lambda sw, s: F.alte_shorts(sw, seed=s)},
        {"key": "zahlen_abwaerts", "kurz": "B", "name": "+ Short nach schlechten Zahlen (nicht im Aufwärtsmarkt)",
         "anpassen": _zahlen(True), "zufall": lambda sw, s: _zahlen(True, s)(sw)},
        {"key": "zahlen_immer", "kurz": "C", "name": "+ Short nach schlechten Zahlen (jede Marktlage)",
         "anpassen": _zahlen(False), "zufall": lambda sw, s: _zahlen(False, s)(sw)},
    ]
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG, VERMUTUNG=VERMUTUNG,
                                 WIDERLEGT_WENN=WIDERLEGT_WENN, VARIANTEN=VARIANTEN)
    return F.pruefen(P, a, sektor_von, idee, zr, varianten, len(watch))
