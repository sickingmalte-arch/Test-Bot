"""Bausteine für Short-Ideen auf dem Prüfstand (Wunsch des Nutzers vom 17.11.2026: Shorts, damit der Bot auch bei
fallenden Kursen verdient). Die 8 alten Short-Strategien bleiben aus (alle verloren im Test); eine Idee hängt genau eine
neue Short-Strategie an. Stop und Ziel wie bei den alten Trend-Shorts (Stop +3 ATR, Ziel −3 ATR), höchstens
MAX_SHORTS Shorts gleichzeitig und alle übrigen Regeln wie im Bot (Platz, Branche, Risiko, Spread)."""
import numpy as np

QUELLE_DRIFT = ("Bernard & Thomas (1989), „Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?“, "
                "Journal of Accounting Research 27; Chan, Jegadeesh & Lakonishok (1996), Journal of Finance 51. Nach "
                "schlechten Quartalszahlen fallen Kurse im Schnitt noch Wochen weiter (Post-Earnings-Drift).")


def zahlen_absturz(d, faktor=2.0):
    """Am Tag, an dem Quartalszahlen auf den Kurs wirken, schließt die Aktie mindestens faktor × ATR (vom Vortag) unter
    dem Vortagesschluss – ein Kursrutsch nach schlechten Zahlen. Alles am Abend dieses Tages bekannt; die Termine der
    Zahlen stehen vorher fest. Ohne Termine (keine Daten) feuert nichts."""
    c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
    n = len(c)
    reak = d.get("reak")
    if reak is None:
        return np.zeros(n, bool)
    reak = np.asarray(reak, dtype=bool)[:n]
    vor, atr_vor = np.r_[np.nan, c[:-1]], np.r_[np.nan, atr[:-1]]
    with np.errstate(invalid="ignore"):
        return reak & ((vor - c) >= faktor * atr_vor)


def short_strategie(sw, key, name, feuert_fn, marktfilter=True, zufall_seed=None):
    """Hängt eine Short-Strategie (Art Trend) an den Bot an. feuert_fn(d) -> bool je Tag. marktfilter: wie bei den alten
    Shorts nur, wenn der Markt nicht im Aufwärtstrend ist. Mit zufall_seed: je Aktie gleich viele Shorts an zufälligen
    erlaubten Tagen mit denselben Abständen (Gegenprobe)."""
    sw.STRATEGIEN[key] = {"name": name, "richtung": -1, "art": "trend", "regel": name}
    sw.VORRANG[key] = len(sw.VORRANG)
    original = sw.bereite_vor

    def neu(ticker, df, fx, zahlen_df, einst, markt=None):
        d = original(ticker, df, fx, zahlen_df, einst, markt)
        c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
        stop, ziel = c + sw.STOP_TREND_ATR * atr, c - sw.ZIEL_TREND_ATR * atr
        with np.errstate(invalid="ignore"):
            ok = np.isfinite(atr) & (atr > 0) & (ziel > 0) & (np.arange(len(c)) >= sw.MIN_KERZEN - 1)
        if marktfilter and markt is not None and getattr(einst, "marktfilter", True):
            ok &= sw.markt_vortag(markt, d["idx"]) != 1
        feuert = np.asarray(feuert_fn(d), dtype=bool) & ok
        if zufall_seed is not None:
            frei, anzahl = np.flatnonzero(ok & ~feuert), int(feuert.sum())
            feuert = np.zeros(len(c), bool)
            if anzahl and len(frei):
                rng = np.random.default_rng([zufall_seed, sum(map(ord, ticker))])
                feuert[rng.choice(frei, min(anzahl, len(frei)), replace=False)] = True
        d["signale_roh"][key] = (feuert, stop, ziel)
        d["signale"][key] = (feuert, stop, ziel)
        return d
    sw.bereite_vor = neu
