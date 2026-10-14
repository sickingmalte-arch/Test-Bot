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

Mit Papier-Depot (Vorwärtstest mit virtuellem Geld, Stand in deinem Google Drive) – Colab fragt beim ersten Mal nach der Erlaubnis für Drive. Am besten jeden Börsentag einmal abends starten:

```
!pip install -q -U yfinance
!wget -q -O swing_scanner.py https://raw.githubusercontent.com/sickingmalte-arch/Test-Bot/claude/new-session-hbq1tg/swing_scanner.py
%run swing_scanner.py --konto 10000 --risiko 1 --papier
```

### Lokal (PowerShell)

```powershell
python -m pip install -U yfinance pandas numpy
python swing_scanner.py
```

### Was das Skript zeigt

1. **Scanner (heute):** je Ticker 🟢 KAUFEN, 🔴 SHORT, ⏸ WARTEN (mit Grund), ⚠️ GEWINNE SICHERN, BEOBACHTEN oder ❌ FEHLER – mit Strategie, Kurs, Limit (höchster Kaufkurs), Stop, Ziel, Chance-Risiko-Verhältnis (CRV), Stückzahl, Einsatz, Risiko in €, nächstem Quartalszahlen-Termin und erkannten Ereignissen aus den Schlagzeilen. Für die besten Signale steht darunter ein Handelsplan in einem Satz (wann, wie viel, bis zu welchem Kurs, Stop, Ziel, spätestens raus am …) – nach denselben Grenzen wie im Depot: höchstens 5 Positionen, davon 2 Short, zusammen höchstens 5 % Risiko und nicht mehr Geld als auf dem Konto. Alle Beträge in Euro.
2. **Strategie-Tagebuch („Lernen“):** Jede der 16 Strategien handelt im Hintergrund gedanklich mit. Läuft eine Strategie über ihre letzten bis zu 60 Trades im Schnitt deutlich schlecht (unter −0,1 R ab 20 Trades), wird sie pausiert, bis sie wieder im Plus ist. Die Tabelle zeigt ehrlich, wie groß der Zufall dabei sein kann.
3. **Papier-Depot (Vorwärtstest, mit `--papier`):** Der Bot handelt ab dem ersten Lauf vorwärts mit virtuellem Geld nach genau denselben Regeln und speichert den Stand – in Colab in Google Drive (`MyDrive/swing_scanner/papier_depot.json`), sonst in `papier_depot.json`. Jeder Lauf rechnet die neuen fertigen Kurstage seit dem letzten Lauf: Aufträge vom Vorabend zur Eröffnung (nur bis zum Limit), Stop, Ziel, Quartalszahlen, Zeitstopp, neue Signale zum Schluss. Verpasste Tage holt er nach, jede Entscheidung nutzt nur Kurse, die es da schon gab. Aktiensplits und Dividenden (Yahoo rechnet alte Kurse um) werden erkannt und verrechnet. Das ist der ehrliche Test: Anders als der Rückblick kennt das Papier-Depot die Zukunft nicht.
4. **Virtuelles Depot (Rückblick):** Der Bot handelt die letzten Monate mit dem Startkapital nach seinen Signalen – einmal mit und einmal ohne Lernen – im Vergleich zu „alle Ticker kaufen und halten“. Es wird kein echtes Geld bewegt.

### Strategien und Regeln

