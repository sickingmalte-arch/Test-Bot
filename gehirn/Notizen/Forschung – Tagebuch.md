---
tags: [forschung, tagebuch]
---
# 🔬 Forschung – Tagebuch

Hier schreibt der Forschungs-Bot jede geprüfte Idee auf, auch die, die durchfallen. Neueste oben. Zurück zur [[Start|Startseite]] · alle Tests auf einen Blick: [[Notizen/Was der Bot schon weiß]] · wie der Forschungs-Bot arbeitet: `forschung/README.md`.

> [!info] So wird geprüft
> - Echter Bot auf der Watchlist, 2010–2014, 2015–2021, 2022–2026, mit Gebühr und Spread.
> - Übernommen wird nur, was überall hilft. Ideen, die nur sortieren oder auswählen, müssen zusätzlich den Zufall schlagen (Gegenprobe), weil schon die Reihenfolge die Rendite um bis zu ±2 Punkte im Jahr verschiebt.
> - Eingebaut wird nur per Pull Request nach deinem „Ja“.

## 02.11.2026 · Lernmodell: klarere Frage und ein Modell je Strategie

**Idee:** Das Lernmodell fragt bisher nur „Gewinn ja oder nein?“. Geprüft wurden drei andere Fragen, jeweils Walk-forward (jeden Monat neu gelernt, nur mit Trades, deren Ergebnis vorher feststand). Der Bot kauft dann bei mehr Signalen als Plätzen die beste Punktzahl zuerst:
- **Höhe von R:** Wie viel bringt der Trade, statt nur ob er Gewinn macht.
- **Ziel vor Stop:** Erreicht der Trade sein Ziel, bevor der Stop greift?
- **Ein Modell je Strategie:** Jede der 8 Kauf-Strategien bekommt ein eigenes Modell.

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +9,2 % / −17 % | +10,5 % / −17 % | +7,0 % / −16 % |
| Bisheriges Modell, beste zuerst | +6,1 % / −19 % | +14,6 % / −16 % | +10,1 % / −18 % |
| Höhe von R, beste zuerst | +9,9 % / −13 % | +14,8 % / −13 % | +9,8 % / −14 % |
| Ziel vor Stop, beste zuerst | +9,5 % / −14 % | +12,9 % / −15 % | +10,0 % / −16 % |
| Ein Modell je Strategie, beste zuerst | +7,1 % / −16 % | +14,1 % / −17 % | +7,3 % / −11 % |
| **Gegenprobe: zufällige Punktzahl (6-mal)** | **+4,8 bis +8,8 %** | **+7,2 bis +15,3 %** | **+4,7 bis +11,6 %** |

- **Trennschärfe** (0,50 = Münzwurf): bisher 0,506 · Höhe von R 0,499 · Ziel vor Stop 0,517 · je Strategie 0,507. Das beste Fünftel der Punktzahlen lief bei keiner Frage besser als das schlechteste.
- **„Höhe von R“ sieht im Bot gut aus:** In allen drei Zeiträumen mehr Rendite und kleinere Rückgänge als der jetzige Bot. Aber eine ganz zufällige Punktzahl schaffte 2015–2021 und 2022–2026 teils genauso viel. Allein die zufällige Reihenfolge verschiebt die Rendite hier um bis zu 8 Punkte.
- **Ergebnis:** nicht übernommen, weil nicht besser als Zufall. Auffällig bleibt, dass die Rückgänge mit „Höhe von R“ in allen drei Zeiträumen kleiner waren (−13 bis −14 % statt −16 bis −17 %), meist auch kleiner als bei den Zufalls-Punktzahlen. Kandidat für das Experimentier-Depot, wenn der Lern-Lauf diese Punktzahl einmal mitrechnet.

## 30.10.2026 · Tagesbremse nach einem schlechten Tag

**Anlass:** Das Übungsdepot verlor an einem Tag 211 € (−2,1 %). Frage: Kann der Bot solche Tage vermeiden?

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +9,2 % / −17 % | +10,5 % / −17 % | +7,0 % / −16 % |
| … Tage mit −2 % oder schlimmer, pro Jahr | 3,7 | 4,6 | 1,8 |
| Nach −2 %-Tag 1 Tag nichts kaufen | +8,3 % / −18 % | +10,5 % / −17 % | +6,9 % / −16 % |
| Nach −2 %-Tag 3 Tage nichts kaufen | +9,1 % / −18 % | +11,7 % / −15 % | +6,2 % / −16 % |
| Nach −2 %-Tag alles verkaufen | +7,5 % / −16 % | +8,8 % / −15 % | +5,1 % / −14 % |
| Nach −1,5 %-Tag alles verkaufen | +5,5 % / −20 % | +6,5 % / −19 % | +5,3 % / −14 % |
| Risiko 0,75 % statt 1 % je Trade | +6,6 % / −14 % | +7,8 % / −13 % | +5,3 % / −12 % |
| … Tage mit −2 % oder schlimmer, pro Jahr | 0,6 | 2,0 | 0,2 |

**Ergebnis:** nicht übernommen.
- Tage mit −2 % sind normal (2- bis 5-mal pro Jahr). Eine Bremse greift erst, wenn der Tag schon passiert ist, und kostet dann nur Rendite.
- Nur kleinere Positionen machen solche Tage seltener. 0,75 % Risiko kostet aber etwa 2 bis 3 Punkte Rendite im Jahr. Das ist eine Frage des Geschmacks, keine bessere Regel. Einstellbar über die Variable `RISIKO` bei GitHub.
