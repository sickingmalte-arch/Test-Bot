# 🧠 Lernmodell des Swing-Bots

Stand: 31.10.2026 11:31 Uhr · Kurse bis 30.10.2026 · 523 Aktien (S&P 500, Nasdaq-100 und Watchlist)

> Der Bot lernt hier aus jedem Trade – auch aus den nur gedachten: Jedes Kauf-Signal jeder Aktie wird nach seinen Regeln durchgespielt, jeder Verlust bekommt Gründe, und ein Lernmodell lernt jeden Monat neu, welche Signale gut laufen. **Die Kaufregeln ändern sich dadurch noch nicht** – der Bot zeigt die Punktzahl nur an. Nach der Punktzahl kauft er erst, wenn der [Rückblick](RUECKBLICK.md) zeigt, dass es besser ist, und du Ja sagst.

## ⚠️ Daten

- ✅ Alle Kurse, Termine und Bilanzen sind da.

## 📋 Kauf-Signale vom 30.10.2026 mit Punktzahl

Punktzahl = vom Modell geschätzte Chance, dass der Trade im Plus endet. Rang = besser als so viel Prozent der Signale der 12 Monate davor. ✅ = unter den besten 30 % (Kauf-Schwelle diesen Monat: 57 %).

**Deine Watchlist** (nur aus ihr kauft der Bot):

| Aktie | Strategie | Punktzahl | Rang | |
|---|---|---:|---:|---|
| COST | ATR-Ausbruch | 53 % | 44 | – |
| LLY | Ausbruch | 49 % | 15 | – |
| XOM | Ausbruch | 48 % | 11 | – |
| NVDA | RSI-2-Rücksetzer | 46 % | 5 | – |

**Ganzer Markt – die 15 besten von 74 Signalen** (nur zum Lernen und Vergleichen):

| Aktie | Strategie | Punktzahl | Rang | |
|---|---|---:|---:|---|
| KIM | Ausbruch | 58 % | 72 | ✅ |
| MRVL | RSI-2-Rücksetzer | 56 % | 63 | – |
| LNT | Ausbruch | 55 % | 55 | – |
| CASY | Rücksetzer | 55 % | 54 | – |
| MDLZ | MACD-Wende | 54 % | 51 | – |
| D | ATR-Ausbruch | 54 % | 48 | – |
| FDX | Ausbruch | 54 % | 47 | – |
| CNC | Rücksetzer | 53 % | 45 | – |
| COST | ATR-Ausbruch | 53 % | 44 | – |
| HPE | RSI-2-Rücksetzer | 53 % | 43 | – |
| GD | Ausbruch | 53 % | 41 | – |
| EXC | Ausbruch | 53 % | 40 | – |
| TSN | ATR-Ausbruch | 52 % | 37 | – |
| DELL | RSI-2-Rücksetzer | 52 % | 34 | – |
| ACGL | ATR-Ausbruch | 52 % | 33 | – |

## 🧠 Was das Modell gelernt hat

Modell für 2026-10: trainiert am Monatsanfang mit **461.444 abgeschlossenen gedachten Trades** (alle Kauf-Signale aller Aktien seit 2008, Ergebnis bekannt bis 2026-09-30).

**Trennt es gute von schlechten Signalen?** Letzte 12 Monate (24721 gedachte Trades, jeder Monat mit dem Modell, das damals galt – also ohne Blick in die Zukunft):

| Punktzahl | Trefferquote | Ø Ergebnis |
|---|---:|---:|
| bestes Fünftel | 56 % | +0,06 R |
| 2. Fünftel | 51 % | -0,03 R |
| Mitte | 50 % | -0,01 R |
| 4. Fünftel | 50 % | -0,00 R |
| schlechtestes Fünftel | 49 % | -0,00 R |

Trennschärfe (AUC): 0,53 – 0,50 wäre Münzwurf, ab etwa 0,55 ist es für Börsenkurse brauchbar.

