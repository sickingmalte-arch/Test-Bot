"""Wunsch des Nutzers vom 17.11.2026 („Es muss doch einen Weg geben, Shorts profitabel zu machen“ – gewählt: „Short
schwacher Bilanzen“): Shorts nur auf Firmen, die Geld verlieren oder schrumpfen. Geprüft wie der faire Short-Test auf
Zufallslisten aus dem damaligen S&P 500 (forschung/short_fair_hilfe.py)."""
import os
import sys
import types

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import short_fair_hilfe as F  # noqa: E402

NAME = "Short schwacher Bilanzen: Short-Signale nur bei Firmen mit Verlust oder schrumpfendem Geschäft"
QUELLE = ("Campbell, Hilscher & Szilagyi (2008), „In Search of Distress Risk“, Journal of Finance 63 – Aktien mit hohem "
          "Pleiterisiko bringen auffällig wenig; Piotroski (2000), „Value Investing: The Use of Historical Financial "
          "Statement Information to Separate Winners from Losers“, Journal of Accounting Research 38 – Firmen mit "
          "schwachen Bilanzzahlen schneiden schlechter ab.")
BESCHREIBUNG = ("Der Bot darf nur Aktien shorten, deren zuletzt veröffentlichte Bilanz schwach ist: Verlust in den "
                "letzten 12 Monaten ODER Umsatz und Gewinn beide unter Vorjahr. Zahlen von der SEC, bekannt erst ab dem "
                "Tag nach der Veröffentlichung. Short nur, wenn zusätzlich eins der 8 alten Short-Signale feuert. Wie im "
                "fairen Short-Test: 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum, höchstens 2 Shorts "
                "gleichzeitig, Stop und Ziel wie im Bot, mit Gebühr und Spread. Gegenprobe: je Aktie gleich viele "
                "Shorts an zufälligen erlaubten Tagen, ohne Blick auf die Bilanz.")
VERMUTUNG = ("Firmen, die Geld verlieren oder schrumpfen, fallen öfter weiter. Shorts nur auf solche Aktien verdienen "
             "Geld und machen den Bot in allen drei Zeiträumen besser – und besser als Shorts an zufälligen Tagen.")
WIDERLEGT_WENN = ("Keine Variante schafft in jedem Zeitraum alles davon: Mitte der 8 Listen mehr Rendite als der Bot nur "
                  "mit Long, mindestens 6 von 8 Listen besser, höchstens 1 Punkt mehr Rückgang (Mitte), mindestens 30 "
                  "Short-Trades und mehr Rendite als die beste von 6 Zufalls-Gegenproben.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: (1) nur außerhalb des Aufwärtsmarkts wie die alten Shorts, (2) in jeder "
             "Marktlage. „Schwach“ fest: Verlust in 12 Monaten ODER Umsatz und Gewinn beide unter Vorjahr.")


def _schwach_maske(P, cache):
    """maske(ticker, d) -> bool je Kurstag (schwache Bilanz bekannt). Je Aktie einmal über die ganze Kursreihe
    gerechnet: der Wert eines Tages hängt nur von Bilanzen ab, die vor diesem Tag veröffentlicht waren – ein
    kürzerer Zeitraum schneidet die Reihe nur ab."""
    import merkmale as M  # lernen/merkmale.py liegt im Suchpfad des Prüfstands
    voll = {}

    def rechnen(t):
        try:
            bilanz, kurse = P.D.lies_bilanz(cache, t), P.D.lies_kurse(cache, t)
            if bilanz is None or kurse is None or not len(kurse):
                return None
            # nur, was „schwach“ braucht (Umsatz, Gewinn; Vermögen nur für die Berichtstage) – spart viel Rechenzeit
            bilanz = bilanz[bilanz["gruppe"].isin(["umsatz", "gewinn", "vermoegen"])]
            roh = kurse["Roh"] if "Roh" in kurse else kurse["Close"]
            split = kurse["Split"] if "Split" in kurse else None
            m = M.bilanz_reihen(kurse.index, bilanz, roh, split)
        except Exception:  # noqa: BLE001 – kaputte Bilanzdatei: diese Aktie wird nicht geshortet
            return None
        verlust = m["verlust"].to_numpy(dtype=float) == 1
        um, ge = m["umsatz_wachstum"].to_numpy(dtype=float), m["gewinn_wachstum"].to_numpy(dtype=float)
        with np.errstate(invalid="ignore"):
            schwach = verlust | ((um < 0) & (ge < 0))
        return pd.Series(schwach, index=kurse.index)

    def maske(t, d=None, idx=None):
        idx = d["idx"] if idx is None else idx
        if t not in voll:
            voll[t] = rechnen(t)
        if voll[t] is None:
            return np.zeros(len(idx), bool)
        return voll[t].reindex(idx).fillna(False).to_numpy(dtype=bool)
    return maske, voll


def _anteile(P, a, zr, maske, voll):
    """Je Zeitraum: Aktien mit Bilanzdaten und Anteil der Börsentage mit schwacher Bilanz (in den gezogenen Aktien)."""
    teile = []
    for von, z in zr.items():
        mit = ohne = tage = schwach = 0
        for t in sorted({t for liste in z["listen"] for t in liste}):
            kurse = P.D.lies_kurse(a.cache, t)
            if kurse is None:
                continue
            idx = kurse.index[(kurse.index >= pd.Timestamp(von)) & (kurse.index <= z["bis"])]
            m = maske(t, idx=idx)
            if voll.get(t) is None:
                ohne += 1
                continue
            mit += 1
            tage += len(idx)
            schwach += int(m.sum())
        teile.append(f"{von[:4]}–{pd.Timestamp(z['bis']).year}: {mit} Aktien mit Bilanz, {ohne} ohne, schwach an "
                     + (f"{100 * schwach / tage:.0f} %" if tage else "–") + " der Börsentage")
    return "- Bilanzdaten in den gezogenen Aktien: " + "; ".join(teile) + "."


def pruefen(P, a, watch, sektor_von):
    zr = F.listen(P, a, len(watch))
    maske, voll = _schwach_maske(P, a.cache)
    extra = _anteile(P, a, zr, maske, voll)
    print(extra)
    varianten = [
        {"key": "schwach_abwaerts", "kurz": "S1", "name": "+ alte Short-Signale nur bei schwacher Bilanz (nicht im "
                                                          "Aufwärtsmarkt)",
         "anpassen": lambda sw: F.alte_shorts(sw, maske=maske),
         "zufall": lambda sw, s: F.alte_shorts(sw, maske=maske, seed=s)},
        {"key": "schwach_immer", "kurz": "S2", "name": "+ alte Short-Signale nur bei schwacher Bilanz (jede Marktlage)",
         "anpassen": lambda sw: F.alte_shorts(sw, maske=maske, marktfilter=False),
         "zufall": lambda sw, s: F.alte_shorts(sw, maske=maske, marktfilter=False, seed=s)},
    ]
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG, VERMUTUNG=VERMUTUNG,
                                 WIDERLEGT_WENN=WIDERLEGT_WENN, VARIANTEN=VARIANTEN)
    return F.pruefen(P, a, sektor_von, idee, zr, varianten, len(watch), extra)
