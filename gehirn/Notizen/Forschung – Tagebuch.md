---
tags: [forschung, tagebuch]
---
# 🔬 Forschung – Tagebuch

Hier schreibt der Forschungs-Bot jede geprüfte Idee auf, auch die, die durchfallen. Neueste oben. Zurück zur [[Start|Startseite]] · alle Tests auf einen Blick: [[Notizen/Was der Bot schon weiß]] · wie der Forschungs-Bot arbeitet: `forschung/README.md`.

> [!info] So wird geprüft
> - Echter Bot auf der Watchlist, 2010–2014, 2015–2021, 2022–2026, mit Gebühr und Spread.
> - Übernommen wird nur, was überall hilft. Ideen, die nur sortieren oder auswählen, müssen zusätzlich den Zufall schlagen (Gegenprobe), weil schon die Reihenfolge die Rendite um bis zu ±2 Punkte im Jahr verschiebt.
> - Eingebaut wird nur per Pull Request nach deinem „Ja“.

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
