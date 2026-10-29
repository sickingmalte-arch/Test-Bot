---
tags: [lernen, forschung]
---
# 🔁 Gelernt: Nachkaufen, Teilverkauf und 15-Minuten-Chart

Stand: 28.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

Diese Notiz ändert der Bot nie. Sie hält drei Ideen fest, die getestet und **nicht übernommen** wurden, damit sie nicht noch einmal ungeprüft eingebaut werden. Alle drei wollen eine laufende Position feiner steuern: nachkaufen, zwischendurch verkaufen oder im kurzen Chart früher aussteigen. Zurück zur [[Start|Startseite]] · alle Tests auf einen Blick: [[Notizen/Was der Bot schon weiß]].

> [!summary] Kurz gesagt
> - **Nachkaufen bei Rückgang** (mit 80-%-Grenze) erhöht das Risiko genau bei den Aktien, die schon schlecht laufen. Die Rendite wird nicht besser.
> - **Teil verkaufen beim Markt-Rücksetzer, am Boden zurückkaufen:** Der Boden ist erst hinterher sichtbar. Der Rückkauf ist kaum billiger als der Verkauf, und zwei Orders mehr kosten Gebühr und Spread.
> - **15-Minuten-Wächter beim Verkauf:** Früher verkaufen, wenn die Aktie im kurzen Chart dreht, bringt im Schnitt nichts. Am Ziel laufen lassen macht die einzelnen Trades etwas besser, das Depot aber nicht überall.

## So wurde getestet

- **Zeiträume:** 2010–2014, 2015–2021 und 2022–2026, beim 15-Minuten-Wächter nur Mai 2024 bis Oktober 2026 (mehr Stundenkerzen gibt es bei Yahoo nicht)
- **Aktien:** jeweils die Watchlist und 60 andere Aktien
- **Rechnung:** Mittel aus 16 Läufen, mit Gebühren und Spread, ohne Shorts
- **Regel:** Übernommen wird nur, was überall hilft oder zumindest nirgends erkennbar schadet.

## 1. Nachkaufen bei Rückgang, mit 80-%-Grenze

**Idee:** Neue Käufe füllen das Depot höchstens zu 80 %, die restlichen 20 % sind für Nachkäufe reserviert. Fällt eine Position bis zur Hälfte des Wegs zum Stop, kauft der Bot zur nächsten Eröffnung nach. Das passiert einmal je Position und nicht kurz vor Quartalszahlen. Stop und Ziel bleiben gleich.

| Variante (Oktober 2026) | Rendite pro Jahr (Ø der 6 Fälle) | besser als heute | größter Rückgang |
| --- | --- | --- | --- |
| heute | 8,4 % | – | 10–16 % |
| nur 80-%-Grenze | 8,1 % | 1 von 6 | 10–16 % |
| 80 % + halbe Menge nachkaufen | 7,9 % | 2 von 6 | 11–16 %, in 3 von 6 Fällen größer |
| 80 % + gleiche Menge nachkaufen | 8,1 % | 2 von 6 | 12–21 %, in 4 von 6 Fällen größer |

- **Die 80-%-Grenze greift kaum.** Der Bot ist im Schnitt nur zu 36–62 % investiert. Wo sie doch greift, verdrängt sie gute Käufe.
- **Nachkaufen erhöht das Risiko.** Die Trefferquote steigt etwas (56 % auf 58 %), weil der Kurs nach dem Nachkauf nicht mehr so weit steigen muss. Fällt die Aktie aber weiter bis zum Stop, verliert der Bot statt 1 % deutlich mehr.
- **Sehr ungleich:** je Zeitraum −2,1 bis +1,9 Prozentpunkte.

**Ergebnis:** nicht übernommen.

## 2. Teil verkaufen beim Markt-Rücksetzer, am Boden zurückkaufen

