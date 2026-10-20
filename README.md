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

Mit Papier-Depot (Vorwärtstest mit virtuellem Geld, Stand in deinem Google Drive) – Colab fragt beim ersten Mal nach der Erlaubnis für Drive. Am besten jeden Börsentag einmal abends nach 22:15 Uhr starten (dann ist der US-Handelstag fertig; mit Krypto auf der Liste zählt ein Tag erst nach 2:00 Uhr). `--papier-neu` nur einmal zum Neuanfangen anhängen und danach wieder weglassen:

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

### Automatisch jeden Abend (GitHub Actions – ohne PC, ohne Colab)

Der Ablauf `.github/workflows/swing-bot.yml` startet den Bot jeden Börsentag (Mo–Fr) um 22:30 Uhr UTC – also 0:30 Uhr deutscher Sommerzeit bzw. 23:30 Uhr Winterzeit, nach US-Börsenschluss – kostenlos in der Cloud bei GitHub. Du musst keine Seite offen lassen und nichts neu laden.

1. **Einmalig:** Die Änderungen müssen im Hauptzweig `main` sein (Pull Request → „Merge“). Zeitgesteuerte Abläufe laufen bei GitHub nur aus `main`.
2. **Ergebnis ansehen:** Im Repository die Datei [`bericht/README.md`](bericht/README.md) öffnen (auch in der GitHub-App: Code → `bericht` → `README.md`). Dort stehen Signale, Handelsplan, Lernstand, Papier-Depot und Rückblick; ein Klick auf einen Ticker öffnet den Chart bei TradingView. Jeder Lauf zeigt den Bericht außerdem unter **Actions → Swing-Bot → Lauf anklicken** (Zusammenfassung).
3. **Papier-Depot:** liegt in `papier/papier_depot.json` und wird nach jedem Lauf gespeichert. Der Bot holt verpasste Tage nach, falls GitHub einen Lauf auslässt oder Yahoo einmal nicht antwortet. Willst du dein bisheriges Depot aus Google Drive weiterführen: `MyDrive/swing_scanner/papier_depot.json` herunterladen und im Repository über **Add file → Upload files** in den Ordner `papier` hochladen (vor dem nächsten Lauf). Achtung: Drive-Depot und GitHub-Depot sind danach zwei getrennte Dateien – wenn du beide fortschreibst, laufen sie auseinander.
4. **Sofort testen:** **Actions → Swing-Bot → Run workflow**. Ein Lauf dauert einige Minuten.
5. **Einstellungen ohne Code:** **Settings → Secrets and variables → Actions → Tab „Variables“ → New repository variable**:

| Name | Beispiel | Bedeutung |
| --- | --- | --- |
| `KONTO` | `10000` | Kontogröße / Startkapital in € (Standard 10000) |
| `RISIKO` | `1` | Risiko je Trade in % (Standard 1) |
| `TICKER` | `AAPL, NFLX, SOFI` | eigene Watchlist (leer = Liste im Skript) |
| `OPTIONEN` | `--ohne-short` | weitere Optionen aus der Tabelle unten, mit Leerzeichen getrennt |

Zum Neuanfang des Papier-Depots einfach `papier/papier_depot.json` im Repository löschen (die Historie bei GitHub behält den alten Stand) – `--papier-neu` bitte nicht als `OPTIONEN` eintragen, sonst fängt das Depot jeden Abend neu an.

Gut zu wissen: GitHub startet zeitgesteuerte Läufe oft einige Minuten später und lässt bei hoher Last selten einen aus. Yahoo begrenzt manchmal Abfragen von Cloud-Servern – dann steht ❌ im Bericht, das Papier-Depot bleibt unverändert und der nächste Lauf holt alles nach. Schaltet GitHub den Ablauf doch einmal ab (Hinweis im Tab Actions), dort „Enable workflow“ klicken. Neue Versionen des Skripts nutzt der automatische Lauf erst, wenn sie in `main` übernommen sind.

### TradingView: Signale direkt im Chart

Die Datei [`tradingview/swing_bot_signale.pine`](tradingview/swing_bot_signale.pine) ist ein Indikator für TradingView (auch im kostenlosen Tarif). Er zeigt im Tageschart jeder Aktie, was der Bot kaufen würde und was nicht – zum Vergleich mit deinen eigenen Linien und Indikatoren:

