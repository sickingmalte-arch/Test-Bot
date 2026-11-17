# 🔬 Short nach schlechten Zahlen 1: nur außerhalb des Aufwärtsmarkts

Getestet am 17.11.2026 · Quelle: Bernard & Thomas (1989), „Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?“, Journal of Accounting Research 27; Chan, Jegadeesh & Lakonishok (1996), Journal of Finance 51. Nach schlechten Quartalszahlen fallen Kurse im Schnitt noch Wochen weiter (Post-Earnings-Drift).

Neue Short-Strategie: Fällt eine Aktie am Tag, an dem ihre Quartalszahlen wirken, um mindestens 2 ATR unter den Vortagesschluss, setzt der Bot am nächsten Tag zur Eröffnung auf weiter fallende Kurse (Stop +3 ATR, Ziel −3 ATR, Zeitstopp wie immer). Wie bei den alten Shorts nur, wenn der Nasdaq-100 nicht im Aufwärtstrend ist; höchstens 2 Shorts gleichzeitig, alle übrigen Regeln wie im Bot. Die 8 alten Short-Strategien bleiben aus. Gegenprobe: je Aktie gleich viele Shorts an zufälligen erlaubten Tagen.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +11,6 % / −16 % | +12,2 % / −17 % | +7,9 % / −15 % |
| Short nach schlechten Zahlen 1: nur außerhalb des Aufwärtsmarkts | +11,3 % / −15 % | +12,6 % / −17 % | +8,7 % / −15 % |
| Gegenprobe Zufall 1 | +11,8 % / −16 % | +11,5 % / −18 % | +7,6 % / −15 % |
| Gegenprobe Zufall 2 | +11,6 % / −16 % | +12,1 % / −17 % | +7,6 % / −14 % |
| Gegenprobe Zufall 3 | +11,5 % / −16 % | +11,3 % / −17 % | +7,2 % / −16 % |
| Gegenprobe Zufall 4 | +11,3 % / −16 % | +11,5 % / −18 % | +7,9 % / −15 % |
| Gegenprobe Zufall 5 | +11,4 % / −15 % | +12,8 % / −16 % | +7,9 % / −15 % |
| Gegenprobe Zufall 6 | +11,9 % / −15 % | +11,2 % / −17 % | +8,6 % / −13 % |

Unterschied in Prozentpunkten: 2010–2014 -0,3, 2015–2021 +0,4, 2022–2026 +0,8

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
