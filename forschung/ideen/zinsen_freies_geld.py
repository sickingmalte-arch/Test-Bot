"""Wunsch des Nutzers vom 24.11.2026 („Zinsen auf freies Geld“). Messung, keine Kaufregel: Was brächte es, wenn das Geld,
das am Vorabend nicht in Aktien steckt, Zinsen bekäme – so wie es viele Broker heute auf das Kontoguthaben zahlen?
Rechnung des freien Geldes und der Zinsen: forschung/optionen_hilfe.py (freies_geld, ueberlagern)."""
import io
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import optionen_hilfe as O  # noqa: E402

NAME = "Zinsen auf das freie Geld (Messung)"
QUELLE = ("Europäische Zentralbank, Einlagesatz (Data Portal, Reihe FM.D.U2.EUR.4F.KR.DFR.LEV) – viele Broker zahlen "
          "heute Zinsen nahe an diesem Satz auf das Geld im Konto.")
BESCHREIBUNG = ("Keine neue Kaufregel: Der Bot handelt wie immer (Watchlist, mit Gebühr und Spread). Gemessen wird nur, "
                "was es bringt, wenn das Geld, das am Vorabend nicht in Aktien steckt, Zinsen bekommt. Angenommen: "
                "Einlagesatz der EZB minus 0,5 Punkte, nie unter 0 % (vorsichtig; 2015–2021 also 0 %). Zinsen Tag "
                "für Tag nach Kalendertagen, mit Zinseszins. Zur Info auch der volle Einlagesatz (nie unter 0 %).")
VERMUTUNG = ("Oft steckt nur gut die Hälfte des Geldes in Aktien. Zinsen auf den Rest heben die Rendite ohne mehr "
             "Rückgang – in den Jahren mit hohen Zinsen (2022–2026) um mehr als 0,5 Punkte im Jahr.")
WIDERLEGT_WENN = ("In einem Zeitraum weniger Rendite oder mehr Rückgang als der jetzige Bot, oder 2022–2026 weniger als "
                  "0,5 Punkte mehr Rendite im Jahr.")
VARIANTEN = ("1 Messung mit fester Annahme (Einlagesatz minus 0,5 Punkte, nie unter 0 %), vor dem Rechnen festgelegt; "
             "der volle Satz nur zur Info. Keine Gegenprobe nötig: Zinsen wählen keine Aktien aus.")

EZB = "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata"
ANNAHMEN = {"vorsichtig": 0.5, "voll": 0.0}  # Abschlag in Prozentpunkten
SCHWELLE = 0.5  # Punkte mehr Rendite 2022–2026, die die Vermutung verlangt


def ezb_einlagesatz(url=EZB):
    """Einlagesatz der EZB in % (Tage mit Änderung oder jeder Tag), None, wenn nicht zu laden. Bewusst ohne die SEC-Kennung."""
    try:
        anfrage = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Forschung Swing-Bot)"})
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            df = pd.read_csv(io.StringIO(antwort.read().decode("utf-8", "replace")))
        zeit = df["TIME_PERIOD"] if "TIME_PERIOD" in df else df.iloc[:, 0]
        wert = df["OBS_VALUE"] if "OBS_VALUE" in df else df.iloc[:, -1]
        s = pd.Series(pd.to_numeric(wert, errors="coerce").to_numpy(), index=pd.to_datetime(zeit, errors="coerce"))
        s = O._ohne_zone(s[s.index.notna()])
    except Exception:  # noqa: BLE001 – Netzfehler oder anderes Format: dann Ersatzquelle
        return None
    plausibel = len(s) >= 10 and s.index[0] <= pd.Timestamp("2009-12-31") and s.between(-2, 10).all()
    return s if plausibel else None


def zinssatz(satz, kalender, abschlag):
    """Jahreszins in % je Tag des Kalenders (letzter bekannter Satz, minus Abschlag, nie unter 0)."""
    s = satz.reindex(satz.index.union(kalender)).ffill().reindex(kalender)
    return (s.fillna(0.0) - abschlag).clip(lower=0.0)


def tagesrate(jahr):
    """Ertrag je Zeile: Jahreszins mal Kalendertage seit der Zeile davor / 365."""
    tage = pd.Series(jahr.index, index=jahr.index).diff().dt.days.fillna(0.0)
    return jahr / 100 * tage / 365