- **▲ grün = KAUFEN, ▼ rot = SHORT** mit Namen der Strategie; Maus darüber (am Handy antippen) zeigt Limit, Stop, Ziel und CRV.
- **Jeder Trade wie mit dem Positions-Werkzeug von TradingView:** grüne Zielzone, rote Stop-Zone, graue Einstiegslinie vom Einstieg bis zum Ausstieg, dort das Ergebnis (✅ Ziel, ❌ Stop, ⏱ Zeitstopp nach 20 Tagen) in R – 1 R ist der geplante Verlust bis zum Stop, also bei 1 % Risiko und 10.000 € rund 100 €. Gerechnet wird wie im Papier-Depot des Bots: Einstieg am nächsten Handelstag zur Eröffnung nur bis zum Limit, Stop vor Ziel, nach Spread und Gebühren.
- **Grau = der Bot handelt nicht**, mit Grund beim Antippen: ⏸ Marktfilter, Long- und Short-Signal zugleich oder Strategie ausgeschaltet; ✕ Auftrag verfallen, weil die Eröffnung über dem Limit lag.
- **Auftrag für den nächsten Handelstag:** gestrichelte Linien rechts neben der letzten Kerze (Kauf-Limit, Stop, Ziel).
- **Infotafel oben rechts:** heutige Entscheidung wie in der Tabelle des Bots (KAUFEN, SHORT, WARTEN mit Grund, GEWINNE SICHERN oder BEOBACHTEN), offene Position mit Tag x/20, Marktlage und die Bilanz der Trades im Chart (Anzahl, Trefferquote, Summe in R und ≈ €).
- Roter Hintergrund = Abwärtsmarkt (Nasdaq-100 unter seiner 200-Tage-Linie). Auf Wunsch zeichnet er auch EMA 20, SMA 50 und SMA 200, die der Bot benutzt.

1. Die Datei auf GitHub öffnen und mit dem Kopieren-Knopf („Copy raw file“) kopieren.
2. Bei TradingView einen Chart öffnen, unten **Pine-Editor** anklicken, den Inhalt komplett ersetzen und **Zum Chart hinzufügen** klicken (danach **Speichern**, dann findest du ihn unter „Indikatoren → Meine Skripte“ für jeden Chart).
3. Tageschart (**1D**) wählen und unten rechts am Chart **ADJ** einschalten (Kurse für Dividenden bereinigen). Der Bot rechnet wie Yahoo mit dividendenbereinigten Kursen – ohne ADJ weichen die Signale bei Dividendenwerten wie XOM, JPM oder COST oft ab; der Indikator zeigt dann oben rechts einen roten Hinweis. Signale gelten zum Tagesschluss – wie beim Bot: Einstieg am nächsten Handelstag nur bis zum Limit.
4. Zahnrad am Indikator: Short-Signale, Marktfilter, Trades, graue Signale, Infotafel, Konto, Risiko und jede Strategie einzeln an/aus. Strategien, die im Bericht des Bots „aus“ oder „pausiert“ sind, hier abschalten. Wird es dir am Handy zu voll: graue Signale oder Infotafel ausschalten.
5. Benachrichtigung aufs Handy: Rechtsklick im Chart → **Alarm hinzufügen** → Bedingung „Swing-Bot“ → „Swing-Bot: KAUFEN-Signal“ oder „SHORT-Signal“ → „Einmal pro Balkenschluss“.

Der Indikator kennt nur den einen Chart: Lernregel über die ganze Watchlist, Quartalszahlen-Regel, Schlagzeilen und die Grenzen für Positionen und Risiko gibt es nur im Bot. Die Trades im Chart sind deshalb die eines Depots, das nur diese eine Aktie handelt – ihre Bilanz ist ein Vergleich, keine Vorhersage. Kurse stehen in der Währung des Charts (meist $), nicht in €. In den ersten Monaten eines Charts können Signale durch andere Startwerte der Indikatoren abweichen – maßgeblich ist der Bericht des Bots. TradingView handelt damit nicht automatisch; der Bot handelt nur virtuell.

### Was das Skript zeigt

1. **Scanner (heute):** je Ticker 🟢 KAUFEN, 🔴 SHORT, ⏸ WARTEN (mit Grund), ⚠️ GEWINNE SICHERN, BEOBACHTEN oder ❌ FEHLER – mit Strategie, Kurs, Limit (höchster Kaufkurs), Stop, Ziel, Chance-Risiko-Verhältnis (CRV), Stückzahl, Einsatz, Risiko in €, nächstem Quartalszahlen-Termin und erkannten Ereignissen aus den Schlagzeilen. Für die besten Signale steht darunter ein Handelsplan in einem Satz (wann, wie viel, bis zu welchem Kurs, Stop, Ziel, spätestens raus am …) – nach denselben Grenzen wie im Depot: höchstens 5 Positionen, davon 2 Short, zusammen höchstens 5 % Risiko und nicht mehr Geld als auf dem Konto. Alle Beträge in Euro.
2. **Strategie-Tagebuch („Lernen“):** Jede der 16 Strategien handelt im Hintergrund gedanklich mit. Läuft eine Strategie über ihre letzten bis zu 60 Trades im Schnitt deutlich schlecht (unter −0,1 R ab 20 Trades), wird sie pausiert, bis sie wieder im Plus ist. Hat sie über ihre ganze Geschichte (ab 50 Trades) nach Kosten Geld verloren, handelt der Bot sie gar nicht. Die Tabelle zeigt ehrlich, wie groß der Zufall dabei sein kann.
3. **Papier-Depot (Vorwärtstest, mit `--papier`):** Der Bot handelt ab dem ersten Lauf vorwärts mit virtuellem Geld nach genau denselben Regeln und speichert den Stand – in Colab in Google Drive (`MyDrive/swing_scanner/papier_depot.json`), sonst in `papier_depot.json`. Jeder Lauf rechnet die neuen Kurstage seit dem letzten Lauf, sobald sie für alle Werte der Liste fertig sind: Aufträge vom Vorabend zur Eröffnung (nur bis zum Limit), Stop, Ziel, Quartalszahlen, Zeitstopp, neue Signale zum Schluss. Verpasste Tage holt er nach, jede Entscheidung nutzt nur Kurse, die es da schon gab. Aktiensplits und Dividenden (Yahoo rechnet alte Kurse um) werden erkannt und verrechnet. Das ist der ehrliche Test: Anders als der Rückblick kennt das Papier-Depot die Zukunft nicht.
4. **Virtuelles Depot (Rückblick):** Der Bot handelt die letzten Monate mit dem Startkapital nach seinen Signalen – einmal mit und einmal ohne Lernen – im Vergleich zu „alle Ticker kaufen und halten“. Es wird kein echtes Geld bewegt.

