"""Marktfilter feiner (Wunsch des Nutzers vom 24.11.2026, als der Bot wegen des Filters tagelang nicht kaufte). Heute:
Der Bot kauft nur, wenn der Nasdaq-100 (QQQ) am Vortag über seiner 200-Tage-Linie schloss. Geprüft werden zwei
Varianten der Ampel; alles andere bleibt gleich. Gegenprobe: dieselbe Zahl roter Tage in gleich langen Blöcken an
zufälligen Stellen (zufällige Kaufpausen gleicher Länge)."""
import numpy as np
import pandas as pd

import absicherung_hilfe as A

QUELLE = ("Faber (2007), „A Quantitative Approach to Tactical Asset Allocation“, Journal of Wealth Management – Trend "
          "über die 200-Tage-Linie als Ampel; die Bestätigung über 2 Tage soll Fehlsignale rund um die Linie vermeiden.")


def bestaetigt(trend, tage=2):
    """Ampel schaltet erst um, wenn der Markt `tage` Schlusskurse in Folge auf der anderen Seite der Linie liegt."""
    werte = trend.to_numpy(dtype=float)
    aus, zustand = np.full(len(werte), np.nan), np.nan
    for i, w in enumerate(werte):
        if np.isfinite(w):
            if not np.isfinite(zustand):
                zustand = w
            elif w != zustand and i >= tage - 1 and all(werte[i - k] == w for k in range(tage)):
                zustand = w
        aus[i] = zustand
    return pd.Series(aus, index=trend.index)


def zufall(trend, seed):
    """Gleich viele rote Tage in gleich langen Blöcken, aber an zufälligen Stellen (Gegenprobe)."""
    werte = trend.to_numpy(dtype=float).copy()
    gueltig = np.flatnonzero(np.isfinite(werte))
    rot = A.zufalls_tage(werte[gueltig] == 0, seed)
    werte[gueltig] = np.where(rot, 0.0, 1.0)
    return pd.Series(werte, index=trend.index)


def ampel(sw, cache, D, art, seed=None):
    """Ersetzt die Marktampel des Bots: art 'spy' = S&P 500 statt Nasdaq-100, 'zwei_tage' = Umschalten erst nach 2 Tagen."""
    original = sw.markt_trend

    def neu(markt_df):
        if art == "spy":
            spy = D.lies_kurse(cache, "SPY")
            if spy is not None and markt_df is not None and len(markt_df):
                spy = spy[spy.index <= markt_df.index.max()]
            t = original(spy)
        else:
            t = original(markt_df)
            if t is not None and art == "zwei_tage":
                t = bestaetigt(t, 2)
        if t is not None and seed is not None:
            t = zufall(t, seed)
        return t
    sw.markt_trend = neu


def rote_tage(P, a, art):
    """Je Zeitraum: Anteil der Börsentage mit roter Ampel heute und mit der Variante (in %)."""
    sw = P.R.sw
    qqq = P.D.lies_kurse(a.cache, "QQQ")
    heute = sw.markt_trend(qqq)
    if art == "spy":
        neu = sw.markt_trend(P.D.lies_kurse(a.cache, "SPY"))
    else:
        neu = bestaetigt(heute, 2)
    aus = {}
    for name, (von, bis) in P.R.ZEITRAEUME.items():
        h = heute[(heute.index >= pd.Timestamp(von)) & (heute.index <= pd.Timestamp(bis))].dropna()
        v = neu[(neu.index >= pd.Timestamp(von)) & (neu.index <= pd.Timestamp(bis))].dropna()
        aus[name] = (float((h == 0).mean() * 100) if len(h) else float("nan"),
                     float((v == 0).mean() * 100) if len(v) else float("nan"))
    return aus


def pruefen(P, a, watch, sektor_von, idee, art):
    basis = P.lauf(a.cache, watch, sektor_von, a.laeufe)
    erg = P.lauf(a.cache, watch, sektor_von, a.laeufe, lambda sw: ampel(sw, a.cache, P.D, art))
    zufall_erg = [P.lauf(a.cache, watch, sektor_von, a.laeufe, lambda sw, s=s: ampel(sw, a.cache, P.D, art, seed=s))
                  for s in range(P.ZUFALL_LAEUFE)]
    text, plus = P.urteil(basis, erg, zufall_erg)
    md = P.markdown(None, idee, basis, erg, zufall_erg, text, plus)
    rot = rote_tage(P, a, art)
    md += ("\nTage mit roter Ampel (heute / Variante): " + ", ".join(
        f"{k} {h:.0f} / {v:.0f} %" for k, (h, v) in rot.items()) + "\n")
    return text, plus, {"basis": basis, "idee": erg, "zufall": zufall_erg, "rote_tage": rot}, md
