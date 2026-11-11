# 🔬 Day-Trader-Skill: Zeitmaschine – nur kaufen, wenn 1.000 Wiederholungen zum Ziel neigen

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Die Zeitmaschine des Skills mit Tageskerzen statt 5-Minuten-Kerzen: Jede der letzten 60 Kerzen wird zu Verhältnissen zum Schluss davor (Eröffnung, Hoch, Tief, Schluss); 1.000 Wiederholungen ziehen für jeden der nächsten 20 Tage zufällig eine davon (Seed 19, Stop vor Ziel am selben Tag). Gekauft wird nur, wenn unter den Wiederholungen, die Stop oder Ziel erreichen, das Ziel mindestens 5 Punkte öfter zuerst kommt, als zum Ausgleich nötig wäre. Gegenprobe: je Aktie gleich viele Signale weglassen, aber zufällig.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +7,1 % / −15 % |
| Day-Trader-Skill: Zeitmaschine – nur kaufen, wenn 1.000 Wiederholungen zum Ziel neigen | +10,3 % / −14 % | +13,6 % / −16 % | +9,5 % / −14 % |
| Gegenprobe Zufall 1 | +14,0 % / −15 % | +12,1 % / −17 % | +8,9 % / −17 % |
| Gegenprobe Zufall 2 | +14,0 % / −12 % | +13,7 % / −17 % | +8,3 % / −15 % |
| Gegenprobe Zufall 3 | +14,2 % / −13 % | +14,6 % / −16 % | +7,1 % / −17 % |
| Gegenprobe Zufall 4 | +9,9 % / −16 % | +12,3 % / −16 % | +7,3 % / −15 % |
| Gegenprobe Zufall 5 | +11,9 % / −14 % | +13,1 % / −16 % | +6,9 % / −18 % |
| Gegenprobe Zufall 6 | +11,1 % / −20 % | +16,1 % / −17 % | +9,9 % / −17 % |

Unterschied in Prozentpunkten: 2010–2014 -2,6, 2015–2021 +0,9, 2022–2026 +2,4

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