### Strategien und Regeln

- 16 Strategien, je 8 für steigende und fallende Kurse: Ausbruch/Abbruch (20-Tage-Hoch/-Tief mit Volumen), RSI-2-Rücksetzer/-Übertreibung, Gegenbewegung/Rückfall (überverkauft/überhitzt), MACD-Wende, Rücksetzer/Erholung an der EMA 20, dazu Trendfolge und Volatilität: Squeeze-Ausbruch/-Abbruch (Bollinger-Bänder erst sehr eng, dann Ausbruch), EMA-Kreuz (EMA 9 kreuzt EMA 21) und ATR-Ausbruch/-Abbruch (Schluss mehr als 2 ATR von der EMA 20, Keltner-Kanal).
- Watchlist (`TICKER_LISTE` im Skript): SE, HIMS, NOW, INTU, CRWV, NBIS, MELI, IREN, NFLX, AAPL, ASTS, SOFI sowie NVDA, MSFT, AMZN, META, GOOGL, TSLA, AMD, PLTR, JPM, LLY, XOM, COST – keine Empfehlung, nur liquide Werte aus mehreren Branchen. Eigene Liste mit `--ticker`.
- Marktfilter: Long nur, wenn der Nasdaq-100 (QQQ) am Vortag über seiner 200-Tage-Linie schloss, Short nur darunter – die meisten Aktien laufen mit dem Gesamtmarkt. Der Rückblick zeigt zum Vergleich, wie es mit deinen Kursen ohne Marktfilter gelaufen wäre (`--ohne-marktfilter` schaltet ihn ab).
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
| `--ohne-marktfilter` | Long und Short unabhängig davon, ob der Nasdaq-100 über oder unter seiner 200-Tage-Linie liegt |
| `--ohne-news` | keine Schlagzeilen laden (Quartalszahlen-Regel bleibt) |
| `--ohne-zahlen` | keine Quartalszahlen-Termine laden – die Zahlen-Regel ist dann aus |
| `--rueckblick 6` | Monate für das virtuelle Depot (0 = aus, max. 18) |
| `--gebuehr 1` | Ordergebühr in € je Kauf/Verkauf |
| `--bruchstuecke` | auch Bruchteile von Aktien handeln |
| `--nur-schluss` | laufende Tageskerze ignorieren, nur abgeschlossene Tage bewerten |
| `--papier` | Papier-Depot fortschreiben (Vorwärtstest mit virtuellem Geld, Stand wird gespeichert); eigene Datei mit `--papier meine_datei.json` (in Colab ebenfalls im Drive-Ordner `swing_scanner`) |
| `--papier-neu` | Papier-Depot neu anfangen (der bisherige Stand bleibt als Kopie mit Datum erhalten) |
| `--bericht bericht/README.md` | alles zusätzlich als Markdown-Bericht speichern (Ticker als TradingView-Links; nutzt der automatische Lauf) |
| `--csv signale.csv` | Scanner-Tabelle als CSV für Excel speichern, alle Depot-Trades in `signale_trades.csv` |
| `--debug` | Original-Meldungen von yfinance anzeigen |

Die festen Regeln (Positionsgrenzen, Lernregel, Zeitstopp …) stehen als Konstanten oben im Skript. Sie sind bewusst vorab festgelegt: Wer sie so lange verstellt, bis der Rückblick gut aussieht, passt sie nur an den Zufall der Vergangenheit an.

Daten: 5 Jahre Tageskerzen, Quartalszahlen-Termine und Schlagzeilen von Yahoo Finance. Short-Positionen (z. B. per CFD oder Turbo-Schein) haben nach oben offene Verluste; Leih- und Finanzierungskosten sind im Rückblick nicht berücksichtigt. Der Rückblick nutzt die heutige Watchlist und sieht deshalb für Kauf-Strategien tendenziell zu gut aus. Vergangene Ergebnisse sind keine Garantie für die Zukunft; die Ausgabe ist keine Anlageberatung.
