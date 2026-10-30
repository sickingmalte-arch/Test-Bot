---
tags: [lernen, forschung, lernmodell]
---
# 🧠 Gelernt: Lernmodell und Fehler-Analyse

Stand: 30.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

Diese Notiz ändert der Bot nie. Sie hält fest, was der große Test des Lernmodells ergeben hat, damit es nicht noch einmal ungeprüft eingebaut wird. Zurück zur [[Start|Startseite]] · alle Tests auf einen Blick: [[Notizen/Was der Bot schon weiß]] · was der Bot jeden Tag aus seinen Trades lernt: [[Lehren]].

> [!summary] Kurz gesagt
> - **Das Lernmodell läuft im Bot mit, entscheidet aber nicht.** Jeden Abend spielt es alle Kauf-Signale von rund 520 Aktien als gedachte Trades durch, analysiert jeden Verlust und gibt jedem neuen Signal eine Punktzahl. Der Bericht zeigt die Punktzahl, das Gehirn zeigt auf der Seite [[Lehren]] die Fehler-Analyse.
> - **Es trennt gute und schlechte Signale kaum.** Die Trennschärfe liegt bei 0,51 (0,50 wäre ein Münzwurf). Erkennen kann es vor allem die Marktlage, kaum die einzelne Aktie.
> - **Kaufen nach Punktzahl war nicht überall besser.** „Beste Punktzahl zuerst“ war 2015–2021 und 2022–2026 besser, 2010–2014 aber 3 Punkte schlechter. Nur die besten 30 % oder 50 % zu kaufen, war fast überall schlechter.
> - **Nicht bei jedem Schreck verkaufen half nicht.** Stop erst zum Tagesschluss, die Panik-Regel und starke Aktien halten: Alle drei waren schlechter als heute.
> - **Auch eine Markt-Ampel aus dem Modell und der Vergleich der Signale am selben Tag** waren nicht überall besser.

## So wurde getestet

- **Aktien:** alle aus S&P 500 und Nasdaq-100 plus die Watchlist (518 mit genug Kursen), Kurse von Yahoo
- **Bilanzzahlen:** von der US-Börsenaufsicht SEC, jede mit dem Tag ihrer Veröffentlichung. Das Modell sah eine Zahl erst ab dem Tag danach.
- **Signale:** rund 490.000 Kauf-Signale seit 2008, jedes als gedachter Trade nach den Regeln des Bots (mit Gebühr und Spread)
- **Lernen:** Für jeden Monat seit 2010 wurde neu gelernt, nur mit Trades, deren Ergebnis vorher feststand (Walk-forward)
- **Depot:** wie das Übungsdepot, gekauft wird nur aus der Watchlist; 2010–2014, 2015–2021, 2022–2026, je 16 Läufe
- **Regel:** Übernommen wird nur, was überall hilft oder zumindest nirgends erkennbar schadet.

## Ergebnisse

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +9,2 % / −17 % | +10,5 % / −17 % | +7,0 % / −16 % |
| Beste Punktzahl zuerst | +6,1 % / −19 % | +14,6 % / −16 % | +10,1 % / −18 % |
| Nur beste 50 %, beste zuerst | +2,7 % / −21 % | +11,7 % / −13 % | +5,7 % / −13 % |
| Nur beste 30 %, beste zuerst | +3,2 % / −13 % | +7,6 % / −12 % | +3,9 % / −11 % |
| S&P 500 kaufen und halten | +19,2 % / −21 % | +15,8 % / −33 % | +12,3 % / −23 % |
| Nasdaq-100 kaufen und halten | +22,9 % / −20 % | +23,3 % / −31 % | +13,9 % / −30 % |

Verkaufs-Regeln (Signale wie heute, nur Watchlist), Rendite pro Jahr:

| Verkauf | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| wie heute (Stop gilt sofort) | +12,7 % | +10,1 % | +6,0 % |
| Stop erst zum Tagesschluss (Notbremse 1,5 R) | +7,5 % | +8,9 % | +3,2 % |
| nur an Panik-Tagen erst zum Schluss | +7,6 % | +7,1 % | +2,8 % |
| starke Aktien halten | +9,9 % | +11,9 % | +4,4 % |

Damit das Risiko je Trade auch mit der Notbremse nie über 1 % steigt, waren die Positionen bei diesen Regeln kleiner. Die Rückgänge wurden dadurch kleiner, die Rendite aber deutlich niedriger.

## Was die Fehler-Analyse zeigt

