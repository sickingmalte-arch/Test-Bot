"""Eigene Depots für den Prüfstand – eine andere Art Strategie als der Swing-Bot: einmal im Monat umschichten.

Arten: Momentum (stärkster Anstieg über 6 oder 12 Monate, ohne den letzten Monat), geringe Schwankung, Branchen-ETFs,
Trendfolge mit dem Nasdaq-100. Gleiche Regeln für die Idee und ihre Gegenprobe (Zufall aus denselben Kandidaten):
- Entscheidung am letzten Handelstag des Monats zum Schlusskurs, gehandelt am nächsten Handelstag zur Eröffnung –
  kein Blick in die Zukunft.
- Spread 0,1 % je Order wie beim Swing-Bot, Gebühr je Order aus der Variable GEBUEHR (Euro, Standard 0).
- Depot in Euro (Start 10.000 €), Geld liegt in Euro, Aktien werden über den Euro-Dollar-Kurs bewertet.
  Bruchstücke erlaubt (die Kurse sind split-bereinigt, ganze Stück wären rückblickend falsch).
- Marktfilter: Liegt der Filter-Wert (Standard SPY) am Entscheidungstag unter seiner 200-Tage-Linie, nur Geld.
Bekannte Verzerrung: Die Aktienliste ist die von heute (S&P 500 und Nasdaq-100). Firmen, die pleite gingen oder
aus dem Index flogen, fehlen. Das macht jede Aktien-Strategie rückblickend zu gut – deshalb zählt vor allem der
Vergleich mit zufällig gewählten Aktien aus derselben Liste. Die Branchen-ETFs haben diese Verzerrung nicht.
Mit stichtag=True zählt eine Aktie erst ab dem Tag, an dem sie in den S&P 500 aufgenommen wurde (Wikipedia-Tabelle
der Index-Änderungen) – sonst kauft Momentum rückblickend Aktien, die erst WEGEN ihres Anstiegs in den Index kamen."""
import os
import sys

import numpy as np
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HIER), "lernen"))
import daten as D  # noqa: E402

