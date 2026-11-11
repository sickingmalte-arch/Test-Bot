# 🔬 Day-Trader-Skill: Tageshandel mit dem Ausbruch aus der Eröffnungsspanne

Getestet am 11.11.2026 · Quelle: github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026

Der Tageshandel des Skills: Kauf, wenn eine Kerze über dem Hoch der Eröffnungsspanne schließt, Stop in der Mitte der Spanne, Ziel 1R oder 2R, raus spätestens zum Schluss. Geprüft mit Stunden-Kerzen der letzten 2 Jahre (Spanne = erste Stunde) und 5-Minuten-Kerzen der letzten 60 Tage (Spanne = erste 15 Minuten, wie im Skill) für alle Aktien der Watchlist. Gegenprobe: für jeden Trade 20 Einstiege an zufälligen anderen Tagen derselben Aktie zur gleichen Uhrzeit, mit gleichem Stop-Abstand und Ziel.

- **Vermutung:** Der Ausbruch aus der Eröffnungsspanne bringt nach Spread im Schnitt mehr als 0 R je Trade und mehr als zufällige Einstiege zur gleichen Uhrzeit mit gleichem Risiko.
- **Widerlegt, wenn:** Je Variante: im Schnitt höchstens 0 R nach Spread, oder der Unterschied zu den Zufalls-Einstiegen ist nicht klar positiv (98-%-Intervall, nach Handelstagen gezogen, nicht ganz über 0). Unter 30 Trades: keine Aussage.
- **Varianten:** 4, vor dem Rechnen festgelegt: Stunden-Kerzen (2 Jahre) und 5-Minuten-Kerzen (60 Tage), je Ziel 1R (Beispiel im Skill) und 2R (Standard im Skill). Selbst wenn eine besteht: nur ein Zeitraum statt drei, und der Bot kann nicht minutengenau handeln (Live-Kurse 15 Minuten verzögert) – also höchstens eine Vermutung, kein Einbau.

**Ergebnis:** Tageshandel (ORB): besteht in keiner Variante

| Variante | Aktien / Handelstage | Trades | Ziel / Stop / Schluss | Gewinner | Ø R nach Spread | Ø R Zufall | Unterschied (98-%-Intervall) | Urteil |
|---|---:|---:|---|---:|---:|---:|---|---|
| Stunden-Kerzen, 2 Jahre, Ziel 1R | 23 / 16193 | 5440 | 17% / 16% / 67% | 40% | -0,181 | -0,186 | +0,005 (-0,030 bis +0,040) | besteht nicht |
| Stunden-Kerzen, 2 Jahre, Ziel 2R | 23 / 16193 | 5440 | 3% / 17% / 80% | 38% | -0,179 | -0,186 | +0,007 (-0,033 bis +0,046) | besteht nicht |
| 5-Minuten-Kerzen, 60 Tage, Ziel 1R | 24 / 1416 | 755 | 34% / 41% / 26% | 43% | -0,298 | -0,259 | -0,040 (-0,152 bis +0,064) | besteht nicht |
| 5-Minuten-Kerzen, 60 Tage, Ziel 2R | 24 / 1416 | 755 | 13% / 44% / 42% | 36% | -0,276 | -0,270 | -0,005 (-0,136 bis +0,113) | besteht nicht |

R = Gewinn oder Verlust in Vielfachen des geplanten Risikos (Einstieg bis Stop), nach 0,1 % Spread je Order. Stunden-Kerzen sind gröber als im Skill (Spanne = erste Stunde, Ausstieg zum Tagesschluss). Nur die letzten 2 Jahre bzw. 60 Tage und die heutige Watchlist – ein einziger Zeitraum. Simulation, keine Anlageberatung.
