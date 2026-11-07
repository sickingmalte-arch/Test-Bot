"""Ehrlicher Check 2 (06.11.2026, der Nutzer gab freie Hand): drei Fragen in einem Lauf, alle mit Aktien, die zu Beginn
des Zeitraums wirklich im S&P 500 waren (Liste github.com/fja05680/sp500) – keine Rückblick-Watchlist.

1. Watchlist nach fester Regel: die 24 meistgehandelten (Ø Umsatz in Dollar, letzte 3 Monate) oder die 24 stärksten
   (Anstieg über 12 Monate ohne den letzten Monat) S&P-500-Aktien am Start – statt von Hand gewählt.
2. Kern und Beimischung: halb Swing-Bot, halb S&P 500 halten.
3. Welche Strategien haben auf zufälligen damaligen Aktien wirklich einen Vorteil – mehr Ø R nach Kosten als zufällige
   Käufe mit denselben Stop- und Zielabständen (sonst verdient jeder Kauf nur am steigenden Markt)?
Nur eine Messung: Am Bot ändert sich nichts."""
import importlib
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot_ehrliche_aktienliste as E  # noqa: E402  (gleiche Zufallslisten wie im Check vom 06.11.)

NAME = "Ehrlicher Check 2: Watchlist nach Regel, halb Bot halb S&P 500, echte Stärke der Strategien"
QUELLE = "Folge des ehrlichen Bot-Checks vom 06.11.2026"
BESCHREIBUNG = ("Zu Beginn jedes Zeitraums (2010, 2015, 2022) stehen nur Aktien zur Wahl, die an diesem Tag im S&P 500 "
                "waren. Der unveränderte Swing-Bot handelt mit 8 Zufallslisten (wie im ersten Check) und mit zwei "
                "Regel-Listen: die 24 meistgehandelten und die 24 stärksten Aktien. Dazu: halb Bot, halb S&P 500 halten, "
                "und für jede Strategie der Schnitt ihrer gedachten Trades (Strategie-Tagebuch) auf den Zufallslisten.")
VERMUTUNG = ("(1) Eine feste Regel für die Watchlist schlägt Zufallslisten. (2) Halb Bot, halb S&P 500 hat mehr Rendite "
             "pro Rückgang als jedes allein. (3) Mindestens eine Strategie hat auf damaligen Aktien einen echten Vorteil.")
WIDERLEGT_WENN = ("(1) Die Regel-Liste bringt nicht in allen drei Zeiträumen mehr Rendite als 7 von 8 Zufallslisten. "
                  "(2) Die Mischung (Mitte der Zufallslisten) hat nicht in allen drei Zeiträumen mehr Rendite pro Rückgang "
                  "als der S&P 500 allein und als der Bot allein. (3) Keine Strategie hat in allen drei Zeiträumen (je "
                  "mindestens 30 Trades) einen höheren Schnitt als zufällige Käufe mit denselben Stop- und Zielabständen.")
VARIANTEN = ("2 Regel-Listen (Umsatz, Stärke), 1 Mischung (50/50), 9 Kauf-Strategien – alles vor dem Rechnen festgelegt. "
             "Bei 9 Strategien kann eine zufällig über 0 liegen – deshalb alle drei Zeiträume.")
N = 24
ZUFALL_NAMEN = {"zufall_trend": "🎲 Zufall mit Trend-Ausstieg (±3 ATR)",
                "zufall_gegen": "🎲 Zufall mit Gegen-Ausstieg (−2,5 / +2 ATR)"}
GEGEN = {"rsi2_long", "gegenbewegung_long"}  # Strategien mit Gegenbewegungs-Ausstieg (Stop 2,5 / Ziel 2 ATR)


def _umsatz_liste(cache, D, T, kand, i):
    tag = T["tage"][i]
    werte = {}
    for t in kand:
        df = D.lies_kurse(cache, t)
        if df is None or "Volume" not in df:
            continue
        idx = pd.DatetimeIndex(df.index)
        df.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize()
        stueck = df[df.index <= tag].tail(63)
        if len(stueck) >= 50:
            werte[t] = float((stueck["Close"] * stueck["Volume"]).mean())
    return sorted(sorted(werte, key=werte.get, reverse=True)[:N])


