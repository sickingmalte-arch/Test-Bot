# 🔬 Optionen 2: Gedeckter Call am Kursziel

Getestet am 18.11.2026 · Quelle: Whaley (2002), „Return and Risk of CBOE Buy Write Monthly Index“, Journal of Derivatives 10; Israelov & Nielsen (2014), „Covered Call Strategies: One Fact and Eight Myths“, Financial Analysts Journal 70 – gedeckte Calls verdienen eine Prämie, geben dafür starke Anstiege ab.

Zu jedem Kauf verkauft der Bot einen Call je Aktie mit Basispreis genau am Kursziel, fällig am Tag des Zeitstopps (20 Börsentage). Das Ziel ist damit kein Ausstieg mehr: Liegt der Kurs am Verfallstag über dem Ziel, wird die Aktie zum Ziel abgegeben und die Prämie bleibt; sonst verkauft der Bot zum Schlusskurs. Stop und Ausstieg vor Quartalszahlen gelten wie immer, dann kauft er den Call zurück. Optionspreise berechnet (Black-Scholes) mit zwei Annahmen: Schwankung der letzten 20 Tage ×1,0 und ×1,25, Spread 2 %. Gleiche Trades des Bots auf 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum.

- **Vermutung:** Die Call-Prämie bringt bei jedem Trade etwas dazu; weil der Bot am Ziel ohnehin verkauft, kostet sie kaum etwas. Mit beiden Preis-Annahmen in allen drei Zeiträumen mehr Rendite als der Bot.
- **Widerlegt, wenn:** Mit einer der beiden Preis-Annahmen in einem Zeitraum: Mitte der 8 Listen nicht besser als der Bot, weniger als 6 von 8 Listen besser, mehr als 1 Punkt mehr Rückgang (Mitte) oder unter 30 Trades.
- **Varianten:** 1 Regel (Basispreis = Kursziel, Verfall am Tag des Zeitstopps), gerechnet mit 2 festen Preis-Annahmen; bestehen muss sie mit beiden.

**Ergebnis: nicht überall besser (Preise günstig: -1,0 / -0,2 / +0,7 Punkte; Preise teuer: +3,4 / +4,0 / +4,4 Punkte)**

Je Zeitraum 8 Zufallslisten mit je 24 Aktien aus dem damaligen S&P 500 (zur Wahl standen 2010–2014: 266, 2015–2021: 303, 2022–2026: 411 Aktien). Werte: Mitte (Median) der 8 Listen, Rendite pro Jahr / größter Rückgang.

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot ohne Call (wie heute) | +11,4 % / −16 % | +4,5 % / −19 % | +2,9 % / −14 % |
| **Gedeckter Call am Ziel – Preise günstig (×1,0)** | +10,4 % / −19 % | +4,5 % / −22 % | +3,0 % / −14 % |
| … Unterschied zum Vergleich (Mitte, Punkte) · Listen besser | -1,0 · 1 von 8 | -0,2 · 3 von 8 | +0,7 · 7 von 8 |
| **Gedeckter Call am Ziel – Preise teuer (×1,25)** | +14,7 % / −15 % | +8,2 % / −18 % | +6,9 % / −11 % |
| … Unterschied zum Vergleich (Mitte, Punkte) · Listen besser | +3,4 · 8 von 8 | +4,0 · 8 von 8 | +4,4 · 8 von 8 |
| … Trades je Zeitraum (alle Listen) · Ø Extra je Trade durch den Call: günstig / teuer | 4999 · -0,01 / +0,05 R | 6494 · -0,00 / +0,06 R | 3957 · +0,01 / +0,07 R |

So gelesen: Optionspreise sind berechnet (Black-Scholes, Schwankung der letzten 20 Tage mal 1,0 bzw. 1,25, Zins 2 %, Spread 2 %), nicht echt gehandelt – echte Preise können anders sein. „R“ ist das geplante Risiko eines Trades (1 % des Kontos). Die Trades sind die des Bots auf Zufallslisten aus dem damaligen S&P 500; Pleitefirmen fehlen darin. Simulation mit Spielgeld, keine Anlageberatung.
