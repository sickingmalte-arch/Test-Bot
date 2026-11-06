"""Prüfstand des Forschungs-Bots: testet eine Idee aus forschung/ideen/<name>.py ehrlich gegen den jetzigen Bot.

Gleicher Test wie bei allen früheren Ideen (gehirn/Notizen/Was der Bot schon weiß.md): echter Bot auf der Watchlist,
2010–2014, 2015–2021 und 2022–2026, mit Gebühr und Spread, mehrere Läufe mit gemischter Reihenfolge der Aktien.

Eine Idee ist eine kleine Python-Datei mit
  NAME = "kurzer Name", QUELLE = "Link", BESCHREIBUNG = "in einfachen Worten"
  def anpassen(sw): ...            # verändert den Bot (Modul swing_scanner) nur für den Test
  def gegenprobe(sw, seed): ...    # optional: dieselbe Art Änderung, aber zufällig (z. B. zufällige Aktien zuerst)
Statt anpassen kann eine Idee auch ein EIGENES DEPOT sein (andere Art Strategie, z. B. einmal im Monat umschichten):
  def depot(cache, von, bis): ...          # Wertverlauf in Euro (siehe forschung/rotation.py)
  def zufall(cache, von, bis, seed): ...   # optional: dieselbe Regel mit zufällig gewählten Aktien
  KOMBI_BOT = 0.5                          # optional: halb Swing-Bot, halb eigenes Depot
  VERMUTUNG, WIDERLEGT_WENN, VARIANTEN     # vor dem Rechnen festgelegt (siehe CLAUDE.md)
Oder ein eigener Prüfablauf: def pruefen(P, a, watch, sektor_von) -> (urteil, plus, mehr, markdown), P = dieses Modul.
Ein eigenes Depot besteht nur, wenn es in allen drei Zeiträumen mehr Rendite pro Rückgang bringt als der Swing-Bot,
nicht tiefer fällt als der Nasdaq-100 beim Halten und (mit Gegenprobe) besser ist als 19 von 20 Zufallsdepots.
Ergebnis: forschung/ergebnisse/<name>.json und .md, Zeile in forschung/ergebnisse/uebersicht.json."""
import argparse
import datetime as dt
import importlib
import importlib.util
import json
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
sys.path.insert(0, os.path.join(WURZEL, "lernen"))
sys.path.insert(0, WURZEL)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import daten as D  # noqa: E402
import rueckblick as R  # noqa: E402

sys.path.insert(0, HIER)
import rotation as ROT  # noqa: E402

ENDE = pd.Timestamp.today().normalize() - pd.Timedelta(days=2)
ZUFALL_LAEUFE = 6
DEPOT_ZUFALL = 20  # Gegenprobe für eigene Depots: 20 Zufallsdepots, die Idee muss mindestens 19 schlagen


