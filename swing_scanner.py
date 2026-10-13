import argparse
import datetime as dt
import html
import logging
import math
import os
import re
import sys
import time

import numpy as np
import pandas as pd
import yfinance as yf

# ============================================================================
# EINSTELLUNGEN – hier anpassen oder beim Start mitgeben, z. B.:
#   python swing_scanner.py --ticker "AAPL, NFLX, SOFI" --konto 10000 --risiko 1
# ============================================================================
TICKER_LISTE = [
    "SE", "HIMS", "NOW", "INTU", "CRWV", "NBIS",
    "MELI", "IREN", "NFLX", "AAPL", "ASTS", "SOFI"
]
KONTO = 10_000              # Kontogröße / virtuelles Startkapital in €
RISIKO_PROZENT = 1.0        # max. Verlust pro Trade in % des Kontos, wenn der Stop-Loss greift
MAX_POSITION_PROZENT = 25   # eine einzelne Position höchstens so viel % des Kontos
MIT_SHORT = True            # auch auf fallende Kurse setzen (Short-Signale)
GEBUEHR = 1.0               # Ordergebühr in € je Kauf/Verkauf (z. B. Neobroker)
BRUCHSTUECKE = False        # True = auch Bruchteile von Aktien (z. B. 0,35 Stück)
MIN_EINSATZ = 25            # kleinere Trades lohnen wegen der Gebühr nicht (in €)
RUECKBLICK_MONATE = 6       # so viele Monate spielt der Bot das virtuelle Depot rückwirkend durch
MAX_TRADES_ANZEIGE = 20     # so viele abgeschlossene Trades zeigt die Liste (alle per --csv)

# Mindestanzahl an Tageskerzen, damit RSI/EMA/Bollinger/ATR aussagekräftig sind
MIN_KERZEN = 30

# Wechselkurs bei Yahoo: Dollar je 1 Euro
FX_TICKER = "EURUSD=X"
# Börsenendungen bei Yahoo, deren Kurse schon in Euro sind (z. B. SAP.DE, ASML.AS)
EURO_BOERSEN = {"DE", "F", "SG", "MU", "BE", "DU", "HM", "HA", "PA", "AS", "MI", "MC", "BR", "VI", "LS", "HE", "IR"}

# Signale (Reihenfolge = Sortierung in der Tabelle)
SCHARF_KAUFEN = "🚀 SCHARF KAUFEN"
KAUFEN = "⭐ KAUFEN"
SCHARF_SHORT = "🔥 SCHARF SHORT"
SHORT = "🔻 SHORT"
BEOBACHTEN = "BEOBACHTEN"
TEILVERKAUF = "⚠️ TEILVERKAUF"   # nur ohne Short-Signale (--ohne-short)
FEHLER = "❌ FEHLER"
PRIORITAET = {SCHARF_KAUFEN: 1, KAUFEN: 2, SCHARF_SHORT: 3, SHORT: 4, BEOBACHTEN: 5, TEILVERKAUF: 6, FEHLER: 7}
LONG_SIGNALE = (SCHARF_KAUFEN, KAUFEN)
SHORT_SIGNALE = (SCHARF_SHORT, SHORT)

LEGENDE = {
    SCHARF_KAUFEN: "RSI unter 32 oder Kurs am/unter dem unteren Bollinger-Band (Gegenbewegung nach oben). "
                   "Ziel = EMA 20, Stop = Kurs − 1,2 × ATR",
    KAUFEN: "Kurs 0–1,5 % über der EMA 20 und RSI unter 60 (Rücksetzer im Aufwärtstrend). "
            "Ziel = Kurs + 3 × ATR, Stop = Kurs − 1,5 × ATR",
    SCHARF_SHORT: "RSI über 70 oder Kurs am/über dem oberen Band (überhitzt): Short auf Rückfall zur EMA 20. "
                  "Stop = Kurs + 1,2 × ATR. Falls die Aktie im Depot ist: Hälfte verkaufen, Stop auf 3 % unter "
                  "Kurs nachziehen",
    SHORT: "Kurs 0–1,5 % unter der EMA 20 und RSI über 40 (Erholung im Abwärtstrend): "
           "Ziel = Kurs − 3 × ATR, Stop = Kurs + 1,5 × ATR",
    TEILVERKAUF: "RSI über 70 oder Kurs am/über dem oberen Band. Falls im Depot: "
                 "Teilgewinne sichern, Stop auf 3 % unter Kurs nachziehen",
    BEOBACHTEN: "kein Setup – nichts tun",
}

# Zeilenfarben: (Hintergrund, Schrift) für die Notebook-Tabelle, ANSI-Codes fürs Terminal
FARBEN = {
    SCHARF_KAUFEN: ("#1b5e20", "#ffffff"),
    KAUFEN: ("#c8e6c9", "#1b1b1b"),
    SCHARF_SHORT: ("#b71c1c", "#ffffff"),
    SHORT: ("#ffcdd2", "#1b1b1b"),
    TEILVERKAUF: ("#ffe0b2", "#1b1b1b"),
    FEHLER: ("#eeeeee", "#555555"),
}
ANSI = {SCHARF_KAUFEN: "\033[1;97;42m", KAUFEN: "\033[32m", SCHARF_SHORT: "\033[1;97;41m", SHORT: "\033[31m",
        TEILVERKAUF: "\033[33m", FEHLER: "\033[2m"}


# ----------------------------------------------------------------------------
# Zahlen deutsch formatieren
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

def tabellen_formate(einst):
    return {
        "Kurs": lambda v: de(v, 2), "Tag %": lambda v: de(v, 1, True), "RSI": lambda v: de(v, 1),
        "Stop": lambda v: de(v, 2), "Ziel": lambda v: de(v, 2), "CRV": lambda v: de(v, 1),
        "Stück": lambda v: de(v, 2 if einst.bruchstuecke else 0), "Einsatz": lambda v: de(v, 0),
    }

