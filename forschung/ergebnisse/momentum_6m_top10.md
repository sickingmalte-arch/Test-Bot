# 🔬 Momentum: die 10 stärksten Aktien der letzten 6 Monate, monatlich umschichten

Getestet am 05.11.2026 · Quelle: Jegadeesh & Titman (1993); Asness, Moskowitz & Pedersen (2013) „Value and Momentum Everywhere“

Wie Momentum 12 Monate, aber der Anstieg zählt über 6 Monate (ohne den letzten Monat). Liegt der S&P 500 (SPY) am Monatsende unter seiner 200-Tage-Linie, hält das Depot nur Geld. Gegenprobe: 20-mal zufällige 10 Aktien aus denselben Kandidaten.

- **Vermutung:** Diese Monats-Regel bringt in allen drei Zeiträumen mehr Rendite pro Rückgang als der Swing-Bot und ist besser als zufällig gewählte Aktien aus derselben Liste.
- **Widerlegt, wenn:** In einem der drei Zeiträume weniger Rendite pro Rückgang als der Swing-Bot, tiefer gefallen als der Nasdaq-100 beim Halten, oder mehr als 1 von 20 Zufallsdepots gleich gut oder besser.
- **Varianten:** 7, alle vor dem Rechnen am 05.11.2026 festgelegt: Momentum 12 Monate Top 10, Momentum 6 Monate Top 10, Momentum 12 Monate Top 20, Branchen-ETFs Top 3, Nasdaq-100 nur über der 200-Tage-Linie, halb Swing-Bot halb Momentum, geringe Schwankung Top 20. Besteht eine von sieben, bleibt Vorsicht nötig (Glückstreffer).

**Ergebnis: fällt tiefer als der Nasdaq-100 beim Halten**

| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang) | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Swing-Bot (jetzt) | +13,3 % / −14 % (0,95) | +11,9 % / −18 % (0,67) | +7,7 % / −15 % (0,50) |
| **Momentum: die 10 stärksten Aktien der letzten 6 Monate, monatlich umschichten** | +34,1 % / −31 % (1,09) | +33,4 % / −32 % (1,04) | +45,4 % / −40 % (1,13) |
| Zufallsdepots (20×): Spanne der Rendite | +13,6 bis +25,5 % (Mitte +19,7 %) | +2,9 bis +15,9 % (Mitte +10,7 %) | -2,8 bis +17,9 % (Mitte +6,4 %) |
| Nasdaq-100 halten | +22,9 % / −20 % (1,17) | +23,3 % / −31 % (0,76) | +12,8 % / −30 % (0,43) |
| S&P 500 halten | +19,2 % / −21 % (0,93) | +15,8 % / −33 % (0,48) | +11,8 % / −23 % (0,51) |

| Prüfung | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| mehr Rendite pro Rückgang als der Swing-Bot | ✅ | ✅ | ✅ |
| nicht tiefer als Nasdaq halten | ❌ | ❌ | ❌ |
| besser als 19 von 20 Zufallsdepots | ✅ | ✅ | ✅ |

Orders pro Jahr: 2010–2014 147, 2015–2021 150, 2022–2026 139

In Euro, mit Spread (0,1 % je Order) und Gebühr, Entscheidung zum Monatsende, Handel am nächsten Tag zur Eröffnung. Aktienliste von heute (S&P 500 und Nasdaq-100): rückblickend zu gut, deshalb zählt der Vergleich mit Zufall aus derselben Liste. Simulation, keine Anlageberatung.