**Idee:** Liegt eine Position deutlich im Plus und der Markt (Nasdaq-100) macht einen Rücksetzer, verkauft der Bot zur nächsten Eröffnung einen Teil. Zeigt der Markt einen Boden, kauft er den Teil zur nächsten Eröffnung zurück, solange die Position noch offen ist.
- **Deutlich im Plus:** mindestens halb so weit im Plus, wie der Stop entfernt ist (0,5 R, etwa der halbe Weg zum Ziel); auch getestet: schon ab 0,3 R
- **Rücksetzer:** 3 % unter dem Hoch der letzten 20 Tage, Schluss unter der 20-Tage-Linie (EMA 20) oder ein Tag mit −1,5 %
- **Boden:** Schluss über dem Hoch des Vortags (Umkehrtag) oder wieder über der 20-Tage-Linie
- **Menge:** die Hälfte, auch getestet: alles; außerdem nur verkaufen, nie zurückkaufen

| Variante (Oktober 2026) | Rendite pro Jahr (Ø der 6 Fälle) | besser als heute | größter Rückgang (Ø) |
| --- | --- | --- | --- |
| heute | 8,4 % | – | 14,2 % |
| −3 % vom Hoch, Rückkauf am Umkehrtag | 8,2 % | 1 von 6 | 14,1 % |
| −3 % vom Hoch, Rückkauf über der 20-Tage-Linie | 8,2 % | 1 von 6 | 14,2 % |
| unter der 20-Tage-Linie, Rückkauf am Umkehrtag | 8,2 % | 1 von 6 | 14,1 % |
| unter der 20-Tage-Linie, Rückkauf darüber | 8,1 % | 1 von 6 | 14,2 % |
| Tag mit −1,5 %, Rückkauf am Umkehrtag | 8,4 % | 4 von 6 | 14,1 % |
| dasselbe, alles statt halb verkaufen | 8,5 % | 4 von 6 | 14,0 % |
| −3 % vom Hoch, schon ab kleinerem Plus | 8,0 % | 2 von 6 | 13,6 % |
| −3 % vom Hoch, nie zurückkaufen | 8,3 % | 3 von 6 | 13,9 % |

- **Der Boden ist erst hinterher sichtbar.** In etwa der Hälfte der Fälle kaufte der Bot teurer zurück, als er verkauft hatte. Im Schnitt war der Rückkauf nur 0,15–0,4 % billiger, weniger als Gebühr und Spread für zwei zusätzliche Orders.
- **Oft kommt der Rückkauf gar nicht.** In etwa 4 von 10 Fällen war der Trade vorher zu Ende (Ziel, Stop oder Zeitstopp). Erreicht die Aktie das Ziel, fehlt der verkaufte Teil.
- **Nur 3–7 % der Trades betroffen.** Der Bot kauft nur, wenn der Nasdaq-100 über seiner 200-Tage-Linie liegt.
- **Die beste Variante (+0,06 Punkte) ist Zufall.** Die Läufe schwanken allein durch die Reihenfolge der Aktien um 1,5–2 Punkte. 2022–2026 war jede Variante schlechter, die Rückgänge wurden nicht kleiner.

**Ergebnis:** nicht übernommen.

## 3. 15-Minuten-Wächter beim Verkauf

**Idee:** Kurz vor einem Verkauf schaut der Bot auf den 15-Minuten-Chart:
- **Vor Quartalszahlen und beim Zeitstopp** (heute immer zum Schlusskurs): Dreht die Aktie, schon vorher verkaufen.
- **Am Ziel:** Steigt die Aktie weiter, nicht verkaufen. Das Ziel wird zum neuen Stop, verkauft wird erst beim Drehen.
- **Kurz vor dem Stop:** Dreht die Aktie nahe am Stop klar nach unten, schon vorher verkaufen.

**Was „dreht“ heißt, wurde getestet:** Schluss unter dem Tief der letzten 3 Kerzen, Rückgang um 0,5 Tages-ATR vom Hoch, Schluss unter dem Tagesdurchschnittspreis (VWAP), EMA 9 unter EMA 21. Bei Quartalszahlen und Zeitstopp außerdem: ganzer Tag oder nur die letzten 2 Stunden.

