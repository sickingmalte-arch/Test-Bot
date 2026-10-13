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
#   python swing_scanner.py --ticker "AAPL, NFLX, SOFI" --konto 5000 --risiko 1
# ============================================================================
TICKER_LISTE = [
    "SE", "HIMS", "NOW", "INTU", "CRWV", "NBIS",
    "MELI", "IREN", "NFLX", "AAPL", "ASTS", "SOFI"
]
KONTO = 10_000              # Kontogröße in $ (alle Kurse sind in US-Dollar)
RISIKO_PROZENT = 1.0        # max. Verlust pro Trade in % des Kontos, wenn der Stop-Loss greift
MAX_POSITION_PROZENT = 25   # eine einzelne Position höchstens so viel % des Kontos

# Mindestanzahl an Tageskerzen, damit RSI/EMA/Bollinger/ATR aussagekräftig sind
MIN_KERZEN = 30

# Signale (Reihenfolge = Sortierung in der Tabelle)
SCHARF_KAUFEN = "🚀 SCHARF KAUFEN"
KAUFEN = "⭐ KAUFEN"
BEOBACHTEN = "BEOBACHTEN"
TEILVERKAUF = "⚠️ TEILVERKAUF"
FEHLER = "❌ FEHLER"
PRIORITAET = {SCHARF_KAUFEN: 1, KAUFEN: 2, BEOBACHTEN: 3, TEILVERKAUF: 4, FEHLER: 5}

LEGENDE = {
    SCHARF_KAUFEN: "RSI unter 32 oder Kurs am/unter dem unteren Bollinger-Band (Gegenbewegung). "
                   "Ziel = EMA 20, Stop = Kurs − 1,2 × ATR",
    KAUFEN: "Kurs 0–1,5 % über der EMA 20 und RSI unter 60 (Rücksetzer im Trend). "
            "Ziel = Kurs + 3 × ATR, Stop = Kurs − 1,5 × ATR",
    TEILVERKAUF: "RSI über 70 oder Kurs am/über dem oberen Band. Falls im Depot: "
                 "Teilgewinne sichern, Stop auf 3 % unter Kurs nachziehen",
    BEOBACHTEN: "kein Setup – nichts tun",
}

# Tabellenspalten und ihr Zahlenformat
SPALTEN = ["Ticker", "Signal", "Kurs", "Tag %", "RSI", "Stop", "Ziel", "CRV", "Stück", "Einsatz $"]
FORMATE = {
    "Kurs": "{:.2f}", "Tag %": "{:+.1f}", "RSI": "{:.1f}", "Stop": "{:.2f}", "Ziel": "{:.2f}",
    "CRV": "{:.1f}", "Stück": "{:.0f}", "Einsatz $": "{:.0f}",
}

# Zeilenfarben: (Hintergrund, Schrift) für die Notebook-Tabelle, ANSI-Codes fürs Terminal
FARBEN = {
    SCHARF_KAUFEN: ("#1b5e20", "#ffffff"),
    KAUFEN: ("#c8e6c9", "#1b1b1b"),
    TEILVERKAUF: ("#ffe0b2", "#1b1b1b"),
    FEHLER: ("#eeeeee", "#555555"),
}
ANSI = {SCHARF_KAUFEN: "\033[1;97;42m", KAUFEN: "\033[32m", TEILVERKAUF: "\033[33m", FEHLER: "\033[2m"}


# ----------------------------------------------------------------------------
# Einstellungen
# ----------------------------------------------------------------------------
def zahl(text):
    """Erlaubt auch ein deutsches Komma, z. B. --risiko 1,5"""
    try:
        return float(str(text).replace(",", "."))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' ist keine Zahl")

def ticker_aus_text(text):
    """'aapl, NFLX nflx' -> ['AAPL', 'NFLX'] (groß geschrieben, ohne Duplikate, Reihenfolge bleibt)"""
    liste = [t.upper() for t in re.split(r"[,;\s]+", text or "") if t]
    return list(dict.fromkeys(liste))

