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

### In Google Colab (ohne Installation)

Neue Zelle anlegen, einfügen und mit Umschalt + Enter ausführen:

```
!pip install -q -U yfinance
!wget -q -O swing_scanner.py https://raw.githubusercontent.com/sickingmalte-arch/Test-Bot/claude/new-session-hbq1tg/swing_scanner.py
%run swing_scanner.py --konto 10000 --risiko 1
```

Mit `%run` erscheint eine farbige Tabelle; mit `!python swing_scanner.py` die Textversion.

### Lokal (PowerShell)

```powershell
python -m pip install -U yfinance pandas numpy
python swing_scanner.py
```

### Optionen

| Option | Bedeutung |
| --- | --- |
| `--ticker "AAPL, NFLX, SOFI"` | eigene Ticker-Liste statt `TICKER_LISTE` im Skript |
| `--konto 10000` | Kontogröße in $ für die Spalten „Stück“ und „Einsatz $“ |
| `--risiko 1` | max. Verlust pro Trade in % des Kontos, wenn der Stop greift (auch `1,5`) |
| `--nur-schluss` | laufende Tageskerze ignorieren, nur abgeschlossene Tage bewerten |
| `--csv signale.csv` | Ergebnis zusätzlich als CSV für Excel speichern |
| `--debug` | Original-Meldungen von yfinance anzeigen |

Lädt sechs Monate Tageskerzen von Yahoo Finance (über `yfinance`) und berechnet RSI (14, Wilder), EMA 20, Bollinger-Bänder (20, 2σ) und ATR (14, Wilder). Daraus werden drei Setups geprüft (EMA-20-Pullback, RSI/Band-Überdehnung, überhitzter Markt). Die Tabelle zeigt je Ticker Signal, Kurs, Tagesänderung, RSI, Stop, Ziel, Chance-Risiko-Verhältnis (CRV) und die Positionsgröße, bei der ein Stop höchstens `--risiko` % des Kontos kostet (max. 25 % des Kontos je Position). Während der US-Handelszeit ist die letzte Kerze noch nicht abgeschlossen; die Kopfzeile weist darauf hin. Es werden keine Orders gesendet; die Ausgabe ist keine Anlageberatung.
