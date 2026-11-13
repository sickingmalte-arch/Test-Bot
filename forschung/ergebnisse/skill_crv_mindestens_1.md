# 🔬 Day-Trader-Skill: nur Käufe mit Chance-Risiko (CRV) mindestens 1,0

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Wie die Risiko-Prüfung des Skills: Signale mit einem CRV unter 1,0 (Ziel näher als der Stop) kauft der Bot nicht. Beim Bot betrifft das die Gegenbewegungs-Strategien (Stop 2,5 ATR, Ziel 2 ATR = CRV 0,8: RSI-2-Rücksetzer und Gegenbewegung). Gegenprobe: je Aktie gleich viele Signale weglassen, aber zufällig aus allen Strategien.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: nur Käufe mit Chance-Risiko (CRV) mindestens 1,0 | +10,7 % / −13 % | +12,8 % / −15 % | +7,0 % / −17 % |
| Gegenprobe Zufall 1 | +13,6 % / −16 % | +13,8 % / −17 % | +6,9 % / −16 % |
| Gegenprobe Zufall 2 | +11,0 % / −15 % | +12,3 % / −16 % | +9,1 % / −15 % |
| Gegenprobe Zufall 3 | +11,7 % / −17 % | +11,0 % / −19 % | +7,0 % / −16 % |
| Gegenprobe Zufall 4 | +11,7 % / −17 % | +12,3 % / −17 % | +8,5 % / −16 % |
| Gegenprobe Zufall 5 | +13,2 % / −12 % | +9,6 % / −18 % | +8,3 % / −12 % |
| Gegenprobe Zufall 6 | +12,8 % / −13 % | +11,8 % / −16 % | +9,4 % / −13 % |

Unterschied in Prozentpunkten: 2010–2014 -2,2, 2015–2021 +0,2, 2022–2026 -0,1

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
