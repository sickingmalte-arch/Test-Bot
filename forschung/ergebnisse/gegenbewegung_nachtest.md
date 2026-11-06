# 🔬 Nachtest Gegenbewegung: auf neuen Zufallslisten besser als Zufallskäufe? Und ein Bot nur mit ihr?

Getestet am 06.11.2026 · Ehrlicher Check 2 vom 06.11.2026 (einzige Strategie mit Vorteil gegen Zufallskäufe)

Zu Beginn jedes Zeitraums 8 neue Zufallslisten mit je 24 Aktien, die damals im S&P 500 waren (andere Ziehungen als im Check 2). Mit jeder Liste: der volle Bot und ein Bot, der nur „Gegenbewegung ↑“ handelt (RSI 14 unter 32 oder am unteren Bollinger-Band, über der 200-Tage-Linie, mindestens 1,2 ATR unter der EMA 20; Stop −2,5 ATR, Ziel +2 ATR). Dazu der Schnitt ihrer gedachten Trades gegen zufällige Käufe mit denselben Abständen.

- **Vermutung:** Gegenbewegung schlägt auch auf neuen Aktien in allen drei Zeiträumen zufällige Käufe, und ein Bot nur mit ihr hat mehr Rendite pro Rückgang als der volle Bot.
- **Widerlegt, wenn:** Gegenbewegung liegt in einem Zeitraum nicht über dem Zufall mit Gegen-Ausstieg (je mindestens 30 Trades), oder der Bot nur mit ihr hat in einem Zeitraum (Mitte der 8 Listen) nicht mehr Rendite pro Rückgang als der volle Bot.
- **Varianten:** 1 Strategie, 1 Nachtest – vor dem Rechnen festgelegt.

**Ergebnis:** Gegenbewegung gegen Zufallskäufe auf neuen Listen: besteht; Bot nur mit Gegenbewegung besser als der volle Bot: nein

| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang), Mitte aus 8 neuen Listen | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Voller Bot (9 Strategien) | +12,7 % / −16 % (0,78) | +4,7 % / −18 % (0,27) | +2,5 % / −15 % (0,16) |
| **Bot nur mit Gegenbewegung** | +3,4 % / −12 % (0,29) | +1,5 % / −17 % (0,09) | -1,1 % / −11 % (-0,11) |
| S&P 500 halten | +19,2 % / −21 % (0,93) | +15,8 % / −33 % (0,48) | +12,1 % / −23 % (0,53) |
| Trades pro Jahr (voll / nur Gegenbewegung) | 129 / 42 | 119 / 38 | 98 / 24 |

| Gedachte Trades (Ø R nach Kosten) | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Gegenbewegung ↑ | +0,11 R (2175) | +0,10 R (2531) | -0,03 R (1275) |
| 🎲 Zufall mit Gegen-Ausstieg | +0,09 R (3919) | +0,06 R (4871) | -0,04 R (2926) |
| 🎲 Zufall mit Trend-Ausstieg | +0,13 R (3236) | +0,07 R (4260) | -0,02 R (2590) |

Neue Zufallslisten (andere Aktien als im Check 2). Verbleibende Verzerrung: Aktien, die seitdem aus dem Index geflogen sind, fehlen. Simulation, keine Anlageberatung.
