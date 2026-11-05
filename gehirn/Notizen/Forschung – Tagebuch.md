---
tags: [forschung, tagebuch]
---
# 🔬 Forschung – Tagebuch

Hier schreibt der Forschungs-Bot jede geprüfte Idee auf, auch die, die durchfallen. Neueste oben. Zurück zur [[Start|Startseite]] · alle Tests auf einen Blick: [[Notizen/Was der Bot schon weiß]] · wie der Forschungs-Bot arbeitet: `forschung/README.md`.

> [!info] So wird geprüft
> - Echter Bot auf der Watchlist, 2010–2014, 2015–2021, 2022–2026, mit Gebühr und Spread.
> - Übernommen wird nur, was überall hilft. Ideen, die nur sortieren oder auswählen, müssen zusätzlich den Zufall schlagen (Gegenprobe), weil schon die Reihenfolge die Rendite um bis zu ±2 Punkte im Jahr verschiebt.
> - Eingebaut wird nur per Pull Request nach deinem „Ja“.

## 05.11.2026 · Boden-Kauf (neues Kauf-Signal)

**Idee** (Wunsch des Nutzers): Der Bot darf zusätzlich am Boden kaufen, nicht nur filtern. Neue Strategie „Boden-Abpraller ↑“: Das Tagestief berührt ein bestätigtes Wendetief (höchstens 0,25 ATR darüber oder 0,5 ATR darunter), der Schluss liegt wieder darüber und in der oberen Hälfte der Kerze, Kurs über der 200-Tage-Linie, Markt im Aufwärtstrend. Stop 0,5 ATR unter dem Boden (mindestens 1 ATR), Ziel +2 ATR. Gegenprobe: gleich viele Käufe an zufälligen Tagen über der 200-Tage-Linie mit denselben Stop-Abständen (6-mal). Gerechnet bei GitHub.

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +13,3 % / −14 % | +11,9 % / −18 % | +7,7 % / −15 % |
| a) jede Unterstützung (1 Grund) | +13,2 % / −13 % | +11,3 % / −20 % | +6,6 % / −20 % |
| … Gegenprobe Zufall (6-mal) | +13,1 bis +16,6 % | +12,2 bis +14,2 % | +4,3 bis +7,8 % |
| b) nur starke Zone (mind. 2 Gründe: Doppel-Tief, großes Wendetief, runde Zahl) | +12,7 % / −13 % | +10,6 % / −18 % | +7,7 % / −17 % |
| … Gegenprobe Zufall (6-mal) | +10,0 bis +14,2 % | +10,1 bis +14,3 % | +8,0 bis +9,1 % |

**Ergebnis:** beide nicht besser – nicht übernommen.
- a) −0,1 / −0,6 / −1,1 Punkte, 2022–2026 Rückgang −20 % statt −15 %.
- b) −0,6 / −1,3 / ±0 Punkte.
- Zufällige Zusatz-Käufe waren meist genauso gut oder besser: Das Berühren des Bodens bringt keinen eigenen Vorteil. Der Boden bleibt nur Anzeige.

## 04.11.2026 · Boden-Regeln

**Idee** (Wunsch des Nutzers): Der Bot soll auf den Boden achten, also auf das letzte Wendetief unter dem Kurs (tiefer als je 5 Tage davor und danach, erst 5 Tage später bekannt). Vier Regeln, gerechnet bei GitHub (Watchlist dort, 0 € Gebühr, 7 Positionen):

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +13,3 % / −14 % | +11,9 % / −18 % | +7,9 % / −16 % |
| a) Stop 0,5 ATR unter den Boden | +9,4 % / −23 % | +13,9 % / −14 % | +9,5 % / −18 % |
| b) nur kaufen, wenn höchstens 1,5 ATR über dem Boden | +6,8 % / −10 % | +7,2 % / −16 % | +4,9 % / −10 % |
| … Gegenprobe: gleich viele zufällig auslassen (6-mal) | +3,2 bis +8,9 % | +7,5 bis +12,1 % | +3,2 bis +7,3 % |
| c) nicht kaufen, wenn der Boden gerade gebrochen ist | +13,2 % / −14 % | +13,3 % / −15 % | +7,3 % / −15 % |
| … Gegenprobe (6-mal) | +10,4 bis +14,9 % | +12,6 bis +14,4 % | +4,9 bis +8,1 % |
| d) Ziel am nächsten Widerstand | +6,7 % / −23 % | +13,3 % / −20 % | +12,1 % / −17 % |