**Worauf es am meisten achtet** (Modell bis 2025-10-01, geprüft an den 12 Monaten danach: Wie viel schlechter wird die Vorhersage, wenn man das Merkmal durcheinanderwürfelt?):

| Merkmal | Wichtigkeit | Richtung |
|---|---|---|
| Markt 3 Monate | ████████ | wirkt nur zusammen mit anderen Merkmalen |
| Chance/Risiko | █████ | je niedriger, desto besser |
| Anteil Aktien über 50-Tage-Linie | ███ | je niedriger, desto besser |
| Tage bis zu den Quartalszahlen | ███ | wirkt nur zusammen mit anderen Merkmalen |
| Stärke der Branche (1 Monat) | ███ | wirkt nur zusammen mit anderen Merkmalen |
| Branche über 50-Tage-Linie | ██ | je niedriger, desto besser |
| Momentum 12 Monate ohne letzten Monat | ██ | wirkt nur zusammen mit anderen Merkmalen |
| schon gelaufen (vom 10-Tage-Tief) | █ | je niedriger, desto besser |
| Markt 1 Woche | █ | je niedriger, desto besser |
| Stärke gegenüber dem S&P 500 (3 Monate) | █ | wirkt nur zusammen mit anderen Merkmalen |
| Momentum 12 Monate | █ | wirkt nur zusammen mit anderen Merkmalen |
| letzte Gewinnüberraschung | █ | wirkt nur zusammen mit anderen Merkmalen |

## 🔎 Häufigste Fehler

Alle gedachten Trades der letzten 12 Monate: 24721 Signale, davon verloren 49 %. Von den 10087 Signalen mit ✅ verloren 47 %. Lernt das Modell aus den Fehlern, kommen sie bei ✅ seltener vor:

| Warum verloren? | bei allen Signalen | bei ✅ |
|---|---:|---:|
| Branche schwach | 14 % | 15 % |
| Zeitstopp ohne Schwung | 13 % | 14 % |
| Quartalszahlen | 11 % | 7 % ↓ |
| Normales Auf und Ab (kein besonderer Grund) | 10 % | 10 % |
| Absturz des Gesamtmarkts | 7 % | 6 % |
| Stop zu eng (Kurs war danach schnell wieder über dem Einstieg) | 4 % | 5 % |
| Signal zu spät (Aktie war schon weit gelaufen) | 4 % | 3 % ↓ |
| Kurslücke unter den Stop (über Nacht) | 3 % | 3 % |
| Plötzlicher Einbruch nur dieser Aktie (vermutlich eine Nachricht) | 1 % | 1 % ↓ |

Anteil an allen Trades; ein Trade kann mehrere Gründe haben. ↓ = das Modell meidet diesen Fehler deutlich, ↑ = es tappt öfter hinein.

## 📒 Fehler-Analyse der Trades im Übungsdepot

| Aktie | Kauf | Verkauf | Ergebnis | Verkauft wegen | Warum verloren? |
|---|---|---|---:|---|---|
| AAPL | 21.10.26 | 30.10.26 | +0,57 R | vor Quartalszahlen | – |
| NOW | 21.10.26 | 28.10.26 | +0,09 R | vor Quartalszahlen | – |
| LLY | 21.10.26 | 28.10.26 | +0,47 R | vor Quartalszahlen | – |

## Ehrlich bleiben

- **Bilanzdaten** (Bewertung, Wachstum, Qualität) kommen von der SEC mit dem Tag der Veröffentlichung; das Modell sieht jede Zahl erst ab dem Tag danach. Vor 2009 gibt es sie nicht, und Firmen ohne US-Bilanz haben keine.
- **Überlebens-Verzerrung:** Die Aktienliste ist die von heute. Firmen, die früher pleite gingen oder aus dem Index flogen, fehlen beim Lernen und im Rückblick – beides sieht dadurch etwas zu gut aus.
- **Nur Papier.** Kein echtes Geld, keine Anlageberatung.

