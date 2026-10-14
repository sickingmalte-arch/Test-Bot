"""Swing-Trading-Scanner mit Strategie-Tagebuch und virtuellem Depot.

Ablauf: Kurse (5 Jahre Tageskerzen) und Quartalszahlen-Termine von Yahoo laden, 16 Strategien je Ticker
prüfen, jede Strategie im Tagebuch gedanklich mithandeln lassen ("lernen"), daraus den Scanner für heute
und ein virtuelles Depot über die letzten Monate berechnen. Es werden keine echten Orders gesendet.
"""
import argparse
import datetime as dt
import html
import json
import logging
import math
import os
import re
import shutil
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait

import numpy as np
import pandas as pd
import yfinance as yf
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay, USMartinLutherKingJr,
                                    USMemorialDay, USPresidentsDay, USThanksgivingDay, nearest_workday,
                                    sunday_to_monday)

# ============================================================================
# EINSTELLUNGEN – hier anpassen oder beim Start mitgeben, z. B.:
#   python swing_scanner.py --ticker "AAPL, NFLX, SOFI" --konto 10000 --risiko 1
# ============================================================================
TICKER_LISTE = [
    "SE", "HIMS", "NOW", "INTU", "CRWV", "NBIS",
    "MELI", "IREN", "NFLX", "AAPL", "ASTS", "SOFI",
    # dazu sehr liquide Werte aus weiteren Branchen (Chips, Plattformen, Banken, Pharma, Energie, Handel)
    "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA",
    "AMD", "PLTR", "JPM", "LLY", "XOM", "COST",
]
KONTO = 10_000              # Kontogröße / virtuelles Startkapital in €
RISIKO_PROZENT = 1.0        # max. Verlust pro Trade in % des Kontos, wenn der Stop-Loss greift
MIT_SHORT = True            # auch auf fallende Kurse setzen (Short-Signale)
GEBUEHR = 1.0               # Ordergebühr in € je Kauf/Verkauf (z. B. Neobroker)
SPREAD_PROZENT = 0.1        # geschätzter Spread je Order in % (Kauf etwas teurer, Verkauf etwas billiger)
BRUCHSTUECKE = False        # True = auch Bruchteile von Aktien (z. B. 0,35 Stück)
RUECKBLICK_MONATE = 6       # so viele Monate spielt der Bot das virtuelle Depot rückwirkend durch

# ============================================================================
# FESTE REGELN – vorab festgelegt. Bitte NICHT so lange verstellen, bis der Rückblick gut aussieht:
# dann passt man die Regeln nur an den Zufall der Vergangenheit an.
# ============================================================================
MAX_POSITION_PROZENT = 25        # eine einzelne Position höchstens so viel % des Kontos
MAX_POSITIONEN = 5               # höchstens so viele Positionen gleichzeitig
MAX_SHORTS = 2                   # davon höchstens so viele Shorts
MAX_GESAMTRISIKO_PROZENT = 5     # alle offenen Positionen zusammen höchstens so viel % Risiko bis zum Stop
MIN_EINSATZ = 25                 # kleinere Trades lohnen wegen der Gebühr nicht (in €)
ZEITSTOPP_TAGE = 20              # spätestens nach so vielen Handelstagen (inkl. Einstiegstag) aussteigen
ZAHLEN_SPERRE_TAGE = 3           # kein Einstieg, wenn Quartalszahlen in den nächsten 3 Handelstagen wirken
LIMIT_ATR = 0.5                  # Einstieg nur bis Schlusskurs ± 0,5 ATR (Limit-Order), höchstens bis Mitte Stop/Ziel
R_GRENZE = 3.0                   # ein einzelner Tagebuch-Trade zählt höchstens ±3 R
LERNEN_FENSTER = 60              # die letzten 60 gedachten Trades je Strategie zählen
LERNEN_MIN_TRADES = 20           # erst ab 20 Trades wird eine Strategie überhaupt pausiert
LERNEN_PAUSE_AB = -0.10          # Pause, wenn der Schnitt unter −0,1 R fällt
LERNEN_WIEDER_AB = 0.0           # wieder aktiv, sobald der Schnitt über 0 R steigt
TAGEBUCH_AB_KERZE = 100          # Tagebuch erst, wenn die Indikatoren eingeschwungen sind
MIN_KERZEN = 50                  # Mindestanzahl Tageskerzen für den Scanner
NEWS_TAGE = 3                    # Schlagzeilen der letzten 3 Handelstage
MAX_TRADES_ANZEIGE = 20          # so viele abgeschlossene Trades zeigt die Liste (alle per --csv)
YAHOO_ZEITBUDGET = 45            # Sekunden je Abruf-Phase (Termine bzw. Schlagzeilen)

FX_TICKER = "EURUSD=X"           # Wechselkurs bei Yahoo: Dollar je 1 Euro
MARKT_TICKER = "QQQ"             # Nasdaq-100 als Marktampel (nur Anzeige)
PAPIER_DATEI = "papier_depot.json"                                       # Papier-Depot außerhalb von Colab
PAPIER_DATEI_COLAB = "/content/drive/MyDrive/swing_scanner/papier_depot.json"  # in Colab: Google Drive
# Börsenendungen bei Yahoo, deren Kurse schon in Euro sind (z. B. SAP.DE, ASML.AS)
EURO_BOERSEN = {"DE", "F", "SG", "MU", "BE", "DU", "HM", "HA", "PA", "AS", "MI", "MC", "BR", "VI", "LS", "HE", "IR"}
NY = "America/New_York"
BERLIN = "Europe/Berlin"

# ----------------------------------------------------------------------------
# Strategien – Reihenfolge = Vorrang, wenn mehrere in dieselbe Richtung feuern
# (art "trend": Trendregel über die 50-Tage-Linie, art "gegen": Gegenbewegung, Trendregel über die 200-Tage-Linie)
# ----------------------------------------------------------------------------
STRATEGIEN = {
    "ausbruch_long":      {"name": "Ausbruch", "richtung": 1, "art": "trend",
                           "regel": "Schluss über dem 20-Tage-Hoch mit 1,5-fachem Volumen, über der 50-Tage-Linie. "
                                    "Stop −2 ATR, Ziel +4 ATR"},
    "abbruch_short":      {"name": "Abbruch", "richtung": -1, "art": "trend",
                           "regel": "Schluss unter dem 20-Tage-Tief mit 1,5-fachem Volumen, unter der 50-Tage-Linie. "
                                    "Stop +2 ATR, Ziel −4 ATR"},
    "rsi2_long":          {"name": "RSI-2-Rücksetzer", "richtung": 1, "art": "gegen",
                           "regel": "RSI(2) unter 10 über der 200-Tage-Linie (kurzer Rücksetzer im langen Aufwärtstrend). "
                                    "Stop −2 ATR, Ziel +2 ATR – braucht über 50 % Treffer"},
    "rsi2_short":         {"name": "RSI-2-Übertreibung", "richtung": -1, "art": "gegen",
                           "regel": "RSI(2) über 90 unter der 200-Tage-Linie (kurze Erholung im langen Abwärtstrend). "
                                    "Stop +2 ATR, Ziel −2 ATR – braucht über 50 % Treffer"},
    "gegenbewegung_long": {"name": "Gegenbewegung", "richtung": 1, "art": "gegen",
                           "regel": "RSI(14) unter 32 oder am unteren Bollinger-Band, über der 200-Tage-Linie, "
                                    "EMA 20 mindestens 1,2 ATR über dem Kurs. Stop −1,2 ATR, Ziel EMA 20"},
    "rueckfall_short":    {"name": "Rückfall", "richtung": -1, "art": "gegen",
                           "regel": "RSI(14) über 70 oder am oberen Bollinger-Band, unter der 200-Tage-Linie, "
                                    "EMA 20 mindestens 1,2 ATR unter dem Kurs. Stop +1,2 ATR, Ziel EMA 20"},
    "macd_long":          {"name": "MACD-Wende", "richtung": 1, "art": "trend",
                           "regel": "MACD kreuzt heute seine Signallinie nach oben, über der 50-Tage-Linie. "
                                    "Stop −1,5 ATR, Ziel +3 ATR"},
    "macd_short":         {"name": "MACD-Wende", "richtung": -1, "art": "trend",
                           "regel": "MACD kreuzt heute seine Signallinie nach unten, unter der 50-Tage-Linie. "
                                    "Stop +1,5 ATR, Ziel −3 ATR"},
    "ruecksetzer_long":   {"name": "Rücksetzer", "richtung": 1, "art": "trend",
                           "regel": "Kurs bis 0,5 ATR über der EMA 20, RSI(14) unter 60, über der 50-Tage-Linie. "
                                    "Stop −1,5 ATR, Ziel +3 ATR"},
    "erholung_short":     {"name": "Erholung", "richtung": -1, "art": "trend",
                           "regel": "Kurs bis 0,5 ATR unter der EMA 20, RSI(14) über 40, unter der 50-Tage-Linie. "
                                    "Stop +1,5 ATR, Ziel −3 ATR"},
    "squeeze_long":       {"name": "Squeeze-Ausbruch", "richtung": 1, "art": "trend",
                           "regel": "Bollinger-Bänder waren an einem der 5 Vortage so eng wie selten (unterste 15 % der "
                                    "letzten 120 Tage), heute erster Schluss über dem oberen Band, über der 50-Tage-Linie "
                                    "(Ausbruch nach ruhiger Phase). Stop −2 ATR, Ziel +4 ATR"},
    "squeeze_short":      {"name": "Squeeze-Abbruch", "richtung": -1, "art": "trend",
                           "regel": "Bollinger-Bänder waren an einem der 5 Vortage so eng wie selten (unterste 15 % der "
                                    "letzten 120 Tage), heute erster Schluss unter dem unteren Band, unter der "
                                    "50-Tage-Linie. Stop +2 ATR, Ziel −4 ATR"},
    "ema_kreuz_long":     {"name": "EMA-Kreuz", "richtung": 1, "art": "trend",
                           "regel": "EMA 9 kreuzt heute die EMA 21 nach oben (neuer Aufwärtstrend), über der "
                                    "50-Tage-Linie. Stop −2 ATR, Ziel +4 ATR"},
    "ema_kreuz_short":    {"name": "EMA-Kreuz", "richtung": -1, "art": "trend",
                           "regel": "EMA 9 kreuzt heute die EMA 21 nach unten (neuer Abwärtstrend), unter der "
                                    "50-Tage-Linie. Stop +2 ATR, Ziel −4 ATR"},
    "atr_ausbruch_long":  {"name": "ATR-Ausbruch", "richtung": 1, "art": "trend",
                           "regel": "Schluss erstmals mehr als 2 ATR über der EMA 20 (Keltner-Kanal – Bewegung größer "
                                    "als das normale Schwanken), über der 50-Tage-Linie. Stop −2 ATR, Ziel +4 ATR"},
    "atr_abbruch_short":  {"name": "ATR-Abbruch", "richtung": -1, "art": "trend",
                           "regel": "Schluss erstmals mehr als 2 ATR unter der EMA 20 (Keltner-Kanal), unter der "
                                    "50-Tage-Linie. Stop +2 ATR, Ziel −4 ATR"},
}
VORRANG = {k: i for i, k in enumerate(STRATEGIEN)}

def strategie_name(key):
    s = STRATEGIEN[key]
    return f"{s['name']}\u00a0{'↑' if s['richtung'] > 0 else '↓'}"  # geschütztes Leerzeichen: Pfeil bleibt am Namen

# Signale (Reihenfolge = Sortierung in der Tabelle)
KAUFEN = "🟢 KAUFEN"
SHORT = "🔴 SHORT"
WARTEN = "⏸ WARTEN"
SICHERN = "⚠️ GEWINNE SICHERN"
BEOBACHTEN = "BEOBACHTEN"
FEHLER = "❌ FEHLER"
PRIORITAET = {KAUFEN: 1, SHORT: 1, WARTEN: 2, SICHERN: 3, BEOBACHTEN: 4, FEHLER: 5}

# Zeilenfarben: (Hintergrund, Schrift) für die Notebook-Tabelle, ANSI-Codes fürs Terminal
FARBEN = {
    KAUFEN: ("#1b5e20", "#ffffff"),
    SHORT: ("#b71c1c", "#ffffff"),
    WARTEN: ("#fff3cd", "#1b1b1b"),
    SICHERN: ("#ffe0b2", "#1b1b1b"),
    FEHLER: ("#eeeeee", "#555555"),
}
ANSI = {KAUFEN: "\033[1;97;42m", SHORT: "\033[1;97;41m", WARTEN: "\033[33m", SICHERN: "\033[33m", FEHLER: "\033[2m"}


# ----------------------------------------------------------------------------
# Zahlen und Daten deutsch formatieren
# ----------------------------------------------------------------------------
def de(wert, nachkomma=2, vorzeichen=False):
    """1234.5 -> '1.234,50' (deutsche Schreibweise); NaN -> '–'"""
    if wert is None or pd.isna(wert):
        return "–"
    text = f"{wert:{'+' if vorzeichen else ''},.{nachkomma}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")

def prozent(wert):
    """1.5 -> '1,5' (deutsche Schreibweise, ohne überflüssige Nullen)"""
    return f"{wert:g}".replace(".", ",")

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def datum(tag):
    """Timestamp -> 'Do 16.10.'"""
    return f"{WOCHENTAGE[tag.weekday()]} {tag:%d.%m.}"

def tabellen_formate(einst):
    return {
        "Kurs": lambda v: de(v, 2), "Limit": lambda v: de(v, 2), "Stop": lambda v: de(v, 2),
        "Ziel": lambda v: de(v, 2), "CRV": lambda v: de(v, 1),
        "Stück": lambda v: de(v, 2 if einst.bruchstuecke else 0), "Einsatz": lambda v: de(v, 0),
        "Risiko": lambda v: de(v, 0),
    }

SPALTEN = ["Ticker", "Signal", "Strategie", "Kurs", "Limit", "Stop", "Ziel", "CRV", "Stück", "Einsatz", "Risiko",
           "Zahlen", "News"]


# ----------------------------------------------------------------------------
# Einstellungen
# ----------------------------------------------------------------------------
def zahl(text):
    """Erlaubt auch ein deutsches Komma, z. B. --risiko 1,5"""
    try:
        return float(str(text).replace(",", "."))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' ist keine Zahl")

def betrag(text):
    """Kontogröße; erlaubt auch Tausenderpunkte, z. B. --konto 10.000"""
    s = str(text).strip()
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)
    return zahl(s)

def ticker_aus_text(text):
    """'aapl, NFLX nflx' -> ['AAPL', 'NFLX'] (groß geschrieben, ohne Duplikate, Reihenfolge bleibt)"""
    liste = [t.upper() for t in re.split(r"[,;\s]+", text or "") if t]
    return list(dict.fromkeys(liste))

def lies_einstellungen():
    p = argparse.ArgumentParser(description="Swing-Trading-Scanner für deine Watchlist (Beträge in €)")
    p.add_argument("--ticker", help='z. B. "AAPL, NFLX, SOFI" (Standard: TICKER_LISTE im Skript)')
    p.add_argument("--konto", type=betrag, default=KONTO, help="Kontogröße / Startkapital in € (z. B. 10000)")
    p.add_argument("--risiko", type=zahl, default=RISIKO_PROZENT, help="Risiko pro Trade in %% des Kontos")
    p.add_argument("--ohne-short", action="store_true", help="keine Short-Signale, nur auf steigende Kurse setzen")
    p.add_argument("--ohne-lernen", action="store_true", help="schlecht laufende Strategien nicht pausieren")
    p.add_argument("--ohne-news", action="store_true", help="keine Schlagzeilen laden (Quartalszahlen-Regel bleibt)")
    p.add_argument("--ohne-zahlen", action="store_true",
                   help="keine Quartalszahlen-Termine laden – die Zahlen-Regel ist dann AUS")
    p.add_argument("--gebuehr", type=zahl, default=GEBUEHR, help="Ordergebühr in € je Kauf/Verkauf")
    p.add_argument("--bruchstuecke", action="store_true", help="auch Bruchteile von Aktien handeln")
    p.add_argument("--rueckblick", type=int, default=RUECKBLICK_MONATE,
                   help="Monate, die der Bot das virtuelle Depot rückwirkend durchspielt (0 = aus, max. 18)")
    p.add_argument("--nur-schluss", action="store_true",
                   help="laufende Tageskerze auch im Scanner ignorieren, nur abgeschlossene Tage bewerten")
    p.add_argument("--papier", nargs="?", const="auto", metavar="DATEI",
                   help="Papier-Depot: der Bot handelt ab heute vorwärts mit virtuellem Geld und speichert den Stand "
                        "(in Colab in Google Drive, sonst in papier_depot.json)")
    p.add_argument("--papier-neu", action="store_true",
                   help="Papier-Depot neu anlegen (der bisherige Stand wird als Kopie aufbewahrt)")
    p.add_argument("--csv", metavar="DATEI", help="Ergebnis zusätzlich als CSV speichern (für Excel)")
    p.add_argument("--debug", action="store_true", help="Original-Meldungen von yfinance anzeigen")
    einst, unbekannt = p.parse_known_args()
    if unbekannt:
        print(f"Hinweis: unbekannte Angaben ignoriert: {' '.join(unbekannt)}")
    if not (0 < einst.konto < math.inf and 0 < einst.risiko < math.inf):
        p.error("--konto und --risiko müssen Zahlen größer als 0 sein")
    if not 0 <= einst.gebuehr < math.inf:
        p.error("--gebuehr muss 0 oder größer sein")
    if not 0 <= einst.rueckblick <= 18:
        p.error("--rueckblick muss zwischen 0 und 18 Monaten liegen")
    einst.mit_short = MIT_SHORT and not einst.ohne_short
    einst.lernen = not einst.ohne_lernen
    einst.bruchstuecke = BRUCHSTUECKE or einst.bruchstuecke
    einst.ticker_liste = ticker_aus_text(einst.ticker if einst.ticker else ",".join(TICKER_LISTE))
    if einst.papier_neu and not einst.papier:
        einst.papier = "auto"
    return einst


# ----------------------------------------------------------------------------
# Yahoo: Meldungen abfangen, Kurse laden
# ----------------------------------------------------------------------------
class YahooMeldungen(logging.Handler):
    """Sammelt die Meldungen von yfinance je Ticker, statt sie rot über die Tabelle zu schreiben."""
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.gruende = {}

    def emit(self, record):
        # yfinance meldet z. B. "['SE', 'HIMS']: ConnectionError('... 403 ...')",
        # "Failed to get ticker 'SE' reason: ..." oder "SOFI: No earnings dates found ..."
        text = record.getMessage()
        treffer = (re.match(r"\s*\[(.*?)\]:\s*(.*)", text, re.S)
                   or re.match(r"\s*Failed to get ticker ('[^']+') reason:\s*(.*)", text, re.S))
        if treffer:
            for ticker in re.findall(r"'([^']+)'", treffer.group(1)):
                self.gruende[ticker] = self.gruende.get(ticker, "") + " " + treffer.group(2)
            return
        treffer = re.match(r"\s*([A-Z0-9][A-Z0-9.\-=^]*):\s+(.*)", text, re.S)
        if treffer:
            self.gruende[treffer.group(1)] = self.gruende.get(treffer.group(1), "") + " " + treffer.group(2)

