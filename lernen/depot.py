"""Lernmodell des Swing-Bots: Depot-Simulation für den Rückblick, mit denselben Grenzen wie das Übungsdepot.

- Kauf zur nächsten Eröffnung bis zum Limit, höchstens 5 Positionen, höchstens 2 aus derselben Branche (GICS),
  1 % Risiko je Trade, höchstens 25 % des Depots je Position, zusammen höchstens 5 % Risiko, 1 € Gebühr und 0,1 %
  Spread je Order.
- Auswahl „alle“: wie der jetzige Bot (bestes Chance/Risiko zuerst). Auswahl „modell“: nur Signale mit hoher
  Punktzahl des Lernmodells, die besten zuerst.
- Ausstieg (Punkt 4 „nicht bei jedem Schreck verkaufen“):
    normal  – wie heute: Stop gilt jederzeit, Ziel, vor Quartalszahlen raus, Zeitstopp.
    schluss – Stop zählt erst zum Tagesschluss; eine Notbremse 1,5 R unter dem Einstieg gilt jederzeit.
    panik   – nur an Panik-Tagen des Gesamtmarkts (S&P 500 eröffnet 1,5 % tiefer oder fällt im Tag 2,5 %)
              entscheidet der Stop erst zum Schluss, sonst wie heute; Notbremse 1,5 R.
    stark   – nur bei starken Aktien (3 Monate mindestens 5 % besser als der S&P 500) Stop zum Schluss.
  Damit das Risiko je Trade nie über 1 % steigt, richtet sich die Stückzahl bei diesen Varianten nach der
  Notbremse statt nach dem Stop (also kleinere Positionen).
"""
import random

import numpy as np
import pandas as pd

import merkmale as M

sw = M.sw
REGELN = dict(konto=10_000.0, risiko=1.0, max_pos=5, je_sektor=2, gesamt_risiko=5.0, gebuehr=1.0, min_einsatz=25.0)
NOTBREMSE_R = 1.5
VARIANTEN = {
    "normal": "Stop wie heute (gilt jederzeit)",
    "schluss": "Stop erst zum Tagesschluss, Notbremse bei 1,5 R",
    "panik": "nur an Panik-Tagen Stop erst zum Schluss, Notbremse bei 1,5 R",
    "stark": "nur bei starken Aktien Stop zum Schluss, Notbremse bei 1,5 R",
}


def panik_tage(spy):
    o, l, c = spy["Open"], spy["Low"], spy["Close"]
    vortag = c.shift()
    return ((o / vortag - 1 <= -0.015) | (l / vortag - 1 <= -0.025)).fillna(False)


def stark(z):
    return bool(np.nan_to_num(z.get("rs63", np.nan), nan=-1) >= 0.05 and np.nan_to_num(z.get("mom126", np.nan)) > 0)


def _ausstieg(d, i, pos, variante, panik):
    besonders = (variante == "schluss" or (variante == "panik" and panik)
                 or (variante == "stark" and pos["stark"]))
    if not besonders:
        return sw.pruefe_ausstieg(d, i, 1, pos)
    o, h, l, c = d["O"][i], d["H"][i], d["L"][i], d["C"][i]
    nb, nicht_neu = pos["notbremse"], pos["start"] != i
    if nicht_neu and np.isfinite(o) and o <= nb:
        return o, "Notbremse (Kurslücke)"
    if nicht_neu and np.isfinite(o) and o >= pos["ziel"]:
        return o, "Ziel (Kurslücke)"
    if l <= nb:
        return nb, "Notbremse"
    if h >= pos["ziel"]:
        return pos["ziel"], "Ziel"
    if c <= pos["stop"]:
        return c, "Stop zum Schluss"
    if d["morgen"][i]:
        return c, "vor Quartalszahlen"
    if i - pos["start"] + 1 >= sw.ZEITSTOPP_TAGE:
        return c, "Zeitstopp"
    return None, None