SPALTEN = ["Ticker", "Signal", "Kurs", "Tag %", "RSI", "Stop", "Ziel", "CRV", "Stück", "Einsatz"]


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
    p.add_argument("--gebuehr", type=zahl, default=GEBUEHR, help="Ordergebühr in € je Kauf/Verkauf")
    p.add_argument("--bruchstuecke", action="store_true", help="auch Bruchteile von Aktien handeln")
    p.add_argument("--rueckblick", type=int, default=RUECKBLICK_MONATE,
                   help="Monate, die der Bot das virtuelle Depot rückwirkend durchspielt (0 = aus, max. 18)")
    p.add_argument("--nur-schluss", action="store_true",
                   help="laufende Tageskerze ignorieren und nur abgeschlossene Tage bewerten")
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
    einst.bruchstuecke = BRUCHSTUECKE or einst.bruchstuecke
    einst.ticker_liste = ticker_aus_text(einst.ticker if einst.ticker else ",".join(TICKER_LISTE))
    return einst


# ----------------------------------------------------------------------------
# Kursdaten laden
# ----------------------------------------------------------------------------
class YahooFehler(logging.Handler):
    """Sammelt die Fehlermeldungen von yfinance je Ticker, statt sie über die Tabelle zu schreiben."""
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.gruende = {}

    def emit(self, record):
        # yfinance meldet z. B. "['SE', 'HIMS']: ConnectionError('... 403 ...')"
        # oder "Failed to get ticker 'SE' reason: ..." – alle Meldungen je Ticker sammeln
        text = record.getMessage()
        treffer = (re.match(r"\s*\[(.*?)\]:\s*(.*)", text, re.S)
                   or re.match(r"\s*Failed to get ticker ('[^']+') reason:\s*(.*)", text, re.S))
        if treffer:
            for ticker in re.findall(r"'([^']+)'", treffer.group(1)):
                self.gruende[ticker] = self.gruende.get(ticker, "") + " " + treffer.group(2)

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

def lade_kurse(ticker_liste, periode, debug=False):
    """Lädt alle Ticker in einem Rutsch (Tageskerzen); leere Ticker werden einmal nachgeladen."""
    sammler = YahooFehler()
    handler = [sammler] + ([logging.StreamHandler()] if debug else [])
    yf_log = logging.getLogger("yfinance")
    alte_weitergabe = yf_log.propagate
    for h in handler:
        yf_log.addHandler(h)
    yf_log.propagate = False
    daten, fehlend = {}, list(ticker_liste)
    try:
        for versuch in range(2):
            if not fehlend:
                break
            if versuch:
                time.sleep(3)
            roh = yf.download(fehlend, period=periode, interval="1d", auto_adjust=True,
                              group_by="ticker", progress=False, threads=True)
            rest = []
            for ticker in fehlend:
                df = tabelle_fuer(roh, ticker)
                if df is None:
                    rest.append(ticker)
                else:
                    daten[ticker] = df
            fehlend = rest
    finally:
        for h in handler:
            yf_log.removeHandler(h)
        yf_log.propagate = alte_weitergabe
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

def kurs_umrechner(fx, index):
    """Dollar je Euro für jeden Tag des Index (fehlende Tage mit dem letzten bekannten Kurs)."""
    if fx is None:
        return pd.Series(1.0, index=index)
    return fx.reindex(fx.index.union(index)).ffill().reindex(index).bfill()

def kerze_noch_offen(df):
    """True, wenn die letzte Tageskerze von heute ist und die US-Börse noch nicht geschlossen hat."""
    try:
        jetzt = pd.Timestamp.now(tz="America/New_York")
    except Exception:
        return False
    return df.index[-1].date() == jetzt.date() and jetzt.time() < dt.time(16, 15)


# ----------------------------------------------------------------------------
# Indikatoren und Strategien
# ----------------------------------------------------------------------------
def calculate_indicators(df):
    """Berechnet alle notwendigen Indikatoren für die erweiterten Strategien.
    Jeder Wert eines Tages hängt nur von Kursen bis zu diesem Tag ab."""
    # 1. RSI (Relative Strength Index) mit Wilder-Glättung wie bei TradingView/Brokern
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 2. EMA 20 (Trendfilter)
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()

    # 3. Bollinger Bänder (20 Perioden, 2 Standardabweichungen)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['Std_Dev'] = df['Close'].rolling(window=20).std()
    df['Upper_Band'] = df['SMA_20'] + (df['Std_Dev'] * 2)
    df['Lower_Band'] = df['SMA_20'] - (df['Std_Dev'] * 2)

    # 4. ATR (Average True Range für mathematisch genaue Stop-Loss Platzierung, Wilder-Glättung)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.ewm(alpha=1/14, adjust=False, min_periods=14).mean()

    return df

def signal_aus(price, rsi, ema, lower_b, upper_b, atr, mit_short=True):
    """Die Strategien. Gibt (Signal, Stop-Loss, Take-Profit) in der Währung der Kurse zurück."""
    # --- STRATEGIE 1: EMA PULLBACK (Trendfolgend, long) ---
    if price > ema and (price / ema) < 1.015 and rsi < 60:
        stop_loss = price - (1.5 * atr)    # Stop 1,5 ATR unter dem Kurs
        take_profit = price + (3.0 * atr)  # Ziel 3 ATR über dem Kurs -> CRV (Chance-Risiko-Verhältnis) 2:1
        return KAUFEN, stop_loss, take_profit

    # --- STRATEGIE 2: RSI MEAN REVERSION (Antizyklisch, long) ---
    if rsi < 32 or price <= lower_b:
        stop_loss = price - (1.2 * atr)
        take_profit = ema  # Kursziel ist die Rückkehr zum Mittelwert (EMA20)
        return SCHARF_KAUFEN, stop_loss, take_profit

    # --- STRATEGIE 3: ÜBERHITZT – Gewinne sichern bzw. Short auf Rückfall zum Mittelwert ---
    if rsi > 70 or price >= upper_b:
        if mit_short and ema < price:  # Short nur, wenn das Ziel (EMA) unter dem Kurs liegt
            return SCHARF_SHORT, price + (1.2 * atr), ema
        return TEILVERKAUF, price * 0.97, np.nan  # Nachziehender Stopp zur Gewinnsicherung, kein Kursziel

    # --- STRATEGIE 4: EMA PULLBACK (Trendfolgend, short) – Spiegelbild von Strategie 1 ---
    if mit_short and price < ema and (ema / price) < 1.015 and rsi > 40:
        return SHORT, price + (1.5 * atr), price - (3.0 * atr)

    return BEOBACHTEN, np.nan, np.nan

