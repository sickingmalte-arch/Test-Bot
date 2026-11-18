# 🔬 Short direkt nach schlechten Nachrichten: Herabstufung durch Analysten oder Pflichtmeldung mit Kursrutsch

Getestet am 18.11.2026 · Quelle: Womack (1996), „Do Brokerage Analysts' Recommendations Have Investment Value?“, Journal of Finance 51 – nach Herabstufungen fallen Kurse noch Wochen weiter; Chan (2003), „Stock price reaction to news and no-news: drift and reversal after headlines“, Journal of Financial Economics 70 – nach schlechten Nachrichten fällt der Kurs weiter, nach einem Rutsch ohne Nachricht erholt er sich eher.

Neue Short-Strategie in zwei Varianten. Alte Schlagzeilen gibt es nicht, aber zwei Arten schlechter Nachrichten haben eine echte, datierte Geschichte. (1) Ein Analyst stuft die Aktie herunter (Daten von Yahoo) – der Bot geht zur nächsten Eröffnung short. (2) Die Firma meldet der US-Börsenaufsicht SEC eine wichtige Nachricht (Formular 8-K, ohne Quartalszahlen) und die Aktie fällt an dem Tag um mindestens 2 ATR – die Börse fand die Nachricht also schlecht; Short zur nächsten Eröffnung, nicht am Zahlen-Tag. Eine Nachricht bis 16:00 New Yorker Zeit zählt für denselben Tag, eine spätere für den nächsten. In jeder Marktlage, Stop +3 ATR, Ziel −3 ATR, Zeitstopp wie immer, höchstens 2 Shorts gleichzeitig, mit Gebühr und Spread, auf den 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum. Gegenprobe: je Aktie gleich viele Shorts an zufälligen Tagen.

- **Vermutung:** Nach schlechten Nachrichten fällt eine Aktie weiter. Wer direkt danach shortet, verdient Geld und macht den Bot in allen drei Zeiträumen besser – und besser als Shorts an zufälligen Tagen.
- **Widerlegt, wenn:** Keine Variante schafft in jedem Zeitraum alles davon: Mitte der 8 Listen mehr Rendite als der Bot nur mit Long, mindestens 6 von 8 Listen besser, höchstens 1 Punkt mehr Rückgang (Mitte), mindestens 30 Short-Trades und mehr Rendite als die beste von 6 Zufalls-Gegenproben.
- **Varianten:** 2, vor dem Rechnen festgelegt: (N1) Herabstufung durch einen Analysten → Short, (N2) 8-K-Meldung ohne Quartalszahlen und am selben Tag ein Rutsch von mindestens 2 ATR → Short. Beide in jeder Marktlage.

**Ergebnis: N1: nicht überall besser; N2: nicht überall besser**

Je Zeitraum 8 Zufallslisten mit je 24 Aktien aus dem damaligen S&P 500 (zur Wahl standen 2010–2014: 266, 2015–2021: 303, 2022–2026: 411 Aktien). Werte: Mitte (Median) der 8 Listen, Rendite pro Jahr / größter Rückgang.

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot nur Long (wie heute) | +11,4 % / −16 % | +4,5 % / −19 % | +2,9 % / −14 % |
| **N1: + Short nach Herabstufung durch einen Analysten** | +11,3 % / −16 % | +4,0 % / −18 % | +2,5 % / −14 % |
| … Unterschied zum Bot (Mitte, Punkte) · Listen besser | -0,3 · 2 von 8 | +0,1 · 5 von 8 | -0,1 · 4 von 8 |
| … Shorts pro Jahr je Liste · Treffer · Ø Ergebnis je Short | 0,8 · 32 % · -0,28 R | keine Shorts | keine Shorts |
| … Gegenprobe: gleich viele Shorts an Zufallstagen (beste von 2) · Ø je Short | +12,0 % · -0,15 R | +4,6 % · -0,26 R | +2,6 % · keine Shorts |
| **N2: + Short nach Pflichtmeldung mit Kursrutsch** | +11,4 % / −17 % | +4,7 % / −19 % | +2,6 % / −15 % |
| … Unterschied zum Bot (Mitte, Punkte) · Listen besser | -0,4 · 1 von 8 | -0,2 · 4 von 8 | +0,0 · 4 von 8 |
| … Shorts pro Jahr je Liste · Treffer · Ø Ergebnis je Short | 0,3 · 22 % · -0,49 R | 0,6 · 43 % · +0,01 R | 0,4 · 49 % · +0,11 R |
| … Gegenprobe: gleich viele Shorts an Zufallstagen (beste von 2) · Ø je Short | +11,8 % · -0,27 R | +4,1 % · -0,10 R | +2,8 % · -0,01 R |

**Urteile:**

- **N1** (+ Short nach Herabstufung durch einen Analysten): nicht überall besser
- **N2** (+ Short nach Pflichtmeldung mit Kursrutsch): nicht überall besser

**Daten der Nachrichten:**

- Herabstufungen: Daten für 306 von 306 Aktien, früheste vom 08.12.2011, bei der Hälfte der Aktien ab 2012. Ereignisse in den gezogenen Aktien je Zeitraum: 2010–2014: 947, 2015–2021: 2271, 2022–2026: 1472.
- Pflichtmeldungen: Daten für 306 von 306 Aktien. Ereignisse in den gezogenen Aktien je Zeitraum: 2010–2014: 7353, 2015–2021: 11098, 2022–2026: 7185.

So gelesen: „Ø Ergebnis je Short“ ist der Gewinn oder Verlust eines Shorts nach Spread und Gebühr in R (1 R = der geplante Verlust bis zum Stop). Unter 0 R kostet jeder Short im Schnitt Geld.

Verbleibende Verzerrung: Zur Wahl stehen nur Aktien, die heute noch im S&P 500 oder Nasdaq-100 sind – Pleitefirmen und abgestürzte Verlierer fehlen, also genau die Aktien, an denen Shorts verdient hätten. Für Shorts ist das Ergebnis deshalb eher noch zu schlecht. Leihgebühren für Shorts sind nicht abgezogen. Simulation mit Spielgeld, keine Anlageberatung.
