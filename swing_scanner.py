import yfinance as yf
import pandas as pd
import numpy as np

# Ticker-Liste aus deiner Watchlist
TICKER_LISTE = [
    "SE", "HIMS", "NOW", "INTU", "CRWV", "NBIS",
    "MELI", "IREN", "NFLX", "AAPL", "ASTS", "SOFI"
]

# Mindestanzahl an Tageskerzen, damit RSI/EMA/Bollinger/ATR aussagekräftig sind
MIN_KERZEN = 30

SPALTEN = ["Ticker", "Kurs ($)", "Beste Strategie", "Signal", "Einstieg ($)", "Stop-Loss ($)", "Take-Profit ($)", "RSI"]

def fehler_zeile(ticker, grund):
    return {"Ticker": ticker, "Kurs ($)": 0, "Beste Strategie": "-", "Signal": f"Fehler: {grund}", "Einstieg ($)": "-", "Stop-Loss ($)": "-", "Take-Profit ($)": "-", "RSI": 0}

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

def evaluate_strategies(ticker):
    try:
        # Lade Daten (6 Monate für stabile Indikatoren-Berechnung)
        df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=True, progress=False)
        if df.empty:
            return fehler_zeile(ticker, "keine Kursdaten")

        # Neuere yfinance-Versionen liefern auch für einen einzelnen Ticker
        # zweistufige Spalten ('Close', 'AAPL') – auf 'Close' usw. reduzieren
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(subset=['High', 'Low', 'Close'])
        if len(df) < MIN_KERZEN:
            return fehler_zeile(ticker, f"nur {len(df)} Kerzen")

        df = calculate_indicators(df)

        # Aktuellste Datenzeile extrahieren
        last = df.iloc[-1]
        price = float(last['Close'])
        rsi = float(last['RSI'])
        ema = float(last['EMA_20'])
        lower_b = float(last['Lower_Band'])
        upper_b = float(last['Upper_Band'])
        atr = float(last['ATR'])

        if np.isnan([price, rsi, ema, lower_b, upper_b, atr]).any():
            return fehler_zeile(ticker, "Indikatoren unvollständig")

        # Standard-Werte für das Risikomanagement
        empfehlung = "BEOBACHTEN"
        strategie_name = "Kein klares Setup"
        stop_loss = 0.0
        take_profit = 0.0

        # --- STRATEGIE 1: EMA PULLBACK (Trendfolgend) ---
        if price > ema and (price / ema) < 1.015 and rsi < 60:
            empfehlung = "⭐ KAUFEN"
            strategie_name = "EMA 20 Pullback"
            # Stop-Loss knapp unter den EMA legen (1.5x ATR Puffer)
            stop_loss = price - (1.5 * atr)
            # Take-Profit am letzten lokalen Hoch / Widerstand simulieren
            take_profit = price + (3.0 * atr)  # CRV (Chance-Risiko-Verhältnis) von 2:1

        # --- STRATEGIE 2: RSI MEAN REVERSION (Antizyklisch) ---
        elif rsi < 32 or price <= lower_b:
            empfehlung = "🚀 SCHARF KAUFEN"
            strategie_name = "RSI / Band Overextended"
            stop_loss = price - (1.2 * atr)
            take_profit = ema  # Kursziel ist die Rückkehr zum Mittelwert (EMA20)

        # --- STRATEGIE 3: GEWINNE SICHERN / SHORT (Überhitzt) ---
        elif rsi > 70 or price >= upper_b:
            empfehlung = "⚠️ TEILVERKAUF"
            strategie_name = "Markt überhitzt"
            stop_loss = price * 0.97  # Nachziehender Stopp zur Gewinnsicherung
            take_profit = price

        return {
            "Ticker": ticker,
            "Kurs ($)": round(price, 2),
            "Beste Strategie": strategie_name,
            "Signal": empfehlung,
            "Einstieg ($)": round(price, 2) if "KAUFEN" in empfehlung else "Warten",
            "Stop-Loss ($)": round(stop_loss, 2) if stop_loss > 0 else "-",
            "Take-Profit ($)": round(take_profit, 2) if take_profit > 0 else "-",
            "RSI": round(rsi, 1)
        }

    except Exception as e:
        return fehler_zeile(ticker, str(e))

def main():
    print("🤖 Analysiere professionelle Swing-Trading-Strategien...")
    results = []

    for ticker in TICKER_LISTE:
        analysis = evaluate_strategies(ticker)
        if analysis:
            results.append(analysis)

    df_results = pd.DataFrame(results, columns=SPALTEN)

    # Sortieren, damit die wichtigsten Kaufsignale ganz oben stehen (Fehler ganz unten)
    df_results['Priorität'] = df_results['Signal'].map({"🚀 SCHARF KAUFEN": 1, "⭐ KAUFEN": 2, "BEOBACHTEN": 3, "⚠️ TEILVERKAUF": 4}).fillna(5)
    df_results = df_results.sort_values(by='Priorität', kind='stable').drop(columns=['Priorität'])

    print("\n" + "="*95)
    print("📈 MULTI-STRATEGIE DASHBOARD FÜR DEINE WATCHLIST")
    print("="*95)
    print(df_results.to_string(index=False))
    print("="*95)
    if df_results['Signal'].str.startswith("Fehler").all():
        print("\n❌ Für keinen Ticker konnten Kursdaten geladen werden. Internetverbindung / Yahoo Finance prüfen.")
    print("\n💡 TIPP: Nutze den berechneten Stop-Loss (SL), um dein Risiko pro Trade strikt auf max. 1-2% deines Kontos zu begrenzen.")

if __name__ == "__main__":
    main()