class YahooRuhig:
    """Kontextmanager: Während alle Yahoo-Abfragen laufen, landen die yfinance-Meldungen im Sammler."""
    def __init__(self, debug=False):
        self.sammler = YahooMeldungen()
        self.handler = [self.sammler] + ([logging.StreamHandler()] if debug else [])
        self.log = logging.getLogger("yfinance")

    def __enter__(self):
        self.alte_weitergabe = self.log.propagate
        if not any(isinstance(h, logging.NullHandler) for h in self.log.handlers):
            self.log.addHandler(logging.NullHandler())  # späte Meldungen aus Threads nicht auf stderr
        for h in self.handler:
            self.log.addHandler(h)
        self.log.propagate = False
        return self.sammler

    def __exit__(self, *fehler):
        for h in self.handler:
            self.log.removeHandler(h)
        self.log.propagate = self.alte_weitergabe

def frischer_yahoo_cache():
    """yfinance merkt sich Antworten (auch Fehlerseiten) im laufenden Colab-Kernel – bei jedem Lauf leeren."""
    try:
        from yfinance.data import YfData
        YfData.cache_get.cache_clear()
    except Exception:
        pass

YAHOO_LIMIT = "Yahoo-Limit erreicht – in 1–2 Minuten erneut starten"
KEINE_VERBINDUNG = "keine Verbindung zu Yahoo"
TICKER_UNBEKANNT = "keine Kursdaten (Ticker richtig geschrieben?)"

def verstaendlicher_grund(text):
    t = (text or "").lower()
    if "too many requests" in t or "rate limit" in t:
        return YAHOO_LIMIT
    if any(k in t for k in ("connection", "timed out", "timeout", "resolve", "curl", "proxy")):
        return KEINE_VERBINDUNG
    if "delisted" in t or "no price data" in t or "no data found" in t:
        return TICKER_UNBEKANNT
    return "keine Kursdaten"

def tabelle_fuer(roh, ticker):
    """Holt die Kurstabelle eines Tickers aus dem Sammel-Download (None, wenn leer)."""
    if roh is None or roh.empty:
        return None
    if isinstance(roh.columns, pd.MultiIndex):
        if ticker not in roh.columns.get_level_values(0):
            return None
        df = roh[ticker]
    else:  # ältere yfinance-Versionen: einzelner Ticker ohne Ticker-Ebene
        df = roh
    df = df.dropna(subset=["High", "Low", "Close"])
    return df if not df.empty else None

def lade_kurse(ticker_liste, sammler):
    """Lädt 5 Jahre Tageskerzen aller Ticker in einem Rutsch; leere Ticker werden einmal nachgeladen."""
    daten, fehlend = {}, list(ticker_liste)
    for versuch in range(2):
        if not fehlend:
            break
        if versuch:
            time.sleep(3)
        roh = yf.download(fehlend, period="5y", interval="1d", auto_adjust=True,
                          group_by="ticker", progress=False, threads=True)
        rest = []
        for ticker in fehlend:
            df = tabelle_fuer(roh, ticker)
            if df is None:
                rest.append(ticker)
            else:
                daten[ticker] = df
        fehlend = rest
    gruende = {t: verstaendlicher_grund(sammler.gruende.get(t)) for t in fehlend}
    # Bei Verbindungsproblemen meldet yfinance andere Ticker oft fälschlich als "delisted"
    if any(g in (YAHOO_LIMIT, KEINE_VERBINDUNG) for g in gruende.values()):
        gruende = {t: "keine Kursdaten (Verbindungsproblem oder falscher Ticker)" if g == TICKER_UNBEKANNT else g
                   for t, g in gruende.items()}
    return daten, gruende

def waehrung_von(ticker):
    """'USD' für US-Werte (ohne Börsenendung) und z. B. BTC-USD, 'EUR' für Euro-Börsen und BTC-EUR, sonst None."""
    if re.fullmatch(r".+-[A-Z]{3}", ticker):  # Krypto/Devisen wie BTC-USD
        return {"USD": "USD", "EUR": "EUR"}.get(ticker[-3:])
    if "." in ticker:
        return "EUR" if ticker.rsplit(".", 1)[1] in EURO_BOERSEN else None
    return "USD"

def hat_zahlen(ticker):
    """Krypto, Devisen und Indizes haben keine Quartalszahlen – gar nicht erst fragen."""
    return not (ticker.startswith("^") or "=" in ticker or re.fullmatch(r".+-[A-Z]{3}", ticker))

class NYSEFeiertage(AbstractHolidayCalendar):
    """Handelsfreie Tage der New Yorker Börse (für künftige Tage; die Vergangenheit kommt aus den Kursdaten)."""
    rules = [
        Holiday("Neujahr", month=1, day=1, observance=sunday_to_monday),
        USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
        Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
        Holiday("Unabhängigkeitstag", month=7, day=4, observance=nearest_workday),
        USLaborDay, USThanksgivingDay,
        Holiday("Weihnachten", month=12, day=25, observance=nearest_workday),
    ]

NYSE_TAG = pd.offsets.CustomBusinessDay(calendar=NYSEFeiertage())

def ist_krypto(ticker):
    return bool(re.fullmatch(r".+-[A-Z]{3}", ticker))

def handelstag(ticker):
    """Schritt zum nächsten Handelstag: US-Werte mit NYSE-Feiertagen, Euro-Börsen Mo–Fr, Krypto jeden Tag."""
    if ist_krypto(ticker):
        return pd.offsets.Day(1)
    return NYSE_TAG if waehrung_von(ticker) == "USD" else pd.offsets.BDay(1)

def kurs_umrechner(fx, index):
    """Dollar je Euro für jeden Tag des Index (fehlende Tage mit dem letzten bekannten Kurs)."""
    if fx is None:
        return pd.Series(1.0, index=index)
    return fx.reindex(fx.index.union(index)).ffill().reindex(index).bfill()

REGIONALBOERSEN = {"F", "SG", "MU", "BE", "DU", "HM", "HA"}  # deutsche Regionalbörsen handeln bis 22:00 Uhr

def kerze_noch_offen(df, ticker=""):
    """True, wenn die letzte Tageskerze noch läuft: bei Aktien von heute und die Börse noch nicht geschlossen
    (US 16:00 New York, Euro-Börsen 17:30 Uhr, deutsche Regionalbörsen 22:00 Uhr – jeweils mit Puffer, weil Yahoo
    Euro-Kurse etwa 15 Minuten verzögert liefert),
    bei Krypto (Tageskerze = UTC-Tag, Handel rund um die Uhr) die Kerze des heutigen UTC-Tags."""
    try:
        if re.fullmatch(r".+-[A-Z]{3}", ticker):
            return df.index[-1].date() >= pd.Timestamp.now(tz="UTC").date()
        if waehrung_von(ticker) == "EUR":
            jetzt = pd.Timestamp.now(tz=BERLIN)
            schluss = dt.time(22, 30) if ticker.rsplit(".", 1)[1] in REGIONALBOERSEN else dt.time(18, 15)
        else:
            jetzt, schluss = pd.Timestamp.now(tz=NY), dt.time(16, 15)
    except Exception:
        return False
    return df.index[-1].date() == jetzt.date() and jetzt.time() < schluss


# ----------------------------------------------------------------------------
# Yahoo: Quartalszahlen-Termine und Schlagzeilen (parallel, mit Zeitbudget und Bremse bei Yahoo-Limit)
# ----------------------------------------------------------------------------
def hole_zusatzdaten(termin_ticker, news_ticker, sammler, budget=YAHOO_ZEITBUDGET):
    """Phase 1: Termine (Teil der Regeln), Phase 2: Schlagzeilen (nur Anzeige).
    Gibt {ticker: {"zahlen", "zahlen_info", "news", "news_info"}} zurück."""
    bremse = threading.Event()  # erster 429 von Yahoo: alle weiteren Abfragen sofort auslassen
    alle = list(dict.fromkeys(list(termin_ticker) + list(news_ticker)))
    erg = {t: {"zahlen": None, "zahlen_info": "nicht abgefragt", "news": None, "news_info": "nicht abgefragt"}
           for t in alle}

    def termine(t):
        e = erg[t]
        if bremse.is_set():
            e["zahlen_info"] = YAHOO_LIMIT
            return
        try:
            df = yf.Ticker(t).get_earnings_dates(limit=50)
            if df is None or len(df) == 0:
                e["zahlen_info"] = "keine Termine gefunden (bei ETFs normal, sonst Yahoo gerade nicht erreichbar)"
            else:
                e["zahlen"], e["zahlen_info"] = df, "ok"
        except Exception as fehler:  # Yahoo-Limit, Formatwechsel, Zeitzone, Verbindung ...
            if type(fehler).__name__ == "YFRateLimitError":
                bremse.set()
                e["zahlen_info"] = YAHOO_LIMIT
            else:
                e["zahlen_info"] = f"Termine nicht lesbar ({type(fehler).__name__})"

    def schlagzeilen_holen(t):
        e = erg[t]
        if bremse.is_set():
            e["news_info"] = YAHOO_LIMIT
            return
        try:
            e["news"], e["news_info"] = yf.Ticker(t).get_news(count=10), "ok"
        except Exception as fehler:
            if type(fehler).__name__ == "YFRateLimitError":
                bremse.set()
                e["news_info"] = YAHOO_LIMIT
            else:
                e["news_info"] = f"nicht abrufbar ({type(fehler).__name__})"

    start = time.perf_counter()
    pool = ThreadPoolExecutor(max_workers=4)
    offen = set()
    if termin_ticker:
        _, offen = wait([pool.submit(termine, t) for t in termin_ticker], timeout=budget * 2 / 3)
    if news_ticker and not offen:
        rest = max(budget - (time.perf_counter() - start), 1)
        _, offen = wait([pool.submit(schlagzeilen_holen, t) for t in news_ticker], timeout=rest)
    pool.shutdown(wait=False, cancel_futures=True)
    for t, e in erg.items():
        meldung = sammler.gruende.get(t, "")
        # yfinance liefert bei kaputter News-Antwort still [] und meldet das nur ins Log
        if e["news_info"] == "ok" and not e["news"] and "Failed to retrieve the news" in meldung:
            e["news"], e["news_info"] = None, "nicht abrufbar (Yahoo-Antwort unlesbar)"
        for art in ("zahlen_info", "news_info"):
            if e[art] == "nicht abgefragt" and offen:
                e[art] = "Zeitüberschreitung"
    return {t: dict(e) for t, e in erg.items()}  # Momentaufnahme: späte Threads ändern nichts mehr

def zahlen_termine(df):
    """Yahoo-Termine -> sortierte Zeitpunkte in New Yorker Zeit (ohne NaT, auch für ältere yfinance ohne Zeitzone)."""
    idx = pd.DatetimeIndex(df.index)
    idx = idx[idx.notna()]
    if idx.tz is None:
        idx = idx.tz_localize(NY)
    return idx.tz_convert(NY).sort_values()

def reaktionstag(termin):
    """Kalendertag, an dem die Zahlen auf den Kurs wirken: Bericht ab 16:00 New York -> am nächsten Tag,
    sonst am selben Tag (00:00 = Uhrzeit unbekannt -> vorsichtig derselbe Tag). Wochenende/Feiertag rutschen
    beim Einordnen in die Handelstage automatisch auf den nächsten Handelstag."""
    tag = pd.Timestamp(termin.date())
    return tag + pd.Timedelta(days=1) if termin.hour >= 16 else tag

def uhrzeit_text(termin):
    if termin.hour >= 16:
        return "nach Börsenschluss"
    if termin.hour == 0:
        return "Uhrzeit unbekannt"
    if termin.hour < 10:
        return "vor Börsenbeginn"
    return "während des Handels"

def zahlen_regeln(termine, kurs_index, schritt=pd.offsets.BDay(1)):
    """Für jeden Kurstag i: morgen[i] = Zahlen wirken am nächsten Handelstag (heute zum Schluss raus),
    gesperrt[i] = Zahlen wirken in den nächsten ZAHLEN_SPERRE_TAGE Handelstagen (kein Einstieg),
    gerade[i] = Zahlen haben heute oder gestern gewirkt (keine Gegenbewegungs-Trades)."""
    n = len(kurs_index)
    zukunft = pd.date_range(kurs_index[-1] + schritt, periods=ZAHLEN_SPERRE_TAGE + 30, freq=schritt)
    lang = kurs_index.append(zukunft)              # Handelstage + künftige Handelstage laut Börsenkalender
    reak = np.zeros(len(lang) + ZAHLEN_SPERRE_TAGE + 2, bool)
    for termin in termine:
        pos = lang.searchsorted(reaktionstag(termin))
        if pos < len(lang):
            reak[pos] = True
    morgen = reak[1:n + 1].copy()
    gesperrt = np.zeros(n, bool)
    for k in range(1, ZAHLEN_SPERRE_TAGE + 1):
        gesperrt |= reak[k:n + k]
    gerade = reak[:n] | np.r_[False, reak[:n - 1]]
    return morgen, gesperrt, gerade, lang, reak


# ----------------------------------------------------------------------------
# Schlagzeilen: erkannte Ereignisse statt Stimmungs-Punkte (nur Anzeige und Warnung)
# ----------------------------------------------------------------------------
FIRMENNAMEN = {
    "SE": r"sea (ltd|limited)|shopee|garena|monee", "HIMS": r"hims", "NOW": r"servicenow",
    "INTU": r"intuit|turbotax|quickbooks", "CRWV": r"coreweave", "NBIS": r"nebius", "MELI": r"mercado ?libre",
    "IREN": r"iren|iris energy", "NFLX": r"netflix", "AAPL": r"apple|iphone", "ASTS": r"ast spacemobile",
    "SOFI": r"sofi", "NVDA": r"nvidia", "MSFT": r"microsoft", "AMZN": r"amazon|aws", "META": r"meta|facebook|instagram",
    "GOOGL": r"alphabet|google|youtube", "TSLA": r"tesla", "AMD": r"amd|advanced micro", "PLTR": r"palantir",
    "JPM": r"jpmorgan(?: ?chase)?|jp morgan", "LLY": r"eli lilly|lilly", "XOM": r"exxon(?: ?mobil)?", "COST": r"costco",
}
NEWS_IGNORIEREN = re.compile(
    r"\?\s*$|reasons? to|time to buy|should you|is it too late|could |strong buy|buy the dip|stock market today|"
    r"dow jones futures|^prediction:|"
    r"law firm|class action|investor alert|securities fraud|secure counsel|\brosen\b|pomerantz|levi & korsinsky|"
    r"bragar|schall law|gross law|faruqi|bronstein", re.I)
NEWS_EREIGNISSE = [  # (Muster, Richtung: +1 gut / −1 schlecht / 0 Sonderfall, deutsches Etikett)
    (r"\b(beats?|tops?|surpass\w*)\b.{0,40}\b(estimates?|expectations|forecasts?)\b", 1, "Zahlen besser als erwartet"),
    (r"\bmiss(es|ed)?\b.{0,40}\b(estimates?|expectations|forecasts?)\b", -1, "Zahlen schlechter als erwartet"),
    (r"\b(raises?|raised|lifts?|boosts?|hikes?)\b.{0,40}\b(guidance|outlook|forecast)\b", 1, "Prognose angehoben"),
    (r"(?<!\brate )(?<!\brate-)\b(cuts?|lowers?|lowered|slash\w*|trims?)\b(?!\s+(interest\s+)?rates?\b)"
     r"(?:[^,;]|,(?=\s*(?:annual\s+|full-year\s+)?(?:sales|revenues?|profits?|margins?|earnings|eps|ebitda)\b)){0,40}"
     r"\b(guidance|outlook|forecast)\b"
     r"|\bweak (guidance|outlook)\b",
     -1, "Prognose gesenkt"),
    (r"\bupgraded\b.{0,25}\b(to|at|by)\b|\bupgrades?\b.{0,40}\b(buy|outperform|overweight)\b|\banalysts?\s+upgrades?\b",
     1, "Analyst stuft hoch"),
    (r"\bdowngrade[ds]?\b(?!\s+(the\s+)?(us|u\.s\.|united states|sovereign)\b)", -1, "Analyst stuft runter"),
    (r"\b(stock|share|equity|convertible|notes?|secondary|public)\b.{0,25}\boffering\b|at-the-market|(?<!non-)\bdilut\w*",
     -1, "Kapitalerhöhung/Verwässerung"),
    (r"\b(fda|sec|doj|ftc|antitrust|eu)\b.{0,40}\b(warns?|probe|investigat\w*|sues?|charges?)\b", -1,
     "Behörde ermittelt/warnt"),
    (r"\bshort[- ]sellers?\b|\bshort report\b", -1, "Leerverkäufer-Bericht"),
    (r"\b(ceo|cfo|insider|director|founder)\b.{0,30}\bsells?\b(?=\s+\$|.{0,30}\b(shares|stock|stake)\b)", -1,
     "Insider verkauft"),
    (r"\b(ceo|cfo)\b.{0,30}\b(resigns?|steps? down|departs?|ousted)\b", -1, "Chefwechsel"),
    (r"going concern|bankruptcy|chapter 11|restate\w*|delist\w*", -1, "Warnung (Bilanz/Insolvenz/Delisting)"),
    (r"\block-?up\b", -1, "Lock-up-Ende"),
    (r"\b(buybacks?|buy[- ]back|repurchase)\b", 1, "Aktienrückkauf"),
    (r"\b(to join|added to|joins?)\b.{0,20}\b(s&p|nasdaq-100|index)\b", 1, "Indexaufnahme"),
    (r"\bstock split\b", 1, "Aktiensplit"),
    (r"\b(signs?|wins?|secures?|lands?)\b.{0,30}\b(deal|contract|agreement)\b", 1, "Auftrag/Vertrag"),
    (r"\b(to acquire|to be acquired|acquisition of|merger|takeover|buyout)\b"
     r"|\b(agrees?|deal|offer|bid|talks)\s+to\s+buy\s+(?!back\b)"
     r"|\bto buy\s+(?!back\b)(?-i:[A-Z])\S*(\s+(?!(chips?|gpus?|servers?|spectrum|shares|stakes?|miners?|rights|assets)\b)\S+)?"
     r"\s+for \$\d"
     r"|\bto buy\s+(?!back\b)(\S+\s+){1,3}?(firm|company|startup|maker|rival|business|unit|developer|operator|provider)\b",
     0, "Übernahme/Fusion"),
    (r"\btrading halt(ed)?\b|\bhalts? trading\b|\b(shares|stock|trading)\b.{0,20}(?<!streak )(?<!rally )\bhalted\b", 0, "Handelsaussetzung"),
]
VERNEINUNG = re.compile(r"\b(not|no|without|denies|despite)\b", re.I)

def lies_schlagzeilen(liste, ab_zeit):
    """Neue (seit Ende 2024) und alte yfinance-News-Struktur lesen, nur Meldungen ab 'ab_zeit'."""
    aus = []
    for a in liste or []:
        if not isinstance(a, dict):
            continue
        c = a["content"] if isinstance(a.get("content"), dict) else a
        titel = (c.get("title") or "").strip()
        zeit = pd.to_datetime(c.get("pubDate") or c.get("displayTime"), utc=True, errors="coerce")
        if pd.isna(zeit) and a.get("providerPublishTime"):
            zeit = pd.to_datetime(a["providerPublishTime"], unit="s", utc=True, errors="coerce")
        quelle = (c.get("provider") or {}).get("displayName") or a.get("publisher") or ""
        if titel and not pd.isna(zeit) and zeit >= ab_zeit:
            aus.append({"titel": titel, "zeit": zeit.tz_convert(BERLIN), "quelle": quelle,
                        "video": str(c.get("contentType", "")).upper() == "VIDEO"})
    return aus

