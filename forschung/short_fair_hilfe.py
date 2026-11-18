"""Fairer Short-Test auf Aktien, die man damals ohne Rückblick hätte wählen können (Wunsch des Nutzers vom
17./18.11.2026: „Es muss doch einen Weg geben, Shorts profitabel zu machen“).

Bisher liefen alle Short-Tests mit der heutigen Watchlist – lauter Aktien, die im Rückblick stark gestiegen sind. Auf
deren Fallen zu wetten, muss fast zwangsläufig verlieren. Hier handelt der Bot stattdessen mit denselben 8 Zufallslisten
aus dem damaligen S&P 500 wie im ehrlichen Bot-Check vom 06.11.2026 (je Zeitraum am Abend vor dem Start gezogen, so viele
Aktien wie die Watchlist hat). Je Liste rechnet er den jetzigen Bot (nur Long) und denselben Bot mit einer
Short-Variante, mit Gebühr und Spread wie immer.

Urteil je Variante (vor dem Rechnen festgelegt) – besser nur, wenn in jedem der drei Zeiträume
  - der Median über die 8 Listen mehr Rendite pro Jahr bringt als der Bot nur mit Long,
  - mindestens 6 von 8 Listen mehr Rendite bringen,
  - der größte Rückgang im Median höchstens 1 Punkt größer ist,
  - es mindestens 30 Short-Trades gibt (alle Listen zusammen; darunter keine Aussage) und
  - die Variante die beste von 6 Gegenproben schlägt (je Aktie und Strategie gleich viele Shorts an zufälligen
    erlaubten Tagen, gleicher Stop und gleiches Ziel).
Die 6 Gegenproben laufen nur, wenn eine Variante die ersten vier Punkte schafft; sonst laufen 2 zum Vergleich.

Verbleibende Verzerrung: Zur Wahl stehen nur Aktien, die heute noch im S&P 500 oder Nasdaq-100 sind (für die anderen
fehlen Kurse). Pleitefirmen und abgestürzte Verlierer fehlen also – genau die Aktien, an denen Shorts verdient hätten.
Für Shorts ist das Ergebnis deshalb eher noch zu schlecht. Leihgebühren rechnet der Bot nicht (bei großen US-Aktien
meist unter 0,5 % pro Jahr)."""
import datetime as dt
import hashlib
import importlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "ideen"))
import bot_ehrliche_aktienliste as E  # noqa: E402  (gleiche Zufallslisten wie im Check vom 06.11.)

MIN_SHORTS = 30           # unter 30 Short-Trades je Zeitraum (alle Listen zusammen) keine Aussage
MEHRHEIT = 6              # so viele der 8 Listen müssen besser sein
VERGLEICH_SEEDS = 2       # Gegenproben nur zum Vergleich, wenn eine Variante schon vorher scheitert
VERGLEICH_FRIST = 45 * 60  # danach keine Vergleichs-Gegenproben mehr (Zeitgrenze des Ablaufs auf GitHub)


# ----------------------------------------------------------------------------
# Listen und Läufe
# ----------------------------------------------------------------------------
def listen(P, a, n):
    """Je Zeitraum die 8 Zufallslisten aus dem damaligen S&P 500 – genau wie im ehrlichen Bot-Check vom 06.11."""
    R, ROT = P.R, P.ROT
    T = ROT.tabellen(a.cache)
    if T["wechsel"] is None:
        T["wechsel"] = ROT.index_wechsel(a.cache)
    aus = {}
    for von, bis in R.ZEITRAEUME.values():
        i = int(T["tage"].searchsorted(pd.Timestamp(von))) - 1  # Abend vor dem Start
        kand = E._kandidaten(ROT, T, i)
        gezogen = [np.random.default_rng([z, T["tage"][i].year]).choice(kand, n, replace=False)
                   for z in range(E.ZIEHUNGEN)]
        aus[von] = {"bis": min(pd.Timestamp(bis), P.ENDE), "kandidaten": len(kand),
                    "listen": [sorted(str(t) for t in liste) for liste in gezogen]}
    return aus


