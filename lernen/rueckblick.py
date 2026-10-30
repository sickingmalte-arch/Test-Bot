"""Lernmodell des Swing-Bots: ehrlicher Rückblick 2010–2026 (Walk-forward).

1. Alle Kauf-Signale aller Aktien mit Merkmalen und Ergebnis.
2. Lernmodell jeden Monat neu – nur mit Trades, deren Ergebnis vorher feststand.
3. Depot-Simulation in drei Zeiträumen (2010–2014, 2015–2021, 2022–2026), je 16 Läufe mit zufälliger Reihenfolge der
   Aktien bei Gleichstand, mit Gebühr und Spread.
4. Vergleich: jetziger Bot (gleiche Aktien, mit seiner Lernregel), S&P 500 und Nasdaq-100 kaufen und halten.
5. Fehler-Analyse und was das Modell gelernt hat.

Aufruf: python lernen/rueckblick.py --cache DATENORDNER [--laeufe 16] [--aus lernen/rueckblick]
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import daten as D  # noqa: E402
import depot as P  # noqa: E402
import fehler as F  # noqa: E402
import merkmale as M  # noqa: E402
import modell as L  # noqa: E402

sw = M.sw
ZEITRAEUME = {"2010–2014": ("2010-01-01", "2014-12-31"), "2015–2021": ("2015-01-01", "2021-12-31"),
              "2022–2026": ("2022-01-01", "2026-12-31")}
_G = {}  # Daten für die Arbeitsprozesse (per fork geteilt)


def daten_fuer_depot(cache, tickers, fx, ende):
    daten = {}
    for t in tickers:
        df = D.lies_kurse(cache, t)
        if df is None or len(df) < 300:
            continue
        daten[t] = M.vorbereiten(t, df[df.index <= ende], fx, D.lies_termine(cache, t))
    return daten


def _lauf(a):
    name, von, bis, auswahl, variante, anteil, filter_an, nur_watchlist, seed = a
    daten, kand = _G["daten"], _G["kand"]
    if nur_watchlist:
        kand = kand[kand["ticker"].isin(_G["watchlist"])]
    tage = _G["spy"].index[(_G["spy"].index >= von) & (_G["spy"].index <= bis)]
    schwellen = _G["schwellen"].get(anteil) if auswahl == "modell" else None
    erg = P.simuliere(daten, kand, tage, auswahl=auswahl, variante=variante, schwellen=schwellen, seed=seed,
                      marktfilter=_G["marktfilter"] if filter_an else None)
    return name, von, seed, P.kennzahlen(erg), erg["trades"] if seed == 0 else None


def bot_sperre(kand, schwellen, tickers):
    """Wie im Bot (lernmodell_anwenden): Signaltag -> Aktien, deren Punktzahl unter der Kauf-Schwelle liegt."""
    k = kand[kand["ticker"].isin(list(tickers)) & kand["punkte"].notna()]
    unter = k["punkte"].to_numpy() < k["tag"].dt.to_period("M").map(schwellen).fillna(np.inf).to_numpy()
    aus = {}
    for tag, t in zip(k["tag"][unter], k["ticker"][unter]):
        aus.setdefault(pd.Timestamp(tag), set()).add(t)
    return {tag: frozenset(v) for tag, v in aus.items()}


def bot_rang(kand, tickers):
    """Wie im Bot (lern_rang_aus): Signaltag -> {Aktie: Punktzahl}."""
    k = kand[kand["ticker"].isin(list(tickers)) & kand["punkte"].notna()]
    aus = {}
    for tag, t, p in zip(k["tag"], k["ticker"], k["punkte"]):
        aus.setdefault(pd.Timestamp(tag), {})[t] = float(p)
    return aus


def jetziger_bot(cache, tickers, sektor_von, von, bis, laeufe, sperre=None, rang=None):
    """Der jetzige Bot mit seinen Regeln (Marktfilter, Lernregel, Branchen-Grenze nach GICS) auf denselben Aktien.
    sperre: Signale, die der Bot wegen des Lernmodells nicht kauft (siehe bot_sperre)."""
    import io, contextlib, random  # noqa: E401
    alt = sys.argv
    sys.argv = ["x", "--ohne-news", "--konto", "10000", "--risiko", "1"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            einst = sw.lies_einstellungen()
    finally:
        sys.argv = alt
    einst.lern_sperre, einst.lern_rang = sperre or {}, rang or {}
    sw.BRANCHE.clear()
    sw.BRANCHE.update({t: s for t, s in sektor_von.items() if isinstance(s, str)})
    bis_ts = pd.Timestamp(bis)
    fx = D.lies_kurse(cache, "EURUSD=X")["Close"]
    fx = fx[fx.index <= bis_ts]
    qqq = D.lies_kurse(cache, "QQQ")
    trend = sw.markt_trend(qqq[qqq.index <= bis_ts])
    daten = {}
    for t in tickers:
        df = D.lies_kurse(cache, t)
        if df is None or len(df) < sw.MIN_KERZEN:
            continue
        df = df[df.index <= bis_ts][["Open", "High", "Low", "Close", "Volume"]]
        if len(df) < sw.MIN_KERZEN:
            continue
        termine = D.lies_termine(cache, t)
        d = sw.bereite_vor(t, df, fx, termine, einst, trend)
        d["n_fertig"] = d["n"]
        d["offen"] = False
        daten[t] = d
    tb = sw.strategie_tagebuch(daten, einst)
    tage = sorted(set().union(*(set(d["idx"][:d["n_fertig"]]) for d in daten.values())))
    pausen, _ = sw.lernverlauf(tb, tage, einst)
    von_ts = pd.Timestamp(von)
    letzter = tage[-1]
    einst.rueckblick = (letzter.year - von_ts.year) * 12 + (letzter.month - von_ts.month) + 1
    ergebnisse = []
    for s in range(laeufe):
        keys = list(daten)
        if s:
            random.Random(s).shuffle(keys)
        dep = sw.simuliere_depot({k: daten[k] for k in keys}, pausen, einst, einst.lernen)
        tr = [x for x in dep["trades"] if x["kauf_tag"] >= von_ts]
        jahre = (dep["ende"] - dep["start"]).days / 365.25
        g = np.array([x["erloes"] - x["kosten"] for x in tr])
        rr = np.array([(x["erloes"] - x["kosten"]) / x["risiko_eur"] for x in tr])
        ergebnisse.append({"rendite": 100 * ((dep["end_wert"] / dep["start_wert"]) ** (1 / jahre) - 1),
                           "rueckgang": dep["max_rueckgang"], "treffer": float((g > 0).mean() * 100),
                           "schnitt_r": float(rr.mean()), "trades_jahr": len(tr) / jahre})
    return {k: float(np.mean([e[k] for e in ergebnisse])) for k in ergebnisse[0]}


# ----------------------------------------------------------------------------
# RUECKBLICK.md in einfachen Worten
# ----------------------------------------------------------------------------
def _pz(x, stellen=1):
    return "–" if x is None or not np.isfinite(x) else f"{x:+.{stellen}f} %".replace(".", ",")


def _z(x, stellen=1):
    return "–" if x is None or not np.isfinite(x) else f"{x:.{stellen}f}".replace(".", ",")


def _tsd(n):
    return f"{int(n):,}".replace(",", ".")


def _zeile_kz(name, je):
    zellen = []
    for von in [v for v, _ in ZEITRAEUME.values()]:
        w = (je or {}).get(von)
        zellen.append(f"{_pz(w['rendite'])} / −{_z(w['rueckgang'], 0)} %" if w else "–")
    return f"| {name} | " + " | ".join(zellen) + " |"


BOT_ZEILEN = [("**Jetziger Bot** (Watchlist, Marktfilter, Lernregel)", "jetziger_bot"),
              ("**Bot + Lernmodell:** beste Punktzahl zuerst (kein Filter)", "bot_rang"),
              ("**Bot + Lernmodell:** nur beste 50 %, beste zuerst", "bot_mit_lernmodell_50"),
              ("**Bot + Lernmodell:** nur beste 30 %, beste zuerst", "bot_mit_lernmodell"),
              ("**Bot + Lernmodell:** nur beste 30 % (Reihenfolge wie heute)", "bot_nur_filter")]


def markdown(erg):
    L_ = []
    a = L_.append
    kopf = " | ".join(ZEITRAEUME)
    a("# 📜 Lernmodell des Swing-Bots – Rückblick 2010–2026")
    a("")
    a(f"Stand: {erg.get('stand', '')[:10]} · {erg.get('aktien', 0)} Aktien aus S&P 500 und Nasdaq-100 · "
      f"{_tsd(erg.get('signale', 0))} Kauf-Signale seit 2008, davon {_tsd(erg.get('signale_fertig', 0))} mit "
      "Ergebnis")
    a("")
    a("So wurde gerechnet:")
    a("")
    a("- **Walk-forward:** Das Lernmodell wird für jeden Monat neu trainiert, und zwar nur mit Trades, deren "
      "Ergebnis vor Monatsbeginn schon feststand. Die Signale des Monats selbst hat es nie gesehen.")
    a("- **Depot wie beim Übungsdepot:** 10.000 €, 1 % Risiko je Trade, höchstens 5 Positionen und 2 aus "
      "derselben Branche, höchstens 25 % je Position und 5 % Risiko zusammen, Kauf zur nächsten Eröffnung bis "
      "zum Limit, 1 € Gebühr und 0,1 % Spread je Order, Kurse in Euro.")
    a("- **16 Läufe je Zeitraum:** Bei Gleichstand entscheidet eine zufällige Reihenfolge der Aktien; gezeigt ist "
      "der Durchschnitt.")
    a("")
    # Depot
    dep = erg.get("depot") or {}
    if dep:
        a("## Rendite pro Jahr / größter Rückgang")
        a("")
        a(f"| | {kopf} |")
        a("|---|---:|---:|---:|")
        for name, je in BOT_ZEILEN:
            if erg.get(je):
                a(_zeile_kz(name, erg[je]))
        for name, je in dep.items():
            a(_zeile_kz(name, je))
        for name, je in (erg.get("halten") or {}).items():
            a(_zeile_kz(name, je))
        a("")
        a("## Trefferquote / Ø Ergebnis je Trade / Trades pro Jahr")
        a("")
        a(f"| | {kopf} |")
        a("|---|---:|---:|---:|")
        zeilen = [(name, erg[je]) for name, je in BOT_ZEILEN if erg.get(je)] + list(dep.items())
        for name, je in zeilen:
            zellen = []
            for von in [v for v, _ in ZEITRAEUME.values()]:
                w = je.get(von)
                zellen.append(f"{_z(w['treffer'], 0)} % / {_z(w['schnitt_r'], 2)} R / {_z(w['trades_jahr'], 0)}"
                              if w else "–")
            a(f"| {name} | " + " | ".join(zellen) + " |")
        a("")
        a("1 R = der geplante Verlust bis zum Stop. Kaufen und halten hat keine Trades.")
        a("")
    # Güte
    g = erg.get("guete") or {}
    if g:
        a("## Trennt das Lernmodell gute von schlechten Signalen?")
        a("")
        a(f"Alle {_tsd(g['n'])} Signale seit 2010 mit Ergebnis, nach der Punktzahl in fünf gleich große Gruppen "
          "geteilt:")
        a("")
        a("| Punktzahl | Trefferquote | Ø Ergebnis |")
        a("|---|---:|---:|")
        f5 = {int(x["fuenftel"]): x for x in g["fuenftel"]}
        for q, text in ((5, "bestes Fünftel"), (4, "2. Fünftel"), (3, "Mitte"), (2, "4. Fünftel"),
                        (1, "schlechtestes Fünftel")):
            if q in f5:
                a(f"| {text} | {_z(100 * f5[q]['treffer'], 0)} % | {_z(f5[q]['R'], 2)} R |")
        a("")
        a(f"Trennschärfe (AUC): **{_z(g['auc'], 3)}** (0,50 = Münzwurf). Je Jahr: "
          + ", ".join(f"{j}: {_z(v, 2)}" for j, v in sorted((g.get("auc_je_jahr") or {}).items())) + ".")
        a("")
        g2 = erg.get("guete_ohne_bilanz") or {}
        if g2:
            a(f"Ohne Bilanzdaten (nur Chart, Momentum, Quartalszahlen-Termine, Markt, Branche): AUC "
              f"{_z(g2['auc'], 3)}.")
            a("")
    ab = erg.get("bilanz_abdeckung") or {}
    if ab:
        a("## Bilanzdaten (Value, Growth, Qualität)")
        a("")
        a("Quelle: SEC EDGAR – jede Zahl mit dem Tag, an dem sie veröffentlicht wurde; das Modell sieht sie erst ab "
          "dem Tag danach, spätere Korrekturen erst ab ihrem eigenen Datum. Damit dürfen Value und Growth auch im "
          "Rückblick getestet werden. Anteil der Signale mit Bewertung (Gewinnrendite) je Jahr:")
        a("")
        a(" · ".join(f"{j}: {_z(100 * v, 0)} %" for j, v in sorted(ab.items()) if int(j) >= 2008))
        a("")
        ue = erg.get("ueberraschung_abdeckung") or {}
        if ue:
            a("Gewinnüberraschung (von Yahoo, nur die letzten rund 25 Quartale): "
              + " · ".join(f"{j}: {_z(100 * v, 0)} %" for j, v in sorted(ue.items()) if int(j) >= 2008))
            a("")
    fs = erg.get("fehler_signale") or {}
    if fs.get("tabelle"):
        a("## Häufigste Fehler – und meidet das Modell sie?")
        a("")
        a(f"Alle {_tsd(fs['n_alle'])} gedachten Trades seit 2010: verloren {_z(100 * fs['verlust_alle'], 0)} %. Von "
          f"den {_tsd(fs['n_ausgewaehlt'])}, die das Modell gekauft hätte (beste 30 %): verloren "
          f"{_z(100 * fs['verlust_ausgewaehlt'], 0)} %.")
        a("")
        a("| Warum verloren? | bei allen Signalen | bei der Auswahl des Modells |")
        a("|---|---:|---:|")
        for x in fs["tabelle"]:
            a(f"| {x['text']} | {_z(100 * x['alle'], 1)} % | {_z(100 * x['ausgewaehlt'], 1)} % |")
        a("")
        a("Anteil an allen Trades (nicht nur an den Verlusten); ein Trade kann mehrere Gründe haben.")
        a("")
    gl = erg.get("gelernt") or []
    if gl:
        a("## Was das Modell gelernt hat (die 15 wichtigsten Merkmale)")
        a("")
        a("| Merkmal | Wichtigkeit | Richtung |")
        a("|---|---:|---|")
        for x in gl[:15]:
            r = x.get("richtung")
            richtung = ("je höher, desto besser" if r is not None and r >= 0.15 else
                        "je niedriger, desto besser" if r is not None and r <= -0.15 else "nur im Zusammenspiel")
            a(f"| {x['name']} | {_z(1000 * x['wichtigkeit'], 1)} | {richtung} |")
        a("")
        a("Wichtigkeit: Um so viele Tausendstel sinkt die Trennschärfe, wenn man das Merkmal durcheinanderwürfelt "
          "(Modell bis 12 Monate vor Schluss, geprüft an den 12 Monaten danach).")
        a("")
    a("## Ehrlich bleiben")
    a("")
    weg = erg.get("sp500_entfernt_seit_2010")
    a("- **Überlebens-Verzerrung:** Getestet wurden die Aktien, die HEUTE im S&P 500 oder Nasdaq-100 sind. Firmen, "
      "die seit 2010 herausgefallen, übernommen worden oder pleite gegangen sind, fehlen"
      + (f" (allein im S&P 500 rund {weg} Änderungen seit 2010)" if weg else "")
      + ". Dadurch sieht der Rückblick für alle Varianten zu gut aus – auch für den jetzigen Bot. Kaufen und "
      "halten ist davon nicht betroffen (der Index-Fonds hatte die Verlierer damals wirklich).")
    a("- **Bilanzdaten:** nur mit Veröffentlichungsdatum (SEC). Vor 2009 gibt es keine, Firmen ohne US-Bilanz "
      "(z. B. ASML) haben keine. Die Gewinnüberraschung von Yahoo reicht nur einige Jahre zurück.")
    a("- **Kosten** (Gebühr und Spread) sind abgezogen, Steuern nicht.")
    a("")
    return "\n".join(L_) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cache", required=True)
    p.add_argument("--laeufe", type=int, default=16)
    p.add_argument("--aus", default=os.path.join(HIER, "rueckblick"))
    p.add_argument("--ende", default="2026-12-31")
    p.add_argument("--schritte", default="kand,modell,depot,bot,fehler,gelernt")
    p.add_argument("--md", default=os.path.join(HIER, "RUECKBLICK.md"))
    p.add_argument("--nur-text", action="store_true", help="nur RUECKBLICK.md aus ergebnis.json neu schreiben")
    a = p.parse_args()
    if a.nur_text:
        with open(os.path.join(a.aus, "ergebnis.json"), encoding="utf-8") as f:
            text = markdown(json.load(f))
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(text)
        return
    schritte = set(a.schritte.split(","))
    os.makedirs(a.aus, exist_ok=True)
    zwischen = os.path.join(a.cache, "zwischen")
    os.makedirs(zwischen, exist_ok=True)
    t0 = time.time()
    uni = pd.read_csv(os.path.join(a.cache, "universum.csv"))
    tickers = [t for t in uni["ticker"] if os.path.exists(D.kurs_datei(a.cache, t))]
    sektor_von = dict(zip(uni["ticker"], uni["sektor"]))
    spy, qqq, markt_df = M.markt(a.cache)
    fx = D.lies_kurse(a.cache, "EURUSD=X")["Close"]
    ende = pd.Timestamp(a.ende)
    kand_datei = os.path.join(zwischen, "kandidaten.pkl")
    if "kand" in schritte or not os.path.exists(kand_datei):
        kand, _ = M.alle_kandidaten(a.cache, tickers, ende, sektor_von, markt_df)
        kand.to_pickle(kand_datei)
        print(f"Kandidaten: {len(kand)} aus {kand['ticker'].nunique()} Aktien ({time.time() - t0:.0f} s)", flush=True)
    kand = pd.read_pickle(kand_datei)
    punkte_datei = os.path.join(zwischen, "punkte.pkl")
    if "modell" in schritte or not os.path.exists(punkte_datei):
        protokoll = []
        punkte = L.walk_forward(kand, "2010-01-01", ende, protokoll=protokoll)
        ohne_bilanz = [m for m in M.MERKMALE if m not in M.BILANZ_MERKMALE
                       and m not in ("ueberraschung", "ueberraschung4", "treffer4")]
        punkte_ohne = L.walk_forward(kand, "2010-01-01", ende, merkmale=ohne_bilanz)
        pd.to_pickle({"mit": punkte, "ohne_bilanz": punkte_ohne, "protokoll": protokoll}, punkte_datei)
        print(f"Walk-forward fertig ({time.time() - t0:.0f} s)", flush=True)
    pk = pd.read_pickle(punkte_datei)
    kand["punkte"] = pk["mit"]
    ergebnis = {"stand": pd.Timestamp.now(tz="Europe/Berlin").isoformat(timespec="minutes"),
                "aktien": int(kand["ticker"].nunique()), "signale": int(len(kand)),
                "signale_fertig": int((kand["status"] == "fertig").sum())}
    ergebnis["guete"] = L.guete(kand, pk["mit"])
    ergebnis["guete_ohne_bilanz"] = L.guete(kand, pk["ohne_bilanz"])
    jahre = kand.groupby(kand["tag"].dt.year)
    ergebnis["bilanz_abdeckung"] = {int(j): float(g["gewinnrendite"].notna().mean()) for j, g in jahre}
    ergebnis["ueberraschung_abdeckung"] = {int(j): float(g["ueberraschung"].notna().mean()) for j, g in jahre}
    watch = [t for t in D.watchlist() if t in set(kand["ticker"])]
    ergebnis["watchlist"] = watch
    schwellen = {anteil: L.monats_schwellen(kand, anteil) for anteil in (0.5, 0.3)}
    if "depot" in schritte:
        daten = daten_fuer_depot(a.cache, tickers, fx, ende)
        daten["__SPY__"] = spy
        lage = sw.markt_trend(qqq)
        marktfilter = pd.Series(sw.markt_vortag(lage, spy.index) != 0, index=spy.index)
        kand_ohne = kand.assign(punkte=pk["ohne_bilanz"])
        _G.update(daten=daten, kand=kand, spy=spy, schwellen=schwellen, marktfilter=marktfilter, watchlist=watch)
        # (Name, Auswahl, Ausstieg, Anteil, Marktfilter, nur Watchlist)
        varianten = [
            ("Watchlist: Signale wie heute, ohne Modell", "alle", "normal", None, False, True),
            ("Watchlist: Lernmodell beste 50 %", "modell", "normal", 0.5, False, True),
            ("Watchlist: Lernmodell beste 30 %", "modell", "normal", 0.3, False, True),
            ("Watchlist: ohne Modell · Stop zum Schluss", "alle", "schluss", None, False, True),
            ("Watchlist: ohne Modell · Panik-Regel", "alle", "panik", None, False, True),
            ("Watchlist: ohne Modell · starke Aktien halten", "alle", "stark", None, False, True),
            ("Watchlist: Lernmodell 30 % · Stop zum Schluss", "modell", "schluss", 0.3, False, True),
            ("Watchlist: Lernmodell 30 % · Panik-Regel", "modell", "panik", 0.3, False, True),
            ("Watchlist: Lernmodell 30 % · starke Aktien halten", "modell", "stark", 0.3, False, True),
            ("Alle Aktien: Signale wie heute, ohne Modell", "alle", "normal", None, False, False),
            ("Alle Aktien: Lernmodell beste 30 %", "modell", "normal", 0.3, False, False),
            ("Alle Aktien: Lernmodell 30 % + Marktfilter", "modell", "normal", 0.3, True, False),
            ("Alle Aktien: Lernmodell 30 % · Panik-Regel", "modell", "panik", 0.3, False, False),
        ]
        jobs = [(n, von, bis, aus, var, ant, fil, wl, s) for (n, aus, var, ant, fil, wl) in varianten
                for von, bis in ZEITRAEUME.values() for s in range(a.laeufe)]
        tab, trades_basis = {}, {}
        with ProcessPoolExecutor(4) as ex:
            for name, von, seed, kz, tr in ex.map(_lauf, jobs, chunksize=2):
                tab.setdefault(name, {}).setdefault(von, []).append(kz)
                if tr is not None:
                    trades_basis[(name, von)] = tr
        # ohne Bilanzdaten (gleiche Auswahl 30 %)
        _G["kand"] = kand_ohne
        _G["schwellen"] = {0.3: L.monats_schwellen(kand_ohne, 0.3)}
        jobs = [(name, von, bis, "modell", "normal", 0.3, False, wl, s)
                for name, wl in (("Watchlist: Lernmodell 30 % ohne Bilanzdaten", True),
                                 ("Alle Aktien: Lernmodell 30 % ohne Bilanzdaten", False))
                for von, bis in ZEITRAEUME.values() for s in range(a.laeufe)]
        with ProcessPoolExecutor(4) as ex:
            for name, von, seed, kz, tr in ex.map(_lauf, jobs, chunksize=2):
                tab.setdefault(name, {}).setdefault(von, []).append(kz)
        _G["kand"], _G["schwellen"] = kand, schwellen
        ergebnis["depot"] = {n: {z: {k: float(np.nanmean([e[k] for e in liste])) for k in liste[0]}
                                 | {"rendite_streuung": float(np.std([e["rendite"] for e in liste]))}
                                 for z, liste in je.items()} for n, je in tab.items()}
        ergebnis["halten"] = {}
        for name, df in (("S&P 500 kaufen und halten", spy), ("Nasdaq-100 kaufen und halten", qqq)):
            ergebnis["halten"][name] = {von: P.kaufen_und_halten(df, fx, pd.Timestamp(von), pd.Timestamp(bis))
                                        for von, bis in ZEITRAEUME.values()}
        pd.to_pickle(trades_basis, os.path.join(zwischen, "trades.pkl"))
        print(f"Depot fertig ({time.time() - t0:.0f} s)", flush=True)
    if "bot" in schritte:
        # Der echte Bot (Marktfilter, Lernregel) auf der Watchlist – ohne und mit Kaufen nach dem Lernmodell
        sperre = {anteil: bot_sperre(kand, schwellen[anteil], watch) for anteil in (0.3, 0.5)}
        rang = bot_rang(kand, watch)
        bot_varianten = {"jetziger_bot": {}, "bot_rang": {"rang": rang},
                         "bot_mit_lernmodell": {"sperre": sperre[0.3], "rang": rang},
                         "bot_mit_lernmodell_50": {"sperre": sperre[0.5], "rang": rang},
                         "bot_nur_filter": {"sperre": sperre[0.3]}}
        for name in bot_varianten:
            ergebnis[name] = {}
        for von, bis in ZEITRAEUME.values():
            b = min(pd.Timestamp(bis), ende)
            for name, k in bot_varianten.items():
                ergebnis[name][von] = jetziger_bot(a.cache, watch, sektor_von, von, b, min(a.laeufe, 8), **k)
            print(f"Jetziger Bot {von} fertig ({time.time() - t0:.0f} s)", flush=True)
    if "fehler" in schritte:
        # a) alle gedachten Trades: Wie oft verliert ein Signal mit welchem Grund – bei allen und bei den vom Modell
        #    ausgewählten (beste 30 %)? Zeigt, ob das Modell gelernt hat, diese Fehler zu meiden.
        wahl = (kand["punkte"].to_numpy()
                >= kand["tag"].dt.to_period("M").map(schwellen[0.3]).fillna(np.inf).to_numpy())
        ab = kand["tag"] >= pd.Timestamp("2010-01-01")
        tab = F.vergleich(kand[ab], wahl[ab.to_numpy()])
        ergebnis["fehler_signale"] = {"tabelle": tab.to_dict("records"), **tab.attrs}
        # b) Trades im Depot (erster Lauf je Zeitraum)
        trades_basis = pd.read_pickle(os.path.join(zwischen, "trades.pkl"))
        daten = _G.get("daten") or daten_fuer_depot(a.cache, tickers, fx, ende)
        branche = M.branchen_index(a.cache)
        spy_c = spy["Close"]
        fehler_tab = {}
        for name in ("Watchlist: Signale wie heute, ohne Modell", "Watchlist: Lernmodell beste 30 %",
                     "Alle Aktien: Signale wie heute, ohne Modell", "Alle Aktien: Lernmodell beste 30 %"):
            alle_tr = []
            for von in [v for v, _ in ZEITRAEUME.values()]:
                for t in trades_basis.get((name, von), []):
                    t = dict(t)
                    t["fehler"] = F.gruende(t, daten[t["ticker"]], spy_c, branche.get(t["sektor"]), t.get("gelaufen10"))
                    alle_tr.append(t)
            fehler_tab[name] = F.auswertung(alle_tr).to_dict("records")
            fehler_tab[name + " (Trades)"] = len(alle_tr)
        ergebnis["fehler"] = fehler_tab
    if "gelernt" in schritte:
        ergebnis["gelernt"] = L.was_gelernt(kand, kand["tag"].max())
    aend = os.path.join(a.cache, "sp500_aenderungen.csv")
    if os.path.exists(aend):
        try:
            ch = pd.read_csv(aend, header=[0, 1])
            ergebnis["sp500_entfernt_seit_2010"] = int(sum(
                1 for x in ch.iloc[:, 0].astype(str) if any(str(j) in x for j in range(2010, 2027))))
        except Exception:  # noqa: BLE001
            pass
    datei = os.path.join(a.aus, "ergebnis.json")
    if os.path.exists(datei):  # nur einzelne Schritte neu gerechnet: Rest behalten
        with open(datei, encoding="utf-8") as f:
            ergebnis = {**json.load(f), **ergebnis}
    with open(datei, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=1, default=float)
    with open(a.md, "w", encoding="utf-8") as f:
        f.write(markdown(ergebnis))
    print(f"Fertig ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
