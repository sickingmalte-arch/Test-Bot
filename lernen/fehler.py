"""Lernmodell des Swing-Bots: Fehler-Analyse – warum hat ein Trade verloren?

Jeder abgeschlossene Trade mit Verlust bekommt einen oder mehrere Gründe. Die Gründe werden gezählt und im Bericht
ausgewertet. Das Lernmodell bekommt zu jedem Grund passende Merkmale (z. B. Kurslücken zuletzt, Angst-Index VIX,
Stärke der Branche, wie weit die Aktie schon gelaufen war) – so kann es lernen, solche Verluste zu vermeiden.
Ob das klappt, zeigt der Vergleich: Wie oft kommt jeder Fehler bei allen Signalen vor, wie oft bei den Signalen,
die das Modell auswählt?
"""
import numpy as np
import pandas as pd

GRUENDE = {
    "kursluecke": "Kurslücke unter den Stop (über Nacht)",
    "markt": "Absturz des Gesamtmarkts",
    "branche": "Branche schwach",
    "zahlen": "Quartalszahlen",
    "zu_spaet": "Signal zu spät (Aktie war schon weit gelaufen)",
    "stop_eng": "Stop zu eng (Kurs war danach schnell wieder über dem Einstieg)",
    "nachricht": "Plötzlicher Einbruch nur dieser Aktie (vermutlich eine Nachricht)",
    "zeit": "Zeitstopp ohne Schwung",
    "normal": "Normales Auf und Ab (kein besonderer Grund)",
}


def gruende(trade, d, spy, branche_index=None, gelaufen=None):
    """Gründe für einen Verlust-Trade. trade: dict mit einstieg_i, ausstieg_i, signal_i, einstieg, grund, R.
    d: Daten der Aktie (O, H, L, C, ATR, idx, morgen/gerade), spy: Schlusskurse S&P 500 (Series nach Datum),
    branche_index: Durchschnitt der Branche (Series), gelaufen: Wert „schon gelaufen“ am Signaltag (in ATR)."""
    if trade.get("R") is None or trade["R"] >= 0:
        return []
    i0, i1, s = trade["einstieg_i"], trade["ausstieg_i"], trade.get("signal_i", trade["einstieg_i"] - 1)
    idx = d["idx"]
    aus = []
    grund = str(trade.get("grund", ""))
    if "Kurslücke" in grund and "Stop" in grund:
        aus.append("kursluecke")
    sp = spy.reindex(idx[max(s, 0):i1 + 1]).ffill()
    if len(sp) > 1:
        gesamt = sp.iloc[-1] / sp.iloc[0] - 1
        schlechtester_tag = (sp / sp.shift() - 1).min()
        if gesamt <= -0.03 or schlechtester_tag <= -0.025:
            aus.append("markt")
        if branche_index is not None:
            b = branche_index.reindex(idx[max(s, 0):i1 + 1]).ffill()
            if len(b) > 1 and np.isfinite(b.iloc[0]) and (b.iloc[-1] / b.iloc[0] - 1) - gesamt <= -0.03:
                aus.append("branche")
    reak = np.asarray(d.get("gerade", np.zeros(d["n"], bool)))
    if reak[i0:i1 + 1].any() or "Quartalszahlen" in grund:
        aus.append("zahlen")
    atr_s = d["ATR"][s] if 0 <= s < d["n"] else np.nan
    if (gelaufen is not None and gelaufen >= 4) or (np.isfinite(atr_s) and d["O"][i0] - d["C"][s] >= 0.5 * atr_s):
        aus.append("zu_spaet")
    if grund.startswith("Stop") and i1 + 1 < d["n"]:
        danach = d["C"][i1 + 1:min(i1 + 11, d["n"])]
        if len(danach) and np.nanmax(danach) >= trade["einstieg"]:
            aus.append("stop_eng")
    c, atr = d["C"], d["ATR"]
    for k in range(i0, i1 + 1):
        if k > 0 and np.isfinite(atr[k - 1]) and c[k] - c[k - 1] <= -3 * atr[k - 1]:
            markt_tag = sp.get(idx[k], np.nan) / sp.get(idx[k - 1], np.nan) - 1 if idx[k - 1] in sp.index else np.nan
            if not (np.isfinite(markt_tag) and markt_tag <= -0.01):
                aus.append("nachricht")
                break
    if "Zeitstopp" in grund:
        aus.append("zeit")
    return aus or ["normal"]


def auswertung(trades):
    """Zählt die Gründe über alle Verlust-Trades: Anteil der Verluste und Ø R."""
    verluste = [t for t in trades if t.get("R") is not None and t["R"] < 0]
    if not verluste:
        return pd.DataFrame(columns=["grund", "text", "anzahl", "anteil", "R"])
    zeilen = []
    for g, text in GRUENDE.items():
        mit = [t for t in verluste if g in (t.get("fehler") or [])]
        zeilen.append({"grund": g, "text": text, "anzahl": len(mit), "anteil": len(mit) / len(verluste),
                       "R": float(np.mean([t["R"] for t in mit])) if mit else np.nan})
    return pd.DataFrame(zeilen).sort_values("anzahl", ascending=False)


def vergleich(kand, ausgewaehlt):
    """Lernt das Modell, Fehler zu vermeiden? Je Grund: Anteil der gedachten Trades, die mit diesem Grund verloren
    haben – bei allen Signalen und bei den vom Modell ausgewählten. kand: Spalten status, R, fehler ('|'-getrennt);
    ausgewaehlt: Maske (True = das Modell hätte gekauft)."""
    k = kand[kand["status"] == "fertig"]
    wahl = np.asarray(ausgewaehlt, bool)[(kand["status"] == "fertig").to_numpy()]
    listen = k["fehler"].fillna("").astype(str).str.split("|")
    zeilen = []
    for g, text in GRUENDE.items():
        hat = listen.apply(lambda x, g=g: g in x).to_numpy()
        zeilen.append({"grund": g, "text": text, "alle": float(hat.mean()) if len(hat) else np.nan,
                       "ausgewaehlt": float(hat[wahl].mean()) if wahl.any() else np.nan})
    tab = pd.DataFrame(zeilen).sort_values("alle", ascending=False)
    tab.attrs["n_alle"], tab.attrs["n_ausgewaehlt"] = int(len(k)), int(wahl.sum())
    tab.attrs["verlust_alle"] = float((k["R"] < 0).mean()) if len(k) else np.nan
    tab.attrs["verlust_ausgewaehlt"] = float((k["R"][wahl] < 0).mean()) if wahl.any() else np.nan
    return tab