def indikatoren_der_zeile(z):
    werte = [float(z['Close']), float(z['RSI']), float(z['EMA_20']),
             float(z['Lower_Band']), float(z['Upper_Band']), float(z['ATR'])]
    return None if np.isnan(werte).any() else werte

def positionsgroesse(kurs, stop, konto, risiko_prozent, bruchstuecke, bargeld=math.inf):
    """Stückzahl, bei der der Stop-Loss höchstens risiko_prozent des Kontos kostet
    (Position max. MAX_POSITION_PROZENT des Kontos und nicht mehr als das freie Geld). Long und Short."""
    risiko_je_aktie = abs(kurs - stop)
    if risiko_je_aktie <= 0 or bargeld <= 0 or kurs <= 0:
        return 0
    stueck = min(konto * risiko_prozent / 100 / risiko_je_aktie,
                 konto * MAX_POSITION_PROZENT / 100 / kurs,
                 bargeld / kurs)
    return math.floor(stueck * 100 + 1e-9) / 100 if bruchstuecke else math.floor(stueck + 1e-9)

def fehler_zeile(ticker, grund):
    return {"Ticker": ticker, "Signal": FEHLER, "_fehler": grund}

def evaluate_strategies(ticker, df, fx, einst):
    try:
        offen = kerze_noch_offen(df)
        ignoriert = offen and einst.nur_schluss
        if ignoriert:
            df = df.iloc[:-1]
        if len(df) < MIN_KERZEN:
            return fehler_zeile(ticker, f"nur {len(df)} Kerzen – zu wenig Historie")

        df = calculate_indicators(df.copy())
        werte = indikatoren_der_zeile(df.iloc[-1])
        if werte is None:
            return fehler_zeile(ticker, "Indikatoren unvollständig")
        empfehlung, stop_loss, take_profit = signal_aus(*werte, mit_short=einst.mit_short)

        # In Euro umrechnen (Kurse sind in US-Dollar)
        rate = kurs_umrechner(fx, df.index)
        kurs = werte[0] / rate.iloc[-1]
        vortag = float(df['Close'].iloc[-2]) / rate.iloc[-2]
        stop = stop_loss / rate.iloc[-1] if stop_loss > 0 else np.nan
        ziel = take_profit / rate.iloc[-1] if take_profit > 0 else np.nan

        crv = stueck = np.nan
        richtung = 1 if empfehlung in LONG_SIGNALE else -1 if empfehlung in SHORT_SIGNALE else 0
        if richtung and stop > 0 and ziel > 0:
            crv = richtung * (ziel - kurs) / (richtung * (kurs - stop))
            stueck = positionsgroesse(kurs, stop, einst.konto, einst.risiko, einst.bruchstuecke)

        return {
            "Ticker": ticker,
            "Signal": empfehlung,
            "Kurs": kurs,
            "Tag %": (kurs / vortag - 1) * 100 if vortag > 0 else np.nan,
            "RSI": werte[1],
            "Stop": stop,
            "Ziel": ziel,
            "CRV": crv,
            "Stück": stueck,
            "Einsatz": stueck * kurs,
            "_stand": df.index[-1],
            "_offen": offen and not ignoriert,
            "_ignoriert": ignoriert,
        }

    except Exception as e:
        return fehler_zeile(ticker, f"Rechenfehler: {str(e)[:80]}")


# ----------------------------------------------------------------------------
# Virtuelles Depot: der Bot handelt die letzten Monate mit dem Startkapital nach
# ----------------------------------------------------------------------------
def positionswert(p, kurs_usd, fx):
    """Wert einer Position in €. Long: Aktien zum aktuellen Kurs. Short: hinterlegter Einsatz
    plus Gewinn (bzw. minus Verlust) aus dem gefallenen (bzw. gestiegenen) Kurs."""
    if p["richtung"] > 0:
        return p["stueck"] * kurs_usd / fx
    return p["stueck"] * (p["einsatz_je_stueck"] + (p["einstieg_usd"] - kurs_usd) / fx)

