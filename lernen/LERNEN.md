# 🧠 Lernmodell des Swing-Bots

Stand: 03.11.2026 12:59 Uhr · Kurse bis 02.11.2026 · 523 Aktien (S&P 500, Nasdaq-100 und Watchlist)

> Der Bot lernt hier aus jedem Trade – auch aus den nur gedachten: Jedes Kauf-Signal jeder Aktie wird nach seinen Regeln durchgespielt, jeder Verlust bekommt Gründe, und ein Lernmodell lernt jeden Monat neu, welche Signale gut laufen. **Die Kaufregeln ändern sich dadurch noch nicht** – der Bot zeigt die Punktzahl nur an. Nach der Punktzahl kauft er erst, wenn der [Rückblick](RUECKBLICK.md) zeigt, dass es besser ist, und du Ja sagst.

## ⚠️ Daten

- ⚠️ Alte Kurse (nicht bis 02.11.2026) bei 1 Aktien: KVUE – sie werden heute nicht gehandelt.

## 📋 Kauf-Signale vom 02.11.2026 mit Punktzahl

Punktzahl = vom Modell geschätzte Chance, dass der Trade im Plus endet. Rang = besser als so viel Prozent der Signale der 12 Monate davor. ✅ = unter den besten 30 % (Kauf-Schwelle diesen Monat: 58 %).

**Deine Watchlist** (nur aus ihr kauft der Bot):

| Aktie | Strategie | Punktzahl | Rang | |
|---|---|---:|---:|---|
| MSFT | RSI-2-Rücksetzer | 51 % | 26 | – |

**Ganzer Markt – die 15 besten von 104 Signalen** (nur zum Lernen und Vergleichen):

| Aktie | Strategie | Punktzahl | Rang | |
|---|---|---:|---:|---|
| DELL | RSI-2-Rücksetzer | 68 % | 95 | ✅ |
| HPE | RSI-2-Rücksetzer | 66 % | 93 | ✅ |
| NTAP | RSI-2-Rücksetzer | 64 % | 90 | ✅ |
| CRM | RSI-2-Rücksetzer | 62 % | 86 | ✅ |
| PANW | RSI-2-Rücksetzer | 61 % | 83 | ✅ |
| MU | RSI-2-Rücksetzer | 61 % | 81 | ✅ |
| CRWD | RSI-2-Rücksetzer | 60 % | 78 | ✅ |
| P | RSI-2-Rücksetzer | 59 % | 77 | ✅ |
| IQV | RSI-2-Rücksetzer | 59 % | 75 | ✅ |
| VEEV | Rücksetzer | 57 % | 69 | – |
| LEN | ATR-Ausbruch | 57 % | 68 | – |
| CB | ATR-Ausbruch | 57 % | 67 | – |
| PPL | ATR-Ausbruch | 56 % | 64 | – |
| CPRT | ATR-Ausbruch | 55 % | 58 | – |
| FE | ATR-Ausbruch | 54 % | 51 | – |

## 🧠 Was das Modell gelernt hat

Modell für 2026-11: trainiert am Monatsanfang mit **463.621 abgeschlossenen gedachten Trades** (alle Kauf-Signale aller Aktien seit 2008, Ergebnis bekannt bis 2026-10-30).

**Trennt es gute von schlechten Signalen?** Letzte 12 Monate (23577 gedachte Trades, jeder Monat mit dem Modell, das damals galt – also ohne Blick in die Zukunft):

| Punktzahl | Trefferquote | Ø Ergebnis |
|---|---:|---:|
| bestes Fünftel | 57 % | +0,07 R |
| 2. Fünftel | 52 % | -0,01 R |
| Mitte | 51 % | +0,01 R |
| 4. Fünftel | 52 % | +0,02 R |
| schlechtestes Fünftel | 52 % | +0,03 R |

Trennschärfe (AUC): 0,52 – 0,50 wäre Münzwurf, ab etwa 0,55 ist es für Börsenkurse brauchbar.

