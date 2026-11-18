# 🔬 Short schwacher Bilanzen: Short-Signale nur bei Firmen mit Verlust oder schrumpfendem Geschäft

Getestet am 18.11.2026 · Quelle: Campbell, Hilscher & Szilagyi (2008), „In Search of Distress Risk“, Journal of Finance 63 – Aktien mit hohem Pleiterisiko bringen auffällig wenig; Piotroski (2000), „Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers“, Journal of Accounting Research 38 – Firmen mit schwachen Bilanzzahlen schneiden schlechter ab.

Der Bot darf nur Aktien shorten, deren zuletzt veröffentlichte Bilanz schwach ist: Verlust in den letzten 12 Monaten ODER Umsatz und Gewinn beide unter Vorjahr. Zahlen von der SEC, bekannt erst ab dem Tag nach der Veröffentlichung. Short nur, wenn zusätzlich eins der 8 alten Short-Signale feuert. Wie im fairen Short-Test: 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum, höchstens 2 Shorts gleichzeitig, Stop und Ziel wie im Bot, mit Gebühr und Spread. Gegenprobe: je Aktie gleich viele Shorts an zufälligen erlaubten Tagen, ohne Blick auf die Bilanz.

- **Vermutung:** Firmen, die Geld verlieren oder schrumpfen, fallen öfter weiter. Shorts nur auf solche Aktien verdienen Geld und machen den Bot in allen drei Zeiträumen besser – und besser als Shorts an zufälligen Tagen.
- **Widerlegt, wenn:** Keine Variante schafft in jedem Zeitraum alles davon: Mitte der 8 Listen mehr Rendite als der Bot nur mit Long, mindestens 6 von 8 Listen besser, höchstens 1 Punkt mehr Rückgang (Mitte), mindestens 30 Short-Trades und mehr Rendite als die beste von 6 Zufalls-Gegenproben.
- **Varianten:** 2, vor dem Rechnen festgelegt: (1) nur außerhalb des Aufwärtsmarkts wie die alten Shorts, (2) in jeder Marktlage. „Schwach“ fest: Verlust in 12 Monaten ODER Umsatz und Gewinn beide unter Vorjahr.

**Ergebnis: S1: nicht überall besser; S2: nicht überall besser**

Je Zeitraum 8 Zufallslisten mit je 24 Aktien aus dem damaligen S&P 500 (zur Wahl standen 2010–2014: 266, 2015–2021: 303, 2022–2026: 411 Aktien). Werte: Mitte (Median) der 8 Listen, Rendite pro Jahr / größter Rückgang.

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot nur Long (wie heute) | +11,4 % / −16 % | +4,5 % / −19 % | +2,9 % / −14 % |
| **S1: + alte Short-Signale nur bei schwacher Bilanz (nicht im Aufwärtsmarkt)** | +9,7 % / −18 % | +2,9 % / −22 % | +2,2 % / −15 % |
| … Unterschied zum Bot (Mitte, Punkte) · Listen besser | -1,7 · 1 von 8 | -1,0 · 1 von 8 | -0,1 · 4 von 8 |
| … Shorts pro Jahr je Liste · Treffer · Ø Ergebnis je Short | 3,4 · 25 % · -0,44 R | 3,8 · 38 % · -0,20 R | 2,6 · 50 % · -0,05 R |
| … Gegenprobe: gleich viele Shorts an Zufallstagen (beste von 2) · Ø je Short | +11,5 % · -0,33 R | +3,9 % · -0,24 R | +2,9 % · +0,02 R |
| **S2: + alte Short-Signale nur bei schwacher Bilanz (jede Marktlage)** | +9,7 % / −17 % | +3,7 % / −20 % | +1,5 % / −15 % |
| … Unterschied zum Bot (Mitte, Punkte) · Listen besser | -1,8 · 1 von 8 | -0,9 · 2 von 8 | -0,2 · 1 von 8 |
| … Shorts pro Jahr je Liste · Treffer · Ø Ergebnis je Short | 6,4 · 36 % · -0,23 R | 4,1 · 40 % · -0,17 R | 0,6 · 28 % · -0,36 R |
| … Gegenprobe: gleich viele Shorts an Zufallstagen (beste von 2) · Ø je Short | +10,3 % · -0,28 R | +4,2 % · -0,21 R | +2,9 % · -0,00 R |

**Urteile:**

- **S1** (+ alte Short-Signale nur bei schwacher Bilanz (nicht im Aufwärtsmarkt)): nicht überall besser
- **S2** (+ alte Short-Signale nur bei schwacher Bilanz (jede Marktlage)): nicht überall besser

- Bilanzdaten in den gezogenen Aktien: 2010–2014: 142 Aktien mit Bilanz, 0 ohne, schwach an 14 % der Börsentage; 2015–2021: 151 Aktien mit Bilanz, 0 ohne, schwach an 21 % der Börsentage; 2022–2026: 158 Aktien mit Bilanz, 0 ohne, schwach an 15 % der Börsentage.

So gelesen: „Ø Ergebnis je Short“ ist der Gewinn oder Verlust eines Shorts nach Spread und Gebühr in R (1 R = der geplante Verlust bis zum Stop). Unter 0 R kostet jeder Short im Schnitt Geld.

Verbleibende Verzerrung: Zur Wahl stehen nur Aktien, die heute noch im S&P 500 oder Nasdaq-100 sind – Pleitefirmen und abgestürzte Verlierer fehlen, also genau die Aktien, an denen Shorts verdient hätten. Für Shorts ist das Ergebnis deshalb eher noch zu schlecht. Leihgebühren für Shorts sind nicht abgezogen. Simulation mit Spielgeld, keine Anlageberatung.
