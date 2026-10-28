"""Strategie-Labor: sucht nachts selbstständig nach einer Handelsstrategie für Tech-Aktien (long und short).

Bauplan und Regeln stehen in labor/PROMPT.md. Kurz:
- beobachtet den ganzen Markt (alle Aktien aus BRANCHEN im Swing-Bot), handelt nur Technologie und Kommunikation,
- erzeugt Strategien als Baupläne aus Genen, prüft sie Walk-Forward (3 Jahre suchen, 1 unbekanntes Jahr handeln),
- vergleicht mit Nasdaq-100 halten, Tech-Aktien halten und dem Swing-Bot,
- merkt sich in labor/gedaechtnis.json, welche Gene im Testjahr verloren haben, und zieht sie seltener,
- liest seine Bibliothek (labor/bibliothek.json: Lehren aus Trading-Büchern und Studien), prüft jede Lehre selbst an
  Kursen und übernimmt nur, was die Prüfung besteht (labor/WISSEN.md),
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
import statistics
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
TRAIN_JAHRE = 3              # Walk-Forward: mindestens so viele Jahre suchen, dann 1 unbekanntes Jahr handeln
WACHSEND = True              # Training mit allen Jahren davor (statt nur den letzten TRAIN_JAHRE): mehr Einbrüche,
                             # weniger Glückstreffer
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
    "max_long": [2, 3, 4, 5, 6, 8, 10],
    "max_short": [1, 2, 3],
    "stop_atr": [2.0, 3.0, 4.0, 6.0, None],
    "zeitstopp": [10, 20, 40, 60, None],
    "umschichten": [5, 10, 20],                # nur Momentum: alle so viele Tage neu sortieren
    "rsi_grenze": [5, 10, 15],                 # nur Rücksetzer: RSI(2) unter dieser Grenze
    "hebel": [1.0, 1.25, 1.5],
    # aus der Bibliothek (der erste Wert ist jeweils das Verhalten ohne die Lehre)
    "ueberspringen": [0, 21],                  # Jegadeesh & Titman: letzten Monat beim Momentum auslassen (12-1)
    "rangfolge": ["momentum", "hoch_52w"],     # George & Hwang: Nähe zum 52-Wochen-Hoch statt vergangener Rendite
    "groesse": ["gleich", "volatilitaet", "atr_risiko"],  # Barroso/Moreira: nach Schwankung · Turtle: 1 ATR = 1 %
    "saison": ["immer", "nov_bis_apr"],        # Bouman & Jacobsen: nur November bis April long
    "volaziel": [None, 12, 18],                # Moreira & Muir: neue Positionen kleiner, wenn das Depot zu stark schwankt
}
STANDARD = {gen: werte[0] for gen, werte in GENE.items()}  # fehlt ein Gen (alter Bauplan), gilt der erste Wert

T_BESTAETIGT = 3.0           # Harvey, Liu & Zhu: eine Lehre gilt erst ab t-Wert 3 als bestätigt (2–3: Tendenz)
TURTLE_RISIKO = 0.01         # Turtle-Regel: 1 ATR Bewegung kostet 1 % des Kontos
MIN_VERGLEICHE = 8           # so viele Vergleiche mit Wirkung braucht eine Lehre mindestens für ein Urteil
KOMITEE = 5                  # im Testjahr handeln 5 Baupläne zu gleichen Teilen: der beste jeder Familie, dann die
                             # nächstbesten (verschiedene Stile federn sich gegenseitig ab)
MIN_RENDITE = 10.0           # die Suche will mindestens so viel Rendite pro Jahr, darunter gibt es Abzug

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
        self.vola = self.atr / self.c  # Ø Tagesschwankung in % des Kurses
        self.winter = np.isin(self.tage.month, (11, 12, 1, 2, 3, 4))

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

    def momentum(self, n, auslassen=0):
        return self._merke(("mom", n, auslassen),
                           lambda: (self.C.shift(auslassen) / self.C.shift(n + auslassen) - 1).to_numpy())

    def naehe_hoch(self):
        """Schluss geteilt durch das Hoch der letzten 52 Wochen (1 = am Hoch)."""
        return self._merke(("naehe",), lambda: (self.C / self.H.rolling(252, min_periods=60).max()).to_numpy())

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
    mom = m.momentum(lb, g["ueberspringen"])
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
    if g["rangfolge"] == "hoch_52w":
        rang = m.naehe_hoch()
        gueltig &= ~np.isnan(rang)
    else:
        rang = mom
    return long_ein & gueltig, short_ein & gueltig, long_aus, short_aus, np.nan_to_num(rang, nan=0.0)


def marktampel(m, g):
    """Je Tag: Long erlaubt? Short erlaubt? Long-Saison?"""
    filt = g["marktfilter"]
    long_ok = {"qqq": m.qqq_ok, "breite": m.breite_ok, "beides": m.qqq_ok & m.breite_ok,
               "aus": np.ones(len(m.tage), dtype=bool)}[filt]
    baer = ~(m.qqq_ok if filt == "aus" else long_ok)
    short_ok = {"aus": np.zeros(len(m.tage), dtype=bool), "nur_baerenmarkt": baer,
                "immer": np.ones(len(m.tage), dtype=bool)}[g["short"]]
    saison = m.winter if g["saison"] == "nov_bis_apr" else np.ones(len(m.tage), dtype=bool)
    return long_ok & saison, short_ok, saison


def vollstaendig(g):
    return {**STANDARD, **g}


# ---------------------------------------------------------------------------------------------------------------
# Testmotor: Depot Tag für Tag
# ---------------------------------------------------------------------------------------------------------------

def simuliere(m, g, start, ende, kapital=START_KAPITAL, glattstellen=True, kosten=None):
    """Handelt den Bauplan g von Tag start bis ende (Indizes). Entscheidung zum Schluss, Ausführung zur nächsten
    Eröffnung, Stop auch innerhalb des Tages (Kurslücke: Eröffnungskurs). Gibt Wertverlauf, Trades und Kosten zurück."""
    gebuehr, spread = kosten or KOSTEN
    g = vollstaendig(g)
    long_ein, short_ein, long_aus, short_aus, rang = signale(m, g)
    long_ok, short_ok, saison = marktampel(m, g)
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
            if p["r"] > 0 and not saison[t]:
                gruende.append("Saison")
            if umschichten and (long_aus[t, j] if p["r"] > 0 else short_aus[t, j]):
                gruende.append("Signal vorbei")
            if gruende:
                p["grund_aus"] = gruende[0]
                auftraege_aus.add(j)
        if not umschichten:
            continue
        platz_wert = g["hebel"] * wert / plaetze
        if g["volaziel"] and len(werte) > 20:  # Schwankung des eigenen Depots der letzten 20 Tage, aufs Jahr gerechnet
            letzte = np.asarray(werte[-21:])
            vola = float(np.std(np.diff(letzte) / letzte[:-1]) * math.sqrt(252) * 100)
            platz_wert *= min(1.0, g["volaziel"] / vola) if vola > 0 else 1.0
        ziel_vola = np.nanmedian(m.vola[t, m.tech]) if g["groesse"] == "volatilitaet" else np.nan

        def stueckzahl(j):
            kurs = m.c[t, j]
            if g["groesse"] == "volatilitaet" and ziel_vola > 0:  # ruhige Aktien größer, wilde kleiner
                return math.floor(platz_wert * min(1.5, max(0.5, ziel_vola / m.vola[t, j])) / kurs)
            if g["groesse"] == "atr_risiko":  # Turtle: 1 ATR Bewegung kostet 1 % des Kontos
                return math.floor(min(g["hebel"] * TURTLE_RISIKO * wert / m.atr[t, j], 1.5 * platz_wert / kurs))
            return math.floor(platz_wert / kurs)

        brutto = sum(p["stueck"] * schluss[j] for j, p in positionen.items() if j not in auftraege_aus)
        offen = {r: sum(1 for j, p in positionen.items() if p["r"] == r and j not in auftraege_aus) for r in (1, -1)}
        for r, erlaubt, maske, maximal in ((1, long_ok[t], long_ein[t], g["max_long"]),
                                           (-1, short_ok[t], short_ein[t], g["max_short"] if g["short"] != "aus" else 0)):
            if not erlaubt or offen[r] >= maximal:
                continue
            kandidaten = [j for j in np.flatnonzero(maske) if j not in positionen]
            kandidaten.sort(key=lambda j: -r * rang[t, j])
            for j in kandidaten[: maximal - offen[r]]:
                stueck = stueckzahl(j)
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
    taeglich = np.diff(werte) / werte[:-1] if len(werte) > 2 and np.all(werte[:-1] > 0) else np.zeros(1)
    sharpe = float(taeglich.mean() / taeglich.std() * math.sqrt(252)) if taeglich.std() > 0 else 0.0
    return {
        "rendite": round(float(rendite), 2), "rueckgang": round(rueckgang, 2), "sharpe": round(sharpe, 3),
        "trades": len(trades),
        "quote": round(100 * gewinner / len(trades), 1) if trades else None,
        "long": round(sum(t["ergebnis"] for t in trades if t["richtung"] == "long"), 2),
        "short": round(sum(t["ergebnis"] for t in trades if t["richtung"] == "short"), 2),
        "short_trades": int(sum(t["richtung"] == "short" for t in trades)),
    }


def fitness(k):
    """Zielfunktion der Suche: Rendite je Prozent größtem Rückgang (wie im Wettkampf gegen den Swing-Bot), Rendite
    gedeckelt, damit kein Glückstreffer alles dominiert, Rückgang mindestens 5 % (sonst zählt Nichtstun als genial).
    Abzug unter MIN_RENDITE und für Rückgänge über MAX_RUECKGANG. Unter MIN_TRADES Trades ist es eher Halten mit
    Glück als eine Strategie: fällt praktisch raus."""
    strafe = (0.05 * max(0.0, MIN_RENDITE - k["rendite"]) + 0.05 * max(0.0, k["rueckgang"] - MAX_RUECKGANG)
              + (100 if k["trades"] < MIN_TRADES else 0))
    return min(k["rendite"], 80.0) / max(k["rueckgang"], 5.0) - strafe


def waehle_komitee(rangliste, groesse=KOMITEE):
    """Der beste Bauplan jeder Familie, dann die nächstbesten, bis das Komitee voll ist."""
    komitee, familien = [], set()
    for e in rangliste:
        if e["genom"]["familie"] not in familien:
            komitee.append(e["genom"])
            familien.add(e["genom"]["familie"])
    for e in rangliste:
        if len(komitee) >= groesse:
            break
        if e["genom"] not in komitee:
            komitee.append(e["genom"])
    return komitee[:groesse]


def komitee_lauf(m, genome, start, ende):
    """Mehrere Baupläne zu gleichen Teilen: Jeder bekommt 1/K des Geldes. Gerechnet wird jeder mit 10.000 $ und
    K-facher Gebühr (das entspricht 1/K des Geldes mit einfacher Gebühr), dann gemittelt."""
    gebuehr, spread = KOSTEN
    laeufe = [simuliere(m, g, start, ende, kosten=(gebuehr * len(genome), spread)) for g in genome]
    return {"werte": np.mean([lauf["werte"] for lauf in laeufe], axis=0),
            "trades": [dict(t, ergebnis=t["ergebnis"] / len(genome)) for lauf in laeufe for t in lauf["trades"]],
            "kosten": round(sum(lauf["kosten"] for lauf in laeufe) / len(genome), 2)}


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

    for g in [vollstaendig(g) for g in startwerte] + [zufalls_bauplan(rng, gewichte) for _ in range(n_zufall)]:
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
    """Für jedes Testjahr: Suche nur mit den Jahren davor (alle seit Beginn oder die letzten TRAIN_JAHRE), dann das
    unbekannte Jahr handeln.
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
        train_start = m.jahr_bereich(erstes if WACHSEND else jahr - TRAIN_JAHRE)[0]
        train_ende = test[0] - 1
        gewichte = gewichte_aus(belege)
        startwerte = [vorheriger] if vorheriger else []
        rangliste = suche(m, train_start, train_ende, rng, gewichte, budget, startwerte)
        sieger = rangliste[0]
        dsr = deflated_sharpe(simuliere(m, sieger["genom"], train_start, train_ende)["werte"],
                              [e["kennzahlen"]["sharpe"] for e in rangliste])
        komitee = waehle_komitee(rangliste)
        oos = komitee_lauf(m, komitee, test[0], test[1])
        k = kennzahlen(oos["werte"], oos["trades"])
        q = kennzahlen(nasdaq(m, *test))
        tech = kennzahlen(halten(m, *test))
        # Belege für das Gedächtnis: die 5 besten Baupläne aus dem Training, alle im Testjahr nachgeprüft
        for platz, e in enumerate(rangliste[:5]):
            r = simuliere(m, e["genom"], test[0], test[1])
            nach = kennzahlen(r["werte"], r["trades"])
            belege.append({"jahr": int(jahr), "genom": e["genom"], "platz": platz + 1,
                           "train_rendite": e["kennzahlen"]["rendite"], "oos_rendite": nach["rendite"],
                           "oos_rueckgang": nach["rueckgang"], "short": nach["short"], "long": nach["long"],
                           "short_trades": nach["short_trades"],
                           "qqq": q["rendite"], "ueberschuss": round(nach["rendite"] - q["rendite"], 2)})
        schritte.append({"jahr": int(jahr), "bis": str(m.tage[test[1]].date()), "genom": sieger["genom"],
                         "training": sieger["kennzahlen"], "test": k, "qqq": q, "tech_halten": tech,
                         "kosten": oos["kosten"], "geprueft": len(rangliste), "deflated_sharpe": dsr,
                         "komitee": komitee,
                         "top": [e["genom"] for e in rangliste[:3]]})
        kette.append(oos["werte"] / START_KAPITAL)
        kette_qqq.append(nasdaq(m, *test) / START_KAPITAL)
        kette_tech.append(halten(m, *test) / START_KAPITAL)
        vorheriger = sieger["genom"]
        protokoll(f"  {jahr}: Test {k['rendite']:+.1f} % (Rückgang {k['rueckgang']:.1f} %) · Training "
                  f"{sieger['kennzahlen']['rendite']:+.1f} % · Nasdaq-100 {q['rendite']:+.1f} % · "
                  f"{FAMILIEN_NAME[sieger['genom']['familie']]} · {len(rangliste)} Baupläne · Deflated Sharpe "
                  f"{dsr['dsr']:.0f} %")

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