def _mit_variante(P, anpassen):
    """Bot frisch laden, Variante anwenden und jeden Depot-Lauf mitschreiben (für die Short-Trades)."""
    R = P.R
    importlib.reload(R.sw)
    R.sw.GEBUEHR = float(os.environ.get("GEBUEHR", "0"))
    if anpassen:
        anpassen(R.sw)
    gemerkt = []
    original = R.sw.simuliere_depot

    def merken(*x, **k):
        dep = original(*x, **k)
        gemerkt.append(dep)
        return dep
    R.sw.simuliere_depot = merken
    return gemerkt


def _lauf(P, a, sektor_von, gemerkt, liste, von, bis):
    """Kennzahlen des Bots mit einer Liste plus die Short-Trades (Mittel je Lauf)."""
    gemerkt.clear()
    k = P.R.jetziger_bot(a.cache, liste, sektor_von, von, bis, a.laeufe)
    von_ts = pd.Timestamp(von)
    kurz = [t for dep in gemerkt for t in dep["trades"] if t["richtung"] < 0 and t["kauf_tag"] >= von_ts]
    n = max(len(gemerkt), 1)
    g = [t["erloes"] - t["kosten"] for t in kurz]
    r = [x / t["risiko_eur"] if t["risiko_eur"] > 0 else 0.0 for x, t in zip(g, kurz)]
    return {**k, "shorts": len(kurz) / n, "short_summe_r": float(np.sum(r)) / n,
            "short_gewinner": float(sum(x > 0 for x in g)) / n, "short_euro": float(np.sum(g)) / n}


def alle_listen(P, a, sektor_von, zr, anpassen):
    """Bot mit Variante (oder ohne: anpassen=None) auf allen Listen aller Zeiträume."""
    gemerkt = _mit_variante(P, anpassen)
    try:
        return {von: [_lauf(P, a, sektor_von, gemerkt, liste, von, z["bis"]) for liste in z["listen"]]
                for von, z in zr.items()}
    finally:
        importlib.reload(P.R.sw)


def nur_long(P, a, sektor_von, zr):
    """Der Bot nur mit Long auf allen Listen – einmal gerechnet und im Zwischenspeicher des Ablaufs gemerkt, damit
    die Short-Ideen desselben Laufs ihn nicht jede neu rechnen."""
    schluessel = json.dumps({"listen": {v: z["listen"] for v, z in zr.items()}, "laeufe": a.laeufe,
                             "gebuehr": os.environ.get("GEBUEHR", "0"), "ende": str(P.ENDE)}, sort_keys=True)
    pfad = os.path.join(a.cache, f"short_fair_long_{hashlib.sha256(schluessel.encode()).hexdigest()[:16]}.json")
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        pass
    lang = alle_listen(P, a, sektor_von, zr, None)
    try:
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(lang, f)
    except OSError:
        pass
    return lang


# ----------------------------------------------------------------------------
# Bausteine für Short-Varianten
# ----------------------------------------------------------------------------
def _verteilen(feuert, ok, seed):
    """Gleich viele Signale wie in feuert, aber an zufälligen erlaubten Tagen (Gegenprobe)."""
    anzahl, frei = int(np.sum(feuert)), np.flatnonzero(ok)
    neu = np.zeros(len(feuert), bool)
    if anzahl and len(frei):
        neu[np.random.default_rng(seed).choice(frei, min(anzahl, len(frei)), replace=False)] = True
    return neu