**Worauf es am meisten achtet** (Modell bis 2025-11-01, geprüft an den 12 Monaten danach: Wie viel schlechter wird die Vorhersage, wenn man das Merkmal durcheinanderwürfelt?):

| Merkmal | Wichtigkeit | Richtung |
|---|---|---|
| Anteil Aktien über 50-Tage-Linie | ████████ | je niedriger, desto besser |
| Markt 3 Monate | ███████ | wirkt nur zusammen mit anderen Merkmalen |
| Markt 1 Woche | ███████ | wirkt nur zusammen mit anderen Merkmalen |
| Chance/Risiko | ██████ | je niedriger, desto besser |
| Tage bis zu den Quartalszahlen | █████ | wirkt nur zusammen mit anderen Merkmalen |
| Branche über 50-Tage-Linie | ████ | je niedriger, desto besser |
| Markt 1 Monat | ████ | je niedriger, desto besser |
| Momentum 12 Monate ohne letzten Monat | ███ | wirkt nur zusammen mit anderen Merkmalen |
| VIX-Anstieg 1 Woche | ██ | wirkt nur zusammen mit anderen Merkmalen |
| Momentum 6 Monate | ██ | wirkt nur zusammen mit anderen Merkmalen |
| Stärke der Branche (1 Monat) | █ | wirkt nur zusammen mit anderen Merkmalen |
| Umsatzwachstum | █ | wirkt nur zusammen mit anderen Merkmalen |

## 🔎 Häufigste Fehler

Alle gedachten Trades der letzten 12 Monate: 23577 Signale, davon verloren 47 %. Von den 9394 Signalen mit ✅ verloren 46 %. Lernt das Modell aus den Fehlern, kommen sie bei ✅ seltener vor:

| Warum verloren? | bei allen Signalen | bei ✅ |
|---|---:|---:|
| Branche schwach | 14 % | 15 % |
| Zeitstopp ohne Schwung | 13 % | 14 % |
| Normales Auf und Ab (kein besonderer Grund) | 10 % | 10 % |
| Quartalszahlen | 10 % | 5 % ↓ |
| Absturz des Gesamtmarkts | 5 % | 5 % |
| Stop zu eng (Kurs war danach schnell wieder über dem Einstieg) | 4 % | 5 % |
| Signal zu spät (Aktie war schon weit gelaufen) | 4 % | 2 % ↓ |
| Kurslücke unter den Stop (über Nacht) | 3 % | 3 % ↑ |
| Plötzlicher Einbruch nur dieser Aktie (vermutlich eine Nachricht) | 1 % | 1 % ↓ |

Anteil an allen Trades; ein Trade kann mehrere Gründe haben. ↓ = das Modell meidet diesen Fehler deutlich, ↑ = es tappt öfter hinein.

## 📒 Fehler-Analyse der Trades im Übungsdepot

| Aktie | Kauf | Verkauf | Ergebnis | Verkauft wegen | Warum verloren? |
|---|---|---|---:|---|---|
| HIMS | 21.10.26 | 02.11.26 | -0,98 R | Stop | Normales Auf und Ab (kein besonderer Grund) (vorläufig) |
| AAPL | 21.10.26 | 30.10.26 | +0,57 R | vor Quartalszahlen | – |
| NOW | 21.10.26 | 28.10.26 | +0,09 R | vor Quartalszahlen | – |
| LLY | 21.10.26 | 28.10.26 | +0,47 R | vor Quartalszahlen | – |

## Ehrlich bleiben

- **Bilanzdaten** (Bewertung, Wachstum, Qualität) kommen von der SEC mit dem Tag der Veröffentlichung; das Modell sieht jede Zahl erst ab dem Tag danach. Vor 2009 gibt es sie nicht, und Firmen ohne US-Bilanz haben keine.
- **Überlebens-Verzerrung:** Die Aktienliste ist die von heute. Firmen, die früher pleite gingen oder aus dem Index flogen, fehlen beim Lernen und im Rückblick – beides sieht dadurch etwas zu gut aus.
- **Nur Papier.** Kein echtes Geld, keine Anlageberatung.