class Depot:
    """Ein Depot mit den Regeln oben, Tag für Tag durchgerechnet. Mit als_dict / aus_dict lässt es sich speichern und
    später weiterrechnen."""

    def __init__(self, variante="normal", regeln=None):
        self.r = dict(REGELN, **(regeln or {}))
        self.variante = variante
        self.bargeld = self.wert = self.r["konto"]
        self.positionen, self.auftraege, self.trades, self.verlauf = {}, [], [], []

    # 1) Aufträge vom Vortag zur Eröffnung
    def eroeffnung(self, tag, daten):
        r, warten = self.r, []
        for a in self.auftraege:
            t = a["ticker"]
            d = daten.get(t)
            i = d["pos"].get(tag) if d is not None else None
            if i is None:
                warten.append(a)
                continue
            if t in self.positionen or not sw.einstieg_moeglich(d, i, 1, a["stop"], a["limit"]):
                continue
            if len(self.positionen) >= r["max_pos"]:
                continue
            if sum(1 for p in self.positionen.values() if p["sektor"] == a["sektor"]) >= r["je_sektor"]:
                continue
            rate = d["FX"][i]
            einstieg = sw.mit_spread(d["O"][i], 1, True)
            ist_stark = stark(a)
            mit_nb = self.variante in ("schluss", "panik") or (self.variante == "stark" and ist_stark)
            nb = a["kurs"] - NOTBREMSE_R * (a["kurs"] - a["stop"]) if mit_nb else None
            plan = nb if mit_nb else a["stop"]
            frei = self.wert * r["gesamt_risiko"] / 100 - sum(p["risiko_plan"] for p in self.positionen.values())
            stueck = sw.positionsgroesse(einstieg / rate, plan / rate, self.wert, r["risiko"], False,
                                         self.bargeld - r["gebuehr"], frei)
            einsatz = stueck * einstieg / rate
            if stueck <= 0 or einsatz < r["min_einsatz"]:
                continue
            self.bargeld -= einsatz + r["gebuehr"]
            self.positionen[t] = {
                "ticker": t, "start": i, "kauf_tag": tag, "stop": a["stop"], "ziel": a["ziel"], "notbremse": nb,
                "stark": ist_stark, "stueck": stueck, "einstieg": einstieg, "kosten": einsatz + r["gebuehr"],
                "sektor": a["sektor"], "strategie": a["strategie"], "risiko_eur": stueck * (einstieg - a["stop"]) / rate,
                "risiko_plan": stueck * (einstieg - plan) / rate, "depotwert": self.wert, "signal_tag": a["tag"],
                "punkte": a.get("punkte"), "gelaufen10": a.get("gelaufen10")}
        self.auftraege = warten

    # 2) Stop, Ziel, Quartalszahlen, Zeitstopp
    def ausstiege(self, tag, daten, panik=False):
        for t in list(self.positionen):
            p, d = self.positionen[t], daten.get(t)
            i = d["pos"].get(tag) if d is not None else None
            if i is None:
                continue
            p["start"] = d["pos"].get(p["kauf_tag"], p["start"])  # Kaufkerze (falls die Kursreihe neu geladen wurde)
            preis, grund = _ausstieg(d, i, p, self.variante, panik)
            if preis is None:
                continue
            rate = d["FX"][i]
            erloes = p["stueck"] * sw.mit_spread(preis, 1, False) / rate - self.r["gebuehr"]
            self.bargeld += erloes
            del self.positionen[t]
            self.trades.append({**p, "verkauf_tag": tag, "ausstieg_i": i, "einstieg_i": p["start"], "grund": grund,
                                "erloes": erloes, "ausstieg": preis,
                                "R": (erloes - p["kosten"]) / p["risiko_eur"] if p["risiko_eur"] > 0 else np.nan})

    # 3) neue Aufträge aus den Signalen von heute (zum Schluss), schon in der gewünschten Reihenfolge
    def neue_auftraege(self, kandidaten):
        self.auftraege = [z for z in kandidaten if z["ticker"] not in self.positionen]

    # 4) Depotwert zum Schluss
    def bewerten(self, tag, daten):
        wert = self.bargeld
        for t, p in self.positionen.items():
            d = daten[t]
            i = d["pos"].get(tag)
            if i is None:
                i = max(int(d["idx"].searchsorted(tag)) - 1, 0)
            wert += p["stueck"] * d["C"][i] / d["FX"][i]
        self.wert = wert
        self.verlauf.append((tag, wert))

    def tag(self, tag, daten, kandidaten, panik=False):
        self.eroeffnung(tag, daten)
        self.ausstiege(tag, daten, panik)
        self.neue_auftraege(kandidaten)
        self.bewerten(tag, daten)

    # Speichern und Laden
    AUFTRAG_FELDER = ("ticker", "tag", "strategie", "sektor", "kurs", "stop", "ziel", "limit", "crv", "punkte",
                      "rs63", "mom126", "gelaufen10")
    TAGE = ("tag", "kauf_tag", "signal_tag", "verkauf_tag")

    def als_dict(self):
        auftraege = [{k: a.get(k) for k in self.AUFTRAG_FELDER} for a in self.auftraege]
        return _json({"variante": self.variante, "regeln": self.r, "bargeld": self.bargeld, "depotwert": self.wert,
                      "positionen": list(self.positionen.values()), "auftraege": auftraege, "trades": self.trades,
                      "verlauf": [[t, w] for t, w in self.verlauf]})

    @classmethod
    def aus_dict(cls, z):
        dep = cls(z["variante"], z["regeln"])
        dep.bargeld, dep.wert = float(z["bargeld"]), float(z["depotwert"])

        def tage(x):
            return {k: (pd.Timestamp(v) if k in cls.TAGE and v is not None else v) for k, v in x.items()}
        dep.positionen = {p["ticker"]: tage(p) for p in z["positionen"]}
        dep.auftraege = [tage(a) for a in z["auftraege"]]
        dep.trades = [tage(t) for t in z["trades"]]
        dep.verlauf = [(pd.Timestamp(t), float(w)) for t, w in z["verlauf"]]
        return dep


