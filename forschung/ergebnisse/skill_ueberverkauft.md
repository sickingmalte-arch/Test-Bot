# 🔬 Day-Trader-Skill: Überverkauft (RSI 14 unter 30) als neue Kauf-Strategie

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Kauf-Signal, solange der RSI 14 (Wilder) unter 30 liegt. Regel wörtlich aus dem Scanner des Skills (nur Schlusskurse), dazu wie im Skill Kurs mindestens 5 $ und 1 Mio. Stück Umsatz. Kein eigener Trendfilter (der Skill hat keinen), aber wie bei allen Long-Strategien des Bots der Marktfilter. Stop und Ziel wie die Bot-Strategien derselben Art: Stop −2,5 ATR, Ziel +2 ATR (wie Gegenbewegung und RSI-2). Gegenprobe: gleich viele Käufe je Aktie an zufälligen erlaubten Tagen mit denselben Abständen.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: Überverkauft (RSI 14 unter 30) als neue Kauf-Strategie | +12,8 % / −13 % | +13,3 % / −17 % | +8,0 % / −15 % |
| Gegenprobe Zufall 1 | +13,1 % / −13 % | +13,1 % / −17 % | +8,2 % / −15 % |
| Gegenprobe Zufall 2 | +13,7 % / −13 % | +11,0 % / −18 % | +7,5 % / −16 % |
| Gegenprobe Zufall 3 | +12,5 % / −13 % | +10,5 % / −17 % | +7,8 % / −15 % |
| Gegenprobe Zufall 4 | +14,2 % / −13 % | +12,6 % / −17 % | +8,2 % / −15 % |
| Gegenprobe Zufall 5 | +13,4 % / −13 % | +12,6 % / −17 % | +8,7 % / −15 % |
| Gegenprobe Zufall 6 | +12,5 % / −12 % | +11,2 % / −16 % | +8,8 % / −15 % |

Unterschied in Prozentpunkten: 2010–2014 -0,1, 2015–2021 +0,6, 2022–2026 +0,9

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
