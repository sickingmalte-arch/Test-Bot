"""Nachtest (06.11.2026): Im ehrlichen Check 2 schlug als einzige von 9 Strategien „Gegenbewegung ↑“ zufällige Käufe
mit denselben Stop- und Zielabständen – in allen drei Zeiträumen. Bei 9 Strategien kann eine davon Glück sein. Deshalb
hier dieselbe Prüfung auf NEUEN Zufallslisten (andere Aktien aus dem damaligen S&P 500), dazu die Frage, ob ein Bot nur
mit dieser Strategie besser ist als der volle Bot. Nur eine Messung: Am Bot ändert sich nichts."""
import importlib
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot_ehrliche_aktienliste as E  # noqa: E402
import ehrlicher_check_2 as C2  # noqa: E402

NAME = "Nachtest Gegenbewegung: auf neuen Zufallslisten besser als Zufallskäufe? Und ein Bot nur mit ihr?"
QUELLE = "Ehrlicher Check 2 vom 06.11.2026 (einzige Strategie mit Vorteil gegen Zufallskäufe)"
BESCHREIBUNG = ("Zu Beginn jedes Zeitraums 8 neue Zufallslisten mit je 24 Aktien, die damals im S&P 500 waren (andere "
                "Ziehungen als im Check 2). Mit jeder Liste: der volle Bot und ein Bot, der nur „Gegenbewegung ↑“ handelt "
                "(RSI 14 unter 32 oder am unteren Bollinger-Band, über der 200-Tage-Linie, mindestens 1,2 ATR unter der "
                "EMA 20; Stop −2,5 ATR, Ziel +2 ATR). Dazu der Schnitt ihrer gedachten Trades gegen zufällige Käufe mit "
                "denselben Abständen.")
VERMUTUNG = ("Gegenbewegung schlägt auch auf neuen Aktien in allen drei Zeiträumen zufällige Käufe, und ein Bot nur mit ihr "
             "hat mehr Rendite pro Rückgang als der volle Bot.")
WIDERLEGT_WENN = ("Gegenbewegung liegt in einem Zeitraum nicht über dem Zufall mit Gegen-Ausstieg (je mindestens 30 Trades), "
                  "oder der Bot nur mit ihr hat in einem Zeitraum (Mitte der 8 Listen) nicht mehr Rendite pro Rückgang als "
                  "der volle Bot.")
VARIANTEN = "1 Strategie, 1 Nachtest – vor dem Rechnen festgelegt."
SEEDS = range(100, 108)  # andere Ziehungen als im Check 2 (dort 0–7)
NUR = "gegenbewegung_long"


