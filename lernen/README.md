# 🧠 Lernmodell des Swing-Bots

Hier lernt der Bot **aus jedem einzelnen Trade** – nicht nur, indem er schwache Strategien pausiert. Der Lern-Lauf
gehört zum Swing-Bot: Er rechnet abends nach dem US-Schluss (und noch einmal früh vor dem Morgen-Lauf), der Bot zeigt
das Ergebnis in seinem Bericht (`bericht/README.md`, Abschnitt „🧠 Lernmodell“) und im Gehirn (Seite „Lehren“).

> **Die Kaufregeln ändern sich dadurch noch nicht.** Der Bot zeigt die Punktzahl je Signal nur an. Nach der
> Punktzahl kauft er erst, wenn der ehrliche Rückblick ([RUECKBLICK.md](RUECKBLICK.md)) zeigt, dass es besser ist,
> und du im Pull Request Ja sagst. Das Übungsdepot misst bis dahin weiter die heutigen Regeln.

## So lernt der Bot

1. **Den ganzen Markt ansehen.** Gelernt wird aus allen Aktien aus S&P 500 und Nasdaq-100 (rund 520, die Liste
   kommt jeden Tag von Wikipedia) plus deiner Watchlist. **Gekauft wird weiter nur aus der Watchlist** (Variable
   `TICKER`). Die Kurse liegen im Zwischenspeicher von GitHub; geladen werden nur die neuen Tage.
2. **Viele Merkmale je Kauf-Signal** – alles, was am Signaltag zum Schlusskurs schon bekannt war:

   | Art | Merkmale |
   |---|---|
   | Momentum | Anstieg über 3, 6 und 12 Monate, Stärke gegenüber dem S&P 500, Abstand zum 52-Wochen-Hoch |
   | Value (günstig?) | Gewinnrendite (1/KGV), Buchwert/Börsenwert (1/KBV), Free-Cashflow-Rendite |
   | Growth (Wachstum) | Umsatz- und Gewinnwachstum, Gewinnüberraschung der letzten Quartalszahlen |
   | Qualität | Gewinnmarge, Brutto- und operative Marge, Verschuldung, Eigenkapitalrendite, stabile Gewinne |
   | Chart | die acht Kauf-Strategien des Bots, RSI, Abstand zu den Durchschnittslinien, Bollinger, Volumen, MACD, wie weit die Aktie schon gelaufen ist, Kurslücken und Absturz-Tage zuletzt |
   | Markt und Branche | S&P 500 und Nasdaq-100 über der 200-Tage-Linie, Angst-Index VIX, Anteil der Aktien über ihrer 50-Tage-Linie, Stärke der eigenen Branche |
   | Quartalszahlen | Tage seit und bis zu den nächsten Zahlen |

3. **Gedachte Trades.** Jedes Kauf-Signal jeder Aktie wird nach den Regeln des Bots durchgespielt (Kauf zur
   nächsten Eröffnung bis zum Limit, Stop, Ziel, vor Quartalszahlen raus, Zeitstopp, mit Kosten). So lernt der Bot
   aus Hunderttausenden Fällen statt nur aus den paar eigenen Käufen.
4. **Fehler-Analyse.** Jeder Verlust – im Übungsdepot und bei den gedachten Trades – bekommt Gründe:
   - Kurslücke unter den Stop,
   - Absturz des Gesamtmarkts,
   - Branche schwach,
   - Quartalszahlen,
   - Signal zu spät (Aktie schon weit gelaufen),
   - Stop zu eng (Kurs war danach schnell wieder über dem Einstieg),
   - plötzlicher Einbruch nur dieser Aktie (vermutlich eine Nachricht),
   - Zeitstopp.

   Die Gründe werden gezählt. Der Bericht zeigt, ob das Modell diese Fehler bei den Signalen mit der besten
   Punktzahl seltener macht.
5. **Lernmodell.** Ein Gradient-Boosting-Modell (scikit-learn: viele kleine Entscheidungsbäume hintereinander)
   lernt aus allen Merkmalen, welche Signale gut liefen. Es gibt jedem neuen Signal eine **Punktzahl**: die
   geschätzte Chance auf einen Gewinn. ✅ heißt: unter den besten 30 % der Punktzahlen der 12 Monate davor.
6. **Jeden Monat neu lernen, ohne Blick in die Zukunft.** Am Monatsanfang wird das Modell neu trainiert, und zwar
   nur mit Trades, deren Ergebnis vorher schon feststand (Walk-forward).

## Ehrlich prüfen

- **Bilanzdaten mit Datum.** Yahoo kennt Bilanzen nur von heute. Der Lern-Teil nimmt sie deshalb von der
  US-Börsenaufsicht SEC (EDGAR), wo jede Zahl den Tag ihrer Veröffentlichung trägt.
  - Das Modell sieht eine Zahl erst ab dem Tag danach, eine spätere Korrektur erst ab ihrem eigenen Datum. Damit
    dürfen Value, Growth und Qualität auch im Rückblick getestet werden.
  - Vor 2009 gibt es keine solchen Daten, und Firmen ohne US-Bilanz haben keine.
  - Zum Vergleich rechnet der Rückblick auch ein Modell ganz ohne Bilanzdaten.
