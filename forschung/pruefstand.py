"""Prüfstand des Forschungs-Bots: testet eine Idee aus forschung/ideen/<name>.py ehrlich gegen den jetzigen Bot.

Gleicher Test wie bei allen früheren Ideen (gehirn/Notizen/Was der Bot schon weiß.md): echter Bot auf der Watchlist,
2010–2014, 2015–2021 und 2022–2026, mit Gebühr und Spread, mehrere Läufe mit gemischter Reihenfolge der Aktien.

Eine Idee ist eine kleine Python-Datei mit
  NAME = "kurzer Name", QUELLE = "Link", BESCHREIBUNG = "in einfachen Worten"
  def anpassen(sw): ...            # verändert den Bot (Modul swing_scanner) nur für den Test
  def gegenprobe(sw, seed): ...    # optional: dieselbe Art Änderung, aber zufällig (z. B. zufällige Aktien zuerst)
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
import pandas as pd  # noqa: E402

import daten as D  # noqa: E402
import rueckblick as R  # noqa: E402

ENDE = pd.Timestamp.today().normalize() - pd.Timedelta(days=2)
ZUFALL_LAEUFE = 6


def lade_idee(pfad):
    spec = importlib.util.spec_from_file_location("idee", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def lauf(cache, watch, sektor_von, laeufe, aendern=None):
    importlib.reload(R.sw)  # immer vom unveränderten Bot ausgehen
    if aendern:
        aendern(R.sw)
    try:
        return {von: R.jetziger_bot(cache, watch, sektor_von, von, min(pd.Timestamp(bis), ENDE), laeufe)
                for von, bis in R.ZEITRAEUME.values()}
    finally:
        importlib.reload(R.sw)


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
    basis = lauf(a.cache, watch, sektor_von, a.laeufe)
    erg = lauf(a.cache, watch, sektor_von, a.laeufe, idee.anpassen)
    zufall = []
    if hasattr(idee, "gegenprobe"):
        for seed in range(ZUFALL_LAEUFE):
            zufall.append(lauf(a.cache, watch, sektor_von, a.laeufe, lambda sw, s=seed: idee.gegenprobe(sw, s)))
    text, plus = urteil(basis, erg, zufall)
    aus = os.path.join(HIER, "ergebnisse")
    os.makedirs(aus, exist_ok=True)
    with open(os.path.join(aus, name + ".json"), "w", encoding="utf-8") as f:
        json.dump({"name": idee.NAME, "datei": name, "datum": f"{dt.date.today()}", "quelle": getattr(idee, "QUELLE", None),
                   "urteil": text, "plus": plus, "basis": basis, "idee": erg, "zufall": zufall,
                   "sekunden": round(time.time() - t0)}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(aus, name + ".md"), "w", encoding="utf-8") as f:
        f.write(markdown(name, idee, basis, erg, zufall, text, plus))
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