def _json(x):
    """Für JSON: Zeitpunkte als Datum, numpy-Zahlen als Python-Zahlen, NaN als leer."""
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json(v) for v in x]
    if isinstance(x, pd.Timestamp):
        return x.strftime("%Y-%m-%d")
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else float(x)
    return x


def tagesliste(kand, auswahl, seed=0, tickers=()):
    """Kandidaten je Tag in der Reihenfolge, in der gekauft wird."""
    rng = random.Random(seed)
    reihe = sorted(set(tickers) | set(kand["ticker"]))
    rng.shuffle(reihe)
    rang = {t: n for n, t in enumerate(reihe)}
    aus = {}
    for tag, g in kand.groupby("tag"):
        z = g.to_dict("records")
        if auswahl == "modell":
            z.sort(key=lambda x: (-x["punkte"], rang.get(x["ticker"], 0)))
        else:
            z.sort(key=lambda x: (-x["crv"], sw.VORRANG[x["strategie"]], rang.get(x["ticker"], 0)))
        aus[tag] = z
    return aus


def auswaehlen(kand, auswahl, schwellen=None, marktfilter=None):
    if auswahl == "modell":
        kand = kand[kand["punkte"].notna()]
        if schwellen is not None:
            monat = kand["tag"].dt.to_period("M")
            kand = kand[kand["punkte"].to_numpy() >= monat.map(schwellen).fillna(np.inf).to_numpy()]
    if marktfilter is not None:
        kand = kand[kand["tag"].map(marktfilter).fillna(True).astype(bool).to_numpy()]
    return kand


def simuliere(daten, kand, tage, auswahl="alle", variante="normal", schwellen=None, seed=0, regeln=None,
              marktfilter=None):
    """kand: Kandidaten mit ticker, i, tag, stop, ziel, limit, kurs, crv, strategie, sektor (und punkte).
    schwellen: Series Monat -> Mindest-Punktzahl (nur bei auswahl='modell'). marktfilter: Series Tag -> True,
    wenn Long-Käufe erlaubt sind (wie beim jetzigen Bot: Nasdaq-100 am Vortag über der 200-Tage-Linie)."""
    tage = pd.DatetimeIndex(tage)
    kand = kand[(kand["tag"] >= tage[0]) & (kand["tag"] <= tage[-1])]
    je_tag = tagesliste(auswaehlen(kand, auswahl, schwellen, marktfilter), auswahl, seed, daten)
    panik = panik_tage(daten["__SPY__"]) if "__SPY__" in daten else pd.Series(False, index=tage)
    dep = Depot(variante, regeln)
    for tag in tage:
        dep.tag(tag, daten, je_tag.get(tag, []), bool(panik.get(tag, False)))
    kurve = pd.Series([w for _, w in dep.verlauf], index=[t for t, _ in dep.verlauf])
    return {"kurve": kurve, "trades": dep.trades, "offen": list(dep.positionen.values())}


def kennzahlen(erg, konto=REGELN["konto"]):
    k = erg["kurve"]
    if k.empty:
        return {}
    jahre = max((k.index[-1] - k.index[0]).days / 365.25, 1e-9)
    tr = erg["trades"]
    rr = np.array([t["R"] for t in tr if np.isfinite(t["R"])])
    gew = np.array([t["erloes"] - t["kosten"] for t in tr])
    return {"rendite": 100 * ((k.iloc[-1] / konto) ** (1 / jahre) - 1),
            "rueckgang": float(((k.cummax() - k) / k.cummax()).max() * 100),
            "treffer": float((gew > 0).mean() * 100) if len(gew) else np.nan,
            "schnitt_r": float(rr.mean()) if len(rr) else np.nan,
            "trades_jahr": len(tr) / jahre}


def kaufen_und_halten(df, fx, von, bis, konto=REGELN["konto"], gebuehr=REGELN["gebuehr"]):
    """Index-Fonds am ersten Tag zur Eröffnung kaufen und halten (in €, mit Gebühr und Spread)."""
    d = df[(df.index >= von) & (df.index <= bis)]
    rate = sw.kurs_umrechner(fx, d.index).to_numpy(float)
    stueck = (konto - gebuehr) / (sw.mit_spread(d["Open"].iloc[0], 1, True) / rate[0])
    werte = pd.Series(stueck * d["Close"].to_numpy(float) / rate, index=d.index)
    jahre = (werte.index[-1] - werte.index[0]).days / 365.25
    return {"rendite": 100 * ((werte.iloc[-1] / konto) ** (1 / jahre) - 1),
            "rueckgang": float(((werte.cummax() - werte) / werte.cummax()).max() * 100)}
