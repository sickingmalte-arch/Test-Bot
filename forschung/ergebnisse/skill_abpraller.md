# 🔬 Day-Trader-Skill: Abpraller nach Überverkauft als neue Kauf-Strategie

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Kauf-Signal, wenn der RSI 14 gestern unter 30 lag und der Schluss heute über dem von gestern liegt. Regel wörtlich aus dem Scanner des Skills (nur Schlusskurse), dazu wie im Skill Kurs mindestens 5 $ und 1 Mio. Stück Umsatz. Kein eigener Trendfilter (der Skill hat keinen), aber wie bei allen Long-Strategien des Bots der Marktfilter. Stop und Ziel wie die Bot-Strategien derselben Art: Stop −2,5 ATR, Ziel +2 ATR (wie Gegenbewegung und RSI-2). Gegenprobe: gleich viele Käufe je Aktie an zufälligen erlaubten Tagen mit denselben Abständen.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: Abpraller nach Überverkauft als neue Kauf-Strategie | +13,2 % / −13 % | +12,1 % / −16 % | +7,1 % / −15 % |
| Gegenprobe Zufall 1 | +12,9 % / −13 % | +12,4 % / −17 % | +7,3 % / −16 % |
| Gegenprobe Zufall 2 | +13,0 % / −14 % | +11,8 % / −16 % | +7,1 % / −15 % |
| Gegenprobe Zufall 3 | +12,8 % / −13 % | +11,8 % / −17 % | +7,8 % / −14 % |
| Gegenprobe Zufall 4 | +11,6 % / −13 % | +12,2 % / −16 % | +8,8 % / −15 % |
| Gegenprobe Zufall 5 | +12,9 % / −13 % | +11,7 % / −17 % | +8,2 % / −16 % |
| Gegenprobe Zufall 6 | +12,8 % / −13 % | +11,9 % / −17 % | +8,3 % / −15 % |

Unterschied in Prozentpunkten: 2010–2014 +0,3, 2015–2021 -0,6, 2022–2026 +0,0

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