def _staerke_liste(T, kand, i):
    roh = T["roh"]
    if i < 252:
        return []
    m = {t: roh[t].iloc[i - 21] / roh[t].iloc[i - 252] - 1 for t in kand
         if pd.notna(roh[t].iloc[i - 21]) and pd.notna(roh[t].iloc[i - 252])}
    return sorted(sorted(m, key=m.get, reverse=True)[:N])


def pruefen(P, a, watch, sektor_von):
    R, ROT, D = P.R, P.ROT, P.D
    basis = P.lauf(a.cache, watch, sektor_von, a.laeufe)
    T = ROT.tabellen(a.cache)
    if T["wechsel"] is None:
        T["wechsel"] = ROT.index_wechsel(a.cache)
    importlib.reload(R.sw)
    R.sw.GEBUEHR = float(os.environ.get("GEBUEHR", "0"))
    gemerkt = {"kurven": [], "tagebuch": [], "zufall_tb": []}
    for key, art in (("zufall_trend", "trend"), ("zufall_gegen", "gegen")):  # Vergleich: zufällige Käufe
        R.sw.STRATEGIEN[key] = {"name": f"Zufall ({art})", "richtung": 1, "art": art, "regel": ""}
        R.sw.VORRANG[key] = len(R.sw.VORRANG)
    orig_depot, orig_tb = R.sw.simuliere_depot, R.sw.strategie_tagebuch

    def depot_merken(*x, **k):
        dep = orig_depot(*x, **k)
        gemerkt["kurven"].append(dep["verlauf"])
        return dep

    def tb_merken(daten, einst, *x, **k):
        tb = orig_tb(daten, einst, *x, **k)
        gemerkt["tagebuch"].append(tb)
        gemerkt["zufall_tb"].append(orig_tb(_zufalls_daten(daten, R.sw), einst))
        return tb
    R.sw.simuliere_depot, R.sw.strategie_tagebuch = depot_merken, tb_merken

    def bot(liste, von, bis):
        for v in gemerkt.values():
            v.clear()
        k = R.jetziger_bot(a.cache, liste, sektor_von, von, bis, a.laeufe)
        return k, gemerkt["kurven"][0], gemerkt["tagebuch"][0] + gemerkt["zufall_tb"][0]

    erg = {}
    strat = {}
    try:
        for von, bis in R.ZEITRAEUME.values():
            bis = min(pd.Timestamp(bis), P.ENDE)
            i = int(T["tage"].searchsorted(pd.Timestamp(von))) - 1
            kand = E._kandidaten(ROT, T, i)
            zufall = [sorted(np.random.default_rng([z, T["tage"][i].year]).choice(kand, len(watch), replace=False))
                      for z in range(E.ZIEHUNGEN)]
            spy_kurve = ROT.halten(a.cache, "SPY", von, bis)
            e = {"kandidaten": len(kand), "spy": ROT.kennzahlen(spy_kurve),
                 "qqq": ROT.kennzahlen(ROT.halten(a.cache, "QQQ", von, bis)), "zufall": [], "mix": [], "regel": {}}
            r_je = {}
            for liste in zufall:
                k, kurve, tb = bot(liste, von, bis)
                e["zufall"].append(k)
                e["mix"].append(ROT.kennzahlen(ROT.kombi(kurve, spy_kurve, 0.5)))
                for t in tb:
                    if pd.Timestamp(von) <= _naiv(t["einstieg_tag"]) <= bis:
                        r_je.setdefault(t["strategie"], []).append(t["R"])
            for name, liste in (("umsatz", _umsatz_liste(a.cache, D, T, kand, i)), ("staerke", _staerke_liste(T, kand, i))):
                k, kurve, _ = bot(liste, von, bis)
                e["regel"][name] = {"liste": liste, **k, "mix": ROT.kennzahlen(ROT.kombi(kurve, spy_kurve, 0.5))}
            strat[von] = {s: {"n": len(v), "schnitt": float(np.mean(v))} for s, v in r_je.items()}
            erg[von] = e
            print(f"{von}: Zufall Mitte {np.median([z['rendite'] for z in e['zufall']]):+.1f} %, "
                  f"Umsatz {e['regel']['umsatz']['rendite']:+.1f} %, Stärke {e['regel']['staerke']['rendite']:+.1f} %")
    finally:
        importlib.reload(R.sw)
    text, ergebnis = _urteil(basis, erg, strat)
    plus = {v: ergebnis["regel_plus"][v] for v in basis}
    return text, plus, {"basis": basis, "zeitraeume": erg, "strategien": strat, "urteil_teile": ergebnis}, \
        _markdown(P, basis, erg, strat, text, ergebnis, R.sw)