def pruefen(P, a, watch, sektor_von):
    zr = {von: {"bis": min(pd.Timestamp(bis), P.ENDE), "kandidaten": len(watch), "listen": [list(watch)]}
          for von, bis in P.R.ZEITRAEUME.values()}
    satz, quelle = ezb_einlagesatz(), "Einlagesatz der EZB (Data Portal)"
    if satz is None:
        satz, quelle = O.yahoo_reihe("^IRX"), "US-Geldmarkt (^IRX), weil die EZB-Reihe nicht zu laden war"
    if satz is None:
        satz, quelle = pd.Series([0.0], index=[pd.Timestamp("2000-01-01")]), "nicht geladen – 0 % gerechnet"
    print("Zinsen:", quelle)

    def auswerter(deps, daten):
        je = []
        for dep in deps:
            kurve = dep["verlauf"].astype(float)
            frei = O.freies_geld(P.R.sw, dep, daten)
            e = {"bot": P.ROT.kennzahlen(kurve), "frei": float((frei / kurve).mean() * 100)}
            for name, abschlag in ANNAHMEN.items():
                jahr = zinssatz(satz, kurve.index, abschlag)
                e[name] = P.ROT.kennzahlen(O.ueberlagern(kurve, frei, tagesrate(jahr)))
                e[f"satz_{name}"] = float(jahr.mean())
            je.append(e)
        return O.mittel(je)
    werte = {v: w[0] for v, w in O.auswerten(P, a, sektor_von, zr, None, auswerter).items()}
    vs = list(zr)
    plus = {v: werte[v]["vorsichtig"]["rendite"] - werte[v]["bot"]["rendite"] for v in vs}
    tiefer = {v: werte[v]["vorsichtig"]["rueckgang"] - werte[v]["bot"]["rueckgang"] for v in vs}
    if any(plus[v] < 0 or tiefer[v] > 0.05 for v in vs):
        text = "widerlegt: in einem Zeitraum weniger Rendite oder mehr Rückgang"
    elif plus[vs[-1]] < SCHWELLE:
        text = f"widerlegt: 2022–2026 nur {plus[vs[-1]]:+.1f} Punkte (verlangt: mindestens +{SCHWELLE:.1f})"
    else:
        text = "Vermutung bestätigt: " + " / ".join(f"{plus[v]:+.1f}" for v in vs) + " Punkte pro Jahr"
    text = text.replace(".", ",")
    z = [f"# 🔬 {NAME}", "", f"Getestet am {pd.Timestamp.today():%d.%m.%Y} · Quelle: {QUELLE}", "", BESCHREIBUNG, "",
         f"- **Vermutung:** {VERMUTUNG}", f"- **Widerlegt, wenn:** {WIDERLEGT_WENN}", f"- **Varianten:** {VARIANTEN}",
         "", f"**Ergebnis: {text}**", "", "| Rendite pro Jahr / größter Rückgang | " + " | ".join(P.R.ZEITRAEUME) + " |",
         "|---|" + "---:|" * len(vs)]

    def zelle(e):
        return f"{e['rendite']:+.1f} % / −{e['rueckgang']:.0f} %".replace(".", ",")
    z += ["| Jetziger Bot (freies Geld ohne Zinsen) | " + " | ".join(zelle(werte[v]["bot"]) for v in vs) + " |",
          "| … freies Geld im Schnitt (Anteil am Depot) | " + " | ".join(
              f"{werte[v]['frei']:.0f} %" for v in vs) + " |"]
    for name, titel in (("vorsichtig", "**Mit Zinsen: Einlagesatz − 0,5 Punkte**"),
                        ("voll", "Mit dem vollen Einlagesatz (zur Info)")):
        z += [f"| {titel} | " + " | ".join(zelle(werte[v][name]) for v in vs) + " |",
              "| … Zinssatz im Schnitt · Unterschied zum Bot (Punkte pro Jahr) | " + " | ".join(
                  f"{werte[v][f'satz_{name}']:.2f} % · {O.zahl(werte[v][name]['rendite'] - werte[v]['bot']['rendite'], 2)}"
                  .replace(".", ",") for v in vs) + " |"]
    z += ["", f"Daten: Zinsen – {quelle}. Watchlist mit {len(watch)} Aktien, Mittel aus {a.laeufe} Läufen, mit Gebühr "
          "und Spread. Ohne Steuern (wie überall im Bot). Gezählt wird das Geld, das am Vorabend nicht in Aktien steckt; "
          "die Zinsen selbst verzinsen sich mit. Simulation mit Spielgeld, keine Anlageberatung."]
    md = "\n".join(z) + "\n"
    basis = {v: werte[v]["bot"] for v in vs}
    return text, plus, {"basis": basis, "werte": werte, "quelle": quelle,
                        "abweichung_rueckgang": {v: float(np.round(tiefer[v], 3)) for v in vs}}, md