def simuliere_depot(daten, fx_je_ticker, einst):
    """Spielt die Strategien rückwirkend mit einem virtuellen Depot durch.
    Regeln: Signal zum Schlusskurs -> Einstieg/Teilverkauf zur Eröffnung des nächsten Handelstags;
    Stop/Ziel werden im Tagesverlauf geprüft (bei beidem am selben Tag zählt der Stop);
    Gebühr je Order; Beträge in € zum jeweiligen Tageswechselkurs; je Ticker höchstens eine Position."""
    tabellen = {}
    for t, df in daten.items():
        df = calculate_indicators(df.copy())
        df["FX"] = kurs_umrechner(fx_je_ticker.get(t), df.index)
        df["Nr"] = np.arange(len(df))
        tabellen[t] = df
    if not tabellen:
        return None
    alle_tage = sorted(set().union(*(df.index for df in tabellen.values())))
    start = alle_tage[-1] - pd.DateOffset(months=einst.rueckblick)
    tage = [d for d in alle_tage if d > start]
    if len(tage) < 5:
        return None

    gebuehr = einst.gebuehr
    bargeld = float(einst.konto)
    depotwert = float(einst.konto)  # zum letzten Schlusskurs – Grundlage für die Positionsgröße
    positionen = {}    # Ticker -> offene Position
    auftraege = {}     # Ticker -> Auftrag für die nächste Eröffnung
    trades = []        # abgeschlossene Positionen
    verlauf = []       # (Tag, Depotwert)
    letzter_kurs = {}  # Ticker -> (Schlusskurs in $, Wechselkurs) für Tage ohne Handel
    gebuehren = 0.0

    def verkaufe(p, stueck, kurs_usd, rate):
        """Schließt 'stueck' Aktien der Position (Long: verkaufen, Short: zurückkaufen)."""
        nonlocal bargeld, gebuehren
        teil = dict(p, stueck=stueck)
        erloes = positionswert(teil, kurs_usd, rate) - gebuehr
        bargeld += erloes
        gebuehren += gebuehr
        p["erloes"] += erloes
        p["stueck"] -= stueck

    for tag in tage:
        # 1) Aufträge vom Vortag zur Eröffnung ausführen
        for t in list(auftraege):
            df = tabellen[t]
            if tag not in df.index:
                continue  # Ticker handelt heute nicht – Auftrag wartet
            art, signal, stop, ziel = auftraege.pop(t)
            z = df.loc[tag]
            eroeffnung = float(z["Open"]) if not pd.isna(z["Open"]) else float(z["Close"])
            rate = float(z["FX"])
            if art == "einstieg":
                r = 1 if signal in LONG_SIGNALE else -1
                # Kurslücke über das Ziel oder hinter den Stop: Setup ungültig
                if t in positionen or not (r * (eroeffnung - stop) > 0 and r * (ziel - eroeffnung) > 0):
                    continue
                stueck = positionsgroesse(eroeffnung / rate, stop / rate, depotwert, einst.risiko,
                                          einst.bruchstuecke, bargeld - gebuehr)
                einsatz = stueck * eroeffnung / rate
                if stueck <= 0 or einsatz < MIN_EINSATZ:
                    continue
                bargeld -= einsatz + gebuehr
                gebuehren += gebuehr
                positionen[t] = {"ticker": t, "richtung": r, "signal": signal, "stueck": stueck,
                                 "einstieg_usd": eroeffnung, "einsatz_je_stueck": eroeffnung / rate,
                                 "stop": stop, "ziel": ziel, "kauf_tag": tag, "kosten": einsatz + gebuehr,
                                 "erloes": 0.0, "teil_geschlossen": False}
            elif art == "teil" and t in positionen:
                # Gegensignal (überhitzt bei Long, überverkauft bei Short): Hälfte schließen, Stop nachziehen
                p = positionen[t]
                p["stop"] = max(p["stop"], stop) if p["richtung"] > 0 else min(p["stop"], stop)
                if not p["teil_geschlossen"]:
                    haelfte = (math.floor(p["stueck"] / 2 * 100) / 100 if einst.bruchstuecke
                               else math.floor(p["stueck"] / 2))
                    if haelfte > 0 and haelfte * eroeffnung / rate >= MIN_EINSATZ:
                        p["teil_geschlossen"] = True
                        verkaufe(p, haelfte, eroeffnung, rate)

        # 2) Stop und Ziel im Tagesverlauf prüfen
        for t in list(positionen):
            p, df = positionen[t], tabellen[t]
            if tag not in df.index:
                continue
            z = df.loc[tag]
            r, rate = p["richtung"], float(z["FX"])
            eroeffnung = float(z["Open"]) if not pd.isna(z["Open"]) else float(z["Close"])
            gegen = float(z["Low"]) if r > 0 else float(z["High"])   # ungünstigster Kurs des Tages
            fuer = float(z["High"]) if r > 0 else float(z["Low"])    # günstigster Kurs des Tages
            preis = grund = None
            if p["kauf_tag"] != tag and r * (eroeffnung - p["stop"]) <= 0:
                preis, grund = eroeffnung, "Stop (Kurslücke)"
            elif p["kauf_tag"] != tag and r * (eroeffnung - p["ziel"]) >= 0:
                preis, grund = eroeffnung, "Ziel (Kurslücke)"
            elif r * (gegen - p["stop"]) <= 0:
                preis, grund = p["stop"], "Stop"
            elif r * (fuer - p["ziel"]) >= 0:
                preis, grund = p["ziel"], "Ziel"
            if preis is not None:
                verkaufe(p, p["stueck"], preis, rate)
                del positionen[t]
                if p["teil_geschlossen"]:
                    grund += " (½ vorher)"
                trades.append({**p, "verkauf_tag": tag, "verkauf_preis": preis / rate, "grund": grund})

        # 3) Signale zum Schlusskurs -> Aufträge für den nächsten Handelstag
        for t, df in tabellen.items():
            if tag not in df.index:
                continue
            z = df.loc[tag]
            letzter_kurs[t] = (float(z["Close"]), float(z["FX"]))
            werte = indikatoren_der_zeile(z)
            if werte is None or z["Nr"] < MIN_KERZEN - 1:
                continue
            signal, stop, ziel = signal_aus(*werte, mit_short=einst.mit_short)
            p = positionen.get(t)
            if p is None and (signal in LONG_SIGNALE or signal in SHORT_SIGNALE) and stop > 0 and ziel > 0:
                auftraege[t] = ("einstieg", signal, stop, ziel)
            elif p is not None and p["richtung"] > 0 and signal in (SCHARF_SHORT, TEILVERKAUF):
                auftraege[t] = ("teil", signal, werte[0] * 0.97, np.nan)
            elif p is not None and p["richtung"] < 0 and signal == SCHARF_KAUFEN:
                auftraege[t] = ("teil", signal, werte[0] * 1.03, np.nan)

        # 4) Depotwert zum Schlusskurs
        depotwert = bargeld + sum(positionswert(p, *letzter_kurs[t]) for t, p in positionen.items())
        verlauf.append((tag, depotwert))

    # Vergleich: das Startkapital gleichmäßig aufteilen und jeden Ticker an seinem ersten Handelstag
    # im Zeitraum kaufen und halten (Ticker, die erst später starten, z. B. Börsengänge, bleiben Bargeld)
    anteil = einst.konto / len(tabellen)
    halten = {}  # Ticker -> (Kauftag, Stück)
    for t, df in tabellen.items():
        eigene = df.index[df.index >= tage[0]]
        if len(eigene) and eigene[0] - tage[0] <= pd.Timedelta(days=7):
            z = df.loc[eigene[0]]
            eroeffnung = float(z["Open"]) if not pd.isna(z["Open"]) else float(z["Close"])
            halten[t] = (eigene[0], (anteil - gebuehr) / (eroeffnung / float(z["FX"])))
    vergleich = None
    if halten:
        kurse, werte_halten = {}, []
        for tag in tage:
            wert = anteil * (len(tabellen) - len(halten))
            for t, (kauftag, stueck) in halten.items():
                df = tabellen[t]
                if tag in df.index:
                    kurse[t] = float(df.loc[tag, "Close"]) / float(df.loc[tag, "FX"])
                wert += stueck * kurse[t] if tag >= kauftag else anteil
            werte_halten.append(wert)
        vergleich = pd.Series(werte_halten, index=[d for d, _ in verlauf])

    for t, p in positionen.items():  # offene Positionen zum letzten Kurs bewerten
        p["wert"] = positionswert(p, *letzter_kurs[t])
        p["kurs_jetzt"] = letzter_kurs[t][0] / letzter_kurs[t][1]

    werte = pd.Series([w for _, w in verlauf], index=[d for d, _ in verlauf])
    hoch = werte.cummax()
    return {
        "start": tage[0], "ende": tage[-1], "start_wert": float(einst.konto), "end_wert": float(werte.iloc[-1]),
        "verlauf": werte, "vergleich": vergleich, "trades": trades, "offen": list(positionen.values()),
        "nicht_gehalten": [t for t in tabellen if t not in halten],
        "gebuehren": gebuehren, "max_rueckgang": float(((hoch - werte) / hoch).max() * 100), "bargeld": bargeld,
    }


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