**Ergebnis:** keine Regel ist überall besser – nicht übernommen.
- a) und d) helfen 2015–2026, kosten aber 2010–2014 4 bzw. 7 Punkte und machen dort den größten Rückgang deutlich größer (−23 % statt −14 %).
- b) lässt viele gute Trades weg: Rückgänge kleiner, aber 3 bis 6,5 Punkte weniger Rendite – nicht besser als zufälliges Auslassen.
- c) ändert kaum etwas und liegt im Bereich des Zufalls.

**Lehre:** Der Boden ist eine gute Orientierung zum Anschauen, als feste Regel bringt er dem Bot nichts. Die Anzeige im Bericht und auf der Webseite bleibt (nur Info).

## 03.11.2026 · Kosten-Filter und „70–80 % Treffer“

**Kosten-Filter** (Wunsch des Nutzers): nur Signale kaufen, deren Ziel mindestens 3 % bzw. 5 % über dem Kurs liegt. Dann frisst der Spread (zusammen etwa 0,2 % je Trade, Ordergebühr seit heute 0 €) höchstens rund 7 % bzw. 4 % des geplanten Gewinns. Gerechnet bei GitHub mit der Watchlist dort; Ergebnisse: `forschung/ergebnisse/kosten_filter_3.md` und `kosten_filter_5.md`.

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot (0 € Gebühr) | +13,2 % / −15 % | +13,3 % / −17 % | +8,0 % / −14 % |
| Ziel mindestens 3 % | +12,3 % / −18 % | +13,8 % / −16 % | +8,4 % / −14 % |
| Ziel mindestens 5 % | +10,1 % / −17 % | +12,2 % / −17 % | +6,4 % / −15 % |
| Gegenprobe: gleich viele zufällig auslassen (3 %, 6-mal) | +11,5 bis +13,4 % | +12,3 bis +14,0 % | +6,2 bis +8,6 % |

**Ergebnis:** nicht übernommen. Signale mit kleinem Ziel liefen nicht schlechter als die anderen; mit 0 € Gebühr ist der Spread zu klein, als dass ein Filter etwas bringt.

**70–80 % Treffer** (Frage des Nutzers): Ziel näher an den Einstieg gelegt, echter Bot auf der Watchlist (mit 1 € Gebühr und 0,1 % Spread).

| | Treffer | Rendite pro Jahr (2010–14 / 2015–21 / 2022–26) |
|---|---:|---|
| Bot wie heute | 56–58 % | +9,2 / +10,5 / +7,0 % |
| Ziel halb so weit | 65–67 % | +5,6 / +5,1 / +3,5 % |
| Ziel ein Drittel so weit | 71–73 % | +1,5 / −2,6 / +0,5 % |
| Ziel ein Viertel so weit | 75–79 % | +4,0 / −1,5 / +2,2 % |
| Ziel ein Drittel, ohne Kosten | 72–74 % | +10,3 / +10,3 / +8,6 % |

**Lehre:** Die Trefferquote ist eine Einstellung, kein Können. Ein näheres Ziel wird öfter erreicht, bringt aber weniger – ohne Kosten bleibt es gleich, mit Kosten wird es schlechter. Es zählt der Gewinn je Trade nach Kosten, nicht wie oft der Bot gewinnt. Dazu: Ohne Gebühr und Spread brächte der Bot +16,2 / +15,1 / +10,3 % statt +9,2 / +10,5 / +7,0 % – deshalb rechnet er seit dem 03.11. mit 0 € Ordergebühr (wie beim Broker des Nutzers).

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
