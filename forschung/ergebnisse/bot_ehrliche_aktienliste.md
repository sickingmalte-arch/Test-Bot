# 🔬 Ehrlicher Bot-Check: Swing-Bot mit zufälligen Aktien aus dem damaligen S&P 500 statt der heutigen Watchlist

Getestet am 06.11.2026 · Nacht-Forschung 05.11.2026 (Verzerrung durch die heutige Aktienliste)

Zu Beginn jedes Zeitraums (2010, 2015, 2022) zieht der Test 8-mal zufällig so viele Aktien, wie die Watchlist hat, aus allen Aktien, die an diesem Tag im S&P 500 waren (Liste github.com/fja05680/sp500) und genug Kurse haben. Mit jeder Liste handelt der unveränderte Swing-Bot den ganzen Zeitraum, mit Spread und Gebühr. Zum Vergleich: dieselben Aktien einfach zu gleichen Teilen halten (monatlich ausgeglichen), die heutige Watchlist halten, S&P 500 und Nasdaq-100 halten.

- **Vermutung:** Mit Aktien, die man damals ohne Rückblick hätte wählen können, bringt der Swing-Bot deutlich weniger als mit der heutigen Watchlist.
- **Widerlegt, wenn:** Der Bot liegt mit den zufälligen damaligen Listen im Mittel (Median) in allen drei Zeiträumen höchstens 1 Punkt pro Jahr unter seinem Ergebnis mit der heutigen Watchlist.
- **Varianten:** 1 Messung, je Zeitraum 8 zufällige Listen. Keine Regeländerung, nichts wird übernommen.

**Ergebnis: Vermutung bestätigt: mit damaligen Aktien bringt der Bot weniger (-1,7 / -8,7 / -4,8 Punkte pro Jahr)**

| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang) | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Swing-Bot mit der heutigen Watchlist | +13,3 % / −14 % (0,95) | +11,9 % / −18 % (0,67) | +8,1 % / −15 % (0,53) |
| **Swing-Bot mit 24 zufälligen damaligen S&P-500-Aktien (Mitte aus 8 Listen)** | +11,6 % / −16 % (0,73) | +3,2 % / −19 % (0,17) | +3,3 % / −15 % (0,22) |
| … Spanne der Rendite | +7,4 bis +13,1 % | +1,5 bis +7,0 % | -0,4 bis +8,8 % |
| Dieselben zufälligen Aktien einfach halten (Mitte) | +22,8 % / −22 % (1,03) | +16,2 % / −38 % (0,43) | +10,9 % / −21 % (0,53) |
| Heutige Watchlist einfach halten (19 US-Aktien) | +28,5 % / −20 % (1,40) | +42,8 % / −32 % (1,33) | +27,7 % / −32 % (0,88) |
| S&P 500 halten | +19,2 % / −21 % (0,93) | +15,8 % / −33 % (0,48) | +12,1 % / −23 % (0,53) |
| Nasdaq-100 halten | +22,9 % / −20 % (1,17) | +23,3 % / −31 % (0,76) | +13,0 % / −30 % (0,43) |

| Bot-Kennzahlen | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Treffer heutige Watchlist / damalige Listen | 58 % / 58 % | 59 % / 55 % | 58 % / 53 % |
| Schnitt je Trade in R (heutige / damalige) | +0,15 / +0,14 | +0,13 / +0,04 | +0,10 / +0,05 |
| Trades pro Jahr (heutige / damalige) | 120 / 126 | 128 / 115 | 106 / 99 |
| Aktien im S&P 500 mit Kursen zum Start (Auswahl) | 266 | 303 | 411 |

Verbleibende Verzerrung: Aktien, die seitdem aus dem Index geflogen sind, haben meist keine Kurse mehr und fehlen in der Auswahl – auch dieses Ergebnis ist eher noch etwas zu gut. Simulation, keine Anlageberatung.