Von allen gedachten Trades seit 2010 verloren 44 %. Häufigste Gründe, als Anteil an allen Trades (ein Trade kann mehrere Gründe haben):

- Absturz des Gesamtmarkts: 12 % (bei der Auswahl des Modells sogar 14 %)
- Zeitstopp ohne Schwung: 12 %
- Quartalszahlen: 9 % (bei der Auswahl des Modells nur 7 %)
- Branche schwach: 6 %
- Stop zu eng, Kurs war danach schnell wieder über dem Einstieg: 6 %
- Signal zu spät, Aktie war schon weit gelaufen: 4 % (bei der Auswahl des Modells nur 2 %)
- Kurslücke unter den Stop: 3 %

**Das Modell lernt also aus Fehlern:** Es meidet Quartalszahlen und zu späte Signale. Den häufigsten Fehler, den Absturz des ganzen Markts, kann es aber nicht vermeiden. Im Gegenteil: Es mag Signale nach schwachen Markttagen („je niedriger der Markt, desto besser“), und genau dann geht es manchmal weiter abwärts.

## Was das Modell am wichtigsten findet

1. Markt der letzten 3 Monate
2. Anteil der Aktien über ihrer 50-Tage-Linie (je niedriger, desto besser)
3. Markt der letzten Woche (je niedriger, desto besser)
4. Chance/Risiko des Signals (je niedriger, desto besser)
5. Branche über der 50-Tage-Linie

Bewertung, Wachstum und Qualität aus den Bilanzen spielen kaum eine Rolle. Ohne Bilanzdaten war die Trennschärfe praktisch gleich (0,505 statt 0,506).

## Warum es trotzdem im Bot bleibt

- Es lernt **jeden Monat weiter**. Werden die Punktzahlen besser, zeigt das die Trennschärfe im Bericht.
- Die **Fehler-Analyse** jedes Trades im Übungsdepot zeigt dir, warum ein Trade verloren hat.
- **Kaufen nach Punktzahl ist eingebaut, aber aus.** Einschalten erst nach einem neuen Test, der überall besser ist.

## Nachtest: Markt-Ampel und Signale am selben Tag vergleichen

Weil das Modell vor allem die Marktlage erkennt, wurden zwei weitere Ideen geprüft, beide im echten Bot auf der Watchlist:

- **Markt-Ampel:** An Tagen, an denen das Modell den Markt so schlecht sieht wie an den schlechtesten 20 % bzw. 30 % der Tage des Jahres davor, kauft der Bot nichts Neues.
- **Signale am selben Tag vergleichen:** Das Modell lernt nicht „Gewinn oder Verlust“, sondern „besser als die anderen Signale desselben Tages“. So fällt die Marktlage heraus.

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +9,2 % / −17 % | +10,5 % / −17 % | +7,0 % / −16 % |
| Markt-Ampel (schlechteste 20 % der Tage) | +9,4 % / −18 % | +9,3 % / −14 % | +6,9 % / −18 % |
| Markt-Ampel (schlechteste 30 % der Tage) | +10,2 % / −16 % | +9,7 % / −16 % | +6,6 % / −15 % |
| Am selben Tag verglichen, beste zuerst | +9,0 % / −18 % | +10,8 % / −18 % | +7,3 % / −16 % |
| Am selben Tag verglichen, nur beste 30 % | +4,7 % / −12 % | +6,9 % / −15 % | +5,1 % / −11 % |

- Die **Markt-Ampel mit 30 %** machte die Rückgänge überall etwas kleiner (rund 1 Punkt), kostete aber 2015–2021 und 2022–2026 Rendite. Nicht übernommen.
- **Am selben Tag vergleichen** trennt nur ganz wenig besser (Trennschärfe 0,515). Das beste Fünftel bringt +0,06 R, das schlechteste +0,04 R. Beim Kaufen änderte es fast nichts (±0,3 Punkte), die Rückgänge wurden etwas größer. Nicht übernommen.

## Auch geprüft: 7 statt 5 Positionen

- **Nur 7 Positionen:** +8,6 % statt +8,4 % pro Jahr, also praktisch gleich.
- **7 Positionen mit 7 % Gesamtrisiko:** +9,4 % pro Jahr, aber der größte Rückgang war 17,9 % statt 14,2 %, und er war in allen 6 Fällen größer.

Mehr Rendite gab es also nur mit mehr Risiko. Deshalb bleiben es 5 Positionen.

## Meine Gedanken

