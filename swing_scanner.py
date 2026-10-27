"""Swing-Trading-Scanner mit Strategie-Tagebuch und virtuellem Depot.

Ablauf: Kurse (5 Jahre Tageskerzen) und Quartalszahlen-Termine von Yahoo laden, 8 Strategien (mit --mit-short
16) je Ticker prüfen, jede Strategie im Tagebuch gedanklich mithandeln lassen ("lernen"), daraus den Scanner für
heute und ein virtuelles Depot über die letzten Monate berechnen. Es werden keine echten Orders gesendet.
"""
import argparse
import contextlib
import datetime as dt
import html
import io
import json
import logging
import math
import os
import re
import shutil
import sys
import threading
import unicodedata
import time
import urllib.parse
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait
from statistics import NormalDist

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
MIT_SHORT = False           # auch auf fallende Kurse setzen (Short-Signale) – aus: alle 8 Short-Strategien haben im Test
                            # 2010–2026 im Schnitt Geld verloren (einschalten mit --mit-short)
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
MAX_JE_BRANCHE = 2              # höchstens so viele Positionen aus derselben Branche (nicht alles auf eine Karte)
# Branche je Ticker (grob nach GICS-Sektoren). Ticker, die hier fehlen, zählen als eigene Branche (keine Grenze).
BRANCHEN = {
    "Technologie": "NOW INTU CRWV NBIS IREN AAPL NVDA MSFT AMD PLTR ADBE CRM ORCL AVGO QCOM TXN INTC CSCO IBM SNOW "
                   "DDOG NET CRWD ZS PANW MU AMAT LRCX MRVL SMCI DELL ARM APP SHOP MSTR ASML TSM SAP",
    "Kommunikation": "GOOGL GOOG META NFLX ASTS ROKU DIS RBLX SPOT T VZ",
    "Konsum": "SE MELI AMZN TSLA HD NKE SBUX MCD ABNB DKNG RIVN BABA PDD LULU CMG",
    "Finanzen": "JPM SOFI PYPL COIN GS BAC V MA AFRM UPST HOOD MS WFC C BRK-B AXP",
    "Gesundheit": "LLY HIMS UNH JNJ PFE MRK ABBV NVO ISRG TMO",
    "Energie": "XOM CVX OXY COP SLB",
    "Basiskonsum": "COST KO PEP WMT CELH PG",
    "Industrie": "BA CAT GE RKLB UBER LMT RTX DE HON",
}
BRANCHE = {t: b for b, liste in BRANCHEN.items() for t in liste.split()}
MIN_EINSATZ = 25                 # kleinere Trades lohnen wegen der Gebühr nicht (in €)
ZEITSTOPP_TAGE = 20              # spätestens nach so vielen Handelstagen (inkl. Einstiegstag) aussteigen
ZAHLEN_SPERRE_TAGE = 3           # kein Einstieg, wenn Quartalszahlen in den nächsten 3 Handelstagen wirken
VOLA_TAGE = 20                   # Ziel-Chance (nur Info): Schwankung der täglichen Log-Renditen über 20 Tage
LIMIT_ATR = 0.5                  # Einstieg nur bis Schlusskurs ± 0,5 ATR (Limit-Order), höchstens halber Weg zum Ziel
# Stop und Ziel: weiter Stop, Ziel nicht weiter als der Stop – im Test 2010–2026 (84 Aktien) gut 55 % Treffer statt
# gut 45 %, dafür kleinere Gewinne je Treffer
STOP_TREND_ATR = 3               # Trend-Strategien: Stop 3 ATR vom Schlusskurs ...
ZIEL_TREND_ATR = 3               # ... und Ziel 3 ATR (weiter Stop, Ziel nicht weiter als der Stop: mehr Treffer)
STOP_GEGEN_ATR = 2.5             # Gegenbewegungs-Strategien (RSI-2, Gegenbewegung): Stop 2,5 ATR ...
ZIEL_GEGEN_ATR = 2               # ... und Ziel 2 ATR (kurze Rückkehr zur Mitte, Ziel näher als der Stop)
R_GRENZE = 3.0                   # ein einzelner Tagebuch-Trade zählt höchstens ±3 R
LERNEN_FENSTER = 60              # die letzten 60 gedachten Trades je Strategie zählen
LERNEN_MIN_TRADES = 20           # erst ab 20 Trades wird eine Strategie überhaupt pausiert
LERNEN_PAUSE_AB = -0.10          # Pause, wenn der Schnitt unter −0,1 R fällt
LERNEN_WIEDER_AB = 0.0           # wieder aktiv, sobald der Schnitt über 0 R steigt
LERNEN_LANG_MIN = 50             # ab so vielen Trades insgesamt muss eine Strategie im Schnitt im Plus sein
MARKTFILTER_TAGE = 200           # Marktfilter: Long nur über, Short nur unter der 200-Tage-Linie des Nasdaq-100
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
                                    "Stop −3 ATR, Ziel +3 ATR"},
    "abbruch_short":      {"name": "Abbruch", "richtung": -1, "art": "trend",
                           "regel": "Schluss unter dem 20-Tage-Tief mit 1,5-fachem Volumen, unter der 50-Tage-Linie. "
                                    "Stop +3 ATR, Ziel −3 ATR"},
    "rsi2_long":          {"name": "RSI-2-Rücksetzer", "richtung": 1, "art": "gegen",
                           "regel": "RSI(2) unter 10 über der 200-Tage-Linie (kurzer Rücksetzer im langen Aufwärtstrend). "
                                    "Stop −2,5 ATR, Ziel +2 ATR – braucht etwa 56 % Treffer"},
    "rsi2_short":         {"name": "RSI-2-Übertreibung", "richtung": -1, "art": "gegen",
                           "regel": "RSI(2) über 90 unter der 200-Tage-Linie (kurze Erholung im langen Abwärtstrend). "
                                    "Stop +2,5 ATR, Ziel −2 ATR – braucht etwa 56 % Treffer"},
    "gegenbewegung_long": {"name": "Gegenbewegung", "richtung": 1, "art": "gegen",
                           "regel": "RSI(14) unter 32 oder am unteren Bollinger-Band, über der 200-Tage-Linie, "
                                    "EMA 20 mindestens 1,2 ATR über dem Kurs. Stop −2,5 ATR, Ziel +2 ATR"},
    "rueckfall_short":    {"name": "Rückfall", "richtung": -1, "art": "gegen",
                           "regel": "RSI(14) über 70 oder am oberen Bollinger-Band, unter der 200-Tage-Linie, "
                                    "EMA 20 mindestens 1,2 ATR unter dem Kurs. Stop +2,5 ATR, Ziel −2 ATR"},
    "macd_long":          {"name": "MACD-Wende", "richtung": 1, "art": "trend",
                           "regel": "MACD kreuzt heute seine Signallinie nach oben, über der 50-Tage-Linie. "
                                    "Stop −3 ATR, Ziel +3 ATR"},
    "macd_short":         {"name": "MACD-Wende", "richtung": -1, "art": "trend",
                           "regel": "MACD kreuzt heute seine Signallinie nach unten, unter der 50-Tage-Linie. "
                                    "Stop +3 ATR, Ziel −3 ATR"},
    "ruecksetzer_long":   {"name": "Rücksetzer", "richtung": 1, "art": "trend",
                           "regel": "Kurs bis 0,5 ATR über der EMA 20, RSI(14) unter 60, über der 50-Tage-Linie. "
                                    "Stop −3 ATR, Ziel +3 ATR"},
    "erholung_short":     {"name": "Erholung", "richtung": -1, "art": "trend",
                           "regel": "Kurs bis 0,5 ATR unter der EMA 20, RSI(14) über 40, unter der 50-Tage-Linie. "
                                    "Stop +3 ATR, Ziel −3 ATR"},
    "squeeze_long":       {"name": "Squeeze-Ausbruch", "richtung": 1, "art": "trend",
                           "regel": "Bollinger-Bänder waren an einem der 5 Vortage so eng wie selten (unterste 15 % der "
                                    "letzten 120 Tage), heute erster Schluss über dem oberen Band, über der 50-Tage-Linie "
                                    "(Ausbruch nach ruhiger Phase). Stop −3 ATR, Ziel +3 ATR"},
    "squeeze_short":      {"name": "Squeeze-Abbruch", "richtung": -1, "art": "trend",
                           "regel": "Bollinger-Bänder waren an einem der 5 Vortage so eng wie selten (unterste 15 % der "
                                    "letzten 120 Tage), heute erster Schluss unter dem unteren Band, unter der "
                                    "50-Tage-Linie. Stop +3 ATR, Ziel −3 ATR"},
    "ema_kreuz_long":     {"name": "EMA-Kreuz", "richtung": 1, "art": "trend",
                           "regel": "EMA 9 kreuzt heute die EMA 21 nach oben (neuer Aufwärtstrend), über der "
                                    "50-Tage-Linie. Stop −3 ATR, Ziel +3 ATR"},
    "ema_kreuz_short":    {"name": "EMA-Kreuz", "richtung": -1, "art": "trend",
                           "regel": "EMA 9 kreuzt heute die EMA 21 nach unten (neuer Abwärtstrend), unter der "
                                    "50-Tage-Linie. Stop +3 ATR, Ziel −3 ATR"},
    "atr_ausbruch_long":  {"name": "ATR-Ausbruch", "richtung": 1, "art": "trend",
                           "regel": "Schluss erstmals mehr als 2 ATR über der EMA 20 (Keltner-Kanal – Bewegung größer "
                                    "als das normale Schwanken), über der 50-Tage-Linie. Stop −3 ATR, Ziel +3 ATR"},
    "atr_abbruch_short":  {"name": "ATR-Abbruch", "richtung": -1, "art": "trend",
                           "regel": "Schluss erstmals mehr als 2 ATR unter der EMA 20 (Keltner-Kanal), unter der "
                                    "50-Tage-Linie. Stop +3 ATR, Ziel −3 ATR"},
}
VORRANG = {k: i for i, k in enumerate(STRATEGIEN)}

def strategie_name(key):
    s = STRATEGIEN[key]
    return f"{s['name']}\u00a0{'↑' if s['richtung'] > 0 else '↓'}"  # geschütztes Leerzeichen: Pfeil bleibt am Namen

# Signale (Reihenfolge = Sortierung in der Tabelle)
KAUFEN = "🟢 KAUFEN"
SHORT = "🔴 SHORT"
WARTEN = "⏸ WARTEN"
SICHERN = "⚠️ ÜBERHITZT"  # nur Info – verkaufen danach war im Test schlechter
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
def zahl(text, zeige=None):
    """Erlaubt auch ein deutsches Komma und Einheiten, z. B. --risiko 1,5 oder 1 %"""
    try:
        return float(re.sub(r"[\s€%]", "", str(text)).replace(",", "."))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{zeige if zeige is not None else text}' ist keine Zahl")

def betrag(text):
    """Kontogröße; erlaubt auch Tausenderpunkte und Cent, z. B. --konto 10.000 oder 10.000,00 €"""
    s = re.sub(r"[€%]", "", str(text)).strip()
    m = re.fullmatch(r"(\d{1,3}(?:[.\s]\d{3})+)(?:,(\d*|-))?", s)
    if m:
        s = re.sub(r"[.\s]", "", m.group(1)) + ("." + m.group(2) if m.group(2) and m.group(2) != "-" else "")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+", s):
        s = s.replace(",", "")
    return zahl(s, text)

def ticker_aus_text(text):
    """'aapl, NFLX nflx' -> ['AAPL', 'NFLX'] (groß geschrieben, ohne Duplikate, Reihenfolge bleibt)"""
    liste = [t.upper() for t in re.split(r"[,;\s]+", text or "") if t]
    return list(dict.fromkeys(liste))

def lies_einstellungen():
    p = argparse.ArgumentParser(description="Swing-Trading-Scanner für deine Watchlist (Beträge in €)")
    p.add_argument("--ticker", help='z. B. "AAPL, NFLX, SOFI" (Standard: TICKER_LISTE im Skript)')
    p.add_argument("--konto", type=betrag, default=KONTO, help="Kontogröße / Startkapital in € (z. B. 10000)")
    p.add_argument("--risiko", type=zahl, default=RISIKO_PROZENT, help="Risiko pro Trade in %% des Kontos")
    p.add_argument("--mit-short", action="store_true",
                   help="auch Short-Signale (auf fallende Kurse setzen) – im Test im Schnitt mit Verlust, nicht empfohlen")
    p.add_argument("--ohne-short", action="store_true", help="keine Short-Signale (Standard)")
    p.add_argument("--ohne-lernen", action="store_true", help="schlecht laufende Strategien nicht pausieren")
    p.add_argument("--ohne-marktfilter", action="store_true",
                   help="Long und Short unabhängig vom Gesamtmarkt (Nasdaq-100 über/unter der 200-Tage-Linie)")
    p.add_argument("--ohne-news", action="store_true",
                   help="keine Schlagzeilen laden – dann auch keine Nachrichten-Regel (Quartalszahlen-Regel bleibt)")
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
    p.add_argument("--gehirn", nargs="?", const="gehirn", metavar="ORDNER",
                   help="Gehirn für Obsidian: Tagesnotiz, Trade-Tagebuch mit Lehren, Strategie- und Aktien-Seiten in "
                        "ORDNER (Standard: gehirn); liest dort 'Meine Regeln.md' (gesperrte Aktien, ausgeschaltete "
                        "Strategien)")
    p.add_argument("--nachricht", metavar="DATEI",
                   help="bei Kauf-Signalen eine kurze Nachricht (Handelsplan) in DATEI schreiben, z. B. für eine "
                        "Benachrichtigung aufs Handy; ohne Signal wird die Datei gelöscht")
    p.add_argument("--claude-depot", metavar="DATEI",
                   help="Claude-Depot (Versuch, nur mit --papier): startet als Kopie des Papier-Depots und rechnet mit "
                        "denselben Regeln weiter – nur ohne die Signale, die Claude rechtzeitig ausgelassen hat")
    p.add_argument("--claude-entscheidungen", metavar="DATEI",
                   help="Claudes Entscheidungen für das Claude-Depot: Kommentare aus dem GitHub-Thema als JSON "
                        "(holt der Workflow)")
    p.add_argument("--uebersicht", metavar="DATEI",
                   help="Daten für die Übersichtsseite (docs/index.html) als JSON in DATEI schreiben")
    p.add_argument("--live", metavar="DATEI",
                   help="nur Live-Vorschau: aktuelle Kurse (etwa 15 Minuten verzögert) und --papier und --claude-depot "
                        "nach denselben Regeln bis jetzt weitergerechnet (Käufe, Stop, Ziel) als JSON in DATEI – "
                        "speichert nichts sonst, endgültig bucht der normale Lauf mit den Schlusskursen")
    p.add_argument("--csv", metavar="DATEI", help="Ergebnis zusätzlich als CSV speichern (für Excel)")
    p.add_argument("--bericht", metavar="DATEI",
                   help="alles zusätzlich als Markdown-Bericht speichern (z. B. bericht/README.md – GitHub zeigt ihn an)")
    p.add_argument("--debug", action="store_true", help="Original-Meldungen von yfinance anzeigen")
    einst, unbekannt = p.parse_known_args()
    if unbekannt:
        print(f"Hinweis: unbekannte Angaben ignoriert: {' '.join(unbekannt)}")
        BERICHT_HINWEISE.append(f"Nicht verstanden und ignoriert: {' '.join(unbekannt)} – Schreibweise prüfen"
                                + (" (Variable OPTIONEN)" if os.environ.get("GITHUB_ACTIONS") else "") + ".")
    if not (0 < einst.konto < math.inf and 0 < einst.risiko < math.inf):
        p.error("--konto und --risiko müssen Zahlen größer als 0 sein")
    if not 0 <= einst.gebuehr < math.inf:
        p.error("--gebuehr muss 0 oder größer sein")
    if not 0 <= einst.rueckblick <= 18:
        p.error("--rueckblick muss zwischen 0 und 18 Monaten liegen")
    einst.mit_short = (MIT_SHORT or einst.mit_short) and not einst.ohne_short
    einst.lernen = not einst.ohne_lernen
    einst.sperre_ticker = frozenset()  # aus 'Meine Regeln' im Gehirn (--gehirn)
    einst.sperre_strategien = frozenset()
    einst.nachrichten_sperre, einst.nachrichten_tag = frozenset(), None  # Nachrichten-Regel (nur für den letzten Kurstag)
    einst.marktfilter = not einst.ohne_marktfilter
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

