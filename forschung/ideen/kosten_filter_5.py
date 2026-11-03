"""Kosten-Filter (Wunsch vom 03.11.2026): nur Signale kaufen, deren Ziel mindestens 5 % über dem Kurs liegt.

Ohne Ordergebühr kostet ein Trade nur noch den Spread: 0,1 % beim Kauf und 0,1 % beim Verkauf, zusammen etwa 0,2 %
des Einsatzes. Bei einem Ziel 5 % über dem Kurs sind das höchstens rund 4 % des geplanten Gewinns."""
import numpy as np

NAME = "Kosten-Filter: Ziel mindestens 5 % über dem Kurs"
QUELLE = "eigene Idee (Chat vom 03.11.2026): ohne Kosten brächte der Bot im Rückblick 3–7 Punkte mehr"
BESCHREIBUNG = ("Der Bot kauft nur Signale, bei denen der geplante Gewinn bis zum Ziel mindestens 5 % beträgt. So "
                "fressen der Spread (zusammen etwa 0,2 % je Trade) höchstens rund 4 % des geplanten Gewinns.")
MINDEST = 5 / 100


def _filtern(sw, auswahl):
    """Ersetzt bereite_vor: Signale, die auswahl(d, key, feuert, ziel) verwirft, feuern nicht."""
    original = sw.bereite_vor

    def neu(ticker, *a, **k):
        d = original(ticker, *a, **k)
        for key, (feuert, stop_a, ziel_a) in list(d["signale"].items()):
            feuert = np.asarray(feuert, dtype=bool).copy()
            weg = auswahl(ticker, d, key, feuert, np.asarray(ziel_a, dtype=float))
            d["signale"][key] = (feuert & ~weg, stop_a, ziel_a)
        return d
    sw.bereite_vor = neu


def _zu_klein(d, ziel):
    c = np.asarray(d["C"], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (ziel - c) / c < MINDEST


def anpassen(sw):
    _filtern(sw, lambda t, d, key, feuert, ziel: feuert & _zu_klein(d, ziel))


def gegenprobe(sw, seed):
    """Gleich viele Signale je Aktie und Strategie auslassen wie der Filter – aber zufällig ausgewählte."""
    def zufall(t, d, key, feuert, ziel):
        n = int((feuert & _zu_klein(d, ziel)).sum())
        weg = np.zeros(len(feuert), dtype=bool)
        orte = np.flatnonzero(feuert)
        if n and len(orte):
            rng = np.random.default_rng([seed, sum(map(ord, t)), sum(map(ord, key))])
            weg[rng.choice(orte, min(n, len(orte)), replace=False)] = True
        return weg
    _filtern(sw, zufall)