- **Rückblick 2010–2026.** Drei Zeiträume (2010–2014, 2015–2021, 2022–2026), Walk-forward, mit Gebühr und Spread,
  je 16 Läufe: [RUECKBLICK.md](RUECKBLICK.md). Verglichen werden:
  - Kaufen nach der Punktzahl, aus der Watchlist und aus allen Aktien,
  - der jetzige Bot,
  - „Nasdaq-100 kaufen und halten“ und „S&P 500 kaufen und halten“.
- **Nicht bei jedem Schreck verkaufen.** Der Rückblick prüft auch, erst zum Tagesschluss über den Stop zu
  entscheiden. Dabei gilt eine Notbremse 1,5 R unter dem Einstieg; geprüft werden drei Fälle:
  - immer so,
  - nur an Panik-Tagen des Gesamtmarkts,
  - nur bei starken Aktien.

  Damit das Risiko je Trade nie über 1 % steigt, richtet sich die Stückzahl dann nach der Notbremse (also kleinere
  Positionen). Ob ein Absturz eher Panik ist, kann das Modell selbst aus dem VIX, der Marktlage, Kurslücken und den
  Absturz-Tagen der letzten Wochen lernen.
- **Überlebens-Verzerrung.** Die Aktienliste ist die von heute. Firmen, die seit 2010 herausgefallen oder pleite
  gegangen sind, fehlen. Der Rückblick sieht dadurch für alle Varianten zu gut aus, auch für den jetzigen Bot.

## Dateien

| Datei | Inhalt |
|---|---|
| [lernlauf.py](lernlauf.py) | täglicher Lern-Lauf: Daten, Signale, Fehler-Analyse, Modell, Punktzahlen |
| [daten.py](daten.py) | Aktienliste (Wikipedia + Watchlist), Kurse und Quartalszahlen (Yahoo), Bilanzen (SEC) im Zwischenspeicher |
| [merkmale.py](merkmale.py) | Merkmale je Signal und das Ergebnis jedes gedachten Trades |
| [modell.py](modell.py) | Lernmodell, Walk-forward, Schwelle, was gelernt wurde |
| [fehler.py](fehler.py) | Fehler-Analyse der Verluste |
| [depot.py](depot.py) | Depot-Simulation für den Rückblick (Grenzen wie das Übungsdepot, Ausstiegs-Varianten) |
| [rueckblick.py](rueckblick.py) | Rückblick 2010–2026 → `rueckblick/ergebnis.json` und [RUECKBLICK.md](RUECKBLICK.md) |
| `punkte.json` | Punktzahl je Kauf-Signal der letzten Börsentage (liest der Bot) |
| `lernstand.json` | was das Modell diesen Monat gelernt hat, Güte, häufigste Fehler, Fehler-Analyse der Trades im Übungsdepot |
| `LERNEN.md` | alles davon zum Lesen |
| [tests/](tests) | Tests mit festen, gespeicherten Daten |

## Abläufe bei GitHub

- [`lernen.yml`](../.github/workflows/lernen.yml) – „Swing-Bot – Lernen“:
  - läuft um 23:23 UTC (Mo–Fr) und um 4:13 UTC (Di–Sa), also vor dem Morgen-Lauf des Bots um 6:47 UTC;
  - fehlen Kurse vom letzten Börsentag, steht das oben auf der Seite und im Bericht;
  - der allererste Lauf holt alle Daten seit 2007 und braucht rund eine Stunde.
- [`swing-bot.yml`](../.github/workflows/swing-bot.yml): Der Morgen-Lauf liest `lernen/` (Option `--lernmodell`).
- [`lernen-check.yml`](../.github/workflows/lernen-check.yml): Tests bei jeder Änderung an `lernen/` oder am Bot.
- Secret `LERNEN_SEC_KONTAKT` (Settings → Secrets and variables → Actions → Secrets): Name und E-Mail als Kennung für
  die SEC, z. B. `Test-Bot deinname@beispiel.de`. Die SEC verlangt das; ohne Secret fehlen die Bilanzdaten
  (Bewertung, Wachstum, Qualität), und der Bericht sagt das. Das Secret ist nicht öffentlich sichtbar.

## Selbst rechnen

```
pip install -r lernen/requirements.txt
python lernen/daten.py --cache lern_cache --watchlist        # Daten holen (beim ersten Mal rund eine Stunde)
python lernen/rueckblick.py --cache lern_cache --laeufe 16   # Rückblick (mehrere Stunden)
python lernen/lernlauf.py --cache lern_cache                 # ein Lern-Lauf wie bei GitHub
python -m pytest -q lernen/tests                             # Tests
```