def deflated_sharpe(werte, sharpes):
    """Bailey & López de Prado (2014): Wahrscheinlichkeit, dass der Sieger aus len(sharpes) Versuchen wirklich mehr
    kann als null, nach Abzug des Auswahl-Glücks und mit Schiefe und Wölbung seiner Tagesrenditen. Ähnliche Baupläne
    zählen hier voll, die echte Zahl unabhängiger Versuche ist kleiner: die Schwelle ist eher etwas zu streng."""
    werte = np.asarray(werte, dtype=float)
    r = np.diff(werte) / werte[:-1] if len(werte) > 2 and np.all(werte[:-1] > 0) else np.zeros(1)
    n, T = len(sharpes), len(r)
    if T < 3 or r.std() == 0:
        return {"dsr": 0.0, "sharpe": 0.0, "schwelle": None, "versuche": n}
    z = statistics.NormalDist()
    sr = r.mean() / r.std()
    sr0 = 0.0
    if n > 1:
        euler = 0.5772156649
        streuung = statistics.stdev(x / math.sqrt(252) for x in sharpes)
        sr0 = streuung * ((1 - euler) * z.inv_cdf(1 - 1 / n) + euler * z.inv_cdf(1 - 1 / (n * math.e)))
    abw = r - r.mean()
    schiefe = (abw ** 3).mean() / r.std() ** 3
    woelbung = (abw ** 4).mean() / r.std() ** 4
    nenner = math.sqrt(max(1e-12, 1 - schiefe * sr + (woelbung - 1) / 4 * sr ** 2))
    return {"dsr": round(z.cdf((sr - sr0) * math.sqrt(T - 1) / nenner) * 100, 1),
            "sharpe": round(sr * math.sqrt(252), 2), "schwelle": round(sr0 * math.sqrt(252), 2), "versuche": n}