def lies_einstellungen():
    p = argparse.ArgumentParser(description="Swing-Trading-Scanner für deine Watchlist")
    p.add_argument("--ticker", help='z. B. "AAPL, NFLX, SOFI" (Standard: TICKER_LISTE im Skript)')
    p.add_argument("--konto", type=zahl, default=KONTO, help="Kontogröße in $")
    p.add_argument("--risiko", type=zahl, default=RISIKO_PROZENT, help="Risiko pro Trade in %% des Kontos")
    p.add_argument("--nur-schluss", action="store_true",
                   help="laufende Tageskerze ignorieren und nur abgeschlossene Tage bewerten")
    p.add_argument("--csv", metavar="DATEI", help="Ergebnis zusätzlich als CSV speichern (für Excel)")
    p.add_argument("--debug", action="store_true", help="Original-Meldungen von yfinance anzeigen")
    einst, unbekannt = p.parse_known_args()
    if unbekannt:
        print(f"Hinweis: unbekannte Angaben ignoriert: {' '.join(unbekannt)}")
    if einst.konto <= 0 or einst.risiko <= 0:
        p.error("--konto und --risiko müssen größer als 0 sein")
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
        # yfinance meldet z. B.: "['SE', 'HIMS']: ConnectionError('... 403 ...')"
        treffer = re.match(r"\s*\[(.*?)\]:\s*(.*)", record.getMessage(), re.S)
        if treffer:
            for ticker in re.findall(r"'([^']+)'", treffer.group(1)):
                self.gruende[ticker] = treffer.group(2)

def verstaendlicher_grund(text):
    t = (text or "").lower()
    if "too many requests" in t or "rate limit" in t:
        return "Yahoo-Limit erreicht – in 1–2 Minuten erneut starten"
    if any(k in t for k in ("connection", "timed out", "timeout", "resolve", "curl", "proxy")):
        return "keine Verbindung zu Yahoo"
    if "delisted" in t or "no price data" in t or "no data found" in t:
        return "keine Kursdaten (Ticker richtig geschrieben?)"
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

