"""Boden-Regel d (Wunsch vom 03.11.2026): Ziel am nächsten Widerstand statt fester Abstand."""
import numpy as np
import pandas as pd


def _boden_und_hoch(d, w=5, fenster=126):
    """Je Tag: letzter bestätigter Boden unter dem Schluss (Wendetief, je w Tage höher, erst w Tage später bekannt) und
    letzter bestätigter Widerstand über dem Schluss (Wendehoch). Wie boden_am_tag/unterstuetzungen im Bot, nur schnell."""
    l, h, c = (np.asarray(d[k], dtype=float) for k in ("L", "H", "C"))
    n = len(c)
    tief = pd.Series(l).rolling(2 * w + 1, center=True).min().to_numpy() == l
    hoch = pd.Series(h).rolling(2 * w + 1, center=True).max().to_numpy() == h
    tiefs, hochs = np.flatnonzero(tief), np.flatnonzero(hoch)
    boden, wid = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(n):
        for p in tiefs[np.searchsorted(tiefs, i - w, side="right") - 1::-1][:20] if len(tiefs) else []:
            if p < i - fenster:
                break
            if l[p] < c[i]:
                boden[i] = l[p]
                break
        for p in hochs[np.searchsorted(hochs, i - w, side="right") - 1::-1][:20] if len(hochs) else []:
            if p < i - fenster:
                break
            if h[p] > c[i]:
                wid[i] = h[p]
                break
    return boden, wid


def _signale_aendern(sw, aendern):
    """Ersetzt bereite_vor: aendern(ticker, d, key, feuert, stop, ziel) -> (feuert, stop, ziel)."""
    original = sw.bereite_vor

    def neu(ticker, *a, **k):
        d = original(ticker, *a, **k)
        for key, (feuert, stop_a, ziel_a) in list(d["signale"].items()):
            d["signale"][key] = aendern(ticker, d, key, np.asarray(feuert, dtype=bool).copy(),
                                        np.asarray(stop_a, dtype=float).copy(), np.asarray(ziel_a, dtype=float).copy())
        return d
    sw.bereite_vor = neu


def _zufaellig_weg(seed, t, key, feuert, n):
    weg = np.zeros(len(feuert), dtype=bool)
    orte = np.flatnonzero(feuert)
    if n and len(orte):
        rng = np.random.default_rng([seed, sum(map(ord, t)), sum(map(ord, key))])
        weg[rng.choice(orte, min(n, len(orte)), replace=False)] = True
    return weg


NAME = "Boden d: Ziel am nächsten Widerstand (letztes Wendehoch über dem Kurs)"
QUELLE = "Wunsch des Nutzers (Chat vom 03.11.2026), klassische Widerstands-Regel"
BESCHREIBUNG = ("Das Ziel liegt am letzten Wendehoch über dem Kurs (Widerstand) statt beim heutigen festen Abstand. Gibt es "
                "keinen Widerstand oder läge er weniger als 0,5 ATR über dem Kurs, bleibt das heutige Ziel.")


def anpassen(sw):
    def aendern(t, d, key, feuert, stop, ziel):
        _, wid = _boden_und_hoch(d)
        c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
        ok = np.isfinite(wid) & (wid - c >= 0.5 * atr)
        return feuert, stop, np.where(ok, wid, ziel)
    _signale_aendern(sw, aendern)