def ereignisse(titel, ticker):
    """Erkannte Ereignisse einer Schlagzeile als Liste (Richtung, Etikett)."""
    name = FIRMENNAMEN.get(ticker)
    nennt_firma = re.search(rf"\b{re.escape(ticker)}\b", titel) or (name and re.search(rf"\b({name})\b", titel, re.I))
    if NEWS_IGNORIEREN.search(titel) or (name and not nennt_firma):
        return []
    gefunden = []
    for muster, richtung, etikett in NEWS_EREIGNISSE:
        treffer = re.search(muster, titel, re.I)
        if treffer and not VERNEINUNG.search(titel[max(0, treffer.start() - 25):treffer.start()]):
            gefunden.append((richtung, etikett))
    return gefunden

def werte_news(zusatz, kurstag, scanner_zeilen):
    """Für Ticker mit Signal: Schlagzeilen der letzten NEWS_TAGE Handelstage, erkannte Ereignisse, Warnungen."""
    ab_zeit = (kurstag - pd.offsets.BDay(NEWS_TAGE - 1)).tz_localize(NY).tz_convert("UTC")
    lesbar = {t: lies_schlagzeilen(e["news"], ab_zeit) for t, e in zusatz.items() if e.get("news")}
    # Dieselbe Meldung bei mehreren Tickern = allgemeine Marktnachricht -> anzeigen, aber nicht werten
    anzahl = {}
    for liste in lesbar.values():
        for s in {s["titel"] for s in liste}:
            anzahl[s] = anzahl.get(s, 0) + 1
    ergebnis = {}
    for z in scanner_zeilen:
        t = z["Ticker"]
        e = zusatz.get(t)
        if e is None or e["news_info"] == "nicht abgefragt":
            continue
        if e["news"] is None:
            ergebnis[t] = {"spalte": "?", "zeilen": [], "info": e["news_info"]}
            continue
        richtung = 1 if z["Signal"] == KAUFEN else -1 if z["Signal"] == SHORT else 0
        zeilen, etiketten, warnende, warnung = [], [], [], False
        for s in lesbar.get(t, []):
            ev = [] if s["video"] or anzahl.get(s["titel"], 0) > 1 else ereignisse(s["titel"], t)
            warnt = False
            for r, etikett in ev:
                gegen = r == 0 or (richtung and r == -richtung)
                warnt = warnt or gegen
                if etikett not in etiketten:
                    etiketten.insert(len(warnende) if gegen else len(etiketten), etikett)
                    if gegen:
                        warnende.append(etikett)
            warnung = warnung or warnt
            zeilen.append({**s, "ereignisse": [e2 for _, e2 in ev], "warnt": warnt})
        spalte = ("⚠️ " if warnung else "📰 ") + ", ".join(etiketten) if etiketten else ""
        zeilen.sort(key=lambda z: (not z["warnt"], not z["ereignisse"]))  # Warnungen, dann Ereignisse zuerst
        ergebnis[t] = {"spalte": spalte, "zeilen": zeilen[:2], "warnung": warnung, "info": "ok"}
    return ergebnis


# ----------------------------------------------------------------------------
# Indikatoren und Strategien (alles vektorisiert, jeder Wert eines Tages nur aus Kursen bis zu diesem Tag)
# ----------------------------------------------------------------------------
def calculate_indicators(df):
    """Berechnet alle Indikatoren für die Strategien."""
    c = df['Close']
    # 1. RSI (Relative Strength Index) mit Wilder-Glättung wie bei TradingView/Brokern
    delta = c.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    df['RSI'] = 100 - 100 / (1 + gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
                             / loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean())
    # 2. RSI über 2 Tage (sehr kurzfristig überkauft/überverkauft)
    df['RSI_2'] = 100 - 100 / (1 + gain.ewm(alpha=1/2, adjust=False, min_periods=2).mean()
                               / loss.ewm(alpha=1/2, adjust=False, min_periods=2).mean())
    # 3. EMA 20 und Trendlinien (gleitende Durchschnitte über 50 und 200 Tage)
    df['EMA_20'] = c.ewm(span=20, adjust=False).mean()
    df['SMA_50'] = c.rolling(50).mean()
    df['SMA_200'] = c.rolling(200).mean()
    # 4. Bollinger Bänder (20 Perioden, 2 Standardabweichungen)
    sma20 = c.rolling(window=20).mean()
    std20 = c.rolling(window=20).std()
    df['Upper_Band'] = sma20 + 2 * std20
    df['Lower_Band'] = sma20 - 2 * std20
    # 5. ATR (Average True Range, Wilder-Glättung) für Stop, Ziel und Limit
    ranges = pd.concat([df['High'] - df['Low'], (df['High'] - c.shift()).abs(), (df['Low'] - c.shift()).abs()], axis=1)
    df['ATR'] = ranges.max(axis=1).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    # 6. MACD (12/26) mit Signallinie (9)
    df['MACD'] = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    # 7. Hoch, Tief und Ø-Volumen der 20 VORTAGE (heute zählt nicht mit)
    df['Hoch_20'] = df['High'].shift(1).rolling(20).max()
    df['Tief_20'] = df['Low'].shift(1).rolling(20).min()
    volumen = df['Volume'] if 'Volume' in df else pd.Series(np.nan, index=df.index)
    df['Volumen_20'] = volumen.shift(1).rolling(20).mean()
    # 8. EMA 9 und EMA 21 (schnelle Trendlinien für den EMA-Kreuz)
    df['EMA_9'] = c.ewm(span=9, adjust=False).mean()
    df['EMA_21'] = c.ewm(span=21, adjust=False).mean()
    # 9. Bollinger-Bandbreite und „Squeeze“: Bänder so eng wie an höchstens 15 % der letzten 120 Tage
    df['BB_Breite'] = (df['Upper_Band'] - df['Lower_Band']) / sma20
    df['Squeeze'] = df['BB_Breite'] <= df['BB_Breite'].rolling(120).quantile(0.15)
    # 10. Keltner-Kanal: EMA 20 ± 2 ATR
    df['Keltner_Oben'] = df['EMA_20'] + 2 * df['ATR']
    df['Keltner_Unten'] = df['EMA_20'] - 2 * df['ATR']
    return df

def strategie_signale(df, mit_short):
    """Je Strategie: Bool-Array 'feuert' (Signal zum Schlusskurs) und Arrays Stop/Ziel in Kurswährung.
    Vergleiche mit NaN ergeben False – fehlt ein Indikator (z. B. SMA200 bei jungen Aktien), ist nur
    diese Strategie aus."""
    c, atr, ema, rsi = df['Close'], df['ATR'], df['EMA_20'], df['RSI']
    sma50, sma200 = df['SMA_50'], df['SMA_200']
    volumen = df['Volume'] if 'Volume' in df else pd.Series(np.nan, index=df.index)
    viel_volumen = (volumen > 0) & (df['Volumen_20'] > 0) & (volumen > 1.5 * df['Volumen_20'])
    macd, macd_sig = df['MACD'], df['MACD_Signal']
    kreuzt_hoch = (macd > macd_sig) & (macd.shift() <= macd_sig.shift())
    kreuzt_runter = (macd < macd_sig) & (macd.shift() >= macd_sig.shift())
    ueberverkauft = (rsi < 32) | (c <= df['Lower_Band'])
    ueberhitzt = (rsi > 70) | (c >= df['Upper_Band'])
    oben, unten = df['Upper_Band'], df['Lower_Band']
    squeeze_vorher = df['Squeeze'].astype(float).shift(1).rolling(5, min_periods=1).max() == 1  # an einem der 5 Vortage
    ema9, ema21 = df['EMA_9'], df['EMA_21']
    k_oben, k_unten = df['Keltner_Oben'], df['Keltner_Unten']
    regeln = {
        "ausbruch_long": ((c > df['Hoch_20']) & viel_volumen & (c > sma50), c - 2 * atr, c + 4 * atr),
        "abbruch_short": ((c < df['Tief_20']) & viel_volumen & (c < sma50), c + 2 * atr, c - 4 * atr),
        "rsi2_long": ((df['RSI_2'] < 10) & (c > sma200), c - 2 * atr, c + 2 * atr),
        "rsi2_short": ((df['RSI_2'] > 90) & (c < sma200), c + 2 * atr, c - 2 * atr),
        "gegenbewegung_long": (ueberverkauft & (c > sma200) & (ema - c >= 1.2 * atr), c - 1.2 * atr, ema),
        "rueckfall_short": (ueberhitzt & (c < sma200) & (c - ema >= 1.2 * atr), c + 1.2 * atr, ema),
        "macd_long": (kreuzt_hoch & (c > sma50), c - 1.5 * atr, c + 3 * atr),
        "macd_short": (kreuzt_runter & (c < sma50), c + 1.5 * atr, c - 3 * atr),
        "ruecksetzer_long": ((c > ema) & (c - ema <= 0.5 * atr) & (rsi < 60) & (c > sma50), c - 1.5 * atr, c + 3 * atr),
        "erholung_short": ((c < ema) & (ema - c <= 0.5 * atr) & (rsi > 40) & (c < sma50), c + 1.5 * atr, c - 3 * atr),
        "squeeze_long": (squeeze_vorher & (c > oben) & (c.shift() <= oben.shift()) & (c > sma50),
                         c - 2 * atr, c + 4 * atr),
        "squeeze_short": (squeeze_vorher & (c < unten) & (c.shift() >= unten.shift()) & (c < sma50),
                          c + 2 * atr, c - 4 * atr),
        "ema_kreuz_long": ((ema9 > ema21) & (ema9.shift() <= ema21.shift()) & (c > sma50), c - 2 * atr, c + 4 * atr),
        "ema_kreuz_short": ((ema9 < ema21) & (ema9.shift() >= ema21.shift()) & (c < sma50), c + 2 * atr, c - 4 * atr),
        "atr_ausbruch_long": ((c > k_oben) & (c.shift() <= k_oben.shift()) & (c > sma50), c - 2 * atr, c + 4 * atr),
        "atr_abbruch_short": ((c < k_unten) & (c.shift() >= k_unten.shift()) & (c < sma50), c + 2 * atr, c - 4 * atr),
    }
    genug = np.arange(len(df)) >= MIN_KERZEN - 1
    signale = {}
    for key, (bedingung, stop, ziel) in regeln.items():
        r = STRATEGIEN[key]["richtung"]
        if r < 0 and not mit_short:
            continue
        ok = (bedingung & atr.notna() & (stop > 0) & (ziel > 0) & (r * (c - stop) > 0) & (r * (ziel - c) > 0)
              ).to_numpy(dtype=bool) & genug
        signale[key] = (ok, stop.to_numpy(dtype=float), ziel.to_numpy(dtype=float))
    return signale, ueberhitzt.to_numpy(dtype=bool), ueberverkauft.to_numpy(dtype=bool)

def limit_kurs(r, kurs, atr, stop, ziel):
    """Höchster Kaufkurs (Long) bzw. tiefster Verkaufskurs (Short) für den Einstieg am nächsten Tag:
    Schluss ± 0,5 ATR, aber nie über die Mitte zwischen Stop und Ziel (dann bleibt das CRV mindestens 1)."""
    mitte = (stop + ziel) / 2
    return min(kurs + LIMIT_ATR * atr, mitte) if r > 0 else max(kurs - LIMIT_ATR * atr, mitte)

def bereite_vor(ticker, df, fx, zahlen_df, einst):
    """Alles, was Scanner, Tagebuch und Depot je Ticker brauchen, einmal als schnelle Listen/Arrays."""
    df = calculate_indicators(df.copy())
    signale, ueberhitzt, ueberverkauft = strategie_signale(df, einst.mit_short)
    n = len(df)
    offen = kerze_noch_offen(df, ticker)
    d = {
        "ticker": ticker, "df": df, "idx": df.index, "n": n,
        "n_fertig": n - 1 if offen else n,  # Tagebuch und Depot nutzen nur abgeschlossene Kerzen
        "offen": offen,
        "O": df['Open'].to_numpy(dtype=float),  # NaN, wenn Yahoo keine Eröffnung liefert
        "O_ersatz": df['Open'].fillna(df['Close']).to_numpy(dtype=float), "H": df['High'].to_numpy(dtype=float),
        "L": df['Low'].to_numpy(dtype=float), "C": df['Close'].to_numpy(dtype=float),
        "ATR": df['ATR'].to_numpy(dtype=float), "FX": kurs_umrechner(fx, df.index).to_numpy(dtype=float),
        "signale": signale, "ueberhitzt": ueberhitzt, "ueberverkauft": ueberverkauft,
        "pos": {tag: i for i, tag in enumerate(df.index)},
        "termine": None,
    }
    d["morgen"] = d["gesperrt"] = d["gerade"] = np.zeros(n, bool)
    if zahlen_df is not None:
        termine = zahlen_termine(zahlen_df)
        d["termine"] = termine
        d["morgen"], d["gesperrt"], d["gerade"], d["lang"], d["reak"] = zahlen_regeln(termine, df.index,
                                                                                      handelstag(ticker))
    return d

def signal_zuletzt(df, mit_short):
    """Feuert am letzten Kurstag irgendeine Strategie? (Die Signale hängen nicht von den Terminen ab.)"""
    try:
        signale = strategie_signale(calculate_indicators(df.copy()), mit_short)[0]
        return any(ok[-1] for ok, _, _ in signale.values())
    except Exception:
        return False

def kandidaten(d, i, pausiert=frozenset()):
    """Welche Strategien feuern am Tag i (Signal zum Schlusskurs) und was ist die Entscheidung?
    Gibt (gewählte Strategie oder None, Grund fürs Warten oder None) zurück. Dieselbe Regel gilt für den
    Scanner und beide Depot-Läufe – mit und ohne Lernen unterscheiden sich nur durch die Pausen."""
    feuernd = [k for k, (ok, _, _) in d["signale"].items() if ok[i]]
    if not feuernd:
        return None, None
    if len({STRATEGIEN[k]["richtung"] for k in feuernd}) > 1:
        return None, "Signale widersprechen sich"
    if d["gesperrt"][i]:
        return None, "Quartalszahlen"
    if d["gerade"][i]:
        feuernd_ok = [k for k in feuernd if STRATEGIEN[k]["art"] != "gegen"]
        if not feuernd_ok:
            return None, "Zahlen gerade erst – Gegenbewegung riskant"
        feuernd = feuernd_ok
    aktiv = [k for k in feuernd if k not in pausiert]
    if not aktiv:
        return None, f"{strategie_name(feuernd[0])} pausiert"
    return aktiv[0], None


# ----------------------------------------------------------------------------
# Gemeinsame Ein- und Ausstiegsregeln für Tagebuch und Depot
# ----------------------------------------------------------------------------
SPREAD = SPREAD_PROZENT / 100

def mit_spread(kurs, r, einstieg):
    """Ausführungskurs inkl. Spread: Kauf (Long-Einstieg, Short-Eindeckung) etwas teurer, Verkauf etwas billiger."""
    kaufen = (r > 0) == einstieg
    return kurs * (1 + SPREAD) if kaufen else kurs * (1 - SPREAD)

def einstieg_moeglich(d, i, r, stop, limit):
    """Einstieg zur Eröffnung am Tag i nur, wenn die Eröffnung nicht hinter dem Stop und nicht über dem Limit liegt
    (fehlt die Eröffnung, ergibt der Vergleich mit NaN False: kein Einstieg)."""
    o = d["O"][i]
    return r * (o - stop) > 0 and r * (limit - o) >= 0

def pruefe_ausstieg(d, i, r, pos):
    """Ausstieg am Tag i? Reihenfolge: Kurslücke über Stop/Ziel (nicht am Einstiegstag), Stop vor Ziel im
    Tagesverlauf, vor Quartalszahlen zum Schluss, Zeitstopp zum Schluss. Gibt (Kurs in $, Grund) zurück."""
    o, h, l, c = d["O"][i], d["H"][i], d["L"][i], d["C"][i]  # o ist NaN ohne Eröffnung: dann keine Lückenregel
    gegen, fuer = (l, h) if r > 0 else (h, l)  # ungünstigster / günstigster Kurs des Tages
    nicht_neu = pos["start"] != i
    if nicht_neu and r * (o - pos["stop"]) <= 0:
        return o, "Stop (Kurslücke)"
    if nicht_neu and r * (o - pos["ziel"]) >= 0:
        return o, "Ziel (Kurslücke)"
    if r * (gegen - pos["stop"]) <= 0:
        return pos["stop"], "Stop"
    if r * (fuer - pos["ziel"]) >= 0:
        return pos["ziel"], "Ziel"
    if d["morgen"][i]:
        return c, "vor Quartalszahlen"
    if i - pos["start"] + 1 >= ZEITSTOPP_TAGE:
        return c, "Zeitstopp"
    return None, None


# ----------------------------------------------------------------------------
# Strategie-Tagebuch: jede Strategie handelt gedanklich mit, unabhängig vom Depot ("Lernen aus Fehlern")
# ----------------------------------------------------------------------------
def strategie_tagebuch(daten, einst):
    """Jede Strategie wird für jeden Ticker unabhängig vom Depot durchgespielt (höchstens ein gedachter Trade
    je Ticker und Strategie, gleiche Ein- und Ausstiegsregeln, ohne Kapitalgrenzen). Ergebnis je Trade in R:
    1 R = der geplante Verlust bis zum Stop (am Signaltag). Kosten (Spread, Gebühren) sind abgezogen."""
    gebuehr_in_r = 2 * einst.gebuehr / (einst.konto * einst.risiko / 100)
    eintraege = []
    for t, d in daten.items():
        n = d["n_fertig"]
        for key, (feuert, stop_a, ziel_a) in d["signale"].items():
            r = STRATEGIEN[key]["richtung"]
            gegen = STRATEGIEN[key]["art"] == "gegen"
            i = TAGEBUCH_AB_KERZE
            while i < n - 1:
                if not feuert[i] or d["gesperrt"][i] or (gegen and d["gerade"][i]):
                    i += 1
                    continue
                stop, ziel, kurs = stop_a[i], ziel_a[i], d["C"][i]
                limit = limit_kurs(r, kurs, d["ATR"][i], stop, ziel)
                j = i + 1
                if not einstieg_moeglich(d, j, r, stop, limit):
                    i += 1
                    continue
                einstieg = mit_spread(d["O"][j], r, True)
                pos = {"start": j, "stop": stop, "ziel": ziel}
                k = j
                while k < n:
                    preis, grund = pruefe_ausstieg(d, k, r, pos)
                    if preis is not None:
                        break
                    k += 1
                if k >= n:
                    break  # am Datenende noch offen: zählt (noch) nicht
                ausstieg = mit_spread(preis, r, False)
                roh = r * (ausstieg - einstieg) / abs(kurs - stop)
                eintraege.append({"strategie": key, "ticker": t, "signal_tag": d["idx"][i], "einstieg_tag": d["idx"][j],
                                  "ausstieg_tag": d["idx"][k], "grund": grund,
                                  "R": max(-R_GRENZE, min(R_GRENZE, roh)) - gebuehr_in_r})
                i = k  # nächstes Signal frühestens am Ausstiegstag (zum Schlusskurs)
    eintraege.sort(key=lambda e: (e["ausstieg_tag"], e["ticker"], VORRANG[e["strategie"]]))
    return eintraege