def kopfzeilen(zeilen, einst, fx_heute, waehrung):
    ok = [z for z in zeilen if "_stand" in z]
    stand = max(z["_stand"] for z in ok)
    risiko_betrag = einst.konto * einst.risiko / 100
    titel = (f"📈 SWING-SCANNER · Daten bis {stand:%d.%m.%Y} · Konto {de(einst.konto, 0)} {waehrung} · "
             f"Risiko je Trade {prozent(einst.risiko)} % = {de(risiko_betrag, 0)} {waehrung}")
    if fx_heute:
        titel += f" · 1 € = {de(fx_heute, 4)} $"
    anzahl = pd.Series([z["Signal"] for z in zeilen]).value_counts()
    zusammenfassung = " · ".join(f"{anzahl[s]}× {s}" for s in PRIORITAET if s in anzahl)
    hinweise = []
    if not fx_heute:
        hinweise.append("⚠️ Wechselkurs EUR/USD nicht verfügbar – US-Kurse nicht umgerechnet (Beträge in $).")
    if any(z["_offen"] for z in ok):
        hinweise.append("⏳ US-Börse noch offen: Die heutige Kerze ist nicht fertig, Signale können sich bis "
                        "Börsenschluss (16:00 New York) noch ändern. Mit --nur-schluss nur fertige Tage bewerten.")
    if any(z["_ignoriert"] for z in ok):
        hinweise.append("⏳ Laufende Tageskerze ignoriert (--nur-schluss): Kurs = letzter Schlusskurs.")
    for z in ok:
        if (stand - z["_stand"]).days > 5:
            hinweise.append(f"⚠️ {z['Ticker']}: letzte Kurse vom {z['_stand']:%d.%m.%Y} – veraltet?")
    return titel, zusammenfassung, hinweise

def fusszeilen(zeilen, einst, waehrung):
    fuss = []
    fehler = {}
    for z in zeilen:
        if "_fehler" in z:
            fehler.setdefault(z["_fehler"], []).append(z["Ticker"])
    for grund, ticker in fehler.items():
        fuss.append(f"❌ {', '.join(ticker)}: {grund}")
    if fehler:
        fuss.append("")
    vorkommend = {z["Signal"] for z in zeilen}
    for signal, text in LEGENDE.items():
        if signal in SHORT_SIGNALE and not einst.mit_short:
            continue
        if signal != TEILVERKAUF or TEILVERKAUF in vorkommend:
            fuss.append(f"{signal}: {text}")
    umrechnung = "US-Kurse umgerechnet" if waehrung == "€" else "Wechselkurs nicht verfügbar, nicht umgerechnet"
    fuss.append(f"Kurs, Stop, Ziel und Einsatz in {waehrung} ({umrechnung}). Stück = so viele Aktien, "
                f"dass du am Stop höchstens {prozent(einst.risiko)} % des Kontos verlierst "
                f"(max. {MAX_POSITION_PROZENT} % des Kontos je Position). CRV = Chance ÷ Risiko.")
    if einst.mit_short:
        fuss.append("🔻 Short = auf fallende Kurse setzen (z. B. per CFD oder Turbo-Schein). Verluste sind dabei "
                    "nach oben offen – den Stop unbedingt setzen.")
    fuss.append("💡 Kurs = letzter Kurs; der echte Kurs beim Einstieg am nächsten Tag weicht ab – Stückzahl dann "
                "neu rechnen. Keine Anlageberatung.")
    return fuss

def als_text(tabelle, titel, zusammenfassung, hinweise, fuss, formate, farbig=False):
    # east_asian_width: Emojis zählen als 2 Zeichen breit, damit die Spalten bündig bleiben
    with pd.option_context("display.unicode.east_asian_width", True):
        text = tabelle.to_string(index=False, formatters=formate, na_rep="–")
    zeilen = text.splitlines()
    linie = "=" * len(zeilen[0])

    ausgabe = ["", titel, f"   {zusammenfassung}", *hinweise, linie, zeilen[0]]
    for zeile, signal in zip(zeilen[1:], tabelle["Signal"]):
        code = ANSI.get(signal) if farbig else None
        ausgabe.append(f"{code}{zeile}\033[0m" if code else zeile)
    ausgabe += [linie, *fuss]
    return "\n".join(ausgabe)

def absatz(text, stil=""):
    return f'<p style="margin: 2px 0; {stil}">{html.escape(text)}</p>' if text else "<br>"

def tabelle_als_html(tabelle, formate, zellfarben=None, links=2):
    """Styler-Tabelle; ohne jinja2 eine schlichte, aber formatierte HTML-Tabelle."""
    try:
        stil = tabelle.style
        if zellfarben:
            stil = stil.apply(zellfarben, axis=1)
        links_css = ", ".join(f"td.col{i}" for i in range(links))
        return (stil.format(formate, na_rep="–")
                .hide(axis="index")
                .set_table_styles([
                    {"selector": "th", "props": "padding: 4px 10px; text-align: center;"},
                    {"selector": "td", "props": "padding: 4px 10px; text-align: right;"},
                    {"selector": links_css, "props": "text-align: left; font-weight: bold;"},
                ])
                .to_html())
    except (ImportError, AttributeError):  # ohne jinja2 gibt es keinen Styler
        return tabelle.to_html(index=False, na_rep="–", formatters=formate)

def zeige(html_teil, text_teil):
    """Im Notebook als HTML mit Textfassung (Spyder, qtconsole, jupyter console zeigen die Textfassung)."""
    from IPython.display import display
    display({"text/html": html_teil, "text/plain": text_teil}, raw=True)

