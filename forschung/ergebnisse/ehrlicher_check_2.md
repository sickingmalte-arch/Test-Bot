# 🔬 Ehrlicher Check 2: Watchlist nach Regel, halb Bot halb S&P 500, echte Stärke der Strategien

Getestet am 06.11.2026 · Folge des ehrlichen Bot-Checks vom 06.11.2026

Zu Beginn jedes Zeitraums (2010, 2015, 2022) stehen nur Aktien zur Wahl, die an diesem Tag im S&P 500 waren. Der unveränderte Swing-Bot handelt mit 8 Zufallslisten (wie im ersten Check) und mit zwei Regel-Listen: die 24 meistgehandelten und die 24 stärksten Aktien. Dazu: halb Bot, halb S&P 500 halten, und für jede Strategie der Schnitt ihrer gedachten Trades (Strategie-Tagebuch) auf den Zufallslisten.

- **Vermutung:** (1) Eine feste Regel für die Watchlist schlägt Zufallslisten. (2) Halb Bot, halb S&P 500 hat mehr Rendite pro Rückgang als jedes allein. (3) Mindestens eine Strategie hat auf damaligen Aktien einen echten Vorteil.
- **Widerlegt, wenn:** (1) Die Regel-Liste bringt nicht in allen drei Zeiträumen mehr Rendite als 7 von 8 Zufallslisten. (2) Die Mischung (Mitte der Zufallslisten) hat nicht in allen drei Zeiträumen mehr Rendite pro Rückgang als der S&P 500 allein und als der Bot allein. (3) Keine Strategie hat in allen drei Zeiträumen (je mindestens 30 Trades) einen höheren Schnitt als zufällige Käufe mit denselben Stop- und Zielabständen.
- **Varianten:** 2 Regel-Listen (Umsatz, Stärke), 1 Mischung (50/50), 9 Kauf-Strategien – alles vor dem Rechnen festgelegt. Bei 9 Strategien kann eine zufällig über 0 liegen – deshalb alle drei Zeiträume.

**Ergebnis:** Watchlist nach Umsatz: besteht nicht; Watchlist nach Stärke: besteht nicht; halb Bot, halb S&P 500: besteht nicht; Strategien mit echtem Vorteil: gegenbewegung_long

## 1. Watchlist nach fester Regel

| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang) | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot mit der heutigen Watchlist (Rückblick!) | +12,9 % / −13 % (1,00) | +12,6 % / −17 % (0,75) | +8,3 % / −15 % (0,56) |
| Bot mit 24 zufälligen damaligen Aktien (Mitte aus 8) | +12,3 % / −16 % (0,78) | +4,4 % / −18 % (0,24) | +3,1 % / −14 % (0,22) |
| … Spanne der 8 Zufallslisten | +7,9 bis +13,5 % | +1,6 bis +8,0 % | -0,3 bis +8,9 % |
| **Bot mit den 24 meistgehandelten** | +10,3 % / −18 % (0,56) | +3,3 % / −22 % (0,15) | +4,0 % / −15 % (0,26) |
| **Bot mit den 24 stärksten (12 Monate)** | +6,2 % / −20 % (0,30) | +2,8 % / −20 % (0,14) | +4,0 % / −15 % (0,27) |
| S&P 500 halten | +19,2 % / −21 % (0,93) | +15,8 % / −33 % (0,48) | +12,1 % / −23 % (0,53) |
| Nasdaq-100 halten | +22,9 % / −20 % (1,17) | +23,3 % / −31 % (0,76) | +13,0 % / −30 % (0,43) |