# ---------------------------------------------------------------------------------------------------------------
# Bibliothek: Lehren aus Büchern und Studien selbst prüfen
# ---------------------------------------------------------------------------------------------------------------

URTEIL_NAME = {"bestaetigt": "bestätigt", "tendenz": "Tendenz", "verworfen": "verworfen", "unklar": "unklar"}
URTEIL_GEWICHT = {"bestaetigt": (1.5, 0.8), "tendenz": (1.2, 0.9), "verworfen": (0.6, 1.1), "unklar": (1.0, 1.0)}


def lade_bibliothek(pfad):
    """Liest labor/bibliothek.json und prüft, dass jede Hypothese ein bekanntes Gen mit erlaubten Werten nutzt."""
    bib = json.loads(pathlib.Path(pfad).read_text(encoding="utf-8"))
    quellen = {q["id"] for q in bib["quellen"]}
    for h in bib["hypothesen"]:
        if h["quelle"] not in quellen:
            raise ValueError(f"{h['id']}: Quelle {h['quelle']} fehlt in der Bibliothek.")
        for gen, wert in [(h["gen"], h["kontrolle"]), (h["gen"], h["test"]), *h["bedingung"].items()]:
            if gen not in GENE or wert not in GENE[gen]:
                raise ValueError(f"{h['id']}: {gen} = {wert!r} gibt es im Bauplan nicht (erlaubt: {GENE.get(gen)}).")
    return bib


