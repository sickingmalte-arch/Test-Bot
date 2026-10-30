# 🧠 Lernmodell des Swing-Bots

Stand: 30.10.2026 07:10 Uhr · Kurse bis 29.10.2026 · 523 Aktien (S&P 500, Nasdaq-100 und Watchlist)

> Der Bot lernt hier aus jedem Trade – auch aus den nur gedachten: Jedes Kauf-Signal jeder Aktie wird nach seinen Regeln durchgespielt, jeder Verlust bekommt Gründe, und ein Lernmodell lernt jeden Monat neu, welche Signale gut laufen. **Die Kaufregeln ändern sich dadurch noch nicht** – der Bot zeigt die Punktzahl nur an. Nach der Punktzahl kauft er erst, wenn der [Rückblick](RUECKBLICK.md) zeigt, dass es besser ist, und du Ja sagst.

## ⚠️ Daten

- ✅ Alle Kurse, Termine und Bilanzen sind da.

## 📋 Kauf-Signale vom 29.10.2026 mit Punktzahl

Punktzahl = vom Modell geschätzte Chance, dass der Trade im Plus endet. Rang = besser als so viel Prozent der Signale der 12 Monate davor. ✅ = unter den besten 30 % (Kauf-Schwelle diesen Monat: 57 %).

**Deine Watchlist** (nur aus ihr kauft der Bot):

| Aktie | Strategie | Punktzahl | Rang | |
|---|---|---:|---:|---|
| SOFI | EMA-Kreuz | 52 % | 34 | – |
| JPM | Squeeze-Ausbruch | 50 % | 24 | – |
| LLY | Ausbruch | 50 % | 21 | – |
| HIMS | MACD-Wende | 47 % | 7 | – |
| MSFT | Rücksetzer | 45 % | 3 | – |

**Ganzer Markt – die 15 besten von 116 Signalen** (nur zum Lernen und Vergleichen):

| Aktie | Strategie | Punktzahl | Rang | |
|---|---|---:|---:|---|
| CASY | Rücksetzer | 58 % | 74 | ✅ |
| KIM | ATR-Ausbruch | 58 % | 72 | ✅ |
| HD | ATR-Ausbruch | 56 % | 61 | – |
| TXT | Ausbruch | 55 % | 58 | – |
| ROST | Rücksetzer | 55 % | 56 | – |
| LOW | ATR-Ausbruch | 55 % | 55 | – |
| HII | Ausbruch | 55 % | 54 | – |
| XEL | ATR-Ausbruch | 55 % | 53 | – |
| WEC | Ausbruch | 55 % | 53 | – |
| DG | Rücksetzer | 55 % | 53 | – |
| BF-B | Rücksetzer | 54 % | 51 | – |
| HPQ | RSI-2-Rücksetzer | 54 % | 50 | – |
| NCLH | Ausbruch | 54 % | 50 | – |
| TROW | EMA-Kreuz | 54 % | 50 | – |
| VLO | RSI-2-Rücksetzer | 54 % | 49 | – |

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
| NOW | 21.10.26 | 28.10.26 | +0,09 R | vor Quartalszahlen | – |
| LLY | 21.10.26 | 28.10.26 | +0,47 R | vor Quartalszahlen | – |

## Ehrlich bleiben

- **Bilanzdaten** (Bewertung, Wachstum, Qualität) kommen von der SEC mit dem Tag der Veröffentlichung; das Modell sieht jede Zahl erst ab dem Tag danach. Vor 2009 gibt es sie nicht, und Firmen ohne US-Bilanz haben keine.
- **Überlebens-Verzerrung:** Die Aktienliste ist die von heute. Firmen, die früher pleite gingen oder aus dem Index flogen, fehlen beim Lernen und im Rückblick – beides sieht dadurch etwas zu gut aus.
- **Nur Papier.** Kein echtes Geld, keine Anlageberatung.