def lernverlauf(tagebuch, tage, einst):
    """Geht Tag für Tag vor: Welche Strategien sind am Abend von Tag t pausiert? Es zählen nur gedachte Trades,
    deren Ausstieg spätestens an Tag t war (beim Entscheiden also schon bekannt). Pause, wenn die letzten bis zu
    60 Trades im Schnitt unter −0,1 R liegen (ab 20 Trades), wieder aktiv, sobald der Schnitt über 0 R ist."""
    fenster = {k: deque(maxlen=LERNEN_FENSTER) for k in STRATEGIEN}
    alle_r = {k: [] for k in STRATEGIEN}
    pausiert = set()
    zeiger = 0
    pausen = {}
    for tag in tage:
        while zeiger < len(tagebuch) and tagebuch[zeiger]["ausstieg_tag"] <= tag:
            e = tagebuch[zeiger]
            fenster[e["strategie"]].append(e["R"])
            alle_r[e["strategie"]].append(e["R"])
            zeiger += 1
        if einst.lernen:
            for k, f in fenster.items():
                n = len(f)
                schnitt = sum(f) / n if n else 0.0
                if k not in pausiert and n >= LERNEN_MIN_TRADES and schnitt < LERNEN_PAUSE_AB:
                    pausiert.add(k)
                elif k in pausiert and (n < LERNEN_MIN_TRADES or schnitt > LERNEN_WIEDER_AB):
                    pausiert.discard(k)
        pausen[tag] = frozenset(pausiert)
    stand = {}
    for k in STRATEGIEN:
        f, a = list(fenster[k]), alle_r[k]
        n = len(f)
        schnitt = sum(f) / n if n else np.nan
        streuung = float(np.std(a, ddof=1)) if len(a) > 1 else np.nan
        stand[k] = {"n": n, "gesamt": len(a), "schnitt": schnitt,
                    "spanne": 2 * streuung / math.sqrt(n) if n > 1 else np.nan,
                    "quote": sum(1 for x in f if x > 0) / n * 100 if n else np.nan,
                    "pausiert": k in pausiert}
    return pausen, stand


# ----------------------------------------------------------------------------
# Virtuelles Depot: der Bot handelt die letzten Monate mit dem Startkapital
# ----------------------------------------------------------------------------
def positionswert(p, kurs_usd, fx):
    """Wert einer Position in € (ohne Ausstiegskosten). Long: Aktien zum aktuellen Kurs. Short: hinterlegter
    Einsatz plus Gewinn (bzw. minus Verlust) aus dem gefallenen (bzw. gestiegenen) Kurs."""
    if p["richtung"] > 0:
        return p["stueck"] * kurs_usd / fx
    return p["stueck"] * (p["einsatz_je_stueck"] + (p["einstieg_usd"] - kurs_usd) / fx)

def positionsgroesse(kurs, stop, konto, risiko_prozent, bruchstuecke, bargeld=math.inf, risiko_frei=math.inf):
    """Stückzahl, bei der der Stop-Loss höchstens risiko_prozent des Kontos kostet. Zusätzlich: Position
    höchstens MAX_POSITION_PROZENT des Kontos, nicht mehr als das freie Geld und nicht mehr als das noch freie
    Gesamtrisiko. Gilt für Long und Short."""
    risiko_je_aktie = abs(kurs - stop)
    if risiko_je_aktie <= 0 or bargeld <= 0 or kurs <= 0 or risiko_frei <= 0:
        return 0
    stueck = min(konto * risiko_prozent / 100 / risiko_je_aktie,
                 konto * MAX_POSITION_PROZENT / 100 / kurs,
                 bargeld / kurs,
                 risiko_frei / risiko_je_aktie)
    return math.floor(stueck * 100 + 1e-9) / 100 if bruchstuecke else math.floor(stueck + 1e-9)

def simuliere_depot(daten, pausen, einst, lernen, zustand=None, signal_ticker=None):
    """Spielt die Strategien rückwirkend mit einem virtuellen Depot durch. Regeln wie im Tagebuch (Signal zum
    Schluss, Einstieg zur nächsten Eröffnung bis zum Limit, Stop/Ziel/Zahlen/Zeitstopp), dazu Kapital- und
    Risikogrenzen, Gebühr und Spread je Order. Mit Lernen werden pausierte Strategien nicht gehandelt.
    Papier-Depot: Mit 'zustand' geht es vom gespeicherten Stand aus nur über die Tage nach zustand["bis"] weiter
    (beim Anlegen nur der letzte fertige Tag); 'signal_ticker' begrenzt, für welche Ticker neue Aufträge entstehen."""
    alle_tage = sorted(set().union(*(set(d["idx"][:d["n_fertig"]]) for d in daten.values())))
    if not alle_tage:
        return None
    if zustand is None:
        start = alle_tage[-1] - pd.DateOffset(months=einst.rueckblick)
        tage = [tag for tag in alle_tage if tag > start]
        if len(tage) < 5:
            return None
    else:
        # Ein Tag zählt erst, wenn er für alle Ticker fertig ist (läuft z. B. die US- oder Krypto-Kerze noch, wartet
        # er auf den nächsten Lauf) – sonst wäre er für diese Ticker danach für immer übersprungen
        laufend = [d["idx"][d["n_fertig"]] for d in daten.values() if d["n_fertig"] < d["n"]]
        if laufend:
            alle_tage = [tag for tag in alle_tage if tag < min(laufend)]
        tage = [tag for tag in alle_tage if tag > zustand["bis"]] if zustand["bis"] is not None else alle_tage[-1:]
        if zustand["bis"] is None and not tage:
            return None

    gebuehr = einst.gebuehr
    bargeld = float(einst.konto)
    depotwert = float(einst.konto)  # zum letzten Schlusskurs – Grundlage für die Positionsgröße
    positionen, auftraege, trades, verlauf = {}, [], [], []
    letzter_kurs = {}  # Ticker -> (Schlusskurs in $, Wechselkurs) für Tage ohne Handel
    gebuehren = spread_kosten = 0.0
    hoechstes_risiko = (0.0, 0)
    reihenfolge = {t: i for i, t in enumerate(daten)}
    if zustand is not None:
        bargeld, depotwert = zustand["bargeld"], zustand["depotwert"]
        gebuehren, spread_kosten = zustand["gebuehren"], zustand["spread"]
        hoechstes_risiko = tuple(zustand["hoechstes_risiko"])
        positionen = {p["ticker"]: dict(p) for p in zustand["positionen"]}
        auftraege = [dict(a) for a in zustand["auftraege"]]
        for t, p in positionen.items():
            d = daten[t]
            p["start"] = d["pos"][p["kauf_tag"]]
            i = d["pos"][letzter_tag_bis(d, zustand["bis"])]
            letzter_kurs[t] = (d["C"][i], d["FX"][i])

    def in_euro(p, kurs, rate):
        """Kurs in € für die Trade-Tabelle. Bei Shorts entsteht das Ergebnis in $ und wird zum heutigen Wechselkurs
        umgerechnet – der Kurs wird so angezeigt, dass Einstieg − Ausstieg genau zum Ergebnis passt."""
        return kurs / rate if p["richtung"] > 0 else p["einsatz_je_stueck"] - (p["einstieg_usd"] - kurs) / rate

    def offenes_risiko():
        """Geplantes Risiko aller offenen Positionen: Verlust vom Einstieg bis zum Stop (in €)."""
        return sum(p["risiko_eur"] for p in positionen.values())

    for tag in tage:
        # 1) Aufträge vom Vortag zur Eröffnung ausführen – in fester Reihenfolge (bestes CRV zuerst)
        warten = []
        for auftrag in auftraege:
            t = auftrag["ticker"]
            d = daten[t]
            i = d["pos"].get(tag)
            if i is None or i >= d["n_fertig"]:
                warten.append(auftrag)  # Ticker handelt heute nicht – Auftrag wartet
                continue
            r, stop = auftrag["richtung"], auftrag["stop"]
            if t in positionen or not einstieg_moeglich(d, i, r, stop, auftrag["limit"]):
                continue  # Kurslücke hinter den Stop oder über das Limit: Auftrag verfällt
            if len(positionen) >= MAX_POSITIONEN:
                continue
            if r < 0 and sum(1 for p in positionen.values() if p["richtung"] < 0) >= MAX_SHORTS:
                continue
            rate = d["FX"][i]
            ausfuehrung = mit_spread(d["O"][i], r, True)
            risiko_frei = depotwert * MAX_GESAMTRISIKO_PROZENT / 100 - offenes_risiko()
            stueck = positionsgroesse(ausfuehrung / rate, stop / rate, depotwert, einst.risiko, einst.bruchstuecke,
                                      bargeld - gebuehr, risiko_frei)
            einsatz = stueck * ausfuehrung / rate
            if stueck <= 0 or einsatz < MIN_EINSATZ:
                continue
            bargeld -= einsatz + gebuehr
            gebuehren += gebuehr
            spread_kosten += stueck * d["O"][i] * SPREAD / rate
            positionen[t] = {"ticker": t, "richtung": r, "strategie": auftrag["strategie"], "stueck": stueck,
                             "einstieg_usd": ausfuehrung, "einsatz_je_stueck": ausfuehrung / rate, "stop": stop,
                             "ziel": auftrag["ziel"], "start": i, "kauf_tag": tag, "kosten": einsatz + gebuehr,
                             "erloes": 0.0, "risiko_eur": stueck * abs(ausfuehrung - stop) / rate}
            letzter_kurs[t] = (d["O"][i], rate)
            risiko_jetzt = offenes_risiko() / depotwert * 100
            if risiko_jetzt > hoechstes_risiko[0]:
                hoechstes_risiko = (risiko_jetzt, len(positionen))
        auftraege = warten

        # 2) Stop, Ziel, Quartalszahlen und Zeitstopp prüfen
        for t in list(positionen):
            p, d = positionen[t], daten[t]
            i = d["pos"].get(tag)
            if i is None or i >= d["n_fertig"]:
                continue
            preis, grund = pruefe_ausstieg(d, i, p["richtung"], p)
            if preis is None:
                continue
            rate = d["FX"][i]
            ausfuehrung = mit_spread(preis, p["richtung"], False)
            erloes = positionswert(p, ausfuehrung, rate) - gebuehr
            bargeld += erloes
            gebuehren += gebuehr
            spread_kosten += p["stueck"] * preis * SPREAD / rate
            p["erloes"] += erloes
            del positionen[t]
            trades.append({**p, "verkauf_tag": tag, "verkauf_preis": in_euro(p, ausfuehrung, rate), "grund": grund})

        # 3) Signale zum Schlusskurs -> Aufträge für den nächsten Handelstag
        pausiert = pausen.get(tag, frozenset()) if lernen else frozenset()
        neue = []
        for t, d in daten.items():
            i = d["pos"].get(tag)
            if i is None or i >= d["n_fertig"]:
                continue
            letzter_kurs[t] = (d["C"][i], d["FX"][i])
            if t in positionen or i < MIN_KERZEN - 1 or (signal_ticker is not None and t not in signal_ticker):
                continue
            wahl, _ = kandidaten(d, i, pausiert)
            if wahl is None:
                continue
            r = STRATEGIEN[wahl]["richtung"]
            _, stop_a, ziel_a = d["signale"][wahl]
            stop, ziel, kurs = stop_a[i], ziel_a[i], d["C"][i]
            neue.append({"ticker": t, "richtung": r, "strategie": wahl, "stop": stop, "ziel": ziel,
                         "limit": limit_kurs(r, kurs, d["ATR"][i], stop, ziel),
                         "crv": r * (ziel - kurs) / (r * (kurs - stop))})
        ersetzt = {a["ticker"] for a in neue}
        auftraege = sorted([a for a in auftraege if a["ticker"] not in ersetzt] + neue,
                           key=lambda a: (-a["crv"], VORRANG[a["strategie"]], reihenfolge[a["ticker"]]))

        # 4) Depotwert zum Schlusskurs
        depotwert = bargeld + sum(positionswert(p, *letzter_kurs[t]) for t, p in positionen.items())
        verlauf.append((tag, depotwert))

    if zustand is not None:  # Papier-Depot: neuer Stand ohne Kaufen-und-Halten-Vergleich
        for t, p in positionen.items():
            kurs, fx = letzter_kurs[t]
            p["wert"] = positionswert(p, kurs, fx)
            p["kurs_jetzt"] = in_euro(p, kurs, fx)
            p["tage"] = daten[t]["n_fertig"] - p["start"]
        return {"bis": tage[-1] if tage else zustand["bis"], "tage": tage, "bargeld": bargeld,
                "depotwert": depotwert, "positionen": list(positionen.values()), "auftraege": auftraege,
                "trades": trades, "verlauf": verlauf, "gebuehren": gebuehren, "spread": spread_kosten,
                "hoechstes_risiko": hoechstes_risiko, "offenes_risiko": offenes_risiko() / depotwert * 100}

    # Vergleich: Startkapital gleichmäßig aufteilen und jeden Ticker an seinem ersten Handelstag im Zeitraum
    # kaufen und halten (Ticker, die erst später starten, z. B. Börsengänge, bleiben Bargeld)
    anteil = einst.konto / len(daten)
    halten = {}
    for t, d in daten.items():
        eigene = [tag for tag in d["idx"][:d["n_fertig"]] if tag >= tage[0]]
        if eigene and eigene[0] - tage[0] <= pd.Timedelta(days=7):
            i = d["pos"][eigene[0]]
            halten[t] = (eigene[0], (anteil - gebuehr) / (mit_spread(d["O_ersatz"][i], 1, True) / d["FX"][i]))
    vergleich = None
    if halten:
        kurse, werte_halten = {}, []
        for tag in tage:
            wert = anteil * (len(daten) - len(halten))
            for t, (kauftag, stueck) in halten.items():
                d = daten[t]
                i = d["pos"].get(tag)
                if i is not None and i < d["n_fertig"]:
                    kurse[t] = d["C"][i] / d["FX"][i]
                wert += stueck * kurse[t] if tag >= kauftag else anteil
            werte_halten.append(wert)
        vergleich = pd.Series(werte_halten, index=[tag for tag, _ in verlauf])

    for t, p in positionen.items():  # offene Positionen zum letzten Kurs bewerten
        kurs, fx = letzter_kurs[t]
        p["wert"] = positionswert(p, kurs, fx)
        p["kurs_jetzt"] = in_euro(p, kurs, fx)
        d = daten[t]
        p["tage"] = d["n_fertig"] - p["start"]
    werte = pd.Series([w for _, w in verlauf], index=[tag for tag, _ in verlauf])
    hoch = werte.cummax()
    return {
        "start": tage[0], "ende": tage[-1], "start_wert": float(einst.konto), "end_wert": float(werte.iloc[-1]),
        "verlauf": werte, "vergleich": vergleich, "trades": trades, "offen": list(positionen.values()),
        "nicht_gehalten": [t for t in daten if t not in halten], "gebuehren": gebuehren, "spread": spread_kosten,
        "max_rueckgang": float(((hoch - werte) / hoch).max() * 100), "bargeld": bargeld,
        "hoechstes_risiko": hoechstes_risiko, "offenes_risiko": offenes_risiko() / werte.iloc[-1] * 100,
    }

def letzter_tag_bis(d, tag):
    """Letzter fertige Kurstag des Tickers am oder vor 'tag' (für Tage, an denen er nicht gehandelt wurde)."""
    fertig = d["idx"][:d["n_fertig"]]
    return fertig[max(fertig.searchsorted(tag, side="right") - 1, 0)]

def zufallsspanne(erg_a, erg_b):
    """Wie groß kann der Unterschied zweier Depots allein durch Zufall sein? Es zählen nur Trades, die nur eines
    der beiden Depots gemacht hat (gemeinsame heben sich auf); ±2 Standardabweichungen."""
    def ergebnisse(erg):
        aus = {(p["ticker"], p["kauf_tag"], p["strategie"]): p["erloes"] - p["kosten"] for p in erg["trades"]}
        aus.update({(p["ticker"], p["kauf_tag"], p["strategie"]): p["erloes"] + p["wert"] - p["kosten"]
                    for p in erg["offen"]})
        return aus
    a, b = ergebnisse(erg_a), ergebnisse(erg_b)
    nur_einer = [v for k, v in a.items() if k not in b] + [v for k, v in b.items() if k not in a]
    return 2 * math.sqrt(sum(v * v for v in nur_einer))


# ----------------------------------------------------------------------------
# Scanner: Entscheidung für heute je Ticker
# ----------------------------------------------------------------------------
def fehler_zeile(ticker, grund):
    return {"Ticker": ticker, "Signal": FEHLER, "_fehler": grund}

def naechster_termin(d, kurstag):
    """Nächster bekannter Quartalszahlen-Termin nach dem letzten Kurstag (oder None)."""
    if d["termine"] is None:
        return None
    zukunft = [t for t in d["termine"] if reaktionstag(t) > kurstag]
    return zukunft[0] if zukunft else None

def letzter_tag_vor(termin, kurstag, schritt):
    """Letzter Handelstag vor dem Reaktionstag der Zahlen (nach dem Börsenkalender)."""
    reak = reaktionstag(termin)
    tage = pd.date_range(kurstag + schritt, reak - pd.Timedelta(days=1), freq=schritt)
    return tage[-1] if len(tage) else None

def scanner_zeile(t, d, pausiert, einst):
    i = (d["n_fertig"] if einst.nur_schluss else d["n"]) - 1
    if i + 1 < MIN_KERZEN:
        return fehler_zeile(t, f"nur {i + 1} Kerzen – zu wenig Historie")
    kurstag = d["idx"][i]
    rate = d["FX"][i]
    kurs = d["C"][i] / rate
    if pd.isna(d["ATR"][i]) or pd.isna(kurs):
        return fehler_zeile(t, "Indikatoren unvollständig")
    wahl, grund = kandidaten(d, i, pausiert if einst.lernen else frozenset())
    zeile = {"Ticker": t, "Kurs": kurs, "_stand": kurstag, "_offen": d["offen"] and not einst.nur_schluss,
             "_kerze_offen": d["offen"], "_strategie": wahl}
    termin = naechster_termin(d, kurstag)
    if einst.ohne_zahlen:
        zeile["Zahlen"] = "aus"
    elif not hat_zahlen(t):
        zeile["Zahlen"] = "–"
    elif d["termine"] is None:
        zeile["Zahlen"] = "?"
    elif termin is None:
        zeile["Zahlen"] = "? (fällig?)" if (len(d["termine"]) and kurstag - d["termine"][-1].tz_localize(None)
                                             > pd.Timedelta(days=100)) else "–"
    else:
        zeile["Zahlen"] = datum(termin)
    zeile["_termin"] = termin

    if wahl is not None:
        r = STRATEGIEN[wahl]["richtung"]
        _, stop_a, ziel_a = d["signale"][wahl]
        stop, ziel = stop_a[i] / rate, ziel_a[i] / rate
        limit = limit_kurs(r, kurs, d["ATR"][i] / rate, stop, ziel)
        stueck = positionsgroesse(kurs, stop, einst.konto, einst.risiko, einst.bruchstuecke)
        zeile.update({"Signal": KAUFEN if r > 0 else SHORT,
                      "Strategie": strategie_name(wahl) + ("" if stueck else " (Konto zu klein)"), "Limit": limit,
                      "Stop": stop, "Ziel": ziel, "CRV": r * (ziel - kurs) / (r * (kurs - stop)), "Stück": stueck,
                      "Einsatz": stueck * kurs, "Risiko": stueck * abs(kurs - stop)})
        if zeile["_offen"]:
            zeile["Strategie"] += " (vorläufig)"
    elif grund is not None:
        if grund == "Quartalszahlen" and termin is not None:
            grund = f"Quartalszahlen {datum(termin)}"
        zeile.update({"Signal": WARTEN, "Strategie": grund})
    elif d["ueberhitzt"][i]:
        zeile.update({"Signal": SICHERN, "Strategie": "überhitzt – falls Long im Depot"})
    elif einst.mit_short and d["ueberverkauft"][i]:
        zeile.update({"Signal": SICHERN, "Strategie": "überverkauft – falls Short im Depot"})
    else:
        zeile.update({"Signal": BEOBACHTEN, "Strategie": ""})
    return zeile