def t_wert(werte):
    werte = list(werte)
    if len(werte) < 2:
        return 0.0
    sd = statistics.stdev(werte)
    return mittel(werte) / (sd / math.sqrt(len(werte))) if sd > 0 else 0.0


def urteil_fuer(rendite, rueckgang, t_rendite, t_rueckgang):
    """Hilft eine Lehre? Mehr Rendite ohne deutlich mehr Rückgang, oder kleinerer Rückgang ohne Renditeverlust.
    Bestätigt erst ab t-Wert 3 (Harvey, Liu & Zhu), Tendenz ab 2. Verworfen, wenn sie deutlich Rendite kostet, ohne
    den Rückgang mindestens ebenso deutlich zu senken (oder umgekehrt)."""
    def hilft(grenze):
        return (t_rendite >= grenze and rueckgang <= 2) or (t_rueckgang <= -grenze and rendite >= -0.5)
    if hilft(T_BESTAETIGT):
        return "bestaetigt"
    kostet_rendite = t_rendite <= -2 and not (t_rueckgang <= -2 and rueckgang <= rendite)
    kostet_ruhe = t_rueckgang >= 2 and not (t_rendite >= 2 and rendite >= rueckgang)
    if kostet_rendite or kostet_ruhe:
        return "verworfen"
    if hilft(2):
        return "tendenz"
    return "unklar"


