# 🔬 Optionen 3: Call statt Aktie

Getestet am 18.11.2026 · Quelle: Coval & Shumway (2001), „Expected Option Returns“, Journal of Finance 56 – gekaufte Optionen bringen im Schnitt weniger, als ihr Risiko erwarten lässt; Black & Scholes (1973), Journal of Political Economy 81 – die Preisformel.

Bei jedem Kauf-Signal kauft der Bot statt der Aktie einen Call am Geld (Basispreis = Kurs beim Einstieg) mit 60 Tagen Laufzeit. Die Prämie ist so groß wie das geplante Risiko des Trades (1 % des Kontos) – mehr kann nicht verloren gehen. Ausstieg am selben Tag wie bei der Aktie (Stop, Ziel, Zeitstopp, vor Quartalszahlen). Optionspreise berechnet (Black-Scholes) mit zwei Annahmen: Schwankung der letzten 20 Tage ×1,0 und ×1,25, Spread 2 %. Gleiche Trades des Bots auf 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum.

- **Vermutung:** Mit dem Call verliert der Bot am Stop weniger als 1 R und gewinnt am Ziel mehr. Das bringt mit beiden Preis-Annahmen in allen drei Zeiträumen mehr Rendite als die Aktie.
- **Widerlegt, wenn:** Mit einer der beiden Preis-Annahmen in einem Zeitraum: Mitte der 8 Listen nicht besser als der Bot, weniger als 6 von 8 Listen besser, mehr als 1 Punkt mehr Rückgang (Mitte) oder unter 30 Trades.
- **Varianten:** 1 Regel (Call am Geld, 60 Tage, Prämie = 1 % des Kontos), gerechnet mit 2 festen Preis-Annahmen.

**Ergebnis: nicht überall besser (Preise günstig: -8,7 / -3,9 / -3,5 Punkte; Preise teuer: -15,7 / -10,2 / -8,4 Punkte)**

Je Zeitraum 8 Zufallslisten mit je 24 Aktien aus dem damaligen S&P 500 (zur Wahl standen 2010–2014: 266, 2015–2021: 303, 2022–2026: 411 Aktien). Werte: Mitte (Median) der 8 Listen, Rendite pro Jahr / größter Rückgang.

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot mit Aktien (wie heute) | +11,4 % / −16 % | +4,5 % / −19 % | +2,9 % / −14 % |
| **Call statt Aktie – Preise günstig (×1,0)** | +2,4 % / −19 % | +0,9 % / −18 % | -0,8 % / −17 % |
| … Unterschied zum Vergleich (Mitte, Punkte) · Listen besser | -8,7 · 0 von 8 | -3,9 · 0 von 8 | -3,5 · 0 von 8 |
| **Call statt Aktie – Preise teuer (×1,25)** | -5,1 % / −31 % | -5,8 % / −42 % | -5,8 % / −31 % |
| … Unterschied zum Vergleich (Mitte, Punkte) · Listen besser | -15,7 · 0 von 8 | -10,2 · 0 von 8 | -8,4 · 0 von 8 |
| … Trades je Zeitraum (alle Listen) · Ø je Trade: Aktie / Call günstig / Call teuer | 5028 · +0,13 / +0,03 / -0,03 R | 6510 · +0,06 / +0,02 / -0,05 R | 3969 · +0,04 / -0,01 / -0,07 R |

So gelesen: Optionspreise sind berechnet (Black-Scholes, Schwankung der letzten 20 Tage mal 1,0 bzw. 1,25, Zins 2 %, Spread 2 %), nicht echt gehandelt – echte Preise können anders sein. „R“ ist das geplante Risiko eines Trades (1 % des Kontos). Die Trades sind die des Bots auf Zufallslisten aus dem damaligen S&P 500; Pleitefirmen fehlen darin. Simulation mit Spielgeld, keine Anlageberatung.