# ----------------------------------------------------------------------------
# Ausgabe
# ----------------------------------------------------------------------------
def im_notebook():
    """True unter Jupyter/Colab mit %run (dort kann eine farbige HTML-Tabelle angezeigt werden)."""
    try:
        from IPython import get_ipython
    except ImportError:
        return False
    ip = get_ipython()
    return ip is not None and hasattr(ip, "kernel")

def farben_im_terminal():
    # IDLE behauptet ein Terminal zu sein, kann aber keine ANSI-Farben darstellen
    if os.environ.get("NO_COLOR") or "idlelib" in sys.modules or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")  # schaltet ANSI-Farben in der Windows-Konsole ein
    return True

def berlin(tag, uhr_ny):
    """US-Börsenzeit (New York) an einem Tag -> Uhrzeit in Deutschland, z. B. '15:30'."""
    return f"{pd.Timestamp(f'{tag:%Y-%m-%d} {uhr_ny}', tz=NY).tz_convert(BERLIN):%H:%M}"

def handelsplan(zeile, nr, einst, waehrung):
    """Ein Satz, was genau zu tun ist (für KAUFEN/SHORT)."""
    t = zeile["Ticker"]
    kaufen = zeile["Signal"] == KAUFEN
    kopf = f"{'🟢' if kaufen else '🔴'} {nr}. {t} · {zeile['Strategie']}"
    schritt = handelstag(t)
    einstieg = zeile["_stand"] + schritt
    raus, warum = einstieg + (ZEITSTOPP_TAGE - 1) * schritt, f"{ZEITSTOPP_TAGE} Handelstage"
    if zeile["_termin"] is not None:
        vor_zahlen = letzter_tag_vor(zeile["_termin"], zeile["_stand"], schritt)
        if vor_zahlen is not None and vor_zahlen < raus:
            raus, warum = vor_zahlen, f"Quartalszahlen {datum(zeile['_termin'])} {uhrzeit_text(zeile['_termin'])}"
    if ist_krypto(t):  # Handel rund um die Uhr, Tageskerze nach UTC
        ab, bis = "", ""
    elif waehrung_von(t) == "USD":
        frueh = (raus.month, raus.day) in ((7, 3), (12, 24)) or (raus.month == 11 and raus.weekday() == 4
                                                                   and 23 <= raus.day <= 29)
        ab = f" ab {berlin(einstieg, '09:30')} Uhr (US-Börsenstart)"
        bis = f" vor {berlin(raus, '13:00' if frueh else '16:00')} Uhr{' (verkürzter Handelstag)' if frueh else ''}"
    else:
        ab, bis = " ab 09:00 Uhr (Börsenstart)", " vor 17:30 Uhr"
    stueck = de(zeile["Stück"], 2 if einst.bruchstuecke else 0)
    if kaufen:
        tun = f"{stueck} Stück kaufen, Limit {de(zeile['Limit'])} {waehrung} (höchster Kaufkurs)"
    else:
        tun = (f"{stueck} Stück leerverkaufen (z. B. per CFD/Turbo), Limit {de(zeile['Limit'])} {waehrung} "
               f"(tiefster Verkaufskurs)")
    risiko_limit = zeile["Stück"] * abs(zeile["Limit"] - zeile["Stop"])
    satz = (f"{kopf}: Am {datum(einstieg)}{ab} {tun}. Sofort Stop {de(zeile['Stop'])} {waehrung} setzen, Ziel "
            f"{de(zeile['Ziel'])} {waehrung}. Greift der Stop, verlierst du ca. {de(zeile['Risiko'], 0)} {waehrung} "
            f"(bei Einstieg zum Limit bis {de(risiko_limit, 0)} {waehrung}, bei Kurslücken mehr). Spätestens "
            f"{datum(raus)}{bis} {'verkaufen' if kaufen else 'eindecken'} ({warum}).")
    if str(zeile.get("Zahlen", "")).startswith("?"):
        satz += " Achtung: Quartalszahlen-Termin unbekannt – vor dem Kauf selbst prüfen."
    return satz

def marktampel(markt, mit_short=True):
    if markt is None:
        return None
    d = markt["df"]
    i = markt["n_fertig"] - 1
    sma = d["SMA_50"].iloc[i]
    if pd.isna(sma):
        return None
    if d["Close"].iloc[i] > sma:
        return "🟢 Markt (Nasdaq-100/QQQ) über der 50-Tage-Linie – Rückenwind für Long."
    return ("🔴 Markt (Nasdaq-100/QQQ) unter der 50-Tage-Linie – Vorsicht bei Long"
            + (", Rückenwind für Short." if mit_short else "."))

def kopfzeilen(zeilen, einst, fx_heute, waehrung, markt, ohne_zahlen):
    ok = [z for z in zeilen if "_stand" in z]
    stand = max(z["_stand"] for z in ok)
    risiko_betrag = einst.konto * einst.risiko / 100
    titel = (f"📈 SWING-SCANNER · Daten bis {stand:%d.%m.%Y} · Konto {de(einst.konto, 0)} {waehrung} · "
             f"Risiko je Trade {prozent(einst.risiko)} % = {de(risiko_betrag, 0)} {waehrung}")
    if fx_heute:
        titel += f" · 1 € = {de(fx_heute, 4)} $"
    anzahl = pd.Series([z["Signal"] for z in zeilen]).value_counts()
    zusammenfassung = " · ".join(f"{anzahl[s]}× {s}" for s in (KAUFEN, SHORT, WARTEN, SICHERN, BEOBACHTEN, FEHLER)
                                 if s in anzahl)
    hinweise = []
    ampel = marktampel(markt, einst.mit_short)
    if ampel:
        hinweise.append(ampel)
    gesamt = einst.konto * MAX_GESAMTRISIKO_PROZENT / 100
    shorts = f" (davon höchstens {MAX_SHORTS} Short)" if einst.mit_short else ""
    hinweise.append(f"Regel: höchstens {MAX_POSITIONEN} Positionen gleichzeitig{shorts} "
                    f"und zusammen höchstens {MAX_GESAMTRISIKO_PROZENT} % = {de(gesamt, 0)} {waehrung} Risiko – "
                    f"bei mehr Signalen die oberen nehmen.")
    if not fx_heute:
        hinweise.append("⚠️ Wechselkurs EUR/USD nicht verfügbar – US-Kurse nicht umgerechnet (Beträge in $).")
    if ohne_zahlen:
        hinweise.append("⚠️ Ohne Quartalszahlen-Termine (--ohne-zahlen): Die Zahlen-Regel ist aus – Termine selbst prüfen.")
    if any(z["_offen"] for z in ok):
        hinweise.append("⏳ Die heutige Tageskerze ist noch nicht fertig (Börse noch offen bzw. Krypto-Tag läuft). "
                        "Signale sind vorläufig – vor "
                        "allem Ausbruch/Abbruch (Volumen) und MACD-Wende sind erst nach Börsenschluss sicher. "
                        "Mit --nur-schluss nur fertige Tage bewerten.")
    if einst.nur_schluss and any(z["_kerze_offen"] for z in ok):
        hinweise.append("⏳ Laufende Tageskerze ignoriert (--nur-schluss): Kurs = letzter Schlusskurs.")
    for z in ok:
        if (stand - z["_stand"]).days > 5:
            hinweise.append(f"⚠️ {z['Ticker']}: letzte Kurse vom {z['_stand']:%d.%m.%Y} – veraltet?")
    return titel, zusammenfassung, hinweise

def fusszeilen(zeilen, einst, waehrung, news, zusatz):
    fuss = []
    fehler = {}
    for z in zeilen:
        if "_fehler" in z:
            fehler.setdefault(z["_fehler"], []).append(z["Ticker"])
    for grund, ticker in fehler.items():
        fuss.append(f"❌ {', '.join(ticker)}: {grund}")
    ohne_termine = [z["Ticker"] for z in zeilen if z.get("Zahlen", "").startswith("?")]
    if ohne_termine:
        je_grund = {}
        for t in ohne_termine:
            info = zusatz.get(t, {}).get("zahlen_info", "")
            je_grund.setdefault(info if info and info != "ok" else "kein künftiger Termin bei Yahoo", []).append(t)
        teile = "; ".join(f"{', '.join(ts)}: {grund}" for grund, ts in je_grund.items())
        fuss.append(f"⚠️ Zahlen „?“ = kein (aktueller) Quartalszahlen-Termin ({teile}) – vor dem Kauf selbst prüfen.")
    ohne_news = [t for t, n in news.items() if n.get("spalte") == "?"]
    if ohne_news:
        gruende = "; ".join(sorted({news[t].get("info", "") for t in ohne_news}))
        fuss.append(f"📰 News „?“ = Schlagzeilen für {', '.join(ohne_news)} nicht geladen ({gruende}) – selbst prüfen.")
    if fehler or ohne_termine or ohne_news:
        fuss.append("")
    heute = sorted({z["_strategie"] for z in zeilen if z.get("_strategie")}, key=VORRANG.get)
    for key in heute:
        fuss.append(f"{strategie_name(key)}: {STRATEGIEN[key]['regel']}")
    umrechnung = "US-Kurse umgerechnet" if waehrung == "€" else "Wechselkurs nicht verfügbar, nicht umgerechnet"
    fuss.append(f"Beträge in {waehrung} ({umrechnung}). Limit = höchster Kaufkurs (Short: tiefster Verkaufskurs) für den "
                f"Einstieg. Risiko = Verlust, wenn der Stop greift. CRV = Chance ÷ Risiko; nötige Trefferquote = "
                f"1 ÷ (1 + CRV), bei CRV 2 also 34 %, bei CRV 1 über 50 %. ⏸ WARTEN = ein Signal ist da, aber eine "
                f"Regel hält den Bot zurück (Grund in der Spalte Strategie).")
    if any(z.get("Signal") == SICHERN for z in zeilen):
        fuss.append("⚠️ GEWINNE SICHERN = überhitzt bzw. überverkauft. Nur ein Hinweis für eine Position, die du schon "
                    "hast (z. B. einen Teil verkaufen oder den Stop nachziehen) – das virtuelle Depot handelt danach nicht.")
    if einst.mit_short:
        fuss.append("🔴 Short = auf fallende Kurse setzen (z. B. per CFD oder Turbo-Schein). Verluste sind nach oben "
                    "offen. Bei Hebelprodukten zählt der Verlust am Stop, nicht der Einsatz: Hebel × Einsatz = echte "
                    "Positionsgröße.")
    fuss.append("Stop-Orders auf deutschen Handelsplätzen können schon vor 15:30 Uhr bei dünnem Handel auslösen. "
                "Quartalszahlen-Termine kommen von Yahoo und können sich verschieben. Keine Anlageberatung.")
    if any(n.get("zeilen") for n in news.values()):
        fuss.append("📰 Schlagzeilen sind nur ein Hinweis: Die Wortsuche versteht keinen Zusammenhang – vor dem Kauf "
                    "selbst lesen. Sie unterdrücken keine Signale, weil sie sich nicht rückwirkend testen lassen.")
    return fuss

def kuerzen(text, laenge):
    text = str(text)
    return text if len(text) <= laenge else text[:laenge - 1] + "…"

def als_text(tabelle, titel, zusammenfassung, hinweise, fuss, formate, farbig=False, mitte=()):
    tabelle = tabelle.copy()
    if "News" in tabelle:  # Details stehen bei den Schlagzeilen
        tabelle["News"] = tabelle["News"].map(lambda v: kuerzen(v, 26))
    if "Strategie" in tabelle and "Signal" in tabelle:  # Details stehen im Handelsplan; WARTEN-Gründe nur hier
        mit_plan = tabelle["Signal"].isin([KAUFEN, SHORT])
        tabelle.loc[mit_plan, "Strategie"] = tabelle.loc[mit_plan, "Strategie"].map(lambda v: kuerzen(v, 28))
    # east_asian_width: Emojis zählen als 2 Zeichen breit, damit die Spalten bündig bleiben
    with pd.option_context("display.unicode.east_asian_width", True):
        text = tabelle.to_string(index=False, formatters=formate, na_rep="–")
    zeilen = text.splitlines()
    linie = "=" * len(zeilen[0])
    ausgabe = ["", titel, f"   {zusammenfassung}", *hinweise, linie, zeilen[0]]
    signale = tabelle["Signal"] if "Signal" in tabelle else [None] * len(tabelle)
    for zeile, signal in zip(zeilen[1:], signale):
        code = ANSI.get(signal) if farbig else None
        ausgabe.append(f"{code}{zeile}\033[0m" if code else zeile)
    ausgabe += [linie, *mitte, *fuss]
    return "\n".join(ausgabe)

def absatz(text, stil=""):
    return f'<p style="margin: 2px 0; {stil}">{html.escape(text)}</p>' if text else "<br>"

def tabelle_als_html(tabelle, formate, zellfarben=None, links=2, umbruch=()):
    """Styler-Tabelle; ohne jinja2 eine schlichte, aber formatierte HTML-Tabelle."""
    try:
        stil = tabelle.style
        if zellfarben:
            stil = stil.apply(zellfarben, axis=1)
        links_css = ", ".join(f"td.col{i}" for i in range(links))
        return (stil.format(formate, na_rep="–")
                .hide(axis="index")
                .set_table_styles([
                    {"selector": "th", "props": "padding: 4px 6px; text-align: center;"},
                    {"selector": "td", "props": "padding: 4px 6px; text-align: right;"},
                    {"selector": links_css, "props": "text-align: left; font-weight: bold;"},
                    {"selector": "td, th", "props": "white-space: nowrap;"},
                ] + [{"selector": f"td.col{tabelle.columns.get_loc(s)}",
                      "props": "white-space: normal; text-align: left;" + (" min-width: 10em;" if s == "News" and tabelle[s].astype(str).str.len().max() > 20 else "")}
                     for s in umbruch if s in tabelle.columns])
                .to_html())
    except (ImportError, AttributeError):  # ohne jinja2 gibt es keinen Styler
        return tabelle.to_html(index=False, na_rep="–", formatters=formate)

def zeige(html_teil, text_teil):
    """Im Notebook als HTML mit Textfassung (Spyder, qtconsole, jupyter console zeigen die Textfassung)."""
    from IPython.display import display
    display({"text/html": html_teil, "text/plain": text_teil}, raw=True)

def zeige_scanner(tabelle, titel, zusammenfassung, hinweise, plan, schlagzeilen, fuss, formate, notebook):
    mitte = ([""] + plan if plan else []) + ([""] + schlagzeilen if schlagzeilen else []) + [""]
    if not notebook:
        print(als_text(tabelle, titel, zusammenfassung, hinweise, fuss, formate, farben_im_terminal(), mitte))
        return

    def zeilenfarbe(zeile):
        bg, fg = FARBEN.get(zeile["Signal"], (None, None))
        return [f"background-color: {bg}; color: {fg}" if bg else ""] * len(zeile)

    # Schmale Ausgabe (z. B. Colab mit Seitenleiste): Signal, Strategie und News dürfen umbrechen,
    # das Symbol bleibt dabei am Wort („⚠️ GEWINNE / SICHERN“)
    signal_html = {**formate, "Signal": lambda v: str(v).replace(" ", "\u00a0", 1),
                   "News": lambda v: str(v).replace("/", "/\u200b")}
    kopf = absatz(titel, "font-size: 1.15em; font-weight: bold;") + absatz(zusammenfassung)
    kopf += "".join(absatz(h, "opacity: 0.85;") for h in hinweise)
    mitte_html = "".join(absatz(p, "margin: 4px 0;") for p in plan)
    if schlagzeilen:
        mitte_html += absatz(schlagzeilen[0], "font-weight: bold; margin-top: 8px;")
        mitte_html += "".join(absatz(s, "font-size: 0.9em;") for s in schlagzeilen[1:])
    fuss_html = "".join(absatz(f, "font-size: 0.9em; opacity: 0.8;") for f in fuss)
    zeige(kopf + '<div style="margin: 8px 0;">' + tabelle_als_html(tabelle, signal_html, zeilenfarbe, 3, ("Signal", "Strategie", "News"))
          + "</div>"
          + mitte_html + '<div style="margin-top: 8px;">' + fuss_html + "</div>",
          als_text(tabelle, titel, zusammenfassung, hinweise, fuss, formate, mitte=mitte))


# --- Lern-Tabelle -------------------------------------------------------------
LERN_FORMATE = {"Ø je Trade": lambda v: de(v, 2, True) + " R" if not pd.isna(v) else "–",
                "± Zufall": lambda v: "±" + de(v, 2) + " R" if not pd.isna(v) else "–"}

def lern_tabelle(stand, einst, waehrung):
    risiko = einst.konto * einst.risiko / 100
    zeilen = []
    for key, s in stand.items():
        r = STRATEGIEN[key]["richtung"]
        if r < 0 and not einst.mit_short:
            continue
        if s["n"] < LERNEN_MIN_TRADES:
            einschaetzung = "zu wenig Daten"
        elif s["schnitt"] - s["spanne"] > 0:
            einschaetzung = "klar im Plus"
        elif s["schnitt"] + s["spanne"] < 0:
            einschaetzung = "klar im Minus"
        else:
            einschaetzung = "unklar – kann Zufall sein"
        if not einst.lernen:
            status = "– (ohne Lernen)"
        elif s["pausiert"]:
            status = "⏸ pausiert (lief zuletzt schlecht – kann auch Pech sein)"
        elif s["n"] < LERNEN_MIN_TRADES:
            status = f"aktiv (lernt noch: {s['n']}/{LERNEN_MIN_TRADES})"
        else:
            status = "✅ aktiv"
        zeilen.append({"Strategie": strategie_name(key), "Trades": f"{s['n']} von {s['gesamt']}",
                       "Ø je Trade": s["schnitt"],
                       "≈ je Trade": (f"{de(s['schnitt'] * risiko, 0 if abs(s['schnitt'] * risiko) >= 10 else 2, True)} "
                                      f"{waehrung}" if s["n"] else "–"),
                       "± Zufall": s["spanne"], "Einschätzung": einschaetzung, "Status": status})
    return pd.DataFrame(zeilen)

