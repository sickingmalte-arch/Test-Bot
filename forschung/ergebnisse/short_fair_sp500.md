# 🔬 Fairer Short-Test: alte Shorts und Short nach schlechten Zahlen mit zufälligen damaligen S&P-500-Aktien

Getestet am 18.11.2026 · Quelle: Ehrlicher Bot-Check vom 06.11.2026 (Verzerrung durch die heutige Watchlist); Bernard & Thomas (1989), „Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?“, Journal of Accounting Research 27; Chan, Jegadeesh & Lakonishok (1996), Journal of Finance 51. Nach schlechten Quartalszahlen fallen Kurse im Schnitt noch Wochen weiter (Post-Earnings-Drift).

Bisher liefen alle Short-Tests mit der heutigen Watchlist – lauter Aktien, die im Rückblick stark gestiegen sind. Hier handelt der Bot mit denselben 8 Zufallslisten aus dem damaligen S&P 500 wie im ehrlichen Bot-Check vom 06.11. (je Zeitraum am Abend vor dem Start gezogen). Je Liste: der Bot nur mit Long gegen denselben Bot mit Shorts. Höchstens 2 Shorts gleichzeitig, Stop und Ziel wie im Bot, mit Gebühr und Spread. Gegenprobe: je Aktie gleich viele Shorts an zufälligen erlaubten Tagen.

- **Vermutung:** Shorts haben bisher nur verloren, weil die heutige Watchlist aus späteren Gewinnern besteht. Mit Aktien, die man damals ohne Rückblick hätte wählen können, macht mindestens eine Short-Variante den Bot in allen drei Zeiträumen besser.
- **Widerlegt, wenn:** Keine Variante schafft in jedem Zeitraum alles davon: Mitte der 8 Listen mehr Rendite als der Bot nur mit Long, mindestens 6 von 8 Listen besser, höchstens 1 Punkt mehr Rückgang (Mitte), mindestens 30 Short-Trades und mehr Rendite als die beste von 6 Zufalls-Gegenproben.
- **Varianten:** 3, vor dem Rechnen festgelegt: (A) die 8 alten Short-Strategien wie im Bot (nur außerhalb des Aufwärtsmarkts), (B) Short nach schlechten Zahlen nur außerhalb des Aufwärtsmarkts, (C) Short nach schlechten Zahlen in jeder Marktlage – B und C genau wie am 17.11. (Rutsch ab 2 ATR am Zahlen-Tag).

**Ergebnis: A: nicht überall besser; B: nicht überall besser; C: nicht überall besser**

Je Zeitraum 8 Zufallslisten mit je 24 Aktien aus dem damaligen S&P 500 (zur Wahl standen 2010–2014: 266, 2015–2021: 303, 2022–2026: 411 Aktien). Werte: Mitte (Median) der 8 Listen, Rendite pro Jahr / größter Rückgang.

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot nur Long (wie heute) | +11,4 % / −16 % | +4,5 % / −19 % | +2,9 % / −14 % |
| **A: + die 8 alten Short-Strategien** | +9,5 % / −17 % | +4,0 % / −19 % | +2,3 % / −15 % |
| … Unterschied zum Bot (Mitte, Punkte) · Listen besser | -2,2 · 0 von 8 | -0,2 · 1 von 8 | +0,0 · 1 von 8 |
| … Shorts pro Jahr je Liste · Treffer · Ø Ergebnis je Short | 3,3 · 26 % · -0,48 R | 0,7 · 33 % · -0,31 R | 0,8 · 46 % · -0,13 R |
| … Gegenprobe: gleich viele Shorts an Zufallstagen (beste von 2) · Ø je Short | +10,6 % · -0,35 R | +4,5 % · -0,25 R | +2,2 % · -0,25 R |
| **B: + Short nach schlechten Zahlen (nicht im Aufwärtsmarkt)** | +11,0 % / −17 % | +3,9 % / −19 % | +2,0 % / −14 % |
| … Unterschied zum Bot (Mitte, Punkte) · Listen besser | -0,0 · 3 von 8 | -0,4 · 2 von 8 | +0,2 · 5 von 8 |
| … Shorts pro Jahr je Liste · Treffer · Ø Ergebnis je Short | 0,3 · 36 % · -0,40 R | 0,7 · 29 % · -0,25 R | 1,1 · 51 % · +0,07 R |
| … Gegenprobe: gleich viele Shorts an Zufallstagen (beste von 2) · Ø je Short | +11,5 % · -0,49 R | +4,5 % · -0,19 R | +2,9 % · -0,09 R |
| **C: + Short nach schlechten Zahlen (jede Marktlage)** | +10,8 % / −16 % | +3,8 % / −18 % | +2,8 % / −15 % |
| … Unterschied zum Bot (Mitte, Punkte) · Listen besser | -0,1 · 2 von 8 | -0,3 · 0 von 8 | +0,0 · 1 von 8 |
| … Shorts pro Jahr je Liste · Treffer · Ø Ergebnis je Short | 1,3 · 39 % · -0,18 R | 0,9 · 38 % · -0,12 R | 0,5 · 42 % · -0,07 R |
| … Gegenprobe: gleich viele Shorts an Zufallstagen (beste von 2) · Ø je Short | +11,8 % · -0,24 R | +3,9 % · keine Shorts | +2,7 % · -0,45 R |

**Urteile:**

- **A** (+ die 8 alten Short-Strategien): nicht überall besser
- **B** (+ Short nach schlechten Zahlen (nicht im Aufwärtsmarkt)): nicht überall besser
- **C** (+ Short nach schlechten Zahlen (jede Marktlage)): nicht überall besser

So gelesen: „Ø Ergebnis je Short“ ist der Gewinn oder Verlust eines Shorts nach Spread und Gebühr in R (1 R = der geplante Verlust bis zum Stop). Unter 0 R kostet jeder Short im Schnitt Geld.

Verbleibende Verzerrung: Zur Wahl stehen nur Aktien, die heute noch im S&P 500 oder Nasdaq-100 sind – Pleitefirmen und abgestürzte Verlierer fehlen, also genau die Aktien, an denen Shorts verdient hätten. Für Shorts ist das Ergebnis deshalb eher noch zu schlecht. Leihgebühren für Shorts sind nicht abgezogen. Simulation mit Spielgeld, keine Anlageberatung.
