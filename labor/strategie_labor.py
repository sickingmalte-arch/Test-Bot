"""Strategie-Labor: sucht nachts selbstständig nach einer Handelsstrategie für Tech-Aktien (long und short).

Bauplan und Regeln stehen in labor/PROMPT.md. Kurz:
- beobachtet den ganzen Markt (alle Aktien aus BRANCHEN im Swing-Bot), handelt nur Technologie und Kommunikation,
- erzeugt Strategien als Baupläne aus Genen, prüft sie Walk-Forward (3 Jahre suchen, 1 unbekanntes Jahr handeln),
- vergleicht mit Nasdaq-100 halten, Tech-Aktien halten und dem Swing-Bot,
- merkt sich in labor/gedaechtnis.json, welche Gene im Testjahr verloren haben, und zieht sie seltener,
- führt ein eigenes Übungsdepot mit Spielgeld (keine echten Orders).

Der Swing-Bot (swing_scanner.py) bleibt unverändert; von dort kommen nur die Branchenliste und die Kosten.

Aufruf:
    python labor/strategie_labor.py                                   # Yahoo-Kurse ab 2010 (GitHub Actions)
    python labor/strategie_labor.py --daten tests/daten/kurse --budget klein --ausgabe /tmp/labor   # ohne Internet
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import math
import pathlib
import random
import sys
import time

import numpy as np
import pandas as pd

WURZEL = pathlib.Path(__file__).resolve().parents[1]
LABOR = WURZEL / "labor"

ZIEL_RENDITE = 30.0          # Ziel: Rendite pro Jahr in % nach Kosten
MAX_RUECKGANG = 25.0         # ... bei höchstens so viel % größtem Rückgang
START_KAPITAL = 10_000.0     # Spielgeld in US-Dollar
LEIH_ZINS = 0.06             # Zinsen im Jahr auf geliehenes Geld (Hebel), wie im Hebel-Test des Swing-Bots
SHORT_GEBUEHR = 0.01         # Leihgebühr im Jahr für leerverkaufte Aktien
TRAIN_JAHRE = 3              # Walk-Forward: so viele Jahre suchen, dann 1 unbekanntes Jahr handeln
VORLAUF_TAGE = 250           # so viele Tage brauchen die Indikatoren (200-Tage-Linie, 250-Tage-Momentum)
TECH_BRANCHEN = ("Technologie", "Kommunikation")
MARKT_TICKER = "QQQ"
MIN_TRADES = 8               # weniger Trades im Training: Strategie zählt als zu zufällig
VERDACHT_UNTER = 30          # unter so vielen Belegen ist eine Lehre nur ein Verdacht

# Der Bauplan einer Strategie: jedes Gen und seine erlaubten Werte
GENE = {
    "familie": ["momentum", "ausbruch", "ruecksetzer"],
    "rueckblick": [20, 60, 120, 250],          # Tage für Momentum bzw. Ausbruch
    "trendlinie": [50, 100, 200],              # Long nur über, Short nur unter dieser Linie
    "marktfilter": ["qqq", "breite", "beides", "aus"],
    "markt_ausstieg": [True, False],           # Positionen schließen, wenn die Marktampel umspringt
    "short": ["aus", "nur_baerenmarkt", "immer"],
    "max_long": [2, 3, 4, 5, 6],
    "max_short": [1, 2, 3],
    "stop_atr": [2.0, 3.0, 4.0, 6.0, None],
    "zeitstopp": [10, 20, 40, 60, None],
    "umschichten": [5, 10, 20],                # nur Momentum: alle so viele Tage neu sortieren
    "rsi_grenze": [5, 10, 15],                 # nur Rücksetzer: RSI(2) unter dieser Grenze
    "hebel": [1.0, 1.25, 1.5],
}

FAMILIEN_NAME = {"momentum": "Momentum-Rotation", "ausbruch": "Ausbruch", "ruecksetzer": "Rücksetzer"}

# Vergleich mit dem Swing-Bot aus der README („Gelernt – Hebel und 4-Stunden-Kerzen“): Ø der 6 Testfälle 2010–2026
SWING_BOT_REFERENZ = {"rendite": 8.4, "rueckgang": "10–16", "quelle": "README / gehirn: Test 2010–2026, Ø aus 6 Fällen"}

BUDGETS = {  # Zufallsbaupläne, Generationen, Kinder je Generation
    "klein": (16, 2, 8),
    "normal": (60, 3, 24),
    "gross": (150, 5, 40),
}


def swing_bot():
    """swing_scanner.py als Modul laden, ohne den Bot zu starten (nur Branchen und Kosten werden gelesen)."""
    spec = importlib.util.spec_from_file_location("swing_scanner", WURZEL / "swing_scanner.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


# ---------------------------------------------------------------------------------------------------------------
# Daten
# ---------------------------------------------------------------------------------------------------------------

def lade_ordner(ordner):
    """Tageskerzen aus CSV-Dateien (Date, Open, High, Low, Close, Volume), z. B. tests/daten/kurse."""
    daten = {}
    for datei in sorted(pathlib.Path(ordner).glob("*.csv")):
        if "=" in datei.stem:  # Wechselkurse
            continue
        df = pd.read_csv(datei, index_col=0)
        df.index = pd.to_datetime(df.index)
        daten[datei.stem] = df[["Open", "High", "Low", "Close"]].astype(float)
    return daten


def lade_yahoo(ticker, ab="2010-01-01"):
    """Tageskerzen von Yahoo (um Splits und Dividenden bereinigt) in einem Rutsch."""
    import yfinance as yf

    roh = yf.download(sorted(ticker), start=ab, interval="1d", auto_adjust=True, group_by="ticker",
                      progress=False, threads=True)
    daten = {}
    for t in ticker:
        if isinstance(roh.columns, pd.MultiIndex):
            if t not in roh.columns.get_level_values(0):
                continue
            df = roh[t]
        else:
            df = roh
        df = df[["Open", "High", "Low", "Close"]].dropna()
        if len(df) > VORLAUF_TAGE:
            df.index = pd.to_datetime(df.index).tz_localize(None)
            daten[t] = df.astype(float)
    return daten


class Markt:
    """Alle Kurse auf einem gemeinsamen Kalender als Matrizen (Tage × Aktien) plus Indikatoren mit Zwischenspeicher.
    Jeder Indikator am Tag t nutzt nur Kurse bis zum Schluss von Tag t."""

    def __init__(self, daten, branche):
        if MARKT_TICKER not in daten:
            raise ValueError(f"{MARKT_TICKER} fehlt – ohne Nasdaq-100 gibt es keine Marktampel und keinen Vergleich.")
        aktien = sorted(t for t in daten if t != MARKT_TICKER)
        self.tage = daten[MARKT_TICKER].index
        self.ticker = aktien
        self.branche = {t: branche.get(t, t) for t in aktien}
        self.tech = np.array([self.branche[t] in TECH_BRANCHEN for t in aktien])
        if not self.tech.any():
            raise ValueError("Keine Tech-Aktie in den Daten – das Labor handelt nur Technologie und Kommunikation.")

        def feld(name):
            return pd.DataFrame({t: daten[t][name] for t in aktien}).reindex(self.tage)

        self.O, self.H, self.L, self.C = (feld(n) for n in ("Open", "High", "Low", "Close"))
        self.C_voll = self.C.ffill()  # Bewertung an Tagen ohne Kurs mit dem letzten Schluss
        self.markt = daten[MARKT_TICKER].reindex(self.tage)
        self._cache = {}
        self.o, self.h, self.l = self.O.to_numpy(), self.H.to_numpy(), self.L.to_numpy()
        self.c, self.c_voll = self.C.to_numpy(), self.C_voll.to_numpy()
        self.atr = self._atr()
        self.rsi2 = self._rsi(2)
        qqq = self.markt["Close"]
        self.qqq = qqq.to_numpy()
        self.qqq_ok = (qqq > qqq.rolling(200).mean()).to_numpy()
        sma200 = self.C.rolling(200).mean()
        gueltig = sma200.notna()
        ueber = (self.C > sma200) & gueltig
        self.breite = (ueber.sum(axis=1) / gueltig.sum(axis=1).replace(0, np.nan)).to_numpy()
        self.breite_ok = np.nan_to_num(self.breite, nan=0.0) > 0.5

    def _atr(self):
        vorher = self.C.shift()
        spannen = [self.H - self.L, (self.H - vorher).abs(), (self.L - vorher).abs()]
        tr = pd.concat([s.stack(future_stack=True) for s in spannen], axis=1).max(axis=1).unstack()
        tr = tr.reindex(index=self.tage, columns=self.ticker)
        return tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy()

    def _rsi(self, n):
        d = self.C.diff()
        auf = d.where(d > 0, 0.0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        ab = (-d.where(d < 0, 0.0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        return (100 - 100 / (1 + auf / ab)).to_numpy()

    def sma(self, n):
        return self._merke(("sma", n), lambda: self.C.rolling(n).mean().to_numpy())

    def momentum(self, n):
        return self._merke(("mom", n), lambda: (self.C / self.C.shift(n) - 1).to_numpy())

    def hoch(self, n):
        return self._merke(("hoch", n), lambda: self.H.shift(1).rolling(n).max().to_numpy())

    def tief(self, n):
        return self._merke(("tief", n), lambda: self.L.shift(1).rolling(n).min().to_numpy())

    def _merke(self, schluessel, rechne):
        if schluessel not in self._cache:
            self._cache[schluessel] = rechne()
        return self._cache[schluessel]

    def jahr_bereich(self, jahr):
        """(erster, letzter) Tagesindex eines Kalenderjahrs oder None."""
        idx = np.flatnonzero(self.tage.year == jahr)
        return (int(idx[0]), int(idx[-1])) if len(idx) else None


# ---------------------------------------------------------------------------------------------------------------
# Strategie: Signale aus dem Bauplan
# ---------------------------------------------------------------------------------------------------------------

def signale(m, g):
    """Bool-Matrizen (Tage × Aktien) für Einstieg und Ausstieg, dazu die Rangfolge. Alles zum Schlusskurs von Tag t."""
    c, lb = m.c, g["rueckblick"]
    trend = m.sma(g["trendlinie"])
    mom = m.momentum(lb)
    with np.errstate(invalid="ignore"):
        ueber, unter = c > trend, c < trend
        if g["familie"] == "momentum":
            long_ein, short_ein = (mom > 0) & ueber, (mom < 0) & unter
            long_aus, short_aus = ~long_ein, ~short_ein
        elif g["familie"] == "ausbruch":
            long_ein, short_ein = (c > m.hoch(lb)) & ueber, (c < m.tief(lb)) & unter
            halb = max(5, lb // 2)
            long_aus, short_aus = c < m.tief(halb), c > m.hoch(halb)
        else:  # Rücksetzer im Trend
            grenze = g["rsi_grenze"]
            long_ein, short_ein = (m.rsi2 < grenze) & ueber, (m.rsi2 > 100 - grenze) & unter
            long_aus, short_aus = m.rsi2 > 70, m.rsi2 < 30
    gueltig = ~np.isnan(mom) & ~np.isnan(m.atr) & m.tech[None, :]
    return long_ein & gueltig, short_ein & gueltig, long_aus, short_aus, np.nan_to_num(mom, nan=0.0)


def marktampel(m, g):
    """Je Tag: Long erlaubt? Short erlaubt?"""
    filt = g["marktfilter"]
    long_ok = {"qqq": m.qqq_ok, "breite": m.breite_ok, "beides": m.qqq_ok & m.breite_ok,
               "aus": np.ones(len(m.tage), dtype=bool)}[filt]
    baer = ~(m.qqq_ok if filt == "aus" else long_ok)
    short_ok = {"aus": np.zeros(len(m.tage), dtype=bool), "nur_baerenmarkt": baer,
                "immer": np.ones(len(m.tage), dtype=bool)}[g["short"]]
    return long_ok, short_ok


# ---------------------------------------------------------------------------------------------------------------
# Testmotor: Depot Tag für Tag
# ---------------------------------------------------------------------------------------------------------------

def simuliere(m, g, start, ende, kapital=START_KAPITAL, glattstellen=True, kosten=None):
    """Handelt den Bauplan g von Tag start bis ende (Indizes). Entscheidung zum Schluss, Ausführung zur nächsten
    Eröffnung, Stop auch innerhalb des Tages (Kurslücke: Eröffnungskurs). Gibt Wertverlauf, Trades und Kosten zurück."""
    gebuehr, spread = kosten or KOSTEN
    long_ein, short_ein, long_aus, short_aus, rang = signale(m, g)
    long_ok, short_ok = marktampel(m, g)
    plaetze = g["max_long"] + (g["max_short"] if g["short"] != "aus" else 0)
    bargeld, positionen, trades = kapital, {}, []
    auftraege_aus, auftraege_ein = set(), []
    werte, zinsen, leihe, gebuehren = [], 0.0, 0.0, 0.0

    def schliessen(j, kurs_roh, tag, grund):
        nonlocal bargeld, gebuehren
        p = positionen.pop(j)
        kurs = kurs_roh * (1 - p["r"] * spread)  # Long verkauft etwas billiger, Short kauft etwas teurer zurück
        bargeld += p["r"] * p["stueck"] * kurs - gebuehr
        gebuehren += gebuehr
        ergebnis = p["r"] * p["stueck"] * (kurs - p["kurs"]) - 2 * gebuehr
        trades.append({"ticker": m.ticker[j], "richtung": "long" if p["r"] > 0 else "short", "grund": grund,
                       "kauf": str(m.tage[p["tag"]].date()), "verkauf": str(m.tage[tag].date()),
                       "einstieg": round(p["kurs"], 2), "ausstieg": round(kurs, 2), "ergebnis": round(ergebnis, 2)})

    for t in range(start, ende + 1):
        o, h, l = m.o[t], m.h[t], m.l[t]
        # 1. Eröffnung: Aufträge vom Vorabend
        for j in sorted(auftraege_aus):
            if j in positionen and not np.isnan(o[j]):
                schliessen(j, o[j], t, positionen[j]["grund_aus"])
                auftraege_aus.discard(j)
        for j, r, stueck in auftraege_ein:
            if j in positionen or np.isnan(o[j]):
                continue
            kurs = o[j] * (1 + r * spread)
            bargeld -= r * stueck * kurs + gebuehr
            gebuehren += gebuehr
            stop = kurs - r * g["stop_atr"] * m.atr[t - 1, j] if g["stop_atr"] else None
            positionen[j] = {"r": r, "stueck": stueck, "kurs": kurs, "stop": stop, "tag": t, "grund_aus": ""}
        auftraege_ein = []
        # 2. Stop innerhalb des Tages
        for j in list(positionen):
            p = positionen[j]
            if p["stop"] is None or np.isnan(l[j]):
                continue
            if p["r"] > 0 and l[j] <= p["stop"]:
                schliessen(j, min(o[j], p["stop"]), t, "Stop (Kurslücke)" if o[j] < p["stop"] else "Stop")
            elif p["r"] < 0 and h[j] >= p["stop"]:
                schliessen(j, max(o[j], p["stop"]), t, "Stop (Kurslücke)" if o[j] > p["stop"] else "Stop")
        # 3. Schluss: Zinsen, Leihgebühr, Bewertung
        schluss = m.c_voll[t]
        if bargeld < 0:
            zinsen += -bargeld * LEIH_ZINS / 252
            bargeld -= -bargeld * LEIH_ZINS / 252
        short_wert = sum(p["stueck"] * schluss[j] for j, p in positionen.items() if p["r"] < 0)
        leihe += short_wert * SHORT_GEBUEHR / 252
        bargeld -= short_wert * SHORT_GEBUEHR / 252
        wert = bargeld + sum(p["r"] * p["stueck"] * schluss[j] for j, p in positionen.items())
        if t == ende and glattstellen:
            for j in list(positionen):
                schliessen(j, schluss[j], t, "Ende des Zeitraums")
            wert = bargeld
        werte.append(wert)
        if wert <= 0:  # Totalverlust: Rest des Zeitraums bleibt bei null
            werte += [0.0] * (ende - t)
            break
        if t == ende:
            break
        # 4. Entscheidung für morgen
        umschichten = g["familie"] != "momentum" or (t - start) % g["umschichten"] == 0
        for j, p in positionen.items():
            gruende = []
            if g["zeitstopp"] and t - p["tag"] + 1 >= g["zeitstopp"]:
                gruende.append("Zeitstopp")
            if g["markt_ausstieg"] and not (long_ok[t] if p["r"] > 0 else short_ok[t]):
                gruende.append("Marktampel")
            if umschichten and (long_aus[t, j] if p["r"] > 0 else short_aus[t, j]):
                gruende.append("Signal vorbei")
            if gruende:
                p["grund_aus"] = gruende[0]
                auftraege_aus.add(j)
        if not umschichten:
            continue
        platz_wert = g["hebel"] * wert / plaetze
        brutto = sum(p["stueck"] * schluss[j] for j, p in positionen.items() if j not in auftraege_aus)
        offen = {r: sum(1 for j, p in positionen.items() if p["r"] == r and j not in auftraege_aus) for r in (1, -1)}
        for r, erlaubt, maske, maximal in ((1, long_ok[t], long_ein[t], g["max_long"]),
                                           (-1, short_ok[t], short_ein[t], g["max_short"] if g["short"] != "aus" else 0)):
            if not erlaubt or offen[r] >= maximal:
                continue
            kandidaten = [j for j in np.flatnonzero(maske) if j not in positionen]
            kandidaten.sort(key=lambda j: -r * rang[t, j])
            for j in kandidaten[: maximal - offen[r]]:
                stueck = math.floor(platz_wert / m.c[t, j])
                if stueck < 1 or brutto + stueck * m.c[t, j] > g["hebel"] * wert * 1.01:
                    continue
                auftraege_ein.append((j, r, stueck))
                brutto += stueck * m.c[t, j]
    offene = [{"ticker": m.ticker[j], "richtung": "long" if p["r"] > 0 else "short", "stueck": p["stueck"],
               "einstieg": round(p["kurs"], 2), "seit": str(m.tage[p["tag"]].date()),
               "stop": round(p["stop"], 2) if p["stop"] else None,
               "kurs": round(float(m.c_voll[ende, j]), 2),
               "ergebnis": round(p["r"] * p["stueck"] * (m.c_voll[ende, j] - p["kurs"]), 2)}
              for j, p in positionen.items()]
    morgen = [{"ticker": m.ticker[j], "aktion": "kaufen" if r > 0 else "leerverkaufen", "stueck": s}
              for j, r, s in auftraege_ein]
    morgen += [{"ticker": m.ticker[j], "aktion": "schließen", "grund": positionen[j]["grund_aus"]}
               for j in sorted(auftraege_aus) if j in positionen]
    return {"werte": np.array(werte), "trades": trades, "offen": offene, "morgen": morgen,
            "kosten": round(gebuehren + zinsen + leihe, 2), "zinsen": round(zinsen, 2), "leihe": round(leihe, 2)}


KOSTEN = (1.0, 0.001)  # Gebühr je Order und Spread wie im Swing-Bot; wird beim Start aus swing_scanner.py gelesen


def kennzahlen(werte, trades=()):
    """Rendite pro Jahr, größter Rückgang, Trefferquote und Ergebnis von Long und Short."""
    werte = np.asarray(werte, dtype=float)
    tage = max(len(werte), 1)
    gesamt = werte[-1] / werte[0] if len(werte) and werte[0] > 0 else 0.0
    rendite = (gesamt ** (252 / tage) - 1) * 100 if gesamt > 0 else -100.0
    spitze = np.maximum.accumulate(werte) if len(werte) else np.array([1.0])
    rueckgang = float(np.max(1 - werte / spitze) * 100) if len(werte) else 0.0
    gewinner = sum(t["ergebnis"] > 0 for t in trades)
    return {
        "rendite": round(rendite, 2), "rueckgang": round(rueckgang, 2), "trades": len(trades),
        "quote": round(100 * gewinner / len(trades), 1) if trades else None,
        "long": round(sum(t["ergebnis"] for t in trades if t["richtung"] == "long"), 2),
        "short": round(sum(t["ergebnis"] for t in trades if t["richtung"] == "short"), 2),
        "short_trades": sum(t["richtung"] == "short" for t in trades),
    }


def fitness(k):
    """Zielfunktion der Suche: Rendite (gedeckelt, damit kein Glückstreffer alles dominiert) minus Strafe für zu
    tiefe Rückgänge. Unter MIN_TRADES Trades ist es eher Halten mit Glück als eine Strategie: fällt praktisch raus."""
    strafe = 2 * max(0.0, k["rueckgang"] - MAX_RUECKGANG) + (100 if k["trades"] < MIN_TRADES else 0)
    return min(k["rendite"], 80.0) - strafe


# ---------------------------------------------------------------------------------------------------------------
# Suche: Zufall, Mutation und Gedächtnis
# ---------------------------------------------------------------------------------------------------------------

def schluessel(g):
    return json.dumps(g, sort_keys=True)


def ziehe(rng, gewichte, gen):
    werte = GENE[gen]
    w = [gewichte.get(gen, {}).get(json.dumps(v), 1.0) for v in werte]
    return rng.choices(werte, weights=w, k=1)[0]


def zufalls_bauplan(rng, gewichte):
    return {gen: ziehe(rng, gewichte, gen) for gen in GENE}


def mutiere(rng, g, gewichte):
    kind = dict(g)
    for gen in rng.sample(list(GENE), k=rng.choice((1, 2))):
        kind[gen] = ziehe(rng, gewichte, gen)
    return kind


def suche(m, start, ende, rng, gewichte, budget, startwerte=()):
    """Sucht im Zeitraum [start, ende] die besten Baupläne. Gibt sie sortiert nach Zielfunktion zurück."""
    n_zufall, generationen, kinder = BUDGETS[budget]
    gesehen = {}

    def bewerte(g):
        s = schluessel(g)
        if s not in gesehen:
            erg = simuliere(m, g, start, ende)
            k = kennzahlen(erg["werte"], erg["trades"])
            gesehen[s] = {"genom": g, "kennzahlen": k, "fitness": fitness(k)}
        return gesehen[s]

    for g in list(startwerte) + [zufalls_bauplan(rng, gewichte) for _ in range(n_zufall)]:
        bewerte(g)
    for _ in range(generationen):
        beste = sorted(gesehen.values(), key=lambda e: -e["fitness"])[:5]
        for _ in range(kinder):
            bewerte(mutiere(rng, rng.choice(beste)["genom"], gewichte))
    return sorted(gesehen.values(), key=lambda e: -e["fitness"])


def gewichte_aus(belege):
    """Ziehgewichte je Gen-Wert aus den Belegen: Werte, die im Testjahr hinter dem Nasdaq-100 lagen, werden seltener
    gezogen. Geschrumpft (+3 Phantom-Belege mit 0), damit wenige Belege wenig bewirken; nie unter 0,3."""
    summe, anzahl = {}, {}
    for b in belege:
        for gen, wert in b["genom"].items():
            if gen not in GENE:
                continue
            k = (gen, json.dumps(wert))
            summe[k] = summe.get(k, 0.0) + max(-50.0, min(50.0, b["ueberschuss"]))
            anzahl[k] = anzahl.get(k, 0) + 1
    gewichte = {}
    for (gen, wert), s in summe.items():
        schnitt = s / (anzahl[(gen, wert)] + 3)
        gewichte.setdefault(gen, {})[wert] = round(min(3.0, max(0.3, math.exp(schnitt / 20))), 3)
    return gewichte


# ---------------------------------------------------------------------------------------------------------------
# Walk-Forward und Vergleich
# ---------------------------------------------------------------------------------------------------------------

def halten(m, start, ende, nur_tech=True):
    """Wertverlauf von 10.000 $, verteilt auf alle (Tech-)Aktien zum Schluss vor dem Start und dann nur gehalten."""
    spalten = np.flatnonzero(m.tech if nur_tech else np.ones(len(m.ticker), dtype=bool))
    basis = m.c[start - 1, spalten]
    ok = ~np.isnan(basis)
    verlauf = m.c_voll[start:ende + 1, spalten[ok]] / basis[ok]
    return START_KAPITAL * np.nanmean(verlauf, axis=1)


def nasdaq(m, start, ende):
    return START_KAPITAL * m.qqq[start:ende + 1] / m.qqq[start - 1]


def walk_forward(m, rng, budget, protokoll=print):
    """Für jedes Testjahr: Suche nur mit den TRAIN_JAHRE Jahren davor, dann das unbekannte Jahr handeln.
    Gelernt wird nur aus Testjahren, die schon vorbei sind (die Gewichte starten neutral)."""
    jahre = sorted(set(m.tage.year))
    # erstes Trainingsjahr: das erste ganze Jahr, in dem alle Indikatoren schon rechnen
    erstes = next((j for j in jahre if m.jahr_bereich(j)[0] >= VORLAUF_TAGE), None)
    schritte, belege, kette, kette_qqq, kette_tech = [], [], [], [], []
    vorheriger = None
    for jahr in jahre:
        if erstes is None or jahr < erstes + TRAIN_JAHRE:
            continue
        test = m.jahr_bereich(jahr)
        train_start = m.jahr_bereich(jahr - TRAIN_JAHRE)[0]
        train_ende = test[0] - 1
        gewichte = gewichte_aus(belege)
        startwerte = [vorheriger] if vorheriger else []
        rangliste = suche(m, train_start, train_ende, rng, gewichte, budget, startwerte)
        sieger = rangliste[0]
        oos = simuliere(m, sieger["genom"], test[0], test[1])
        k = kennzahlen(oos["werte"], oos["trades"])
        q = kennzahlen(nasdaq(m, *test))
        tech = kennzahlen(halten(m, *test))
        # Belege für das Gedächtnis: die 5 besten Baupläne aus dem Training, alle im Testjahr nachgeprüft
        for platz, e in enumerate(rangliste[:5]):
            if platz == 0:
                nach = k
            else:
                r = simuliere(m, e["genom"], test[0], test[1])
                nach = kennzahlen(r["werte"], r["trades"])
            belege.append({"jahr": int(jahr), "genom": e["genom"], "platz": platz + 1,
                           "train_rendite": e["kennzahlen"]["rendite"], "oos_rendite": nach["rendite"],
                           "oos_rueckgang": nach["rueckgang"], "short": nach["short"], "long": nach["long"],
                           "short_trades": nach["short_trades"],
                           "qqq": q["rendite"], "ueberschuss": round(nach["rendite"] - q["rendite"], 2)})
        schritte.append({"jahr": int(jahr), "bis": str(m.tage[test[1]].date()), "genom": sieger["genom"],
                         "training": sieger["kennzahlen"], "test": k, "qqq": q, "tech_halten": tech,
                         "kosten": oos["kosten"], "geprueft": len(rangliste)})
        kette.append(oos["werte"] / START_KAPITAL)
        kette_qqq.append(nasdaq(m, *test) / START_KAPITAL)
        kette_tech.append(halten(m, *test) / START_KAPITAL)
        vorheriger = sieger["genom"]
        protokoll(f"  {jahr}: Test {k['rendite']:+.1f} % (Rückgang {k['rueckgang']:.1f} %) · Training "
                  f"{sieger['kennzahlen']['rendite']:+.1f} % · Nasdaq-100 {q['rendite']:+.1f} % · "
                  f"{FAMILIEN_NAME[sieger['genom']['familie']]} · {len(rangliste)} Baupläne")

    def verkette(teile):
        if not teile:
            return np.array([START_KAPITAL])
        werte, stand = [], 1.0
        for teil in teile:
            werte.extend(stand * teil)
            stand *= teil[-1]
        return START_KAPITAL * np.array(werte)

    gesamt = kennzahlen(verkette(kette))
    gesamt["trades"] = sum(s["test"]["trades"] for s in schritte)
    gewinner = sum((s["test"]["quote"] or 0) * s["test"]["trades"] / 100 for s in schritte)
    gesamt["quote"] = round(100 * gewinner / gesamt["trades"], 1) if gesamt["trades"] else None
    gesamt["short_trades"] = sum(s["test"]["short_trades"] for s in schritte)
    gesamt["short"] = round(sum(s["test"]["short"] for s in schritte), 2)
    gesamt["long"] = round(sum(s["test"]["long"] for s in schritte), 2)
    return {"schritte": schritte, "belege": belege, "gesamt": gesamt,
            "qqq": kennzahlen(verkette(kette_qqq)), "tech_halten": kennzahlen(verkette(kette_tech)),
            "verlauf": verkette(kette), "verlauf_qqq": verkette(kette_qqq)}


# ---------------------------------------------------------------------------------------------------------------
# Lehren aus Fehlern
# ---------------------------------------------------------------------------------------------------------------

def de(x, nachkomma=1, vorzeichen=False):
    text = f"{x:+,.{nachkomma}f}" if vorzeichen else f"{x:,.{nachkomma}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def mittel(werte):
    werte = list(werte)
    return sum(werte) / len(werte) if werte else None


def lehren(wf, belege):
    """Lehren in einfachen Sätzen, jede mit Zahlen. 'bestaetigt' erst ab VERDACHT_UNTER Belegen."""
    aus = []
    schritte = wf["schritte"]
    if schritte:
        abstand = mittel(s["training"]["rendite"] - s["test"]["rendite"] for s in schritte)
        aus.append({"titel": "Überanpassung",
                    "text": f"Beim Suchen sah die beste Strategie im Schnitt {de(abstand)} Prozentpunkte pro Jahr "
                            f"besser aus als danach im unbekannten Jahr. Nur die Testjahre zählen.",
                    "belege": len(schritte), "status": "bestaetigt" if abstand > 5 else "zweifel"})
        erreicht = sum(s["test"]["rendite"] >= ZIEL_RENDITE for s in schritte)
        g = wf["gesamt"]
        aus.append({"titel": "Ziel 30 % pro Jahr",
                    "text": f"In {erreicht} von {len(schritte)} Testjahren erreicht. Über alle Testjahre "
                            f"{de(g['rendite'])} % pro Jahr bei {de(g['rueckgang'])} % größtem Rückgang.",
                    "belege": len(schritte),
                    "status": "bestaetigt" if g["rendite"] >= ZIEL_RENDITE and g["rueckgang"] <= MAX_RUECKGANG
                    else "zweifel"})
    if belege:
        mit_short = [b for b in belege if b.get("short_trades", 0) > 0]
        ohne_short = [b for b in belege if b["genom"]["short"] == "aus"]
        if not mit_short:
            aus.append({"titel": "Shorts", "text": "In den geprüften Testjahren gab es noch keinen Short-Trade: Die "
                        "besten Baupläne hatten Shorts aus, oder die Marktampel stand nie auf Rot.",
                        "belege": len(belege), "status": "zweifel"})
        else:
            verlust = sum(b["short"] < 0 for b in mit_short)
            satz = (f"In {verlust} von {len(mit_short)} geprüften Testjahren mit Shorts haben die Shorts Geld "
                    f"gekostet (zusammen {de(sum(b['short'] for b in mit_short), 0)} $).")
            if ohne_short:
                satz += (f" Ø Vorsprung vor dem Nasdaq-100: mit Shorts {de(mittel(b['ueberschuss'] for b in mit_short), 1, True)}"
                         f", ohne {de(mittel(b['ueberschuss'] for b in ohne_short), 1, True)} Prozentpunkte.")
            aus.append({"titel": "Shorts", "text": satz, "belege": len(mit_short),
                        "status": "bestaetigt" if len(mit_short) >= VERDACHT_UNTER else "zweifel"})
        mit_hebel = [b for b in belege if b["genom"]["hebel"] > 1]
        ohne_hebel = [b for b in belege if b["genom"]["hebel"] == 1]
        if mit_hebel and ohne_hebel:
            aus.append({"titel": "Hebel",
                        "text": f"Ø größter Rückgang im Testjahr mit Hebel {de(mittel(b['oos_rueckgang'] for b in mit_hebel))} %, "
                                f"ohne {de(mittel(b['oos_rueckgang'] for b in ohne_hebel))} %. Ø Rendite mit Hebel "
                                f"{de(mittel(b['oos_rendite'] for b in mit_hebel))} %, ohne "
                                f"{de(mittel(b['oos_rendite'] for b in ohne_hebel))} %.",
                        "belege": len(belege),
                        "status": "bestaetigt" if min(len(mit_hebel), len(ohne_hebel)) >= VERDACHT_UNTER else "zweifel"})
        je_familie = {}
        for b in belege:
            je_familie.setdefault(b["genom"]["familie"], []).append(b["ueberschuss"])
        reihe = sorted(je_familie.items(), key=lambda kv: -mittel(kv[1]))
        aus.append({"titel": "Familien",
                    "text": "Ø Vorsprung vor dem Nasdaq-100 im Testjahr: " + ", ".join(
                        f"{FAMILIEN_NAME[f]} {de(mittel(v), 1, True)} Pkt. ({len(v)}×)" for f, v in reihe) + ".",
                    "belege": len(belege),
                    "status": "bestaetigt" if min(len(v) for v in je_familie.values()) >= VERDACHT_UNTER else "zweifel"})
        gewichte = gewichte_aus(belege)
        seltener = sorted(((w, gen, wert) for gen, ws in gewichte.items() for wert, w in ws.items() if w < 0.8))
        if seltener:
            aus.append({"titel": "Wird seltener ausprobiert",
                        "text": "Diese Gene lagen im Testjahr oft hinter dem Nasdaq-100 und werden seltener gezogen: "
                                + ", ".join(f"{gen} = {json.loads(wert)}" for _, gen, wert in seltener[:5]) + ".",
                        "belege": len(belege), "status": "zweifel"})
    return aus


# ---------------------------------------------------------------------------------------------------------------
# Markt heute und Übungsdepot
# ---------------------------------------------------------------------------------------------------------------

def marktlage(m):
    t = len(m.tage) - 1
    mom63, mom126 = m.momentum(63)[t], m.momentum(126)[t]
    branchen = {}
    for j, tk in enumerate(m.ticker):
        if not np.isnan(mom63[j]):
            branchen.setdefault(m.branche[tk], []).append(mom63[j])
    reihe = sorted(((b, mittel(v)) for b, v in branchen.items()), key=lambda x: -x[1])
    tech = [(m.ticker[j], mom126[j]) for j in np.flatnonzero(m.tech) if not np.isnan(mom126[j])]
    tech.sort(key=lambda x: -x[1])
    return {
        "tag": str(m.tage[t].date()),
        "nasdaq_ueber_200": bool(m.qqq_ok[t]),
        "breite": round(float(m.breite[t]) * 100, 1) if not np.isnan(m.breite[t]) else None,
        "aktien": len(m.ticker), "tech_aktien": int(m.tech.sum()),
        "branchen_3_monate": [{"branche": b, "rendite": round(v * 100, 1)} for b, v in reihe],
        "tech_staerkste": [{"ticker": tk, "rendite_6_monate": round(v * 100, 1)} for tk, v in tech[:5]],
        "tech_schwaechste": [{"ticker": tk, "rendite_6_monate": round(v * 100, 1)}
                             for tk, v in tech[max(5, len(tech) - 5):][::-1]],
    }


def uebungsdepot(m, pfad, vorschlag, neuer_champion):
    """Der Champion handelt ab seinem Starttag vorwärts mit Spielgeld. Er wird nur auf ausdrücklichen Wunsch
    ausgetauscht, damit das Depot ehrlich misst (wie das eingefrorene Übungsdepot des Swing-Bots)."""
    letzter = len(m.tage) - 1
    stand = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None
    if stand is None or neuer_champion:
        stand = {"start": str(m.tage[letzter].date()), "genom": vorschlag,
                 "hinweis": "Champion eingefroren – Austausch nur mit --neuer-champion."}
        pfad.write_text(json.dumps(stand, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    start_tag = pd.Timestamp(stand["start"])
    folgende = np.flatnonzero(m.tage > start_tag)
    if not len(folgende):
        erg = simuliere(m, stand["genom"], letzter, letzter, glattstellen=False)
        return {**stand, "tage": 0, "wert": START_KAPITAL, "rendite": 0.0, "qqq": 0.0, "offen": [],
                "trades": [], "morgen": erg["morgen"], "verlauf": []}
    start = int(folgende[0])
    erg = simuliere(m, stand["genom"], start, letzter, glattstellen=False)
    werte = erg["werte"]
    q = nasdaq(m, start, letzter)
    return {**stand, "tage": len(werte), "wert": round(float(werte[-1]), 2),
            "rendite": round((werte[-1] / START_KAPITAL - 1) * 100, 2),
            "qqq": round((q[-1] / START_KAPITAL - 1) * 100, 2), "offen": erg["offen"], "trades": erg["trades"][-20:],
            "morgen": erg["morgen"], "kosten": erg["kosten"],
            "verlauf": [[str(m.tage[start + i].date()), round(float(w), 2)] for i, w in enumerate(werte)]}


# ---------------------------------------------------------------------------------------------------------------
# Bericht
# ---------------------------------------------------------------------------------------------------------------

def bauplan_text(g):
    teile = [FAMILIEN_NAME[g["familie"]], f"Rückblick {g['rueckblick']} Tage", f"Trendlinie {g['trendlinie']}",
             f"Marktfilter {g['marktfilter']}", f"{g['max_long']} Long-Plätze"]
    if g["short"] != "aus":
        teile.append(f"{g['max_short']} Short-Plätze ({g['short'].replace('_', ' ')})")
    else:
        teile.append("keine Shorts")
    teile.append(f"Stop {de(g['stop_atr'])} ATR" if g["stop_atr"] else "kein Stop")
    teile.append(f"Zeitstopp {g['zeitstopp']} Tage" if g["zeitstopp"] else "kein Zeitstopp")
    if g["familie"] == "momentum":
        teile.append(f"umschichten alle {g['umschichten']} Tage")
    if g["familie"] == "ruecksetzer":
        teile.append(f"RSI(2) unter {g['rsi_grenze']}")
    teile.append(f"Hebel {de(g['hebel'], 2)}")
    return " · ".join(teile)


def bericht(erg):
    wf, lage, depot = erg["walk_forward"], erg["markt"], erg["depot"]
    g, q, tech = wf["gesamt"], wf["qqq"], wf["tech_halten"]
    z = [
        "# 🧪 Strategie-Labor · Nachtschicht",
        "",
        f"Stand: Kurse bis {lage['tag']} · Quelle: {erg['quelle']} · Simulation mit Spielgeld, keine Anlageberatung.",
        "",
        f"**Ziel:** {de(ZIEL_RENDITE, 0)} % pro Jahr bei höchstens {de(MAX_RUECKGANG, 0)} % Rückgang.",
        "",
        "## Ergebnis der Testjahre (Walk-Forward)",
        "",
        f"Jedes Jahr wurde nur mit den {TRAIN_JAHRE} Jahren davor gesucht und dann unbekannt gehandelt.",
        "",
        "| | Rendite pro Jahr | größter Rückgang |",
        "| --- | --- | --- |",
        f"| Labor (Testjahre aneinandergereiht) | {de(g['rendite'])} % | {de(g['rueckgang'])} % |",
        f"| Nasdaq-100 halten | {de(q['rendite'])} % | {de(q['rueckgang'])} % |",
        f"| alle Tech-Aktien halten | {de(tech['rendite'])} % | {de(tech['rueckgang'])} % |",
        f"| Swing-Bot ({erg['swing_bot']['quelle']}) | {de(erg['swing_bot']['rendite'])} % | "
        f"{erg['swing_bot']['rueckgang']} % |",
        "",
        f"Abstand zum Ziel: **{de(g['rendite'] - ZIEL_RENDITE, 1, True)} Prozentpunkte**. "
        f"Long brachte {de(g['long'], 0)} $, Short {de(g['short'], 0)} $ (über alle Testjahre, je mit 10.000 $ Start).",
        "",
        "| Jahr | Test | Training | Nasdaq-100 | Rückgang | Trades | Bauplan |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in wf["schritte"]:
        z.append(f"| {s['jahr']} | {de(s['test']['rendite'], 1, True)} % | {de(s['training']['rendite'], 1, True)} % | "
                 f"{de(s['qqq']['rendite'], 1, True)} % | {de(s['test']['rueckgang'])} % | {s['test']['trades']} | "
                 f"{bauplan_text(s['genom'])} |")
    z += ["", "## Lehren aus Fehlern", ""]
    for l in erg["lehren"]:
        marke = "✅ bestätigt" if l["status"] == "bestaetigt" else "🤔 Verdacht"
        z.append(f"- **{l['titel']}** ({marke}, {l['belege']} Belege): {l['text']}")
    z += ["", "## Markt heute", "",
          f"- Nasdaq-100 {'über' if lage['nasdaq_ueber_200'] else 'unter'} seiner 200-Tage-Linie · Marktbreite "
          f"{de(lage['breite']) if lage['breite'] is not None else '–'} % der {lage['aktien']} Aktien über ihrer "
          f"200-Tage-Linie",
          "- Branchen (3 Monate): " + ", ".join(f"{b['branche']} {de(b['rendite'], 1, True)} %"
                                                for b in lage["branchen_3_monate"]),
          "- Stärkste Tech-Aktien (6 Monate): " + ", ".join(f"{t['ticker']} {de(t['rendite_6_monate'], 1, True)} %"
                                                            for t in lage["tech_staerkste"]),
          "- Schwächste Tech-Aktien (6 Monate): " + ", ".join(f"{t['ticker']} {de(t['rendite_6_monate'], 1, True)} %"
                                                              for t in lage["tech_schwaechste"]),
          "", "## Vorschlag für heute (nur Training, noch nicht geprüft)", "",
          f"- {bauplan_text(erg['vorschlag']['genom'])}",
          f"- im Training ({erg['vorschlag']['zeitraum']}): {de(erg['vorschlag']['kennzahlen']['rendite'])} % pro Jahr, "
          f"Rückgang {de(erg['vorschlag']['kennzahlen']['rueckgang'])} %",
          "", "## Übungsdepot des Labors", "",
          f"- Champion seit {depot['start']}: {bauplan_text(depot['genom'])}",
          f"- Wert {de(depot['wert'], 2)} $ ({de(depot['rendite'], 2, True)} %) · Nasdaq-100 im selben Zeitraum "
          f"{de(depot['qqq'], 2, True)} % · {depot['tage']} Handelstage"]
    for p in depot["offen"]:
        z.append(f"- offen: {p['ticker']} {p['richtung']} {p['stueck']} Stück seit {p['seit']}, Ergebnis "
                 f"{de(p['ergebnis'], 2, True)} $")
    for a in depot["morgen"]:
        z.append(f"- morgen: {a['ticker']} {a['aktion']}" + (f" ({a['stueck']} Stück)" if "stueck" in a else "")
                 + (f" – {a['grund']}" if a.get("grund") else ""))
    z += ["", "## Vorsicht", "",
          "- Die Aktienliste ist von heute. Aktien, die abgestürzt oder verschwunden sind, fehlen. Kaufen und Halten "
          "und Long-Strategien sehen dadurch besser aus, als man es damals hätte wissen können.",
          "- Gerechnet in US-Dollar, ganze Stück, 1 $ Gebühr und 0,1 % Spread je Order, 6 % Zinsen auf Hebel, "
          "1 % Leihgebühr für Shorts im Jahr.",
          f"- Unter {VERDACHT_UNTER} Belegen ist eine Lehre nur ein Verdacht.", ""]
    return "\n".join(z)


# ---------------------------------------------------------------------------------------------------------------
# Ablauf
# ---------------------------------------------------------------------------------------------------------------

def gedaechtnis_lesen(pfad):
    if pfad.exists():
        return json.loads(pfad.read_text(encoding="utf-8"))
    return {"version": 1, "belege": [], "naechte": []}


def gedaechtnis_merken(alt, neue_belege, nacht, maximal=4000):
    """Neue Belege dazu; gleicher Bauplan im gleichen Jahr wird ersetzt statt doppelt gezählt."""
    belege = {(b["jahr"], schluessel(b["genom"])): b for b in alt["belege"]}
    for b in neue_belege:
        belege[(b["jahr"], schluessel(b["genom"]))] = b
    naechte = [n for n in alt["naechte"] if n["datum"] != nacht["datum"]] + [nacht]
    return {"version": 1, "belege": list(belege.values())[-maximal:], "naechte": naechte[-120:]}


def swing_bot_vergleich(quelle):
    """Mit den festen Testdaten: das echte Ergebnis des Swing-Bots im Sicherheits-Check (2022–2024, gleiche Kurse).
    Sonst: die Zahlen aus seinem Test 2010–2026."""
    finger = WURZEL / "tests" / "fingerabdruck.json"
    if "tests/daten" in quelle.replace("\\", "/") and finger.exists():
        depot = json.loads(finger.read_text(encoding="utf-8"))["depot"]
        rendite = ((depot["end_wert"] / 10_000) ** (1 / 3) - 1) * 100
        return {"rendite": round(rendite, 2), "rueckgang": de(depot["max_rueckgang"]),
                "quelle": "Sicherheits-Check, gleiche Kurse 2022–2024"}
    return dict(SWING_BOT_REFERENZ)


def main(argv=None):
    global KOSTEN
    p = argparse.ArgumentParser(description="Strategie-Labor (Simulation, keine echten Orders)")
    p.add_argument("--daten", help="Ordner mit CSV-Kursen statt Yahoo (z. B. tests/daten/kurse)")
    p.add_argument("--budget", choices=list(BUDGETS), default="normal")
    p.add_argument("--seed", type=int, help="Zufallsstart (Standard: Datum, jede Nacht anders)")
    p.add_argument("--ausgabe", default=str(LABOR), help="Ordner für Bericht, Ergebnis, Gedächtnis und Depot")
    p.add_argument("--neuer-champion", action="store_true", help="Übungsdepot mit dem heutigen Vorschlag neu starten")
    a = p.parse_args(argv)

    beginn = time.time()
    aus = pathlib.Path(a.ausgabe)
    aus.mkdir(parents=True, exist_ok=True)
    sw = swing_bot()
    KOSTEN = (float(sw.GEBUEHR), float(sw.SPREAD_PROZENT) / 100)
    if a.daten:
        daten, quelle = lade_ordner(a.daten), a.daten
    else:
        ticker = sorted(set(sw.BRANCHE) | {MARKT_TICKER})
        print(f"🧪 Lade Kurse ab 2010 für {len(ticker)} Ticker von Yahoo …")
        daten, quelle = lade_yahoo(ticker), "Yahoo Finance (Tageskerzen ab 2010)"
    m = Markt(daten, sw.BRANCHE)
    seed = a.seed if a.seed is not None else int(dt.date.today().strftime("%Y%m%d"))
    rng = random.Random(seed)
    print(f"🧪 {len(m.ticker)} Aktien ({int(m.tech.sum())} Tech), {m.tage[0].date()} bis {m.tage[-1].date()}, "
          f"Budget {a.budget}, Zufallsstart {seed}")

    wf = walk_forward(m, rng, a.budget)
    gd_pfad = aus / "gedaechtnis.json"
    gedaechtnis = gedaechtnis_lesen(gd_pfad)
    alle_belege = gedaechtnis["belege"] + wf["belege"]
    # Vorschlag für heute: Suche in den letzten TRAIN_JAHRE Jahren, mit allem, was das Gedächtnis weiß
    ende = len(m.tage) - 1
    start = max(VORLAUF_TAGE, int(np.searchsorted(m.tage, m.tage[ende] - pd.DateOffset(years=TRAIN_JAHRE))))
    startwerte = [s["genom"] for s in wf["schritte"][-3:]]
    rangliste = suche(m, start, ende, rng, gewichte_aus(alle_belege), a.budget, startwerte)
    vorschlag = {"genom": rangliste[0]["genom"], "kennzahlen": rangliste[0]["kennzahlen"],
                 "zeitraum": f"{m.tage[start].date()} bis {m.tage[ende].date()}", "geprueft": len(rangliste)}
    depot = uebungsdepot(m, aus / "labor_depot.json", vorschlag["genom"], a.neuer_champion)
    nacht = {"datum": str(dt.date.today()), "daten_bis": str(m.tage[ende].date()), "seed": seed,
             "test_rendite": wf["gesamt"]["rendite"], "test_rueckgang": wf["gesamt"]["rueckgang"],
             "baupläne": sum(s["geprueft"] for s in wf["schritte"]) + len(rangliste)}
    gedaechtnis = gedaechtnis_merken(gedaechtnis, wf["belege"], nacht)

    erg = {
        "version": 1, "erstellt": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "quelle": quelle,
        "ziel": {"rendite": ZIEL_RENDITE, "rueckgang": MAX_RUECKGANG},
        "markt": marktlage(m),
        "walk_forward": {k: v for k, v in wf.items() if k not in ("belege", "verlauf", "verlauf_qqq")},
        "verlauf": {"tage": [str(d.date()) for d in m.tage[len(m.tage) - len(wf["verlauf"]):]],
                    "labor": [round(float(x), 2) for x in wf["verlauf"]],
                    "qqq": [round(float(x), 2) for x in wf["verlauf_qqq"]]} if wf["schritte"] else None,
        "swing_bot": swing_bot_vergleich(quelle),
        "vorschlag": vorschlag,
        "depot": depot,
        "lehren": lehren(wf, gedaechtnis["belege"]),
        "gewichte": gewichte_aus(gedaechtnis["belege"]),
        "gedaechtnis": {"belege": len(gedaechtnis["belege"]), "naechte": len(gedaechtnis["naechte"])},
        "dauer_sekunden": round(time.time() - beginn, 1),
    }
    (aus / "ergebnis.json").write_text(json.dumps(erg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    gd_pfad.write_text(json.dumps(gedaechtnis, ensure_ascii=False) + "\n", encoding="utf-8")
    (aus / "BERICHT.md").write_text(bericht(erg), encoding="utf-8")
    g = wf["gesamt"]
    print(f"🧪 Testjahre: {de(g['rendite'])} % pro Jahr, Rückgang {de(g['rueckgang'])} % · Nasdaq-100 "
          f"{de(wf['qqq']['rendite'])} % · Ziel {de(ZIEL_RENDITE, 0)} % · {erg['dauer_sekunden']} s")
    return erg


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
