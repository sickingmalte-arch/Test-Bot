# 🔬 Optionen 4: Put statt Short

Getestet am 18.11.2026 · Quelle: Coval & Shumway (2001), „Expected Option Returns“, Journal of Finance 56; dazu die Short-Tests vom 17. und 18.11.2026 (alle Short-Signale verloren).

Der Bot nimmt die 8 alten Short-Signale dazu, setzt aber nicht mit einem Short auf fallende Kurse, sondern kauft einen Put am Geld mit 60 Tagen Laufzeit. Die Prämie ist so groß wie das geplante Risiko (1 % des Kontos), Ausstieg am selben Tag wie beim Short. Vergleich: der Bot nur mit Long; zur Info auch der Bot mit echten Shorts. Gegenprobe: gleich viele Puts an zufälligen erlaubten Tagen. Optionspreise berechnet (Black-Scholes) mit zwei Annahmen: Schwankung der letzten 20 Tage ×1,0 und ×1,25, Spread 2 %. 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum.

- **Vermutung:** Mit Puts ist der Verlust je Trade begrenzt, große Abstürze bringen viel. So machen die Short-Signale den Bot mit beiden Preis-Annahmen in allen drei Zeiträumen besser – und besser als Puts an zufälligen Tagen.
- **Widerlegt, wenn:** Mit einer der beiden Preis-Annahmen in einem Zeitraum: Mitte der 8 Listen nicht besser als der Bot nur mit Long, weniger als 6 von 8 Listen besser, mehr als 1 Punkt mehr Rückgang (Mitte), unter 30 Puts oder nicht besser als die beste von 6 Zufalls-Gegenproben.
- **Varianten:** 1 Regel (Put am Geld, 60 Tage, Prämie = 1 % des Kontos, Signale der 8 alten Short-Strategien), gerechnet mit 2 festen Preis-Annahmen.

**Ergebnis: nicht überall besser (Preise günstig: -2,2 / -0,1 / +0,0 Punkte; Preise teuer: -2,1 / -0,1 / +0,0 Punkte)**

Je Zeitraum 8 Zufallslisten mit je 24 Aktien aus dem damaligen S&P 500 (zur Wahl standen 2010–2014: 266, 2015–2021: 303, 2022–2026: 411 Aktien). Werte: Mitte (Median) der 8 Listen, Rendite pro Jahr / größter Rückgang.

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot nur mit Long (wie heute) | +11,4 % / −16 % | +4,5 % / −19 % | +2,9 % / −14 % |
| Bot mit den alten Shorts als echte Shorts (zur Info) | +9,5 % / −17 % | +4,0 % / −19 % | +2,3 % / −15 % |
| **Put statt Short – Preise günstig (×1,0)** | +9,4 % / −17 % | +4,0 % / −19 % | +2,5 % / −15 % |
| … Unterschied zum Vergleich (Mitte, Punkte) · Listen besser | -2,2 · 1 von 8 | -0,1 · 1 von 8 | +0,0 · 0 von 8 |
| **Put statt Short – Preise teuer (×1,25)** | +9,5 % / −17 % | +4,0 % / −19 % | +2,4 % / −15 % |
| … Unterschied zum Vergleich (Mitte, Punkte) · Listen besser | -2,1 · 1 von 8 | -0,1 · 1 von 8 | +0,0 · 0 von 8 |
| … Puts je Zeitraum (alle Listen) · Ø je Trade: Short / Put günstig / Put teuer | 133 · -0,48 / -0,47 / -0,44 R | 40 · -0,31 / -0,37 / -0,37 R | 33 · -0,12 / -0,16 / -0,19 R |
| … Gegenprobe: gleich viele Puts an Zufallstagen (beste von 2): günstig / teuer | +10,4 % / +10,4 % | +4,5 % / +4,5 % | +2,3 % / +2,3 % |

So gelesen: Optionspreise sind berechnet (Black-Scholes, Schwankung der letzten 20 Tage mal 1,0 bzw. 1,25, Zins 2 %, Spread 2 %), nicht echt gehandelt – echte Preise können anders sein. „R“ ist das geplante Risiko eines Trades (1 % des Kontos). Die Trades sind die des Bots auf Zufallslisten aus dem damaligen S&P 500; Pleitefirmen fehlen darin. Simulation mit Spielgeld, keine Anlageberatung.