def pruefen(P, a, watch, sektor_von):
    R, ROT = P.R, P.ROT
    T = ROT.tabellen(a.cache)
    if T["wechsel"] is None:
        T["wechsel"] = ROT.index_wechsel(a.cache)
    importlib.reload(R.sw)
    R.sw.GEBUEHR = float(os.environ.get("GEBUEHR", "0"))
    for key, art in (("zufall_trend", "trend"), ("zufall_gegen", "gegen")):
        R.sw.STRATEGIEN[key] = {"name": f"Zufall ({art})", "richtung": 1, "art": art, "regel": ""}
        R.sw.VORRANG[key] = len(R.sw.VORRANG)
    zustand = {"nur": False, "tb": []}
    orig_vor, orig_tb = R.sw.bereite_vor, R.sw.strategie_tagebuch

    def vor(*x, **k):
        d = orig_vor(*x, **k)
        if zustand["nur"]:
            d["signale"] = {k2: v for k2, v in d["signale"].items() if k2 == NUR}
        return d

    def tb_merken(daten, einst, *x, **k):
        tb = orig_tb(daten, einst, *x, **k)
        if not zustand["nur"]:
            zustand["tb"].append(orig_tb(C2._zufalls_daten(daten, R.sw), einst) + tb)
        return tb
    R.sw.bereite_vor, R.sw.strategie_tagebuch = vor, tb_merken
    erg = {}
    try:
        for von, bis in R.ZEITRAEUME.values():
            bis = min(pd.Timestamp(bis), P.ENDE)
            i = int(T["tage"].searchsorted(pd.Timestamp(von))) - 1
            kand = E._kandidaten(ROT, T, i)
            e = {"voll": [], "nur": [], "spy": ROT.kennzahlen(ROT.halten(a.cache, "SPY", von, bis)), "r": {}}
            for z in SEEDS:
                liste = sorted(np.random.default_rng([z, T["tage"][i].year]).choice(kand, len(watch), replace=False))
                zustand["nur"], zustand["tb"] = False, []
                e["voll"].append(R.jetziger_bot(a.cache, liste, sektor_von, von, bis, a.laeufe))
                for t in zustand["tb"][0]:
                    if pd.Timestamp(von) <= C2._naiv(t["einstieg_tag"]) <= bis:
                        e["r"].setdefault(t["strategie"], []).append(t["R"])
                zustand["nur"] = True
                e["nur"].append(R.jetziger_bot(a.cache, liste, sektor_von, von, bis, a.laeufe))
            e["r"] = {s: {"n": len(v), "schnitt": float(np.mean(v))} for s, v in e["r"].items()}
            erg[von] = e
            print(f"{von}: voll {np.median([x['rendite'] for x in e['voll']]):+.1f} %, nur Gegenbewegung "
                  f"{np.median([x['rendite'] for x in e['nur']]):+.1f} %")
    finally:
        importlib.reload(R.sw)
    vs = list(erg)
    mitte = lambda lst: {k: float(np.median([x[k] for x in lst])) for k in ("rendite", "rueckgang", "treffer", "trades_jahr")}  # noqa: E731
    voll, nur = {v: mitte(erg[v]["voll"]) for v in vs}, {v: mitte(erg[v]["nur"]) for v in vs}
    gegen_ok = all(erg[v]["r"].get(NUR, {"n": 0})["n"] >= 30 and erg[v]["r"][NUR]["schnitt"]
                   > erg[v]["r"].get("zufall_gegen", {"schnitt": np.inf})["schnitt"] for v in vs)
    bot_ok = all(C2._q(nur[v]) > C2._q(voll[v]) for v in vs)
    text = (f"Gegenbewegung gegen Zufallskäufe auf neuen Listen: {'besteht' if gegen_ok else 'besteht nicht'}; "
            f"Bot nur mit Gegenbewegung besser als der volle Bot: {'ja' if bot_ok else 'nein'}")
    plus = {v: nur[v]["rendite"] - voll[v]["rendite"] for v in vs}
    return text, plus, {"basis": voll, "nur_gegenbewegung": nur, "zeitraeume": erg}, \
        _markdown(P, erg, voll, nur, text)


def _markdown(P, erg, voll, nur, text):
    import datetime as dt
    vs = list(erg)
    f = lambda e: f"{e['rendite']:+.1f} % / −{e['rueckgang']:.0f} % ({C2._q(e):.2f})".replace(".", ",")  # noqa: E731
    z = [f"# 🔬 {NAME}", "", f"Getestet am {dt.date.today():%d.%m.%Y} · {QUELLE}", "", BESCHREIBUNG, "",
         f"- **Vermutung:** {VERMUTUNG}", f"- **Widerlegt, wenn:** {WIDERLEGT_WENN}", f"- **Varianten:** {VARIANTEN}",
         "", f"**Ergebnis:** {text}", "",
         "| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang), Mitte aus 8 neuen Listen | "
         + " | ".join(P.R.ZEITRAEUME) + " |", "|---|" + "---:|" * len(vs),
         "| Voller Bot (9 Strategien) | " + " | ".join(f(voll[v]) for v in vs) + " |",
         "| **Bot nur mit Gegenbewegung** | " + " | ".join(f(nur[v]) for v in vs) + " |",
         "| S&P 500 halten | " + " | ".join(f(erg[v]["spy"]) for v in vs) + " |",
         "| Trades pro Jahr (voll / nur Gegenbewegung) | " + " | ".join(
             f"{voll[v]['trades_jahr']:.0f} / {nur[v]['trades_jahr']:.0f}" for v in vs) + " |",
         "", "| Gedachte Trades (Ø R nach Kosten) | " + " | ".join(P.R.ZEITRAEUME) + " |", "|---|" + "---:|" * len(vs)]
    for s, name in ((NUR, "Gegenbewegung ↑"), ("zufall_gegen", "🎲 Zufall mit Gegen-Ausstieg"),
                    ("zufall_trend", "🎲 Zufall mit Trend-Ausstieg")):
        z.append(f"| {name} | " + " | ".join(
            f"{erg[v]['r'][s]['schnitt']:+.2f} R ({erg[v]['r'][s]['n']})".replace(".", ",") if s in erg[v]["r"] else "–"
            for v in vs) + " |")
    z += ["", "Neue Zufallslisten (andere Aktien als im Check 2). Verbleibende Verzerrung: Aktien, die seitdem aus dem "
          "Index geflogen sind, fehlen. Simulation, keine Anlageberatung."]
    return "\n".join(z) + "\n"
