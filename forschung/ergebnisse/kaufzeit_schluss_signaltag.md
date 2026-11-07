# 🔬 Kaufzeit 1: Kauf zum Schlusskurs am Signaltag (statt zur Eröffnung am nächsten Tag)

Getestet am 06.11.2026 · Quelle: Wunsch des Nutzers (Chat vom 05.11.2026): sollten wir die Kaufzeit ändern?

Der Bot würde kurz vor Börsenschluss (etwa 21:45 Uhr) entscheiden und zum Schlusskurs des Signaltags kaufen (mit Spread), statt am nächsten Tag zur Eröffnung bis zum Limit. Stop und Ziel bleiben gleich, ab dem nächsten Tag gelten sie wie bisher (auch Kurslücken über den Stop). In echt kennt man den Schlusskurs erst kurz vorher – der Test ist deshalb etwas zu günstig.

**Ergebnis: nicht überall besser**

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +12,9 % / −13 % | +12,6 % / −17 % | +8,3 % / −15 % |
| Kaufzeit 1: Kauf zum Schlusskurs am Signaltag (statt zur Eröffnung am nächsten Tag) | +12,4 % / −17 % | +12,8 % / −21 % | +8,0 % / −13 % |

Unterschied in Prozentpunkten: 2010–2014 -0,5, 2015–2021 +0,1, 2022–2026 -0,3

Watchlist, mit Gebühr und Spread, Mittel aus mehreren Läufen. Simulation, keine Anlageberatung.
