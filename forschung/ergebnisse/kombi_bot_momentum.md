# 🔬 Kombi: halb Swing-Bot, halb Momentum (10 stärkste Aktien, 12 Monate)

Getestet am 05.11.2026 · Quelle: Jegadeesh & Titman (1993); Asness, Moskowitz & Pedersen (2013) „Value and Momentum Everywhere“

Das Startgeld liegt zur Hälfte im jetzigen Swing-Bot und zur Hälfte im Momentum-Depot (10 Aktien, 12 Monate, monatlich, mit Marktfilter), ohne Umschichten zwischen beiden. Idee: zwei verschiedene Strategien schwanken nicht gleichzeitig, der Rückgang wird kleiner. Gegenprobe: halb Swing-Bot, halb zufällige 10 Aktien.

- **Vermutung:** Diese Monats-Regel bringt in allen drei Zeiträumen mehr Rendite pro Rückgang als der Swing-Bot und ist besser als zufällig gewählte Aktien aus derselben Liste.
- **Widerlegt, wenn:** In einem der drei Zeiträume weniger Rendite pro Rückgang als der Swing-Bot, tiefer gefallen als der Nasdaq-100 beim Halten, oder mehr als 1 von 20 Zufallsdepots gleich gut oder besser.
- **Varianten:** 7, alle vor dem Rechnen am 05.11.2026 festgelegt: Momentum 12 Monate Top 10, Momentum 6 Monate Top 10, Momentum 12 Monate Top 20, Branchen-ETFs Top 3, Nasdaq-100 nur über der 200-Tage-Linie, halb Swing-Bot halb Momentum, geringe Schwankung Top 20. Besteht eine von sieben, bleibt Vorsicht nötig (Glückstreffer).

**Ergebnis: fällt tiefer als der Nasdaq-100 beim Halten**

| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang) | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Swing-Bot (jetzt) | +13,3 % / −14 % (0,95) | +11,9 % / −18 % (0,67) | +7,7 % / −15 % (0,50) |
| **Kombi: halb Swing-Bot, halb Momentum (10 stärkste Aktien, 12 Monate)** | +28,2 % / −19 % (1,50) | +19,8 % / −25 % (0,80) | +32,1 % / −33 % (0,96) |
| Zufallsdepots (20×): Spanne der Rendite | +14,7 bis +18,9 % (Mitte +16,8 %) | +9,4 bis +13,1 % (Mitte +11,0 %) | +2,8 bis +11,4 % (Mitte +5,9 %) |
| Nasdaq-100 halten | +22,9 % / −20 % (1,17) | +23,3 % / −31 % (0,76) | +12,8 % / −30 % (0,43) |
| S&P 500 halten | +19,2 % / −21 % (0,93) | +15,8 % / −33 % (0,48) | +11,8 % / −23 % (0,51) |

| Prüfung | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| mehr Rendite pro Rückgang als der Swing-Bot | ✅ | ✅ | ✅ |
| nicht tiefer als Nasdaq halten | ✅ | ✅ | ❌ |
| besser als 19 von 20 Zufallsdepots | ✅ | ✅ | ✅ |

Orders pro Jahr: 2010–2014 130, 2015–2021 134, 2022–2026 123

In Euro, mit Spread (0,1 % je Order) und Gebühr, Entscheidung zum Monatsende, Handel am nächsten Tag zur Eröffnung. Aktienliste von heute (S&P 500 und Nasdaq-100): rückblickend zu gut, deshalb zählt der Vergleich mit Zufall aus derselben Liste. Simulation, keine Anlageberatung.
