# 🔬 Zinsen auf das freie Geld (Messung)

Getestet am 24.11.2026 · Quelle: Europäische Zentralbank, Einlagesatz (Data Portal, Reihe FM.D.U2.EUR.4F.KR.DFR.LEV) – viele Broker zahlen heute Zinsen nahe an diesem Satz auf das Geld im Konto.

Keine neue Kaufregel: Der Bot handelt wie immer (Watchlist, mit Gebühr und Spread). Gemessen wird nur, was es bringt, wenn das Geld, das am Vorabend nicht in Aktien steckt, Zinsen bekommt. Angenommen: Einlagesatz der EZB minus 0,5 Punkte, nie unter 0 % (vorsichtig; 2015–2021 also 0 %). Zinsen Tag für Tag nach Kalendertagen, mit Zinseszins. Zur Info auch der volle Einlagesatz (nie unter 0 %).

- **Vermutung:** Oft steckt nur gut die Hälfte des Geldes in Aktien. Zinsen auf den Rest heben die Rendite ohne mehr Rückgang – in den Jahren mit hohen Zinsen (2022–2026) um mehr als 0,5 Punkte im Jahr.
- **Widerlegt, wenn:** In einem Zeitraum weniger Rendite oder mehr Rückgang als der jetzige Bot, oder 2022–2026 weniger als 0,5 Punkte mehr Rendite im Jahr.
- **Varianten:** 1 Messung mit fester Annahme (Einlagesatz minus 0,5 Punkte, nie unter 0 %), vor dem Rechnen festgelegt; der volle Satz nur zur Info. Keine Gegenprobe nötig: Zinsen wählen keine Aktien aus.

**Ergebnis: Vermutung bestätigt: +0,0 / +0,0 / +0,9 Punkte pro Jahr**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot (freies Geld ohne Zinsen) | +11,6 % / −14 % | +11,9 % / −16 % | +7,3 % / −15 % |
| … freies Geld im Schnitt (Anteil am Depot) | 37 % | 40 % | 60 % |
| **Mit Zinsen: Einlagesatz − 0,5 Punkte** | +11,6 % / −14 % | +11,9 % / −16 % | +8,2 % / −14 % |
| … Zinssatz im Schnitt · Unterschied zum Bot (Punkte pro Jahr) | 0,02 % · +0,01 | 0,00 % · +0,00 | 1,93 % · +0,93 |
| Mit dem vollen Einlagesatz (zur Info) | +11,6 % / −14 % | +11,9 % / −16 % | +8,4 % / −14 % |
| … Zinssatz im Schnitt · Unterschied zum Bot (Punkte pro Jahr) | 0,18 % · +0,06 | 0,00 % · +0,00 | 2,36 % · +1,16 |

Daten: Zinsen – Einlagesatz der EZB (Data Portal). Watchlist mit 24 Aktien, Mittel aus 8 Läufen, mit Gebühr und Spread. Ohne Steuern (wie überall im Bot). Gezählt wird das Geld, das am Vorabend nicht in Aktien steckt; die Zinsen selbst verzinsen sich mit. Simulation mit Spielgeld, keine Anlageberatung.