def fehlender_us_tag(zeilen, jetzt=None):
    """US-Handelstag, der bei Yahoo schon fertig sein müsste, aber bei keinem US-Wert dabei ist (sonst None).
    Yahoo liefert die Kerze eines Tages manchmal erst Stunden nach Börsenschluss – dann wären alle Signale einen Tag
    alt und der Kauftag im Handelsplan schon vorbei."""
    us = [z["_stand"] for z in zeilen if "_stand" in z and waehrung_von(z["Ticker"]) == "USD"
          and not ist_krypto(z["Ticker"])]
    if not us:
        return None
    jetzt = jetzt if jetzt is not None else pd.Timestamp.now(tz=NY)
    tag = pd.Timestamp(jetzt.date())
    if jetzt.time() < dt.time(16, 15):
        tag -= pd.Timedelta(days=1)
    erwartet = NYSE_TAG.rollback(tag)
    return erwartet if max(pd.Timestamp(s.date()) for s in us) < erwartet else None


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
            news = yf.Ticker(t).get_news(count=10)
            if not news and hasattr(yf, "Search"):
                # get_news liefert bei GitHub nur leere Listen (Yahoo antwortet dort mit 404) – die Suche geht noch
                try:
                    treffer = yf.Search(t, max_results=1, news_count=10).news or []
                    # nur Meldungen, zu denen Yahoo diese Aktie nennt (die Suche nach „NOW“ findet sonst jedes „now“)
                    news = [n for n in treffer if not isinstance(n, dict) or "relatedTickers" not in n
                            or t in (n.get("relatedTickers") or [])]
                except Exception as fehler:
                    if type(fehler).__name__ == "YFRateLimitError":
                        raise
                    e["news_info"] = f"nicht abrufbar (Suche: {type(fehler).__name__})"
                    return
            e["news"], e["news_info"] = news, "ok"
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
    (r"\b(to acquire|to be acquired|acquisition of|merger|takeover)\b"
     # „buyout“ ist auch eine Abfindung für Mitarbeiter („offers voluntary buyout to 60,000 employees“) – das zählt nicht
     r"|(?<!voluntary )(?<!employee )\bbuyouts?\b(?!.{0,40}\b(employees|workers|staff|retirees)\b)"
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
        link = str((c.get("clickThroughUrl") or {}).get("url") or (c.get("canonicalUrl") or {}).get("url") or a.get("link") or "")
        if titel and not pd.isna(zeit) and zeit >= ab_zeit:
            aus.append({"titel": titel, "zeit": zeit.tz_convert(BERLIN), "quelle": quelle,
                        "link": link if link.startswith(("https://", "http://")) else "",
                        "video": "VIDEO" in (str(c.get("contentType", "")).upper(), str(a.get("type", "")).upper())})
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

UEBERSETZER = "https://api.mymemory.translated.net/get"  # kostenlos, ohne Anmeldung bis 5000 Zeichen am Tag

def _mehrzahl_verb(verb):
    """'jumps' -> 'jump' für 'Tesla shares jump': mit Verb in der Einzahl liest der Übersetzer 'shares' als 'teilt'."""
    unregelmaessig = {"is": "are", "was": "were", "has": "have", "does": "do"}
    if verb.lower() in unregelmaessig:
        return unregelmaessig[verb.lower()]
    if re.search(r"[^aeiou]ies$", verb):
        return verb[:-3] + "y"
    return verb[:-2] if re.search(r"(?:ss|sh|ch|x|z|o)es$", verb) else verb[:-1]

# Börsen-Ausdrücke, die der kostenlose Übersetzer oft falsch versteht ("Loads Up On" wurde zu "belastet" statt "kauft
# viel"): vor dem Übersetzen in einfaches Englisch umschreiben. Nur für die Anzeige – die Nachrichten-Regel liest das Original.
_WERT = r"(?:\S+ ){0,3}(?:estimates|expectations|forecasts?|views|consensus)\b"
KLARTEXT = [(re.compile(m, re.I), e) for m, e in (
    (r"\bloads up on\b", "buys a lot of"), (r"\bloaded up on\b", "bought a lot of"),
    (r"\bloading up on\b", "buying a lot of"), (r"\bload up on\b", "buy a lot of"),
    (r"\btrims\b(?= (?:its |his |her |their |a )?(?:\S+ )?(?:stake|position|holding))", "reduces"),
    (r"\btrimmed\b(?= (?:its |his |her |their |a )?(?:\S+ )?(?:stake|position|holding))", "reduced"),
    (r"\b(?:beats|tops)\b(?= " + _WERT + ")", "exceeds"), (r"\b(?:topped)\b(?= " + _WERT + ")", "exceeded"),
    (r"\bmisses\b(?= " + _WERT + ")", "falls short of"), (r"\bmissed\b(?= " + _WERT + ")", "fell short of"),
    (r"\bguidance\b", "forecast"),
    (r"\bearnings season\b", "reporting season"), (r"\bearnings report\b", "quarterly report"),
    (r"\bearnings call\b", "conference call on the quarterly results"),
    (r"\b(reports?|reported|reporting|ahead of|before|after) earnings\b", r"\1 quarterly results"),
    (r"\bearnings(?=\s*(?:[:;,!?]|$| preview\b))", "quarterly results"),
    (r"\b([\w.]+)-worried (investors|traders|markets?|buyers)\b", r"\2 worried about \1"),
    (r"(?<!think )(?<!oil )(?<!storage )(?<!fuel )\btanks\b", "falls sharply"),
    (r"(?<!think )(?<!oil )(?<!storage )(?<!fuel )\btanked\b", "fell sharply"), (r"\btanking\b", "falling sharply"),
    (r"\b(shares|stocks) tank\b", r"\1 fall sharply"),
    (r"\bcraters\b", "falls sharply"), (r"\bcratered\b", "fell sharply"),
    (r"\bslides\b", "falls"), (r"\bslid\b", "fell"), (r"\bsheds\b", "loses"),
    (r"\bpops\b", "jumps"), (r"\bpopped\b", "jumped"),
    (r"\bbull case\b", "optimistic scenario"), (r"\bbear case\b", "pessimistic scenario"),
    (r"\bbullish\b", "optimistic"), (r"\bbearish\b", "pessimistic"),
    (r"(?<!rate )(?<!price )(?<!tax )(?<!tariff )\bhikes\b", "raises"), (r"\bhiked\b", "raised"),
    (r"\bsoars\b", "rises sharply"), (r"\bsoared\b", "rose sharply"), (r"\bsoaring\b", "rising sharply"),
    (r"\b(profit|earnings|revenue|sales) beat\b", r"better-than-expected \1"),
    # "stock" allein wurde zu "Lager": "Is X Stock a Buy?" -> "Is X a Buy?", "Tesla stock jumps" -> "Tesla shares jump"
    (r"\bstock (?=an? (?:buy|sell|bargain|steal)\b)", ""),
    (r"\bstock (?!(?:as|us|plus|minus|versus|this|thus|news|analysis|basis|bonus|status|focus|crisis|losses|sales|"
     r"prices|options|futures|picks|markets|exchanges|splits|buybacks|ratings|holdings|returns|investors|traders|"
     r"analysts)\b)(\w+s)\b", lambda m: "shares " + _mehrzahl_verb(m.group(1))),
    (r"\bstock\b(?! (?:market|exchange|split|options?|buyback|index|futures|picks?|price)\b)", "shares"),
    (r"\beyes\b(?= (?:a |an |the )?\S+(?: \S+)? (?:merger|deal|takeover|acquisition|ipo|listing|sale|bid)\b)", "is considering"),
)]
# ... und danach im Deutschen nachbessern, was der Übersetzer falsch eindeutscht (Firmennamen, Börsenwörter)
NACHBESSERN = [(re.compile(m), e) for m, e in (
    (r"\bPreisziel", "Kursziel"), (r"\bApfels?\b", "Apple"),
    (r"\bApfel([a-zäöüß])", lambda m: "Apple-" + m.group(1).upper()),  # "Apfelanteil" -> "Apple-Anteil"
    (r"\bMeta-Plattformen\b", "Meta Platforms"), (r"\bAst SpaceMobile\b", "AST SpaceMobile"),
    (r"\bTurbo-?Steuer", "TurboTax"), (r"\bHims & (?:ihre|ihr|ihren|ihrer)\b", "Hims & Hers"),
)]

def klartext(text):
    """Schlagzeile für den Übersetzer: Börsen-Ausdrücke aus KLARTEXT in einfaches Englisch umschreiben."""
    neu = text
    for muster, ersatz in KLARTEXT:
        neu = muster.sub(ersatz, neu)
    return neu[:1].upper() + neu[1:] if text[:1].isupper() else neu

def auf_deutsch(texte, zeitlimit=40):
    """Englische Schlagzeilen maschinell ins Deutsche übersetzen (für die Übersichtsseite).
    Gibt {englisch: deutsch} zurück. Was nicht klappt (Dienst nicht erreichbar, Tageslimit erreicht), fehlt einfach –
    die Seite zeigt dann das englische Original. Die Nachrichten-Regel wertet immer das Original."""
    fertig, start = {}, time.monotonic()
    for text in dict.fromkeys(t for t in texte if t):
        if time.monotonic() - start > zeitlimit:
            break
        try:
            anfrage = urllib.request.Request(UEBERSETZER + "?" + urllib.parse.urlencode({"q": klartext(text)[:450], "langpair": "en|de"}),
                                             headers={"User-Agent": "Swing-Bot (GitHub Actions)"})
            with urllib.request.urlopen(anfrage, timeout=10) as antwort:
                d = json.loads(antwort.read().decode("utf-8"))
        except Exception:
            break  # Dienst nicht erreichbar: nicht bei jeder Schlagzeile neu warten
        if not isinstance(d, dict) or not isinstance(d.get("responseData"), dict):
            break
        deutsch = str(d["responseData"].get("translatedText") or "").strip()
        if str(d.get("responseStatus")) != "200" or d.get("quotaFinished") or not deutsch or "MYMEMORY WARNING" in deutsch.upper():
            break
        deutsch = html.unescape(deutsch)
        for muster, ersatz in NACHBESSERN:
            deutsch = muster.sub(ersatz, deutsch)
        fertig[text] = deutsch
    return fertig

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
        stimmung = {"gut": 0, "schlecht": 0}  # Schlagzeilen mit guten bzw. schlechten Ereignissen für die Aktie (nur Info)
        for s in lesbar.get(t, []):
            ev = [] if s["video"] or anzahl.get(s["titel"], 0) > 1 else ereignisse(s["titel"], t)
            stimmung["gut"] += any(r > 0 for r, _ in ev)
            stimmung["schlecht"] += any(r < 0 for r, _ in ev)
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
        ergebnis[t] = {"spalte": spalte, "zeilen": zeilen[:2], "warnung": warnung, "warnende": warnende, "info": "ok",
                       "stimmung": stimmung}
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
    st, zt = STOP_TREND_ATR * atr, ZIEL_TREND_ATR * atr  # Trend: Abstand Stop / Ziel
    sg, zg = STOP_GEGEN_ATR * atr, ZIEL_GEGEN_ATR * atr  # Gegenbewegung: Abstand Stop / Ziel
    regeln = {
        "ausbruch_long": ((c > df['Hoch_20']) & viel_volumen & (c > sma50), c - st, c + zt),
        "abbruch_short": ((c < df['Tief_20']) & viel_volumen & (c < sma50), c + st, c - zt),
        "rsi2_long": ((df['RSI_2'] < 10) & (c > sma200), c - sg, c + zg),
        "rsi2_short": ((df['RSI_2'] > 90) & (c < sma200), c + sg, c - zg),
        "gegenbewegung_long": (ueberverkauft & (c > sma200) & (ema - c >= 1.2 * atr), c - sg, c + zg),
        "rueckfall_short": (ueberhitzt & (c < sma200) & (c - ema >= 1.2 * atr), c + sg, c - zg),
        "macd_long": (kreuzt_hoch & (c > sma50), c - st, c + zt),
        "macd_short": (kreuzt_runter & (c < sma50), c + st, c - zt),
        "ruecksetzer_long": ((c > ema) & (c - ema <= 0.5 * atr) & (rsi < 60) & (c > sma50), c - st, c + zt),
        "erholung_short": ((c < ema) & (ema - c <= 0.5 * atr) & (rsi > 40) & (c < sma50), c + st, c - zt),
        "squeeze_long": (squeeze_vorher & (c > oben) & (c.shift() <= oben.shift()) & (c > sma50),
                         c - st, c + zt),
        "squeeze_short": (squeeze_vorher & (c < unten) & (c.shift() >= unten.shift()) & (c < sma50),
                          c + st, c - zt),
        "ema_kreuz_long": ((ema9 > ema21) & (ema9.shift() <= ema21.shift()) & (c > sma50), c - st, c + zt),
        "ema_kreuz_short": ((ema9 < ema21) & (ema9.shift() >= ema21.shift()) & (c < sma50), c + st, c - zt),
        "atr_ausbruch_long": ((c > k_oben) & (c.shift() <= k_oben.shift()) & (c > sma50), c - st, c + zt),
        "atr_abbruch_short": ((c < k_unten) & (c.shift() >= k_unten.shift()) & (c < sma50), c + st, c - zt),
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
    Schluss ± 0,5 ATR, aber höchstens der halbe Weg vom Schluss zum Ziel (sonst bliebe zu wenig Gewinn bis zum Ziel).
    Liegt das Ziel näher als der Stop (CRV unter 1, hohe Trefferquote), sperrt das keine normalen Einstiege."""
    halb = kurs + (ziel - kurs) / 2
    return min(kurs + LIMIT_ATR * atr, halb) if r > 0 else max(kurs - LIMIT_ATR * atr, halb)

def ziel_chance(kurs, ziel, vola, tage=ZEITSTOPP_TAGE):
    """Ziel-Chance nach dem Black-Scholes-Modell (Optionsskript, nur zur Info – der Bot kauft nicht danach): Der Kurs
    schwankt zufällig (geometrische Brownsche Bewegung, ohne Zins, also ohne Vorteil für eine Richtung) mit der
    Tagesvolatilität 'vola'. Ergebnis: Wahrscheinlichkeit, dass er das Ziel innerhalb von 'tage' Handelstagen
    mindestens einmal berührt (Spiegelungsprinzip) – der Stop zählt dabei nicht. NaN, wenn unbekannt."""
    try:
        kurs, ziel, vola = float(kurs), float(ziel), float(vola)
        if not (kurs > 0 and ziel > 0 and vola > 0 and tage > 0) or ziel == kurs:
            return math.nan
    except (TypeError, ValueError):
        return math.nan
    r = 1 if ziel > kurs else -1  # Short: Ziel unter dem Kurs
    abstand = abs(math.log(ziel / kurs))
    drift = -r * vola ** 2 / 2  # Drift von r·ln(Kurs) je Tag
    s = vola * math.sqrt(tage)
    n = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))  # Standardnormalverteilung N(x)
    p = n((drift * tage - abstand) / s) + math.exp(2 * drift * abstand / vola ** 2) * n((-abstand - drift * tage) / s)
    return min(max(p, 0.0), 1.0)

CHANCE_STUFEN = (0.3, 0.4, 0.5)  # Gruppen der Selbstkontrolle: unter 30 %, 30–40 %, 40–50 %, ab 50 %

def chance_pruefung(tagebuch, daten):
    """Selbstkontrolle der Ziel-Chance an den gedachten Trades: je Gruppe (Ziel-Chance am Signaltag) die Zahl der
    Signale, die Ø vorhergesagte Chance, wie oft der Kurs das Ziel in den nächsten 20 Handelstagen wirklich berührt
    hat (der Stop zählt dabei nicht – genau das sagt die Formel voraus), dazu Trefferquote und Ø R der Trades. Es
    zählen nur Signale, nach denen die 20 Handelstage schon vorbei sind."""
    grenzen = (0.0,) + CHANCE_STUFEN + (1.01,)
    gruppen = [{"von": a, "bis": b, "p": [], "beruehrt": [], "R": []} for a, b in zip(grenzen, grenzen[1:])]
    for e in tagebuch:
        d = daten.get(e["ticker"])
        i = d["pos"].get(e["signal_tag"]) if d is not None and "VOLA" in d else None
        if i is None or e["strategie"] not in d["signale"] or i + ZEITSTOPP_TAGE >= d["n_fertig"]:
            continue
        ziel = d["signale"][e["strategie"]][2][i]
        chance = ziel_chance(d["C"][i], ziel, d["VOLA"][i])
        r = STRATEGIEN[e["strategie"]]["richtung"]
        fenster = r * (d["H"] if r > 0 else d["L"])[i + 1:i + 1 + ZEITSTOPP_TAGE]
        if not math.isfinite(chance) or not np.isfinite(fenster).any():
            continue
        g = next(g for g in gruppen if g["von"] <= chance < g["bis"])
        g["p"].append(chance)
        g["beruehrt"].append(np.nanmax(fenster) >= r * ziel)
        g["R"].append(e["R"])
    return [{"von": g["von"], "bis": g["bis"], "n": len(g["p"]), "chance": 100 * float(np.mean(g["p"])),
             "beruehrt": 100 * float(np.mean(g["beruehrt"])), "quote": 100 * float(np.mean(np.array(g["R"]) > 0)),
             "schnitt": float(np.mean(g["R"]))} for g in gruppen if g["p"]]

def chance_praxis(chance, gruppen, mindestens=30):
    """Wie oft der Kurs das Ziel bei Signalen mit ähnlicher Ziel-Chance (gleiche Gruppe der Selbstkontrolle) bisher
    wirklich berührt hat, in % – NaN, wenn die Gruppe weniger als 'mindestens' Signale hat."""
    for g in gruppen:
        if g["von"] <= chance < g["bis"] and g["n"] >= mindestens:
            return g["beruehrt"]
    return math.nan

def chance_gesamt(gruppen):
    """Alle Gruppen der Selbstkontrolle zusammen: Signale, Ø vorhergesagt, Ø berührt, Ø Abstand (in Prozentpunkten)."""
    n = sum(g["n"] for g in gruppen)
    if not n:
        return None
    mittel = lambda feld: sum(g[feld] * g["n"] for g in gruppen) / n
    return {"n": n, "chance": mittel("chance"), "beruehrt": mittel("beruehrt"),
            "abstand": sum(abs(g["beruehrt"] - g["chance"]) * g["n"] for g in gruppen) / n}

# Kerzen- und Chartmuster (Poster „Candlestick Patterns & Chart Patterns“, Lehrbücher „Traden lernen“ und „Forex
# Trading lernen“): nur zur Info mit Selbstkontrolle – als Kaufregel (bestätigen, warnen, vorziehen) und als
# variables Ziel haben sie im Test über 16 Jahre nicht geholfen (gehirn/Notizen/Gelernt – Muster und Lehrbücher.md).
KERZEN_NAMEN = {
    "bull": {"engulfing": "Bullish Engulfing", "hammer": "Hammer", "harami": "Bullish Harami",
             "piercing": "Piercing Line", "morning_star": "Morning Star", "three_soldiers": "Three White Soldiers"},
    "bear": {"engulfing": "Bearish Engulfing", "shooting_star": "Shooting Star", "hanging_man": "Hanging Man",
             "evening_star": "Evening Star", "dark_cloud": "Dark Cloud Cover", "three_crows": "Three Black Crows"},
}
AUSBRUCH_STRATEGIEN = ("ausbruch_long", "atr_ausbruch_long", "squeeze_long")  # Musterziel: Höhe nach oben verlängert

def kerzenmuster(df):
    """Bullische und bärische Kerzenmuster je Tag (nur aus Kursen bis zu diesem Tag): {"bull": {name: Bool-Array},
    "bear": {…}}. Hammer und Hanging Man nur nach einem Rückgang bzw. Anstieg in den 5 Tagen davor."""
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    body, spanne = (c - o).abs(), (h - l).replace(0, np.nan)
    oben, unten = h - np.maximum(o, c), np.minimum(o, c) - l
    gruen, rot = c > o, c < o
    rot1, gruen1 = rot.shift(1, fill_value=False), gruen.shift(1, fill_value=False)
    o1, c1, h1, l1, o2, c2 = o.shift(1), c.shift(1), h.shift(1), l.shift(1), o.shift(2), c.shift(2)
    body1, body2 = (c1 - o1).abs(), (c2 - o2).abs()
    lang1, lang2 = body1 >= 0.6 * (h1 - l1), body2 >= 0.6 * (h.shift(2) - l.shift(2))
    gefallen, gestiegen = c < c.shift(5), c > c.shift(5)
    klein = body <= 0.35 * spanne
    muster = {
        "bull": {"engulfing": rot1 & gruen & (o <= c1) & (c >= o1) & (body > body1),
                 "hammer": gefallen & klein & (unten >= 2 * body) & (oben <= 0.25 * spanne),
                 "harami": rot1 & lang1 & gruen & (o > c1) & (c < o1),
                 "piercing": rot1 & lang1 & gruen & (o < c1) & (c > (o1 + c1) / 2) & (c < o1),
                 "morning_star": (c2 < o2) & lang2 & (body1 <= 0.3 * body2) & gruen & (c > (o2 + c2) / 2),
                 "three_soldiers": gruen & gruen1 & gruen.shift(2, fill_value=False) & (c > c1) & (c1 > c2)
                                   & (o > o1) & (o1 > o2)},
        "bear": {"engulfing": gruen1 & rot & (o >= c1) & (c <= o1) & (body > body1),
                 "shooting_star": gestiegen & klein & (oben >= 2 * body) & (unten <= 0.25 * spanne),
                 "hanging_man": gestiegen & klein & (unten >= 2 * body) & (oben <= 0.25 * spanne),
                 "evening_star": (c2 > o2) & lang2 & (body1 <= 0.3 * body2) & rot & (c < (o2 + c2) / 2),
                 "dark_cloud": gruen1 & lang1 & rot & (o > c1) & (c < (o1 + c1) / 2) & (c > o1),
                 "three_crows": rot & rot1 & rot.shift(2, fill_value=False) & (c < c1) & (c1 < c2) & (o < o1)
                                & (o1 < o2)},
    }
    return {seite: {k: m.fillna(False).to_numpy(bool) for k, m in liste.items()} for seite, liste in muster.items()}

def doppelboden(df, links=5, rechts=5, fenster=80):
    """Doppelboden (W) wie auf dem Poster: zwei Tiefs (Wendepunkte mit je 5 Tagen links und rechts, erst nach diesen
    5 Tagen bekannt) höchstens 0,75 ATR auseinander, 10–80 Tage Abstand, beide das Tief der Gegend, Höhe mindestens
    2 ATR. Signal am ersten Schluss über der Nackenlinie (höchstes Hoch zwischen den Tiefs), höchstens 25 Tage nach dem
    zweiten Tief. Gibt (Bool-Array, Musterziel = Nackenlinie + Höhe) zurück."""
    h, l, c = df["High"].to_numpy(float), df["Low"].to_numpy(float), df["Close"].to_numpy(float)
    atr = df["ATR"].to_numpy(float)
    n = len(df)
    ok, ziel = np.zeros(n, bool), np.full(n, np.nan)
    bestaetigt = {}
    for p in range(links, n - rechts):
        if l[p] == l[p - links:p + rechts + 1].min():
            bestaetigt.setdefault(p + rechts, []).append(p)
    bekannt = []
    for i in range(1, n):
        bekannt += bestaetigt.get(i, [])
        if not bekannt or not np.isfinite(atr[i]) or i - bekannt[-1] > 25:
            continue
        p2 = bekannt[-1]
        for p1 in reversed(bekannt[:-1]):
            if p2 - p1 < 10:
                continue
            if p2 - p1 > fenster:
                break
            if abs(l[p1] - l[p2]) > 0.75 * atr[i]:
                continue
            boden = min(l[p1], l[p2])
            if l[max(0, p1 - 20):i + 1].min() < boden:
                continue
            nacken = h[p1:p2 + 1].max()
            if nacken - boden >= 2 * atr[i] and c[i] > nacken >= c[i - 1]:
                ok[i], ziel[i] = True, nacken + (nacken - boden)
            break
    return ok, ziel

def muster_am_tag(d, i):
    """Erkannte Kerzenmuster an Tag i: bullische am Tag oder am Tag davor, bärische am Tag selbst (Namen)."""
    k = d.get("KERZEN")
    if k is None or i is None:
        return {"bull": [], "bear": []}
    bull = [KERZEN_NAMEN["bull"][m] for m, a in k["bull"].items() if a[i] or (i >= 1 and a[i - 1])]
    bear = [KERZEN_NAMEN["bear"][m] for m, a in k["bear"].items() if a[i]]
    return {"bull": bull, "bear": bear}

def muster_gruppe(muster):
    """Gruppe der Selbstkontrolle: 'bear' hat Vorrang (Warnzeichen), dann 'bull', sonst 'keins'."""
    return "bear" if muster["bear"] else "bull" if muster["bull"] else "keins"

def musterziel(d, i, strategie):
    """Kursziel aus dem Chartmuster (nur Info, in Kurswährung) und seine Art – oder (NaN, None)."""
    if i is None or i < 21:
        return math.nan, None
    db = d.get("DBOD")
    if db is not None and db[0][i]:
        return float(db[1][i]), "Doppelboden (W): Nackenlinie + Höhe"
    if strategie in AUSBRUCH_STRATEGIEN:
        hoch, tief = np.nanmax(d["H"][i - 20:i]), np.nanmin(d["L"][i - 20:i])
        if np.isfinite(hoch) and np.isfinite(tief) and hoch > tief:
            return float(hoch + (hoch - tief)), "Ausbruch: Höhe der Seitwärtsphase nach oben verlängert"
    return math.nan, None

def muster_pruefung(tagebuch, daten):
    """Selbstkontrolle der Kerzenmuster an allen gedachten Kauf-Trades: je Gruppe (bärisches Muster am Signaltag,
    bullisches am Signaltag oder Tag davor, keins) Zahl, Trefferquote und Ø R."""
    gruppen = {g: [] for g in ("bull", "bear", "keins")}
    for e in tagebuch:
        d = daten.get(e["ticker"])
        if d is None or STRATEGIEN[e["strategie"]]["richtung"] < 0:
            continue
        i = d["pos"].get(e["signal_tag"])
        if i is not None:
            gruppen[muster_gruppe(muster_am_tag(d, i))].append(e["R"])
    return {g: {"n": len(r), "quote": 100 * float(np.mean(np.array(r) > 0)), "schnitt": float(np.mean(r))}
            for g, r in gruppen.items() if r}

def muster_praxis(gruppe, pruefung, mindestens=30):
    """Trefferquote der gedachten Trades in dieser Muster-Gruppe (NaN bei weniger als 'mindestens' Trades)."""
    g = pruefung.get(gruppe)
    return g["quote"] if g and g["n"] >= mindestens else math.nan

# Nachrichten-Stimmung je Signal (gute und schlechte Schlagzeilen der letzten Tage) – neben dem Übungsdepot gespeichert,
# damit die Lehren-Seite später prüfen kann, ob Signale mit guten Nachrichten wirklich besser laufen. Alte Schlagzeilen
# gibt es nicht, deshalb lässt sich das nur ab jetzt sammeln.
NACHRICHTEN_LOG = "nachrichten_log.json"

def nachrichten_log_lesen(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            daten = json.load(f)
        return [e for e in daten if isinstance(e, dict) and {"tag", "ticker", "gut", "schlecht"} <= set(e)]
    except (OSError, ValueError, TypeError):
        return []

def nachrichten_log_schreiben(pfad, zeilen):
    """Stimmung aller Ticker mit Strategie-Signal ergänzen (ein Eintrag je Tag und Ticker, ein neuer Lauf ersetzt ihn)."""
    neu = {(f"{z['_stand']:%Y-%m-%d}", z["Ticker"]): {"tag": f"{z['_stand']:%Y-%m-%d}", "ticker": z["Ticker"],
                                                      "strategie": z["_strategie"], "gut": int(z["_stimmung"]["gut"]),
                                                      "schlecht": int(z["_stimmung"]["schlecht"])}
           for z in zeilen if z.get("_strategie") and z.get("_stimmung") and "_stand" in z}
    if not neu:
        return
    alt = {(e["tag"], e["ticker"]): e for e in nachrichten_log_lesen(pfad)}
    alt.update(neu)
    eintraege = sorted(alt.values(), key=lambda e: (e["tag"], e["ticker"]))[-3000:]
    try:
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(eintraege, f, ensure_ascii=False, indent=1)
    except OSError as e:
        print(f"⚠️ Nachrichten-Stimmung nicht gespeichert: {e}")

def nachrichten_pruefung(log, tagebuch):
    """Selbstkontrolle der Nachrichten-Stimmung: gedachte Trades je Gruppe (mehr gute / mehr schlechte / gleich viele
    oder keine Schlagzeilen am Signaltag) mit Trefferquote und Ø R."""
    stimmung = {(e["tag"], e["ticker"]): e for e in log}
    gruppen = {"gut": [], "schlecht": [], "neutral": []}
    for e in tagebuch:
        s = stimmung.get((f"{e['signal_tag']:%Y-%m-%d}", e["ticker"]))
        if s is None or STRATEGIEN[e["strategie"]]["richtung"] < 0:
            continue
        g = "gut" if s["gut"] > s["schlecht"] else "schlecht" if s["schlecht"] > s["gut"] else "neutral"
        gruppen[g].append(e["R"])
    return {g: {"n": len(r), "quote": 100 * float(np.mean(np.array(r) > 0)), "schnitt": float(np.mean(r))}
            for g, r in gruppen.items() if r}

def markt_trend(markt_df):
    """Nasdaq-100 (QQQ) je Tag: 1 = Schluss über der 200-Tage-Linie, 0 = darunter, NaN = noch zu wenig Daten."""
    if markt_df is None or "Close" not in markt_df:
        return None
    c = markt_df["Close"]
    sma = c.rolling(MARKTFILTER_TAGE).mean()
    trend = (c > sma).astype(float).where(sma.notna())
    return trend if trend.notna().any() else None

def markt_vortag(trend, index):
    """Marktlage für jeden Tag des Index vom letzten Börsentag DAVOR – so sieht auch ein Euro-Wert (Schluss vor
    New York) nichts aus der Zukunft. NaN, wenn unbekannt (dann gilt kein Filter)."""
    vortag = pd.DatetimeIndex(index) - pd.Timedelta(days=1)
    if trend.index.tz is not None and vortag.tz is None:
        vortag = vortag.tz_localize(trend.index.tz)
    return trend.reindex(vortag, method="ffill").to_numpy(dtype=float)

def bereite_vor(ticker, df, fx, zahlen_df, einst, markt=None):
    """Alles, was Scanner, Tagebuch und Depot je Ticker brauchen, einmal als schnelle Listen/Arrays.
    markt: Marktlage (markt_trend) – Long-Strategien nur im Aufwärtsmarkt, Short-Strategien nur im Abwärtsmarkt."""
    df = calculate_indicators(df.copy())
    roh, ueberhitzt, ueberverkauft = strategie_signale(df, einst.mit_short)
    signale = roh
    if markt is not None and getattr(einst, "marktfilter", True):
        lage = markt_vortag(markt, df.index)
        lang_ok, short_ok = lage != 0, lage != 1  # unbekannte Marktlage (NaN) sperrt nichts
        signale = {k: (ok & (lang_ok if STRATEGIEN[k]["richtung"] > 0 else short_ok), stop, ziel)
                   for k, (ok, stop, ziel) in roh.items()}
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
        "signale": signale, "signale_roh": roh, "ueberhitzt": ueberhitzt, "ueberverkauft": ueberverkauft,
        "VOLA": np.log(df['Close'].where(df['Close'] > 0)).diff().rolling(VOLA_TAGE).std().to_numpy(dtype=float),
        "pos": {tag: i for i, tag in enumerate(df.index)},
        "termine": None,
    }
    d["KERZEN"] = kerzenmuster(df)  # nur Info (Selbstkontrolle auf der Lehren-Seite)
    d["DBOD"] = doppelboden(df)
    d["morgen"] = d["gesperrt"] = d["gerade"] = np.zeros(n, bool)
    if zahlen_df is not None:
        termine = zahlen_termine(zahlen_df)
        d["termine"] = termine
        d["morgen"], d["gesperrt"], d["gerade"], d["lang"], d["reak"] = zahlen_regeln(termine, df.index,
                                                                                      handelstag(ticker))
    return d

def signal_zuletzt(df, mit_short, markt=None):
    """Feuert am letzten Kurstag eine Strategie, die der Marktfilter erlaubt? (Die Signale hängen nicht von den
    Terminen ab.)"""
    try:
        df = calculate_indicators(df.copy())
        signale = strategie_signale(df, mit_short)[0]
        lage = markt_vortag(markt, df.index[-1:])[0] if markt is not None else np.nan
        return any(ok[-1] and lage != (0 if STRATEGIEN[k]["richtung"] > 0 else 1) for k, (ok, _, _) in signale.items())
    except Exception:
        return False

def kandidaten(d, i, pausiert=frozenset(), aus=frozenset()):
    """Welche Strategien feuern am Tag i (Signal zum Schlusskurs) und was ist die Entscheidung?
    Gibt (gewählte Strategie oder None, Grund fürs Warten oder None) zurück. Dieselbe Regel gilt für den
    Scanner und beide Depot-Läufe – mit und ohne Lernen unterscheiden sich nur durch die Pausen.
    'aus': Strategien, die du in 'Meine Regeln' ausgeschaltet hast (gelten immer, auch ohne Lernen)."""
    feuernd = [k for k, (ok, _, _) in d["signale"].items() if ok[i]]
    if not feuernd:
        return None, None
    if aus and all(k in aus for k in feuernd):
        return None, f"{strategie_name(feuernd[0])} – von dir ausgeschaltet (Meine Regeln)"
    feuernd = [k for k in feuernd if k not in aus]  # was du ausgeschaltet hast, zählt gar nicht (auch nicht als Widerspruch)
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
    60 Trades im Schnitt unter −0,1 R liegen (ab 20 Trades), wieder aktiv, sobald der Schnitt über 0 R ist.
    Außerdem: Ab 50 Trades insgesamt muss der Schnitt über die ganze Geschichte im Plus sein – eine Strategie, die
    auf dieser Watchlist bisher nach Kosten Geld verloren hat, handelt der Bot nicht."""
    fenster = {k: deque(maxlen=LERNEN_FENSTER) for k in STRATEGIEN}
    alle_r = {k: [] for k in STRATEGIEN}
    summe = {k: 0.0 for k in STRATEGIEN}
    pausiert, im_minus = set(), set()
    zeiger = 0
    pausen = {}
    for tag in tage:
        while zeiger < len(tagebuch) and tagebuch[zeiger]["ausstieg_tag"] <= tag:
            e = tagebuch[zeiger]
            fenster[e["strategie"]].append(e["R"])
            alle_r[e["strategie"]].append(e["R"])
            summe[e["strategie"]] += e["R"]
            zeiger += 1
        if einst.lernen:
            for k, f in fenster.items():
                n = len(f)
                schnitt = sum(f) / n if n else 0.0
                if k not in pausiert and n >= LERNEN_MIN_TRADES and schnitt < LERNEN_PAUSE_AB:
                    pausiert.add(k)
                elif k in pausiert and (n < LERNEN_MIN_TRADES or schnitt > LERNEN_WIEDER_AB):
                    pausiert.discard(k)
            im_minus = {k for k in STRATEGIEN if len(alle_r[k]) >= LERNEN_LANG_MIN and summe[k] < 0}
        pausen[tag] = frozenset(pausiert | im_minus)
    stand = {}
    for k in STRATEGIEN:
        f, a = list(fenster[k]), alle_r[k]
        n = len(f)
        schnitt = sum(f) / n if n else np.nan
        streuung = float(np.std(a, ddof=1)) if len(a) > 1 else np.nan
        stand[k] = {"n": n, "gesamt": len(a), "schnitt": schnitt,
                    "gesamt_schnitt": sum(a) / len(a) if a else np.nan,
                    "spanne": 2 * streuung / math.sqrt(n) if n > 1 else np.nan,
                    "quote": sum(1 for x in f if x > 0) / n * 100 if n else np.nan,
                    "pausiert": k in pausiert or k in im_minus, "im_minus": k in im_minus}
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

def gleiche_branche(ticker, andere):
    """Wie viele der anderen Ticker gehören zur selben Branche? Unbekannte Ticker bilden ihre eigene Branche."""
    b = BRANCHE.get(ticker)
    return sum(1 for x in andere if b is not None and BRANCHE.get(x) == b)

def ausfuehrbare_auftraege(stand):
    """Teilt die Aufträge des Papier-Depots auf: (ausführbar, {Grund: [Ticker]}, Nachrücker). Gekauft wird zur
    Eröffnung in der gespeicherten Reihenfolge, verkauft erst danach (simuliere_depot, Schritt 1 vor 2) – ist das
    Depot jetzt schon voll oder die Branche schon belegt, verfällt der Auftrag sicher. Belegen erst die Aufträge
    davor die Plätze, rückt er nur nach, wenn einer davon nicht zum Limit klappt. Nur für die Anzeige; gespeichert
    werden alle Aufträge."""
    im_depot = [p["ticker"] for p in stand["positionen"]]
    shorts = sum(1 for p in stand["positionen"] if p["richtung"] < 0)
    ok, verfallen, nachruecker = [], {}, []
    for a in stand["auftraege"]:
        if len(im_depot) >= MAX_POSITIONEN:
            grund = f"Depot voll, {len(im_depot)}/{MAX_POSITIONEN} Positionen"
        elif a["ticker"] in im_depot:
            grund = "schon im Depot"
        elif (gleich := gleiche_branche(a["ticker"], im_depot)) >= MAX_JE_BRANCHE:
            grund = f"schon {gleich} aus derselben Branche im Depot, erlaubt sind {MAX_JE_BRANCHE}"
        elif a["richtung"] < 0 and shorts >= MAX_SHORTS:
            grund = f"schon {MAX_SHORTS} Shorts im Depot"
        else:
            geplant = [x["ticker"] for x in ok]
            if (len(im_depot) + len(ok) >= MAX_POSITIONEN or a["ticker"] in geplant
                    or gleiche_branche(a["ticker"], im_depot + geplant) >= MAX_JE_BRANCHE
                    or (a["richtung"] < 0 and shorts + sum(x["richtung"] < 0 for x in ok) >= MAX_SHORTS)):
                nachruecker.append(a)
            else:
                ok.append(a)
            continue
        verfallen.setdefault(grund, []).append(a["ticker"])
    return ok, verfallen, nachruecker

def simuliere_depot(daten, pausen, einst, lernen, zustand=None, signal_ticker=None, veto=None):
    """Spielt die Strategien rückwirkend mit einem virtuellen Depot durch. Regeln wie im Tagebuch (Signal zum
    Schluss, Einstieg zur nächsten Eröffnung bis zum Limit, Stop/Ziel/Zahlen/Zeitstopp), dazu Kapital- und
    Risikogrenzen, Gebühr und Spread je Order. Mit Lernen werden pausierte Strategien nicht gehandelt.
    Papier-Depot: Mit 'zustand' geht es vom gespeicherten Stand aus nur über die Tage nach zustand["bis"] weiter
    (beim Anlegen nur der letzte fertige Tag); 'signal_ticker' begrenzt, für welche Ticker neue Aufträge entstehen.
    Claude-Depot: veto(Signaltag, Ticker) gibt einen Grund zurück, wenn Claude dieses Signal ausgelassen hat – der
    Auftrag verfällt dann zur Eröffnung."""
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
        # gespeicherte Aufträge stammen vom letzten gerechneten Tag (ihr Signaltag)
        auftraege = [dict(a, signal_tag=a.get("signal_tag", zustand["bis"])) for a in zustand["auftraege"]]
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
            if t in einst.sperre_ticker or auftrag["strategie"] in einst.sperre_strategien:
                continue  # inzwischen in „Meine Regeln“ gesperrt: Auftrag wird gestrichen
            if veto is not None and veto(auftrag.get("signal_tag"), t):
                continue  # Claude-Depot: Claude hat dieses Signal ausgelassen
            r, stop = auftrag["richtung"], auftrag["stop"]
            if t in positionen or not einstieg_moeglich(d, i, r, stop, auftrag["limit"]):
                continue  # Kurslücke hinter den Stop oder über das Limit: Auftrag verfällt
            if len(positionen) >= MAX_POSITIONEN or gleiche_branche(t, positionen) >= MAX_JE_BRANCHE:
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
            if (t in positionen or i < MIN_KERZEN - 1 or (signal_ticker is not None and t not in signal_ticker)
                    or t in einst.sperre_ticker or (t in einst.nachrichten_sperre and tag == einst.nachrichten_tag)):
                continue
            wahl, _ = kandidaten(d, i, pausiert, einst.sperre_strategien)
            if wahl is None:
                continue
            r = STRATEGIEN[wahl]["richtung"]
            _, stop_a, ziel_a = d["signale"][wahl]
            stop, ziel, kurs = stop_a[i], ziel_a[i], d["C"][i]
            neue.append({"ticker": t, "richtung": r, "strategie": wahl, "stop": stop, "ziel": ziel,
                         "limit": limit_kurs(r, kurs, d["ATR"][i], stop, ziel),
                         "crv": r * (ziel - kurs) / (r * (kurs - stop)), "signal_tag": tag})
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
    wahl, grund = kandidaten(d, i, pausiert if einst.lernen else frozenset(), einst.sperre_strategien)
    if wahl is not None and t in einst.sperre_ticker:
        wahl, grund = None, f"{strategie_name(wahl)} – Aktie von dir gesperrt (Meine Regeln)"
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
                      "Einsatz": stueck * kurs, "Risiko": stueck * abs(kurs - stop),
                      "_chance": ziel_chance(d["C"][i], ziel_a[i], d["VOLA"][i]), "_muster": muster_am_tag(d, i)})
        mz, mz_art = musterziel(d, i, wahl)
        if math.isfinite(mz) and r > 0:
            zeile.update({"_musterziel": mz / rate, "_musterziel_art": mz_art})
        if zeile["_offen"]:
            zeile["Strategie"] += " (vorläufig)"
    elif grund is not None:
        if grund == "Quartalszahlen" and termin is not None:
            grund = f"Quartalszahlen {datum(termin)}"
        zeile.update({"Signal": WARTEN, "Strategie": grund})
    elif any(ok[i] for ok, _, _ in d["signale_roh"].values()):
        gesperrt = [k for k, (ok, _, _) in d["signale_roh"].items() if ok[i]]
        lang = STRATEGIEN[gesperrt[0]]["richtung"] > 0
        zeile.update({"Signal": WARTEN, "Strategie": f"{strategie_name(gesperrt[0])} – Marktfilter "
                                                     f"({'kein Long im Abwärtsmarkt' if lang else 'kein Short im Aufwärtsmarkt'})"})
    elif d["ueberhitzt"][i]:
        zeile.update({"Signal": SICHERN, "Strategie": "überhitzt – nur Info, Depot verkauft nicht"})
    elif einst.mit_short and d["ueberverkauft"][i]:
        zeile.update({"Signal": SICHERN, "Strategie": "überverkauft – nur Info (für Shorts)"})
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