def alte_shorts(sw, maske=None, marktfilter=True, seed=None):
    """Schaltet die 8 alten Short-Strategien ein (wie MIT_SHORT im Bot). maske(ticker, d) -> bool je Tag: nur dann
    Short. marktfilter=False: auch im Aufwärtsmarkt. seed: je Aktie und Strategie gleich viele Shorts an zufälligen
    erlaubten Tagen (Gegenprobe). Ohne maske, mit Marktfilter und ohne seed ist das genau der Bot mit Shorts."""
    sw.MIT_SHORT = True
    if maske is None and marktfilter and seed is None:
        return
    original = sw.bereite_vor
    kurz = [k for k, s in sw.STRATEGIEN.items() if s["richtung"] < 0]

    def neu(ticker, df, fx, zahlen_df, einst, markt=None):
        d = original(ticker, df, fx, zahlen_df, einst, markt)
        c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
        n = len(c)
        erlaubt = np.ones(n, bool)
        if marktfilter and markt is not None and getattr(einst, "marktfilter", True):
            erlaubt = np.asarray(sw.markt_vortag(markt, d["idx"]) != 1, dtype=bool)  # wie im Bot (NaN sperrt nicht)
        m = np.ones(n, bool) if maske is None else np.asarray(maske(ticker, d), dtype=bool)[:n]
        neu_sig = {}
        for key in kurz:
            if key not in d["signale_roh"]:
                continue
            feuert, stop, ziel = d["signale_roh"][key]
            stop, ziel = np.asarray(stop, dtype=float), np.asarray(ziel, dtype=float)
            f = np.asarray(feuert, dtype=bool) & erlaubt & m
            if seed is not None:
                with np.errstate(invalid="ignore"):
                    ok = (erlaubt & np.isfinite(atr) & (stop > c) & (ziel < c) & (ziel > 0)
                          & (np.arange(n) >= sw.MIN_KERZEN - 1))
                f = _verteilen(f, ok, [seed, sum(map(ord, ticker)), sum(map(ord, key))])
            neu_sig[key] = (f, stop, ziel)
        d["signale"].update(neu_sig)
        return d
    sw.bereite_vor = neu


def tage_maske(d, ereignisse):
    """bool je Kurstag: an diesem Tag ist bis zum Börsenschluss ein Ereignis bekannt geworden. ereignisse: {Ticker:
    sortierte Tage, ab denen es bekannt ist}; Wochenende und Feiertag rutschen auf den nächsten Handelstag."""
    n = len(d["C"])
    aus = np.zeros(n, bool)
    tage = ereignisse.get(d["ticker"])
    if tage is None or not len(tage):
        return aus
    idx = pd.DatetimeIndex(d["idx"])
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    idx = idx.normalize()[:n]
    tage = pd.DatetimeIndex(tage)
    pos = idx.searchsorted(tage[tage >= idx[0]]) if n else np.array([], int)
    aus[pos[pos < n]] = True
    return aus


# ----------------------------------------------------------------------------
# Urteil und Bericht
# ----------------------------------------------------------------------------
def _stufe1(lang, werte):
    je = {}
    for von in lang:
        dr = [w["rendite"] - b["rendite"] for b, w in zip(lang[von], werte[von])]
        dd = [w["rueckgang"] - b["rueckgang"] for b, w in zip(lang[von], werte[von])]
        je[von] = {"plus": float(np.median(dr)), "besser": int(sum(x > 0 for x in dr)), "tiefer": float(np.median(dd)),
                   "shorts": float(sum(w["shorts"] for w in werte[von]))}
    besser = all(x["plus"] > 0 and x["besser"] >= MEHRHEIT and x["tiefer"] <= 1 for x in je.values())
    genug = all(x["shorts"] >= MIN_SHORTS for x in je.values())
    return {"je": je, "besser": besser, "genug": genug, "ok": besser and genug}


def _mitte(werte, k="rendite"):
    return float(np.median([w[k] for w in werte]))


def _urteil(lang, e, voll):
    s = e["stufe1"]
    if not s["besser"]:
        return "nicht überall besser"
    if not s["genug"]:
        return "keine Aussage (unter 30 Short-Trades in einem Zeitraum)"
    if len(e["zufall"]) < voll:
        return "überall besser, aber Gegenprobe fehlt"
    if all(_mitte(e["werte"][v]) > max(_mitte(z[v]) for z in e["zufall"]) for v in lang):
        return "überall besser, auch besser als Zufall"
    return "überall besser, aber nicht besser als Zufall"