def pruefe_wissen(m, wf, bibliothek, rng, protokoll=print):
    """Jede Lehre als fairer Vergleich: dieselben Baupläne einmal ohne die Lehre (Kontrolle) und einmal mit ihr, in
    jedem Testjahr. Basis je Jahr: die 3 besten Baupläne aus dem Training davor und 2 zufällige."""
    quellen = {q["id"]: q for q in bibliothek["quellen"]}
    basen = {s["jahr"]: [vollstaendig(g) for g in s["top"]] + [zufalls_bauplan(rng, {}) for _ in range(2)]
             for s in wf["schritte"]}

    def lauf(g, bereich):
        e = simuliere(m, g, *bereich)
        return kennzahlen(e["werte"], e["trades"])

    urteile = []
    for h in bibliothek["hypothesen"]:
        d_rendite, d_rueckgang, je_jahr = [], [], {}
        for s in wf["schritte"]:
            bereich = m.jahr_bereich(s["jahr"])
            for basis in basen[s["jahr"]]:
                ohne = {**basis, **h["bedingung"], h["gen"]: h["kontrolle"]}
                mit = {**ohne, h["gen"]: h["test"]}
                a, b = lauf(ohne, bereich), lauf(mit, bereich)
                d_rendite.append(b["rendite"] - a["rendite"])
                d_rueckgang.append(b["rueckgang"] - a["rueckgang"])
                je_jahr.setdefault(s["jahr"], []).append(b["rendite"] - a["rendite"])
        n = len(d_rendite)
        if not n:
            continue
        # Vergleiche ohne jede Wirkung (z. B. kein Short-Trade im Jahr) zählen nicht als Beleg
        wirkt = [(a, b) for a, b in zip(d_rendite, d_rueckgang) if abs(a) > 1e-9 or abs(b) > 1e-9]
        gleich = n - len(wirkt)
        dr, dd = (mittel(x[i] for x in wirkt) if wirkt else 0.0 for i in (0, 1))
        tr, td = (t_wert(x[i] for x in wirkt) for i in (0, 1))
        urteil = "unklar" if len(wirkt) < MIN_VERGLEICHE else urteil_fuer(dr, dd, tr, td)
        q = quellen[h["quelle"]]
        grund = (f"Rendite {de(dr, 1, True)} Pkt. pro Jahr (t = {de(tr, 1)}), größter Rückgang {de(dd, 1, True)} Pkt. "
                 f"(t = {de(td, 1)}), besser in {int(sum(x > 0 for x in d_rendite))} von {n} Vergleichen")
        if gleich:
            grund += f", {gleich}× ohne Wirkung"
        if len(wirkt) < MIN_VERGLEICHE:
            grund += f" – zu wenige Vergleiche mit Wirkung (unter {MIN_VERGLEICHE})"
        urteile.append({
            "id": h["id"], "titel": h["titel"], "quelle": h["quelle"], "quelle_titel": q["titel"],
            "autoren": q["autoren"], "jahr": q["jahr"], "gen": h["gen"], "kontrolle": h["kontrolle"],
            "test": h["test"], "vergleiche": n, "rendite_diff": round(dr, 2), "rueckgang_diff": round(dd, 2),
            "t_rendite": round(tr, 2), "t_rueckgang": round(td, 2), "besser": int(sum(x > 0 for x in d_rendite)),
            "ohne_wirkung": gleich, "urteil": urteil, "grund": grund,
            "je_jahr": {str(j): round(mittel(v), 2) for j, v in je_jahr.items()}})
        protokoll(f"  📚 {h['id']} {h['titel']}: {URTEIL_NAME[urteil]} · {grund}")
    return urteile


def wissen_gewichte(urteile):
    """Was das Labor aus der Bibliothek bestätigt hat, zieht es öfter; was es verworfen hat, seltener."""
    gewichte = {}
    for u in urteile:
        f_test, f_kontrolle = URTEIL_GEWICHT[u["urteil"]]
        for wert, f in ((u["test"], f_test), (u["kontrolle"], f_kontrolle)):
            je_wert = gewichte.setdefault(u["gen"], {})
            je_wert[json.dumps(wert)] = round(je_wert.get(json.dumps(wert), 1.0) * f, 3)
    return gewichte


