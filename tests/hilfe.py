"""Gemeinsame Hilfen für die Tests: Bot laden, feste Kursdaten aus tests/daten lesen und den ganzen Ablauf
(Strategie-Tagebuch, Lernregel, virtuelles Depot) ohne Internet durchrechnen.

Die Kursdaten sind ein fester Ausschnitt (2017–2024, 8 Aktien der Watchlist, Nasdaq-100 und Euro-Kurs). Sie
ändern sich nie – rechnet der Bot damit anders als im gespeicherten Fingerabdruck, hat sich eine Regel geändert."""
import contextlib
import importlib.util
import io
import json
import pathlib
import re
import sys

import pandas as pd

WURZEL = pathlib.Path(__file__).resolve().parents[1]
DATEN = WURZEL / "tests" / "daten"
FINGERABDRUCK = WURZEL / "tests" / "fingerabdruck.json"
NY = "America/New_York"

AKTIEN = ["AAPL", "NVDA", "MSFT", "AMD", "LLY", "XOM", "JPM", "COST"]  # 4 × Technologie: prüft „höchstens 2 je Branche“
RUECKBLICK_MONATE = 36  # virtuelles Depot über 2022–2024, davor laufen Indikatoren und Lernregel ein

_BOT = None


def bot():
    """swing_scanner.py als Modul (einmal geladen, ohne den Bot zu starten)."""
    global _BOT
    if _BOT is None:
        spec = importlib.util.spec_from_file_location("swing_scanner", WURZEL / "swing_scanner.py")
        _BOT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_BOT)
    return _BOT


def einstellungen(*optionen):
    """Einstellungen wie beim automatischen Lauf (10.000 €, 1 % Risiko), ohne Schlagzeilen aus dem Internet."""
    sw = bot()
    alt = sys.argv
    sys.argv = ["swing_scanner.py", "--konto", "10000", "--risiko", "1", "--ohne-news", *optionen]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            einst = sw.lies_einstellungen()
    finally:
        sys.argv = alt
    einst.rueckblick = RUECKBLICK_MONATE  # länger als beim Bot erlaubt (18 Monate) – mehr Trades für den Vergleich
    return einst


def kurse(ticker):
    df = pd.read_csv(DATEN / "kurse" / f"{ticker}.csv", index_col=0)
    df.index = pd.to_datetime(df.index)  # wie yf.download: Tagesdaten ohne Zeitzone
    df.index.name = "Date"
    return df[["Open", "High", "Low", "Close", "Volume"]].astype(float)


def termine(ticker):
    """Quartalszahlen-Termine wie von Yahoo (Zeitzone New York) oder None."""
    datei = DATEN / "termine" / f"{ticker}.csv"
    if not datei.exists():
        return None
    df = pd.read_csv(datei, index_col=0)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(NY)
    df.index.name = "Earnings Date"
    return df


def vorbereiten(einst, aktien=AKTIEN):
    """(daten, alle_tage) wie im Bot: jede Aktie mit Indikatoren, Signalen, Quartalszahlen und Marktfilter."""
    sw = bot()
    fx = kurse("EURUSD=X")["Close"]
    trend = sw.markt_trend(kurse("QQQ")) if einst.marktfilter else None
    daten = {}
    for t in aktien:
        d = sw.bereite_vor(t, kurse(t), fx, termine(t), einst, trend)
        d["n_fertig"], d["offen"] = d["n"], False  # alte Daten: keine Kerze läuft noch
        daten[t] = d
    alle_tage = sorted(set().union(*(set(d["idx"][:d["n_fertig"]]) for d in daten.values())))
    return daten, alle_tage


def durchrechnen(*optionen):
    """Der ganze Ablauf mit den festen Daten: Tagebuch, Lernregel, virtuelles Depot."""
    sw = bot()
    einst = einstellungen(*optionen)
    daten, alle_tage = vorbereiten(einst)
    tagebuch = sw.strategie_tagebuch(daten, einst)
    pausen, _ = sw.lernverlauf(tagebuch, alle_tage, einst)
    depot = sw.simuliere_depot(daten, pausen, einst, einst.lernen)
    return tagebuch, pausen, depot, alle_tage


