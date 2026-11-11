# 🔬 Day-Trader-Skill: Bullen-Flagge als neue Kauf-Strategie

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Kauf-Signal, wenn der Kurs in den 10 Tagen vor den letzten 5 um mehr als 10 % gestiegen ist und die letzten 5 Schlusskurse in einer Spanne von unter 5 % liegen. Regel wörtlich aus dem Scanner des Skills (nur Schlusskurse), dazu wie im Skill Kurs mindestens 5 $ und 1 Mio. Stück Umsatz. Kein eigener Trendfilter (der Skill hat keinen), aber wie bei allen Long-Strategien des Bots der Marktfilter. Stop und Ziel wie die Bot-Strategien derselben Art: Stop −3 ATR, Ziel +3 ATR (wie Ausbruch, Rücksetzer usw.). Gegenprobe: gleich viele Käufe je Aktie an zufälligen erlaubten Tagen mit denselben Abständen.

**Ergebnis: überall besser, aber nicht besser als Zufall**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: Bullen-Flagge als neue Kauf-Strategie | +14,2 % / −13 % | +13,7 % / −18 % | +7,4 % / −16 % |
| Gegenprobe Zufall 1 | +13,3 % / −14 % | +13,0 % / −18 % | +6,7 % / −17 % |
| Gegenprobe Zufall 2 | +12,5 % / −14 % | +13,7 % / −17 % | +5,8 % / −16 % |
| Gegenprobe Zufall 3 | +13,1 % / −14 % | +11,8 % / −19 % | +6,5 % / −15 % |
| Gegenprobe Zufall 4 | +12,5 % / −13 % | +13,9 % / −16 % | +7,9 % / −16 % |
| Gegenprobe Zufall 5 | +12,5 % / −13 % | +11,7 % / −17 % | +7,1 % / −16 % |
| Gegenprobe Zufall 6 | +12,9 % / −12 % | +12,8 % / −17 % | +7,2 % / −16 % |

Unterschied in Prozentpunkten: 2010–2014 +1,3, 2015–2021 +1,1, 2022–2026 +0,2

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
