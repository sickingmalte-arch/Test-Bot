# 🔬 Day-Trader-Skill: 20-Tage-Schlusshoch-Ausbruch als neue Kauf-Strategie

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Kauf-Signal, wenn der Schluss über jedem Schluss der 20 Tage davor liegt (ohne Volumen-Bedingung, anders als die Bot-Strategie Ausbruch). Regel wörtlich aus dem Scanner des Skills (nur Schlusskurse), dazu wie im Skill Kurs mindestens 5 $ und 1 Mio. Stück Umsatz. Kein eigener Trendfilter (der Skill hat keinen), aber wie bei allen Long-Strategien des Bots der Marktfilter. Stop und Ziel wie die Bot-Strategien derselben Art: Stop −3 ATR, Ziel +3 ATR (wie Ausbruch, Rücksetzer usw.). Gegenprobe: gleich viele Käufe je Aktie an zufälligen erlaubten Tagen mit denselben Abständen.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: 20-Tage-Schlusshoch-Ausbruch als neue Kauf-Strategie | +11,9 % / −16 % | +12,2 % / −16 % | +7,4 % / −16 % |
| Gegenprobe Zufall 1 | +13,1 % / −16 % | +11,2 % / −17 % | +8,7 % / −15 % |
| Gegenprobe Zufall 2 | +11,3 % / −16 % | +12,0 % / −18 % | +8,2 % / −15 % |
| Gegenprobe Zufall 3 | +10,4 % / −16 % | +13,4 % / −16 % | +6,7 % / −16 % |
| Gegenprobe Zufall 4 | +14,1 % / −14 % | +12,6 % / −17 % | +7,0 % / −16 % |
| Gegenprobe Zufall 5 | +12,7 % / −15 % | +11,1 % / −18 % | +6,6 % / −17 % |
| Gegenprobe Zufall 6 | +11,0 % / −14 % | +12,7 % / −18 % | +7,5 % / −15 % |

Unterschied in Prozentpunkten: 2010–2014 -0,9, 2015–2021 -0,4, 2022–2026 +0,3

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