Regel-Listen am Start: Umsatz 2010: AAPL, AIG, AMZN, BAC, C, CSCO, FCX, GE, GOOGL, GS, HPQ, IBM, INTC, JNJ, JPM, MSFT, ORCL, PFE, PG, QCOM, V, WFC, WMT, XOM · Umsatz 2015: AAPL, AMZN, BAC, BKNG, BRK-B, C, CMCSA, CVX, DIS, GE, GILD, GOOG, GOOGL, HAL, INTC, JNJ, JPM, MSFT, MU, NFLX, SLB, V, WFC, XOM · Umsatz 2022: AAPL, ADBE, AMD, AMZN, BA, BAC, CRM, DIS, F, GOOG, GOOGL, INTC, JPM, MA, MRNA, MSFT, MU, NFLX, NVDA, PFE, PYPL, QCOM, TSLA, V · Stärke 2010: AAPL, AMD, AMZN, AXP, BKNG, CBRE, CI, CRM, CTSH, DD, EXPE, F, FCX, GOOGL, GS, IP, ISRG, JBL, MS, MU, NTAP, SBUX, TER, WDC · Stärke 2015: AAPL, AMGN, AVGO, DAL, EIX, ESS, EW, FFIV, GD, HPQ, INTC, IRM, KDP, KR, LRCX, LUV, MAR, MNST, MU, ORLY, RCL, REGN, VRTX, WELL · Stärke 2022: ALB, AMAT, ANET, APA, COP, DVN, EOG, EXR, F, FANG, FTNT, GNRC, INTU, IT, JCI, MAA, MRNA, NUE, NVDA, ODFL, OKE, OXY, SPG, STX

## 2. Halb Bot, halb S&P 500 halten

| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang) | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot allein (Zufallslisten, Mitte) | +12,3 % / −16 % (0,78) | +4,4 % / −18 % (0,24) | +3,1 % / −14 % (0,22) |
| S&P 500 allein | +19,2 % / −21 % (0,93) | +15,8 % / −33 % (0,48) | +12,1 % / −23 % (0,53) |
| **Halb Bot (Zufallslisten), halb S&P 500 (Mitte)** | +15,4 % / −17 % (0,89) | +11,3 % / −26 % (0,44) | +8,0 % / −17 % (0,48) |
| Halb Bot (meistgehandelte), halb S&P 500 | +15,5 % / −19 % (0,83) | +10,3 % / −25 % (0,42) | +7,5 % / −18 % (0,43) |

## 3. Strategien auf zufälligen damaligen Aktien (gedachte Trades, Ø R nach Kosten)

Vergleich: „Zufall (trend)“ und „Zufall (gegen)“ kaufen an zufälligen Tagen mit denselben Stop- und Zielabständen. Echter Vorteil = in allen drei Zeiträumen mehr als der passende Zufall (je mindestens 30 Trades).

| Strategie | 2010–2014 | 2015–2021 | 2022–2026 | echter Vorteil? |
|---|---:|---:|---:|---|
| Gegenbewegung ↑ | +0,13 R (2158) | +0,12 R (2549) | +0,05 R (1293) | ✅ |
| Trendlinien-Ausbruch ↑ | +0,11 R (2383) | +0,07 R (3012) | +0,05 R (1586) | – |
| EMA-Kreuz ↑ | +0,11 R (3144) | +0,04 R (4190) | +0,06 R (2301) | – |
| MACD-Wende ↑ | +0,09 R (4283) | +0,04 R (5478) | +0,06 R (2835) | – |
| Rücksetzer ↑ | +0,08 R (6381) | +0,06 R (8269) | +0,03 R (4402) | – |
| RSI-2-Rücksetzer ↑ | +0,09 R (5898) | +0,04 R (7062) | +0,04 R (3876) | – |
| Squeeze-Ausbruch ↑ | +0,06 R (2477) | +0,04 R (2914) | +0,06 R (1565) | – |
| ATR-Ausbruch ↑ | +0,08 R (4530) | +0,04 R (5362) | +0,05 R (3081) | – |
| 🎲 Zufall mit Trend-Ausstieg (±3 ATR) | +0,12 R (3173) | +0,06 R (4116) | -0,03 R (2567) | Vergleich |
| 🎲 Zufall mit Gegen-Ausstieg (−2,5 / +2 ATR) | +0,09 R (3819) | +0,05 R (4739) | -0,01 R (2918) | Vergleich |
| Ausbruch ↑ | +0,05 R (2984) | +0,02 R (3509) | +0,05 R (1853) | – |

In Klammern: Zahl der gedachten Trades über alle 8 Zufallslisten. Verbleibende Verzerrung: Aktien, die seitdem aus dem Index geflogen sind, haben meist keine Kurse mehr und fehlen – eher noch etwas zu gut. Simulation, keine Anlageberatung.