- 16 Strategien, je 8 für steigende und fallende Kurse: Ausbruch/Abbruch (20-Tage-Hoch/-Tief mit Volumen), RSI-2-Rücksetzer/-Übertreibung, Gegenbewegung/Rückfall (überverkauft/überhitzt), MACD-Wende, Rücksetzer/Erholung an der EMA 20, dazu Trendfolge und Volatilität: Squeeze-Ausbruch/-Abbruch (Bollinger-Bänder erst sehr eng, dann Ausbruch), EMA-Kreuz (EMA 9 kreuzt EMA 21) und ATR-Ausbruch/-Abbruch (Schluss mehr als 2 ATR von der EMA 20, Keltner-Kanal).
- Watchlist (`TICKER_LISTE` im Skript): SE, HIMS, NOW, INTU, CRWV, NBIS, MELI, IREN, NFLX, AAPL, ASTS, SOFI sowie NVDA, MSFT, AMZN, META, GOOGL, TSLA, AMD, PLTR, JPM, LLY, XOM, COST – keine Empfehlung, nur liquide Werte aus mehreren Branchen. Eigene Liste mit `--ticker`.
- Trendregel: Trendstrategien nur in Richtung der 50-Tage-Linie, Gegenbewegungen nur in Richtung der 200-Tage-Linie; widersprechen sich Signale, wartet der Bot.
- Quartalszahlen: kein Einstieg in den 3 Handelstagen davor, offene Positionen am Abend vorher schließen, kurz danach keine Gegenbewegungs-Trades.
- Einstieg am nächsten Handelstag nur bis zum Limit; Ausstieg an Stop, Ziel, vor Quartalszahlen oder spätestens nach 20 Handelstagen.
- Risiko: 1 % des Kontos je Trade, höchstens 5 Positionen (davon 2 Short) und 5 % Risiko gleichzeitig, höchstens 25 % des Kontos je Position. Kosten: 1 € Gebühr + 0,1 % Spread je Order.
- Schlagzeilen sind nur ein Hinweis (⚠️, wenn ein erkanntes Ereignis gegen das Signal spricht) – sie lassen sich nicht rückwirkend testen.

### Optionen

| Option | Bedeutung |
| --- | --- |
| `--ticker "AAPL, NFLX, SOFI"` | eigene Ticker-Liste statt `TICKER_LISTE` im Skript (US-Werte und Euro-Börsen wie `SAP.DE`) |
| `--konto 10000` | Kontogröße bzw. virtuelles Startkapital in € |
| `--risiko 1` | max. Verlust pro Trade in % des Kontos, wenn der Stop greift (auch `1,5`) |
| `--ohne-short` | nur auf steigende Kurse setzen |
| `--ohne-lernen` | keine Strategien pausieren |
| `--ohne-news` | keine Schlagzeilen laden (Quartalszahlen-Regel bleibt) |
| `--ohne-zahlen` | keine Quartalszahlen-Termine laden – die Zahlen-Regel ist dann aus |
| `--rueckblick 6` | Monate für das virtuelle Depot (0 = aus, max. 18) |
| `--gebuehr 1` | Ordergebühr in € je Kauf/Verkauf |
| `--bruchstuecke` | auch Bruchteile von Aktien handeln |
| `--nur-schluss` | laufende Tageskerze ignorieren, nur abgeschlossene Tage bewerten |
| `--papier` | Papier-Depot fortschreiben (Vorwärtstest mit virtuellem Geld, Stand wird gespeichert); eigene Datei mit `--papier meine_datei.json` |
| `--papier-neu` | Papier-Depot neu anfangen (der bisherige Stand bleibt als Kopie mit Datum erhalten) |
| `--csv signale.csv` | Scanner-Tabelle als CSV für Excel speichern, alle Depot-Trades in `signale_trades.csv` |
| `--debug` | Original-Meldungen von yfinance anzeigen |

Die festen Regeln (Positionsgrenzen, Lernregel, Zeitstopp …) stehen als Konstanten oben im Skript. Sie sind bewusst vorab festgelegt: Wer sie so lange verstellt, bis der Rückblick gut aussieht, passt sie nur an den Zufall der Vergangenheit an.

Daten: 5 Jahre Tageskerzen, Quartalszahlen-Termine und Schlagzeilen von Yahoo Finance. Short-Positionen (z. B. per CFD oder Turbo-Schein) haben nach oben offene Verluste; Leih- und Finanzierungskosten sind im Rückblick nicht berücksichtigt. Der Rückblick nutzt die heutige Watchlist und sieht deshalb für Kauf-Strategien tendenziell zu gut aus. Vergangene Ergebnisse sind keine Garantie für die Zukunft; die Ausgabe ist keine Anlageberatung.