def zeige_lernen(stand, einst, waehrung, notebook, rueckschau_hinweis):
    tabelle = lern_tabelle(stand, einst, waehrung)
    titel = "🧠 WIE LIEFEN DIE STRATEGIEN ZULETZT? (Strategie-Tagebuch – jede Strategie handelt gedanklich mit)"
    erklaerung = [
        f"Gezählt werden die letzten bis zu {LERNEN_FENSTER} gedachten Trades je Strategie über alle Ticker, nach "
        f"Spread und Gebühren. 1 R = der geplante Verlust bis zum Stop (bei dir {de(einst.konto * einst.risiko / 100, 0)} "
        f"{waehrung}).",
        f"Lernregel: Ab {LERNEN_MIN_TRADES} Trades wird eine Strategie pausiert, wenn sie im Schnitt mehr als "
        f"{de(-LERNEN_PAUSE_AB, 1)} R je Trade verliert, und wieder aktiv, sobald der Schnitt im Plus ist. Pausierte "
        f"Strategien handeln im Tagebuch weiter.",
        f"± Zufall: So weit kann der Schnitt allein durch Glück oder Pech schwanken. Lässt man {len(tabelle)} "
        f"Strategien ganz ohne Vorteil je 20 Trades machen, zeigt die beste meist um +0,5 R – reiner Zufall. Erst ab "
        f"etwa 100–200 Trades lässt sich ein Vorteil von 0,2–0,3 R von Glück unterscheiden. Bei {len(tabelle)} "
        f"Strategien wirkt auch ohne echten Vorteil oft eine 'klar im Plus' oder 'klar im Minus' – das sind Hinweise, "
        f"keine Beweise. 'Pausiert' ist eine Vorsichtsmaßnahme.",
        rueckschau_hinweis,
    ]
    with pd.option_context("display.unicode.east_asian_width", True):
        tabelle_text = tabelle.to_string(index=False, formatters=LERN_FORMATE, na_rep="–")
    text = "\n".join(["", titel, tabelle_text, *erklaerung])
    if not notebook:
        print(text)
        return

    def statusfarbe(zeile):
        return ["background-color: #fff3cd; color: #1b1b1b; font-weight: bold;"
                if s == "Status" and "pausiert" in zeile["Status"] else "" for s in zeile.index]

    zeige(absatz(titel, "font-size: 1.15em; font-weight: bold; margin-top: 18px;")
          + '<div style="margin: 8px 0;">' + tabelle_als_html(tabelle, LERN_FORMATE, statusfarbe, 1, ("Status",)) + "</div>"
          + "".join(absatz(e, "font-size: 0.9em; opacity: 0.8;") for e in erklaerung), text)


# --- Ausgabe des virtuellen Depots -------------------------------------------
TRADE_SPALTEN = ["Ticker", "Art", "Strategie", "Einstieg", "Einstiegskurs", "Ausstieg", "Ausstiegskurs", "Grund",
                 "Einsatz", "Ergebnis", "Ergebnis %"]
TRADE_FORMATE = {
    "Einstiegskurs": lambda v: de(v, 2), "Ausstiegskurs": lambda v: de(v, 2), "Einsatz": lambda v: de(v, 0),
    "Ergebnis": lambda v: de(v, 2, True), "Ergebnis %": lambda v: de(v, 1, True),
}

def depot_auswertung(erg, ohne, einst, waehrung):
    trades = erg["trades"]
    rendite = (erg["end_wert"] / erg["start_wert"] - 1) * 100
    name = "mit Lernen" if einst.lernen else "ohne Lernen"
    zeilen = [
        f"🤖 VIRTUELLES DEPOT · Der Bot handelt seit {erg['start']:%d.%m.%Y} mit {de(erg['start_wert'], 0)} "
        f"{waehrung} nach seinen eigenen Signalen",
        f"Depotwert heute ({name}): {de(erg['end_wert'])} {waehrung} ({de(rendite, 1, True)} %) · davon frei: "
        f"{de(erg['bargeld'])} {waehrung} · {len(erg['offen'])}/{MAX_POSITIONEN} Positionen offen, offenes Risiko "
        f"{de(erg['offenes_risiko'], 1)} %",
    ]
    if ohne is not None:
        unterschied = erg["end_wert"] - ohne["end_wert"]
        spanne = zufallsspanne(erg, ohne)
        if abs(unterschied) < 0.005 and spanne == 0:
            zeilen.append(f"Ohne Lernen: {de(ohne['end_wert'])} {waehrung} – beide Depots sind gleich, die Pausen haben "
                          f"im Rückblick keinen Trade verändert.")
        else:
            einordnung = ("Das liegt im Zufallsbereich – ob das Lernen hilft, lässt sich aus diesem Zeitraum nicht "
                          "ablesen (das ist fast immer so)." if abs(unterschied) <= spanne else
                          "Der Unterschied ist größer als die Zufallsspanne – ein Hinweis, kein Beweis.")
            zeilen.append(f"Ohne Lernen: {de(ohne['end_wert'])} {waehrung} · Unterschied {de(unterschied, 0, True)} "
                          f"{waehrung} · Zufallsspanne ±{de(spanne, 0)} {waehrung} → {einordnung}")
    if erg["vergleich"] is not None:
        v_ende = float(erg["vergleich"].iloc[-1])
        ohne_t = f" (ohne {', '.join(erg['nicht_gehalten'])} – erst später gehandelt)" if erg["nicht_gehalten"] else ""
        zeilen.append(f"Zum Vergleich – alle Ticker am {erg['start']:%d.%m.} kaufen und halten{ohne_t}: "
                      f"{de(v_ende)} {waehrung} ({de((v_ende / erg['start_wert'] - 1) * 100, 1, True)} %)")
    if trades:
        gewinner = sum(1 for p in trades if p["erloes"] > p["kosten"])
        zeilen.append(f"Abgeschlossene Trades: {len(trades)} · Gewinner: {gewinner} "
                      f"({de(gewinner / len(trades) * 100, 0)} %) · größter Rückgang des Depots: "
                      f"{de(erg['max_rueckgang'], 1)} % · höchstes gleichzeitiges Risiko: "
                      f"{de(erg['hoechstes_risiko'][0], 1)} % ({erg['hoechstes_risiko'][1]} "
                      f"Position{'en' if erg['hoechstes_risiko'][1] != 1 else ''})")
        teile = []
        for name_r, r in (("Long", 1), ("Short", -1)):
            auswahl = [p for p in trades if p["richtung"] == r]
            if auswahl:
                summe = sum(p["erloes"] - p["kosten"] for p in auswahl)
                treffer = sum(1 for p in auswahl if p["erloes"] > p["kosten"])
                teile.append(f"{name_r}: {len(auswahl)} Trade{'s' if len(auswahl) != 1 else ''}, {treffer} Gewinner, "
                             f"{de(summe, 2, True)} {waehrung}")
        teile.append(f"Kosten: Gebühren {de(erg['gebuehren'])} {waehrung} + Spread ca. {de(erg['spread'])} {waehrung}")
        zeilen.append(" · ".join(teile))
    else:
        zeilen.append(f"Noch keine abgeschlossenen Trades · Kosten: Gebühren {de(erg['gebuehren'])} {waehrung} + "
                      f"Spread ca. {de(erg['spread'])} {waehrung}")
    return zeilen

def trade_tabelle(erg):
    zeilen = []
    for p in erg["offen"]:
        ergebnis = p["erloes"] + p["wert"] - p["kosten"]
        zeilen.append({"Ticker": p["ticker"], "Art": "Long" if p["richtung"] > 0 else "Short",
                       "Strategie": strategie_name(p["strategie"]), "Einstieg": f"{p['kauf_tag']:%d.%m.%y}",
                       "Einstiegskurs": p["einsatz_je_stueck"], "Ausstieg": "offen", "Ausstiegskurs": p["kurs_jetzt"],
                       "Grund": f"noch im Depot (Tag {p['tage']}/{ZEITSTOPP_TAGE})", "Einsatz": p["kosten"],
                       "Ergebnis": ergebnis, "Ergebnis %": ergebnis / p["kosten"] * 100, "_offen": True,
                       "_sort": p["kauf_tag"]})
    for p in erg["trades"]:
        ergebnis = p["erloes"] - p["kosten"]
        zeilen.append({"Ticker": p["ticker"], "Art": "Long" if p["richtung"] > 0 else "Short",
                       "Strategie": strategie_name(p["strategie"]), "Einstieg": f"{p['kauf_tag']:%d.%m.%y}",
                       "Einstiegskurs": p["einsatz_je_stueck"], "Ausstieg": f"{p['verkauf_tag']:%d.%m.%y}",
                       "Ausstiegskurs": p["verkauf_preis"], "Grund": p["grund"], "Einsatz": p["kosten"],
                       "Ergebnis": ergebnis, "Ergebnis %": ergebnis / p["kosten"] * 100, "_offen": False,
                       "_sort": p["verkauf_tag"]})
    if not zeilen:
        return None
    df = pd.DataFrame(zeilen)
    df = pd.concat([df[df["_offen"]], df[~df["_offen"]].sort_values("_sort", ascending=False)])
    return df[TRADE_SPALTEN].reset_index(drop=True)