def _short_kennzahlen(werte, jahre, listen):
    n = sum(w["shorts"] for w in werte)
    return {"je_jahr": n / max(jahre, 1e-9) / max(listen, 1), "anzahl": n,
            "treffer": 100 * sum(w["short_gewinner"] for w in werte) / n if n else float("nan"),
            "schnitt_r": sum(w["short_summe_r"] for w in werte) / n if n else float("nan")}


def pruefen(P, a, sektor_von, idee, zr, varianten, n_aktien, extra_md=""):
    """Rechnet den Bot nur mit Long und jede Variante auf allen Listen, dazu Gegenproben.
    varianten: [{"key", "kurz", "name", "anpassen": f(sw), "zufall": f(sw, seed)}]. Gibt (text, plus, mehr, md) für
    den Prüfstand zurück."""
    t0 = time.time()
    lang = nur_long(P, a, sektor_von, zr)
    print("Bot nur Long: " + ", ".join(f"{v} {_mitte(lang[v]):+.1f} %" for v in lang))
    erg = {}
    for v in varianten:
        e = {"werte": alle_listen(P, a, sektor_von, zr, v["anpassen"]), "zufall": []}
        e["stufe1"] = _stufe1(lang, e["werte"])
        seeds = P.ZUFALL_LAEUFE if e["stufe1"]["ok"] else (
            VERGLEICH_SEEDS if time.time() - t0 < VERGLEICH_FRIST else 0)
        for s in range(seeds if v.get("zufall") else 0):
            e["zufall"].append(alle_listen(P, a, sektor_von, zr, lambda sw, s=s, f=v["zufall"]: f(sw, s)))
        e["urteil"] = _urteil(lang, e, P.ZUFALL_LAEUFE)
        erg[v["key"]] = e
        print(f"{v['kurz']}: {e['urteil']} – " + ", ".join(
            f"{von} {x['plus']:+.1f} Punkte, {x['besser']}/{len(zr[von]['listen'])} besser, {x['shorts']:.0f} Shorts"
            for von, x in e["stufe1"]["je"].items()) + f" ({time.time() - t0:.0f} s)")
    text = "; ".join(f"{v['kurz']}: {erg[v['key']]['urteil']}" for v in varianten)
    mit_shorts = [v for v in varianten if all(x["shorts"] > 0 for x in erg[v["key"]]["stufe1"]["je"].values())]
    beste = max(mit_shorts or varianten,
                key=lambda v: min(x["plus"] for x in erg[v["key"]]["stufe1"]["je"].values()))
    plus = {von: erg[beste["key"]]["stufe1"]["je"][von]["plus"] for von in lang}
    basis = {von: {k: _mitte(lang[von], k) for k in lang[von][0]} for von in lang}
    mehr = {"basis": basis, "beste_variante": beste["key"], "nur_long": lang,
            "listen": {von: z["listen"] for von, z in zr.items()},
            "varianten": {v["key"]: {"name": v["name"], "urteil": erg[v["key"]]["urteil"],
                                     "stufe1": erg[v["key"]]["stufe1"], "werte": erg[v["key"]]["werte"],
                                     "zufall_mitte": [{von: _mitte(z[von]) for von in lang}
                                                      for z in erg[v["key"]]["zufall"]]}
                          for v in varianten}}
    return text, plus, mehr, markdown(P, idee, zr, lang, erg, varianten, text, n_aktien, extra_md)