def muster_satz(zeile, waehrung):
    """Kerzenmuster, Musterziel und Nachrichten-Stimmung eines Signals als Zusatz zum Handelsplan (nur Info)."""
    teile = []
    muster = zeile.get("_muster")
    if muster and (muster["bull"] or muster["bear"]):
        namen = [f"{m} (bullisch)" for m in muster["bull"]] + [f"{m} (bärisch)" for m in muster["bear"]]
        praxis = zeile.get("_muster_praxis", math.nan)
        teile.append(f"Kerzenmuster: {', '.join(namen)}"
                     + (f" – gedachte Trades mit so einem Muster bisher {de(praxis, 0)} % im Plus" if math.isfinite(praxis)
                        else ""))
    if math.isfinite(zeile.get("_musterziel", math.nan)):
        teile.append(f"Musterziel {de(zeile['_musterziel'])} {waehrung} ({zeile['_musterziel_art']}; der Bot verkauft "
                     f"trotzdem am Ziel {de(zeile['Ziel'])} {waehrung})")
    stimmung = zeile.get("_stimmung")
    if stimmung and (stimmung["gut"] or stimmung["schlecht"]):
        teile.append(f"Nachrichten der letzten Tage: {stimmung['gut']} gut, {stimmung['schlecht']} schlecht")
    return f" {'. '.join(teile)} (nur Info)." if teile else ""

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
    if math.isfinite(zeile.get("_chance", math.nan)):
        praxis = zeile.get("_chance_praxis", math.nan)
        satz += (f" Ziel-Chance nach Black-Scholes: {de(zeile['_chance'] * 100, 0)} % in {ZEITSTOPP_TAGE} Handelstagen"
                 + (f", bei ähnlichen Signalen bisher wirklich erreicht: {de(praxis, 0)} %" if math.isfinite(praxis) else "")
                 + " (nur Info – der Stop kann vorher kommen).")
    satz += muster_satz(zeile, waehrung)
    if str(zeile.get("Zahlen", "")).startswith("?"):
        satz += " Achtung: Quartalszahlen-Termin unbekannt – vor dem Kauf selbst prüfen."
    return satz

def wochen_rueckblick(stand, bis_vorher, markt, fx):
    """Wochenrückblick des Übungsdepots für die Handy-Nachricht (Zeilen) – nur in dem Lauf, der den letzten
    US-Handelstag einer Woche neu ins Depot bucht, sonst None."""
    if not stand or not stand.get("verlauf") or not stand.get("bis"):
        return None
    bis = pd.Timestamp(stand["bis"])
    if not bis_vorher or pd.Timestamp(bis_vorher) >= bis:
        return None  # Depot gerade erst angelegt, oder dieser Tag war schon gebucht (z. B. Lauf von Hand wiederholt)
    if tuple((bis + NYSE_TAG).isocalendar())[:2] == tuple(bis.isocalendar())[:2]:
        return None  # die Woche geht noch weiter
    montag = bis - pd.Timedelta(days=bis.weekday())
    verlauf = [(pd.Timestamp(t), float(w)) for t, w in stand["verlauf"]]
    davor = [w for t, w in verlauf if t < montag]
    vorher = davor[-1] if davor else float(stand["startkapital"])
    wert = verlauf[-1][1]
    woche = lambda tag: bool(tag) and montag <= pd.Timestamp(tag) <= bis
    kaeufe = sum(woche(p.get("kauf_tag")) for p in (stand.get("trades") or []) + (stand.get("positionen") or []))
    verkauft = [p for p in stand.get("trades") or [] if woche(p.get("verkauf_tag"))]
    im_plus = sum(p["erloes"] > p["kosten"] for p in verkauft)
    seit = (f"in dieser Woche, seit dem Start {de((wert / stand['startkapital'] - 1) * 100, 1, True)} %" if davor
            else "seit dem Start")
    zeilen = [f"**📅 Wochenrückblick Übungsdepot** ({montag:%d.%m.}–{bis:%d.%m.%Y})",
              f"- Wert {de(wert, 0)} €: {de(wert - vorher, 0, True)} € ({de((wert / vorher - 1) * 100, 1, True)} %) "
              + seit,
              f"- {kaeufe} {'Kauf' if kaeufe == 1 else 'Käufe'}, {len(verkauft)} "
              f"{'Verkauf' if len(verkauft) == 1 else 'Verkäufe'}"
              + (f", davon {im_plus} im Plus" if verkauft else "")]
    vergleich = papier_vergleich(stand, markt, fx)
    if vergleich is not None:
        basis = vergleich[vergleich.index.tz_localize(None) < montag]
        q_vorher = basis.iloc[-1] if len(basis) else float(stand["startkapital"])
        zeilen.append(f"- Nasdaq-100 (QQQ, in €) in derselben Zeit: "
                      f"{de((vergleich.iloc[-1] / q_vorher - 1) * 100, 1, True)} %")
    return zeilen

def schreibe_nachricht(datei, einstiege, plan, papier, woche=None):
    """Kurze Nachricht fürs Handy (z. B. als Kommentar bei GitHub): bei Kauf- oder Short-Signalen und nach dem letzten
    Handelstag der Woche (Wochenrückblick), sonst wird die Datei gelöscht, damit keine alte Nachricht noch einmal
    verschickt wird. Gibt einen Hinweis zurück, falls etwas nicht klappt."""
    try:
        if not einstiege and not woche:
            if os.path.exists(datei):
                os.remove(datei)
            return None
        if not einstiege:
            with open(datei, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(woche + ["", "Simulation mit Spielgeld – keine Anlageberatung."]) + "\n")
            return None
        heute = max(z["_stand"] for z in einstiege)
        n = len(einstiege)
        zeilen = [f"**{'🟢' if all(z['Signal'] == KAUFEN for z in einstiege) else '🔔'} Swing-Bot: {n} "
                  f"{'neues Signal' if n == 1 else 'neue Signale'}** (Kurse bis {datum(heute)} {heute:%Y})", ""]
        zeilen += [f"- {p}" for p in plan]
        if any(z["_offen"] for z in einstiege):
            zeilen += ["", "⚠️ Vorläufig: Die Börse war beim Lauf noch offen – das Signal kann bis zum Schluss wegfallen."]
        auftraege, verfallen, nachruecker = ausfuehrbare_auftraege(papier) if papier else ([], {}, [])
        if auftraege:
            zeilen += ["", "📒 Übungsdepot: " + ", ".join(
                f"{'kauft' if a['richtung'] > 0 else 'shortet'} {a['ticker']}" for a in auftraege)
                + " zur nächsten Eröffnung (nur bis zum Limit)."
                + (f" Klappt ein Kauf nicht, rückt {', '.join(a['ticker'] for a in nachruecker)} nach."
                   if nachruecker else "")]
        elif verfallen:
            zeilen += ["", f"📒 Übungsdepot: kauft diesmal nichts ({'; '.join(verfallen)})."]
        if woche:
            zeilen += [""] + woche
        zeilen += ["", "Simulation mit Spielgeld – keine Anlageberatung."]
        with open(datei, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(zeilen) + "\n")
    except OSError as fehler:
        return f"Nachricht nicht geschrieben ({fehler.strerror or type(fehler).__name__})."
    return None

def marktampel(trend, zeilen, einst):
    """Marktlage (Nasdaq-100 zur 200-Tage-Linie), wie sie für die Signale der Tabelle gilt: je Zeile der letzte
    QQQ-Schluss vor ihrem Kurstag. Hat QQQ die Linie gerade gekreuzt, gilt für Zeilen mit älterer Kerze noch die
    Lage davor."""
    if trend is None:
        return "⚠️ Keine Nasdaq-100-Daten – der Marktfilter ist diesmal aus." if einst.marktfilter else None
    tage = sorted({z["_stand"] for z in zeilen})
    vortag = pd.DatetimeIndex(tage) - pd.Timedelta(days=1)
    if trend.index.tz is not None and vortag.tz is None:
        vortag = vortag.tz_localize(trend.index.tz)
    bekannt = {}
    for tag, pos in zip(tage, trend.index.searchsorted(vortag, side="right") - 1):
        if pos >= 0 and not np.isnan(trend.iloc[pos]):
            bekannt[tag] = (trend.index[pos], trend.iloc[pos])
    if not bekannt:
        return None
    qqq_tag, lage = bekannt[max(bekannt)]
    oben = lage == 1
    text = f"Nasdaq-100 (QQQ) schloss am {datum(qqq_tag)} {'über' if oben else 'unter'} seiner 200-Tage-Linie"
    if not einst.marktfilter:
        return f"{'🟢' if oben else '🔴'} Markt: {text} (Marktfilter aus, --ohne-marktfilter)."
    if oben:
        satz = f"🟢 Marktfilter: {text} – der Bot kauft nur (Long)" + (", Short-Signale wartet er ab." if einst.mit_short
                                                                         else ".")
    else:
        satz = (f"🔴 Marktfilter: {text} – der Bot kauft nicht, "
                + ("nur Short-Signale zählen." if einst.mit_short else "er wartet ab (Short-Signale sind aus)."))
    anders = [z["Ticker"] for z in zeilen if z["_stand"] in bekannt and bekannt[z["_stand"]][1] != lage]
    if anders:
        namen = ", ".join(anders[:4]) + (" …" if len(anders) > 4 else "")
        satz += (f" Für {namen} (letzte Kerze älter) gilt noch die Lage davor ({'unter' if oben else 'über'} der "
                 f"Linie) – die Signale in der Tabelle beachten das schon.")
    return satz

