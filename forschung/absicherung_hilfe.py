"""Prüfung „Absicherung nur in Krisen“ (Wunsch des Nutzers vom 17.11.2026: Shorts, damit der Bot auch bei fallenden
Kursen verdient). Der Bot handelt ganz normal; dazu kommt ein Nasdaq-100-Short (QQQ) über einen festen Anteil des
Depotwerts, aber nur an Tagen, an denen am Abend vorher der Angst-Index VIX über 30 schloss UND der Nasdaq-100 unter
seiner 200-Tage-Linie lag. Gerechnet auf dem Wertverlauf des Bots (erster Lauf je Zeitraum), Short täglich an den
Depotwert angepasst, 0,1 % Spread bei jedem Ein- und Ausstieg und 0,5 % Leihgebühr pro Jahr. Vereinfachung: Der
Euro-Dollar-Kurs auf den Short-Betrag bleibt außen vor.

Gegenprobe: gleich viele Absicherungs-Tage in gleich langen Blöcken, aber an zufälligen Stellen im Zeitraum."""
import numpy as np
import pandas as pd

QUELLE = ("Whaley (2000), „The Investor Fear Gauge“, Journal of Portfolio Management 26(3) – der VIX steigt in "
          "Krisen; Faber (2007), „A Quantitative Approach to Tactical Asset Allocation“ – Trend über die 200-Tage-Linie. "
          "Frühere eigene Messung (Was der Bot schon weiß): QQQ-Short schon unter der 200-Tage-Linie allein half nicht.")
VIX_GRENZE = 30
SPREAD = 0.001
LEIHE_JAHR = 0.005


def _ohne_zone(s):
    s = s.copy()
    if getattr(s.index, "tz", None) is not None:
        s.index = s.index.tz_localize(None)
    s.index = s.index.normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()


def krisen_tage(qqq, vix):
    """True an Tagen, an deren Schluss VIX > 30 und QQQ unter seiner 200-Tage-Linie lag."""
    q, v = _ohne_zone(qqq), _ohne_zone(vix)
    q200 = q.rolling(200, min_periods=200).mean()
    return ((v.reindex(q.index, method="ffill") > VIX_GRENZE) & (q < q200)).fillna(False)


def ueberlagern(kurve, r_q, an, anteil):
    """Wertverlauf des Bots plus Short über anteil × Depotwert an den Tagen mit an=True (am Vorabend entschieden)."""
    rb = kurve.pct_change().fillna(0).to_numpy()
    an = np.asarray(an, dtype=bool)
    wechsel = np.r_[an[0], an[1:] != an[:-1]]
    tag = rb - anteil * an * r_q - anteil * wechsel * SPREAD - anteil * an * LEIHE_JAHR / 252
    return pd.Series(kurve.iloc[0] * np.cumprod(1 + tag), index=kurve.index)


def zufalls_tage(an, seed):
    """Gleich viele Absicherungs-Tage in gleich langen Blöcken, an zufälligen Stellen (Gegenprobe)."""
    an = np.asarray(an, dtype=bool)
    laengen, k = [], 0
    for x in an:
        if x:
            k += 1
        elif k:
            laengen.append(k)
            k = 0
    if k:
        laengen.append(k)
    if not laengen:
        return an.copy()
    rng = np.random.default_rng(seed)
    rng.shuffle(laengen)
    frei = len(an) - sum(laengen)
    luecken = np.diff(np.r_[0, np.sort(rng.integers(0, frei + 1, size=len(laengen))), frei])
    neu, pos = np.zeros(len(an), bool), 0
    for laenge, luecke in zip(laengen, luecken[:-1]):
        pos += luecke
        neu[pos:pos + laenge] = True
        pos += laenge
    return neu


def pruefen(P, a, watch, sektor_von, idee, anteil):
    """Eigener Prüfablauf für den Prüfstand: jetziger Bot (erster Lauf je Zeitraum) gegen Bot + Krisen-Short und gegen
    Bot + Short an zufälligen Tagen."""
    _, kurven = P.lauf_mit_verlauf(a.cache, watch, sektor_von, a.laeufe)
    qqq = P.D.lies_kurse(a.cache, "QQQ")["Close"]
    krise = krisen_tage(qqq, P.D.lies_kurse(a.cache, "^VIX")["Close"])
    qqq = _ohne_zone(qqq)
    basis, erg, tage = {}, {}, {}
    zufall = [{} for _ in range(P.ZUFALL_LAEUFE)]
    for v, kurve in kurven.items():
        kurve = _ohne_zone(kurve)
        r_q = qqq.reindex(kurve.index, method="ffill").pct_change().fillna(0).to_numpy()
        an = krise.reindex(kurve.index, method="ffill").fillna(False).shift(1, fill_value=False).to_numpy(dtype=bool)
        tage[v] = int(an.sum())
        basis[v] = P.ROT.kennzahlen(kurve)
        erg[v] = P.ROT.kennzahlen(ueberlagern(kurve, r_q, an, anteil))
        for s in range(P.ZUFALL_LAEUFE):
            zufall[s][v] = P.ROT.kennzahlen(ueberlagern(kurve, r_q, zufalls_tage(an, s), anteil))
    text, plus = P.urteil(basis, erg, zufall)
    md = P.markdown(None, idee, basis, erg, zufall, text, plus)
    md = md.replace("Mittel aus mehreren Läufen", "erster Lauf je Zeitraum, Short auf den Wertverlauf gerechnet")
    md += ("\nTage mit Krisen-Short: " + ", ".join(f"{k} {tage[v]}" for k, v in zip(P.R.ZEITRAEUME, basis)) + "\n")
    return text, plus, {"basis": basis, "idee": erg, "zufall": zufall, "krisen_tage": tage}, md
