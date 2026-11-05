"""Boden-Kauf (Wunsch vom 05.11.2026): zusätzliches Kauf-Signal, wenn der Kurs an einer Unterstützung abprallt.
Anders als die Boden-Regeln vom 04.11. ist das kein Filter, sondern eine neue Strategie „Boden-Abpraller ↑“."""
import numpy as np
import pandas as pd

MIN_GRUENDE = 2  # starke Zone: mindestens 2 Gründe (z. B. Doppel-Tief, großes Wendetief, runde Zahl)
KEY = "boden_long"

NAME = "Boden-Kauf: neues Kauf-Signal am Abpraller von einer starken Unterstützung (mind. 2 Gründe)"
QUELLE = "Wunsch des Nutzers (Chat vom 05.11.2026), klassischer Kauf an der Unterstützung"
BESCHREIBUNG = ("Neue Strategie zusätzlich zu den bisherigen: Das Tagestief berührt eine Unterstützung (altes Wendetief, "
                "höchstens 0,25 ATR darüber oder 0,5 ATR darunter), der Schluss liegt wieder über ihr und in der oberen "
                "Hälfte der Tageskerze, der Vortag lag noch über ihr, Kurs über der 200-Tage-Linie, Markt im Aufwärtstrend. "
                f"Die Zone braucht mindestens {MIN_GRUENDE} Gründe (Wendetief, zweites Tief in derselben Zone, großes "
                "Wendetief über 10 Tage, runde Zahl). Stop 0,5 ATR unter der Zone (mindestens 1 ATR unter dem Kurs), "
                "Ziel +2 ATR. Gegenprobe: genauso viele Käufe an zufälligen Tagen über der 200-Tage-Linie, mit "
                "denselben Stop-Abständen.")


def _wendetiefs(l, w):
    """Wendetiefs: Tief, das je w Tage davor und danach nicht unterboten wird (erst w Tage später bekannt)."""
    return np.flatnonzero(pd.Series(l).rolling(2 * w + 1, center=True).min().to_numpy() == l)


def _grundlage(d, markt, einst, sw):
    """Tage, an denen ein Long-Kauf überhaupt in Frage kommt: Kurs über der 200-Tage-Linie, Markt nicht im Abwärtstrend."""
    c = np.asarray(d["C"], dtype=float)
    sma200 = d["df"]["SMA_200"].to_numpy(dtype=float)
    ok = np.isfinite(sma200) & (c > sma200)
    if markt is not None and getattr(einst, "marktfilter", True):
        ok &= sw.markt_vortag(markt, d["idx"]) != 0
    return ok


def _abpraller(d, grund_ok, fenster=126):
    """(feuert, stop, ziel) für die neue Strategie."""
    h, l, c, atr = (np.asarray(d[k], dtype=float) for k in ("H", "L", "C", "ATR"))
    n = len(c)
    feuert, stop, ziel = np.zeros(n, bool), np.full(n, np.nan), np.full(n, np.nan)
    tiefs, gross = _wendetiefs(l, 5), _wendetiefs(l, 10)
    obere_haelfte = (c - l) >= 0.5 * (h - l)
    kandidat = grund_ok & obere_haelfte & np.isfinite(atr) & (atr > 0)
    kandidat[0] = False
    for i in np.flatnonzero(kandidat):
        a = atr[i]
        bekannt = tiefs[(tiefs <= i - 5) & (tiefs >= i - fenster)]  # nur bestätigte Tiefs (kein Blick in die Zukunft)
        if not len(bekannt):
            continue
        for p in bekannt[::-1][:20]:  # das jüngste passende Tief zählt
            f = l[p]
            if not (f - 0.5 * a <= l[i] <= f + 0.25 * a and c[i] > f and c[i - 1] > f):
                continue
            nah = np.abs(l[bekannt] - f) <= 0.01 * f
            g_bekannt = gross[(gross <= i - 10) & (gross >= i - fenster)]
            stufe = 1 if f < 20 else 5 if f < 50 else 10 if f < 200 else 50 if f < 1000 else 100 if f < 5000 else 500
            runde = abs(f - round(f / stufe) * stufe) <= 0.01 * f
            gruende = 1 + (nah.sum() >= 2) + bool(np.any(np.abs(l[g_bekannt] - f) <= 0.01 * f)) + runde
            if gruende >= MIN_GRUENDE:
                feuert[i] = True
                stop[i] = min(f - 0.5 * a, c[i] - 1.0 * a)
                ziel[i] = c[i] + 2.0 * a
            break
    return feuert, stop, ziel


def _neue_strategie(sw, signal):
    sw.STRATEGIEN[KEY] = {"name": "Boden-Abpraller", "richtung": 1, "art": "gegen", "regel": BESCHREIBUNG}
    sw.VORRANG[KEY] = len(sw.VORRANG)
    original = sw.bereite_vor

    def neu(ticker, df, fx, zahlen_df, einst, markt=None):
        d = original(ticker, df, fx, zahlen_df, einst, markt)
        grund_ok = _grundlage(d, markt, einst, sw)
        werte = signal(ticker, d, grund_ok)
        d["signale_roh"][KEY] = werte
        d["signale"][KEY] = werte
        return d
    sw.bereite_vor = neu


def anpassen(sw):
    _neue_strategie(sw, lambda t, d, grund_ok: _abpraller(d, grund_ok))


def gegenprobe(sw, seed):
    """Gleich viele Käufe je Aktie an zufälligen Tagen über der 200-Tage-Linie, mit denselben Stop-Abständen (in ATR)."""
    def zufall(t, d, grund_ok):
        feuert, stop, _ = _abpraller(d, grund_ok)
        c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
        orte, frei = np.flatnonzero(feuert), np.flatnonzero(grund_ok & np.isfinite(atr) & (atr > 0) & ~feuert)
        z_f, z_s, z_z = np.zeros(len(c), bool), np.full(len(c), np.nan), np.full(len(c), np.nan)
        if len(orte) and len(frei):
            rng = np.random.default_rng([seed, sum(map(ord, t))])
            tage = rng.choice(frei, min(len(orte), len(frei)), replace=False)
            abstand = rng.permutation((c[orte] - stop[orte]) / atr[orte])[:len(tage)]
            z_f[tage] = True
            z_s[tage] = c[tage] - abstand * atr[tage]
            z_z[tage] = c[tage] + 2.0 * atr[tage]
        return z_f, z_s, z_z
    _neue_strategie(sw, zufall)
