# 🔬 Day-Trader-Skill: Geschichte – nicht kaufen, wenn dieselbe Regel bei dieser Aktie bisher verlor

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Wie „die Geschichte“ der Zeitmaschine: Für jedes Signal zählt der Bot die früheren Signale derselben Strategie bei derselben Aktie, die am Signaltag schon zu Ende waren (Kauf zur nächsten Eröffnung, raus am Stop, am Ziel oder nach 20 Tagen, nach Spread). Hatte diese Regel dort schon mindestens 5 Trades und im Schnitt höchstens 0 R, wird nicht gekauft. Gegenprobe: je Aktie gleich viele Signale weglassen, aber zufällig.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: Geschichte – nicht kaufen, wenn dieselbe Regel bei dieser Aktie bisher verlor | +9,2 % / −16 % | +9,4 % / −17 % | +7,4 % / −17 % |
| Gegenprobe Zufall 1 | +13,9 % / −15 % | +13,0 % / −13 % | +7,8 % / −17 % |
| Gegenprobe Zufall 2 | +12,0 % / −15 % | +11,4 % / −17 % | +7,3 % / −16 % |
| Gegenprobe Zufall 3 | +11,9 % / −14 % | +12,6 % / −21 % | +7,3 % / −17 % |
| Gegenprobe Zufall 4 | +14,5 % / −15 % | +12,7 % / −13 % | +5,9 % / −17 % |
| Gegenprobe Zufall 5 | +14,4 % / −12 % | +11,0 % / −17 % | +7,8 % / −13 % |
| Gegenprobe Zufall 6 | +15,5 % / −14 % | +13,5 % / −15 % | +8,2 % / −14 % |

Unterschied in Prozentpunkten: 2010–2014 -3,6, 2015–2021 -3,2, 2022–2026 +0,3

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