**Test:** Yahoo liefert 15-Minuten-Kerzen nur für etwa 60 Tage. Deshalb liefen zwei Prüfungen:
- **Hauptprüfung mit Stundenkerzen als Ersatz:** Mai–Dez. 2024, 2025, Jan.–Okt. 2026, je Watchlist und 60 andere Aktien, 16 Läufe.
- **Gegenprobe mit echten 15-Minuten-Kerzen:** 6.8.–21.10.2026, rund 450 Trades.

Vorsichtig gerechnet: Verkauft wird etwa 30 Minuten nach dem Signal (Yahoo-Kurse sind 15 Minuten verzögert, die Live-Kette läuft etwa alle 15 Minuten). Liegt Stop oder Ziel im Weg, greift diese Order zuerst.

| Idee (beste Dreh-Regel) | Rendite pro Jahr (Ø, heute 6,8 %) | besser in | Ergebnis je Trade (alle Signale) |
| --- | --- | --- | --- |
| Quartalszahlen/Zeitstopp: beim Drehen früher verkaufen (VWAP, letzte 2 Stunden) | 7,2 % | 5 von 6 | ±0 |
| am Ziel laufen lassen, Ziel wird zum Stop | 7,6 % | 4 von 6 | +0,015 R, besser in 6 von 6 |
| am Ziel laufen lassen, nur bis Tagesschluss | 7,0 % | 4 von 6 | +0,013 R, besser in 6 von 6 |
| kurz vor dem Stop beim Drehen raus | 8,9 % | 4 von 6 | −0,016 R, schlechter in 6 von 6 |

- **Früher verkaufen vor Zahlen oder Zeitstopp:** Wenn eine Aktie im kurzen Chart dreht, fällt sie danach im Schnitt nicht weiter. Früher oder zum Schluss verkaufen bringt im Mittel dasselbe.
- **Vor dem Stop raus:** Damit verkauft der Bot zu viele Aktien, die sich wieder erholt hätten. Jeder einzelne Trade wird schlechter. Die höhere Rendite kommt nur von anderen Käufen, die nachrücken – sehr ungleich (−6 bis +7 Punkte je Fall).
- **Am Ziel laufen lassen:** die beste Idee. Die einzelnen Trades werden etwas besser, im Depot aber 2025 schlechter (−2,3 bis −3,6 Punkte), weil Plätze länger belegt sind. „Gewinner laufen lassen“ zeigte früher dasselbe Muster ([[Notizen/Gelernt – Stop nachziehen und absichern]]).
- **Gegenprobe mit 15-Minuten-Kerzen:** gleiche Richtung (am Ziel laufen lassen +0,004 bis +0,02 R je Trade, vor dem Stop raus schlechter, Quartalszahlen/Zeitstopp ±0), für eine Depot-Aussage aber zu kurz.
- **In echt eher schlechter:** Die Kurse sind verzögert, GitHub startet Läufe oft später, und die Live-Kette müsste Verkäufe wirklich buchen. Heute rechnet sie nur vor.

**Ergebnis:** nicht übernommen. Falls überhaupt, dann „am Ziel laufen lassen“ später noch einmal prüfen, wenn das Übungsdepot über etwa 30 Trades die Erwartung trifft.

## Was die drei Tests zeigen

- **Rein und raus kostet.** Jede zusätzliche Order kostet Gebühr und Spread. Der Vorteil aus besserem Timing ist meist kleiner.
- **Kurze Bewegungen sind schwer vorherzusagen.** Ob ein Rücksetzer oder ein Dreher im 15-Minuten-Chart weitergeht, lässt sich mit diesen Regeln nicht besser erkennen als durch Zufall.
- **Stop und Ziel bleiben die beste Steuerung.** Der Bot plant beim Kauf, wie viel er höchstens verlieren will und wo er Gewinn nimmt. Wer zwischendurch eingreift, macht das Ergebnis eher schlechter.

## Meine Gedanken

