# 🔬 Short nach schlechten Zahlen 2: in jeder Marktlage

Getestet am 17.11.2026 · Quelle: Bernard & Thomas (1989), „Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?“, Journal of Accounting Research 27; Chan, Jegadeesh & Lakonishok (1996), Journal of Finance 51. Nach schlechten Quartalszahlen fallen Kurse im Schnitt noch Wochen weiter (Post-Earnings-Drift).

Neue Short-Strategie: Fällt eine Aktie am Tag, an dem ihre Quartalszahlen wirken, um mindestens 2 ATR unter den Vortagesschluss, setzt der Bot am nächsten Tag zur Eröffnung auf weiter fallende Kurse (Stop +3 ATR, Ziel −3 ATR, Zeitstopp wie immer) – auch im Aufwärtsmarkt, weil die Drift nach schlechten Zahlen laut Forschung nicht von der Marktlage abhängt. Höchstens 2 Shorts gleichzeitig, alle übrigen Regeln wie im Bot; die 8 alten Short-Strategien bleiben aus. Gegenprobe: je Aktie gleich viele Shorts an zufälligen erlaubten Tagen.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +11,6 % / −16 % | +12,2 % / −17 % | +7,9 % / −15 % |
| Short nach schlechten Zahlen 2: in jeder Marktlage | +11,0 % / −15 % | +11,9 % / −17 % | +8,1 % / −14 % |
| Gegenprobe Zufall 1 | +13,1 % / −14 % | +12,4 % / −17 % | +7,9 % / −15 % |
| Gegenprobe Zufall 2 | +11,6 % / −15 % | +11,7 % / −18 % | +7,9 % / −15 % |
| Gegenprobe Zufall 3 | +11,9 % / −15 % | +12,2 % / −16 % | +7,9 % / −15 % |
| Gegenprobe Zufall 4 | +11,2 % / −16 % | +12,7 % / −17 % | +8,0 % / −15 % |
| Gegenprobe Zufall 5 | +11,6 % / −16 % | +11,6 % / −18 % | +7,9 % / −15 % |
| Gegenprobe Zufall 6 | +11,3 % / −16 % | +11,9 % / −17 % | +8,5 % / −14 % |

Unterschied in Prozentpunkten: 2010–2014 -0,6, 2015–2021 -0,4, 2022–2026 +0,2

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
