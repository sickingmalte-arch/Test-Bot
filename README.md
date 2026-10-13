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

Mit `%run` erscheinen farbige Tabellen und ein Diagramm; mit `!python swing_scanner.py` die Textversion.

### Lokal (PowerShell)

```powershell
python -m pip install -U yfinance pandas numpy
python swing_scanner.py
```

### Was das Skript zeigt

1. **Scanner (heute):** je Ticker ein Signal – 🚀 SCHARF KAUFEN, ⭐ KAUFEN, 🔥 SCHARF SHORT, 🔻 SHORT oder BEOBACHTEN – mit Kurs, Tagesänderung, RSI, Stop, Ziel, Chance-Risiko-Verhältnis (CRV) und der Positionsgröße, bei der ein Stop höchstens `--risiko` % des Kontos kostet (max. 25 % des Kontos je Position). Alle Beträge in Euro (US-Kurse zum aktuellen EUR/USD-Kurs umgerechnet).
2. **Virtuelles Depot (Rückblick):** Der Bot handelt die letzten Monate mit dem Startkapital nach seinen eigenen Signalen – Long und Short – und zeigt Depotwert, Trades, Gewinnquote, größten Rückgang und den Vergleich mit „alle Ticker kaufen und halten“. Einstieg jeweils zur Eröffnung am Tag nach dem Signal, Ausstieg an Stop oder Ziel, 1 € Gebühr je Order. Es wird kein echtes Geld bewegt.

### Optionen

| Option | Bedeutung |
| --- | --- |
| `--ticker "AAPL, NFLX, SOFI"` | eigene Ticker-Liste statt `TICKER_LISTE` im Skript |
| `--konto 10000` | Kontogröße bzw. virtuelles Startkapital in € |
| `--risiko 1` | max. Verlust pro Trade in % des Kontos, wenn der Stop greift (auch `1,5`) |
| `--ohne-short` | nur auf steigende Kurse setzen (statt 🔥 SCHARF SHORT erscheint ⚠️ TEILVERKAUF) |
| `--rueckblick 6` | Monate für das virtuelle Depot (0 = aus, max. 18) |
| `--gebuehr 1` | Ordergebühr in € je Kauf/Verkauf |
| `--bruchstuecke` | auch Bruchteile von Aktien handeln |
| `--nur-schluss` | laufende Tageskerze ignorieren, nur abgeschlossene Tage bewerten |
| `--csv signale.csv` | Scanner-Tabelle als CSV für Excel speichern, alle Depot-Trades in `signale_trades.csv` |
| `--debug` | Original-Meldungen von yfinance anzeigen |

Indikatoren: RSI (14, Wilder), EMA 20, Bollinger-Bänder (20, 2σ), ATR (14, Wilder) aus einem Jahr Tageskerzen von Yahoo Finance. Short-Positionen (z. B. per CFD oder Turbo-Schein) haben nach oben offene Verluste; Leih- und Finanzierungskosten sind im Rückblick nicht berücksichtigt. Vergangene Ergebnisse sind keine Garantie für die Zukunft; die Ausgabe ist keine Anlageberatung.