def kombiniere(*gewichte):
    aus = {}
    for gw in gewichte:
        for gen, werte in gw.items():
            for wert, f in werte.items():
                aus.setdefault(gen, {})[wert] = round(min(4.0, max(0.2, aus.get(gen, {}).get(wert, 1.0) * f)), 3)
    return aus


# ---------------------------------------------------------------------------------------------------------------
# Lehren aus Fehlern
# ---------------------------------------------------------------------------------------------------------------

def de(x, nachkomma=1, vorzeichen=False):
    text = f"{x:+,.{nachkomma}f}" if vorzeichen else f"{x:,.{nachkomma}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def mittel(werte):
    werte = list(werte)
    return sum(werte) / len(werte) if werte else None


def lehren(wf, belege, urteile=()):
    """Lehren in einfachen Sätzen, jede mit Zahlen. 'bestaetigt' erst ab VERDACHT_UNTER Belegen."""
    aus = []
    schritte = wf["schritte"]
    if urteile:
        zaehl = {k: sum(u["urteil"] == k for u in urteile) for k in URTEIL_NAME}
        aus.append({"titel": "Bücherwissen",
                    "text": f"Von {len(urteile)} Lehren aus Büchern und Studien hat das Labor {zaehl['bestaetigt']} "
                            f"bestätigt (t-Wert ab 3), {zaehl['tendenz']} als Tendenz gesehen, {zaehl['verworfen']} "
                            f"verworfen und {zaehl['unklar']} offen gelassen. Details: WISSEN.md.",
                    "belege": sum(u["vergleiche"] for u in urteile),
                    "status": "bestaetigt" if zaehl["bestaetigt"] else "zweifel"})
    if schritte and all(s.get("deflated_sharpe") for s in schritte):
        echt = sum(s["deflated_sharpe"]["dsr"] >= 95 for s in schritte)
        aus.append({"titel": "Glück oder Können (Deflated Sharpe)",
                    "text": f"In {echt} von {len(schritte)} Jahren war der Trainings-Sieger nach Abzug des "
                            f"Auswahl-Glücks mit mindestens 95 % Wahrscheinlichkeit besser als null. Bei rund "
                            f"{mittel(s['deflated_sharpe']['versuche'] for s in schritte):.0f} Bauplänen je Jahr sieht "
                            f"der beste auch ohne Können gut aus.",
                    "belege": len(schritte), "status": "bestaetigt" if echt == len(schritte) else "zweifel"})
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
    g = vollstaendig(g)
    if g["ueberspringen"]:
        teile.append("letzten Monat auslassen")
    if g["rangfolge"] == "hoch_52w":
        teile.append("Rang nach 52-Wochen-Hoch")
    if g["groesse"] != "gleich":
        teile.append({"volatilitaet": "Größe nach Schwankung", "atr_risiko": "Turtle-Größe"}[g["groesse"]])
    if g["saison"] != "immer":
        teile.append("long nur Nov–Apr")
    if g["volaziel"]:
        teile.append(f"Depot-Schwankung höchstens {g['volaziel']} %")
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
        ("Jedes Jahr wurde nur mit allen Jahren davor gesucht und dann unbekannt gehandelt." if WACHSEND else
         f"Jedes Jahr wurde nur mit den {TRAIN_JAHRE} Jahren davor gesucht und dann unbekannt gehandelt."),
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
        "„Deflated Sharpe“ (Bailey & López de Prado): Wahrscheinlichkeit, dass der Sieger aus allen geprüften "
        "Bauplänen des Jahres mehr kann als Glück.",
        "",
        "| Jahr | Test | Training | Nasdaq-100 | Rückgang | Trades | Deflated Sharpe | Bauplan |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in wf["schritte"]:
        z.append(f"| {s['jahr']} | {de(s['test']['rendite'], 1, True)} % | {de(s['training']['rendite'], 1, True)} % | "
                 f"{de(s['qqq']['rendite'], 1, True)} % | {de(s['test']['rueckgang'])} % | {s['test']['trades']} | "
                 f"{de(s['deflated_sharpe']['dsr'], 0)} % | {bauplan_text(s['genom'])} |")
    if erg.get("wissen"):
        z += ["", "## Aus Büchern gelernt", "",
              f"Jede Lehre der Bibliothek ({len(erg['wissen'])} Stück) wurde mit denselben Bauplänen einmal ohne und "
              "einmal mit ihr gehandelt, in jedem Testjahr. Bestätigt erst ab t-Wert 3 (Harvey, Liu & Zhu). "
              "Mehr in WISSEN.md.", "",
              "| Lehre | Quelle | Rendite | Rückgang | t-Werte | Urteil |", "| --- | --- | --- | --- | --- | --- |"]
        for u in erg["wissen"]:
            z.append(f"| {u['titel']} | {u['autoren'].split(',')[0]} {u['jahr']} | {de(u['rendite_diff'], 1, True)} Pkt. | "
                     f"{de(u['rueckgang_diff'], 1, True)} Pkt. | {de(u['t_rendite'], 1)} / {de(u['t_rueckgang'], 1)} | "
                     f"{URTEIL_NAME[u['urteil']]} |")
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

