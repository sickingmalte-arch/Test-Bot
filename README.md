# Automatisches Trading-System

## Streamlit-Dashboard starten

In PowerShell im Projektordner ausführen:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

Das Dashboard lädt abgeschlossene öffentliche Spot-Kerzen von der Binance-API (Standard: BTCUSDT, 5 Minuten) und aktualisiert die Ansicht automatisch. Das SMA-System simuliert Trades lokal mit Paper-Kapital. Es werden keine echten Orders gesendet und es werden keine API-Schlüssel benötigt.

Die ersten bis zu 200 abgeschlossenen Kerzen werden beim Start verarbeitet. Das ist eine Paper-Simulation mit den jüngsten Kursdaten, kein echter Live-Orderverlauf. Gebühren, Slippage und Ausführung sind vereinfachte Modellannahmen.

Für echte Orders muss zuerst eine konkrete Börse, ein Handelspaar und ein sicherer API-Zugang festgelegt werden. Die Orderübermittlung ist in diesem Projekt absichtlich nicht implementiert.

## Offline-Konsolendemonstration

```powershell
py -3 Automatisches_trading_system.py --candles 180
```

## Swing-Scanner für die Aktien-Watchlist

```powershell
python -m pip install -r requirements.txt
python swing_scanner.py
```

Lädt sechs Monate Tageskerzen von Yahoo Finance (über `yfinance`) für die Ticker in `TICKER_LISTE` und berechnet RSI (14, Wilder), EMA 20, Bollinger-Bänder (20, 2σ) und ATR (14, Wilder). Daraus werden drei Setups geprüft (EMA-20-Pullback, RSI/Band-Überdehnung, überhitzter Markt) und mit Stop-Loss/Take-Profit als Tabelle ausgegeben. Die letzte Kerze ist während der Handelszeit noch nicht abgeschlossen. Es werden keine Orders gesendet; die Ausgabe ist keine Anlageberatung.