def _zufalls_daten(daten, sw):
    """Kopie der Daten, in der nur zwei Zufalls-Strategien feuern (an je etwa 3 % der Tage): mit Trend-Ausstieg
    (über der 50-Tage-Linie, Stop/Ziel ±3 ATR) und mit Gegenbewegungs-Ausstieg (über der 200-Tage-Linie, Stop −2,5 /
    Ziel +2 ATR). Ihr Schnitt zeigt, was ein beliebiger Kauf mit denselben Ausstiegen am selben Markt verdient."""
    neu = {}
    for t, d in daten.items():
        c, atr = np.asarray(d["C"], float), np.asarray(d["ATR"], float)
        sma50, sma200 = (d["df"][k].to_numpy(float) for k in ("SMA_50", "SMA_200"))
        rng = np.random.default_rng(sum(map(ord, t)))
        ok = np.isfinite(atr) & (atr > 0)
        trend = ok & (rng.random(len(c)) < 0.03) & (c > sma50)
        gegen = ok & (rng.random(len(c)) < 0.03) & (c > sma200)
        neu[t] = {**d, "signale": {"zufall_trend": (trend, c - sw.STOP_TREND_ATR * atr, c + sw.ZIEL_TREND_ATR * atr),
                                   "zufall_gegen": (gegen, c - sw.STOP_GEGEN_ATR * atr, c + sw.ZIEL_GEGEN_ATR * atr)}}
    return neu


def _naiv(tag):
    tag = pd.Timestamp(tag)
    return tag.tz_localize(None) if tag.tz is not None else tag


def _q(e):
    return e["rendite"] / max(e["rueckgang"], 0.1)


def _urteil(basis, erg, strat):
    vs = list(basis)
    regel_ok = {}
    for name in ("umsatz", "staerke"):
        regel_ok[name] = all(sum(z["rendite"] < erg[v]["regel"][name]["rendite"] for z in erg[v]["zufall"]) >= 7
                             for v in vs)
    mix_mitte = {v: {k: float(np.median([m[k] for m in erg[v]["mix"]])) for k in ("rendite", "rueckgang")} for v in vs}
    bot_mitte = {v: {k: float(np.median([z[k] for z in erg[v]["zufall"]])) for k in ("rendite", "rueckgang")} for v in vs}
    mix_ok = all(_q(mix_mitte[v]) > _q(erg[v]["spy"]) and _q(mix_mitte[v]) > _q(bot_mitte[v]) for v in vs)
    alle = sorted({s for v in vs for s in strat[v]} - {"zufall_trend", "zufall_gegen"})
    vergleich = lambda s, v: strat[v].get("zufall_gegen" if s in GEGEN else "zufall_trend", {"schnitt": np.inf})["schnitt"]  # noqa: E731
    echt = [s for s in alle if all(s in strat[v] and strat[v][s]["n"] >= 30 and strat[v][s]["schnitt"] > vergleich(s, v)
                                   for v in vs)]
    teile = [("Watchlist nach Umsatz", regel_ok["umsatz"]), ("Watchlist nach Stärke", regel_ok["staerke"]),
             ("halb Bot, halb S&P 500", mix_ok)]
    text = "; ".join(f"{n}: {'besteht' if ok else 'besteht nicht'}" for n, ok in teile)
    text += "; Strategien mit echtem Vorteil: " + (", ".join(echt) if echt else "keine")
    beste = max(("umsatz", "staerke"), key=lambda n: sum(erg[v]["regel"][n]["rendite"] for v in vs))
    return text, {"regel_ok": regel_ok, "mix_ok": mix_ok, "echt": echt, "mix_mitte": mix_mitte, "bot_mitte": bot_mitte,
                  "regel_plus": {v: erg[v]["regel"][beste]["rendite"] - bot_mitte[v]["rendite"] for v in vs}}