def zeige_scanner(tabelle, titel, zusammenfassung, hinweise, fuss, formate, notebook):
    if not notebook:
        print(als_text(tabelle, titel, zusammenfassung, hinweise, fuss, formate, farbig=farben_im_terminal()))
        return

    def zeilenfarbe(zeile):
        bg, fg = FARBEN.get(zeile["Signal"], (None, None))
        return [f"background-color: {bg}; color: {fg}" if bg else ""] * len(zeile)

    kopf = absatz(titel, "font-size: 1.15em; font-weight: bold;") + absatz(zusammenfassung)
    kopf += "".join(absatz(h, "color: #b26a00;") for h in hinweise)
    fuss_html = "".join(absatz(f, "font-size: 0.9em; opacity: 0.8;") for f in fuss)
    zeige(kopf + '<div style="margin: 8px 0;">' + tabelle_als_html(tabelle, formate, zeilenfarbe) + "</div>"
          + fuss_html, als_text(tabelle, titel, zusammenfassung, hinweise, fuss, formate))


# --- Ausgabe des virtuellen Depots -------------------------------------------
TRADE_SPALTEN = ["Ticker", "Art", "Einstieg", "Einstiegskurs", "Ausstieg", "Ausstiegskurs", "Grund", "Einsatz",
                 "Ergebnis", "Ergebnis %"]
TRADE_FORMATE = {
    "Einstiegskurs": lambda v: de(v, 2), "Ausstiegskurs": lambda v: de(v, 2), "Einsatz": lambda v: de(v, 0),
    "Ergebnis": lambda v: de(v, 2, True), "Ergebnis %": lambda v: de(v, 1, True),
}

def depot_auswertung(erg, waehrung):
    trades = erg["trades"]
    rendite = (erg["end_wert"] / erg["start_wert"] - 1) * 100
    zeilen = [
        f"🤖 VIRTUELLES DEPOT · Der Bot handelt seit {erg['start']:%d.%m.%Y} mit "
        f"{de(erg['start_wert'], 0)} {waehrung} nach seinen eigenen Signalen",
        f"Depotwert heute: {de(erg['end_wert'])} {waehrung} ({de(rendite, 1, True)} %) · "
        f"davon frei: {de(erg['bargeld'])} {waehrung} · {len(erg['offen'])} offene Position(en)",
    ]
    if erg["vergleich"] is not None:
        v_ende = float(erg["vergleich"].iloc[-1])
        ohne = f" (ohne {', '.join(erg['nicht_gehalten'])} – erst später gehandelt)" if erg["nicht_gehalten"] else ""
        zeilen.append(f"Zum Vergleich – alle Ticker am {erg['start']:%d.%m.} kaufen und halten{ohne}: "
                      f"{de(v_ende)} {waehrung} ({de((v_ende / erg['start_wert'] - 1) * 100, 1, True)} %)")
    if trades:
        gewinner = sum(1 for p in trades if p["erloes"] > p["kosten"])
        zeilen.append(f"Abgeschlossene Trades: {len(trades)} · Gewinner: {gewinner} "
                      f"({de(gewinner / len(trades) * 100, 0)} %) · größter Rückgang des Depots: "
                      f"{de(erg['max_rueckgang'], 1)} % · Gebühren: {de(erg['gebuehren'])} {waehrung}")
        teile = []
        for name, r in (("Long", 1), ("Short", -1)):
            auswahl = [p for p in trades if p["richtung"] == r]
            if auswahl:
                summe = sum(p["erloes"] - p["kosten"] for p in auswahl)
                treffer = sum(1 for p in auswahl if p["erloes"] > p["kosten"])
                teile.append(f"{name}: {len(auswahl)} Trades, {treffer} Gewinner, {de(summe, 2, True)} {waehrung}")
        zeilen.append(" · ".join(teile))
    else:
        zeilen.append(f"Noch keine abgeschlossenen Trades · Gebühren: {de(erg['gebuehren'])} {waehrung}")
    return zeilen

def trade_tabelle(erg):
    zeilen = []
    for p in erg["offen"]:
        ergebnis = p["erloes"] + p["wert"] - p["kosten"]
        zeilen.append({"Ticker": p["ticker"], "Art": "Long" if p["richtung"] > 0 else "Short",
                       "Einstieg": f"{p['kauf_tag']:%d.%m.%y}", "Einstiegskurs": p["einsatz_je_stueck"],
                       "Ausstieg": "offen", "Ausstiegskurs": p["kurs_jetzt"],
                       "Grund": "noch im Depot" + (" (½ geschlossen)" if p["teil_geschlossen"] else ""),
                       "Einsatz": p["kosten"], "Ergebnis": ergebnis, "Ergebnis %": ergebnis / p["kosten"] * 100,
                       "_offen": True, "_sort": p["kauf_tag"]})
    for p in erg["trades"]:
        ergebnis = p["erloes"] - p["kosten"]
        zeilen.append({"Ticker": p["ticker"], "Art": "Long" if p["richtung"] > 0 else "Short",
                       "Einstieg": f"{p['kauf_tag']:%d.%m.%y}", "Einstiegskurs": p["einsatz_je_stueck"],
                       "Ausstieg": f"{p['verkauf_tag']:%d.%m.%y}", "Ausstiegskurs": p["verkauf_preis"],
                       "Grund": p["grund"], "Einsatz": p["kosten"], "Ergebnis": ergebnis,
                       "Ergebnis %": ergebnis / p["kosten"] * 100, "_offen": False, "_sort": p["verkauf_tag"]})
    if not zeilen:
        return None
    df = pd.DataFrame(zeilen)
    df = pd.concat([df[df["_offen"]], df[~df["_offen"]].sort_values("_sort", ascending=False)])
    return df[TRADE_SPALTEN].reset_index(drop=True)