def depot_chart_svg(reihen, start_wert, waehrung):
    """Liniendiagramm der Depotwerte als SVG (Hover zeigt die Werte je Tag). reihen = [(Name, Series, CSS-Farbe)]."""
    erste = reihen[0][1]
    B, H, L, R, O, U = 720, 260, 64, 190, 14, 28
    alle = pd.concat([r for _, r, _ in reihen] + [pd.Series([start_wert])])
    lo, hi = float(alle.min()), float(alle.max())
    rand = max((hi - lo) * 0.08, start_wert * 0.01)
    lo, hi = lo - rand, hi + rand
    n = len(erste)

    def x(i):
        return L + (B - L - R) * i / max(n - 1, 1)

    def y(w):
        return O + (H - O - U) * (1 - (w - lo) / (hi - lo))

    teile = []
    roh = (hi - lo) / 4  # Gitterlinien mit runden Werten
    schritt = 10 ** math.floor(math.log10(roh))
    schritt *= next(f for f in (1, 2, 2.5, 5, 10) if f * schritt >= roh)
    w = math.ceil(lo / schritt) * schritt
    while w <= hi:
        teile.append(f'<line x1="{L}" x2="{B - R}" y1="{y(w):.1f}" y2="{y(w):.1f}" class="gitter"/>'
                     f'<text x="{L - 8}" y="{y(w) + 4:.1f}" text-anchor="end" class="achse">{de(w, 0)}</text>')
        w += schritt
    teile.append(f'<line x1="{L}" x2="{B - R}" y1="{y(start_wert):.1f}" y2="{y(start_wert):.1f}" class="start"/>')
    monate = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    letzter_monat, beschriftet = None, False
    for i, tag in enumerate(erste.index):
        if tag.month != letzter_monat:
            if letzter_monat is not None:
                teile.append(f'<text x="{x(i):.1f}" y="{H - 8}" text-anchor="middle" class="achse">'
                             f'{monate[tag.month - 1]}</text>')
                beschriftet = True
            letzter_monat = tag.month
    if not beschriftet:
        teile.append(f'<text x="{L}" y="{H - 8}" class="achse">{erste.index[0]:%d.%m.}</text>'
                     f'<text x="{B - R}" y="{H - 8}" text-anchor="end" class="achse">{erste.index[-1]:%d.%m.}</text>')
    enden = []
    for name, reihe, farbe in reihen:
        punkte = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(reihe.values))
        teile.append(f'<polyline points="{punkte}" fill="none" stroke="{farbe}" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        enden.append({"y": y(reihe.iloc[-1]), "name": name, "wert": reihe.iloc[-1], "farbe": farbe})
    enden.sort(key=lambda e: e["y"])
    for k, e in enumerate(enden):  # Endbeschriftungen nicht überlappen lassen
        e["label_y"] = e["y"] if k == 0 else max(e["y"], enden[k - 1]["label_y"] + 16)
    for e in enden:
        teile.append(f'<circle cx="{x(n - 1):.1f}" cy="{e["y"]:.1f}" r="4" fill="{e["farbe"]}"/>'
                     f'<text x="{x(n - 1) + 10:.1f}" y="{e["label_y"] + 4:.1f}" class="label">'
                     f'{html.escape(e["name"])} {de(e["wert"], 0)} {waehrung}</text>')
    breite = (B - L - R) / max(n - 1, 1)
    for i, tag in enumerate(erste.index):  # Hover: unsichtbare Streifen je Tag mit Tooltip
        tip = f"{tag:%d.%m.%Y} · " + " · ".join(f"{name} {de(r.iloc[i])} {waehrung}" for name, r, _ in reihen)
        teile.append(f'<rect x="{x(i) - breite / 2:.1f}" y="{O}" width="{breite:.1f}" height="{H - O - U}" '
                     f'class="hover"><title>{html.escape(tip)}</title></rect>')
    legende = "".join(f'<span style="margin-right: 16px;"><span style="display: inline-block; width: 16px; '
                      f'height: 2px; background: {farbe}; vertical-align: middle; margin-right: 6px;"></span>'
                      f'{html.escape(name)}</span>' for name, _, farbe in reihen)
    legende += ('<span><span style="display: inline-block; width: 16px; height: 1px; background: currentColor; '
                'opacity: 0.5; vertical-align: middle; margin-right: 6px;"></span>Startkapital</span>')
    return f"""<div class="viz-root">
<style>
/* Texte und Hilfslinien erben die Schriftfarbe des Notebooks (hell wie dunkel lesbar) */
.viz-root {{ color: inherit; max-width: {B}px; }}
.viz-root .gitter {{ stroke: currentColor; stroke-opacity: 0.15; stroke-width: 1; }}
.viz-root .start {{ stroke: currentColor; stroke-opacity: 0.5; stroke-width: 1; }}
.viz-root .achse {{ fill: currentColor; fill-opacity: 0.7; font-size: 11px; }}
.viz-root .label {{ fill: currentColor; font-size: 12px; font-weight: 600; }}
.viz-root .hover {{ fill: transparent; }}
.viz-root .hover:hover {{ fill: currentColor; fill-opacity: 0.08; }}
</style>
<div style="font-size: 12px; opacity: 0.8; margin: 4px 0;">{legende}</div>
<svg viewBox="0 0 {B} {H}" width="100%" style="max-width: {B}px; font-family: inherit; overflow: visible;" role="img"
 aria-label="Depotwert des Bots im Vergleich">{''.join(teile)}</svg>
</div>"""

def zeige_depot(erg, ohne, einst, waehrung, notebook, ohne_zahlen_regel, rueckschau_hinweis, ohne_zahlen=False):
    zusammenfassung = depot_auswertung(erg, ohne, einst, waehrung)
    tabelle = trade_tabelle(erg)
    weggelassen = 0
    if tabelle is not None:
        anzeige = len(erg["offen"]) + MAX_TRADES_ANZEIGE
        weggelassen = max(len(tabelle) - anzeige, 0)
        tabelle = tabelle.iloc[:anzeige]
    hinweis = (f"… {weggelassen} ältere Trades nicht angezeigt – alle Trades speichert --csv in einer eigenen Datei."
               if weggelassen else "")
    dollar_shorts = waehrung == "€" and any(p["richtung"] < 0 and waehrung_von(p["ticker"]) == "USD"
                                           for p in erg["trades"] + erg["offen"])
    regeln = (f"Regeln: Signal zum Schlusskurs, Einstieg zur Eröffnung des nächsten Handelstags nur bis zum Limit; "
              f"Ausstieg an Stop oder Ziel (bei beidem am selben Tag zählt der Stop), "
              f"{'' if ohne_zahlen else 'zum Schluss vor Quartalszahlen '}"
              f"oder nach {ZEITSTOPP_TAGE} Handelstagen; höchstens {MAX_POSITIONEN} Positionen"
              f"{f', {MAX_SHORTS} Shorts' if einst.mit_short else ''} und "
              f"{MAX_GESAMTRISIKO_PROZENT} % Gesamtrisiko; {de(einst.gebuehr)} {waehrung} Gebühr + "
              f"{prozent(SPREAD_PROZENT)} % Spread je Order; "
              f"{'Bruchteile von Aktien erlaubt' if einst.bruchstuecke else 'nur ganze Aktien'}. "
              f"{'Shorts ohne Leih-/Finanzierungskosten gerechnet' if einst.mit_short else ''}"
              f"{'; bei Shorts auf Dollar-Werte entsteht der Gewinn in $ – ihr Ausstiegskurs in € ist so umgerechnet, dass Einstieg − Ausstieg genau zum Ergebnis passt' if dollar_shorts else ''}"
              f"{'. ' if einst.mit_short else ''}"
              f"{'Ohne Quartalszahlen-Regel gerechnet (--ohne-zahlen). ' if ohne_zahlen else 'Termine im Rückblick sind die tatsächlichen, live können sie sich verschieben. '}"
              f"Simulation mit vergangenen Kursen – kein echtes Geld, keine Garantie für die Zukunft.")
    if ohne_zahlen_regel and not ohne_zahlen:
        regeln += f" Zahlen-Regel nicht angewandt für: {', '.join(ohne_zahlen_regel)} (keine Termine)."
    text = "\n".join(["", zusammenfassung[0], *("   " + z for z in zusammenfassung[1:])])
    if tabelle is not None:
        with pd.option_context("display.unicode.east_asian_width", True):
            text += "\n\n" + tabelle.to_string(index=False, formatters=TRADE_FORMATE, na_rep="–")
    if hinweis:
        text += "\n" + hinweis
    text += "\n" + regeln + "\n" + rueckschau_hinweis
    if not notebook:
        print(text)
        return

    def ergebnisfarbe(zeile):
        bg = "#c8e6c9" if zeile["Ergebnis"] > 0 else "#ffcdd2" if zeile["Ergebnis"] < 0 else ""
        return [f"background-color: {bg}; color: #1b1b1b; font-weight: bold;"
                if bg and s in ("Ergebnis", "Ergebnis %") else "" for s in zeile.index]

    reihen = [("Bot mit Lernen" if einst.lernen else "Bot", erg["verlauf"], "#2a78d6")]
    if erg["vergleich"] is not None:
        reihen.append(("Kaufen & Halten", erg["vergleich"], "#eb6834"))
    if ohne is not None:
        reihen.append(("Bot ohne Lernen", ohne["verlauf"], "#1baf7a"))
    teile = [absatz(zusammenfassung[0], "font-size: 1.15em; font-weight: bold; margin-top: 18px;")]
    teile += [absatz(z) for z in zusammenfassung[1:]]
    teile.append(depot_chart_svg(reihen, erg["start_wert"], waehrung))
    if tabelle is not None:
        teile.append('<div style="margin: 8px 0;">' + tabelle_als_html(tabelle, TRADE_FORMATE, ergebnisfarbe, 3, ("Strategie", "Grund"))
                     + "</div>")
    if hinweis:
        teile.append(absatz(hinweis, "font-size: 0.9em;"))
    teile.append(absatz(regeln, "font-size: 0.9em; opacity: 0.8;"))
    teile.append(absatz(rueckschau_hinweis, "font-size: 0.9em; opacity: 0.8;"))
    zeige("".join(teile), text)

def speichere_csv(tabelle, datei):
    # Semikolon + Dezimalkomma, damit ein deutsches Excel die Datei direkt richtig öffnet
    ganze = [s for s in ("Stück",) if s in tabelle and (tabelle[s].dropna() % 1 == 0).all()]
    try:
        tabelle.astype({s: "Int64" for s in ganze}).to_csv(datei, index=False, sep=";", decimal=",",
                                                          encoding="utf-8-sig", float_format="%.2f")
    except OSError as e:
        print(f"❌ CSV konnte nicht gespeichert werden ({e.strerror or e}): {os.path.abspath(datei)} "
              "– ist die Datei noch in Excel geöffnet oder der Ordner falsch?")
        return
    print(f"💾 Gespeichert: {os.path.abspath(datei)}")

RUECKSCHAU = ("⚠️ Rückblick mit deiner heutigen Watchlist: Du hast diese Aktien heute ausgewählt – oft, weil sie "
              "stark gestiegen sind. Im Rückblick sehen Kauf-Strategien und Kaufen & Halten deshalb besser aus und "
              "Short-Strategien schlechter, als sie in Zukunft sein müssen.")


# ----------------------------------------------------------------------------
# Papier-Depot: der Bot handelt ab dem ersten Lauf vorwärts mit virtuellem Geld (gleiche Regeln wie im Rückblick).
# Jeder Lauf rechnet nur die neuen fertigen Kurstage seit dem letzten Lauf – verpasste Tage werden nachgeholt,
# und jede Entscheidung nutzt nur Kurse, die es zu diesem Zeitpunkt schon gab.
# ----------------------------------------------------------------------------
PAPIER_VERSION = 1
POSITION_FELDER = ("ticker", "richtung", "strategie", "stueck", "einstieg_usd", "einsatz_je_stueck", "stop", "ziel",
                   "kauf_tag", "kosten", "erloes", "risiko_eur")
TRADE_FELDER = POSITION_FELDER + ("verkauf_tag", "verkauf_preis", "grund")
AUFTRAG_FELDER = ("ticker", "richtung", "strategie", "stop", "ziel", "limit", "crv")

def in_colab():
    return "google.colab" in sys.modules or "COLAB_RELEASE_TAG" in os.environ

def papier_pfad(wert):
    """(Datei, Fehlertext). In Colab liegt das Papier-Depot in Google Drive, damit es nach dem Schließen bleibt."""
    pfad = os.path.expanduser(PAPIER_DATEI if wert == "auto" else wert)
    if not in_colab() or os.path.isabs(pfad):
        return os.path.abspath(pfad), None
    if not os.path.isdir("/content/drive/MyDrive"):
        try:
            from google.colab import drive
            drive.mount("/content/drive")
        except Exception:
            pass
    if not os.path.isdir("/content/drive/MyDrive"):
        return None, ("Google Drive ist nicht verbunden – das Papier-Depot wurde nicht gespeichert. In Colab vorher in "
                      "einer eigenen Zelle ausführen: from google.colab import drive; drive.mount('/content/drive')")
    return os.path.join(os.path.dirname(PAPIER_DATEI_COLAB), pfad), None

def lade_papier(pfad, neu_anlegen):
    """(Stand oder None, Fehlertext). Mit neu_anlegen wird ein vorhandener Stand als Kopie aufbewahrt."""
    if not os.path.exists(pfad):
        return None, None
    if neu_anlegen:
        basis = f"{os.path.splitext(pfad)[0]}_bis_{pd.Timestamp.now(tz=BERLIN):%Y-%m-%d_%H%M%S}"
        kopie, nr = basis + ".json", 2
        while os.path.exists(kopie):  # eine vorhandene Kopie nie überschreiben
            kopie, nr = f"{basis}_{nr}.json", nr + 1
        try:
            os.replace(pfad, kopie)
        except OSError as fehler:
            return None, f"Papier-Depot konnte nicht neu angelegt werden ({fehler})."
        return None, None
    try:
        with open(pfad, encoding="utf-8") as f:
            stand = json.load(f)
        if not isinstance(stand, dict) or stand.get("version") != PAPIER_VERSION:
            raise ValueError("unbekanntes Format")
        for feld in ("startkapital", "bargeld", "depotwert", "positionen", "auftraege", "trades", "verlauf", "anker"):
            if feld not in stand:
                raise ValueError(f"Feld {feld} fehlt")
        return stand, None
    except (OSError, ValueError) as fehler:
        return None, (f"Papier-Depot-Datei nicht lesbar ({fehler}) – sie bleibt unverändert. Mit --papier-neu "
                      f"neu anlegen.")

def speichere_papier(pfad, stand):
    """Schreibt erst in eine Hilfsdatei und ersetzt dann (bricht der Lauf ab, bleibt der alte Stand heil);
    der vorige Stand bleibt als .bak erhalten."""
    ordner = os.path.dirname(pfad)
    if ordner:
        os.makedirs(ordner, exist_ok=True)
    with open(pfad + ".tmp", "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)
    if os.path.exists(pfad):
        shutil.copyfile(pfad, pfad + ".bak")
    os.replace(pfad + ".tmp", pfad)

def iso(tag):
    return pd.Timestamp(tag).strftime("%Y-%m-%d")

def speicherbar(wert):
    if isinstance(wert, pd.Timestamp):
        return iso(wert)
    if isinstance(wert, (np.integer, np.bool_)):
        return int(wert)
    if isinstance(wert, np.floating):
        return float(wert)
    return wert

def neues_papier(einst):
    return {"version": PAPIER_VERSION, "startkapital": float(einst.konto), "angelegt": None, "bis": None,
            "bargeld": float(einst.konto), "depotwert": float(einst.konto), "gebuehren": 0.0, "spread": 0.0,
            "hoechstes_risiko": [0.0, 0], "positionen": [], "auftraege": [], "trades": [], "verlauf": [],
            "anker": {}, "letzter_lauf": None}

def als_tag(text, index):
    """Datum aus der Datei als Zeitpunkt passend zum Kursindex (mit oder ohne Zeitzone)."""
    tag = pd.Timestamp(text)
    return tag.tz_localize(index.tz) if index.tz is not None else tag

def anpassungsfaktor(d, anker):
    """(r, Index des letzten Ankertags): Verhältnis neuer zu gespeicherten Schlusskursen der letzten Kurstage.
    Hat Yahoo die Reihe seit dem letzten Lauf umgerechnet (Split, Dividende), sind alle im selben Verhältnis;
    weicht nur ein Kurs ab (nachträglich korrigiert), ist es keine Umrechnung: dann r = 1."""
    verhaeltnisse, letzter = [], None
    for tag, alt in anker or []:
        i = d["pos"].get(als_tag(tag, d["idx"]))
        if i is not None and alt > 0 and d["C"][i] > 0:
            verhaeltnisse.append(d["C"][i] / alt)
            letzter = i
    if not verhaeltnisse:
        return 1, None
    r = float(np.median(verhaeltnisse))
    if not math.isfinite(r) or abs(r - 1) < 1e-6 or any(abs(v / r - 1) > 1e-4 for v in verhaeltnisse):
        return 1, None
    return r, letzter

def papier_fortschreiben(stand, daten, pausen, einst, signal_ticker):
    """Rechnet das Papier-Depot bis zum letzten fertigen Kurstag weiter. Gibt (neuer Stand, Lauf, Bericht) zurück;
    Lauf ist None, wenn diesmal nicht weitergerechnet werden konnte (der Stand bleibt dann unverändert)."""
    bericht = {"neu": stand is None, "anpassungen": [], "warnung": None, "nicht_ausgefuehrt": []}
    if stand is None:
        stand = neues_papier(einst)
    fehlen = [t for t in dict.fromkeys(x["ticker"] for x in stand["positionen"] + stand["auftraege"])
              if t not in daten]
    if fehlen:
        bericht["warnung"] = (f"Keine Kurse für {', '.join(fehlen)} – das Papier-Depot wurde diesmal nicht "
                              f"weitergerechnet (wird beim nächsten Lauf nachgeholt).")
        return stand, None, bericht
    index = next(iter(daten.values()))["idx"]
    lauf = {"bis": als_tag(stand["bis"], index) if stand["bis"] else None, "bargeld": stand["bargeld"],
            "depotwert": stand["depotwert"], "gebuehren": stand["gebuehren"], "spread": stand["spread"],
            "hoechstes_risiko": stand["hoechstes_risiko"],
            "positionen": [dict(p, kauf_tag=als_tag(p["kauf_tag"], daten[p["ticker"]]["idx"]))
                           for p in stand["positionen"]],
            "auftraege": [dict(a) for a in stand["auftraege"]]}
    for p in lauf["positionen"]:
        if p["kauf_tag"] not in daten[p["ticker"]]["pos"]:
            bericht["warnung"] = (f"Kaufdatum {iso(p['kauf_tag'])} von {p['ticker']} fehlt in den Kursdaten – das "
                                  f"Papier-Depot wurde diesmal nicht weitergerechnet.")
            return stand, None, bericht

    # Yahoo rechnet ältere Kurse nach Aktiensplits und Dividenden um. Gespeicherte Kurse (Einstieg, Stop, Ziel,
    # Limit) werden deshalb im selben Verhältnis angepasst; bei Splits auch die Stückzahl.
    positionen = {p["ticker"]: p for p in lauf["positionen"]}
    for t in sorted(set(positionen) | {a["ticker"] for a in lauf["auftraege"]}):
        d = daten[t]
        r, i = anpassungsfaktor(d, stand["anker"].get(t))
        if r == 1:
            continue
        for a in lauf["auftraege"]:
            if a["ticker"] == t:
                a["stop"], a["ziel"], a["limit"] = a["stop"] * r, a["ziel"] * r, a["limit"] * r
        p = positionen.get(t)
        if p is None:
            continue
        fx = d["FX"][i]
        vorher = positionswert(p, d["C"][i] / r, fx)
        split = abs(1 - r) > 0.15  # auch 5:4 (r = 0,8) und 6:5 sind Splits, Dividenden liegen weit darunter
        if split:
            p["stueck"] = round(p["stueck"] / r, 6)
            p["einsatz_je_stueck"] *= r  # gezahlter Betrag je neuer Aktie
        else:
            p["risiko_eur"] *= r  # Einsatz je Stück bleibt der gezahlte Kurs
        p["einstieg_usd"], p["stop"], p["ziel"] = p["einstieg_usd"] * r, p["stop"] * r, p["ziel"] * r
        ausgleich = vorher - positionswert(p, d["C"][i], fx)  # Depotwert bleibt gleich, Rest als Bargeld
        lauf["bargeld"] += ausgleich
        if split:
            bericht["anpassungen"].append(f"{t}: Aktiensplit berücksichtigt – jetzt "
                                             f"{de(p['stueck'], 2 if p['stueck'] % 1 else 0)} Stück")
        elif abs(ausgleich) >= 0.01:
            bericht["anpassungen"].append(f"{t}: Dividende bzw. Kursanpassung verrechnet ({de(ausgleich, 2, True)} €)")

    erg = simuliere_depot(daten, pausen, einst, einst.lernen, zustand=lauf, signal_ticker=signal_ticker)
    if erg is None:
        bericht["warnung"] = "Keine fertigen Kurstage – das Papier-Depot wurde diesmal nicht weitergerechnet."
        return stand, None, bericht

    # Aufträge aus dem letzten Lauf, die am ersten neuen Handelstag ihres Tickers nicht ausgeführt wurden
    gekauft = {(p["ticker"], p["kauf_tag"]) for p in erg["positionen"] + erg["trades"]}
    for a in lauf["auftraege"]:
        d = daten[a["ticker"]]
        neu = [tag for tag in d["idx"][:d["n_fertig"]] if lauf["bis"] is not None and tag > lauf["bis"]]
        if neu and neu[0] in set(erg["tage"]) and (a["ticker"], neu[0]) not in gekauft:
            bericht["nicht_ausgefuehrt"].append(a["ticker"])

    neu = dict(stand)
    hoechstes = erg["hoechstes_risiko"]
    neu.update({
        "bis": iso(erg["bis"]), "bargeld": float(erg["bargeld"]), "depotwert": float(erg["depotwert"]),
        "gebuehren": float(erg["gebuehren"]), "spread": float(erg["spread"]),
        "hoechstes_risiko": [float(hoechstes[0]), int(hoechstes[1])],
        "positionen": [{k: speicherbar(p[k]) for k in POSITION_FELDER} for p in erg["positionen"]],
        "auftraege": [{k: speicherbar(a[k]) for k in AUFTRAG_FELDER} for a in erg["auftraege"]],
        "trades": stand["trades"] + [{k: speicherbar(p[k]) for k in TRADE_FELDER} for p in erg["trades"]],
        "verlauf": stand["verlauf"] + [[iso(tag), float(wert)] for tag, wert in erg["verlauf"]],
        "letzter_lauf": f"{pd.Timestamp.now(tz=BERLIN):%Y-%m-%d %H:%M}",
    })
    neu["angelegt"] = neu["angelegt"] or iso(erg["bis"])
    anker = {}
    for t in sorted({p["ticker"] for p in neu["positionen"]} | {a["ticker"] for a in neu["auftraege"]}):
        d = daten[t]
        bis = d["pos"][letzter_tag_bis(d, erg["bis"])]
        anker[t] = [[iso(d["idx"][i]), float(d["C"][i])] for i in range(max(bis - 4, 0), bis + 1)]
    neu["anker"] = anker
    return neu, erg, bericht

def papier_ansicht(stand, erg):
    """Positionen und Trades für die Trade-Tabelle (Datumsangaben als Zeitpunkte)."""
    trades = [dict(p, kauf_tag=pd.Timestamp(p["kauf_tag"]), verkauf_tag=pd.Timestamp(p["verkauf_tag"]))
              for p in stand["trades"]]
    offen = erg["positionen"] if erg is not None else [
        dict(p, kauf_tag=pd.Timestamp(p["kauf_tag"]), wert=math.nan, kurs_jetzt=math.nan, tage="?")
        for p in stand["positionen"]]
    return {"offen": offen, "trades": trades}

def papier_vergleich(stand, markt, fx):
    """Nasdaq-100 (QQQ) seit dem Start des Papier-Depots, umgerechnet in € und auf das Startkapital skaliert."""
    if markt is None or not stand["verlauf"]:
        return None
    d = markt
    kurse = pd.Series(d["C"][:d["n_fertig"]], index=d["idx"][:d["n_fertig"]])
    if fx is not None:
        kurse = kurse / kurs_umrechner(fx, kurse.index)
    tage = [als_tag(t, d["idx"]) for t, _ in stand["verlauf"]]
    werte = kurse.reindex(kurse.index.union(tage)).ffill().reindex(tage)
    if werte.isna().any() or not werte.iloc[0] > 0:
        return None
    return pd.Series(stand["startkapital"] * werte.to_numpy() / werte.iloc[0], index=pd.DatetimeIndex(tage))

def eroeffnung_vorbei(auftraege, termine):
    """Ist die Eröffnung, zu der die Aufträge ausgeführt werden, jetzt schon vorbei (Lauf während der Börsenzeit)?"""
    for a in auftraege:
        t, tag = a["ticker"], termine[a["ticker"]]
        if ist_krypto(t):
            start = pd.Timestamp(tag.date(), tz="UTC")
        elif waehrung_von(t) == "USD":
            start = pd.Timestamp(f"{tag:%Y-%m-%d} 09:30", tz=NY)
        else:
            start = pd.Timestamp(f"{tag:%Y-%m-%d} 09:00", tz=BERLIN)
        if pd.Timestamp.now(tz="UTC") >= start:
            return True
    return False

def papier_texte(stand, erg, bericht, pfad, einst, waehrung, vergleich, fx_heute, name_von):
    """Überschrift, Zusammenfassung und Hinweise des Papier-Depots als Textzeilen."""
    start = pd.Timestamp(stand["angelegt"]) if stand["angelegt"] else None
    kopf = (f"📒 PAPIER-DEPOT · Vorwärtstest seit {start:%d.%m.%Y} mit {de(stand['startkapital'], 0)} {waehrung}"
            if start is not None else "📒 PAPIER-DEPOT")
    zeilen = []
    if bericht["warnung"]:
        zeilen.append(f"⚠️ {bericht['warnung']}")
    if bericht["neu"] and erg is not None and einst.papier_neu:
        zeilen.append("Mit --papier-neu neu angefangen – beim nächsten Lauf --papier-neu wieder weglassen, sonst beginnt "
                      "das Depot jedes Mal von vorn (ein vorheriger Stand bleibt jeweils als Kopie mit Datum im selben "
                      "Ordner).")
    if bericht["neu"] and erg is not None:
        zeilen.append(f"Neu angelegt mit {de(stand['startkapital'], 0)} {waehrung}. Ab jetzt handelt der Bot hier "
                      f"vorwärts nach seinen Regeln – jede Entscheidung nur mit Kursen, die es da schon gab. Starte "
                      f"ihn jeden Börsentag einmal (am besten abends nach 22:15 Uhr); verpasste Tage holt er nach.")
    wert = stand["depotwert"]
    rendite = (wert / stand["startkapital"] - 1) * 100
    offen = erg["positionen"] if erg is not None else stand["positionen"]
    risiko = erg["offenes_risiko"] if erg is not None else None
    zeilen.append(f"Depotwert am {pd.Timestamp(stand['bis']):%d.%m.%Y}: {de(wert)} {waehrung} ({de(rendite, 1, True)} %)"
                  f" · davon frei: {de(stand['bargeld'])} {waehrung} · {len(offen)}/{MAX_POSITIONEN} Positionen"
                  + (f", offenes Risiko {de(risiko, 1)} %" if risiko is not None else ""))
    if vergleich is not None and len(vergleich) > 1:
        zeilen.append(f"Zum Vergleich Nasdaq-100 (QQQ) im selben Zeitraum: {de(vergleich.iloc[-1])} {waehrung} "
                      f"({de((vergleich.iloc[-1] / stand['startkapital'] - 1) * 100, 1, True)} %)")
    if erg is not None and not bericht["neu"]:
        if erg["tage"]:
            von, bis = erg["tage"][0], erg["tage"][-1]
            zeitraum = f"am {bis:%d.%m.}" if von == bis else f"vom {von:%d.%m.} bis {bis:%d.%m.}"
            teile = []
            neu_rein = [p for p in erg["positionen"] + erg["trades"] if p["kauf_tag"] in set(erg["tage"])]
            if neu_rein:
                teile.append("eingestiegen: " + ", ".join(
                    f"{p['ticker']} ({'Long' if p['richtung'] > 0 else 'Short'}, {de(p['stueck'], 2 if p['stueck'] % 1 else 0)} "
                    f"Stück zu {de(p['einsatz_je_stueck'])} {waehrung})" for p in neu_rein))
            if erg["trades"]:
                teile.append("ausgestiegen: " + ", ".join(
                    f"{p['ticker']} ({p['grund']}, {de(p['erloes'] - p['kosten'], 2, True)} {waehrung})"
                    for p in erg["trades"]))
            if bericht["nicht_ausgefuehrt"]:
                teile.append("nicht ausgeführt (Limit nicht erreicht, Kurslücke oder kein Platz/Geld): "
                             + ", ".join(bericht["nicht_ausgefuehrt"]))
            zeilen.append(f"Neu {zeitraum}: " + ("; ".join(teile) if teile else "keine Käufe oder Verkäufe") + ".")
        else:
            zeilen.append(f"Seit dem letzten Lauf gibt es keinen neuen fertigen Kurstag – nichts zu tun "
                          f"(Stand {pd.Timestamp(stand['bis']):%d.%m.%Y}).")
    zeilen += bericht["anpassungen"]
    trades = stand["trades"]
    if trades:
        gewinner = sum(1 for p in trades if p["erloes"] > p["kosten"])
        summe = sum(p["erloes"] - p["kosten"] for p in trades)
        werte = pd.Series([w for _, w in stand["verlauf"]])
        rueckgang = float(((werte.cummax() - werte) / werte.cummax()).max() * 100) if len(werte) else 0.0
        zeilen.append(f"Abgeschlossene Trades: {len(trades)} · Gewinner: {gewinner} ({de(gewinner / len(trades) * 100, 0)} %)"
                      f" · Summe {de(summe, 2, True)} {waehrung} · größter Rückgang {de(rueckgang, 1)} % · Kosten: "
                      f"Gebühren {de(stand['gebuehren'])} {waehrung} + Spread ca. {de(stand['spread'])} {waehrung}")
    auftraege = stand["auftraege"]
    if auftraege:
        def kurs(t, wert):
            return wert / (fx_heute if waehrung_von(t) == "USD" and fx_heute else 1)
        bis = pd.Timestamp(stand["bis"])
        termine = {a["ticker"]: bis + handelstag(a["ticker"]) for a in auftraege}
        erster = min(termine.values())
        zeilen.append(f"Aufträge für {datum(erster)} (zur Eröffnung, nur bis zum Limit; die Stückzahl ergibt sich erst "
                      f"beim Kauf aus Depotwert, Risiko und freiem Geld): " + " · ".join(
                          f"{'🟢' if a['richtung'] > 0 else '🔴'} {a['ticker']} {name_von(a['strategie'])} "
                          f"Limit {de(kurs(a['ticker'], a['limit']))}, Stop {de(kurs(a['ticker'], a['stop']))}, "
                          f"Ziel {de(kurs(a['ticker'], a['ziel']))} {waehrung}"
                          + (f" (am {datum(termine[a['ticker']])})" if termine[a["ticker"]] != erster else "")
                          for a in auftraege))
        if erg is not None and eroeffnung_vorbei(auftraege, termine):
            zeilen.append(f"Die Eröffnung am {datum(erster)} ist schon gelaufen: Das Papier-Depot bucht einen Tag erst, "
                          f"wenn er für alle Werte fertig ist – also beim nächsten Lauf nach Börsenschluss (US-Werte "
                          f"nach 22:15 Uhr, mit Krypto auf der Liste nach 2:00 Uhr).")
        zeilen.append("Die Aufträge stammen vom letzten fertigen Kurstag und berücksichtigen die offenen Positionen und "
                      "das Geld des Papier-Depots – sie können deshalb vom Handelsplan oben (für ein leeres Konto) "
                      "abweichen.")
    elif erg is not None:
        zeilen.append("Keine Aufträge für den nächsten Handelstag.")
    ort = "Google Drive › MyDrive › swing_scanner › papier_depot.json" if pfad == PAPIER_DATEI_COLAB else pfad
    zeilen.append(f"Gespeichert in: {ort} (neu anfangen mit --papier-neu, der alte Stand bleibt als Kopie erhalten). "
                  f"Simulation mit echten Kursen, ohne echtes Geld – Ausführung zur Eröffnung bzw. am Stop/Ziel, "
                  f"{de(einst.gebuehr)} {waehrung} Gebühr + {prozent(SPREAD_PROZENT)} % Spread je Order.")
    return kopf, zeilen

def zeige_papier(stand, erg, bericht, pfad, einst, waehrung, notebook, vergleich, fx_heute):
    kopf, zeilen = papier_texte(stand, erg, bericht, pfad, einst, waehrung, vergleich, fx_heute, strategie_name)
    tabelle = trade_tabelle(papier_ansicht(stand, erg))
    weggelassen = 0
    if tabelle is not None:
        anzeige = len(stand["positionen"]) + MAX_TRADES_ANZEIGE
        weggelassen = max(len(tabelle) - anzeige, 0)
        tabelle = tabelle.iloc[:anzeige]
    hinweis = f"… {weggelassen} ältere Trades nicht angezeigt (alle stehen in der Datei)." if weggelassen else ""
    text = "\n".join(["", kopf, *("   " + z for z in zeilen)])
    if tabelle is not None:
        with pd.option_context("display.unicode.east_asian_width", True):
            text += "\n\n" + tabelle.to_string(index=False, formatters=TRADE_FORMATE, na_rep="–")
    if hinweis:
        text += "\n" + hinweis
    if not notebook:
        print(text)
        return

    def ergebnisfarbe(zeile):
        bg = "#c8e6c9" if zeile["Ergebnis"] > 0 else "#ffcdd2" if zeile["Ergebnis"] < 0 else ""
        return [f"background-color: {bg}; color: #1b1b1b; font-weight: bold;"
                if bg and s in ("Ergebnis", "Ergebnis %") else "" for s in zeile.index]

    teile = [absatz(kopf, "font-size: 1.15em; font-weight: bold; margin-top: 18px;")]
    teile += [absatz(z) for z in zeilen]
    if len(stand["verlauf"]) > 1:
        verlauf = pd.Series([w for _, w in stand["verlauf"]],
                            index=pd.DatetimeIndex([pd.Timestamp(t) for t, _ in stand["verlauf"]]))
        reihen = [("Papier-Depot", verlauf, "#2a78d6")]
        if vergleich is not None and len(vergleich) == len(verlauf):
            reihen.append(("Nasdaq-100 (QQQ)", pd.Series(vergleich.to_numpy(), index=verlauf.index), "#eb6834"))
        teile.append(depot_chart_svg(reihen, stand["startkapital"], waehrung))
    if tabelle is not None:
        teile.append('<div style="margin: 8px 0;">' + tabelle_als_html(tabelle, TRADE_FORMATE, ergebnisfarbe, 3,
                                                                       ("Strategie", "Grund")) + "</div>")
    if hinweis:
        teile.append(absatz(hinweis, "font-size: 0.9em;"))
    zeige("".join(teile), text)


def papier_lauf(datei, stand, fehler, daten, extra, roh, fx, fx_je_ticker, zusatz, pausen, einst, waehrung, notebook,
                markt):
    """Papier-Depot fortschreiben, anzeigen und speichern. Gibt den neuen Stand zurück (oder None)."""
    def nur_hinweis(text):
        print(f"\n📒 PAPIER-DEPOT\n⚠️ {text}")
        return None
    if fehler:
        return nur_hinweis(fehler)
    if fx is None:
        return nur_hinweis("Ohne Euro-Wechselkurs wird das Papier-Depot diesmal nicht weitergerechnet (es führt alle "
                           "Beträge in €) – beim nächsten Lauf wird nachgeholt.")
    daten_p = dict(daten)
    for t in extra:
        if t in roh:
            daten_p[t] = bereite_vor(t, roh[t], fx_je_ticker.get(t), zusatz.get(t, {}).get("zahlen"), einst)
    # Quartalszahlen-Termine: Klappt die Abfrage diesmal nicht (Yahoo-Limit, Formatfehler), gelten die zuletzt
    # gespeicherten – sonst hielte das Papier-Depot eine Position unbemerkt über die Zahlen
    gemerkt = (stand or {}).get("termine")
    gemerkt = dict(gemerkt) if isinstance(gemerkt, dict) else {}
    if not einst.ohne_zahlen:
        for t, d in list(daten_p.items()):
            if d["termine"] is None and gemerkt.get(t):
                daten_p[t] = bereite_vor(t, roh[t], fx_je_ticker.get(t),
                                         pd.DataFrame(index=pd.to_datetime(gemerkt[t], utc=True)), einst)
    neu, erg, bericht = papier_fortschreiben(stand, daten_p, pausen, einst, set(daten))
    if erg is not None:
        grenze = pd.Timestamp.now(tz=NY) - pd.Timedelta(days=120)
        for t, d in daten_p.items():
            if d["termine"] is not None:
                gemerkt[t] = [x.isoformat() for x in d["termine"] if x >= grenze]
        neu["termine"] = gemerkt
        try:
            speichere_papier(datei, neu)
        except OSError as problem:
            bericht["warnung"] = f"Speichern fehlgeschlagen ({problem}) – dieser Lauf zählt nicht."
            neu, erg = stand, None
    if neu is None or neu["bis"] is None:
        return nur_hinweis(bericht["warnung"] or "Das Papier-Depot konnte nicht angelegt werden.")
    vergleich = papier_vergleich(neu, markt, fx) if erg is not None else None
    zeige_papier(neu, erg, bericht, datei, einst, waehrung, notebook, vergleich, float(fx.iloc[-1]))
    return neu

def main():
    try:
        sys.stdout.reconfigure(errors="replace")  # Emojis -> '?' statt Absturz, wenn Windows in eine Datei umleitet
    except Exception:
        pass

    einst = lies_einstellungen()
    if FX_TICKER in einst.ticker_liste:
        einst.ticker_liste.remove(FX_TICKER)
        print(f"Hinweis: {FX_TICKER} ist der Euro-Wechselkurs und wird nur zum Umrechnen genutzt.")
    if not einst.ticker_liste:
        print("Keine Ticker angegeben.")
        return None

    papier_datei = papier_stand = papier_fehler = None
    if einst.papier:
        papier_datei, papier_fehler = papier_pfad(einst.papier)
        if papier_datei:
            papier_stand, papier_fehler = lade_papier(papier_datei, einst.papier_neu)

    print(f"🤖 Lade 5 Jahre Kurse für {len(einst.ticker_liste)} Ticker, Quartalszahlen-Termine und prüfe "
          f"{len(STRATEGIEN) if einst.mit_short else len(STRATEGIEN) // 2} Strategien ...")
    unterstuetzt = [t for t in einst.ticker_liste if waehrung_von(t)]
    # Ticker, die das Papier-Depot noch hält oder kaufen will, aber nicht (mehr) auf der Watchlist stehen
    papier_extra = []
    if papier_stand is not None:
        papier_extra = [t for t in dict.fromkeys(p["ticker"] for p in papier_stand["positionen"] + papier_stand["auftraege"])
                        if t not in unterstuetzt and waehrung_von(t)]
    frischer_yahoo_cache()
    with YahooRuhig(einst.debug) as sammler:
        extra = [x for x in (FX_TICKER, MARKT_TICKER) if x not in unterstuetzt + papier_extra]
        roh, gruende = lade_kurse(unterstuetzt + papier_extra + extra, sammler)
        termin_ticker = ([t for t in unterstuetzt + papier_extra if t in roh and hat_zahlen(t)]
                         if not einst.ohne_zahlen else [])
        # Termine zuerst für Ticker mit Signal holen – greift Yahoos Limit, fehlen sie eher bei den übrigen
        termin_ticker.sort(key=lambda t: not signal_zuletzt(roh[t], einst.mit_short))
        zusatz = hole_zusatzdaten(termin_ticker, [], sammler)
    fx_daten = roh.pop(FX_TICKER, None)
    fx = fx_daten["Close"] if fx_daten is not None else None
    markt_df = roh.get(MARKT_TICKER) if MARKT_TICKER in unterstuetzt + papier_extra else roh.pop(MARKT_TICKER, None)
    waehrung = "€" if fx is not None else "$"
    # US-Werte werden mit EUR/USD umgerechnet, Werte von Euro-Börsen nicht
    fx_je_ticker = {t: fx if waehrung_von(t) == "USD" else None for t in unterstuetzt + papier_extra}

    daten = {t: bereite_vor(t, roh[t], fx_je_ticker[t], zusatz.get(t, {}).get("zahlen"), einst)
             for t in unterstuetzt if t in roh}
    markt = bereite_vor(MARKT_TICKER, markt_df, None, None, einst) if markt_df is not None else None

    if not daten:
        verbindung = (fx_daten is None and markt_df is None) or any(
            g in (YAHOO_LIMIT, KEINE_VERBINDUNG) for g in gruende.values())
        print("\n❌ Für keinen Ticker gibt es auswertbare Kurse"
              + (" – meist keine Verbindung zu Yahoo oder Yahoo-Limit erreicht." if verbindung else ":"))
        for t in einst.ticker_liste:
            print(f"❌ {t}: {gruende.get(t, 'Währung nicht unterstützt – nur US- und Euro-Börsen')}")
        if verbindung:
            print("Internetverbindung prüfen oder in 1–2 Minuten erneut starten.")
        return None

    # Strategie-Tagebuch und Lernstand (nur abgeschlossene Kerzen)
    tagebuch = strategie_tagebuch(daten, einst)
    alle_tage = sorted(set().union(*(set(d["idx"][:d["n_fertig"]]) for d in daten.values())))
    pausen, stand = lernverlauf(tagebuch, alle_tage, einst)
    pausiert_heute = pausen[alle_tage[-1]] if alle_tage else frozenset()

    # Scanner für heute
    zeilen = []
    for t in einst.ticker_liste:
        if t not in fx_je_ticker:
            zeilen.append(fehler_zeile(t, "Währung nicht unterstützt – nur US- und Euro-Börsen"))
        elif t in daten:
            zeilen.append(scanner_zeile(t, daten[t], pausiert_heute, einst))
        else:
            zeilen.append(fehler_zeile(t, gruende.get(t, "keine Kursdaten")))
    if not any("_stand" in z for z in zeilen):
        for z in zeilen:
            print(f"❌ {z['Ticker']}: {z.get('_fehler', '')}")
        return None

    # Schlagzeilen nur für Ticker mit Signal (sie beeinflussen nur die Anzeige)
    news = {}
    mit_signal = [z["Ticker"] for z in zeilen if z.get("Signal") in (KAUFEN, SHORT, WARTEN)]
    if not einst.ohne_news and mit_signal:
        with YahooRuhig(einst.debug) as sammler:
            news_daten = hole_zusatzdaten([], mit_signal, sammler)
        stand_tag = max(z["_stand"] for z in zeilen if "_stand" in z)
        news = werte_news(news_daten, stand_tag, zeilen)
        for t, e in news_daten.items():
            zusatz.setdefault(t, {}).update({"news_info": e["news_info"]})
    for z in zeilen:
        z["News"] = news.get(z["Ticker"], {}).get("spalte", "")

    # Sortieren: Einstiegssignale nach CRV (wie im Depot), dann Warten, Hinweise, Beobachten, Fehler
    tabelle = pd.DataFrame(zeilen).reindex(columns=SPALTEN + ["_fehler"])
    tabelle["_prio"] = tabelle["Signal"].map(PRIORITAET)
    tabelle["_crv"] = tabelle["CRV"].fillna(-1e9)
    tabelle = tabelle.sort_values(["_prio", "_crv"], ascending=[True, False], kind="stable")
    reihenfolge = list(tabelle["Ticker"])
    tabelle = tabelle[SPALTEN].reset_index(drop=True)
    for spalte in ("Strategie", "Zahlen", "News"):
        tabelle[spalte] = tabelle[spalte].fillna("")

    fx_heute = float(fx.iloc[-1]) if fx is not None else None
    titel, zusammenfassung, hinweise = kopfzeilen(zeilen, einst, fx_heute, waehrung, markt, einst.ohne_zahlen)
    nach_ticker = {z["Ticker"]: z for z in zeilen}
    einstiege = [nach_ticker[t] for t in reihenfolge if nach_ticker[t].get("Signal") in (KAUFEN, SHORT)]
    # Handelsplan nach denselben Grenzen wie das Depot: Anzahl, Shorts, Gesamtrisiko und Geld (bestes CRV zuerst)
    plan, zu_klein, shorts, risiko_summe, geld_summe, mehr = [], [], 0, 0.0, 0.0, 0
    for z in einstiege:
        short = z["Signal"] == SHORT
        if not z["Stück"]:
            zu_klein.append(z["Ticker"])
        elif (len(plan) >= MAX_POSITIONEN or (short and shorts >= MAX_SHORTS)
                or risiko_summe + z["Risiko"] > einst.konto * MAX_GESAMTRISIKO_PROZENT / 100 + 0.005
                or geld_summe + z["Einsatz"] + einst.gebuehr > einst.konto):
            mehr += 1
        else:
            plan.append(handelsplan(z, len(plan) + 1, einst, waehrung))
            shorts += short
            risiko_summe += z["Risiko"]
            geld_summe += z["Einsatz"] + einst.gebuehr
    if zu_klein:
        plan.append(f"Für {', '.join(zu_klein)} ist mit deinem Konto nicht einmal 1 Stück möglich (Risiko je Trade "
                    f"bzw. höchstens {MAX_POSITION_PROZENT} % des Kontos je Position) – auslassen oder --bruchstuecke "
                    f"nutzen.")
    if mehr:
        plan.append(f"… {mehr} {'weiteres Signal' if mehr == 1 else 'weitere Signale'} nicht im Plan – laut Regel "
                    f"höchstens {MAX_POSITIONEN} Positionen gleichzeitig"
                    f"{f' (davon {MAX_SHORTS} Short)' if einst.mit_short else ''}, zusammen höchstens "
                    f"{MAX_GESAMTRISIKO_PROZENT} % Risiko und nicht mehr Geld als auf dem Konto.")
    schlagzeilen = []
    for t in reihenfolge:
        for s in news.get(t, {}).get("zeilen", []):
            ereignis = f" [{', '.join(s['ereignisse'])}]" if s["ereignisse"] else ""
            schlagzeilen.append(f"{t}{ereignis}: {s['titel']} ({s['quelle']}, {s['zeit']:%d.%m. %H:%M})")
    if schlagzeilen:
        schlagzeilen = [f"📰 SCHLAGZEILEN der letzten {NEWS_TAGE} Handelstage (nur Ticker mit Signal)"] + schlagzeilen[:10]
    notebook = im_notebook()
    zeige_scanner(tabelle, titel, zusammenfassung, hinweise, plan, schlagzeilen,
                  fusszeilen(zeilen, einst, waehrung, news, zusatz), tabellen_formate(einst), notebook)

    # Lern-Tabelle, Papier-Depot (vorwärts) und virtuelles Depot (Rückblick)
    zeige_lernen(stand, einst, waehrung, notebook, RUECKSCHAU)
    papier = None
    if einst.papier:
        papier = papier_lauf(papier_datei, papier_stand, papier_fehler, daten, papier_extra, roh, fx, fx_je_ticker,
                             zusatz, pausen, einst, waehrung, notebook, markt)
    depot = ohne = None
    if einst.rueckblick > 0:
        depot = simuliere_depot(daten, pausen, einst, einst.lernen)
        if einst.lernen:
            ohne = simuliere_depot(daten, pausen, einst, False)
        if depot is not None:
            ohne_regel = [t for t, d in daten.items() if d["termine"] is None and hat_zahlen(t)]
            zeige_depot(depot, ohne, einst, waehrung, notebook, ohne_regel, RUECKSCHAU, einst.ohne_zahlen)

    if einst.csv:
        speichere_csv(tabelle, einst.csv)
        trades = trade_tabelle(depot) if depot is not None else None
        if trades is not None:
            name, endung = os.path.splitext(einst.csv)
            speichere_csv(trades, f"{name}_trades{endung or '.csv'}")
    return {"scanner": tabelle, "depot": depot, "depot_ohne_lernen": ohne, "tagebuch": tagebuch, "lernstand": stand,
            "papier": papier}

if __name__ == "__main__":
    # Unter %run in Colab/Jupyter stehen die Ergebnisse danach als 'ergebnis' zur Verfügung
    ergebnis = main()
