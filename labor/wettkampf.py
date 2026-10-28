"""Wettkampf: Strategie-Labor gegen Swing-Bot auf denselben echten Kursen.

Gezählt werden nur Testjahre, die das Labor beim Suchen nicht kannte (Walk-Forward). Der Swing-Bot rechnet mit
seinen eingefrorenen Regeln (swing_scanner.py, nur lesend: Tagebuch, Lernregel, Depot) über dieselben Jahre.
Beide in US-Dollar, mit Kosten, 10.000 $ Start.

„Besser“ ist vorher festgelegt (labor/PROMPT.md): in jedem Zeitraum mehr Rendite pro Jahr UND mehr Rendite je
Prozent größtem Rückgang als der Swing-Bot. Jeder Lauf kommt ins Forschungsprotokoll, auch erfolglose.

Aufruf (braucht Yahoo, z. B. in GitHub Actions):
    python labor/wettkampf.py --versuch "v3: …" --ausgabe labor/forschung
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import importlib.util
import io
import json
import math
import pathlib
import pickle
import random
import statistics
import sys
import time

import numpy as np
import pandas as pd

WURZEL = pathlib.Path(__file__).resolve().parents[1]
AB = "2005-01-01"  # Kurse ab hier: das Labor lernt auch aus der Finanzkrise 2008
ZEITRAEUME = [("2015–2021", "2015-01-01", "2021-12-31"), ("2022–2026", "2022-01-01", "2099-12-31")]


def lade_modul(name, datei):
    spec = importlib.util.spec_from_file_location(name, datei)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def lade_kurse(ticker, ab="2005-01-01"):
    """Tageskerzen mit Volumen (der Swing-Bot braucht es für den Ausbruch), um Splits und Dividenden bereinigt."""
    import yfinance as yf

    roh = yf.download(sorted(ticker), start=ab, interval="1d", auto_adjust=True, group_by="ticker",
                      progress=False, threads=True)
    daten = {}
    for t in ticker:
        if t not in roh.columns.get_level_values(0):
            continue
        df = roh[t][["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["High", "Low", "Close"])
        if len(df) > 60:
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df.index.name = "Date"
            daten[t] = df.astype(float)
    return daten


def lade_termine(ticker):
    """Quartalszahlen-Termine für die Zahlen-Regel des Swing-Bots (fehlen sie, gilt die Regel für die Aktie nicht)."""
    import yfinance as yf

    termine = {}
    for t in ticker:
        try:
            df = yf.Ticker(t).get_earnings_dates(limit=60)
            if df is not None and len(df):
                termine[t] = df
        except Exception:  # Yahoo liefert für manche Werte nichts – dann ohne Zahlen-Regel
            pass
    return termine


def lade_stand(pfad, bis):
    """Fester Datenstand für alle Versuche: einmal laden, bis 'bis' abschneiden, zwischenspeichern. So rechnet jeder
    Versuch mit genau denselben Kursen und Quartalszahlen (sonst verschieben laufende Kerzen, neue Dividenden oder
    fehlende Termine die Messlatte)."""
    pfad = pathlib.Path(pfad)
    if pfad.exists():
        with pfad.open("rb") as f:
            stand = pickle.load(f)
        if stand.get("bis") == bis and stand.get("ab") == AB:
            return stand["kurse"], stand["termine"]
    return None


def speichere_stand(pfad, bis, kurse, termine):
    pfad = pathlib.Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("wb") as f:
        pickle.dump({"bis": bis, "ab": AB, "kurse": kurse, "termine": termine}, f)


def swing_lauf(sw, kurse, termine, ab, reihenfolge=None):
    """Das Depot des Swing-Bots ab 'ab' mit seinen eigenen Regeln, in US-Dollar. Gibt eine Wert-Reihe zurück.
    reihenfolge: Ticker-Reihenfolge (sie entscheidet bei gleich guten Signalen, wie im Test der README)."""
    alt = sys.argv
    sys.argv = ["swing_scanner.py", "--konto", "10000", "--risiko", "1", "--ohne-news"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            einst = sw.lies_einstellungen()
    finally:
        sys.argv = alt
    qqq = kurse[sw.MARKT_TICKER]
    letzter = qqq.index[-1]
    einst.rueckblick = (letzter.year - ab.year) * 12 + letzter.month - ab.month + 1
    trend = sw.markt_trend(qqq)
    fx = pd.Series(1.0, index=qqq.index)  # in Dollar rechnen wie das Labor
    daten = {}
    for t in reihenfolge or sw.TICKER_LISTE:
        if t in kurse:
            daten[t] = sw.bereite_vor(t, kurse[t], fx, termine.get(t), einst, trend)
    alle_tage = sorted(set().union(*(set(d["idx"][:d["n_fertig"]]) for d in daten.values())))
    tagebuch = sw.strategie_tagebuch(daten, einst)
    pausen, _ = sw.lernverlauf(tagebuch, alle_tage, einst)
    depot = sw.simuliere_depot(daten, pausen, einst, einst.lernen)
    reihe = depot["verlauf"].astype(float).sort_index()
    reihe.index = pd.DatetimeIndex(reihe.index)
    return reihe, {"aktien": len(daten), "trades": len(depot["trades"]), "termine": len(termine)}


def kennzahlen(reihe, von, bis):
    """Rendite pro Jahr, größter Rückgang, Sharpe und Rendite je Rückgang in [von, bis], Start = Wert davor."""
    vorher = reihe[reihe.index < pd.Timestamp(von)]
    teil = reihe[(reihe.index >= pd.Timestamp(von)) & (reihe.index <= pd.Timestamp(bis))]
    if len(teil) < 20:
        return None
    start = vorher.iloc[-1] if len(vorher) else teil.iloc[0]
    werte = np.r_[start, teil.to_numpy()]
    rendite = ((werte[-1] / werte[0]) ** (252 / (len(werte) - 1)) - 1) * 100
    rueckgang = float(np.max(1 - werte / np.maximum.accumulate(werte)) * 100)
    r = np.diff(werte) / werte[:-1]
    sharpe = float(r.mean() / r.std() * math.sqrt(252)) if r.std() > 0 else 0.0
    return {"rendite": round(float(rendite), 2), "rueckgang": round(rueckgang, 2), "sharpe": round(sharpe, 2),
            "je_rueckgang": round(float(rendite) / max(rueckgang, 1.0), 3),
            "von": str(teil.index[0].date()), "bis": str(teil.index[-1].date())}


def urteil(labor, swing):
    """Besser = mehr Rendite pro Jahr UND mehr Rendite je Prozent Rückgang (in jedem Zeitraum)."""
    return labor["rendite"] > swing["rendite"] and labor["je_rueckgang"] > swing["je_rueckgang"]


def de(x, n=1, vz=False):
    t = f"{x:+,.{n}f}" if vz else f"{x:,.{n}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def bericht(erg):
    z = ["# 🏁 Wettkampf: Strategie-Labor gegen Swing-Bot", "",
         f"Stand: {erg['erstellt']} · Kurse bis {erg['daten_bis']} · Versuch: **{erg['versuch']}** · "
         "Simulation mit Spielgeld, keine Anlageberatung.", "",
         "Beide auf denselben Kursen (Yahoo, ab 2005), in US-Dollar, mit Kosten, 10.000 $ Start. Das Labor zählt nur "
         "Testjahre, die es beim Suchen nicht kannte. **Besser** heißt: in jedem Zeitraum mehr Rendite pro Jahr und "
         "mehr Rendite je Prozent größtem Rückgang.", "",
         "Beim Labor steht der mittlere von mehreren Zufallsstarts. Besser zählt nur, wenn **alle** Starts besser sind. "
         "Beim Swing-Bot steht je Kennzahl die stärkere von zwei Messungen: durchgehend ab dem ersten Testjahr und "
         "frisch gestartet zum Beginn des Zeitraums (je Mittel aus mehreren Ticker-Reihenfolgen).",
         "",
         "| Zeitraum | Bot | Rendite pro Jahr | größter Rückgang | Rendite je % Rückgang | Sharpe |",
         "| --- | --- | --- | --- | --- | --- |"]
    for zr in erg["zeitraeume"]:
        for name, k in (("Strategie-Labor", zr["labor"]), ("Swing-Bot", zr["swing"]), ("Nasdaq-100 halten", zr["qqq"])):
            z.append(f"| {zr['name']} | {name} | {de(k['rendite'])} % | {de(k['rueckgang'])} % | "
                     f"{de(k['je_rueckgang'], 2)} | {de(k['sharpe'], 2)} |")
        z.append(f"| {zr['name']} | **Urteil** | **{'Labor besser' if zr['besser'] else 'Swing-Bot vorn'}** "
                 f"({zr['besser_anzahl']} von {len(zr['labor_alle'])} Starts besser) | | | |")
    z += ["", f"**Gesamturteil: {'Das Strategie-Labor ist besser als der Swing-Bot.' if erg['besser'] else 'Noch nicht besser.'}**",
          "", f"Labor: {erg['labor_info']['aktien']} Aktien (davon {erg['labor_info']['tech']} Tech), Budget "
          f"{erg['budget']}, Zufallsstart {erg['seed']}, {erg['labor_info']['bauplaene']} Baupläne geprüft. "
          f"Swing-Bot: {erg['swing_info']['aktien']} Aktien seiner Watchlist, Mittel aus "
          f"{erg['swing_info'].get('laeufe', 1)} Ticker-Reihenfolgen, Quartalszahlen für "
          f"{erg['swing_info']['termine']} Aktien. Fester Datenstand bis {erg['daten_bis']}.", "",
          "Vorsicht: Beide Aktienlisten sind von heute (Überlebende). Das hilft Kauf-Strategien und Halten, dem "
          "Tech-Labor vermutlich mehr als dem Swing-Bot mit seinen 8 Branchen.", ""]
    return "\n".join(z)


def main(argv=None):
    p = argparse.ArgumentParser(description="Wettkampf Strategie-Labor gegen Swing-Bot")
    p.add_argument("--versuch", default="ohne Namen", help="kurze Beschreibung der Labor-Version")
    p.add_argument("--budget", default="normal")
    p.add_argument("--seeds", type=int, default=5, help="so viele Zufallsstarts – besser nur, wenn alle besser sind")
    p.add_argument("--ausgabe", default=str(WURZEL / "labor" / "forschung"))
    p.add_argument("--bis", default="2026-10-27", help="fester letzter Kurstag für alle Versuche")
    p.add_argument("--zwischenspeicher", default=str(WURZEL / "labor" / "forschung" / ".kurse.pkl"))
    p.add_argument("--swing-laeufe", type=int, default=8, help="Swing-Bot mit so vielen Ticker-Reihenfolgen (Mittel)")
    a = p.parse_args(argv)
    beginn = time.time()
    labor = lade_modul("strategie_labor", WURZEL / "labor" / "strategie_labor.py")
    sw = lade_modul("swing_scanner", WURZEL / "swing_scanner.py")
    labor.KOSTEN = (float(sw.GEBUEHR), float(sw.SPREAD_PROZENT) / 100)

    ticker = sorted(set(sw.BRANCHE) | set(sw.TICKER_LISTE) | {sw.MARKT_TICKER})
    gespeichert = lade_stand(a.zwischenspeicher, a.bis)
    if gespeichert:
        kurse, termine = gespeichert
        print(f"🏁 Fester Datenstand bis {a.bis} aus dem Zwischenspeicher: {len(kurse)} Ticker", flush=True)
    else:
        print(f"🏁 Lade Kurse ab 2005 für {len(ticker)} Ticker (fester Stand bis {a.bis}) …", flush=True)
        kurse = {t: df[df.index <= pd.Timestamp(a.bis)] for t, df in lade_kurse(ticker, AB).items()}
        termine = lade_termine(sw.TICKER_LISTE)
        speichere_stand(a.zwischenspeicher, a.bis, kurse, termine)

    # Labor: Walk-Forward, nur Testjahre – mehrmals mit anderem Zufallsstart
    lab_daten = {t: df[["Open", "High", "Low", "Close"]] for t, df in kurse.items() if len(df) > labor.VORLAUF_TAGE}
    m = labor.Markt(lab_daten, sw.BRANCHE)
    laeufe = []
    for seed in range(20261028, 20261028 + a.seeds):
        print(f"🏁 Labor, Zufallsstart {seed} …", flush=True)
        wf = labor.walk_forward(m, random.Random(seed), a.budget)
        tage = m.tage[len(m.tage) - len(wf["verlauf"]):]
        laeufe.append((seed, wf, pd.Series(wf["verlauf"], index=tage)))
    qqq = pd.Series(laeufe[0][1]["verlauf_qqq"], index=laeufe[0][2].index)
    ab = pd.Timestamp(laeufe[0][2].index[0])

    # Swing-Bot: dieselben Jahre, eigene Regeln, mehrere Ticker-Reihenfolgen (Mittel wie im Test der README)
    # Zwei Messungen: durchgehend ab dem ersten Testjahr und frisch zum Beginn jedes Zeitraums (das Depot des
    # Swing-Bots hängt vom Startzeitpunkt ab). Das Labor muss jeweils die stärkere schlagen.
    def swing_reihen(start):
        reihen = []
        for i in range(a.swing_laeufe):
            folge = list(sw.TICKER_LISTE)
            if i:
                random.Random(i).shuffle(folge)
            print(f"🏁 Swing-Bot ab {start.date()}, Reihenfolge {i + 1} von {a.swing_laeufe} …", flush=True)
            reihen.append(swing_lauf(sw, kurse, termine, start, folge))
        return reihen

    durchgehend = swing_reihen(ab)
    swing_info = durchgehend[0][1] | {"laeufe": len(durchgehend)}

    def swing_mittel(swings, von, bis):
        alle = [kennzahlen(reihe, von, bis) for reihe, _ in swings]
        if not all(alle):
            return None
        mitte = {k: round(statistics.mean(x[k] for x in alle), 3) for k in ("rendite", "rueckgang", "sharpe")}
        mitte["je_rueckgang"] = round(statistics.mean(x["je_rueckgang"] for x in alle), 3)
        mitte["spanne_rendite"] = [min(x["rendite"] for x in alle), max(x["rendite"] for x in alle)]
        return mitte | {"von": alle[0]["von"], "bis": alle[0]["bis"]}

    zeitraeume = []
    for name, von, bis in ZEITRAEUME:
        frisch_start = qqq.index[qqq.index >= pd.Timestamp(von)][0]
        k_durch, k_frisch = swing_mittel(durchgehend, von, bis), swing_mittel(swing_reihen(frisch_start), von, bis)
        ks = None
        if k_durch and k_frisch:  # die jeweils stärkere Messung des Swing-Bots
            ks = max((k_durch, k_frisch), key=lambda k: (k["je_rueckgang"], k["rendite"]))
            ks = ks | {"rendite": max(k_durch["rendite"], k_frisch["rendite"]),
                       "je_rueckgang": max(k_durch["je_rueckgang"], k_frisch["je_rueckgang"]),
                       "durchgehend": k_durch, "frisch": k_frisch}
        kq = kennzahlen(qqq, von, bis)
        je_seed = [kennzahlen(lab, von, bis) for _, _, lab in laeufe]
        if ks and kq and all(je_seed):
            mitte = sorted(je_seed, key=lambda k: k["je_rueckgang"])[len(je_seed) // 2]  # Median-Lauf
            zeitraeume.append({"name": name, "labor": mitte, "labor_alle": je_seed, "swing": ks, "qqq": kq,
                               "besser": all(urteil(k, ks) for k in je_seed),
                               "besser_anzahl": sum(urteil(k, ks) for k in je_seed)})
    erg = {
        "erstellt": dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC"),
        "daten_bis": str(m.tage[-1].date()), "versuch": a.versuch, "budget": a.budget,
        "seed": f"{len(laeufe)} Starts", "zeitraeume": zeitraeume,
        "besser": bool(zeitraeume) and all(z["besser"] for z in zeitraeume),
        "labor_info": {"aktien": len(m.ticker), "tech": int(m.tech.sum()),
                       "bauplaene": sum(s["geprueft"] for _, wf, _ in laeufe for s in wf["schritte"])},
        "swing_info": swing_info,
        "testjahre": [[{"jahr": s["jahr"], "labor": s["test"]["rendite"], "rueckgang": s["test"]["rueckgang"],
                        "qqq": s["qqq"]["rendite"], "familie": s["genom"]["familie"],
                        "dsr": s["deflated_sharpe"]["dsr"]} for s in wf["schritte"]] for _, wf, _ in laeufe],
        "dauer_sekunden": round(time.time() - beginn),
    }
    aus = pathlib.Path(a.ausgabe)
    aus.mkdir(parents=True, exist_ok=True)
    (aus / "wettkampf.json").write_text(json.dumps(erg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (aus / "WETTKAMPF.md").write_text(bericht(erg), encoding="utf-8")
    protokoll = aus / "protokoll.json"
    alt = json.loads(protokoll.read_text(encoding="utf-8")) if protokoll.exists() else []
    protokoll.write_text(json.dumps(alt + [{k: erg[k] for k in ("erstellt", "versuch", "budget", "seed", "besser",
                                                                    "zeitraeume")}],
                                    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(bericht(erg))
    return erg


if __name__ == "__main__":
    main()