def depot_chart_svg(erg, waehrung):
    """Liniendiagramm Depotwert vs. Kaufen-und-Halten als SVG (Hover zeigt die Werte je Tag)."""
    bot = erg["verlauf"]
    vergleich = erg["vergleich"]
    reihen = [("Bot", bot, "--s1")] + ([("Kaufen & Halten", vergleich, "--s2")] if vergleich is not None else [])
    B, H, L, R, O, U = 720, 260, 64, 170, 14, 28
    alle = pd.concat([r for _, r, _ in reihen] + [pd.Series([erg["start_wert"]])])
    lo, hi = float(alle.min()), float(alle.max())
    rand = max((hi - lo) * 0.08, erg["start_wert"] * 0.01)
    lo, hi = lo - rand, hi + rand
    n = len(bot)

    def x(i):
        return L + (B - L - R) * i / max(n - 1, 1)

    def y(w):
        return O + (H - O - U) * (1 - (w - lo) / (hi - lo))

    teile = []
    # Gitterlinien mit runden Werten
    roh = (hi - lo) / 4
    schritt = 10 ** math.floor(math.log10(roh))
    schritt *= next(f for f in (1, 2, 2.5, 5, 10) if f * schritt >= roh)
    w = math.ceil(lo / schritt) * schritt
    while w <= hi:
        teile.append(f'<line x1="{L}" x2="{B - R}" y1="{y(w):.1f}" y2="{y(w):.1f}" class="gitter"/>'
                     f'<text x="{L - 8}" y="{y(w) + 4:.1f}" text-anchor="end" class="achse">{de(w, 0)}</text>')
        w += schritt
    # Startkapital als Bezugslinie
    teile.append(f'<line x1="{L}" x2="{B - R}" y1="{y(erg["start_wert"]):.1f}" y2="{y(erg["start_wert"]):.1f}" '
                 f'class="start"/>')
    # Monatsbeschriftung
    monate = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    letzter_monat, beschriftet = None, False
    for i, d in enumerate(bot.index):
        if d.month != letzter_monat:
            if letzter_monat is not None:
                teile.append(f'<text x="{x(i):.1f}" y="{H - 8}" text-anchor="middle" class="achse">'
                             f'{monate[d.month - 1]}</text>')
                beschriftet = True
            letzter_monat = d.month
    if not beschriftet:
        teile.append(f'<text x="{L}" y="{H - 8}" class="achse">{bot.index[0]:%d.%m.}</text>'
                     f'<text x="{B - R}" y="{H - 8}" text-anchor="end" class="achse">{bot.index[-1]:%d.%m.}</text>')
    # Linien, Endpunkte und Endbeschriftungen (nicht überlappend)
    enden = []
    for name, reihe, var in reihen:
        punkte = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(reihe.values))
        teile.append(f'<polyline points="{punkte}" fill="none" stroke="var({var})" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        enden.append({"y": y(reihe.iloc[-1]), "label_y": y(reihe.iloc[-1]), "name": name,
                      "wert": reihe.iloc[-1], "var": var})
    enden.sort(key=lambda e: e["y"])
    for i in range(1, len(enden)):
        enden[i]["label_y"] = max(enden[i]["y"], enden[i - 1]["label_y"] + 16)
    for e in enden:
        teile.append(f'<circle cx="{x(n - 1):.1f}" cy="{e["y"]:.1f}" r="4" fill="var({e["var"]})"/>'
                     f'<text x="{x(n - 1) + 10:.1f}" y="{e["label_y"] + 4:.1f}" class="label">'
                     f'{html.escape(e["name"])} {de(e["wert"], 0)} {waehrung}</text>')
    # Hover: unsichtbare Streifen je Tag mit Tooltip
    breite = (B - L - R) / max(n - 1, 1)
    for i, d in enumerate(bot.index):
        tip = f"{d:%d.%m.%Y} · Bot {de(bot.iloc[i])} {waehrung}"
        if vergleich is not None:
            tip += f" · Kaufen & Halten {de(vergleich.iloc[i])} {waehrung}"
        teile.append(f'<rect x="{x(i) - breite / 2:.1f}" y="{O}" width="{breite:.1f}" height="{H - O - U}" '
                     f'class="hover"><title>{html.escape(tip)}</title></rect>')

    legende = "".join(f'<span style="margin-right: 16px;"><span style="display: inline-block; width: 16px; '
                      f'height: 2px; background: var({var}); vertical-align: middle; margin-right: 6px;"></span>'
                      f'{html.escape(name)}</span>' for name, _, var in reihen)
    legende += ('<span><span style="display: inline-block; width: 16px; height: 1px; background: currentColor; '
                'opacity: 0.5; vertical-align: middle; margin-right: 6px;"></span>Startkapital</span>')
    return f"""<div class="viz-root">
<style>
/* Texte und Hilfslinien erben die Schriftfarbe des Notebooks (hell wie dunkel lesbar) */
.viz-root {{ --s1: #2a78d6; --s2: #eb6834; --start: currentColor; color: inherit; max-width: {B}px; }}
.viz-root .gitter {{ stroke: currentColor; stroke-opacity: 0.15; stroke-width: 1; }}
.viz-root .start {{ stroke: currentColor; stroke-opacity: 0.5; stroke-width: 1; }}
.viz-root .achse {{ fill: currentColor; fill-opacity: 0.7; font-size: 11px; }}
.viz-root .label {{ fill: currentColor; font-size: 12px; font-weight: 600; }}
.viz-root .hover {{ fill: transparent; }}
.viz-root .hover:hover {{ fill: currentColor; fill-opacity: 0.08; }}
</style>
<div style="font-size: 12px; opacity: 0.8; margin: 4px 0;">{legende}</div>
<svg viewBox="0 0 {B} {H}" width="100%" style="max-width: {B}px; font-family: inherit; overflow: visible;" role="img"
 aria-label="Depotwert des Bots im Vergleich zu Kaufen und Halten">{''.join(teile)}</svg>
</div>"""

