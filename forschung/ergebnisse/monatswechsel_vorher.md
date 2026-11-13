# 🔬 Monatswechsel 1: nur an den letzten 4 Handelstagen des Monats kaufen

Getestet am 13.11.2026 · Quelle: McConnell & Xu (2008), „Equity Returns at the Turn of the Month“, Financial Analysts Journal 64(2), 49–64; zuerst Lakonishok & Smidt (1988). Laut der Studie kam von 1926 bis 2005 fast die ganze Rendite des US-Aktienmarkts am letzten und an den ersten drei Handelstagen eines Monats zustande.

Wie der Bot, aber ein Kauf (zur Eröffnung am Tag nach dem Signal) ist nur an den letzten 4 Handelstagen des Monats erlaubt – so liegt der Monatswechsel (letzter und erste drei Handelstage) in der Haltezeit. Alle anderen Signale fallen weg. Stop, Ziel, Größe und alle übrigen Regeln bleiben gleich. Gegenprobe: je Aktie gleich viele Signale weglassen, aber zufällig.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +11,5 % / −15 % | +12,0 % / −17 % | +8,3 % / −14 % |
| Monatswechsel 1: nur an den letzten 4 Handelstagen des Monats kaufen | +9,7 % / −10 % | +6,9 % / −11 % | +3,1 % / −15 % |
| Gegenprobe Zufall 1 | +7,0 % / −13 % | +8,1 % / −21 % | +4,5 % / −14 % |
| Gegenprobe Zufall 2 | +10,4 % / −10 % | +12,5 % / −11 % | +7,1 % / −13 % |
| Gegenprobe Zufall 3 | +9,6 % / −8 % | +8,0 % / −23 % | +3,9 % / −13 % |
| Gegenprobe Zufall 4 | +12,4 % / −9 % | +12,0 % / −11 % | +4,8 % / −13 % |
| Gegenprobe Zufall 5 | +7,0 % / −16 % | +12,0 % / −14 % | +9,5 % / −11 % |
| Gegenprobe Zufall 6 | +10,7 % / −7 % | +13,6 % / −18 % | +6,8 % / −14 % |

Unterschied in Prozentpunkten: 2010–2014 -1,8, 2015–2021 -5,1, 2022–2026 -5,2

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
