"""Kaufzeit 3 (Wunsch des Nutzers für Fr 06.11.2026): zur Eröffnung nur kaufen, wenn es keine Lücke nach oben gibt."""
import numpy as np

NAME = "Kaufzeit 3: Kauf zur Eröffnung nur ohne Kurslücke nach oben (Eröffnung nicht über dem Schluss des Signaltags)"
QUELLE = "Wunsch des Nutzers (Chat vom 05.11.2026): sollten wir die Kaufzeit ändern?"
BESCHREIBUNG = ("Wie heute (Eröffnung am nächsten Tag bis zum Limit), aber ein Long-Kauf entfällt, wenn die Eröffnung über "
                "dem Schlusskurs des Signaltags liegt. Gegenprobe: genauso oft zufällig auslassen (je Aktie so oft, wie "
                "sie mit einer Lücke nach oben eröffnet).")
VERMUTUNG = "Nicht hinter einer Lücke nach oben herzukaufen, macht den Bot in allen drei Zeiträumen besser und schlägt Zufall."
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder deutlich mehr Rückgang als der jetzige Bot, oder nicht besser als "
                  "die beste von 6 Gegenproben.")
VARIANTEN = "3 Kaufzeiten (Schluss Signaltag, Schluss nächster Tag, Eröffnung ohne Lücke nach oben), vorher festgelegt."


def _luecke(d, i):
    return i > 0 and np.isfinite(d["O"][i]) and d["O"][i] > d["C"][i - 1]


def anpassen(sw):
    orig = sw.einstieg_moeglich

    def moeglich(d, i, r, stop, limit):
        return orig(d, i, r, stop, limit) and not (r > 0 and _luecke(d, i))
    sw.einstieg_moeglich = moeglich


def gegenprobe(sw, seed):
    orig = sw.einstieg_moeglich

    def moeglich(d, i, r, stop, limit):
        if "_luecke_anteil" not in d:
            o, c = np.asarray(d["O"], float), np.asarray(d["C"], float)
            ok = np.isfinite(o[1:]) & np.isfinite(c[:-1])
            d["_luecke_anteil"] = float((o[1:][ok] > c[:-1][ok]).mean()) if ok.any() else 0.0
        zufall = np.random.default_rng([seed, i, sum(map(ord, d["ticker"]))]).random() < d["_luecke_anteil"]
        return orig(d, i, r, stop, limit) and not (r > 0 and zufall)
    sw.einstieg_moeglich = moeglich