def wissen_text(urteile, bibliothek, gedaechtnis, stand):
    """labor/WISSEN.md: was das Labor gelesen hat, was es daraus geprüft hat und was es übernimmt."""
    je_quelle = {}
    for u in urteile:
        je_quelle.setdefault(u["quelle"], []).append(u)
    marke = {"bestaetigt": "✅ bestätigt", "tendenz": "🟡 Tendenz", "verworfen": "❌ verworfen", "unklar": "🤔 unklar"}
    z = ["# 📚 Was das Labor aus Büchern gelernt hat", "",
         f"Stand: Kurse bis {stand} · Simulation mit Spielgeld, keine Anlageberatung.", "",
         "Das Labor liest seine Bibliothek (`labor/bibliothek.json`), macht aus jeder Lehre einen fairen Vergleich und "
         "prüft ihn jede Nacht selbst: dieselben Baupläne einmal ohne und einmal mit der Lehre, in jedem Testjahr, mit "
         "Kosten. **Bestätigt** heißt: t-Wert ab 3 (Harvey, Liu & Zhu), also sehr wahrscheinlich kein Zufall. "
         "**Tendenz**: t-Wert 2 bis 3. **Verworfen**: schadet deutlich. Was bestätigt ist, zieht das Labor bei der "
         "Suche öfter, was verworfen ist, seltener.", "",
         "t-Werte: Rendite / Rückgang. Ein negativer t-Wert beim Rückgang heißt: kleinerer Rückgang.", "",
         "| Lehre | Rendite | Rückgang | t-Werte | Urteil | letzte Nächte |", "| --- | --- | --- | --- | --- | --- |"]
    verlauf = gedaechtnis.get("wissen", {})
    for u in urteile:
        alt = [v["urteil"] for v in verlauf.get(u["id"], [])][-7:]
        kurz = " ".join({"bestaetigt": "✅", "tendenz": "🟡", "verworfen": "❌", "unklar": "·"}[x] for x in alt)
        z.append(f"| {u['titel']} | {de(u['rendite_diff'], 1, True)} Pkt. | {de(u['rueckgang_diff'], 1, True)} Pkt. | "
                 f"{de(u['t_rendite'], 1)} / {de(u['t_rueckgang'], 1)} | {marke[u['urteil']]} | {kurz} |")
    z += ["", "## Bibliothek", ""]
    for q in bibliothek["quellen"]:
        z += [f"### {q['titel']}", "", f"{q['autoren']} · {q['jahr']} · {q['art']} · {q['zugang']} · [Link]({q['link']})",
              ""]
        z += [f"- {k}" for k in q["kernaussagen"]]
        z.append(f"- *Vorsicht:* {q['vorsicht']}")
        if q.get("umsetzung"):
            z.append(f"- *Im Labor:* {q['umsetzung']}")
        for u in je_quelle.get(q["id"], []):
            z.append(f"- **Geprüft – {u['titel']}:** {marke[u['urteil']]}. {u['grund']}.")
        z.append("")
    z += ["## Vorsicht", "",
          "- Die Kernaussagen sind eigene kurze Zusammenfassungen frei zugänglicher Quellen, keine Zitate.",
          "- Das Labor prüft eine Lehre nur so, wie sie in seinen Bauplan passt. Ein Urteil gilt für Tech-Aktien mit "
          "diesen Regeln, nicht allgemein für das Buch.",
          "- Die Aktienliste ist von heute (Überlebende). Wenige Testjahre heißen: viele Lehren bleiben unklar.", ""]
    return "\n".join(z)


def gedaechtnis_lesen(pfad):
    if pfad.exists():
        return json.loads(pfad.read_text(encoding="utf-8"))
    return {"version": 1, "belege": [], "naechte": []}