def tag(x):
    return pd.Timestamp(x).strftime("%Y-%m-%d")


def fingerabdruck():
    """Alles, was die Kaufregeln ausmacht, als einfach vergleichbare Liste: jeder gedachte Trade des Tagebuchs,
    jede Pausen-Änderung der Lernregel und jeder Trade des virtuellen Depots samt Endwert."""
    sw = bot()
    tagebuch, pausen, depot, alle_tage = durchrechnen()
    vorher, lernregel = frozenset(), []
    for t in alle_tage:
        jetzt = pausen[t]
        if jetzt != vorher:
            lernregel.append([tag(t), sorted(jetzt - vorher), sorted(vorher - jetzt)])
            vorher = jetzt
    return {
        "hinweis": "Automatisch erzeugt mit python tests/fingerabdruck_neu.py – nicht von Hand ändern.",
        "regeln": {k: getattr(sw, k) for k in REGEL_KONSTANTEN},
        "tagebuch": {
            "anzahl": len(tagebuch),
            "trades": [[e["ticker"], e["strategie"], tag(e["signal_tag"]), tag(e["einstieg_tag"]),
                        tag(e["ausstieg_tag"]), str(e["grund"]), round(float(e["R"]), 3)] for e in tagebuch],
        },
        "lernregel": lernregel,
        "depot": {
            "anzahl": len(depot["trades"]),
            "trades": [[x["ticker"], x["strategie"], tag(x["kauf_tag"]), tag(x["verkauf_tag"]), str(x["grund"]),
                        round(float((x["erloes"] - x["kosten"]) / x["risiko_eur"]), 3) if x["risiko_eur"] else 0.0]
                       for x in depot["trades"]],
            "offen": sorted(depot_offen(depot)),
            "end_wert": round(float(depot["end_wert"]), 2),
            "max_rueckgang": round(float(depot["max_rueckgang"]), 2),
            "gebuehren": round(float(depot["gebuehren"]), 2),
        },
    }


def depot_offen(depot):
    return [p["ticker"] for p in depot.get("offen", [])]


# Die Zahlen, die die Kaufregeln festlegen. Ändert sich eine, ist das eine Regeländerung.
REGEL_KONSTANTEN = [
    "RISIKO_PROZENT", "MAX_POSITION_PROZENT", "MAX_POSITIONEN", "MAX_GESAMTRISIKO_PROZENT", "MAX_JE_BRANCHE",
    "STOP_TREND_ATR", "ZIEL_TREND_ATR", "STOP_GEGEN_ATR", "ZIEL_GEGEN_ATR", "LIMIT_ATR", "ZAHLEN_SPERRE_TAGE",
    "ZEITSTOPP_TAGE", "MARKTFILTER_TAGE", "LERNEN_FENSTER", "LERNEN_MIN_TRADES", "LERNEN_PAUSE_AB",
    "LERNEN_WIEDER_AB", "LERNEN_LANG_MIN", "R_GRENZE", "TAGEBUCH_AB_KERZE", "MIN_KERZEN", "SPREAD_PROZENT",
]


def lade_fingerabdruck():
    with open(FINGERABDRUCK, encoding="utf-8") as f:
        return json.load(f)


def speichere_fingerabdruck(inhalt):
    """Ein Trade je Zeile – so zeigt GitHub bei einer Regeländerung genau, welche Trades anders sind."""
    text = json.dumps(inhalt, ensure_ascii=False, indent=1)
    text = re.sub(r"\[\n\s*([^\[\]{}]*?)\n\s*\]",
                  lambda m: "[" + ", ".join(x.strip() for x in m.group(1).split(",\n")) + "]", text)
    with open(FINGERABDRUCK, "w", encoding="utf-8") as f:
        f.write(text + "\n")
