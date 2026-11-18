# 🔬 Optionen 1: Put-Verkauf mit dem freien Geld (S&P 500, wie der CBOE-PutWrite-Index)

Getestet am 18.11.2026 · Quelle: Whaley (2002), „Return and Risk of CBOE Buy Write Monthly Index“, Journal of Derivatives 10; Ungar & Moran (2009), „The Cash-Secured PutWrite Strategy and Performance of Related Benchmark Indexes“, Journal of Alternative Investments 11 – verkaufte Index-Puts brachten etwa so viel wie der S&P 500 bei weniger Schwankung (eine Art Versicherungsprämie).

Der Bot handelt wie immer. Mit dem Geld, das am Vorabend nicht in Aktien steckt (oft über die Hälfte), verkauft er Puts auf den S&P 500 – voll mit Geld gedeckt und jeden Monat neu, so wie der CBOE-PutWrite-Index (echte Börsendaten; nur wenn sie fehlen, eigene Rechnung mit dem VIX). Abzüglich 1 % Kosten im Jahr für Spreads und Gebühren. Zum Vergleich: dasselbe freie Geld nur verzinst (US-Geldmarkt) und im S&P 500. Wie bei den anderen Tests auf 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum.

- **Vermutung:** Verkaufte Puts verdienen eine Versicherungsprämie. Mit dem freien Geld bringt das in allen drei Zeiträumen mehr Rendite als der Bot allein und mehr als dasselbe Geld nur verzinst, bei höchstens 1 Punkt mehr Rückgang.
- **Widerlegt, wenn:** In einem Zeitraum: Mitte der 8 Listen nicht besser als der Bot allein, weniger als 6 von 8 Listen besser, mehr als 1 Punkt mehr Rückgang (Mitte) oder nicht mehr Rendite (Mitte) als das freie Geld nur verzinst.
- **Varianten:** 2, vor dem Rechnen festgelegt: Puts über 100 % bzw. 50 % des freien Geldes (der Rest verzinst); Kosten 1 % im Jahr fest.

**Ergebnis: Puts mit 100 % des freien Geldes: nicht überall besser als der Bot allein; Puts mit 50 % des freien Geldes, Rest verzinst: nicht überall besser als der Bot allein**

Je Zeitraum 8 Zufallslisten mit je 24 Aktien aus dem damaligen S&P 500 (zur Wahl standen 2010–2014: 266, 2015–2021: 303, 2022–2026: 411 Aktien). Werte: Mitte (Median) der 8 Listen, Rendite pro Jahr / größter Rückgang.

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot allein, freies Geld ohne Zins (wie heute) | +11,4 % / −16 % | +4,5 % / −19 % | +2,9 % / −14 % |
| … freies Geld im Schnitt (Anteil am Depot) | 25 % | 35 % | 46 % |
| Freies Geld nur verzinst (Vergleich) | +11,4 % / −16 % | +4,7 % / −19 % | +4,4 % / −12 % |
| **Puts mit 100 % des freien Geldes** | +14,9 % / −21 % | +7,4 % / −31 % | +5,3 % / −20 % |
| … Unterschied zum Bot allein (Mitte, Punkte) · Listen besser · gegen „nur verzinst“ | +3,5 · 8 von 8 · +3,5 | +3,0 · 8 von 8 · +2,7 | +2,4 · 8 von 8 · +0,9 |
| **Puts mit 50 % des freien Geldes, Rest verzinst** | +13,1 % / −18 % | +6,4 % / −22 % | +5,0 % / −15 % |
| … Unterschied zum Bot allein (Mitte, Punkte) · Listen besser · gegen „nur verzinst“ | +1,7 · 8 von 8 · +1,7 | +2,0 · 8 von 8 · +1,7 | +2,1 · 8 von 8 · +0,6 |
| Freies Geld im S&P 500 (zur Info) | +17,7 % / −21 % | +13,3 % / −34 % | +6,9 % / −26 % |

**Urteile:**

- **Puts mit 100 % des freien Geldes:** nicht überall besser als der Bot allein
- **Puts mit 50 % des freien Geldes, Rest verzinst:** nicht überall besser als der Bot allein

Daten: PutWrite – CBOE-PutWrite-Index (^PUT, Yahoo) (ab 2007-01-03); Zins – 13-Wochen-T-Bill (^IRX). Zins und Prämien in Dollar gerechnet und auf das freie Geld in Euro angewandt (Wechselkurs außen vor). Im echten Konto bräuchte man dafür ein Margin-Konto, weil dasselbe Geld zugleich für neue Aktienkäufe bereitsteht. Pleitefirmen fehlen in den Listen. Simulation mit Spielgeld, keine Anlageberatung.
