# 🔬 Krisen-Absicherung 1: Nasdaq-100-Short über 50 % nur bei VIX über 30 und Nasdaq unter der 200-Tage-Linie

Getestet am 17.11.2026 · Quelle: Whaley (2000), „The Investor Fear Gauge“, Journal of Portfolio Management 26(3) – der VIX steigt in Krisen; Faber (2007), „A Quantitative Approach to Tactical Asset Allocation“ – Trend über die 200-Tage-Linie. Frühere eigene Messung (Was der Bot schon weiß): QQQ-Short schon unter der 200-Tage-Linie allein half nicht.

Der Bot handelt ganz normal. Dazu kommt ein Nasdaq-100-Short (QQQ) über 50 % des Depotwerts – aber nur an Tagen, an denen am Abend vorher der Angst-Index VIX über 30 schloss und der Nasdaq-100 unter seiner 200-Tage-Linie lag, also in echten Krisen. 0,1 % Spread bei Ein- und Ausstieg, 0,5 % Leihgebühr pro Jahr. Gegenprobe: gleich viele Short-Tage in gleich langen Blöcken an zufälligen Stellen.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +11,0 % / −17 % | +10,9 % / −17 % | +8,1 % / −15 % |
| Krisen-Absicherung 1: Nasdaq-100-Short über 50 % nur bei VIX über 30 und Nasdaq unter der 200-Tage-Linie | +9,3 % / −19 % | +8,8 % / −22 % | +6,0 % / −17 % |
| Gegenprobe Zufall 1 | +10,0 % / −17 % | +11,0 % / −17 % | +8,3 % / −15 % |
| Gegenprobe Zufall 2 | +9,7 % / −18 % | +10,5 % / −17 % | +8,1 % / −15 % |
| Gegenprobe Zufall 3 | +9,7 % / −18 % | +11,4 % / −17 % | +7,6 % / −15 % |
| Gegenprobe Zufall 4 | +10,6 % / −18 % | +10,5 % / −17 % | +6,3 % / −14 % |
| Gegenprobe Zufall 5 | +10,4 % / −18 % | +10,6 % / −17 % | +6,4 % / −15 % |
| Gegenprobe Zufall 6 | +11,1 % / −17 % | +10,8 % / −17 % | +7,9 % / −13 % |

Unterschied in Prozentpunkten: 2010–2014 -1,8, 2015–2021 -2,2, 2022–2026 -2,1

Watchlist, mit Gebühr und Spread, erster Lauf je Zeitraum, Short auf den Wertverlauf gerechnet. Simulation, keine Anlageberatung.

Tage mit Krisen-Short: 2010–2014 61, 2015–2021 28, 2022–2026 62