def lade_kurse(ticker_liste, debug=False):
    """Lädt alle Ticker in einem Rutsch (6 Monate Tageskerzen); leere Ticker werden einmal nachgeladen."""
    sammler = YahooFehler()
    yf_log = logging.getLogger("yfinance")
    alte_weitergabe = yf_log.propagate
    if not debug:
        yf_log.addHandler(sammler)
        yf_log.propagate = False
    daten, fehlend = {}, list(ticker_liste)
    try:
        for versuch in range(2):
            if not fehlend:
                break
            if versuch:
                time.sleep(3)
            roh = yf.download(fehlend, period="6mo", interval="1d", auto_adjust=True,
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
        yf_log.removeHandler(sammler)
        yf_log.propagate = alte_weitergabe
    gruende = {t: verstaendlicher_grund(sammler.gruende.get(t)) for t in fehlend}
    return daten, gruende

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
    """Berechnet alle notwendigen Indikatoren für die erweiterten Strategien."""
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

def positionsgroesse(kurs, stop, konto, risiko_prozent):
    """Stückzahl, bei der der Stop-Loss höchstens risiko_prozent des Kontos kostet
    (und die Position nicht größer als MAX_POSITION_PROZENT des Kontos wird)."""
    risiko_je_aktie = kurs - stop
    if risiko_je_aktie <= 0:
        return 0
    stueck = math.floor(konto * risiko_prozent / 100 / risiko_je_aktie)
    return min(stueck, math.floor(konto * MAX_POSITION_PROZENT / 100 / kurs))

def fehler_zeile(ticker, grund):
    return {"Ticker": ticker, "Signal": FEHLER, "_fehler": grund}

def evaluate_strategies(ticker, df, einst):
    try:
        offen = kerze_noch_offen(df)
        ignoriert = offen and einst.nur_schluss
        if ignoriert:
            df = df.iloc[:-1]
        if len(df) < MIN_KERZEN:
            return fehler_zeile(ticker, f"nur {len(df)} Kerzen – zu wenig Historie")

        df = calculate_indicators(df.copy())

        # Aktuellste Datenzeile extrahieren
        last = df.iloc[-1]
        price = float(last['Close'])
        vortag = float(df['Close'].iloc[-2])
        rsi = float(last['RSI'])
        ema = float(last['EMA_20'])
        lower_b = float(last['Lower_Band'])
        upper_b = float(last['Upper_Band'])
        atr = float(last['ATR'])

        if np.isnan([price, vortag, rsi, ema, lower_b, upper_b, atr]).any():
            return fehler_zeile(ticker, "Indikatoren unvollständig")

        # Standard-Werte für das Risikomanagement
        empfehlung = BEOBACHTEN
        stop_loss = np.nan
        take_profit = np.nan

        # --- STRATEGIE 1: EMA PULLBACK (Trendfolgend) ---
        if price > ema and (price / ema) < 1.015 and rsi < 60:
            empfehlung = KAUFEN
            stop_loss = price - (1.5 * atr)    # Stop 1,5 ATR unter dem Kurs
            take_profit = price + (3.0 * atr)  # Ziel 3 ATR über dem Kurs -> CRV (Chance-Risiko-Verhältnis) 2:1

        # --- STRATEGIE 2: RSI MEAN REVERSION (Antizyklisch) ---
        elif rsi < 32 or price <= lower_b:
            empfehlung = SCHARF_KAUFEN
            stop_loss = price - (1.2 * atr)
            take_profit = ema  # Kursziel ist die Rückkehr zum Mittelwert (EMA20)

        # --- STRATEGIE 3: GEWINNE SICHERN (Überhitzt) ---
        elif rsi > 70 or price >= upper_b:
            empfehlung = TEILVERKAUF
            stop_loss = price * 0.97  # Nachziehender Stopp zur Gewinnsicherung, kein Kursziel

        kauf = empfehlung in (SCHARF_KAUFEN, KAUFEN)
        if not stop_loss > 0:  # extrem volatil: Stop wäre bei 0 $ oder darunter
            stop_loss = np.nan
        crv = np.nan
        stueck = np.nan
        if kauf and stop_loss > 0:
            crv = (take_profit - price) / (price - stop_loss)
            stueck = positionsgroesse(price, stop_loss, einst.konto, einst.risiko)

        return {
            "Ticker": ticker,
            "Signal": empfehlung,
            "Kurs": price,
            "Tag %": (price / vortag - 1) * 100,
            "RSI": rsi,
            "Stop": stop_loss,
            "Ziel": take_profit,
            "CRV": crv,
            "Stück": stueck,
            "Einsatz $": stueck * price,
            "_stand": df.index[-1],
            "_offen": offen and not ignoriert,
            "_ignoriert": ignoriert,
        }

    except Exception as e:
        return fehler_zeile(ticker, f"Rechenfehler: {str(e)[:80]}")


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
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")  # schaltet ANSI-Farben in der Windows-Konsole ein
    return True

def kopfzeilen(zeilen, einst):
    ok = [z for z in zeilen if "_stand" in z]
    stand = max(z["_stand"] for z in ok)
    risiko_dollar = einst.konto * einst.risiko / 100
    titel = (f"📈 SWING-SCANNER · Daten bis {stand:%d.%m.%Y} · Konto {einst.konto:.0f} $ · "
             f"Risiko je Trade {einst.risiko:g} % = {risiko_dollar:.0f} $")
    anzahl = pd.Series([z["Signal"] for z in zeilen]).value_counts()
    zusammenfassung = " · ".join(f"{anzahl[s]}× {s}" for s in PRIORITAET if s in anzahl)
    hinweise = []
    if any(z["_offen"] for z in ok):
        hinweise.append("⏳ US-Börse noch offen: Die heutige Kerze ist nicht fertig, Signale können sich bis "
                        "Börsenschluss (16:00 New York) noch ändern. Mit --nur-schluss nur fertige Tage bewerten.")
    if any(z["_ignoriert"] for z in ok):
        hinweise.append("⏳ Laufende Tageskerze ignoriert (--nur-schluss): Kurs = letzter Schlusskurs.")
    for z in ok:
        if (stand - z["_stand"]).days > 5:
            hinweise.append(f"⚠️ {z['Ticker']}: letzte Kurse vom {z['_stand']:%d.%m.%Y} – veraltet?")
    return titel, zusammenfassung, hinweise

def fusszeilen(zeilen, einst):
    fuss = []
    fehler = {}
    for z in zeilen:
        if "_fehler" in z:
            fehler.setdefault(z["_fehler"], []).append(z["Ticker"])
    for grund, ticker in fehler.items():
        fuss.append(f"❌ {', '.join(ticker)}: {grund}")
    if fehler:
        fuss.append("")
    for signal, text in LEGENDE.items():
        fuss.append(f"{signal}: {text}")
    fuss.append(f"Stück = so viele Aktien, dass du am Stop höchstens {einst.risiko:g} % des Kontos verlierst "
                f"(max. {MAX_POSITION_PROZENT} % des Kontos je Position). CRV = Chance ÷ Risiko.")
    fuss.append("💡 Kurs = letzter Kurs; der echte Kaufkurs am nächsten Tag weicht ab – Stückzahl dann neu "
                "rechnen. Keine Anlageberatung.")
    return fuss

def zeige_als_text(tabelle, titel, zusammenfassung, hinweise, fuss):
    formatierer = {s: f.format for s, f in FORMATE.items()}
    # east_asian_width: Emojis zählen als 2 Zeichen breit, damit die Spalten bündig bleiben
    with pd.option_context("display.unicode.east_asian_width", True):
        text = tabelle.to_string(index=False, formatters=formatierer, na_rep="–")
    zeilen = text.splitlines()
    linie = "=" * len(zeilen[0])
    farbig = farben_im_terminal()

    print(f"\n{titel}\n   {zusammenfassung}")
    for h in hinweise:
        print(h)
    print(linie)
    print(zeilen[0])
    for zeile, signal in zip(zeilen[1:], tabelle["Signal"]):
        code = ANSI.get(signal) if farbig else None
        print(f"{code}{zeile}\033[0m" if code else zeile)
    print(linie)
    for f in fuss:
        print(f)

def zeige_im_notebook(tabelle, titel, zusammenfassung, hinweise, fuss):
    from IPython.display import HTML, display

    def zeilenfarbe(zeile):
        bg, fg = FARBEN.get(zeile["Signal"], (None, None))
        return [f"background-color: {bg}; color: {fg}" if bg else ""] * len(zeile)

    try:
        tabelle_html = (tabelle.style
                        .apply(zeilenfarbe, axis=1)
                        .format(FORMATE, na_rep="–")
                        .hide(axis="index")
                        .set_table_styles([
                            {"selector": "th", "props": "padding: 4px 10px; text-align: center;"},
                            {"selector": "td", "props": "padding: 4px 10px; text-align: right;"},
                            {"selector": "td.col0, td.col1", "props": "text-align: left; font-weight: bold;"},
                        ])
                        .to_html())
    except (ImportError, AttributeError):  # ohne jinja2 gibt es keinen Styler -> schlichte Tabelle
        tabelle_html = tabelle.to_html(index=False, na_rep="–")

    def absatz(text, stil=""):
        return f'<p style="margin: 2px 0; {stil}">{html.escape(text)}</p>' if text else "<br>"

    kopf = absatz(titel, "font-size: 1.15em; font-weight: bold;") + absatz(zusammenfassung)
    kopf += "".join(absatz(h, "color: #b26a00;") for h in hinweise)
    fuss_html = "".join(absatz(f, "font-size: 0.9em; opacity: 0.8;") for f in fuss)
    display(HTML(kopf + '<div style="margin: 8px 0;">' + tabelle_html + "</div>" + fuss_html))

def speichere_csv(tabelle, datei):
    # Semikolon + Dezimalkomma, damit ein deutsches Excel die Datei direkt richtig öffnet
    tabelle.to_csv(datei, index=False, sep=";", decimal=",", encoding="utf-8-sig", float_format="%.2f")
    print(f"💾 Gespeichert: {os.path.abspath(datei)}")


def main():
    try:
        sys.stdout.reconfigure(errors="replace")  # Emojis -> '?' statt Absturz, wenn Windows in eine Datei umleitet
    except Exception:
        pass

    einst = lies_einstellungen()
    if not einst.ticker_liste:
        print("Keine Ticker angegeben.")
        return None

    print(f"🤖 Lade Kurse für {len(einst.ticker_liste)} Ticker und prüfe die Swing-Trading-Strategien ...")
    daten, gruende = lade_kurse(einst.ticker_liste, einst.debug)
    zeilen = [evaluate_strategies(t, daten[t], einst) if t in daten else fehler_zeile(t, gruende[t])
              for t in einst.ticker_liste]

    if not any("_stand" in z for z in zeilen):
        print("\n❌ Für keinen Ticker konnten Kursdaten ausgewertet werden.")
        for f in fusszeilen(zeilen, einst):
            if f.startswith("❌"):
                print(f)
        print("Internetverbindung prüfen oder in 1–2 Minuten erneut starten.")
        return None

    # Sortieren: wichtigste Signale oben, innerhalb eines Signals das beste CRV zuerst, Fehler ganz unten
    tabelle = pd.DataFrame(zeilen).reindex(columns=SPALTEN + ["_fehler"])
    tabelle["_prio"] = tabelle["Signal"].map(PRIORITAET)
    tabelle = tabelle.sort_values(["_prio", "CRV"], ascending=[True, False], na_position="last", kind="stable")
    tabelle = tabelle[SPALTEN].reset_index(drop=True)

    titel, zusammenfassung, hinweise = kopfzeilen(zeilen, einst)
    fuss = fusszeilen(zeilen, einst)
    if im_notebook():
        zeige_im_notebook(tabelle, titel, zusammenfassung, hinweise, fuss)
    else:
        zeige_als_text(tabelle, titel, zusammenfassung, hinweise, fuss)

    if einst.csv:
        speichere_csv(tabelle, einst.csv)
    return tabelle

if __name__ == "__main__":
    # Unter %run in Colab/Jupyter steht die Tabelle danach als 'ergebnis' zur Verfügung
    ergebnis = main()
