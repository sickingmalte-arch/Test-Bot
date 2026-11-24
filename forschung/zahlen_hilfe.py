"""Kaufen nach guten Quartalszahlen (Wunsch des Nutzers vom 24.11.2026). Post-Earnings-Drift: Nach einer positiven
Überraschung steigen Kurse im Schnitt noch Wochen weiter (Bernard & Thomas 1989; Chan, Jegadeesh & Lakonishok 1996).
Der Bot lässt Zahlen-Tage bisher aus. Neue Kauf-Strategie (Art Trend): Steigt eine Aktie am Tag, an dem ihre Zahlen auf
den Kurs wirken, um mindestens 2 ATR (vom Vortag) über den Vortagesschluss, kauft der Bot zur nächsten Eröffnung.
Stop −3 ATR, Ziel +3 ATR wie bei den Trend-Strategien, alle übrigen Regeln wie im Bot (Platz, Branche, Risiko, Spread,
Zeitstopp, vor den nächsten Zahlen raus)."""
import numpy as np

QUELLE = ("Bernard & Thomas (1989), „Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?“, "
          "Journal of Accounting Research 27; Chan, Jegadeesh & Lakonishok (1996), „Momentum Strategies“, Journal of "
          "Finance 51 – nach guten Zahlen steigen Kurse im Schnitt noch Wochen weiter.")


def zahlen_sprung(d, faktor=2.0):
    """Am Tag, an dem Quartalszahlen auf den Kurs wirken, schließt die Aktie mindestens faktor × ATR (vom Vortag) über
    dem Vortagesschluss. Alles am Abend dieses Tages bekannt; ohne Termine feuert nichts."""
    c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
    n = len(c)
    reak = d.get("reak")
    if reak is None:
        return np.zeros(n, bool)
    r = np.zeros(n, bool)
    rr = np.asarray(reak, dtype=bool)[:n]
    r[:len(rr)] = rr
    vor, atr_vor = np.r_[np.nan, c[:-1]], np.r_[np.nan, atr[:-1]]
    with np.errstate(invalid="ignore"):
        return r & ((c - vor) >= faktor * atr_vor)


def lang_strategie(sw, key, name, feuert_fn, marktfilter=True, zufall_seed=None):
    """Hängt eine Kauf-Strategie (Art Trend) an den Bot an. marktfilter: wie alle Kauf-Strategien nur, wenn der Markt
    nicht im Abwärtstrend ist. zufall_seed: je Aktie gleich viele Käufe an zufälligen erlaubten Tagen (Gegenprobe)."""
    sw.STRATEGIEN[key] = {"name": name, "richtung": 1, "art": "trend", "regel": name}
    sw.VORRANG[key] = len(sw.VORRANG)
    original = sw.bereite_vor

    def neu(ticker, df, fx, zahlen_df, einst, markt=None):
        d = original(ticker, df, fx, zahlen_df, einst, markt)
        c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
        stop, ziel = c - sw.STOP_TREND_ATR * atr, c + sw.ZIEL_TREND_ATR * atr
        with np.errstate(invalid="ignore"):
            ok = np.isfinite(atr) & (atr > 0) & (stop > 0) & (np.arange(len(c)) >= sw.MIN_KERZEN - 1)
        if marktfilter and markt is not None and getattr(einst, "marktfilter", True):
            ok &= sw.markt_vortag(markt, d["idx"]) != 0
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


MIN_KAEUFE = 30  # unter 30 Käufen je Zeitraum gibt es keine Aussage, nur eine Vermutung


def pruefen(P, a, watch, sektor_von, idee, key, anpassen, gegenprobe):
    """Ablauf wie beim Prüfstand (Bot, Idee, 6 Gegenproben, gleiches Urteil), dazu die Käufe der neuen Strategie je
    Zeitraum: Zahl je Lauf, Ø Ergebnis je Kauf in R (nach Kosten) und Trefferquote."""
    import pandas as pd
    basis = P.lauf(a.cache, watch, sektor_von, a.laeufe)
    deps = []

    def mit_zaehlen(sw):
        anpassen(sw)
        original = sw.simuliere_depot

        def neu(*x, **k):
            dep = original(*x, **k)
            deps.append(dep)
            return dep
        sw.simuliere_depot = neu
    erg = P.lauf(a.cache, watch, sektor_von, a.laeufe, mit_zaehlen)
    zufall = [P.lauf(a.cache, watch, sektor_von, a.laeufe, lambda sw, s=s: gegenprobe(sw, s))
              for s in range(P.ZUFALL_LAEUFE)]
    text, plus = P.urteil(basis, erg, zufall)
    kaeufe = {}
    for i, (von, _) in enumerate(P.R.ZEITRAEUME.values()):  # je Zeitraum genau a.laeufe Depot-Läufe, der Reihe nach
        tr = [x for dep in deps[i * a.laeufe:(i + 1) * a.laeufe] for x in dep["trades"]
              if x["strategie"] == key and x["kauf_tag"] >= pd.Timestamp(von)]
        rr = np.array([(x["erloes"] - x["kosten"]) / x["risiko_eur"] for x in tr if x["risiko_eur"] > 0])
        kaeufe[von] = {"je_lauf": len(tr) / a.laeufe, "schnitt_r": float(rr.mean()) if len(rr) else float("nan"),
                       "treffer": float((rr > 0).mean() * 100) if len(rr) else float("nan")}
    if text.startswith("überall besser") and any(k["je_lauf"] < MIN_KAEUFE for k in kaeufe.values()):
        text += f" – aber unter {MIN_KAEUFE} Käufe in einem Zeitraum, also nur eine Vermutung"
    md = P.markdown(None, idee, basis, erg, zufall, text, plus)
    md += "\nKäufe der neuen Strategie je Lauf · Ø Ergebnis je Kauf nach Kosten · Treffer: " + ", ".join(
        f"{name} {k['je_lauf']:.0f} · " + ("–" if not np.isfinite(k["schnitt_r"]) else
                                           f"{k['schnitt_r']:+.2f} R · {k['treffer']:.0f} %").replace(".", ",")
        for name, k in zip(P.R.ZEITRAEUME, kaeufe.values())) + "\n"
    return text, plus, {"basis": basis, "idee": erg, "zufall": zufall, "kaeufe": kaeufe}, md