SPREAD = 0.001
START_WERT = 10_000.0
BRANCHEN_ETF = ["XLK", "XLF", "XLV", "XLE", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE", "XLC"]
MIN_HANDEL = 0.01  # Umschichten unter 1 % des Zielwerts lohnt nicht (spart Spread)
_TABELLEN = {}


def _tage(df):
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df = df.copy()
    df.index = idx.normalize()
    return df[~df.index.duplicated(keep="last")]


def tabellen(cache):
    """Eröffnung und Schluss als breite Tabellen (Börsentage des SPY × Ticker), einmal je Cache geladen."""
    if cache in _TABELLEN:
        return _TABELLEN[cache]
    uni = pd.read_csv(os.path.join(cache, "universum.csv"))
    im_index = uni["index"].fillna("").astype(str).str.contains("S&P|Nasdaq") if "index" in uni else True
    aktien = [t for t in uni.loc[im_index, "ticker"].astype(str)
              if t.replace("-", "").isalnum() and t not in D.ZUSATZ]
    o, c = {}, {}
    for t in aktien + ["SPY", "QQQ"] + BRANCHEN_ETF:
        df = D.lies_kurse(cache, t)
        if df is None or len(df) < 260:
            continue
        df = _tage(df)
        o[t], c[t] = df["Open"], df["Close"]
    tage = c["SPY"].dropna().index
    wechsel = index_wechsel(cache)
    if wechsel:
        neu = sum(1 for t in aktien if any(d.year >= 2010 and not v for d, v in wechsel.get(t, [])))
        print(f"S&P-500-Wechsel geladen: {len(wechsel)} Ticker, {neu} heutige Aktien kamen 2010 oder später dazu")
    C = pd.DataFrame(c).reindex(tage)
    O = pd.DataFrame(o).reindex(tage)
    fx = _tage(D.lies_kurse(cache, "EURUSD=X"))["Close"].reindex(tage).ffill().bfill()
    roh = C.copy()  # ohne Auffüllen: wer am Entscheidungstag keinen Kurs hat, ist kein Kandidat
    C = C.ffill()
    O = O.fillna(C.shift(1)).fillna(C)
    sp500 = set(uni.loc[uni["index"].fillna("").astype(str).str.contains("S&P"), "ticker"].astype(str)) \
        if "index" in uni else set()
    _TABELLEN[cache] = {"C": C, "O": O, "roh": roh, "fx": fx, "tage": tage, "Cn": C.to_numpy(), "On": O.to_numpy(),
                        "sp500": [t for t in aktien if t in C.columns and t in sp500],
                        "wechsel": wechsel,
                        "fxn": fx.to_numpy(), "spalte": {t: j for j, t in enumerate(C.columns)},
                        "aktien": [t for t in aktien if t in C.columns]}
    return _TABELLEN[cache]


def index_wechsel(cache):
    """Aufnahmen und Abgänge im S&P 500 je Ticker: [(Datum, war vorher im Index?)], älteste zuerst."""
    pfad = os.path.join(cache, "sp500_aenderungen.csv")
    if not os.path.exists(pfad):
        return None
    ch = pd.read_csv(pfad, header=[0, 1])

    def spalte(oben, unten):
        for c in ch.columns:
            if oben in str(c[0]).lower() and unten in str(c[1]).lower():
                return ch[c]
        raise KeyError(f"Spalte {oben}/{unten} fehlt in sp500_aenderungen.csv: {list(ch.columns)}")
    datum = pd.to_datetime(ch.iloc[:, 0].astype(str).str.replace(r"\[.*?\]", "", regex=True).str.strip(),
                           errors="coerce", format="mixed")
    wechsel = {}
    for d, plus, minus in zip(datum, spalte("added", "ticker"), spalte("removed", "ticker")):
        if pd.isna(d):
            continue
        for sym, vorher in ((plus, False), (minus, True)):
            if isinstance(sym, str) and sym.strip() and sym.strip().lower() != "nan":
                wechsel.setdefault(D.yahoo_name(sym.strip()), []).append((d.normalize(), vorher))
    for v in wechsel.values():
        v.sort()
    return wechsel


def im_index(T, t, tag):
    """War die (heutige) S&P-500-Aktie t am Tag tag schon im Index? Der nächste Wechsel nach tag sagt es."""
    for d, vorher in T["wechsel"].get(t, []):
        if d > tag:
            return vorher
    return True


def punkte(T, art, i, lang=252, kurz=21, stichtag=False):
    """Punktzahl je Kandidat am Tag i – nur mit Kursen bis einschließlich i. Höher = besser."""
    roh = T["roh"]
    if art == "sektor":
        spalten = [t for t in BRANCHEN_ETF if t in roh.columns]
    elif stichtag:
        if T["wechsel"] is None:
            raise RuntimeError("sp500_aenderungen.csv fehlt im Cache – Stichtag-Test nicht möglich")
        spalten = [t for t in T["sp500"] if im_index(T, t, T["tage"][i])]
    else:
        spalten = T["aktien"]
    if i < lang:
        return pd.Series(dtype=float)
    jetzt, frueher, mitte = roh.iloc[i][spalten], roh.iloc[i - lang][spalten], roh.iloc[i - kurz][spalten]
    ok = jetzt.notna() & frueher.notna() & mitte.notna()
    if art in ("momentum", "sektor"):
        return (mitte[ok] / frueher[ok] - 1).dropna()
    if art == "schwankung":
        fenster = np.log(roh.iloc[i - lang:i + 1][spalten]).diff()
        genug = fenster.notna().sum() >= lang - 12
        return (-fenster.std()[ok & genug]).dropna()
    raise ValueError(art)


def _ueber_200(T, ticker, i):
    s = T["roh"][ticker].iloc[max(0, i - 199):i + 1].dropna()
    return len(s) >= 150 and s.iloc[-1] > s.mean()


def depot(cache, von, bis, art, n, lang=252, kurz=21, filter_ticker="SPY", seed=None, feste=None, stichtag=False):
    """Wertverlauf in Euro (Serie je Börsentag, attrs["orders"] = Zahl der Orders). seed: Gegenprobe – statt der
    besten n zufällige n aus denselben Kandidaten. feste: immer diese Ticker (z. B. ["QQQ"] für Halten/Trendfolge)."""
    T = tabellen(cache)
    tage, C, O, fx, sp = T["tage"], T["Cn"], T["On"], T["fxn"], T["spalte"]
    gebuehr = float(os.environ.get("GEBUEHR", "0"))
    von_i = int(tage.searchsorted(pd.Timestamp(von)))
    bis_i = int(tage.searchsorted(pd.Timestamp(bis), side="right")) - 1
    if von_i < 1 or bis_i <= von_i:
        raise ValueError(f"Zeitraum {von}–{bis} nicht in den Daten")
    monat = tage.to_period("M")
    rng = np.random.default_rng(seed) if seed is not None else None
    bargeld, stueck, werte, orders = START_WERT, {}, [], 0
    ziel = _auswahl(T, art, von_i - 1, n, lang, kurz, filter_ticker, rng, feste, stichtag)  # am Abend vor dem Start
    for k in range(von_i, bis_i + 1):
        if ziel is not None:  # am Vorabend entschieden, heute zur Eröffnung handeln
            kurs = {t: O[k, sp[t]] for t in set(stueck) | set(ziel)}
            f = fx[k]
            wert = bargeld + sum(s * kurs[t] for t, s in stueck.items()) / f
            je = wert * (1 - 2 * SPREAD) / len(ziel) if ziel else 0.0
            soll = {t: je * f / kurs[t] for t in ziel}
            for verkaufen in (True, False):  # erst verkaufen, dann kaufen
                for t in sorted(set(stueck) | set(soll)):
                    delta = soll.get(t, 0.0) - stueck.get(t, 0.0)
                    if delta == 0 or (delta < 0) != verkaufen:
                        continue
                    if t in soll and abs(delta) * kurs[t] / f < MIN_HANDEL * je:
                        continue  # kleine Anpassung lohnt den Spread nicht
                    preis = kurs[t] * (1 - SPREAD if delta < 0 else 1 + SPREAD)
                    bargeld -= delta * preis / f + gebuehr
                    rest = stueck.get(t, 0.0) + delta
                    if t not in soll or abs(rest) < 1e-12:
                        stueck.pop(t, None)
                    else:
                        stueck[t] = rest
                    orders += 1
            ziel = None
        werte.append(bargeld + sum(s * C[k, sp[t]] for t, s in stueck.items()) / fx[k])
        if k < bis_i and monat[k] != monat[k + 1]:  # letzter Handelstag des Monats: neu entscheiden
            ziel = _auswahl(T, art, k, n, lang, kurz, filter_ticker, rng, feste, stichtag)
    kurve = pd.Series(werte, index=tage[von_i:bis_i + 1])
    kurve.attrs["orders"] = orders
    return kurve


def _auswahl(T, art, i, n, lang, kurz, filter_ticker, rng, feste, stichtag=False):
    if filter_ticker and not _ueber_200(T, filter_ticker, i):
        return []
    if feste:
        return [t for t in feste if pd.notna(T["roh"][t].iloc[i])]
    p = punkte(T, art, i, lang, kurz, stichtag)
    if p.empty:
        return []
    if rng is not None:
        return list(rng.choice(p.index.to_numpy(), min(n, len(p)), replace=False))
    return list(p.sort_values(ascending=False).index[:n])


def kennzahlen(kurve):
    """Rendite pro Jahr, größter Rückgang (beides in %) und Orders pro Jahr."""
    kurve = kurve.dropna()
    jahre = max((kurve.index[-1] - kurve.index[0]).days / 365.25, 1 / 365.25)
    hoch = kurve.cummax()
    erg = {"rendite": float(100 * ((kurve.iloc[-1] / START_WERT) ** (1 / jahre) - 1)),
           "rueckgang": float(((hoch - kurve) / hoch).max() * 100)}
    if "orders" in kurve.attrs:
        erg["orders_jahr"] = kurve.attrs["orders"] / jahre
    return erg


def halten(cache, ticker, von, bis):
    """Einmal kaufen und halten (Vergleich)."""
    return depot(cache, von, bis, "fest", 1, filter_ticker=None, feste=[ticker])


def kombi(bot, eigen, anteil_bot):
    """Zwei Depots nebeneinander (ohne Umschichten): anteil_bot vom Startgeld im Swing-Bot, der Rest im eigenen Depot."""
    bot = _tage(bot.to_frame("w"))["w"]
    beide = pd.concat([bot, eigen], axis=1, keys=["bot", "eigen"]).sort_index().ffill().dropna()
    kurve = START_WERT * (anteil_bot * beide["bot"] / beide["bot"].iloc[0]
                          + (1 - anteil_bot) * beide["eigen"] / beide["eigen"].iloc[0])
    kurve.attrs.update(eigen.attrs)
    return kurve
