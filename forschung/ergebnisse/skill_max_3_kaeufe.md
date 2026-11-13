# 🔬 Day-Trader-Skill: höchstens 3 neue Käufe am Tag

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Wie die Risiko-Prüfung des Skills: An einem Handelstag kauft der Bot höchstens 3 neue Positionen, auch wenn mehr Aufträge möglich wären (die übrigen verfallen wie bei vollem Depot). Sonst alles wie heute. Gegenprobe: ebenfalls höchstens 3, aber in zufälliger statt in der Bot-Reihenfolge ausgewählt.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: höchstens 3 neue Käufe am Tag | +13,8 % / −14 % | +11,7 % / −16 % | +8,6 % / −14 % |
| Gegenprobe Zufall 1 | +8,2 % / −17 % | +12,3 % / −16 % | +11,3 % / −14 % |
| Gegenprobe Zufall 2 | +11,2 % / −16 % | +12,0 % / −17 % | +10,0 % / −15 % |
| Gegenprobe Zufall 3 | +9,8 % / −17 % | +16,0 % / −12 % | +8,7 % / −14 % |
| Gegenprobe Zufall 4 | +10,9 % / −14 % | +13,4 % / −14 % | +9,5 % / −15 % |
| Gegenprobe Zufall 5 | +9,4 % / −17 % | +15,1 % / −16 % | +7,9 % / −16 % |
| Gegenprobe Zufall 6 | +12,2 % / −18 % | +14,9 % / −14 % | +8,2 % / −16 % |

Unterschied in Prozentpunkten: 2010–2014 +0,9, 2015–2021 -1,0, 2022–2026 +1,4

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