def gedaechtnis_merken(alt, neue_belege, nacht, urteile=(), maximal=4000):
    """Neue Belege dazu; gleicher Bauplan im gleichen Jahr wird ersetzt statt doppelt gezählt. Dazu je Lehre der
    Verlauf der Urteile über die Nächte (zeigt, ob ein Urteil stabil ist oder vom Zufall der Nacht abhängt)."""
    belege = {(b["jahr"], schluessel(b["genom"])): b for b in alt["belege"]}
    for b in neue_belege:
        belege[(b["jahr"], schluessel(b["genom"]))] = b
    naechte = [n for n in alt["naechte"] if n["datum"] != nacht["datum"]] + [nacht]
    wissen = {k: list(v) for k, v in alt.get("wissen", {}).items()}
    for u in urteile:
        eintrag = {"datum": nacht["datum"], "urteil": u["urteil"], "rendite_diff": u["rendite_diff"],
                   "rueckgang_diff": u["rueckgang_diff"], "t_rendite": u["t_rendite"], "vergleiche": u["vergleiche"]}
        wissen[u["id"]] = [v for v in wissen.get(u["id"], []) if v["datum"] != nacht["datum"]][-59:] + [eintrag]
    return {"version": 1, "belege": list(belege.values())[-maximal:], "naechte": naechte[-120:], "wissen": wissen}


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
    p.add_argument("--bibliothek", default=str(LABOR / "bibliothek.json"), help="Lehren aus Büchern und Studien")
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
    bibliothek = lade_bibliothek(a.bibliothek)
    seed = a.seed if a.seed is not None else int(dt.date.today().strftime("%Y%m%d"))
    rng = random.Random(seed)
    print(f"🧪 {len(m.ticker)} Aktien ({int(m.tech.sum())} Tech), {m.tage[0].date()} bis {m.tage[-1].date()}, "
          f"Budget {a.budget}, Zufallsstart {seed}")

    wf = walk_forward(m, rng, a.budget)
    print(f"📚 Prüfe {len(bibliothek['hypothesen'])} Lehren aus {len(bibliothek['quellen'])} Büchern und Studien …")
    urteile = pruefe_wissen(m, wf, bibliothek, rng)
    gd_pfad = aus / "gedaechtnis.json"
    gedaechtnis = gedaechtnis_lesen(gd_pfad)
    alle_belege = gedaechtnis["belege"] + wf["belege"]
    # Vorschlag für heute: Suche in den letzten TRAIN_JAHRE Jahren mit allem, was Gedächtnis und Bibliothek wissen.
    # (Der Walk-Forward oben startet bewusst neutral: Er darf nicht wissen, was in späteren Testjahren geschah.)
    ende = len(m.tage) - 1
    start = max(VORLAUF_TAGE, int(np.searchsorted(m.tage, m.tage[ende] - pd.DateOffset(years=TRAIN_JAHRE))))
    startwerte = [s["genom"] for s in wf["schritte"][-3:]]
    rangliste = suche(m, start, ende, rng, kombiniere(gewichte_aus(alle_belege), wissen_gewichte(urteile)),
                      a.budget, startwerte)
    vorschlag = {"genom": rangliste[0]["genom"], "kennzahlen": rangliste[0]["kennzahlen"],
                 "zeitraum": f"{m.tage[start].date()} bis {m.tage[ende].date()}", "geprueft": len(rangliste)}
    depot = uebungsdepot(m, aus / "labor_depot.json", vorschlag["genom"], a.neuer_champion)
    nacht = {"datum": str(dt.date.today()), "daten_bis": str(m.tage[ende].date()), "seed": seed,
             "test_rendite": wf["gesamt"]["rendite"], "test_rueckgang": wf["gesamt"]["rueckgang"],
             "baupläne": sum(s["geprueft"] for s in wf["schritte"]) + len(rangliste)}
    gedaechtnis = gedaechtnis_merken(gedaechtnis, wf["belege"], nacht, urteile)

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
        "lehren": lehren(wf, gedaechtnis["belege"], urteile),
        "wissen": urteile,
        "bibliothek": [{k: q[k] for k in ("id", "titel", "autoren", "jahr", "art", "zugang", "link")}
                       for q in bibliothek["quellen"]],
        "gewichte": kombiniere(gewichte_aus(gedaechtnis["belege"]), wissen_gewichte(urteile)),
        "gedaechtnis": {"belege": len(gedaechtnis["belege"]), "naechte": len(gedaechtnis["naechte"])},
        "dauer_sekunden": round(time.time() - beginn, 1),
    }
    (aus / "ergebnis.json").write_text(json.dumps(erg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    gd_pfad.write_text(json.dumps(gedaechtnis, ensure_ascii=False) + "\n", encoding="utf-8")
    (aus / "BERICHT.md").write_text(bericht(erg), encoding="utf-8")
    (aus / "WISSEN.md").write_text(wissen_text(urteile, bibliothek, gedaechtnis, str(m.tage[ende].date())),
                                   encoding="utf-8")
    g = wf["gesamt"]
    print(f"🧪 Testjahre: {de(g['rendite'])} % pro Jahr, Rückgang {de(g['rueckgang'])} % · Nasdaq-100 "
          f"{de(wf['qqq']['rendite'])} % · Ziel {de(ZIEL_RENDITE, 0)} % · {erg['dauer_sekunden']} s")
    return erg


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