def zeige_depot(erg, einst, waehrung, notebook):
    zusammenfassung = depot_auswertung(erg, waehrung)
    tabelle = trade_tabelle(erg)
    weggelassen = 0
    if tabelle is not None:
        anzeige = len(erg["offen"]) + MAX_TRADES_ANZEIGE
        weggelassen = max(len(tabelle) - anzeige, 0)
        tabelle = tabelle.iloc[:anzeige]
    hinweis = (f"… {weggelassen} ältere Trades nicht angezeigt – alle Trades speichert --csv in einer eigenen Datei."
               if weggelassen else "")
    regeln = (f"Regeln: Einstieg zur Eröffnung am Tag nach dem Signal, Ausstieg an Stop oder Ziel "
              f"(bei beidem am selben Tag zählt der Stop); Gegensignal schließt die Hälfte zur Eröffnung; "
              f"{de(einst.gebuehr)} {waehrung} Gebühr je Order; "
              f"{'Bruchteile von Aktien erlaubt' if einst.bruchstuecke else 'nur ganze Aktien'}; "
              f"Positionsgröße wie im Scanner. "
              f"{'Shorts ohne Leihgebühren/Finanzierungskosten gerechnet. ' if einst.mit_short else ''}"
              f"Simulation mit vergangenen Kursen – kein echtes Geld, keine Garantie für die Zukunft.")
    text = "\n".join(["", zusammenfassung[0], *("   " + z for z in zusammenfassung[1:])])
    if tabelle is not None:
        with pd.option_context("display.unicode.east_asian_width", True):
            text += "\n\n" + tabelle.to_string(index=False, formatters=TRADE_FORMATE, na_rep="–")
    if hinweis:
        text += "\n" + hinweis
    text += "\n" + regeln
    if not notebook:
        print(text)
        return

    def ergebnisfarbe(zeile):
        bg = "#c8e6c9" if zeile["Ergebnis"] > 0 else "#ffcdd2" if zeile["Ergebnis"] < 0 else ""
        return [f"background-color: {bg}; color: #1b1b1b; font-weight: bold;"
                if bg and s in ("Ergebnis", "Ergebnis %") else "" for s in zeile.index]

    teile = [absatz(zusammenfassung[0], "font-size: 1.15em; font-weight: bold; margin-top: 18px;")]
    teile += [absatz(z) for z in zusammenfassung[1:]]
    teile.append(depot_chart_svg(erg, waehrung))
    if tabelle is not None:
        teile.append('<div style="margin: 8px 0;">' + tabelle_als_html(tabelle, TRADE_FORMATE, ergebnisfarbe, 2)
                     + "</div>")
    if hinweis:
        teile.append(absatz(hinweis, "font-size: 0.9em;"))
    teile.append(absatz(regeln, "font-size: 0.9em; opacity: 0.8;"))
    zeige("".join(teile), text)

def speichere_csv(tabelle, datei):
    # Semikolon + Dezimalkomma, damit ein deutsches Excel die Datei direkt richtig öffnet
    ganze = [s for s in ("Stück",) if s in tabelle and (tabelle[s].dropna() % 1 == 0).all()]
    try:
        tabelle.astype({s: "Int64" for s in ganze}).to_csv(datei, index=False, sep=";", decimal=",", encoding="utf-8-sig", float_format="%.2f")
    except OSError as e:
        print(f"❌ CSV konnte nicht gespeichert werden ({e.strerror or e}): {os.path.abspath(datei)} "
              "– ist die Datei noch in Excel geöffnet oder der Ordner falsch?")
        return
    print(f"💾 Gespeichert: {os.path.abspath(datei)}")


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

    print(f"🤖 Lade Kurse für {len(einst.ticker_liste)} Ticker und prüfe die Swing-Trading-Strategien ...")
    periode = "1y" if einst.rueckblick <= 6 else "2y"  # Vorlauf für die Indikatoren vor dem Rückblick
    unterstuetzt = [t for t in einst.ticker_liste if waehrung_von(t)]
    daten, gruende = lade_kurse(unterstuetzt + [FX_TICKER], periode, einst.debug)
    fx_daten = daten.pop(FX_TICKER, None)
    fx = fx_daten["Close"] if fx_daten is not None else None
    waehrung = "€" if fx is not None else "$"
    # US-Werte werden mit EUR/USD umgerechnet, Werte von Euro-Börsen nicht
    fx_je_ticker = {t: fx if waehrung_von(t) == "USD" else None for t in unterstuetzt}
    zeilen = []
    for t in einst.ticker_liste:
        if t not in fx_je_ticker:
            zeilen.append(fehler_zeile(t, "Währung nicht unterstützt – nur US- und Euro-Börsen"))
        elif t in daten:
            zeilen.append(evaluate_strategies(t, daten[t], fx_je_ticker[t], einst))
        else:
            zeilen.append(fehler_zeile(t, gruende[t]))

    if not any("_stand" in z for z in zeilen):
        print("\n❌ Für keinen Ticker konnten Kursdaten ausgewertet werden – meist keine Verbindung zu Yahoo "
              "oder Yahoo-Limit erreicht.")
        for f in fusszeilen(zeilen, einst, waehrung):
            if f.startswith("❌"):
                print(f)
        print("Internetverbindung prüfen oder in 1–2 Minuten erneut starten.")
        return None

    # Sortieren: wichtigste Signale oben, innerhalb eines Signals das beste CRV zuerst, Fehler ganz unten
    tabelle = pd.DataFrame(zeilen).reindex(columns=SPALTEN + ["_fehler"])
    tabelle["_prio"] = tabelle["Signal"].map(PRIORITAET)
    tabelle = tabelle.sort_values(["_prio", "CRV"], ascending=[True, False], na_position="last", kind="stable")
    tabelle = tabelle[SPALTEN].reset_index(drop=True)

    fx_heute = float(fx.iloc[-1]) if fx is not None else None
    titel, zusammenfassung, hinweise = kopfzeilen(zeilen, einst, fx_heute, waehrung)
    notebook = im_notebook()
    zeige_scanner(tabelle, titel, zusammenfassung, hinweise, fusszeilen(zeilen, einst, waehrung),
                  tabellen_formate(einst), notebook)

    depot = None
    if einst.rueckblick > 0:
        # wie im Scanner: mit --nur-schluss auch im Depot keine unfertige Tageskerze
        depot_daten = {t: df.iloc[:-1] if einst.nur_schluss and kerze_noch_offen(df) else df
                       for t, df in daten.items() if t in fx_je_ticker}
        depot = simuliere_depot(depot_daten, fx_je_ticker, einst)
        if depot is not None:
            zeige_depot(depot, einst, waehrung, notebook)

    if einst.csv:
        speichere_csv(tabelle, einst.csv)
        trades = trade_tabelle(depot) if depot is not None else None
        if trades is not None:
            name, endung = os.path.splitext(einst.csv)
            speichere_csv(trades, f"{name}_trades{endung or '.csv'}")
    return tabelle, depot

if __name__ == "__main__":
    # Unter %run in Colab/Jupyter stehen Tabelle und Depot danach als 'ergebnis' zur Verfügung
    ergebnis = main()
