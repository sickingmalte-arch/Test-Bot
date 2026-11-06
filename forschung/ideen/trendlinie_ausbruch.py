"""Zeichen-Regel C (Wunsch vom 06.11.2026): Kauf, wenn der Kurs eine fallende Trendlinie nach oben durchbricht.
Die Linie zeichnet der Rechner wie ein Mensch: durch die letzten zwei bestätigten Hochpunkte, das zweite tiefer als
das erste. Anders als die Strategie „Ausbruch“ (waagrechtes 20-Tage-Hoch) ist die Linie schräg."""
import numpy as np
import pandas as pd

KEY = "trendlinie_long"
NAME = "Trendlinien-Ausbruch: neues Kauf-Signal, wenn der Kurs eine fallende Trendlinie nach oben durchbricht"
QUELLE = "Wunsch des Nutzers (Chat vom 06.11.2026), klassische Chart-Zeichnung aus der Technischen Analyse"
BESCHREIBUNG = ("Neue Strategie zusätzlich zu den bisherigen: Die Trendlinie verbindet die letzten zwei bestätigten "
                "Hochpunkte (je 5 Tage davor und danach nicht übertroffen, erst 5 Tage später bekannt) der letzten 6 "
                "Monate, das zweite tiefer als das erste. Kauf-Signal, wenn der Schluss heute über der Linie liegt und "
                "gestern noch darunter, Kurs über der 200-Tage-Linie, Markt im Aufwärtstrend. Stop −3 ATR, Ziel +3 ATR "
                "(wie die anderen Trend-Strategien). Gegenprobe: genauso viele Käufe an zufälligen Tagen über der "
                "200-Tage-Linie, mit denselben Stop- und Zielabständen.")
VERMUTUNG = ("Ein zusätzliches Kauf-Signal beim Bruch einer fallenden Trendlinie macht den Bot in allen drei Zeiträumen "
             "besser und schlägt zufällige Zusatz-Käufe.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder deutlich mehr Rückgang als der jetzige Bot, oder nicht besser als "
                  "die beste von 6 Gegenproben mit Zufall.")
VARIANTEN = "1 (Linie durch die letzten zwei Hochpunkte, 6 Monate, Stop/Ziel 3 ATR), vor dem Rechnen festgelegt."


def _hochpunkte(h, w=5):
    return np.flatnonzero(pd.Series(h).rolling(2 * w + 1, center=True).max().to_numpy() == h)


def trendlinie(h, i, fenster=126, w=5):
    """Wert der fallenden Trendlinie an Tag i (und i-1) aus den letzten zwei bis Tag i bestätigten Hochpunkten,
    sonst None."""
    hoch = _hochpunkte(h, w)
    bekannt = hoch[(hoch <= i - w) & (hoch >= i - fenster)]
    if len(bekannt) < 2:
        return None
    p1, p2 = bekannt[-2], bekannt[-1]
    if h[p2] >= h[p1]:
        return None
    steigung = (h[p2] - h[p1]) / (p2 - p1)
    return h[p1] + steigung * (i - p1), h[p1] + steigung * (i - 1 - p1)


def _ausbruch(d, grund_ok, fenster=126, w=5):
    h, c, atr = (np.asarray(d[k], dtype=float) for k in ("H", "C", "ATR"))
    n = len(c)
    feuert, stop, ziel = np.zeros(n, bool), np.full(n, np.nan), np.full(n, np.nan)
    hoch = _hochpunkte(h, w)
    for i in np.flatnonzero(grund_ok & np.isfinite(atr) & (atr > 0)):
        if i < 1:
            continue
        bekannt = hoch[(hoch <= i - w) & (hoch >= i - fenster)]
        if len(bekannt) < 2:
            continue
        p1, p2 = bekannt[-2], bekannt[-1]
        if h[p2] >= h[p1]:
            continue
        s = (h[p2] - h[p1]) / (p2 - p1)
        heute, gestern = h[p1] + s * (i - p1), h[p1] + s * (i - 1 - p1)
        if c[i] > heute and c[i - 1] <= gestern:
            feuert[i] = True
            stop[i] = c[i] - 3.0 * atr[i]
            ziel[i] = c[i] + 3.0 * atr[i]
    return feuert, stop, ziel


def _grundlage(d, markt, einst, sw):
    c = np.asarray(d["C"], dtype=float)
    sma200 = d["df"]["SMA_200"].to_numpy(dtype=float)
    ok = np.isfinite(sma200) & (c > sma200)
    if markt is not None and getattr(einst, "marktfilter", True):
        ok &= sw.markt_vortag(markt, d["idx"]) != 0
    return ok


def _neue_strategie(sw, signal):
    sw.STRATEGIEN[KEY] = {"name": "Trendlinien-Ausbruch", "richtung": 1, "art": "trend", "regel": BESCHREIBUNG}
    sw.VORRANG[KEY] = len(sw.VORRANG)
    original = sw.bereite_vor

    def neu(ticker, df, fx, zahlen_df, einst, markt=None):
        d = original(ticker, df, fx, zahlen_df, einst, markt)
        werte = signal(ticker, d, _grundlage(d, markt, einst, sw))
        d["signale_roh"][KEY] = werte
        d["signale"][KEY] = werte
        return d
    sw.bereite_vor = neu


def anpassen(sw):
    _neue_strategie(sw, lambda t, d, ok: _ausbruch(d, ok))


def gegenprobe(sw, seed):
    """Gleich viele Käufe je Aktie an zufälligen Tagen über der 200-Tage-Linie, Stop/Ziel wieder ±3 ATR."""
    def zufall(t, d, ok):
        feuert, _, _ = _ausbruch(d, ok)
        c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
        frei = np.flatnonzero(ok & np.isfinite(atr) & (atr > 0) & ~feuert)
        f, s, z = np.zeros(len(c), bool), np.full(len(c), np.nan), np.full(len(c), np.nan)
        n = int(feuert.sum())
        if n and len(frei):
            tage = np.random.default_rng([seed, sum(map(ord, t))]).choice(frei, min(n, len(frei)), replace=False)
            f[tage], s[tage], z[tage] = True, c[tage] - 3.0 * atr[tage], c[tage] + 3.0 * atr[tage]
        return f, s, z
    _neue_strategie(sw, zufall)