def kopfzeilen(zeilen, einst, fx_heute, waehrung, trend, ohne_zahlen, fehlt=None):
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
    if fehlt is not None:
        hinweise.append(f"⚠️ Die Kurse vom {datum(fehlt)} fehlen noch: Yahoo hat diesen US-Handelstag noch nicht "
                        f"geliefert (oder die Börse war an dem Tag geschlossen). Die Signale unten beruhen deshalb auf "
                        f"älteren Kursen, und der Kauftag im Handelsplan ist schon vorbei – nicht danach handeln. Der "
                        f"nächste Lauf holt den Tag nach, auch im Übungsdepot."
                        + (" Eine Nachricht aufs Handy gibt es diesmal nicht." if einst.nachricht else ""))
    ampel = marktampel(trend, ok, einst)
    if ampel:
        hinweise.append(ampel)
    gesamt = einst.konto * MAX_GESAMTRISIKO_PROZENT / 100
    shorts = f" (davon höchstens {MAX_SHORTS} Short)" if einst.mit_short else ""
    hinweise.append(f"Regel: höchstens {MAX_POSITIONEN} Positionen gleichzeitig{shorts}, höchstens {MAX_JE_BRANCHE} aus "
                    f"derselben Branche "
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
    leer = [t for t, n in news.items() if n.get("spalte") != "?" and not n.get("zeilen")]
    if news and len(leer) == len(news):
        fuss.append(f"📰 Für keine Aktie mit Signal ({', '.join(leer)}) kamen Schlagzeilen der letzten {NEWS_TAGE} "
                    f"Handelstage – die Nachrichten-Regel hatte diesmal nichts zu prüfen. Kommt das öfter vor, liefert "
                    f"Yahoo gerade keine Schlagzeilen – dann vor dem Kauf selbst die Nachrichten lesen.")
    if fehler or ohne_termine or ohne_news or (news and len(leer) == len(news)):
        fuss.append("")
    heute = sorted({z["_strategie"] for z in zeilen if z.get("_strategie")}, key=VORRANG.get)
    for key in heute:
        fuss.append(f"{strategie_name(key)}: {STRATEGIEN[key]['regel']}")
    umrechnung = "US-Kurse umgerechnet" if waehrung == "€" else "Wechselkurs nicht verfügbar, nicht umgerechnet"
    fuss.append(f"Beträge in {waehrung} ({umrechnung}). Limit = höchster Kaufkurs (Short: tiefster Verkaufskurs) für den "
                f"Einstieg. Risiko = Verlust, wenn der Stop greift. CRV = Chance ÷ Risiko; nötige Trefferquote = "
                f"1 ÷ (1 + CRV), bei CRV 1 also 50 %, bei CRV 0,8 gut 55 % – der Bot setzt das Ziel absichtlich nicht "
                f"weiter weg als den Stop, dafür trifft er öfter. ⏸ WARTEN = ein Signal ist da, aber eine "
                f"Regel hält den Bot zurück (Grund in der Spalte Strategie).")
    if any(z.get("Signal") == SICHERN for z in zeilen):
        fuss.append("⚠️ ÜBERHITZT = RSI über 70 oder Kurs am oberen Bollinger-Band (mit Shorts auch das Gegenstück: "
                    "überverkauft). Nur Info – das Übungsdepot verkauft nicht danach: Im Test über 16 Jahre brachte "
                    "Verkaufen bei überhitzt bis zu 5,6 Prozentpunkte weniger Rendite pro Jahr, weil die Gewinner früh "
                    "verkauft werden und die Verlierer trotzdem bis zum Stop laufen. Auch den Stop nachziehen oder am "
                    "Ziel nur die Hälfte verkaufen war schlechter. Der Bot verkauft am Stop, am Ziel, vor Quartalszahlen oder nach "
                    f"{ZEITSTOPP_TAGE} Handelstagen.")
    if einst.mit_short:
        fuss.append("🔴 Short = auf fallende Kurse setzen (z. B. per CFD oder Turbo-Schein). Verluste sind nach oben "
                    "offen. Bei Hebelprodukten zählt der Verlust am Stop, nicht der Einsatz: Hebel × Einsatz = echte "
                    "Positionsgröße.")
    fuss.append("Stop-Orders auf deutschen Handelsplätzen können schon vor 15:30 Uhr bei dünnem Handel auslösen. "
                "Quartalszahlen-Termine kommen von Yahoo und können sich verschieben. Keine Anlageberatung.")
    if any(n.get("zeilen") for n in news.values()):
        fuss.append("📰 Schlagzeilen: Spricht eine erkannte Meldung der letzten Tage gegen ein Signal (⚠️, z. B. "
                    "Herabstufung, Kapitalerhöhung, Ermittlungen, Übernahme), wartet der Bot (⏸ WARTEN – Nachricht) und "
                    "kauft auch im Papier-Depot nicht. Die Wortsuche versteht keinen Zusammenhang – vor dem Kauf selbst "
                    "lesen. Rückwirkend lässt sich diese Regel nicht testen; im Rückblick gilt sie nur für den letzten Tag.")
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

# --- Bericht als Markdown-Datei (z. B. für GitHub, wo der Bot automatisch läuft) -----------------------
BERICHT = []  # Abschnitte des laufenden Laufs
BERICHT_HINWEISE = []  # Hinweise für den Kopf des Berichts (z. B. ignorierte Angaben)
BERICHT_STATUS = {}  # z. B. "papier", "verbindung", "einstellungen" (Fehlertext)
TV_BOERSEN = {"DE": "XETR", "F": "FWB", "SG": "SWB", "MU": "MUN", "BE": "BER", "DU": "DUS", "HM": "HAM", "HA": "HAN",
              "PA": "EURONEXT", "AS": "EURONEXT", "BR": "EURONEXT", "LS": "EURONEXT", "IR": "EURONEXT", "MI": "MIL",
              "MC": "BME", "VI": "VIE", "HE": "OMXHEX"}

def tradingview_link(ticker):
    """Link zum Chart bei TradingView (Yahoo-Kürzel umgesetzt, z. B. SAP.DE -> XETR:SAP, BTC-EUR -> BTCEUR);
    None für Kürzel, die TradingView so nicht kennt (Indizes wie ^GSPC, Börsen außerhalb der Liste)."""
    if ticker.startswith("^"):
        return None
    if re.fullmatch(r".+-[A-Z]{3}", ticker):
        symbol = ticker.replace("-", "")
    elif "." in ticker:
        name, boerse = ticker.rsplit(".", 1)
        if boerse not in TV_BOERSEN:
            return None
        symbol = f"{TV_BOERSEN[boerse]}:{name}"
    else:
        symbol = ticker.replace("-", ".")
    return f"https://www.tradingview.com/chart/?symbol={urllib.parse.quote(symbol)}"

def md_tabelle(tabelle, formate, links=False):
    """Tabelle als Markdown (gleiche Zahlenformate wie im Terminal; Ticker optional als TradingView-Link)."""
    spalten = list(tabelle.columns)
    zeilen = ["| " + " | ".join(spalten) + " |",
              "| " + " | ".join("---:" if pd.api.types.is_numeric_dtype(tabelle[s]) else "---" for s in spalten) + " |"]
    for _, zeile in tabelle.iterrows():
        zellen = []
        for s in spalten:
            wert = zeile[s]
            if wert is None or (isinstance(wert, float) and math.isnan(wert)):
                text = "–"
            else:
                text = formate[s](wert) if s in formate else str(wert)
            if links and s == "Ticker" and text not in ("", "–") and tradingview_link(text):
                text = f"[{text}]({tradingview_link(text)})"
            zellen.append(text.replace("|", "\\|").replace("\n", " "))
        zeilen.append("| " + " | ".join(zellen) + " |")
    return "\n".join(zeilen)

def md_text(text):
    """Freitext für Markdown: Zeichen entschärfen, die GitHub sonst als Formatierung oder HTML liest."""
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", str(text))

def berichte(titel, zeilen=(), tabelle=None, formate=None, links=False, nachher=()):
    """Einen Abschnitt für den Markdown-Bericht merken (zwei Leerzeichen am Zeilenende = Zeilenumbruch)."""
    teil = [f"## {md_text(titel)}", ""] + [f"{md_text(z)}  " for z in zeilen if z]
    if tabelle is not None and len(tabelle):
        teil += ["", md_tabelle(tabelle, formate or {}, links), ""]
    teil += [f"{md_text(z)}  " for z in nachher if z]
    BERICHT.append("\n".join(teil))

def schreibe_bericht(datei, ok, absturz=False):
    """Schreibt den Markdown-Bericht. Gibt zurück, ob das geklappt hat."""
    jetzt = pd.Timestamp.now(tz=BERLIN)
    github = bool(os.environ.get("GITHUB_ACTIONS"))
    art = "automatischer Lauf bei GitHub" if github else "Lauf von Hand"
    papier = " Das Papier-Depot bleibt auf dem zuletzt gespeicherten Stand." if BERICHT_STATUS.get("papier") else ""
    kopf = ["# 📈 Swing-Bot – Bericht", "",
            f"Stand: {WOCHENTAGE[jetzt.weekday()]} {jetzt:%d.%m.%Y %H:%M} Uhr ({art}). Ticker anklicken öffnet den "
            f"Chart bei TradingView. Simulation mit echten Kursen, kein echtes Geld, keine Anlageberatung.", ""]
    if "einstellungen" in BERICHT_STATUS:
        kopf += [f"> ❌ Einstellungen fehlerhaft – der Bot ist nicht gelaufen: {md_text(BERICHT_STATUS['einstellungen'])}. "
                 + ("Variablen KONTO, RISIKO, TICKER und OPTIONEN prüfen (Settings → Secrets and variables → Actions)."
                    if github else "Angaben beim Start prüfen."), ""]
    elif absturz:
        kopf += ["> ❌ Dieser Lauf wurde abgebrochen"
                 + (" (Details bei GitHub im Tab „Actions“)." if github else " (Details in der Ausgabe).") + papier, ""]
    elif not ok and BERICHT_STATUS.get("verbindung", True):
        kopf += ["> ❌ Dieser Lauf hat keine auswertbaren Kurse bekommen (Yahoo nicht erreichbar oder Yahoo-Limit)."
                 + (papier and " Das Papier-Depot ist unverändert, der nächste Lauf holt alles nach."), ""]
    elif not ok:
        kopf += ["> ❌ Für keinen Ticker gab es auswertbare Kurse – Gründe unten. Ticker prüfen"
                 + (" (Variable TICKER)." if github else ".") + papier, ""]
    kopf += [x for h in BERICHT_HINWEISE for x in (f"> ⚠️ {md_text(h)}", "")]
    try:
        ordner = os.path.dirname(os.path.abspath(datei))
        os.makedirs(ordner, exist_ok=True)
        with open(datei, "w", encoding="utf-8") as f:
            f.write("\n".join(kopf) + "\n" + "\n\n".join(BERICHT) + "\n")
    except OSError as fehler:
        print(f"❌ Bericht nicht gespeichert ({fehler}).")
        return False
    return True

def zeige(html_teil, text_teil):
    """Im Notebook als HTML mit Textfassung (Spyder, qtconsole, jupyter console zeigen die Textfassung)."""
    from IPython.display import display
    display({"text/html": html_teil, "text/plain": text_teil}, raw=True)

def zeige_scanner(tabelle, titel, zusammenfassung, hinweise, plan, schlagzeilen, fuss, formate, notebook):
    mitte = ([""] + plan if plan else []) + ([""] + schlagzeilen if schlagzeilen else []) + [""]
    berichte(titel, [zusammenfassung, *hinweise], tabelle, formate, True, [*plan, *schlagzeilen, *fuss])
    if not notebook:
        print(als_text(tabelle, titel, zusammenfassung, hinweise, fuss, formate, farben_im_terminal(), mitte))
        return

    def zeilenfarbe(zeile):
        bg, fg = FARBEN.get(zeile["Signal"], (None, None))
        return [f"background-color: {bg}; color: {fg}" if bg else ""] * len(zeile)

    # Schmale Ausgabe (z. B. Colab mit Seitenleiste): Signal, Strategie und News dürfen umbrechen,
    # das Symbol bleibt dabei am Wort („⚠️ ÜBERHITZT“, „⏸ WARTEN“)
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
        if key in einst.sperre_strategien:
            status = "⛔ aus (von dir, Meine Regeln)"
        elif not einst.lernen:
            status = "– (ohne Lernen)"
        elif s["im_minus"]:
            status = (f"⏸ aus (insgesamt im Minus: Ø {de(s['gesamt_schnitt'], 2, True)} R je Trade über "
                      f"{s['gesamt']} Trades)")
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

def zufall_kennzahlen(stand, einst, anzahl):
    """(typischer bester Ø von 'anzahl' Strategien ohne Vorteil nach je 20 Trades, Trades bis ein Vorteil von 0,1 R
    sicher erkennbar ist) – aus der Streuung der Tagebuch-Trades (± Zufall = 2 Streuungen / Wurzel der Anzahl)."""
    streuungen = [s["spanne"] * math.sqrt(s["n"]) / 2 for k, s in stand.items()
                  if (STRATEGIEN[k]["richtung"] > 0 or einst.mit_short) and s["n"] > 1 and not np.isnan(s["spanne"])]
    sigma = float(np.median(streuungen)) if streuungen else 0.8
    beste = sigma / math.sqrt(20) * NormalDist().inv_cdf(0.5 ** (1 / max(anzahl, 1)))  # Median des Besten ohne Vorteil
    noetig = max(50, int(round((2 * sigma / 0.1) ** 2 / 50)) * 50)
    return beste, noetig

def zeige_lernen(stand, einst, waehrung, notebook, rueckschau_hinweis):
    tabelle = lern_tabelle(stand, einst, waehrung)
    beste, noetig = zufall_kennzahlen(stand, einst, len(tabelle))
    titel = "🧠 WIE LIEFEN DIE STRATEGIEN ZULETZT? (Strategie-Tagebuch – jede Strategie handelt gedanklich mit)"
    erklaerung = [
        f"Gezählt werden die letzten bis zu {LERNEN_FENSTER} gedachten Trades je Strategie über alle Ticker, nach "
        f"Spread und Gebühren. 1 R = der geplante Verlust bis zum Stop (bei dir {de(einst.konto * einst.risiko / 100, 0)} "
        f"{waehrung}).",
        f"Lernregel: Ab {LERNEN_MIN_TRADES} Trades wird eine Strategie pausiert, wenn sie im Schnitt mehr als "
        f"{de(-LERNEN_PAUSE_AB, 1)} R je Trade verliert, und wieder aktiv, sobald der Schnitt im Plus ist. Ab "
        f"{LERNEN_LANG_MIN} Trades muss sie außerdem über ihre ganze Geschichte im Plus sein, sonst handelt der Bot sie "
        f"gar nicht. Pausierte Strategien handeln im Tagebuch weiter und kommen zurück, wenn sie wieder gut laufen.",
        f"± Zufall: So weit kann der Schnitt allein durch Glück oder Pech schwanken. Lässt man {len(tabelle)} "
        f"Strategien ganz ohne Vorteil je 20 Trades machen, zeigt die beste meist um {de(beste, 2, True)} R – reiner "
        f"Zufall. Einen Vorteil von 0,1 R je Trade kann man erst nach etwa {noetig} Trades von Glück unterscheiden. "
        f"Bei {len(tabelle)} "
        f"Strategien wirkt auch ohne echten Vorteil oft eine 'klar im Plus' oder 'klar im Minus' – das sind Hinweise, "
        f"keine Beweise. 'Pausiert' ist eine Vorsichtsmaßnahme.",
        rueckschau_hinweis,
    ]
    with pd.option_context("display.unicode.east_asian_width", True):
        tabelle_text = tabelle.to_string(index=False, formatters=LERN_FORMATE, na_rep="–")
    text = "\n".join(["", titel, tabelle_text, *erklaerung])
    berichte(titel, (), tabelle, LERN_FORMATE, False, erklaerung)
    if not notebook:
        print(text)
        return

    def statusfarbe(zeile):
        return ["background-color: #fff3cd; color: #1b1b1b; font-weight: bold;"
                if s == "Status" and zeile["Status"].startswith("⏸") else "" for s in zeile.index]

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

def depot_auswertung(erg, ohne, einst, waehrung, ohne_filter=None):
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
    if ohne_filter is not None:
        unterschied = erg["end_wert"] - ohne_filter["end_wert"]
        spanne = zufallsspanne(erg, ohne_filter)
        einordnung = ("im Zufallsbereich – in diesem Zeitraum kein klarer Unterschied." if abs(unterschied) <= spanne
                      else f"größer als der Zufall – der Marktfilter hat hier {'geholfen' if unterschied > 0 else 'geschadet'} "
                           f"(ein Hinweis, kein Beweis).")
        zeilen.append(f"Ohne Marktfilter: {de(ohne_filter['end_wert'])} {waehrung} · Unterschied "
                      f"{de(unterschied, 0, True)} {waehrung} · Zufallsspanne ±{de(spanne, 0)} {waehrung} → {einordnung}")
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

def zeige_depot(erg, ohne, einst, waehrung, notebook, ohne_zahlen_regel, rueckschau_hinweis, ohne_zahlen=False,
                ohne_filter=None, filter_aktiv=False):
    zusammenfassung = depot_auswertung(erg, ohne, einst, waehrung, ohne_filter)
    tabelle = trade_tabelle(erg)
    weggelassen = 0
    if tabelle is not None:
        anzeige = len(erg["offen"]) + MAX_TRADES_ANZEIGE
        weggelassen = max(len(tabelle) - anzeige, 0)
        tabelle = tabelle.iloc[:anzeige]
    hinweis = ((f"… {weggelassen} ältere Trades nicht angezeigt." if os.environ.get("GITHUB_ACTIONS") else
                f"… {weggelassen} ältere Trades nicht angezeigt – alle Trades speichert --csv in einer eigenen Datei.")
               if weggelassen else "")
    dollar_shorts = waehrung == "€" and any(p["richtung"] < 0 and waehrung_von(p["ticker"]) == "USD"
                                           for p in erg["trades"] + erg["offen"])
    regeln = (f"Regeln: Signal zum Schlusskurs, Einstieg zur Eröffnung des nächsten Handelstags nur bis zum Limit; "
              f"{('Long nur, wenn der Nasdaq-100 über seiner 200-Tage-Linie liegt, Short nur darunter; ' if einst.mit_short else 'gekauft wird nur, wenn der Nasdaq-100 über seiner 200-Tage-Linie liegt; ') if filter_aktiv else ''}"
              f"Ausstieg an Stop oder Ziel (bei beidem am selben Tag zählt der Stop), "
              f"{'' if ohne_zahlen else 'zum Schluss vor Quartalszahlen '}"
              f"oder nach {ZEITSTOPP_TAGE} Handelstagen; höchstens {MAX_POSITIONEN} Positionen"
              f"{f', {MAX_SHORTS} Shorts' if einst.mit_short else ''}, {MAX_JE_BRANCHE} je Branche und "
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
    berichte(zusammenfassung[0], zusammenfassung[1:], tabelle, TRADE_FORMATE, True, [hinweis, regeln, rueckschau_hinweis])
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
        abhilfe = ("Die Datei im Repository löschen (neu anfangen) oder bei GitHub eine frühere Fassung aus der "
                   "Historie zurückholen." if os.environ.get("GITHUB_ACTIONS") else "Mit --papier-neu neu anlegen.")
        return None, f"Papier-Depot-Datei nicht lesbar ({fehler}) – sie bleibt unverändert. {abhilfe}"

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

def papier_fortschreiben(stand, daten, pausen, einst, signal_ticker, veto=None):
    """Rechnet das Papier-Depot bis zum letzten fertigen Kurstag weiter. Gibt (neuer Stand, Lauf, Bericht) zurück;
    Lauf ist None, wenn diesmal nicht weitergerechnet werden konnte (der Stand bleibt dann unverändert)."""
    bericht = {"neu": stand is None, "anpassungen": [], "warnung": None, "nicht_ausgefuehrt": [], "gestrichen": [],
               "ausgelassen": []}
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

    erg = simuliere_depot(daten, pausen, einst, einst.lernen, zustand=lauf, signal_ticker=signal_ticker, veto=veto)
    if erg is None:
        bericht["warnung"] = "Keine fertigen Kurstage – das Papier-Depot wurde diesmal nicht weitergerechnet."
        return stand, None, bericht

    # Aufträge aus dem letzten Lauf, die am ersten neuen Handelstag ihres Tickers nicht ausgeführt wurden
    gekauft = {(p["ticker"], p["kauf_tag"]) for p in erg["positionen"] + erg["trades"]}
    for a in lauf["auftraege"]:
        d = daten[a["ticker"]]
        neu = [tag for tag in d["idx"][:d["n_fertig"]] if lauf["bis"] is not None and tag > lauf["bis"]]
        if neu and neu[0] in set(erg["tage"]) and (a["ticker"], neu[0]) not in gekauft:
            if a["ticker"] in einst.sperre_ticker or a["strategie"] in einst.sperre_strategien:
                bericht["gestrichen"].append(a["ticker"])
            elif veto is not None and veto(lauf["bis"], a["ticker"]):
                bericht["ausgelassen"].append(a["ticker"])
            else:
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

def papier_texte(stand, erg, bericht, pfad, einst, waehrung, vergleich, fx_heute, name_von, titel=None, vorne=()):
    """Überschrift, Zusammenfassung und Hinweise des Papier-Depots als Textzeilen (Claude-Depot: eigener Titel und
    Zeilen 'vorne')."""
    start = pd.Timestamp(stand["angelegt"]) if stand["angelegt"] else None
    kopf = titel or (f"📒 PAPIER-DEPOT · Vorwärtstest seit {start:%d.%m.%Y} mit {de(stand['startkapital'], 0)} "
                     f"{waehrung}" if start is not None else "📒 PAPIER-DEPOT")
    zeilen = list(vorne)
    if bericht["warnung"]:
        zeilen.append(f"⚠️ {bericht['warnung']}")
    if bericht["neu"] and erg is not None and einst.papier_neu:
        zeilen.append("Mit --papier-neu neu angefangen – beim nächsten Lauf --papier-neu wieder weglassen, sonst beginnt "
                      "das Depot jedes Mal von vorn (ein vorheriger Stand bleibt jeweils als Kopie mit Datum im selben "
                      "Ordner).")
    if not bericht["neu"] and abs(einst.konto - stand["startkapital"]) >= 0.5:
        neu_anfangen = ("papier/papier_depot.json im Repository löschen" if os.environ.get("GITHUB_ACTIONS")
                        else "einmal mit --papier-neu starten")
        zeilen.append(f"ℹ️ Das Papier-Depot rechnet mit seinem Startkapital {de(stand['startkapital'], 0)} {waehrung} "
                      f"weiter (Konto jetzt {de(einst.konto, 0)} {waehrung}). Neu anfangen mit dem neuen Betrag: "
                      f"{neu_anfangen}.")
    if bericht["neu"] and erg is not None:
        zeilen.append(f"Neu angelegt mit {de(stand['startkapital'], 0)} {waehrung}. Ab jetzt handelt der Bot hier "
                      f"vorwärts nach seinen Regeln – jede Entscheidung nur mit Kursen, die es da schon gab. "
                      + ("GitHub startet ihn jeden Börsentag automatisch; verpasste Tage holt er nach."
                         if os.environ.get("GITHUB_ACTIONS") else
                         "Starte ihn jeden Börsentag einmal (am besten morgens vor 15:30 Uhr); verpasste Tage holt er "
                         "nach."))
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
            if bericht.get("ausgelassen"):
                teile.append("von Claude ausgelassen: " + ", ".join(bericht["ausgelassen"]))
            if bericht["nicht_ausgefuehrt"]:
                teile.append("nicht ausgeführt (Limit nicht erreicht, Kurslücke, kein Platz/Geld oder schon "
                             f"{MAX_JE_BRANCHE} aus derselben Branche im Depot): "
                             + ", ".join(bericht["nicht_ausgefuehrt"]))
            if bericht.get("gestrichen"):
                teile.append("gestrichen (Meine Regeln): " + ", ".join(bericht["gestrichen"]))
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
    auftraege, verfallen, nachruecker = ausfuehrbare_auftraege(stand)
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
        if nachruecker:
            zeilen.append(f"Nachrücker (gekauft nur, wenn ein Auftrag davor nicht zum Limit klappt – sonst sind die "
                          f"{MAX_POSITIONEN} Plätze bzw. die Branche schon belegt): "
                          + ", ".join(f"{a['ticker']} {name_von(a['strategie'])}" for a in nachruecker))
        if erg is not None and eroeffnung_vorbei(auftraege, termine):
            zeilen.append(f"Die Eröffnung am {datum(erster)} ist schon gelaufen: Das Papier-Depot bucht einen Tag erst, "
                          f"wenn er für alle Werte fertig ist – also beim nächsten Lauf nach dem Handelstag (am besten "
                          f"am Morgen danach).")
        zeilen.append("Die Aufträge stammen vom letzten fertigen Kurstag und berücksichtigen die offenen Positionen und "
                      "das Geld des Papier-Depots – sie können deshalb vom Handelsplan oben (für ein leeres Konto) "
                      "abweichen.")
    elif erg is not None and not verfallen:
        zeilen.append("Keine Aufträge für den nächsten Handelstag.")
    if verfallen:
        zeilen.append(("Keine Käufe zur nächsten Eröffnung möglich" if not auftraege else "Nicht möglich") + ": "
                      + "; ".join(f"{', '.join(t)} – {grund}" for grund, t in verfallen.items())
                      + ". Verkauft wird erst nach der Eröffnung, deshalb verfallen diese Signale.")
    if os.environ.get("GITHUB_ACTIONS"):  # automatischer Lauf: Datei im Repository, alte Stände in der Git-Historie
        ort = (f"{os.path.relpath(pfad)} im Repository (neu anfangen: die Datei im Repository löschen, "
               f"die Historie bei GitHub behält den alten Stand)")
    else:
        ort = ("Google Drive › MyDrive › swing_scanner › papier_depot.json" if pfad == PAPIER_DATEI_COLAB else pfad) \
            + " (neu anfangen mit --papier-neu, der alte Stand bleibt als Kopie erhalten)"
    zeilen.append(f"Gespeichert in: {ort}. "
                  f"Simulation mit echten Kursen, ohne echtes Geld – Ausführung zur Eröffnung bzw. am Stop/Ziel, "
                  f"{de(einst.gebuehr)} {waehrung} Gebühr + {prozent(SPREAD_PROZENT)} % Spread je Order.")
    return kopf, zeilen

def zeige_papier(stand, erg, bericht, pfad, einst, waehrung, notebook, vergleich, fx_heute, titel=None, vorne=()):
    kopf, zeilen = papier_texte(stand, erg, bericht, pfad, einst, waehrung, vergleich, fx_heute, strategie_name,
                                titel, vorne)
    tabelle = trade_tabelle(papier_ansicht(stand, erg))
    weggelassen = 0
    if tabelle is not None:
        anzeige = len(stand["positionen"]) + MAX_TRADES_ANZEIGE
        weggelassen = max(len(tabelle) - anzeige, 0)
        tabelle = tabelle.iloc[:anzeige]
    hinweis = f"… {weggelassen} ältere Trades nicht angezeigt (alle stehen in der Datei)." if weggelassen else ""
    berichte(kopf, zeilen, tabelle, TRADE_FORMATE, True, [hinweis])
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
                markt, trend, veto=None, titel=None, vorne=None):
    """Papier-Depot fortschreiben, anzeigen und speichern. Gibt den neuen Stand zurück (oder None).
    Claude-Depot: veto (siehe simuliere_depot), eigener Titel und vorne(neuer Stand) -> Zeilen über der Übersicht."""
    def nur_hinweis(text):
        print(f"\n{titel or '📒 PAPIER-DEPOT'}\n⚠️ {text}")
        berichte(titel or "📒 PAPIER-DEPOT", [f"⚠️ {text}"])
        return None
    if fehler:
        return nur_hinweis(fehler)
    if fx is None:
        return nur_hinweis("Ohne Euro-Wechselkurs wird das Papier-Depot diesmal nicht weitergerechnet (es führt alle "
                           "Beträge in €) – beim nächsten Lauf wird nachgeholt.")
    if einst.marktfilter and trend is None:
        return nur_hinweis("Ohne Nasdaq-100-Kurse (QQQ) fehlt der Marktfilter – das Papier-Depot wird diesmal nicht "
                           "weitergerechnet, beim nächsten Lauf wird nachgeholt.")
    daten_p = dict(daten)
    for t in extra:
        if t in roh:
            daten_p[t] = bereite_vor(t, roh[t], fx_je_ticker.get(t), zusatz.get(t, {}).get("zahlen"), einst, trend)
    # Quartalszahlen-Termine: Klappt die Abfrage diesmal nicht (Yahoo-Limit, Formatfehler), gelten die zuletzt
    # gespeicherten – sonst hielte das Papier-Depot eine Position unbemerkt über die Zahlen
    gemerkt = (stand or {}).get("termine")
    gemerkt = dict(gemerkt) if isinstance(gemerkt, dict) else {}
    if not einst.ohne_zahlen:
        for t, d in list(daten_p.items()):
            if d["termine"] is None and gemerkt.get(t):
                daten_p[t] = bereite_vor(t, roh[t], fx_je_ticker.get(t),
                                         pd.DataFrame(index=pd.to_datetime(gemerkt[t], utc=True)), einst, trend)
    neu, erg, bericht = papier_fortschreiben(stand, daten_p, pausen, einst, set(daten), veto)
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
    zeige_papier(neu, erg, bericht, datei, einst, waehrung, notebook, vergleich, float(fx.iloc[-1]), titel,
                 vorne(neu) if vorne else ())
    return neu

# ----------------------------------------------------------------------------
# Claude-Depot (Versuch): wie das Übungsdepot, nur lässt Claude einzelne Kauf-Signale aus
# ----------------------------------------------------------------------------
CLAUDE_TITEL = "🧠 CLAUDE-DEPOT (Versuch)"
CLAUDE_THEMA = "🧠 Claude-Depot: Entscheidungen"

def naechste_eroeffnung(signal_tag):
    """Eröffnung des nächsten US-Handelstags nach dem Signaltag (bis dahin muss Claude entschieden haben)."""
    tag = pd.Timestamp(pd.Timestamp(signal_tag).date()) + NYSE_TAG
    return pd.Timestamp(f"{tag:%Y-%m-%d} 09:30", tz=NY)

def lies_claude_entscheidungen(datei):
    """Claudes Entscheidungen aus den Kommentaren im GitHub-Thema (der Workflow holt nur die des Repository-Besitzers):
    je Kommentar ein ```json-Block {"signal_tag": "JJJJ-MM-TT", "auslassen": {Ticker: Grund}, "nehmen": {Ticker:
    Grund}, "notiz": "..."}. Es zählt nur, was vor der Eröffnung des nächsten Handelstags geschrieben und danach nicht
    mehr geändert wurde (Zeitstempel von GitHub); gibt es mehrere, die letzte. Gibt ({Signaltag: Entscheidung},
    [Signaltage mit zu später Entscheidung]) zurück."""
    if not datei or not os.path.exists(datei):
        return {}, []
    try:
        with open(datei, encoding="utf-8") as f:
            text = f.read().strip()
    except OSError:
        return {}, []
    kommentare = []
    try:
        kommentare = json.loads(text) if text.startswith("[") else [json.loads(z) for z in text.splitlines() if z.strip()]
    except ValueError:
        return {}, []

    def saeubern(liste):
        if not isinstance(liste, dict):
            return {}
        return {str(t).strip().upper(): " ".join(str(g).split())[:300] for t, g in liste.items()
                if re.fullmatch(r"[A-Za-z0-9.^=-]{1,15}", str(t).strip())}

    gut, zu_spaet = {}, []
    for k in kommentare if isinstance(kommentare, list) else []:
        if not isinstance(k, dict):
            continue
        bloecke = re.findall(r"```json\s*(\{.*?\})\s*```", str(k.get("body", "")), re.S)
        if not bloecke:
            continue
        try:
            e = json.loads(bloecke[-1])
            tag = pd.Timestamp(e["signal_tag"])
            erstellt = pd.Timestamp(k["created_at"])
            geaendert = pd.Timestamp(k.get("updated_at") or k["created_at"])
            if erstellt.tz is None or geaendert.tz is None:
                raise ValueError("Zeitstempel ohne Zeitzone")
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        if max(erstellt, geaendert) >= naechste_eroeffnung(tag):
            zu_spaet.append(iso(tag))
            continue
        neu = {"entschieden": erstellt.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
               "auslassen": saeubern(e.get("auslassen")), "nehmen": saeubern(e.get("nehmen")),
               "notiz": " ".join(str(e.get("notiz") or "").split())[:500]}
        alt = gut.get(iso(tag))
        if alt is None or neu["entschieden"] >= alt["entschieden"]:
            gut[iso(tag)] = neu
    return gut, sorted(set(zu_spaet) - set(gut))

def qqq_seit(markt, fx, von, bis):
    """Nasdaq-100 (QQQ) in € vom Schluss am Tag 'von' bis zum Schluss am Tag 'bis', in %."""
    if markt is None or fx is None:
        return None
    idx = markt["idx"][:markt["n_fertig"]]
    kurse = pd.Series(markt["C"][:markt["n_fertig"]], index=idx) / kurs_umrechner(fx, idx)
    a, b = kurse[kurse.index <= als_tag(von, idx)], kurse[kurse.index <= als_tag(bis, idx)]
    if a.empty or b.empty or not a.iloc[-1] > 0:
        return None
    return (b.iloc[-1] / a.iloc[-1] - 1) * 100

def claude_zeilen(stand, papier, markt, fx, zu_spaet):
    """Erklärung, Vergleich seit Versuchsbeginn und Claudes Entscheidungen für den Bericht."""
    ab, start = stand["versuch_ab"], stand["versuch_start"]
    zeilen = [f"Gleiche Regeln wie das Übungsdepot und am {pd.Timestamp(ab):%d.%m.%Y} als genaue Kopie gestartet. "
              f"Einziger Unterschied: Claude lässt einzelne Kauf-Signale aus – mit Begründung, festgehalten vor "
              f"Börsenbeginn im GitHub-Thema „{CLAUDE_THEMA}“ (Tab Issues). Ohne Entscheidung nimmt das Claude-Depot "
              f"alle Signale wie das Übungsdepot."]
    teile = [f"Claude-Depot {de((stand['depotwert'] / start['claude'] - 1) * 100, 1, True)} %"]
    if papier is not None and papier.get("bis") == stand["bis"]:
        teile.append(f"Übungsdepot {de((papier['depotwert'] / start['bot'] - 1) * 100, 1, True)} %")
    q = qqq_seit(markt, fx, ab, stand["bis"])
    if q is not None:
        teile.append(f"Nasdaq-100 {de(q, 1, True)} %")
    zeilen.append(f"Seit Versuchsbeginn ({pd.Timestamp(ab):%d.%m.%Y}, Stand {pd.Timestamp(stand['bis']):%d.%m.%Y}): "
                  + " · ".join(teile) + ". Der Unterschied zum Übungsdepot ist die Wirkung von Claudes Entscheidungen.")
    entsch = stand.get("entscheidungen") or {}
    frueher = [t for t in sorted(entsch) if t < stand["bis"]]
    if frueher:
        t = frueher[-1]
        e = entsch[t]
        teile = []
        if e["auslassen"]:
            teile.append("ausgelassen: " + "; ".join(f"{k} – {g}" for k, g in e["auslassen"].items()))
        if e["nehmen"]:
            teile.append("genommen: " + "; ".join(f"{k} – {g}" for k, g in e["nehmen"].items()))
        if e["notiz"]:
            teile.append(e["notiz"])
        zeilen.append(f"Claudes letzte Entscheidung (Signale vom {datum(pd.Timestamp(t))}, festgehalten "
                      f"{pd.Timestamp(e['entschieden']).tz_convert(BERLIN):%d.%m. %H:%M} Uhr): "
                      + (" · ".join(teile) if teile else "alle Signale genommen") + ".")
    if stand["auftraege"]:
        zeilen.append(f"Zu den neuen Aufträgen (Signale vom {datum(pd.Timestamp(stand['bis']))}) entscheidet Claude bis "
                      f"zur Eröffnung am {datum(naechste_eroeffnung(stand['bis']))} – sonst gelten sie wie beim "
                      f"Übungsdepot.")
    ausgelassen = sum(len(e["auslassen"]) for e in entsch.values())
    if ausgelassen:
        tage = sum(1 for e in entsch.values() if e["auslassen"])
        zeilen.append(f"Bisher {ausgelassen} {'Signal' if ausgelassen == 1 else 'Signale'} an {tage} "
                      f"{'Tag' if tage == 1 else 'Tagen'} ausgelassen.")
    if zu_spaet:
        zeilen.append("Nicht gezählt, weil erst nach Börsenbeginn festgehalten: Signale vom "
                      + ", ".join(datum(pd.Timestamp(t)) for t in zu_spaet))
    return zeilen

def claude_lauf(datei, stand, fehler, papier, daten, extra, roh, fx, fx_je_ticker, zusatz, pausen, einst, waehrung,
                notebook, markt, trend):
    """Claude-Depot (Versuch): startet als genaue Kopie des Übungsdepots und rechnet danach mit denselben Regeln
    weiter – nur verfallen Aufträge, deren Signal Claude rechtzeitig ausgelassen hat."""
    def nur_hinweis(zeilen):
        print("\n" + CLAUDE_TITEL + "".join(f"\n   {z}" for z in zeilen))
        berichte(CLAUDE_TITEL, zeilen)
        return None
    if fehler:
        return nur_hinweis([f"⚠️ {fehler.replace('Papier-Depot', 'Claude-Depot')}"])
    neue, zu_spaet = lies_claude_entscheidungen(einst.claude_entscheidungen)
    if stand is None:
        if papier is None or papier.get("bis") is None:
            return nur_hinweis(["Das Claude-Depot startet, sobald das Übungsdepot weitergerechnet wurde."])
        stand = json.loads(json.dumps(papier))  # genaue Kopie (auch Positionen, Aufträge und Verlauf)
        stand.update({"versuch_ab": papier["bis"], "entscheidungen": {},
                      "versuch_start": {"claude": papier["depotwert"], "bot": papier["depotwert"]}})
        try:
            speichere_papier(datei, stand)
        except OSError as problem:
            return nur_hinweis([f"⚠️ Claude-Depot nicht gespeichert ({problem}) – der nächste Lauf versucht es erneut."])
        nur_hinweis(claude_zeilen(stand, papier, markt, fx, []) + [
            f"Der Versuch beginnt heute mit {de(stand['depotwert'])} {waehrung}, denselben Positionen und Aufträgen wie das "
            f"Übungsdepot. Gespeichert in: {os.path.relpath(datei)}"])
        return stand
    entsch = dict(stand.get("entscheidungen") or {})
    entsch.update({t: e for t, e in neue.items() if t >= stand["versuch_ab"]})
    stand = dict(stand, entscheidungen=entsch)

    def veto(signal_tag, ticker):
        return None if signal_tag is None else (entsch.get(iso(signal_tag)) or {}).get("auslassen", {}).get(ticker)

    return papier_lauf(datei, stand, None, daten, extra, roh, fx, fx_je_ticker, zusatz, pausen, einst, waehrung,
                       notebook, markt, trend, veto=veto, titel=CLAUDE_TITEL,
                       vorne=lambda neu: claude_zeilen(neu, papier, markt, fx, zu_spaet))

# ----------------------------------------------------------------------------
# Übersichtsseite (docs/index.html): der Bot schreibt nur die Daten als JSON, die Seite stellt sie dar
# ----------------------------------------------------------------------------
SIGNAL_ART = {KAUFEN: "kaufen", SHORT: "short", WARTEN: "warten", SICHERN: "sichern", BEOBACHTEN: "beobachten",
              FEHLER: "fehler"}

def json_zahl(x, nachkomma=2):
    """Zahl für JSON (None statt NaN/inf)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nachkomma) if math.isfinite(x) else None

def tages_bilanz(stand, daten):
    """Je Tag im Verlauf eines Papier-Depots: Wert, Änderung zum Vortag und woher sie kam – gekaufte und verkaufte
    Aktien und der Beitrag jeder Position an diesem Tag in € (gekauft: Wert zum Schluss minus Kosten, verkauft: Erlös
    minus Wert vom Vortag, sonst Wert heute minus Wert vom Vortag). Zusammen ergeben die Beiträge die Änderung des
    Depotwerts. Für das Fazit (Tag, Woche, Monat) der Übersichtsseite."""
    verlauf = [(pd.Timestamp(t), float(w)) for t, w in stand.get("verlauf") or []]
    alle = [(p, False) for p in stand.get("trades") or []] + [(p, True) for p in stand.get("positionen") or []]

    def wert_am(p, d, tag):
        i = d["pos"][letzter_tag_bis(d, tag)]
        return positionswert(p, d["C"][i], d["FX"][i])

    tage, vorher, vortag = [], float(stand["startkapital"]), None
    for tag, wert in verlauf:
        gekauft, verkauft, beitraege = [], [], []
        for p, offen in alle:
            kauf = pd.Timestamp(p["kauf_tag"])
            verkauf = None if offen else pd.Timestamp(p["verkauf_tag"])
            if tag < kauf or (verkauf is not None and tag > verkauf):
                continue
            name = strategie_name(p["strategie"])
            if kauf == tag:
                gekauft.append({"ticker": p["ticker"], "strategie": name, "stueck": json_zahl(p["stueck"], 4),
                                "preis": json_zahl(p["einsatz_je_stueck"]), "kosten": json_zahl(p["kosten"])})
            if verkauf == tag:
                verkauft.append({"ticker": p["ticker"], "strategie": name, "grund": p.get("grund") or "",
                                 "ergebnis": json_zahl(p["erloes"] - p["kosten"]), "erloes": json_zahl(p["erloes"]),
                                 "prozent": json_zahl((p["erloes"] / p["kosten"] - 1) * 100, 1) if p["kosten"] else None,
                                 "seit": iso(kauf)})
            d = daten.get(p["ticker"])
            if d is None or not d["n_fertig"]:
                beitraege.append({"ticker": p["ticker"], "betrag": None})  # keine Kurse: Beitrag unbekannt
                continue
            jetzt = p["erloes"] if verkauf == tag else wert_am(p, d, tag)
            davor = p["kosten"] if kauf == tag or vortag is None else wert_am(p, d, vortag)
            beitraege.append({"ticker": p["ticker"], "betrag": json_zahl(jetzt - davor)})
        # Passen die Beiträge nicht zur Änderung (z. B. fehlten Kurse), lieber keine Aufteilung als eine falsche
        if any(b["betrag"] is None for b in beitraege) or abs(sum(b["betrag"] for b in beitraege) - (wert - vorher)) > 1:
            beitraege = None
        tage.append({"tag": iso(tag), "wert": json_zahl(wert), "aenderung": json_zahl(wert - vorher),
                     "gekauft": gekauft, "verkauft": verkauft, "beitraege": beitraege})
        vorher, vortag = wert, tag
    return tage

def depot_export(stand, daten, markt, fx):
    """Ein Papier-Depot (Übungs- oder Claude-Depot) für die Übersichtsseite."""
    if not stand or not stand.get("bis"):
        return None
    werte = pd.Series([w for _, w in stand["verlauf"]], dtype=float)
    vergleich = papier_vergleich(stand, markt, fx)
    positionen = []
    for p in stand["positionen"]:
        d = daten.get(p["ticker"])
        kurs = rate = None
        if d is not None and d["n_fertig"]:
            i = d["n_fertig"] - 1
            kurs, rate = d["C"][i], d["FX"][i]
        wert = positionswert(p, kurs, rate) if kurs is not None else None
        termin = naechster_termin(d, d["idx"][d["n_fertig"] - 1]) if d is not None and d["n_fertig"] else None
        positionen.append({
            "ticker": p["ticker"], "strategie": strategie_name(p["strategie"]), "kauf_tag": str(p["kauf_tag"])[:10],
            "stueck": json_zahl(p["stueck"], 4), "einstieg": json_zahl(p["einsatz_je_stueck"]),
            "stop": json_zahl(p["stop"] / rate) if rate else None, "ziel": json_zahl(p["ziel"] / rate) if rate else None,
            "kurs": json_zahl(kurs / rate) if rate else None, "wert": json_zahl(wert),
            "ergebnis": json_zahl(wert - p["kosten"]) if wert is not None else None,
            # Lage zwischen Stop (0) und Ziel (1) in Kurswährung, für den Balken
            "lage": json_zahl((kurs - p["stop"]) / (p["ziel"] - p["stop"]), 3) if kurs is not None and p["ziel"] != p["stop"]
            else None,
            "einstieg_lage": json_zahl((p["einstieg_usd"] - p["stop"]) / (p["ziel"] - p["stop"]), 3)
            if p["ziel"] != p["stop"] else None,
            "zahlen_tag": iso(termin.date()) if termin is not None else None})
    trades = [{"ticker": t["ticker"], "strategie": strategie_name(t["strategie"]), "kauf_tag": t["kauf_tag"],
               "verkauf_tag": t["verkauf_tag"], "grund": t["grund"], "ergebnis": json_zahl(t["erloes"] - t["kosten"]),
               "prozent": json_zahl((t["erloes"] / t["kosten"] - 1) * 100, 1) if t["kosten"] else None}
              for t in stand["trades"][-30:]][::-1]
    alle = stand["trades"]
    ok, verfallen, nachruecker = ausfuehrbare_auftraege(stand)
    return {
        "angelegt": stand.get("angelegt"), "bis": stand["bis"], "startkapital": json_zahl(stand["startkapital"]),
        "wert": json_zahl(stand["depotwert"]), "bargeld": json_zahl(stand["bargeld"]),
        "verlauf": [[t, json_zahl(w)] for t, w in stand["verlauf"]],
        "qqq": [[iso(t), json_zahl(w)] for t, w in vergleich.items()] if vergleich is not None else None,
        "max_rueckgang": json_zahl(((werte.cummax() - werte) / werte.cummax()).max() * 100, 1) if len(werte) else None,
        "trades_anzahl": len(alle), "gewinner": sum(1 for t in alle if t["erloes"] > t["kosten"]),
        "summe": json_zahl(sum(t["erloes"] - t["kosten"] for t in alle)),
        "positionen": positionen, "trades": trades,
        "auftraege": [{"ticker": a["ticker"], "strategie": strategie_name(a["strategie"])} for a in ok],
        "nachruecker": [{"ticker": a["ticker"], "strategie": strategie_name(a["strategie"])} for a in nachruecker],
        "verfallen": [{"grund": g, "ticker": t} for g, t in verfallen.items()],
        "tage": tages_bilanz(stand, daten),
    }

CHART_TAGE = 60  # Tageskerzen je Chart auf der Übersichtsseite (etwa 3 Monate)
KERZEN_30MIN_MAX = 300  # 30-Minuten-Kerzen je Chart höchstens (ein Monat sind etwa 21 × 13 = 273)

def kerzen_30min(ticker_liste, zeitraum="1mo"):
    """30-Minuten-Kerzen für die Charts der Übersichtsseite (nur Anzeige, die Regeln rechnen mit Tageskerzen):
    {Ticker: {"t": [...], "o": [...], ...}} in Kurswährung. Die Zeit steht als deutsche Uhrzeit in Sekunden
    (so, als wäre sie UTC) – der Chart zeigt sie dadurch ohne Umrechnung richtig an. Liefert Yahoo nichts,
    bleibt es beim Tageschart."""
    ticker_liste = [t for t in dict.fromkeys(ticker_liste) if not ist_krypto(t)]
    if not ticker_liste:
        return {}
    try:
        with YahooRuhig():
            roh = yf.download(ticker_liste, period=zeitraum, interval="30m", auto_adjust=True, group_by="ticker",
                              progress=False, threads=True)
    except Exception as fehler:  # nur Anzeige: ein Fehler hier darf den Lauf nicht stören
        print(f"⚠️ 30-Minuten-Kerzen nicht geladen ({type(fehler).__name__}) – die Charts zeigen nur Tageskerzen.")
        return {}
    erg = {}
    for t in ticker_liste:
        df = tabelle_fuer(roh, t)
        if df is None:
            continue
        df = df.dropna(subset=["Open"]).tail(KERZEN_30MIN_MAX)
        idx = df.index if df.index.tz is not None else df.index.tz_localize("UTC")
        sekunden = (idx.tz_convert(BERLIN).tz_localize(None) - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)
        erg[t] = {"t": [int(x) for x in sekunden],
                  **{k: [json_zahl(x) for x in df[q]] for k, q in (("o", "Open"), ("h", "High"), ("l", "Low"), ("c", "Close"))}}
    return erg

def chart_export(d):
    """Die letzten Tageskerzen einer Aktie für einen Chart auf der Übersichtsseite: Kurse in Kurswährung und der
    Wechselkurs des letzten Tages – die Seite rechnet damit in €, wie bei Stop, Ziel und Limit."""
    n = d["n_fertig"]
    if not n:
        return None
    von = max(0, n - CHART_TAGE)
    return {"faktor": json_zahl(d["FX"][n - 1], 6), "tage": [iso(t) for t in d["idx"][von:n]],
            **{k: [json_zahl(x) for x in d[q][von:n]] for k, q in (("o", "O_ersatz"), ("h", "H"), ("l", "L"), ("c", "C"))}}

def uebersicht_daten(einst, waehrung, zeilen, reihenfolge, plan, im_plan, papier, claude, depot, daten, markt, fx,
                     trend, lern, tagebuch, news, fehlt):
    """Alles, was die Übersichtsseite zeigt, als JSON-fähiges dict."""
    ok = [z for z in zeilen if "_stand" in z]
    stand_tag = max(z["_stand"] for z in ok)
    nach = {z["Ticker"]: z for z in zeilen}
    signale = []
    for t in reihenfolge:
        z = nach[t]
        signale.append({"ticker": t, "art": SIGNAL_ART.get(z.get("Signal"), "fehler"),
                        "strategie": z.get("Strategie") or "", "kurs": json_zahl(z.get("Kurs")),
                        "limit": json_zahl(z.get("Limit")), "stop": json_zahl(z.get("Stop")), "ziel": json_zahl(z.get("Ziel")),
                        "crv": json_zahl(z.get("CRV")), "stueck": json_zahl(z.get("Stück"), 4), "einsatz": json_zahl(z.get("Einsatz")),
                        "chance": json_zahl(z.get("_chance", math.nan) * 100, 0),
                        "chance_praxis": json_zahl(z.get("_chance_praxis"), 0),
                        "muster": ([f"{m} (bullisch)" for m in z["_muster"]["bull"]]
                                   + [f"{m} (bärisch)" for m in z["_muster"]["bear"]]) if z.get("_muster") else [],
                        "muster_praxis": json_zahl(z.get("_muster_praxis"), 0),
                        "musterziel": json_zahl(z.get("_musterziel")), "musterziel_art": z.get("_musterziel_art"),
                        "stimmung": z.get("_stimmung"),
                        "risiko": json_zahl(z.get("Risiko")), "zahlen": z.get("Zahlen") or "", "news": z.get("News") or "",
                        "zahlen_tag": iso(z["_termin"].date()) if z.get("_termin") is not None else None,
                        "branche": BRANCHE.get(t), "im_plan": t in im_plan, "fehler": z.get("_fehler")})
    strategien = []
    for k, s in STRATEGIEN.items():
        if s["richtung"] < 0 and not einst.mit_short:
            continue
        l = lern.get(k, {})
        rs = [e["R"] for e in tagebuch if e["strategie"] == k][-LERNEN_FENSTER:]
        kurve = list(np.round(np.cumsum(rs), 2)) if rs else []
        status = ("aus" if k in einst.sperre_strategien else "pausiert" if l.get("pausiert") else "aktiv")
        strategien.append({"name": strategie_name(k), "regel": s["regel"], "status": status,
                           "trades": l.get("n", 0), "gesamt": l.get("gesamt", 0), "schnitt": json_zahl(l.get("schnitt"), 3),
                           "quote": json_zahl(l.get("quote"), 1), "spanne": json_zahl(l.get("spanne"), 3),
                           "kurve": [json_zahl(x) for x in kurve]})
    schlagzeilen = []
    alle = [z["titel"] for n in (news or {}).values() for z in n.get("zeilen", [])]
    deutsch = auf_deutsch(alle)
    if alle:
        n_deutsch = sum(1 for t in alle if t in deutsch)
        print(f"📰 Schlagzeilen für die Übersichtsseite übersetzt: {n_deutsch} von {len(alle)}"
              + ("" if n_deutsch == len(alle) else " (der Rest bleibt englisch)"))
    for t, n in (news or {}).items():
        for z in n.get("zeilen", []):
            schlagzeilen.append({"ticker": t, "titel": z["titel"], "titel_de": deutsch.get(z["titel"]), "link": z.get("link") or None,
                                 "zeit": z["zeit"].isoformat(),
                                 "quelle": z.get("quelle") or "", "warnt": bool(z.get("warnt")),
                                 "ereignisse": list(z.get("ereignisse") or [])})
    schlagzeilen.sort(key=lambda x: x["zeit"], reverse=True)
    rueckblick = None
    if depot is not None:
        tr = depot["trades"]
        q = None
        if markt is not None and fx is not None:
            idx = markt["idx"][:markt["n_fertig"]]
            kurse = pd.Series(markt["C"][:markt["n_fertig"]], index=idx) / kurs_umrechner(fx, idx)
            kurse = kurse.reindex(kurse.index.union(depot["verlauf"].index)).ffill().reindex(depot["verlauf"].index)
            if kurse.notna().all() and kurse.iloc[0] > 0:
                q = [[iso(t), json_zahl(depot["start_wert"] * w / kurse.iloc[0])] for t, w in kurse.items()]
        rueckblick = {"monate": einst.rueckblick, "start": iso(depot["start"]), "ende": iso(depot["ende"]),
                      "start_wert": json_zahl(depot["start_wert"]), "end_wert": json_zahl(depot["end_wert"]),
                      "max_rueckgang": json_zahl(depot["max_rueckgang"], 1), "trades_anzahl": len(tr),
                      "gewinner": sum(1 for x in tr if x["erloes"] > x["kosten"]),
                      "verlauf": [[iso(t), json_zahl(w)] for t, w in depot["verlauf"].items()], "qqq": q,
                      "halten": [[iso(t), json_zahl(w)] for t, w in depot["vergleich"].items()]
                      if depot["vergleich"] is not None else None}
    claude_teil = depot_export(claude, daten, markt, fx)
    if claude_teil is not None and claude.get("versuch_ab"):
        start = claude["versuch_start"]
        entsch = claude.get("entscheidungen") or {}
        claude_teil.update({
            "versuch_ab": claude["versuch_ab"],
            "seit_start": {"claude": json_zahl((claude["depotwert"] / start["claude"] - 1) * 100, 2),
                           "bot": json_zahl((papier["depotwert"] / start["bot"] - 1) * 100, 2)
                           if papier is not None and papier.get("bis") == claude["bis"] else None,
                           "qqq": json_zahl(qqq_seit(markt, fx, claude["versuch_ab"], claude["bis"]), 2)},
            "entscheidungen": [dict(e, signal_tag=t) for t, e in sorted(entsch.items())[-10:]][::-1],
            "ausgelassen": sum(len(e["auslassen"]) for e in entsch.values())})
    lage = trend.dropna().iloc[-1] if trend is not None and trend.notna().any() else None
    return {
        "version": 1, "erstellt": pd.Timestamp.now(tz=BERLIN).isoformat(timespec="seconds"),
        "daten_bis": iso(stand_tag), "fehlt": iso(fehlt) if fehlt is not None else None,
        "vorlaeufig": any(z["_offen"] for z in ok), "waehrung": waehrung, "konto": json_zahl(einst.konto),
        "risiko": json_zahl(einst.risiko), "repo": os.environ.get("GITHUB_REPOSITORY"),
        "markt": {"ueber_200": None if lage is None else bool(lage == 1)},
        "regeln": {"max_positionen": MAX_POSITIONEN, "max_je_branche": MAX_JE_BRANCHE,
                   "max_risiko": MAX_GESAMTRISIKO_PROZENT, "zeitstopp": ZEITSTOPP_TAGE},
        "gehirn": {"aktien": len(daten), "strategien": len(strategien),
                   "aktiv": sum(1 for s in strategien if s["status"] == "aktiv"),
                   "termine": sum(1 for d in daten.values() if d["termine"] is not None),
                   "schlagzeilen": len(schlagzeilen), "tagebuch": len(tagebuch),
                   "kaufen": sum(1 for x in signale if x["art"] in ("kaufen", "short")),
                   "warten": sum(1 for x in signale if x["art"] == "warten"),
                   "sichern": sum(1 for x in signale if x["art"] == "sichern"), "im_plan": len(im_plan)},
        "signale": signale, "plan": plan, "strategien": strategien, "schlagzeilen": schlagzeilen[:12],
        "papier": depot_export(papier, daten, markt, fx), "claude": claude_teil, "rueckblick": rueckblick,
        "chance_pruefung": chance_export(chance_pruefung(tagebuch, daten)),
        "charts": charts_export(papier, claude, signale, daten),
    }

def charts_export(papier, claude, signale, daten):
    """Charts mit Stop, Ziel und Kauf: offene Positionen beider Depots, Aufträge und Kauf-Signale – Tageskerzen
    und, wenn Yahoo sie liefert, die 30-Minuten-Kerzen des letzten Monats ("m30")."""
    ticker = [t for t in dict.fromkeys(
        [x["ticker"] for st in (papier, claude) if st for x in st["positionen"] + st["auftraege"]]
        + [x["ticker"] for x in signale if x["art"] in ("kaufen", "short")]) if t in daten]
    charts = {t: c for t in ticker if (c := chart_export(daten[t])) is not None}
    for t, m30 in kerzen_30min(list(charts)).items():
        charts[t]["m30"] = m30
    return charts

def chance_export(gruppen):
    """Selbstkontrolle der Ziel-Chance für die Übersichtsseite (Prozentwerte gerundet)."""
    gesamt = chance_gesamt(gruppen)
    if gesamt is None:
        return None
    rund = lambda g: {k: json_zahl(v, 3 if k == "schnitt" else 1) for k, v in g.items()}
    return {**rund(gesamt), "gruppen": [rund(g) for g in gruppen]}

def schreibe_uebersicht(datei, inhalt):
    """Schreibt die Daten der Übersichtsseite (erst in eine Hilfsdatei, dann ersetzen)."""
    ordner = os.path.dirname(os.path.abspath(datei))
    os.makedirs(ordner, exist_ok=True)
    with open(datei + ".tmp", "w", encoding="utf-8") as f:
        json.dump(inhalt, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    os.replace(datei + ".tmp", datei)

# ----------------------------------------------------------------------------
# Live-Kurse für die Übersichtsseite (während der Börsenzeit, ohne Signale und ohne Buchungen)
# ----------------------------------------------------------------------------
def live_tabellen(ticker_liste):
    """Tageskerzen der letzten 3 Monate je Ticker; die heutige läuft bei offener Börse noch (Kurse bei Yahoo etwa
    15 Minuten verzögert). 3 Monate reichen für Kaufdaten offener Positionen und die Split-Prüfung."""
    with YahooRuhig():
        roh = yf.download(list(ticker_liste), period="3mo", interval="1d", auto_adjust=True, group_by="ticker",
                          progress=False, threads=True)
    return {t: df for t in ticker_liste if (df := tabelle_fuer(roh, t)) is not None and len(df) >= 2}

def live_vorschau(stand, tabellen, fx, einst, veto=None):
    """Ein Papier-Depot nach denselben Regeln wie am Morgen weiterrechnen – nur zählt die heutige, noch laufende
    Kerze schon: Käufe zur Eröffnung bis zum Limit, Stop und Ziel nach dem bisherigen Tageshoch und -tief, Zeitstopp
    und Verkauf vor Quartalszahlen zum aktuellen Kurs (gelten erst zum Schluss). Nur zum Anschauen: nichts wird
    gespeichert, endgültig bucht der Morgen-Lauf mit den Schlusskursen. Gibt das Depot für docs/live.json zurück."""
    if not stand or not stand.get("bis"):
        return None
    gemerkt = stand.get("termine") if isinstance(stand.get("termine"), dict) else {}
    daten = {}
    for t in {x["ticker"] for x in stand["positionen"] + stand["auftraege"]}:
        if t not in tabellen:
            return {"bis": stand["bis"], "fehlt": t}
        zahlen = pd.DataFrame(index=pd.to_datetime(gemerkt[t], utc=True)) if gemerkt.get(t) else None
        d = bereite_vor(t, tabellen[t], fx if waehrung_von(t) == "USD" else None, zahlen, einst)
        d["n_fertig"] = d["n"]  # die laufende Kerze zählt schon
        daten[t] = d
    if not daten:  # weder Positionen noch Aufträge: nur Bargeld
        return {"bis": stand["bis"], "wert_schluss": json_zahl(stand["depotwert"]), "wert": json_zahl(stand["bargeld"]),
                "aenderung": json_zahl(stand["bargeld"] - stand["depotwert"]), "positionen": [], "gekauft": [],
                "verkauft": [], "nicht_gekauft": [], "ausgelassen": []}
    neu, erg, bericht = papier_fortschreiben(stand, daten, {}, einst, set(), veto)
    if erg is None:
        return {"bis": stand["bis"], "fehlt": bericht.get("warnung") or "nicht weitergerechnet"}
    bis = stand["bis"]
    positionen = []
    for p in erg["positionen"]:
        d = daten[p["ticker"]]
        kurs = d["C"][d["n"] - 1]
        positionen.append({
            "ticker": p["ticker"], "kurs": json_zahl(p["kurs_jetzt"]), "wert": json_zahl(p["wert"]),
            "ergebnis": json_zahl(p["wert"] - p["kosten"]), "heute": json_zahl((kurs / d["C"][d["n"] - 2] - 1) * 100, 2),
            "lage": json_zahl((kurs - p["stop"]) / (p["ziel"] - p["stop"]), 3) if p["ziel"] != p["stop"] else None,
            "neu": iso(p["kauf_tag"]) > bis})
    gekauft = [{"ticker": x["ticker"], "strategie": strategie_name(x["strategie"]), "kurs": json_zahl(x["einsatz_je_stueck"]),
                "stueck": json_zahl(x["stueck"], 4), "einsatz": json_zahl(x["kosten"])}
               for x in erg["positionen"] + erg["trades"] if iso(x["kauf_tag"]) > bis]
    verkauft = [{"ticker": x["ticker"], "grund": x["grund"], "ergebnis": json_zahl(x["erloes"] - x["kosten"]),
                 "prozent": json_zahl((x["erloes"] / x["kosten"] - 1) * 100, 1) if x["kosten"] else None,
                 "zum_schluss": x["grund"] in ("Zeitstopp", "vor Quartalszahlen")} for x in erg["trades"]]
    return {"bis": bis, "wert_schluss": json_zahl(stand["depotwert"]), "wert": json_zahl(erg["depotwert"]),
            "aenderung": json_zahl(erg["depotwert"] - stand["depotwert"]), "positionen": positionen,
            "gekauft": gekauft, "verkauft": verkauft, "nicht_gekauft": bericht["nicht_ausgefuehrt"],
            "ausgelassen": bericht["ausgelassen"]}

def live_daten(einst):
    """Inhalt von docs/live.json. Liest Papier- und Claude-Depot (und „Meine Regeln“) nur, schreibt sie nie."""
    if einst.gehirn:
        ordner, _ = papier_pfad(einst.gehirn)
        if ordner:
            einst.sperre_ticker, einst.sperre_strategien, _ = lies_meine_regeln(ordner)
    staende = {}
    for name, wert in (("papier", einst.papier), ("claude", einst.claude_depot)):
        if wert:
            pfad, _ = papier_pfad(wert)
            staende[name] = lade_papier(pfad, False)[0] if pfad else None
    ticker = list(dict.fromkeys(list(einst.ticker_liste) + [MARKT_TICKER, FX_TICKER]
                                + [x["ticker"] for st in staende.values() if st
                                   for x in st["positionen"] + st["auftraege"]]))
    tabellen = live_tabellen(ticker)
    fx = tabellen[FX_TICKER]["Close"] if FX_TICKER in tabellen else None
    fx_jetzt = float(fx.iloc[-1]) if fx is not None else None
    letzte = {t: (float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])) for t, df in tabellen.items()}
    us = [t for t in tabellen if waehrung_von(t) == "USD" and not ist_krypto(t) and "=" not in t]
    tage = [tabellen[t].index[-1] for t in us]
    aktien = {}
    for t in einst.ticker_liste:
        rate = fx_jetzt if waehrung_von(t) == "USD" else 1.0
        if t in letzte and rate:
            kurs, vortag = letzte[t]
            aktien[t] = {"kurs": json_zahl(kurs / rate), "heute": json_zahl((kurs / vortag - 1) * 100, 2)}
    depots = {}
    if fx is not None:
        claude = staende.get("claude")
        entsch = dict((claude or {}).get("entscheidungen") or {})
        if claude:
            neue, _ = lies_claude_entscheidungen(einst.claude_entscheidungen)
            entsch.update({t: e for t, e in neue.items() if t >= claude.get("versuch_ab", "")})

        def veto(signal_tag, t):
            return None if signal_tag is None else (entsch.get(iso(signal_tag)) or {}).get("auslassen", {}).get(t)

        for name, st in staende.items():
            depots[name] = live_vorschau(st, tabellen, fx, einst, veto if name == "claude" else None)
    q = letzte.get(MARKT_TICKER)
    # heutige (laufende) Kerze je Aktie für die Charts der Seite, in Kurswährung wie in daten.json
    kerzen = {t: [iso(df.index[-1]), *(json_zahl(float(df[k].iloc[-1])) for k in ("Open", "High", "Low", "Close"))]
              for t, df in tabellen.items() if t not in (MARKT_TICKER, FX_TICKER)}
    # und die 30-Minuten-Kerzen von heute (Watchlist, Positionen und Aufträge)
    kerzen30 = kerzen_30min([t for t in ticker if t not in (MARKT_TICKER, FX_TICKER)], "1d")
    return {
        "version": 1, "erstellt": pd.Timestamp.now(tz=BERLIN).isoformat(timespec="seconds"),
        "kurse_vom": iso(max(set(tage), key=tage.count)) if tage else None,
        "boerse_offen": any(kerze_noch_offen(tabellen[t], t) for t in us), "fx": json_zahl(fx_jetzt, 4),
        "nasdaq": {"heute": json_zahl((q[0] / q[1] - 1) * 100, 2)} if q else None,
        "aktien": aktien, "kerzen": kerzen, "kerzen30": kerzen30, **depots,
    }

def schreibe_live(einst):
    """--live: Live-Kurse holen und schreiben. Gibt die Daten zurück (None, wenn Yahoo nichts geliefert hat)."""
    daten = live_daten(einst)
    if not daten["aktien"] and not daten.get("papier"):
        print("❌ Keine Live-Kurse von Yahoo – nichts geschrieben.")
        return None
    schreibe_uebersicht(einst.live, daten)
    p = daten.get("papier")
    print(f"📡 Live-Kurse gespeichert: {einst.live} · Kurse vom {daten['kurse_vom']}"
          + (" (Börse offen)" if daten["boerse_offen"] else "")
          + (f" · Übungsdepot {de(p['wert'])} € ({de(p['aenderung'], 2, True)} € seit dem Schluss am {p['bis']})"
             if p and p.get("wert") is not None else "")
          + (f" · heute gekauft: {', '.join(x['ticker'] for x in p['gekauft'])}" if p and p.get("gekauft") else "")
          + (f" · heute verkauft: {', '.join(x['ticker'] + ' (' + x['grund'] + ')' for x in p['verkauft'])}"
             if p and p.get("verkauft") else ""))
    return daten

# ----------------------------------------------------------------------------
# Gehirn für Obsidian: Notizen, die der Bot bei jedem Lauf schreibt – und „Meine Regeln“, die er liest
# ----------------------------------------------------------------------------
GEHIRN_ANFANG = "%% BOT-ANFANG – diesen Teil schreibt der Bot bei jedem Lauf neu. %%"
GEHIRN_ANFANG_EINMAL = "%% BOT-ANFANG – einmal vom Bot geschrieben und danach nicht mehr geändert. %%"
GEHIRN_ENDE = "%% BOT-ENDE %%"
REGELN_DATEI = "Meine Regeln.md"

class NotizFehler(Exception):
    """Eine Notiz konnte nicht gelesen oder geschrieben werden (die übrigen Notizen werden trotzdem geschrieben)."""
    def __init__(self, pfad, grund):
        super().__init__(f"{pfad} {grund}")
        self.pfad, self.grund = pfad, grund

def notiz_name(text):
    """Dateiname für Obsidian auf Windows, Android und iPhone: Zeichen, die Links oder Dateisysteme stören, werden
    ersetzt (auch %%, Punkt oder Leerzeichen am Rand, reservierte Windows-Namen wie CON oder NUL)."""
    name = unicodedata.normalize("NFC", str(text)).replace("%%", "%")
    name = re.sub(r'[\\/:*?"<>|#^\[\]\x00-\x1f]', "-", name).strip(" .") or "-"
    if re.fullmatch(r"(CON|PRN|AUX|NUL|COM\d|LPT\d)(\..*)?", name, re.IGNORECASE):
        name += "_"
    return name

def strategie_datei(key):
    s = STRATEGIEN[key]
    return notiz_name(f"{s['name']} {'Long' if s['richtung'] > 0 else 'Short'}")

def link_strategie(key):
    return f"[[Strategien/{strategie_datei(key)}|{strategie_name(key)}]]"

def link_aktie(t):
    return f"[[Aktien/{notiz_name(t)}|{t}]]"

def r_text(r, nachkomma=1):
    return f"{de(r, nachkomma, True)} R"

def dekodiere(roh):
    """Text einer Notiz – auch wenn ein Windows-Editor sie nicht als UTF-8 gespeichert hat."""
    kodierungen = (("utf-16",) if roh[:2] in (b"\xff\xfe", b"\xfe\xff") else ()) + ("utf-8-sig", "cp1252")
    for kodierung in kodierungen:
        try:
            return roh.decode(kodierung)
        except ValueError:
            continue
    return roh.decode("utf-8", errors="replace")

def yaml_wert(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return str(round(float(v), 2)) if math.isfinite(v) else '""'
    if isinstance(v, (list, tuple)):  # Listen untereinander – so schreibt sie Obsidian selbst
        return "".join(f"\n  - {yaml_wert(x)}" for x in v)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
        return str(v)
    return json.dumps(str(v), ensure_ascii=False)

def frontmatter_teilen(text):
    """(Frontmatter ohne die ---‑Zeilen, Rest). Frontmatter gibt es nur, wenn die Datei mit --- beginnt."""
    m = re.match(r"---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)", text, re.S | re.M)
    return (m.group(1), text[m.end():]) if m else ("", text)

def eigenschaften_bloecke(frontmatter):
    """Frontmatter in Einträge zerlegen: {Name: Originalzeilen}; eingerückte Folgezeilen (z. B. '  - x') gehören dazu."""
    bloecke, name = {}, None
    for zeile in frontmatter.splitlines():
        m = re.match(r"([^\s#:-][^:]*):(.*)$", zeile)
        if m:
            name = m.group(1).strip()
            bloecke[name] = [zeile]
        elif name is not None and zeile.strip():
            bloecke[name].append(zeile)
    return bloecke

def tags_aus(block):
    """Tag-Werte aus einem tags-Eintrag (Liste untereinander, [a, b] oder einzelner Wert)."""
    werte = [m.group(1) for z in block[1:] for m in [re.match(r"\s*-\s*(.+?)\s*$", z)] if m]
    kopf = block[0].split(":", 1)[1].strip()
    if kopf.startswith("["):
        werte += kopf.strip("[]").split(",")
    elif kopf:
        werte += re.split(r"[,\s]+", kopf)
    return [w.strip().strip("'\"").lstrip("#") for w in werte if w.strip().strip("'\"")]

def schreibe_notiz(pfad, inhalt, eigenschaften=None, nur_neu=False, anfang=GEHIRN_ANFANG, rest_neu=""):
    """Schreibt eine Notiz. Der Bot-Teil steht zwischen BOT-ANFANG und BOT-ENDE und wird jedes Mal ersetzt. Was
    du darunter oder darüber schreibst und eigene Eigenschaften (Properties, Tags) bleiben erhalten.
    nur_neu: eine bestehende Notiz nicht mehr ändern. Gibt zurück, ob die Notiz neu angelegt wurde."""
    alt = None
    if os.path.exists(pfad):
        if nur_neu:
            return False
        try:
            with open(pfad, "rb") as f:
                alt = dekodiere(f.read())
        except OSError as fehler:  # nie überschreiben, was sich nicht lesen ließ
            raise NotizFehler(pfad, f"nicht lesbar ({fehler.strerror or type(fehler).__name__}) – "
                                    "diesmal nicht aktualisiert") from fehler
    eigenschaften = dict(eigenschaften or {})
    eigene, oben, rest = [], "", rest_neu
    if alt is not None:
        frontmatter, koerper = frontmatter_teilen(alt.replace("\r\n", "\n"))
        bloecke = eigenschaften_bloecke(frontmatter)
        if "tags" in eigenschaften and "tags" in bloecke:
            eigenschaften["tags"] = list(dict.fromkeys(list(eigenschaften["tags"]) + tags_aus(bloecke["tags"])))
        eigene = [z for name, b in bloecke.items() if name not in eigenschaften for z in b]
        start = koerper.find("%% BOT-ANFANG")
        if start >= 0 and GEHIRN_ENDE in koerper[start:]:
            oben, rest = koerper[:start], koerper[start:].split(GEHIRN_ENDE, 1)[1]
        elif start >= 0:  # BOT-ENDE gelöscht: alten Bot-Teil ersetzen, deine Abschnitte darunter behalten
            m = re.search(r"^#+ Meine (Notizen|Gedanken)\b", koerper[start:], re.M)
            oben, rest = koerper[:start], ("\n\n" + koerper[start + m.start():] if m else rest_neu)
        else:  # fremde Notiz ohne Markierung: nichts verlieren
            rest = "\n\n" + koerper
    kopf = ""
    if eigenschaften or eigene:
        kopf = ("---\n" + "".join(f"{k}:{'' if isinstance(v, (list, tuple)) else ' '}{yaml_wert(v)}\n"
                                  for k, v in eigenschaften.items())
                + "".join(z + "\n" for z in eigene) + "---\n")
    text = kopf + oben + anfang + "\n" + inhalt.rstrip() + "\n" + GEHIRN_ENDE + rest
    if text == alt:
        return False  # unverändert: nicht neu schreiben (weniger Abgleich-Konflikte auf Handy und PC)
    ordner = os.path.dirname(pfad) or "."
    zwischen = os.path.join(ordner, "." + os.path.basename(pfad) + ".tmp")  # Punkt-Dateien sieht Obsidian nicht
    try:
        os.makedirs(ordner, exist_ok=True)
        with open(zwischen, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(zwischen, pfad)
    except OSError as fehler:
        raise NotizFehler(pfad, f"nicht gespeichert ({fehler.strerror or type(fehler).__name__})") from fehler
    return alt is None

# --- Meine Regeln: der Bot liest die angehakten Kästchen ----------------------
def regel_schluessel(text):
    t = str(text).replace(" ", " ").replace("↑", " long ").replace("↓", " short ").lower()
    t = re.sub(r"[()\-_]", " ", t)
    return " ".join(t.split())

def strategien_aus_text(text):
    """Strategien zu einem Eintrag, z. B. 'EMA-Kreuz ↑', 'EMA-Kreuz Long' oder 'MACD-Wende' (dann beide Richtungen)."""
    such = regel_schluessel(text)
    treffer = [k for k in STRATEGIEN if such in (regel_schluessel(strategie_name(k)), regel_schluessel(k))]
    return treffer or [k for k in STRATEGIEN if such == regel_schluessel(STRATEGIEN[k]["name"])]

def regel_eintrag(text):
    """Text eines Kästchens ohne Link-Klammern, Formatierung und Kommentar (alles nach „ – “)."""
    eintrag = re.sub(r"\[\[(?:[^\]|]*/)?([^\]|]*)(?:\|([^\]]*))?\]\]", lambda m: m.group(2) or m.group(1), text)
    return re.sub(r"\s+[–—-]\s.*$", "", eintrag).strip().strip("`*_").strip()

def lies_meine_regeln(ordner):
    """(gesperrte Ticker, ausgeschaltete Strategien, Hinweise) aus 'Meine Regeln.md'. Zählt nur angehakte Kästchen
    (- [x]) unter Überschriften mit „Aktie“ bzw. „Strateg“ (tiefere Überschriften gehören dazu). Bricht nie ab."""
    try:
        with open(os.path.join(ordner, REGELN_DATEI), "rb") as f:
            text = dekodiere(f.read())
    except OSError:
        return frozenset(), frozenset(), []
    ticker, strategien, unbekannt, ausserhalb = set(), set(), [], []
    bereich, ebene = None, 0
    for zeile in text.splitlines():
        kopf = re.match(r"\s*(#{1,6})\s+(.*)", zeile)
        if kopf:
            n, titel = len(kopf.group(1)), kopf.group(2).lower()
            neu = "ticker" if ("aktie" in titel or "ticker" in titel) else "strategie" if "strateg" in titel else None
            if neu or bereich is None or n <= ebene:
                bereich, ebene = neu, n
            continue
        box = re.match(r"\s*(?:[-*+]|\d+[.)])\s+\[[xX]\]\s+(.+?)\s*$", zeile)
        if not box:
            continue
        eintrag = regel_eintrag(box.group(1))
        wort = eintrag.split()[0].upper() if eintrag.split() else ""
        if bereich is None:
            if strategien_aus_text(eintrag) or re.fullmatch(r"[A-Z0-9^][A-Z0-9.\-=^]{0,9}", eintrag.split()[0] if eintrag else ""):
                ausserhalb.append(eintrag)
        elif bereich == "ticker":
            if re.fullmatch(r"[A-Z0-9^][A-Z0-9.\-=^]*", wort):
                ticker.add(wort)
            else:
                unbekannt.append(eintrag)
        else:
            treffer = strategien_aus_text(eintrag)
            strategien.update(treffer)
            if not treffer:
                unbekannt.append(eintrag)
    hinweise = []
    if unbekannt:
        hinweise.append(f"In „Meine Regeln“ nicht erkannt: {', '.join(unbekannt)} – Schreibweise wie in der Liste verwenden.")
    if ausserhalb:
        hinweise.append(f"In „Meine Regeln“ angehakt, aber nicht unter „Aktien sperren“ bzw. „Strategien ausschalten“ – "
                        f"nicht berücksichtigt: {', '.join(ausserhalb)}.")
    return frozenset(ticker), frozenset(strategien), hinweise

def meine_regeln_vorlage(ticker_liste):
    zeilen = ["# 📝 Meine Regeln für den Bot", "",
              "Der Bot liest diese Seite bei jedem Lauf. **Haken setzen = Regel gilt.** Er versteht nur die Kästchen – "
              "für eigene Gedanken ist unten Platz.", "",
              "> [!tip] So geht's",
              "> - Kästchen antippen, damit ein Haken erscheint. Haken weg = Regel aus.",
              "> - Eine andere Aktie sperren: unter „Aktien sperren“ eine neue Zeile `- [x] KÜRZEL`, z. B. `- [x] TSLA` "
              "(das Kürzel wie im Bot, nicht der Firmenname).",
              "> - Ein kurzer Grund darf dahinter stehen: `- [x] HIMS – zu wild`.",
              "> - Damit der Bot den Haken sieht, muss die Seite bei GitHub ankommen: in Obsidian danach "
              "**Git: Commit-and-sync** (braucht den Zugangs-Token aus der Anleitung) – oder gleich auf GitHub abhaken. "
              "Ob es angekommen ist, steht nach dem nächsten Lauf auf der Startseite unter „Deine Regeln“.",
              "> - Ab dem nächsten Lauf gilt die Regel für Signale und Papier-Depot; offene Aufträge dafür werden "
              "gestrichen, offene Positionen laufen bis Stop, Ziel, Zeitstopp oder vor Quartalszahlen weiter. Im "
              "Rückblick (Simulation der letzten Monate) gilt sie auch rückwirkend.", "",
              "## Aktien sperren (der Bot kauft oder shortet sie nicht)", ""]
    zeilen += [f"- [ ] {t}" for t in ticker_liste]
    zeilen += ["", "## Strategien ausschalten (zusätzlich zur Lernregel des Bots)", ""]
    zeilen += [f"- [ ] {strategie_name(k).replace(chr(160), ' ')}" for k in STRATEGIEN]
    zeilen += ["", "## Meine Notizen", "", "Hier kannst du frei schreiben – der Bot liest diesen Teil nicht.", ""]
    return "\n".join(zeilen)

# --- Auswertungen fürs Gehirn ----------------------------------------------------
def short_aus(key, einst):
    return STRATEGIEN[key]["richtung"] < 0 and not einst.mit_short

def strategie_status(key, stand, einst):
    s = stand[key]
    if short_aus(key, einst):
        return "– aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)"
    if key in einst.sperre_strategien:
        return "⛔ aus – von dir ausgeschaltet ([[Meine Regeln]])"
    if not einst.lernen:
        return "– (Lernen ausgeschaltet)"
    if s["im_minus"]:
        return f"⏸ aus – über ihre ganze Geschichte im Minus (Ø {r_text(s['gesamt_schnitt'], 2)} über {s['gesamt']} Trades)"
    if s["pausiert"]:
        return f"⏸ pausiert – die letzten {s['n']} Trades liefen schlecht (Ø {r_text(s['schnitt'], 2)})"
    if s["n"] < LERNEN_MIN_TRADES:
        return f"aktiv – lernt noch ({s['n']}/{LERNEN_MIN_TRADES} Trades)"
    return f"✅ aktiv (Ø {r_text(s['schnitt'], 2)} über die letzten {s['n']} Trades)"

def kennzahlen(werte):
    """Anzahl, Ø, Trefferquote, Summe einer Liste von R-Werten."""
    n = len(werte)
    if not n:
        return None
    return {"n": n, "schnitt": sum(werte) / n, "quote": sum(1 for x in werte if x > 0) / n * 100, "summe": sum(werte)}

def kennzahl_text(k):
    if not k:
        return "noch keine Trades"
    return f"{k['n']} {'Trade' if k['n'] == 1 else 'Trades'} · Ø {r_text(k['schnitt'], 2)} · Treffer {de(k['quote'], 0)} %"

def rangliste(eintraege, anzahl=3):
    """Aktien nach Ø R (beste zuerst); bei vielen nur die besten und schwächsten."""
    zeilen = [f"{i + 1}. {link_aktie(t)}: {kennzahl_text(k)}" for i, (t, k) in enumerate(eintraege)]
    if len(zeilen) > 2 * anzahl:
        zeilen = zeilen[:anzahl] + ["…"] + zeilen[-anzahl:]
    return zeilen

def papier_trade_info(tr, daten):
    """Kennzahlen eines abgeschlossenen Papier-Depot-Trades (Beträge in €, Kurse wie im Bericht)."""
    r = tr["richtung"]
    je_dollar = tr["einsatz_je_stueck"] / tr["einstieg_usd"] if tr["einstieg_usd"] else 1.0
    gewinn = tr["erloes"] - tr["kosten"]
    risiko = tr["risiko_eur"]
    info = {"ticker": tr["ticker"], "r": r, "strategie": tr["strategie"], "kauf_tag": str(tr["kauf_tag"])[:10],
            "verkauf_tag": str(tr["verkauf_tag"])[:10], "grund": tr["grund"], "gewinn": gewinn,
            "R": gewinn / risiko if risiko > 0 else 0.0, "einstieg": tr["einsatz_je_stueck"],
            "ausstieg": tr["verkauf_preis"], "stop": tr["stop"] * je_dollar, "ziel": tr["ziel"] * je_dollar,
            "einsatz": tr["kosten"], "stueck": tr["stueck"],
            "crv": r * (tr["ziel"] - tr["einstieg_usd"]) / (r * (tr["einstieg_usd"] - tr["stop"]))
            if r * (tr["einstieg_usd"] - tr["stop"]) > 0 else np.nan,
            "tage": None, "tage_art": "Handelstage", "mfe": None, "mae": None, "chance": math.nan, "muster": None}
    d = daten.get(tr["ticker"])
    if d is not None:
        a = d["pos"].get(als_tag(info["kauf_tag"], d["idx"]))
        b = d["pos"].get(als_tag(info["verkauf_tag"], d["idx"]))
        if a is not None and a >= 1 and "VOLA" in d:
            info["chance"] = ziel_chance(d["C"][a - 1], tr["ziel"], d["VOLA"][a - 1])
            info["muster"] = muster_am_tag(d, a - 1)
        if a is not None and b is not None and b >= a:
            info["tage"] = b - a + 1
            hoch, tief = np.nanmax(d["H"][a:b + 1]), np.nanmin(d["L"][a:b + 1])
            eins = abs(tr["einstieg_usd"] - tr["stop"])
            if eins > 0:
                bester, schlechtester = (hoch, tief) if r > 0 else (tief, hoch)
                info["mfe"] = r * (bester - tr["einstieg_usd"]) / eins
                info["mae"] = r * (schlechtester - tr["einstieg_usd"]) / eins
    if info["tage"] is None:
        info["tage"] = max((pd.Timestamp(info["verkauf_tag"]) - pd.Timestamp(info["kauf_tag"])).days, 0) + 1
        info["tage_art"] = "Kalendertage"
    return info

def trade_lehren(info, stand, einst):
    """Was der Bot aus einem abgeschlossenen Trade festhält (Regeln, keine Vermutungen)."""
    lehren, g, tage = [], info["grund"], f"{info['tage']} {info['tage_art']}"
    ergebnis = r_text(info["R"], 2)
    if g.startswith("Ziel"):
        lehren.append(f"✅ Der Plan ging auf: Ziel nach {tage}"
                      + (" – mit einer Kurslücke sogar darüber hinaus." if "Kurslücke" in g else "."))
    elif g == "Stop (Kurslücke)":
        lehren.append(f"⚠️ Kurslücke über den Stop: Die Aktie eröffnete schon hinter dem Stop. Geplant war ein Verlust von "
                      f"etwa 1 R ({prozent(einst.risiko)} % des Kontos), es wurden {ergebnis}. Das kann kein Stop "
                      f"verhindern – deshalb plant der Bot je Trade nur wenig Risiko ein.")
    elif g == "Stop":
        quote = 100 / (1 + info["crv"]) if info["crv"] and math.isfinite(info["crv"]) else None
        lehren.append(f"❌ Stop nach {tage} – Verlust wie geplant ({ergebnis}). Das gehört dazu"
                      + (f": Bei einem Chance-Risiko-Verhältnis von {de(info['crv'], 1)} reichen auf Dauer etwa "
                         f"{de(quote, 0)} % Treffer." if quote else "."))
    elif g == "Zeitstopp":
        lehren.append(f"⏱ Nach {ZEITSTOPP_TAGE} Handelstagen weder Ziel noch Stop – der Bot steigt aus, damit das Geld "
                      f"nicht festliegt ({ergebnis}).")
    elif g == "vor Quartalszahlen":
        lehren.append(f"📅 Vor den Quartalszahlen verkauft ({ergebnis}) – Regel: keine Position über die Zahlen halten, "
                      f"weil der Kurs dann stark springen kann.")
    if info["mfe"] is not None:
        if gewinn_abgegeben(info):
            lehren.append(f"↩️ Lag zwischendurch schon bei {r_text(info['mfe'])} im Plus (mehr als der halbe Weg zum "
                          f"Ziel) und endete trotzdem bei "
                          f"{ergebnis}. Der Bot zieht den Stop nicht nach (im Test half das nicht, siehe "
                          f"[[Notizen/Gelernt – Stop nachziehen und absichern]]) – wie oft das vorkommt, zählt [[Lehren]].")
        elif info["R"] > 0 and info["mae"] is not None and info["mae"] <= -0.7:
            lehren.append(f"😅 Knapp: Zwischendurch lag der Trade bei {r_text(info['mae'])} – fast wäre der Stop gefallen.")
    if info["strategie"] in stand:
        lehren.append(f"🧠 {link_strategie(info['strategie'])} beim Schreiben dieser Notiz: "
                      f"{strategie_status(info['strategie'], stand, einst)}.")
    return lehren

MUSTER_GRUPPEN = (("bull", "bullisches Kerzenmuster (am Signaltag oder Tag davor)"),
                  ("bear", "bärisches Kerzenmuster am Signaltag"), ("keins", "kein Kerzenmuster"))

def muster_lehren(gruppen):
    """Abschnitt der Lehren-Seite: Laufen Signale mit Kerzenmuster (Poster) besser als ohne?"""
    text = ["", "## 🕯️ Selbstkontrolle: Kerzenmuster", "",
            "Bei jedem Signal zeigt der Bot die Kerzenmuster vom Poster (z. B. Hammer, Bullish Engulfing, Shooting Star) "
            "und bei Ausbrüchen und Doppelböden das Musterziel. Er kauft **nicht** danach – als Bestätigung, Warnung, "
            "Vorrang oder Ziel hat das im Test über 16 Jahre nicht geholfen (siehe [[Notizen/Gelernt – Muster und "
            "Lehrbücher]]). Hier prüft er an allen gedachten Kauf-Trades weiter, ob sich das ändert.", ""]
    if not gruppen:
        return text + ["- Noch keine gedachten Trades."]
    text += ["| Gruppe | Trades | im Plus | Ø je Trade |", "| --- | --- | --- | --- |"]
    text += [f"| {name} | {gruppen[g]['n']} | {de(gruppen[g]['quote'], 0)} % | {r_text(gruppen[g]['schnitt'], 2)} |"
             for g, name in MUSTER_GRUPPEN if g in gruppen]
    if "keins" in gruppen and ("bull" in gruppen or "bear" in gruppen):
        abst = [abs(gruppen[g]["quote"] - gruppen["keins"]["quote"]) for g in ("bull", "bear") if g in gruppen]
        text += ["", "- " + ("Mit und ohne Muster liegen nah beieinander – die Muster sagen bei diesen Strategien wenig "
                             "voraus." if max(abst) < 3 else "Die Gruppen liegen mehr als 3 Prozentpunkte auseinander. "
                             "Erst bei vielen Trades und in allen Zeiträumen wäre das ein Grund für einen neuen Test.")]
    return text

def nachrichten_lehren(gruppen, n_log, mindestens=30):
    """Abschnitt der Lehren-Seite: Laufen Signale mit guten Nachrichten besser? (gesammelt ab dem Start der Funktion)"""
    text = ["", "## 📰 Selbstkontrolle: Nachrichten-Stimmung", "",
            "Zu jedem Signal zählt der Bot die guten und schlechten Schlagzeilen der letzten Tage (z. B. Hochstufung, "
            "gute Quartalszahlen bzw. Herabstufung, Klage). Schlechte sperren den Kauf wie bisher; gute ändern nichts. "
            "Alte Schlagzeilen gibt es nicht, darum sammelt er ab jetzt und prüft hier, ob Signale mit guten Nachrichten "
            f"wirklich besser laufen. Mitentscheiden dürfte die Stimmung erst, wenn jede Gruppe mindestens {mindestens} "
            "Trades hat und der Unterschied deutlich ist.", ""]
    if not gruppen:
        return text + [f"- Gesammelt: {n_log} Signal{'' if n_log == 1 else 'e'} mit Schlagzeilen, davon noch keins mit "
                       "abgeschlossenem Trade."]
    namen = {"gut": "mehr gute Schlagzeilen", "schlecht": "mehr schlechte", "neutral": "gleich viele oder keine"}
    text += ["| Stimmung am Signaltag | Trades | im Plus | Ø je Trade |", "| --- | --- | --- | --- |"]
    text += [f"| {namen[g]} | {gruppen[g]['n']} | {de(gruppen[g]['quote'], 0)} % | {r_text(gruppen[g]['schnitt'], 2)} |"
             for g in ("gut", "schlecht", "neutral") if g in gruppen]
    zu_wenig = [namen[g] for g in ("gut", "neutral") if gruppen.get(g, {}).get("n", 0) < mindestens]
    text += ["", f"- Gesammelt: {n_log} Signal{'' if n_log == 1 else 'e'} mit Schlagzeilen. " + (
        f"Noch zu wenige Trades für ein Urteil ({', '.join(zu_wenig)})." if zu_wenig else
        "Genug Trades für einen ersten Vergleich – ein Unterschied wäre ein Grund für einen sauberen Test.")]
    return text

def chance_lehren(gruppen):
    """Abschnitt der Lehren-Seite: Stimmt die Ziel-Chance nach Black-Scholes – und sagt sie etwas über Gewinner?"""
    text = ["", "## 📐 Selbstkontrolle: Ziel-Chance nach Black-Scholes", "",
            f"Bei jedem Signal rechnet der Bot nach dem Black-Scholes-Modell aus dem Optionsskript aus, wie wahrscheinlich "
            f"der Kurs das Ziel innerhalb von {ZEITSTOPP_TAGE} Handelstagen mindestens einmal berührt (aus der Schwankung "
            f"der letzten {VOLA_TAGE} Tage). Er kauft **nicht** danach – im Test über 16 Jahre hat das nichts gebracht "
            "(siehe [[Notizen/Gelernt aus dem Optionsskript]]). Hier prüft er an allen gedachten Trades, ob die Formel "
            "stimmt. Bei jedem Signal zeigt er neben der Formel auch, wie oft das Ziel in dessen Gruppe wirklich berührt "
            "wurde (Spalte „Ziel wirklich berührt“).", ""]
    gesamt = chance_gesamt(gruppen)
    if gesamt is None:
        return text + ["- Noch zu wenige gedachte Trades, nach denen schon 20 Handelstage vorbei sind."]
    stufe = lambda g: (f"unter {de(g['bis'] * 100, 0)} %" if g["von"] == 0 else f"ab {de(g['von'] * 100, 0)} %"
                       if g["bis"] > 1 else f"{de(g['von'] * 100, 0)}–{de(g['bis'] * 100, 0)} %")
    text += ["| Ziel-Chance laut Formel | Signale | Ø vorhergesagt | Ziel wirklich berührt | Trades im Plus | Ø je Trade |",
             "| --- | --- | --- | --- | --- | --- |"]
    text += [f"| {stufe(g)} | {g['n']} | {de(g['chance'], 0)} % | {de(g['beruehrt'], 0)} % | {de(g['quote'], 0)} % "
             f"| {r_text(g['schnitt'], 2)} |" for g in gruppen]
    text += ["", f"- Zusammen: {gesamt['n']} Signale, vorhergesagt Ø {de(gesamt['chance'], 0)} %, berührt "
             f"{de(gesamt['beruehrt'], 0)} % – " + ("die Formel liegt nah dran" if gesamt["abstand"] <= 5 else
                                                 "die Formel liegt deutlich daneben: Die Aktien schwanken anders, als "
                                                 "das Modell annimmt")
             + f" (je Gruppe im Schnitt {de(gesamt['abstand'], 0)} Prozentpunkte Abstand)."]
    quoten = [g["quote"] for g in gruppen]
    text.append(f"- Trades im Plus je Gruppe: {de(min(quoten), 0)} bis {de(max(quoten), 0)} %. Die Formel sagt, wie weit "
                "eine Aktie schwankt – nicht, in welche Richtung. Ob ein Trade gewinnt, hängt davon ab, ob das Ziel vor "
                "dem Stop kommt.")
    return text

def gewinn_abgegeben(info):
    """Erst mehr als den halben Weg zum Ziel im Plus, am Ende trotzdem nicht im Gewinn (Ziel-Ausstiege zählen nicht)."""
    return (info["mfe"] is not None and info["R"] <= 0 and not info["grund"].startswith("Ziel")
            and math.isfinite(info["crv"]) and info["crv"] > 0 and info["mfe"] >= 0.5 * info["crv"])

def lern_wechsel(pausen, tage, key, seit):
    """Wann die Strategie pausiert bzw. wieder aktiv wurde (Tage nach 'seit')."""
    wechsel, vorher = [], None
    for tag in tage:
        jetzt = key in pausen.get(tag, frozenset())
        if vorher is not None and jetzt != vorher and tag > seit:
            wechsel.append((tag, jetzt))
        vorher = jetzt
    return wechsel

def schreibe_gehirn(ordner, einst, waehrung, zeilen, tagebuch, stand, pausen, alle_tage, daten, papier, depot, trend,
                    papier_hinweis=None):
    """Schreibt alle Notizen des Gehirns. Gibt (Zahl neuer Trade-Notizen, Hinweise) zurück; eine Notiz, die nicht
    gelesen oder geschrieben werden kann, wird übersprungen und gemeldet."""
    ok = [z for z in zeilen if "_stand" in z]
    heute = max(z["_stand"] for z in ok)
    tag_name = f"{heute:%Y-%m-%d}"
    jahr, kw, _ = heute.isocalendar()
    woche_name = f"{jahr}-W{kw:02d}"
    vorlaeufig = any(z["_offen"] for z in ok)
    risiko = einst.konto * einst.risiko / 100
    pfad = lambda *teile: os.path.join(ordner, *teile)
    hinweise = []

    def notiz(teile, *args, **kwargs):
        try:
            return schreibe_notiz(pfad(*teile), *args, **kwargs)
        except NotizFehler as fehler:
            hinweise.append(f"Gehirn: {os.path.relpath(fehler.pfad, os.path.dirname(ordner))} {fehler.grund}")
            return False

    # Meine Regeln: nur anlegen, nie überschreiben (die Seite gehört dir)
    if not os.path.exists(pfad(REGELN_DATEI)):
        try:
            os.makedirs(ordner, exist_ok=True)
            with open(pfad(REGELN_DATEI), "w", encoding="utf-8", newline="\n") as f:
                f.write(meine_regeln_vorlage(einst.ticker_liste))
        except OSError as fehler:
            hinweise.append(f"Gehirn: {REGELN_DATEI} nicht angelegt ({fehler})")

    vorige = sorted(f[:-3] for f in os.listdir(pfad("Tage")) if f.endswith(".md") and f[:-3] < tag_name) \
        if os.path.isdir(pfad("Tage")) else []
    papier = papier or {}

    # Abgeschlossene Trades des Papier-Depots: je Trade eine Notiz (einmal angelegt, danach gehört sie dir)
    trades = [papier_trade_info(tr, daten) for tr in papier.get("trades", [])]
    trade_link = {}
    for info in trades:
        name = notiz_name(f"{info['kauf_tag']} {info['ticker']} {strategie_datei(info['strategie'])}")
        trade_link[id(info)] = f"[[Trades/{name}|{info['ticker']} {r_text(info['R'])}]]"
        zeichen = "✅" if info["R"] > 0 else "❌"
        text = [f"# {zeichen} {info['ticker']} · {strategie_name(info['strategie'])} · {r_text(info['R'])}", "",
                f"- Aktie: {link_aktie(info['ticker'])} · Strategie: {link_strategie(info['strategie'])} · "
                f"{'Long (auf steigende Kurse)' if info['r'] > 0 else 'Short (auf fallende Kurse)'}",
                f"- Einstieg: {datum(pd.Timestamp(info['kauf_tag']))} {info['kauf_tag'][:4]} zu {de(info['einstieg'])} "
                f"{waehrung} · {de(info['stueck'], 2 if info['stueck'] % 1 else 0)} Stück · Einsatz "
                f"{de(info['einsatz'], 0)} {waehrung}",
                f"- Plan: Stop {de(info['stop'])} {waehrung} · Ziel {de(info['ziel'])} {waehrung}"
                + (f" · Chance-Risiko {de(info['crv'], 1)}" if math.isfinite(info["crv"]) else "")
                + (f" · Ziel-Chance nach Black-Scholes {de(info['chance'] * 100, 0)} %" if math.isfinite(info["chance"])
                   else "")
                + (" · Kerzenmuster am Signaltag: " + ", ".join(
                    [f"{m} (bullisch)" for m in info["muster"]["bull"]] + [f"{m} (bärisch)" for m in info["muster"]["bear"]])
                   if info.get("muster") and (info["muster"]["bull"] or info["muster"]["bear"]) else ""),
                f"- Ausstieg: {datum(pd.Timestamp(info['verkauf_tag']))} {info['verkauf_tag'][:4]} zu "
                f"{de(info['ausstieg'])} {waehrung} – {info['grund']} · nach {info['tage']} {info['tage_art']}",
                f"- Ergebnis: **{de(info['gewinn'], 2, True)} {waehrung} ({r_text(info['R'], 2)})** nach Gebühren "
                f"und Spread"]
        if info["mfe"] is not None:
            text.append(f"- Im Trade: bestenfalls {r_text(info['mfe'])}, schlimmstenfalls {r_text(info['mae'])} "
                        f"(1 R = geplanter Verlust bis zum Stop)")
        text += ["", "## Was der Bot daraus lernt", ""] + [f"- {l}" for l in trade_lehren(info, stand, einst)]
        text += ["", f"Übersicht: [[Start]] · [[Lehren]] · erfasst am [[Tage/{tag_name}]]"]
        eigenschaften = {"typ": "trade", "aktie": info["ticker"], "strategie": strategie_datei(info["strategie"]),
                         "richtung": "Long" if info["r"] > 0 else "Short", "einstieg": info["kauf_tag"],
                         "ausstieg": info["verkauf_tag"], "grund": info["grund"],
                         "ergebnis_eur": round(info["gewinn"], 2), "ergebnis_r": round(info["R"], 2),
                         "tags": ["trade", "gewinn" if info["R"] > 0 else "verlust"]}
        notiz(("Trades", name + ".md"), "\n".join(text), eigenschaften, nur_neu=True, anfang=GEHIRN_ANFANG_EINMAL,
              rest_neu="\n\n## Meine Gedanken\n\n")
    # Seit der letzten Tagesnotiz abgeschlossen (beim ersten Mal: am letzten gebuchten Tag)
    seit = vorige[-1] if vorige else None
    neu_zu = [i for i in trades if (i["verkauf_tag"] > seit if seit else i["verkauf_tag"] == papier.get("bis"))
              and i["verkauf_tag"] <= tag_name]

    nach_strategie = {}
    for e in tagebuch:
        nach_strategie.setdefault(e["strategie"], []).append(e)
    ein_jahr = heute - pd.DateOffset(months=12)

    # Strategie-Seiten
    for key, s in STRATEGIEN.items():
        eintraege = nach_strategie.get(key, [])
        st = stand[key]
        text = [f"# {strategie_name(key)}", "",
                f"**Status:** {strategie_status(key, stand, einst)}", "",
                f"**Regel:** {s['regel']}", ""]
        if short_aus(key, einst):
            text += ["## Strategie-Tagebuch", "",
                     "- Short-Signale sind aus – diese Strategie rechnet auch im Tagebuch nicht mit. Mit `--mit-short` "
                     "berechnet der Bot ihr Tagebuch beim nächsten Lauf aus den Kursen der letzten 5 Jahre neu."]
        else:
            text += ["## Strategie-Tagebuch (jede Strategie handelt gedanklich auf allen Aktien mit)", "",
                     f"- Letzte {st['n']} Trades: "
                     + (f"Ø {r_text(st['schnitt'], 2)} · Treffer {de(st['quote'], 0)} % · ± Zufall {de(st['spanne'], 2)} R"
                        if st["n"] > 1 else kennzahl_text(kennzahlen([e['R'] for e in eintraege[-1:]]))),
                     f"- Ganze Geschichte: {kennzahl_text(kennzahlen([e['R'] for e in eintraege]))}",
                     f"- In Euro: 1 R ≈ {de(risiko, 0)} {waehrung} bei deinem Risiko je Trade"]
            gruende = {}
            for e in eintraege:
                gruende.setdefault(e["grund"], []).append(e["R"])
            if gruende:
                text += ["", "### So endeten die Trades", ""]
                for g, werte in sorted(gruende.items(), key=lambda x: -len(x[1])):
                    text.append(f"- {g}: {len(werte)}× ({de(len(werte) / len(eintraege) * 100, 0)} %), "
                                f"Ø {r_text(sum(werte) / len(werte), 2)}")
            je_aktie = {}
            for e in eintraege:
                je_aktie.setdefault(e["ticker"], []).append(e["R"])
            genug = sorted(((t, kennzahlen(w)) for t, w in je_aktie.items() if len(w) >= 5),
                           key=lambda x: -x[1]["schnitt"])
            if genug:
                text += ["", "### Rangliste der Aktien (ab 5 Trades, nach Ø R)", ""] + rangliste(genug)
                text.append("- Vorsicht: Bei so wenigen Trades je Aktie ist vieles Zufall – der Bot sperrt deshalb keine "
                            "Aktien von selbst. Das kannst du in [[Meine Regeln]] tun.")
            wechsel = lern_wechsel(pausen, alle_tage, key, ein_jahr)
            text += ["", "### Lernverlauf (letzte 12 Monate)", ""]
            text += ([f"- {datum(t)} {t:%Y}: {'⏸ pausiert/aus' if p else '✅ wieder aktiv'}" for t, p in wechsel[-10:]]
                     or ["- keine Änderung"])
        eigene = [i for i in trades if i["strategie"] == key]
        text += ["", "## Trades im Übungsdepot (Papier-Depot)", ""]
        text += ([f"- {trade_link[id(i)]} ({i['grund']}, {i['verkauf_tag']})" for i in reversed(eigene[-20:])]
                 or ["- noch keine"])
        text += ["", "Übersicht: [[Start]] · [[Lehren]] · [[Meine Regeln]]"]
        status = ("aus" if short_aus(key, einst) or key in einst.sperre_strategien or st["im_minus"]
                  else "pausiert" if st["pausiert"] else "aktiv")
        notiz(("Strategien", strategie_datei(key) + ".md"), "\n".join(text),
              {"typ": "strategie", "status": status, "tags": ["strategie"]})

    # Aktien-Seiten: Watchlist und alles, was das Übungsdepot hält oder gehandelt hat
    zeile_von = {z["Ticker"]: z for z in zeilen}
    depot_ticker = [x["ticker"] for x in papier.get("positionen", []) + papier.get("auftraege", []) + papier.get("trades", [])]
    stand_text = f"{datum(heute)} {heute:%Y}"
    for t in dict.fromkeys(list(einst.ticker_liste) + depot_ticker):
        z = zeile_von.get(t)
        text = [f"# {t}", ""]
        if BRANCHE.get(t):
            text += [f"Branche: {BRANCHE[t]} (höchstens {MAX_JE_BRANCHE} Positionen aus einer Branche zugleich)", ""]
        link = tradingview_link(t)
        if link:
            text.append(f"[Chart bei TradingView]({link})")
        if t in einst.sperre_ticker:
            text.append("**⛔ Von dir gesperrt** ([[Meine Regeln]]) – der Bot kauft oder shortet sie nicht.")
        if z is None:
            text += ["", f"**Stand {stand_text}:** nicht (mehr) auf deiner Watchlist – nur noch im Übungsdepot."]
        else:
            text += ["", f"**Stand {stand_text}:** {z.get('Signal', '–')}" + (f" – {z['Strategie']}" if z.get("Strategie") else "")
                     + (f" · Limit {de(z['Limit'])} · Stop {de(z['Stop'])} · Ziel {de(z['Ziel'])} {waehrung}"
                        if z.get("Signal") in (KAUFEN, SHORT) else "")
                     + (f" · {z['_fehler']}" if z.get("_fehler") else "")]
            if z.get("Zahlen"):
                text.append(f"**Nächste Quartalszahlen:** {z['Zahlen']}")
        offen = [p for p in papier.get("positionen", []) if p["ticker"] == t]
        text += ["", "## Übungsdepot", ""]
        text += [f"- Offen: {'Long' if p['richtung'] > 0 else 'Short'} mit {link_strategie(p['strategie'])} seit "
                 f"{str(p['kauf_tag'])[:10]}" for p in offen]
        eigene = [i for i in trades if i["ticker"] == t]
        text += [f"- {trade_link[id(i)]} mit {link_strategie(i['strategie'])} ({i['grund']}, {i['verkauf_tag']})"
                 for i in reversed(eigene[-20:])] or (["- noch keine Trades"] if not offen else [])
        je = {}
        for e in tagebuch:
            if e["ticker"] == t:
                je.setdefault(e["strategie"], []).append(e["R"])
        text += ["", "## Strategie-Tagebuch auf dieser Aktie", ""]
        if je:
            text.append(f"- **Alle Strategien zusammen:** {kennzahl_text(kennzahlen([x for w in je.values() for x in w]))}")
        text += ([f"- {link_strategie(k)}: {kennzahl_text(kennzahlen(w))}"
                  for k, w in sorted(je.items(), key=lambda x: VORRANG[x[0]])] or ["- noch keine gedachten Trades"])
        text += ["", "Übersicht: [[Start]] · [[Meine Regeln]]"]
        notiz(("Aktien", notiz_name(t) + ".md"), "\n".join(text), {"typ": "aktie", "tags": ["aktie"]})

    # Lehren: was der Bot aus allen Trades zieht
    papier_k = kennzahlen([i["R"] for i in trades])
    text = ["# 🎓 Lehren", "",
            "Hier sammelt der Bot, was er aus seinen Fehlern und Erfolgen zieht. **Automatisch ändert er dabei nur, welche "
            "Strategien er handelt** (Lernregel unten) – und hält sich an [[Meine Regeln]]. Muster wie „auf Aktie X läuft es "
            "schlecht“ zeigt er dir nur: Bei wenigen Trades ist das oft Zufall, und wer jedem Zufall hinterherläuft, "
            "verliert am Ende mehr.", "",
            "## Was der Bot gerade daraus macht (Lernregel)", ""]
    if einst.lernen:
        text += [f"Ab {LERNEN_MIN_TRADES} gedachten Trades pausiert er eine Strategie, wenn sie im Schnitt mehr als "
                 f"{de(-LERNEN_PAUSE_AB, 1)} R je Trade verliert, und nimmt sie wieder, sobald der Schnitt im Plus ist. Ab "
                 f"{LERNEN_LANG_MIN} Trades muss sie über ihre ganze Geschichte im Plus sein.", ""]
    else:
        text += ["Lernen ist ausgeschaltet (Option --ohne-lernen): Der Bot pausiert keine Strategien.", ""]
    for key in STRATEGIEN:
        text.append(f"- {link_strategie(key)}: {strategie_status(key, stand, einst)}")
    letzte = [(t, k, p) for k in STRATEGIEN for t, p in lern_wechsel(pausen, alle_tage, k, heute - pd.Timedelta(days=30))]
    text += ["", "### Änderungen der letzten 30 Tage", ""]
    text += ([f"- {datum(t)}: {link_strategie(k)} {'⏸ pausiert/aus' if p else '✅ wieder aktiv'}"
              for t, k, p in sorted(letzte)] or ["- keine"])
    alle_r = [e["R"] for e in tagebuch]
    text += ["", "## Muster im Strategie-Tagebuch (alle Strategien, alle Aktien)", "",
             f"- Insgesamt: {kennzahl_text(kennzahlen(alle_r))}"]
    gruende = {}
    for e in tagebuch:
        gruende.setdefault(e["grund"], []).append(e["R"])
    for g, werte in sorted(gruende.items(), key=lambda x: -len(x[1])):
        text.append(f"- {g}: {len(werte)}× ({de(len(werte) / max(len(alle_r), 1) * 100, 0)} %), "
                    f"Ø {r_text(sum(werte) / len(werte), 2)}")
    lang = kennzahlen([e["R"] for e in tagebuch if STRATEGIEN[e["strategie"]]["richtung"] > 0])
    kurz = kennzahlen([e["R"] for e in tagebuch if STRATEGIEN[e["strategie"]]["richtung"] < 0])
    text += [f"- Long: {kennzahl_text(lang)}"] + ([f"- Short: {kennzahl_text(kurz)}"] if einst.mit_short else [])
    je_aktie = {}
    for e in tagebuch:
        je_aktie.setdefault(e["ticker"], []).append(e["R"])
    genug = sorted(((t, kennzahlen(w)) for t, w in je_aktie.items() if len(w) >= 20), key=lambda x: -x[1]["schnitt"])
    if len(genug) >= 2:
        text += ["", "### Rangliste der Aktien (ab 20 Trades, nach Ø R)", ""] + rangliste(genug)
        text.append("- Hinweis: Selbst 20–50 Trades je Aktie sind wenig. Sperren kannst du eine Aktie in [[Meine Regeln]].")
        unter = sorted((x for x in genug if x[1]["quote"] <= 50), key=lambda x: x[1]["quote"])
        text += ["", "### Trefferquote je Aktie (Ziel: über 50 %)", "",
                 f"- {len(genug) - len(unter)} von {len(genug)} Aktien (ab 20 Trades) treffen öfter als jedes zweite Mal."]
        liste = ", ".join(f"{link_aktie(a)} {de(k['quote'], 0)} % ({k['n']} Trades, Ø {r_text(k['schnitt'], 2)})"
                          for a, k in unter)
        text.append(f"- Bei 50 % oder darunter: {liste}. Ein paar Prozentpunkte unter 50 % können auch bei über 100 "
                    "Trades Zufall sein – und die Trefferquote allein sagt nicht, ob eine Aktie Geld bringt (dafür zählt "
                    "Ø R, siehe Rangliste oben)." if unter else "- Keine Aktie liegt bei 50 % oder darunter.")
    text += chance_lehren(chance_pruefung(tagebuch, daten))
    text += muster_lehren(muster_pruefung(tagebuch, daten))
    log = nachrichten_log_lesen(einst.nachrichten_log) if getattr(einst, "nachrichten_log", None) else []
    text += nachrichten_lehren(nachrichten_pruefung(log, tagebuch), len(log))
    text += ["", "## Aus dem Übungsdepot (echte Vorwärts-Trades)", ""]
    if papier_k:
        abgegeben = [i for i in trades if gewinn_abgegeben(i)]
        luecken = [i for i in trades if i["grund"] == "Stop (Kurslücke)"]
        zeit = [i for i in trades if i["grund"] == "Zeitstopp"]
        text += [f"- {kennzahl_text(papier_k)} · Summe {de(sum(i['gewinn'] for i in trades), 2, True)} {waehrung}",
                 f"- Gewinn wieder abgegeben (erst mehr als den halben Weg zum Ziel im Plus, am Ende im Minus): "
                 f"{len(abgegeben)} von "
                 f"{len(trades)}" + (" – wird das über viele Trades deutlich häufiger, lohnt ein neuer Test (bisher half ein nachgezogener Stop nicht, "
                                     "siehe [[Notizen/Gelernt – Stop nachziehen und absichern]])."
                                     if len(trades) >= 10 and len(abgegeben) / len(trades) >= 0.2 else ""),
                 f"- Stop mit Kurslücke (größerer Verlust als geplant): {len(luecken)} von {len(trades)}",
                 f"- Zeitstopp (nach {ZEITSTOPP_TAGE} Tagen ohne Ziel und Stop): {len(zeit)} von {len(trades)}"]
        if len(trades) < 30:
            text.append(f"- Erst {len(trades)} Trades – für belastbare Schlüsse braucht es deutlich mehr (etwa 100).")
    elif papier:
        text.append(f"- Noch keine abgeschlossenen Trades – das Übungsdepot läuft seit {papier.get('angelegt')}.")
    else:
        text.append("- Noch kein Übungsdepot.")
    text += ["", "Übersicht: [[Start]] · [[Meine Regeln]]"]
    notiz(("Lehren.md",), "\n".join(text), {"typ": "lehren"})

    # Tagesnotiz
    text = [f"# 📅 {WOCHENTAGE[heute.weekday()]} {heute:%d.%m.%Y}" + (" (vorläufig – Börse noch offen)" if vorlaeufig else ""),
            "", (f"← [[Tage/{vorige[-1]}|Vortag]] · " if vorige else "") + f"[[Wochen/{woche_name}|Woche {kw}]] · "
            "[[Start]] · [[Lehren]] · [[Meine Regeln]]",
            "", "## Markt", ""]
    ampel = marktampel(trend, ok, einst)
    text.append(f"- {ampel}" if ampel else "- Marktfilter aus")
    text += ["", "## Entscheidungen", ""]
    for z in sorted(ok, key=lambda z: PRIORITAET.get(z.get("Signal"), 9)):
        sig = z.get("Signal")
        if sig in (KAUFEN, SHORT):
            text.append(f"- {sig} {link_aktie(z['Ticker'])} mit {link_strategie(z['_strategie'])} – Limit "
                        f"{de(z['Limit'])} · Stop {de(z['Stop'])} · Ziel {de(z['Ziel'])} {waehrung} · CRV {de(z['CRV'], 1)}")
        elif sig in (WARTEN, SICHERN):
            text.append(f"- {sig} {link_aktie(z['Ticker'])}: {z.get('Strategie', '')}")
    beobachten = [link_aktie(z["Ticker"]) for z in ok if z.get("Signal") == BEOBACHTEN]
    if beobachten:
        text.append(f"- Beobachten: {', '.join(beobachten)}")
    text += [f"- ❌ {z['Ticker']}: {z.get('_fehler', '')}" for z in zeilen if "_stand" not in z]
    text += ["", "## Übungsdepot (Papier-Depot)", ""]
    if papier_hinweis:
        text.append(f"- ⚠️ {papier_hinweis}")
    if papier:
        verlauf = papier.get("verlauf") or []
        wert = papier["depotwert"]
        text.append(f"- Depotwert {de(wert)} {waehrung} ({de((wert / papier['startkapital'] - 1) * 100, 1, True)} % seit "
                    f"{papier.get('angelegt')}) · Stand {papier.get('bis')}"
                    + (f" · zum Vortag {de(wert - verlauf[-2][1], 2, True)} {waehrung}" if len(verlauf) >= 2 else ""))
        text += [f"- Abgeschlossen: {trade_link[id(i)]} ({i['grund']}, {i['verkauf_tag']})" for i in neu_zu]
        text += [f"- Offen: {link_aktie(p['ticker'])} {'Long' if p['richtung'] > 0 else 'Short'} mit "
                 f"{link_strategie(p['strategie'])} seit {str(p['kauf_tag'])[:10]}" for p in papier["positionen"]]
        auftraege, verfallen, nachruecker = ausfuehrbare_auftraege(papier)
        text += [f"- Auftrag für den nächsten Handelstag: {link_aktie(a['ticker'])} mit {link_strategie(a['strategie'])}"
                 for a in auftraege]
        text += [f"- Rückt nach, falls ein Auftrag davor nicht zum Limit klappt: {link_aktie(a['ticker'])} mit "
                 f"{link_strategie(a['strategie'])}" for a in nachruecker]
        text += [f"- Kein Kauf möglich ({grund}): " + ", ".join(link_aktie(t) for t in liste)
                 for grund, liste in verfallen.items()]
    elif not einst.papier:
        text.append("- Kein Papier-Depot in diesem Lauf (Option --papier).")
    else:
        text.append("- Noch kein Papier-Depot.")
    text += ["", "## Lernstand", ""]
    if alle_tage:
        vergleich = pd.Timestamp(vorige[-1]) if vorige else (alle_tage[-2] if len(alle_tage) >= 2 else alle_tage[-1])
        if getattr(alle_tage[-1], "tz", None) is not None and vergleich.tz is None:
            vergleich = vergleich.tz_localize(alle_tage[-1].tz)
        aenderungen = [(t, k, p) for k in STRATEGIEN for t, p in lern_wechsel(pausen, alle_tage, k, vergleich)]
        text += [f"- {datum(t)}: {'⏸' if p else '✅'} {link_strategie(k)} {'pausiert/aus' if p else 'wieder aktiv'}"
                 for t, k, p in sorted(aenderungen)] or ["- keine Änderung"]
        aktiv = [link_strategie(k) for k in STRATEGIEN if k not in pausen.get(alle_tage[-1], frozenset())
                 and k not in einst.sperre_strategien and not short_aus(k, einst)]
        text.append(f"- Aktiv: {', '.join(aktiv) if aktiv else 'keine'}")
    if einst.sperre_ticker or einst.sperre_strategien:
        text += ["", "## Deine Regeln", ""]
        if einst.sperre_ticker:
            text.append(f"- Gesperrt: {', '.join(link_aktie(t) for t in sorted(einst.sperre_ticker))}")
        if einst.sperre_strategien:
            text.append(f"- Ausgeschaltet: {', '.join(link_strategie(k) for k in STRATEGIEN if k in einst.sperre_strategien)}")
    notiz(("Tage", tag_name + ".md"), "\n".join(text), {"typ": "tag", "datum": tag_name, "tags": ["tag"]})

    # Wochenrückblick: eine Notiz je Kalenderwoche – während der Woche bei jedem Lauf neu, danach bleibt sie stehen
    montag = (heute - pd.Timedelta(days=heute.weekday())).normalize()
    von = f"{montag:%Y-%m-%d}"
    vorwochen = sorted(f[:-3] for f in os.listdir(pfad("Wochen")) if f.endswith(".md") and f[:-3] < woche_name) \
        if os.path.isdir(pfad("Wochen")) else []
    text = [f"# 📆 Woche {kw}/{jahr} ({montag:%d.%m.}–{montag + pd.Timedelta(days=4):%d.%m.%Y})", "",
            (f"← [[Wochen/{vorwochen[-1]}|Vorwoche]] · " if vorwochen else "") + "[[Start]] · [[Lehren]] · "
            "[[Meine Regeln]]", "",
            f"Stand: Kurse bis {WOCHENTAGE[heute.weekday()]} {heute:%d.%m.%Y}"
            + (" – die Woche läuft noch" if heute.weekday() < 4 or vorlaeufig else ""), "",
            "## Übungsdepot diese Woche", ""]
    if papier:
        vorher = [w for tg, w in (papier.get("verlauf") or []) if str(tg)[:10] < von]
        anfang = vorher[-1] if vorher else papier["startkapital"]
        wert = papier["depotwert"]
        text.append(f"- Depotwert: {de(anfang)} → {de(wert)} {waehrung} ({de(wert - anfang, 2, True)} {waehrung}, "
                    f"{de((wert / anfang - 1) * 100, 1, True)} %)")
        woche = [i for i in trades if von <= i["verkauf_tag"] <= tag_name]
        if woche:
            text.append(f"- Abgeschlossen: {kennzahl_text(kennzahlen([i['R'] for i in woche]))} · Summe "
                        f"{de(sum(i['gewinn'] for i in woche), 2, True)} {waehrung}")
            text += [f"  - {trade_link[id(i)]} ({i['grund']}, {i['verkauf_tag']})" for i in woche]
        else:
            text.append("- Abgeschlossen: keine Trades")
        gekauft = [x for x in list(papier["positionen"]) + trades if von <= str(x["kauf_tag"])[:10] <= tag_name]
        text.append("- Neu gekauft: " + (", ".join(f"{link_aktie(x['ticker'])} ({strategie_name(x['strategie'])})"
                                                   for x in gekauft) or "nichts"))
        text.append("- Offen: " + (", ".join(link_aktie(x["ticker"]) for x in papier["positionen"]) or "nichts"))
    else:
        text.append("- noch kein Übungsdepot")
    text += ["", "## Trefferquote im Übungsdepot (seit dem Start)", ""]
    if trades:
        je_aktie = {}
        for i in trades:
            je_aktie.setdefault(i["ticker"], []).append(i["R"])
        text += [f"- Alle Trades: {kennzahl_text(kennzahlen([i['R'] for i in trades]))}",
                 "- Je Aktie (Treffer von Trades): " + ", ".join(f"{link_aktie(a)} {sum(r > 0 for r in w)} von {len(w)}"
                                                                for a, w in sorted(je_aktie.items())),
                 "- Bei so wenigen Trades je Aktie ist das noch viel Zufall – mehr Trades zeigt das Strategie-Tagebuch "
                 "in [[Lehren]] (Abschnitt „Trefferquote je Aktie“)."]
    else:
        text.append("- noch keine abgeschlossenen Trades")
    text += ["", "## Lernstand diese Woche", ""]
    if alle_tage:
        seit = montag - pd.Timedelta(days=1)
        if getattr(alle_tage[-1], "tz", None) is not None and seit.tz is None:
            seit = seit.tz_localize(alle_tage[-1].tz)
        wechsel = [(tg, k, ps) for k in STRATEGIEN for tg, ps in lern_wechsel(pausen, alle_tage, k, seit)]
        text += [f"- {datum(tg)}: {'⏸' if ps else '✅'} {link_strategie(k)} {'pausiert/aus' if ps else 'wieder aktiv'}"
                 for tg, k, ps in sorted(wechsel)] or ["- keine Änderung"]
    text += ["", "## Markt", "", f"- {ampel}" if ampel else "- Marktfilter aus",
             "", "## Tagesnotizen der Woche", "",
             " · ".join(f"[[Tage/{v}|{WOCHENTAGE[pd.Timestamp(v).weekday()]} {pd.Timestamp(v):%d.%m.}]]"
                        for v in [v for v in vorige if v >= von] + [tag_name])]
    notiz(("Wochen", woche_name + ".md"), "\n".join(text), {"typ": "woche", "woche": woche_name, "tags": ["woche"]},
          rest_neu="\n\n## Meine Gedanken zur Woche\n\n")

    # Startseite (ändert sich nur, wenn es Neues gibt – keine Uhrzeit, damit der Abgleich ruhig bleibt)
    text = ["# 🧠 Gehirn des Swing-Bots", "",
            f"Stand: Kurse bis {WOCHENTAGE[heute.weekday()]} {heute:%d.%m.%Y}" + (" (vorläufig)" if vorlaeufig else "")
            + " · Simulation mit Spielgeld, keine Anlageberatung.", "",
            "> [!info] So funktioniert das Gehirn",
            "> - Der Bot schreibt nach jedem Lauf: die **Tagesnotiz**, den **Wochenrückblick**, eine Notiz zu **jedem "
            "abgeschlossenen Trade** mit "
            "dem, was er daraus lernt, und je eine Seite pro **Strategie** und **Aktie**.",
            "> - Er **liest [[Meine Regeln]]**: Dort kannst du Aktien sperren und Strategien ausschalten (Kästchen "
            "anhaken, dann hochladen – siehe Anleitung).",
            "> - **Eigene Gedanken** schreibst du am besten in die Trade-Notizen (unter „Meine Gedanken“) oder in eigene "
            "Notizen im Ordner `gehirn/Notizen` – die ändert der Bot nie. Die übrigen Seiten schreibt er bei jedem Lauf neu.",
            "",
            f"## Heute: [[Tage/{tag_name}]] · Diese Woche: [[Wochen/{woche_name}|Woche {kw}]]", ""]
    kauf = [f"{link_aktie(z['Ticker'])} ({z['Signal']})" for z in ok if z.get("Signal") in (KAUFEN, SHORT)]
    text.append(f"- Signale: {', '.join(kauf) if kauf else 'keine'}" + (" – vorläufig" if vorlaeufig and kauf else ""))
    if ampel:
        text.append(f"- {ampel}")
    text += ["", "## Übungsdepot", ""]
    if papier_hinweis:
        text.append(f"- ⚠️ {papier_hinweis}")
    if papier:
        text.append(f"- {de(papier['depotwert'])} {waehrung} ({de((papier['depotwert'] / papier['startkapital'] - 1) * 100, 1, True)} % "
                    f"seit {papier.get('angelegt')}) · {len(papier['positionen'])} offen · {kennzahl_text(papier_k)}")
        if trades:
            text.append(f"- Letzte Trades: {', '.join(trade_link[id(i)] for i in reversed(trades[-5:]))}")
    else:
        text.append("- noch kein Papier-Depot")
    if depot is not None:
        halten = depot["vergleich"].iloc[-1] if depot.get("vergleich") is not None else None
        text.append(f"- Rückblick {einst.rueckblick} Monate: {de((depot['end_wert'] / depot['start_wert'] - 1) * 100, 1, True)} %"
                    + (f" (alle Aktien kaufen und halten: {de((halten / depot['start_wert'] - 1) * 100, 1, True)} %)"
                       if halten is not None else ""))
    text += ["", "## Was der Bot gelernt hat → [[Lehren]]", ""]
    gruppen = {"✅ aktiv": [], "⏸ pausiert": [], "⏸ aus": [], "⛔ von dir aus": [], "– Short ausgeschaltet": []}
    for key in STRATEGIEN:
        st = stand[key]
        gruppe = ("– Short ausgeschaltet" if short_aus(key, einst) else "⛔ von dir aus" if key in einst.sperre_strategien
                  else "⏸ aus" if st["im_minus"] else "⏸ pausiert" if st["pausiert"] else "✅ aktiv")
        gruppen[gruppe].append(link_strategie(key))
    text += [f"- {g}: {', '.join(v)}" for g, v in gruppen.items() if v]
    text += ["", "## Deine Regeln → [[Meine Regeln]]", "",
             f"- Gesperrte Aktien: {', '.join(sorted(einst.sperre_ticker)) or 'keine'}",
             f"- Ausgeschaltete Strategien: {', '.join(strategie_name(k) for k in STRATEGIEN if k in einst.sperre_strategien) or 'keine'}",
             "", "## Aktien", "", " · ".join(link_aktie(t) for t in einst.ticker_liste)]
    notizen = sorted(f[:-3] for f in os.listdir(pfad("Notizen")) if f.endswith(".md")) \
        if os.path.isdir(pfad("Notizen")) else []
    if notizen:  # Wissen und eigene Gedanken (der Bot schreibt sie nie um, verlinkt sie nur)
        text += ["", "## Notizen", "", " · ".join(f"[[Notizen/{n}|{n}]]" for n in notizen)]
    notiz(("Start.md",), "\n".join(text), {"typ": "start"})
    return sum(1 for i in neu_zu), hinweise


def auswerten(einst):
    if FX_TICKER in einst.ticker_liste:
        einst.ticker_liste.remove(FX_TICKER)
        print(f"Hinweis: {FX_TICKER} ist der Euro-Wechselkurs und wird nur zum Umrechnen genutzt.")
        BERICHT_HINWEISE.append(f"{FX_TICKER} ist der Euro-Wechselkurs und wird nur zum Umrechnen genutzt.")
    if not einst.ticker_liste:
        print("Keine Ticker angegeben.")
        BERICHT_STATUS["verbindung"] = False
        berichte("❌ KEINE TICKER", ["Keine Ticker angegeben."])
        return None

    # Gehirn (Obsidian): „Meine Regeln“ lesen – gesperrte Aktien und ausgeschaltete Strategien gelten überall
    gehirn_ordner = None
    if einst.gehirn:
        gehirn_ordner, gehirn_fehler = papier_pfad(einst.gehirn)
        hinweise_regeln = []
        if gehirn_ordner:
            einst.sperre_ticker, einst.sperre_strategien, hinweise_regeln = lies_meine_regeln(gehirn_ordner)
        else:
            hinweise_regeln = [gehirn_fehler.replace("das Papier-Depot wurde nicht gespeichert",
                                                     "das Gehirn wurde nicht geschrieben")]
        for h in hinweise_regeln:
            print(f"Hinweis: {h}")
            BERICHT_HINWEISE.append(h)

    papier_datei = papier_stand = papier_fehler = None
    if einst.papier:
        papier_datei, papier_fehler = papier_pfad(einst.papier)
        if papier_datei:
            papier_stand, papier_fehler = lade_papier(papier_datei, einst.papier_neu)
            einst.nachrichten_log = os.path.join(os.path.dirname(papier_datei), NACHRICHTEN_LOG)
    claude_datei = claude_stand = claude_fehler = None
    if einst.claude_depot and einst.papier:
        claude_datei = os.path.abspath(os.path.expanduser(einst.claude_depot))
        claude_stand, claude_fehler = lade_papier(claude_datei, False)

    if einst.sperre_ticker:
        bekannt = set(einst.ticker_liste) | {x["ticker"] for x in (papier_stand or {}).get("positionen", [])
                                             + (papier_stand or {}).get("auftraege", [])}
        fremd = sorted(einst.sperre_ticker - bekannt)
        if fremd:
            h = (f"In „Meine Regeln“ gesperrt, aber nicht auf deiner Watchlist: {', '.join(fremd)} – Kürzel wie im Bot "
                 f"verwenden (z. B. NVDA statt Nvidia).")
            print(f"Hinweis: {h}")
            BERICHT_HINWEISE.append(h)

    print(f"🤖 Lade 5 Jahre Kurse für {len(einst.ticker_liste)} Ticker, Quartalszahlen-Termine und prüfe "
          f"{len(STRATEGIEN) if einst.mit_short else len(STRATEGIEN) // 2} Strategien ...")
    unterstuetzt = [t for t in einst.ticker_liste if waehrung_von(t)]
    # Ticker, die das Papier-Depot noch hält oder kaufen will, aber nicht (mehr) auf der Watchlist stehen
    papier_extra = []
    if papier_stand is not None:
        papier_extra = [t for t in dict.fromkeys(p["ticker"] for p in papier_stand["positionen"] + papier_stand["auftraege"])
                        if t not in unterstuetzt and waehrung_von(t)]
    claude_extra = []
    if claude_stand is not None:
        claude_extra = [t for t in dict.fromkeys(p["ticker"] for p in claude_stand["positionen"] + claude_stand["auftraege"])
                        if t not in unterstuetzt and waehrung_von(t)]
    alle_extra = list(dict.fromkeys(papier_extra + claude_extra))  # alle laden, jedes Depot rechnet mit seinen
    frischer_yahoo_cache()
    with YahooRuhig(einst.debug) as sammler:
        extra = [x for x in (FX_TICKER, MARKT_TICKER) if x not in unterstuetzt + alle_extra]
        roh, gruende = lade_kurse(unterstuetzt + alle_extra + extra, sammler)
        termin_ticker = ([t for t in unterstuetzt + alle_extra if t in roh and hat_zahlen(t)]
                         if not einst.ohne_zahlen else [])
        # Termine zuerst für Ticker mit Signal holen – greift Yahoos Limit, fehlen sie eher bei den übrigen
        trend_vorab = markt_trend(roh.get(MARKT_TICKER)) if einst.marktfilter else None
        termin_ticker.sort(key=lambda t: not signal_zuletzt(roh[t], einst.mit_short, trend_vorab))
        zusatz = hole_zusatzdaten(termin_ticker, [], sammler)
    fx_daten = roh.pop(FX_TICKER, None)
    fx = fx_daten["Close"] if fx_daten is not None else None
    markt_df = roh.get(MARKT_TICKER) if MARKT_TICKER in unterstuetzt + alle_extra else roh.pop(MARKT_TICKER, None)
    waehrung = "€" if fx is not None else "$"
    # US-Werte werden mit EUR/USD umgerechnet, Werte von Euro-Börsen nicht
    fx_je_ticker = {t: fx if waehrung_von(t) == "USD" else None for t in unterstuetzt + alle_extra}

    trend = markt_trend(markt_df)  # Marktfilter: Nasdaq-100 über/unter der 200-Tage-Linie
    daten = {t: bereite_vor(t, roh[t], fx_je_ticker[t], zusatz.get(t, {}).get("zahlen"), einst, trend)
             for t in unterstuetzt if t in roh}
    markt = bereite_vor(MARKT_TICKER, markt_df, None, None, einst) if markt_df is not None else None

    if not daten:
        verbindung = (fx_daten is None and markt_df is None) or any(
            g in (YAHOO_LIMIT, KEINE_VERBINDUNG) for g in gruende.values())
        print("\n❌ Für keinen Ticker gibt es auswertbare Kurse"
              + (" – meist keine Verbindung zu Yahoo oder Yahoo-Limit erreicht." if verbindung else ":"))
        fehlerliste = [f"❌ {t}: {gruende.get(t, 'Währung nicht unterstützt – nur US- und Euro-Börsen')}"
                       for t in einst.ticker_liste]
        for z in fehlerliste:
            print(z)
        if verbindung:
            print("Internetverbindung prüfen oder in 1–2 Minuten erneut starten.")
        BERICHT_STATUS["verbindung"] = verbindung
        berichte("❌ KEINE AUSWERTBAREN KURSE", fehlerliste)
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
    chance_gruppen = chance_pruefung(tagebuch, daten)  # Selbstkontrolle der Ziel-Chance (nur Info)
    muster_gruppen = muster_pruefung(tagebuch, daten)  # Selbstkontrolle der Kerzenmuster (nur Info)
    for z in zeilen:
        if "_chance" in z:
            z["_chance_praxis"] = chance_praxis(z["_chance"], chance_gruppen)
        if "_muster" in z:
            z["_muster_praxis"] = muster_praxis(muster_gruppe(z["_muster"]), muster_gruppen)
    if not any("_stand" in z for z in zeilen):
        fehlerliste = [f"❌ {z['Ticker']}: {z.get('_fehler', '')}" for z in zeilen]
        for z in fehlerliste:
            print(z)
        BERICHT_STATUS["verbindung"] = False
        berichte("❌ KEINE AUSWERTBAREN KURSE", fehlerliste)
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
        # Nachrichten-Regel: Spricht eine erkannte Schlagzeile der letzten Tage gegen das Signal (z. B. Herabstufung,
        # Kapitalerhöhung, Klage einer Behörde) oder ist es ein Sonderfall (Übernahme, Handelsaussetzung), wartet der
        # Bot – im Scanner und im Papier-Depot für diesen Tag. Rückwirkend lässt sich das nicht testen (alte
        # Schlagzeilen gibt es bei Yahoo nicht), deshalb gilt die Regel nur ab heute.
        sperre = set()
        for z in zeilen:
            n = news.get(z["Ticker"], {})
            if z.get("Signal") in (KAUFEN, SHORT) and n.get("warnung"):
                for feld in ("Limit", "Stop", "Ziel", "CRV", "Stück", "Einsatz", "Risiko", "_chance", "_chance_praxis"):
                    z.pop(feld, None)
                z.update({"Signal": WARTEN, "Strategie": f"{strategie_name(z['_strategie'])} – Nachricht: "
                                                         f"{', '.join(n.get('warnende') or ['siehe Schlagzeilen'])}"})
                sperre.add(z["Ticker"])
        einst.nachrichten_sperre, einst.nachrichten_tag = frozenset(sperre), stand_tag
    for z in zeilen:
        z["News"] = news.get(z["Ticker"], {}).get("spalte", "")
        if news.get(z["Ticker"], {}).get("stimmung"):
            z["_stimmung"] = news[z["Ticker"]]["stimmung"]
    if news and getattr(einst, "nachrichten_log", None):
        nachrichten_log_schreiben(einst.nachrichten_log, zeilen)

    # Sortieren: Einstiegssignale nach CRV (wie im Depot), dann Warten, Hinweise, Beobachten, Fehler. Das CRV wird
    # gerundet: Bei gleichem CRV (z. B. 1,0) entschieden sonst winzige Rechenreste die Reihenfolge, und ein zweiter Lauf
    # mit denselben Kursen schickte dieselben Signale in anderer Reihenfolge noch einmal aufs Handy. So gilt bei
    # Gleichstand die Reihenfolge der Watchlist.
    tabelle = pd.DataFrame(zeilen).reindex(columns=SPALTEN + ["_fehler"])
    tabelle["_prio"] = tabelle["Signal"].map(PRIORITAET)
    tabelle["_crv"] = tabelle["CRV"].round(2).fillna(-1e9)
    tabelle = tabelle.sort_values(["_prio", "_crv"], ascending=[True, False], kind="stable")
    reihenfolge = list(tabelle["Ticker"])
    tabelle = tabelle[SPALTEN].reset_index(drop=True)
    for spalte in ("Strategie", "Zahlen", "News"):
        tabelle[spalte] = tabelle[spalte].fillna("")

    fx_heute = float(fx.iloc[-1]) if fx is not None else None
    fehlt = fehlender_us_tag(zeilen)
    titel, zusammenfassung, hinweise = kopfzeilen(zeilen, einst, fx_heute, waehrung, trend, einst.ohne_zahlen, fehlt)
    if einst.sperre_ticker or einst.sperre_strategien:
        hinweise.append("📝 Deine Regeln (Gehirn › Meine Regeln): "
                        + " · ".join(x for x in (
                            f"gesperrt {', '.join(sorted(einst.sperre_ticker))}" if einst.sperre_ticker else "",
                            "ausgeschaltet " + ", ".join(strategie_name(k) for k in STRATEGIEN
                                                         if k in einst.sperre_strategien)
                            if einst.sperre_strategien else "") if x))
    nach_ticker = {z["Ticker"]: z for z in zeilen}
    einstiege = [nach_ticker[t] for t in reihenfolge if nach_ticker[t].get("Signal") in (KAUFEN, SHORT)]
    # Handelsplan nach denselben Grenzen wie das Depot: Anzahl, Shorts, Gesamtrisiko und Geld (bestes CRV zuerst)
    plan, zu_klein, shorts, risiko_summe, geld_summe, mehr, im_plan = [], [], 0, 0.0, 0.0, 0, []
    for z in einstiege:
        short = z["Signal"] == SHORT
        if not z["Stück"]:
            zu_klein.append(z["Ticker"])
        elif (len(plan) >= MAX_POSITIONEN or (short and shorts >= MAX_SHORTS)
                or gleiche_branche(z["Ticker"], im_plan) >= MAX_JE_BRANCHE
                or risiko_summe + z["Risiko"] > einst.konto * MAX_GESAMTRISIKO_PROZENT / 100 + 0.005
                or geld_summe + z["Einsatz"] + einst.gebuehr > einst.konto):
            mehr += 1
        else:
            plan.append(handelsplan(z, len(plan) + 1, einst, waehrung))
            im_plan.append(z["Ticker"])
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
                    f"{f' (davon {MAX_SHORTS} Short)' if einst.mit_short else ''}, höchstens {MAX_JE_BRANCHE} aus "
                    f"derselben Branche, zusammen höchstens {MAX_GESAMTRISIKO_PROZENT} % Risiko und nicht mehr Geld als "
                    f"auf dem Konto.")
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
                             zusatz, pausen, einst, waehrung, notebook, markt, trend)
    claude = None
    if claude_datei:
        claude = claude_lauf(claude_datei, claude_stand, claude_fehler, papier, daten, claude_extra, roh, fx,
                             fx_je_ticker, zusatz, pausen, einst, waehrung, notebook, markt, trend)
    depot = ohne = None
    if einst.rueckblick > 0:
        depot = simuliere_depot(daten, pausen, einst, einst.lernen)
        if einst.lernen:
            ohne = simuliere_depot(daten, pausen, einst, False)
        ohne_filter = None
        if einst.marktfilter and trend is not None and depot is not None:
            # Gegenprobe mit deinen echten Kursen: dieselben Regeln ohne Marktfilter (eigenes Tagebuch und Lernen)
            daten_of = {t: dict(d, signale=d["signale_roh"]) for t, d in daten.items()}
            pausen_of, _ = lernverlauf(strategie_tagebuch(daten_of, einst), alle_tage, einst)
            ohne_filter = simuliere_depot(daten_of, pausen_of, einst, einst.lernen)
        if depot is not None:
            ohne_regel = [t for t, d in daten.items() if d["termine"] is None and hat_zahlen(t)]
            rueckschau = RUECKSCHAU + (
                " ⚠️ Deine Regeln aus „Meine Regeln“ gelten hier für den ganzen Zeitraum – wer im Nachhinein die "
                "Verlierer sperrt, lässt den Rückblick besser aussehen, als er war. Ehrlich ist nur das Papier-Depot."
                if einst.sperre_ticker or einst.sperre_strategien else "")
            zeige_depot(depot, ohne, einst, waehrung, notebook, ohne_regel, rueckschau, einst.ohne_zahlen,
                        ohne_filter, einst.marktfilter and trend is not None)

    if einst.nachricht:
        # Fehlt der letzte US-Handelstag noch, wären Signal und Kauftag schon veraltet – dann keine Nachricht
        woche = None if fehlt is not None else wochen_rueckblick(papier, (papier_stand or {}).get("bis"), markt, fx)
        h = schreibe_nachricht(einst.nachricht, [] if fehlt is not None else einstiege, plan, papier, woche)
        if h:
            print(f"⚠️ {h}")
            BERICHT_HINWEISE.append(h)

    if gehirn_ordner:
        try:
            # Wurde das Papier-Depot diesmal nicht weitergerechnet, zeigt das Gehirn den gespeicherten Stand
            papier_gehirn, papier_hinweis = papier, None
            if einst.papier and papier is None and papier_stand is not None:
                papier_gehirn = papier_stand
                papier_hinweis = ("Das Übungsdepot wurde diesmal nicht weitergerechnet (Grund im Bericht) – der nächste "
                                  "Lauf holt das nach.")
            daten_gehirn = dict(daten)  # auch Aktien, die nur noch im Übungsdepot sind
            for t in papier_extra:
                if t in roh and t not in daten_gehirn:
                    daten_gehirn[t] = bereite_vor(t, roh[t], fx_je_ticker.get(t), zusatz.get(t, {}).get("zahlen"),
                                                  einst, trend)
            neu, gehirn_hinweise = schreibe_gehirn(gehirn_ordner, einst, waehrung, zeilen, tagebuch, stand, pausen,
                                                   alle_tage, daten_gehirn, papier_gehirn, depot, trend, papier_hinweis)
            print(f"\n🧠 Gehirn aktualisiert: {gehirn_ordner}" + (f" ({neu} neu abgeschlossene Trades)" if neu else ""))
            for h in gehirn_hinweise:
                print(f"⚠️ {h}")
                BERICHT_HINWEISE.append(h)
        except Exception as fehler:  # das Gehirn darf den Lauf (Bericht, Papier-Depot) nie verhindern
            text = f"Gehirn konnte nicht geschrieben werden ({type(fehler).__name__}: {fehler})."
            print(f"⚠️ {text}")
            BERICHT_HINWEISE.append(text)

    if einst.uebersicht:
        try:
            schreibe_uebersicht(einst.uebersicht, uebersicht_daten(
                einst, waehrung, zeilen, reihenfolge, plan, im_plan, papier, claude, depot, daten, markt, fx, trend,
                stand, tagebuch, news, fehlt))
        except Exception as fehler:  # die Übersichtsseite darf den Lauf nie verhindern
            text = f"Übersichtsseite nicht geschrieben ({type(fehler).__name__}: {fehler})."
            print(f"⚠️ {text}")
            BERICHT_HINWEISE.append(text)

    if einst.csv:
        speichere_csv(tabelle, einst.csv)
        trades = trade_tabelle(depot) if depot is not None else None
        if trades is not None:
            name, endung = os.path.splitext(einst.csv)
            speichere_csv(trades, f"{name}_trades{endung or '.csv'}")
    return {"scanner": tabelle, "depot": depot, "depot_ohne_lernen": ohne, "tagebuch": tagebuch, "lernstand": stand,
            "papier": papier}

def bericht_datei_aus(argv):
    """--bericht DATEI aus der Befehlszeile – auch wenn eine andere Angabe fehlerhaft ist."""
    for i, a in enumerate(argv):
        if a == "--bericht" and i + 1 < len(argv):
            # beginnt der nächste Teil mit '-', ist es eine andere Angabe: --bericht hatte keinen Dateinamen
            return argv[i + 1] if argv[i + 1] == "-" or not argv[i + 1].startswith("-") else None
        if a.startswith("--bericht="):
            return a.split("=", 1)[1]
    return None

def main():
    try:
        sys.stdout.reconfigure(errors="replace")  # Emojis -> '?' statt Absturz, wenn Windows in eine Datei umleitet
    except Exception:
        pass
    BERICHT.clear()
    BERICHT_HINWEISE.clear()
    BERICHT_STATUS.clear()
    fehlertext = io.StringIO()
    try:
        with contextlib.redirect_stderr(fehlertext):
            einst = lies_einstellungen()
    except SystemExit as ende:
        sys.stderr.write(fehlertext.getvalue())
        datei = bericht_datei_aus(sys.argv[1:])
        if ende.code not in (0, None) and datei:
            meldung = fehlertext.getvalue().strip().splitlines()
            BERICHT_STATUS["einstellungen"] = re.sub(r"^.*?error: ", "", meldung[-1]) if meldung else "unbekannt"
            schreibe_bericht(datei, False)
        raise
    sys.stderr.write(fehlertext.getvalue())
    if einst.live:  # nur Live-Kurse für die Übersichtsseite – kein Scanner, kein Bericht, keine Buchungen
        return schreibe_live(einst)
    BERICHT_STATUS["papier"] = bool(einst.papier)
    ergebnis, absturz = None, True
    try:
        ergebnis = auswerten(einst)
        absturz = False
    finally:
        if einst.bericht and schreibe_bericht(einst.bericht, ergebnis is not None, absturz):
            print(f"\n📝 Bericht gespeichert: {einst.bericht}")
    return ergebnis

if __name__ == "__main__":
    # Unter %run in Colab/Jupyter stehen die Ergebnisse danach als 'ergebnis' zur Verfügung
    ergebnis = main()
