# 🔬 Day-Trader-Skill: Rückkehr über die 20-Tage-Linie als neue Kauf-Strategie

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Kauf-Signal, wenn der Schluss gestern unter seiner 20-Tage-Linie lag und heute darüber. Regel wörtlich aus dem Scanner des Skills (nur Schlusskurse), dazu wie im Skill Kurs mindestens 5 $ und 1 Mio. Stück Umsatz. Kein eigener Trendfilter (der Skill hat keinen), aber wie bei allen Long-Strategien des Bots der Marktfilter. Stop und Ziel wie die Bot-Strategien derselben Art: Stop −3 ATR, Ziel +3 ATR (wie Ausbruch, Rücksetzer usw.). Gegenprobe: gleich viele Käufe je Aktie an zufälligen erlaubten Tagen mit denselben Abständen.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: Rückkehr über die 20-Tage-Linie als neue Kauf-Strategie | +11,6 % / −15 % | +13,4 % / −15 % | +7,1 % / −16 % |
| Gegenprobe Zufall 1 | +14,2 % / −12 % | +12,6 % / −18 % | +8,1 % / −14 % |
| Gegenprobe Zufall 2 | +11,6 % / −17 % | +11,8 % / −17 % | +8,1 % / −15 % |
| Gegenprobe Zufall 3 | +13,7 % / −15 % | +12,2 % / −18 % | +6,0 % / −16 % |
| Gegenprobe Zufall 4 | +13,6 % / −15 % | +11,1 % / −17 % | +6,6 % / −15 % |
| Gegenprobe Zufall 5 | +14,1 % / −12 % | +12,4 % / −18 % | +8,1 % / −16 % |
| Gegenprobe Zufall 6 | +13,3 % / −16 % | +12,9 % / −18 % | +7,6 % / −15 % |

Unterschied in Prozentpunkten: 2010–2014 -1,2, 2015–2021 +0,8, 2022–2026 -0,0

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
