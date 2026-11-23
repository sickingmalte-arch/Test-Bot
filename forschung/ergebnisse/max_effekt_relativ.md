# 🔬 MAX-Effekt 2: kein Kauf nach einem Tagesplus von 3 ATR oder mehr im letzten Monat

Getestet am 23.11.2026 · Quelle: Bali, Cakici & Whitelaw (2011), „Maxing Out: Stocks as Lotteries and the Cross-Section of Expected Returns“, Journal of Financial Economics 99(2), 427–446; Gegenstimme: Gorman, Akhtar, Durand & Gould (2022), Critical Finance Review (eher Übertreibung als Lotto-Lust).

Wie der Bot, aber ein Kauf-Signal fällt weg, wenn die Aktie in den letzten 21 Börsentagen (bis zum Signaltag) an einem Tag um mindestens 3 ATR gestiegen ist – gemessen an ihrer eigenen üblichen Schwankung ein extremer Sprung. Stop, Ziel, Größe und alle übrigen Regeln bleiben gleich. Gegenprobe: je Aktie gleich viele Signale weglassen, aber zufällig.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +11,6 % / −14 % | +11,9 % / −16 % | +7,3 % / −15 % |
| MAX-Effekt 2: kein Kauf nach einem Tagesplus von 3 ATR oder mehr im letzten Monat | +10,3 % / −14 % | +13,1 % / −17 % | +6,6 % / −15 % |
| Gegenprobe Zufall 1 | +11,4 % / −14 % | +13,6 % / −17 % | +7,3 % / −15 % |
| Gegenprobe Zufall 2 | +10,5 % / −15 % | +11,7 % / −15 % | +9,1 % / −14 % |
| Gegenprobe Zufall 3 | +12,9 % / −15 % | +14,0 % / −15 % | +8,5 % / −15 % |
| Gegenprobe Zufall 4 | +11,4 % / −15 % | +12,0 % / −19 % | +6,3 % / −15 % |
| Gegenprobe Zufall 5 | +11,4 % / −16 % | +10,7 % / −15 % | +5,8 % / −16 % |
| Gegenprobe Zufall 6 | +12,1 % / −14 % | +13,4 % / −15 % | +5,7 % / −17 % |

Unterschied in Prozentpunkten: 2010–2014 -1,2, 2015–2021 +1,1, 2022–2026 -0,7

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