def lade_idee(pfad):
    spec = importlib.util.spec_from_file_location("idee", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def lauf(cache, watch, sektor_von, laeufe, aendern=None):
    importlib.reload(R.sw)  # immer vom unveränderten Bot ausgehen
    R.sw.GEBUEHR = float(os.environ.get("GEBUEHR", "0"))  # wie im echten Depot (Variable GEBUEHR)
    if aendern:
        aendern(R.sw)
    try:
        return {von: R.jetziger_bot(cache, watch, sektor_von, von, min(pd.Timestamp(bis), ENDE), laeufe)
                for von, bis in R.ZEITRAEUME.values()}
    finally:
        importlib.reload(R.sw)


def lauf_mit_verlauf(cache, watch, sektor_von, laeufe):
    """Wie lauf() für den jetzigen Bot, merkt sich dazu den Wertverlauf des ersten Laufs je Zeitraum (für KOMBI_BOT)."""
    kurven = []

    def merken(sw):
        original = sw.simuliere_depot

        def neu(*a, **k):
            dep = original(*a, **k)
            kurven.append(dep["verlauf"])
            return dep
        sw.simuliere_depot = neu
    basis = lauf(cache, watch, sektor_von, laeufe, merken)
    return basis, {von: kurven[i * laeufe] for i, von in enumerate(basis)}


def _q(e):
    return e["rendite"] / max(e["rueckgang"], 0.1)


def urteil_depot(basis, erg, zufall, qqq):
    """Drei Prüfungen je Zeitraum: Rendite pro Rückgang besser als der Swing-Bot, Rückgang nicht größer als beim
    Nasdaq-100 halten, und (mit Gegenprobe) höchstens 1 von 20 Zufallsdepots so gut oder besser."""
    pruef = {v: {"bot": _q(erg[v]) > _q(basis[v]), "nasdaq": erg[v]["rueckgang"] <= qqq[v]["rueckgang"]} for v in basis}
    if zufall:
        for v in basis:
            pruef[v]["zufall"] = sum(z[v]["rendite"] >= erg[v]["rendite"] for z in zufall) <= len(zufall) // 20
    fehlt = []
    if not all(p["bot"] for p in pruef.values()):
        fehlt.append("nicht überall mehr Rendite pro Rückgang als der Swing-Bot")
    if not all(p["nasdaq"] for p in pruef.values()):
        fehlt.append("fällt tiefer als der Nasdaq-100 beim Halten")
    if zufall and not all(p["zufall"] for p in pruef.values()):
        fehlt.append("nicht besser als Zufall")
    text = "besteht alle Prüfungen" if not fehlt else "; ".join(fehlt)
    return text, {v: erg[v]["rendite"] - basis[v]["rendite"] for v in basis}, pruef


def markdown_depot(idee, basis, erg, zufall, qqq, spy, text, pruef):
    namen = dict(zip((v for v, _ in R.ZEITRAEUME.values()), R.ZEITRAEUME))
    z = [f"# 🔬 {idee.NAME}", "", f"Getestet am {dt.date.today():%d.%m.%Y} · Quelle: {getattr(idee, 'QUELLE', '–')}", "",
         getattr(idee, "BESCHREIBUNG", ""), ""]
    for titel, feld in (("Vermutung", "VERMUTUNG"), ("Widerlegt, wenn", "WIDERLEGT_WENN"), ("Varianten", "VARIANTEN")):
        if hasattr(idee, feld):
            z.append(f"- **{titel}:** {getattr(idee, feld)}")
    z += ["", f"**Ergebnis: {text}**", "",
          "| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang) | " + " | ".join(R.ZEITRAEUME) + " |",
          "|---|" + "---:|" * len(R.ZEITRAEUME)]
    f = lambda e: f"{e['rendite']:+.1f} % / −{e['rueckgang']:.0f} % ({_q(e):.2f})".replace(".", ",")  # noqa: E731
    zeile = lambda titel, d: "| " + titel + " | " + " | ".join(f(d[v]) for v in basis) + " |"  # noqa: E731
    z += [zeile("Swing-Bot (jetzt)", basis), zeile("**" + idee.NAME + "**", erg)]
    if zufall:
        z.append("| Zufallsdepots (20×): Spanne der Rendite | " + " | ".join(
            f"{min(x[v]['rendite'] for x in zufall):+.1f} bis {max(x[v]['rendite'] for x in zufall):+.1f} % "
            f"(Mitte {np.median([x[v]['rendite'] for x in zufall]):+.1f} %)".replace(".", ",") for v in basis) + " |")
    z += [zeile("Nasdaq-100 halten", qqq), zeile("S&P 500 halten", spy), "",
          "| Prüfung | " + " | ".join(R.ZEITRAEUME) + " |", "|---|" + "---:|" * len(R.ZEITRAEUME)]
    for k, titel in (("bot", "mehr Rendite pro Rückgang als der Swing-Bot"), ("nasdaq", "nicht tiefer als Nasdaq halten"),
                     ("zufall", "besser als 19 von 20 Zufallsdepots")):
        if all(k in pruef[v] for v in basis):
            z.append(f"| {titel} | " + " | ".join("✅" if pruef[v][k] else "❌" for v in basis) + " |")
    if all("orders_jahr" in erg[v] for v in basis):
        z += ["", "Orders pro Jahr: " + ", ".join(f"{namen[v]} {erg[v]['orders_jahr']:.0f}" for v in basis)]
    z += ["", "In Euro, mit Spread (0,1 % je Order) und Gebühr, Entscheidung zum Monatsende, Handel am nächsten Tag zur "
          "Eröffnung. Aktienliste von heute (S&P 500 und Nasdaq-100): rückblickend zu gut, deshalb zählt der Vergleich "
          "mit Zufall aus derselben Liste. Simulation, keine Anlageberatung."]
    return "\n".join(z) + "\n"


def pruefe_depot(a, idee, watch, sektor_von):
    basis, kurven = lauf_mit_verlauf(a.cache, watch, sektor_von, a.laeufe)
    perioden = {von: min(pd.Timestamp(bis), ENDE) for von, bis in R.ZEITRAEUME.values()}
    anteil = float(getattr(idee, "KOMBI_BOT", 0) or 0)

    def mess(kurve, v):
        return ROT.kennzahlen(ROT.kombi(kurven[v], kurve, anteil) if anteil else kurve)
    erg = {v: mess(idee.depot(a.cache, v, b), v) for v, b in perioden.items()}
    qqq = {v: ROT.kennzahlen(ROT.halten(a.cache, "QQQ", v, b)) for v, b in perioden.items()}
    spy = {v: ROT.kennzahlen(ROT.halten(a.cache, "SPY", v, b)) for v, b in perioden.items()}
    zufall = []
    if hasattr(idee, "zufall"):
        zufall = [{v: mess(idee.zufall(a.cache, v, b, seed), v) for v, b in perioden.items()}
                  for seed in range(DEPOT_ZUFALL)]
    text, plus, pruef = urteil_depot(basis, erg, zufall, qqq)
    md = markdown_depot(idee, basis, erg, zufall, qqq, spy, text, pruef)
    return {"basis": basis, "idee": erg, "zufall": zufall, "nasdaq_halten": qqq, "sp500_halten": spy,
            "pruefungen": pruef, "kombi_bot": anteil}, text, plus, md


def urteil(basis, idee, zufall):
    plus = {v: idee[v]["rendite"] - basis[v]["rendite"] for v in basis}
    tiefer = {v: idee[v]["rueckgang"] - basis[v]["rueckgang"] for v in basis}
    ueberall = all(x >= 0 for x in plus.values()) and all(x <= 1 for x in tiefer.values())
    if not ueberall:
        return "nicht überall besser", plus
    if zufall:
        # schlägt die Idee auch die beste Zufalls-Variante in jedem Zeitraum?
        if all(idee[v]["rendite"] > max(z[v]["rendite"] for z in zufall) for v in basis):
            return "überall besser, auch besser als Zufall", plus
        return "überall besser, aber nicht besser als Zufall", plus
    if min(plus.values()) < 2:
        return "überall besser, aber weniger als 2 Punkte (kann Zufall sein, Gegenprobe nötig)", plus
    return "überall besser", plus


def markdown(name, idee, basis, erg, zufall, text, plus):
    z = [f"# 🔬 {idee.NAME}", "", f"Getestet am {dt.date.today():%d.%m.%Y} · Quelle: {getattr(idee, 'QUELLE', '–')}", "",
         getattr(idee, "BESCHREIBUNG", ""), "", f"**Ergebnis: {text}**", "",
         "| Rendite pro Jahr / größter Rückgang | " + " | ".join(R.ZEITRAEUME) + " |",
         "|---|" + "---:|" * len(R.ZEITRAEUME)]
    zeile = lambda titel, e: "| " + titel + " | " + " | ".join(  # noqa: E731
        f"{e[v]['rendite']:+.1f} % / −{e[v]['rueckgang']:.0f} %".replace(".", ",") for v in basis) + " |"
    z += [zeile("Jetziger Bot", basis), zeile(idee.NAME, erg)]
    for i, e in enumerate(zufall):
        z.append(zeile(f"Gegenprobe Zufall {i + 1}", e))
    z += ["", "Unterschied in Prozentpunkten: " + ", ".join(f"{k} {plus[v]:+.1f}".replace(".", ",")
                                                         for k, v in zip(R.ZEITRAEUME, basis)), "",
          "Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung."]
    return "\n".join(z) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("idee", help="Pfad zu forschung/ideen/<name>.py")
    p.add_argument("--cache", default="lern_cache")
    p.add_argument("--laeufe", type=int, default=8)
    a = p.parse_args(argv)
    t0 = time.time()
    name = os.path.splitext(os.path.basename(a.idee))[0]
    idee = lade_idee(a.idee)
    uni = pd.read_csv(os.path.join(a.cache, "universum.csv"))
    sektor_von = dict(zip(uni["ticker"], uni["sektor"]))
    watch = [t for t in D.watchlist() if D.lies_kurse(a.cache, t) is not None]
    if hasattr(idee, "pruefen"):  # eigener Prüfablauf (z. B. Bot-Check), bekommt den Prüfstand mit allen Werkzeugen
        text, plus, mehr, md = idee.pruefen(sys.modules[__name__], a, watch, sektor_von)
        speichern(name, idee, text, plus, mehr, md, t0)
        return
    if hasattr(idee, "depot"):
        mehr, text, plus, md = pruefe_depot(a, idee, watch, sektor_von)
        speichern(name, idee, text, plus, mehr, md, t0)
        return
    basis = lauf(a.cache, watch, sektor_von, a.laeufe)
    erg = lauf(a.cache, watch, sektor_von, a.laeufe, idee.anpassen)
    zufall = []
    if hasattr(idee, "gegenprobe"):
        for seed in range(ZUFALL_LAEUFE):
            zufall.append(lauf(a.cache, watch, sektor_von, a.laeufe, lambda sw, s=seed: idee.gegenprobe(sw, s)))
    text, plus = urteil(basis, erg, zufall)
    speichern(name, idee, text, plus, {"basis": basis, "idee": erg, "zufall": zufall},
              markdown(name, idee, basis, erg, zufall, text, plus), t0)


def speichern(name, idee, text, plus, mehr, md, t0):
    aus = os.path.join(HIER, "ergebnisse")
    os.makedirs(aus, exist_ok=True)
    with open(os.path.join(aus, name + ".json"), "w", encoding="utf-8") as f:
        json.dump({"name": idee.NAME, "datei": name, "datum": f"{dt.date.today()}", "quelle": getattr(idee, "QUELLE", None),
                   "urteil": text, "plus": plus, **mehr, "sekunden": round(time.time() - t0)}, f, ensure_ascii=False,
                  indent=1)
    with open(os.path.join(aus, name + ".md"), "w", encoding="utf-8") as f:
        f.write(md)
    basis = mehr["basis"]
    pfad = os.path.join(aus, "uebersicht.json")
    try:
        with open(pfad, encoding="utf-8") as f:
            liste = json.load(f)
    except (OSError, ValueError):
        liste = []
    liste = [x for x in liste if x.get("datei") != name] + [
        {"datum": f"{dt.date.today()}", "datei": name, "name": idee.NAME, "urteil": text,
         "plus": [round(plus[v], 1) for v in basis]}]
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=1)
    print(f"{idee.NAME}: {text} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