def _markdown(P, basis, erg, strat, text, u, sw):
    import datetime as dt
    vs = list(basis)
    f = lambda e: f"{e['rendite']:+.1f} % / −{e['rueckgang']:.0f} % ({_q(e):.2f})".replace(".", ",")  # noqa: E731
    kopf = ["| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang) | " + " | ".join(P.R.ZEITRAEUME) + " |",
            "|---|" + "---:|" * len(vs)]
    zeile = lambda titel, werte: "| " + titel + " | " + " | ".join(werte) + " |"  # noqa: E731

    def spanne(liste, k="rendite"):
        r = [x[k] for x in liste]
        return f"{min(r):+.1f} bis {max(r):+.1f} %".replace(".", ",")
    z = [f"# 🔬 {NAME}", "", f"Getestet am {dt.date.today():%d.%m.%Y} · {QUELLE}", "", BESCHREIBUNG, "",
         f"- **Vermutung:** {VERMUTUNG}", f"- **Widerlegt, wenn:** {WIDERLEGT_WENN}", f"- **Varianten:** {VARIANTEN}",
         "", f"**Ergebnis:** {text}", "", "## 1. Watchlist nach fester Regel", ""] + kopf + [
        zeile("Bot mit der heutigen Watchlist (Rückblick!)", [f(basis[v]) for v in vs]),
        zeile("Bot mit 24 zufälligen damaligen Aktien (Mitte aus 8)", [f(u["bot_mitte"][v]) for v in vs]),
        zeile("… Spanne der 8 Zufallslisten", [spanne(erg[v]["zufall"]) for v in vs]),
        zeile("**Bot mit den 24 meistgehandelten**", [f(erg[v]["regel"]["umsatz"]) for v in vs]),
        zeile("**Bot mit den 24 stärksten (12 Monate)**", [f(erg[v]["regel"]["staerke"]) for v in vs]),
        zeile("S&P 500 halten", [f(erg[v]["spy"]) for v in vs]),
        zeile("Nasdaq-100 halten", [f(erg[v]["qqq"]) for v in vs]),
        "", "Regel-Listen am Start: " + " · ".join(
            f"{n} {v[:4]}: {', '.join(erg[v]['regel'][k]['liste'])}" for k, n in (("umsatz", "Umsatz"), ("staerke", "Stärke"))
            for v in vs),
        "", "## 2. Halb Bot, halb S&P 500 halten", ""] + kopf + [
        zeile("Bot allein (Zufallslisten, Mitte)", [f(u["bot_mitte"][v]) for v in vs]),
        zeile("S&P 500 allein", [f(erg[v]["spy"]) for v in vs]),
        zeile("**Halb Bot (Zufallslisten), halb S&P 500 (Mitte)**", [f(u["mix_mitte"][v]) for v in vs]),
        zeile("Halb Bot (meistgehandelte), halb S&P 500", [f(erg[v]["regel"]["umsatz"]["mix"]) for v in vs]),
        "", "## 3. Strategien auf zufälligen damaligen Aktien (gedachte Trades, Ø R nach Kosten)", "",
        "Vergleich: „Zufall (trend)“ und „Zufall (gegen)“ kaufen an zufälligen Tagen mit denselben Stop- und Zielabständen. "
        "Echter Vorteil = in allen drei Zeiträumen mehr als der passende Zufall (je mindestens 30 Trades).", "",
        "| Strategie | " + " | ".join(P.R.ZEITRAEUME) + " | echter Vorteil? |", "|---|" + "---:|" * len(vs) + "---|"]
    for s in sorted({s for v in vs for s in strat[v]}, key=lambda s: -sum(strat[v].get(s, {"schnitt": 0})["schnitt"] for v in vs)):
        werte = [f"{strat[v][s]['schnitt']:+.2f} R ({strat[v][s]['n']})".replace(".", ",") if s in strat[v] else "–" for v in vs]
        name = ZUFALL_NAMEN.get(s) or (sw.strategie_name(s) if s in sw.STRATEGIEN else s)
        z.append(f"| {name} | " + " | ".join(werte)
                 + f" | {'Vergleich' if s in ZUFALL_NAMEN else '✅' if s in u['echt'] else '–'} |")
    z += ["", "In Klammern: Zahl der gedachten Trades über alle 8 Zufallslisten. Verbleibende Verzerrung: Aktien, die "
          "seitdem aus dem Index geflogen sind, haben meist keine Kurse mehr und fehlen – eher noch etwas zu gut. "
          "Simulation, keine Anlageberatung."]
    return "\n".join(z) + "\n"