def markdown(P, idee, zr, lang, erg, varianten, text, n_aktien, extra_md=""):
    R = P.R
    vs = list(lang)
    jahre = {v: (zr[v]["bis"] - pd.Timestamp(v)).days / 365.25 for v in vs}
    zahl = lambda x, st=1: "–" if not np.isfinite(x) else f"{x:+.{st}f}".replace(".", ",")  # noqa: E731
    kz = lambda werte: f"{_mitte(werte):+.1f} % / −{_mitte(werte, 'rueckgang'):.0f} %".replace(".", ",")  # noqa: E731

    def shorts_zeile(werte, v):
        s = _short_kennzahlen(werte, jahre[v], len(werte))
        if not s["anzahl"]:
            return "keine Shorts"
        return (f"{s['je_jahr']:.1f}".replace(".", ",") + f" · {s['treffer']:.0f} % · {zahl(s['schnitt_r'], 2)} R")

    def zufall_r(zufall, v):
        s = _short_kennzahlen([w for zz in zufall for w in zz[v]], jahre[v], 1)
        return f"{zahl(s['schnitt_r'], 2)} R" if s["anzahl"] else "keine Shorts"

    anzahl = len(zr[vs[0]]["listen"])
    kopf = "| | " + " | ".join(R.ZEITRAEUME) + " |"
    z = [f"# 🔬 {idee.NAME}", "", f"Getestet am {dt.date.today():%d.%m.%Y} · Quelle: {getattr(idee, 'QUELLE', '–')}", "",
         idee.BESCHREIBUNG, "", f"- **Vermutung:** {idee.VERMUTUNG}", f"- **Widerlegt, wenn:** {idee.WIDERLEGT_WENN}",
         f"- **Varianten:** {idee.VARIANTEN}", "", f"**Ergebnis: {text}**", "",
         f"Je Zeitraum {anzahl} Zufallslisten mit je {n_aktien} Aktien aus dem damaligen S&P 500 (zur Wahl standen "
         + ", ".join(f"{k}: {zr[v]['kandidaten']}" for k, v in zip(R.ZEITRAEUME, vs))
         + f" Aktien). Werte: Mitte (Median) der {anzahl} Listen, Rendite pro Jahr / größter Rückgang.", "",
         kopf, "|---|" + "---:|" * len(vs),
         "| Bot nur Long (wie heute) | " + " | ".join(kz(lang[v]) for v in vs) + " |"]
    for var in varianten:
        e = erg[var["key"]]
        je = e["stufe1"]["je"]
        z += [f"| **{var['kurz']}: {var['name']}** | " + " | ".join(kz(e["werte"][v]) for v in vs) + " |",
              "| … Unterschied zum Bot (Mitte, Punkte) · Listen besser | " + " | ".join(
                  f"{zahl(je[v]['plus'])} · {je[v]['besser']} von {anzahl}" for v in vs) + " |",
              "| … Shorts pro Jahr je Liste · Treffer · Ø Ergebnis je Short | " + " | ".join(
                  shorts_zeile(e["werte"][v], v) for v in vs) + " |"]
        if e["zufall"]:
            z.append(f"| … Gegenprobe: gleich viele Shorts an Zufallstagen (beste von {len(e['zufall'])}) · Ø je Short | "
                     + " | ".join(
                         f"{max(_mitte(zz[v]) for zz in e['zufall']):+.1f} %".replace(".", ",") + " · "
                         + zufall_r(e["zufall"], v) for v in vs) + " |")
    z += ["", "**Urteile:**", ""] + [f"- **{var['kurz']}** ({var['name']}): {erg[var['key']]['urteil']}"
                                     for var in varianten]
    if extra_md:
        z += ["", extra_md]
    z += ["", "So gelesen: „Ø Ergebnis je Short“ ist der Gewinn oder Verlust eines Shorts nach Spread und Gebühr in R "
          "(1 R = der geplante Verlust bis zum Stop). Unter 0 R kostet jeder Short im Schnitt Geld.", "",
          "Verbleibende Verzerrung: Zur Wahl stehen nur Aktien, die heute noch im S&P 500 oder Nasdaq-100 sind – "
          "Pleitefirmen und abgestürzte Verlierer fehlen, also genau die Aktien, an denen Shorts verdient hätten. Für "
          "Shorts ist das Ergebnis deshalb eher noch zu schlecht. Leihgebühren für Shorts sind nicht abgezogen. "
          "Simulation mit Spielgeld, keine Anlageberatung."]
    return "\n".join(z) + "\n"
