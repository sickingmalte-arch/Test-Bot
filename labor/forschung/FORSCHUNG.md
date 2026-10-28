# 🔬 Forschungsprotokoll: Ist das Strategie-Labor besser als der Swing-Bot?

Stand: 28.10.2026 · Kurse bis 27.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

## Die Frage und die Regel (vorher festgelegt)

- Beide Bots auf **denselben echten Kursen** (Yahoo, ab 2005), in US-Dollar, mit Kosten (1 $ je Order, 0,1 % Spread), 10.000 $ Start.
- Das Labor zählt nur **Testjahre, die es beim Suchen nicht kannte** (Walk-Forward). Der Swing-Bot rechnet mit seinen eingefrorenen Regeln über dieselben Jahre.
- **Besser** heißt: in **jedem** der Zeiträume 2015–2021 und 2022–2026 **mehr Rendite pro Jahr und mehr Rendite je Prozent größtem Rückgang** als der Swing-Bot, bei **allen** Zufallsstarts.
- Gerechnet von `labor/wettkampf.py` in GitHub Actions (`.github/workflows/labor-forschung.yml`); jeder Lauf steht in `protokoll.json`.

## Ergebnis (Versuch 7)

| Zeitraum | Bot | Rendite pro Jahr | größter Rückgang | Rendite je % Rückgang |
| --- | --- | --- | --- | --- |
| 2015–2021 | **Strategie-Labor** | **17,6 %** | 16,9 % | **1,04** |
| 2015–2021 | Swing-Bot | 11,4 % | 16,3 % | 0,70 |
| 2015–2021 | Nasdaq-100 halten | 22,3 % | 28,6 % | 0,78 |
| 2022–2026 | **Strategie-Labor** | **20,4 %** | 20,4 % | **1,00** |
| 2022–2026 | Swing-Bot | 6,9 % | 12,1 % | 0,57 |
| 2022–2026 | Nasdaq-100 halten | 13,9 % | 34,8 % | 0,40 |

Beim Swing-Bot steht je Kennzahl die **stärkere** von zwei Messungen (durchgehend ab 2009 und frisch gestartet zum Beginn des Zeitraums, je Mittel aus 8 Ticker-Reihenfolgen). Das Labor ist in beiden Zeiträumen in **5 von 5 Starts** besser. Seit Versuch 7 sind die Starts gleich, weil nur noch aus dem festen Kernraster gehandelt wird.

## Alle Versuche

| Versuch | Änderung | 2015–2021 Labor / Swing-Bot | 2022–2026 Labor / Swing-Bot | Urteil |
| --- | --- | --- | --- | --- |
| 1 | Ausgangslage: Labor wie bisher | 0,50 / 0,72 (Rückgang 49,6 %) | 0,10 / 0,40 (Rückgang 45,5 %) | ❌ 0 von 3 |
| 2 | Rückgang zählt in der Suche, Komitee der 5 besten, Depot-Schwankung begrenzbar | 0,58 / 1,03 | 0,27 / 0,51 | ❌ |
| 2 neu | gleiches Labor, **feste Messlatte** (Datenstand, Swing-Bot Mittel aus 8 Reihenfolgen) | 0,64 / 0,83 | 0,41 / 0,49 | ❌ |
| 3 | Suche nach Rendite je Rückgang, Komitee aus allen drei Familien | 0,17 / 0,83 | 0,66 / 0,49 | ❌ (2 von 3 im 2. Zeitraum) |
| 4 | Training mit allen Jahren davor statt nur 3 | 0,29 / 0,83 | 1,18 / 0,49 | ❌ (2. Zeitraum 3 von 3) |
| 5 | Verlustbremse als Gen, Kurse ab 2005 | 0,29 / 0,66 | 0,71 / 0,51 | ❌ |
| 6 | **Kernraster aus der Bibliothek** in jeder Suche, Komitee = bester je Familie | 1,03 / 0,66 | 0,73 / 0,51 | ✅ 3 von 3 |
| 6 streng | gleiches Labor, Swing-Bot zusätzlich frisch je Zeitraum, 5 Starts | 0,81 / 0,70 | 0,83 / 0,57 | ❌ 4 von 5 im 1. Zeitraum |
| 7 | **gehandelt wird nur aus dem Kernraster**, Zufallsfunde bleiben Forschung | **1,04 / 0,70** | **1,00 / 0,57** | ✅ 5 von 5 |

(Rendite je Prozent Rückgang, beim Labor der mittlere Start.)

## Was die Versuche gezeigt haben

1. **Zufallssuche in einem riesigen Raum findet vor allem Glück.** Bei über 3 Milliarden möglichen Bauplänen und gut 100 Proben je Jahr hingen die Ergebnisse stark vom Zufallsstart ab (Versuch 5: 0,4 % bis 17,8 % pro Jahr). Der Deflated Sharpe bestätigte das: Kaum ein Trainings-Sieger war sicher mehr als Glück.
2. **Der Rückgang muss in die Zielfunktion.** Wer nur auf Rendite sucht, findet Strategien mit 50 % Absturz (Versuch 1).
3. **Mehr Geschichte im Training hilft.** Mit allen Jahren davor statt nur 3 wurde 2022–2026 deutlich besser (Versuch 4).
4. **Eine Verlustbremse allein löst es nicht** (Versuch 5).
5. **Vorwissen aus der Bibliothek schlägt Zufall.** 80 begründete Baupläne (Momentum nach Moskowitz/Jegadeesh, Turtle-Ausbruch, Rücksetzer im Trend, Faber-Marktfilter, ohne Shorts und Hebel), jedes Jahr per Walk-Forward ausgewählt, brachten den Durchbruch (Versuche 6 und 7). Zufallsfunde dürfen forschen, aber erst handeln, wenn sie bewiesen sind (Harvey, Liu & Zhu).
6. **Die Messlatte muss fest sein.** Laufende Kerzen, die Reihenfolge der Aktien und der Startzeitpunkt verschieben das Ergebnis des Swing-Bots um 1–3 Punkte. Deshalb: fester Datenstand, Mittel aus 8 Reihenfolgen, die stärkere von zwei Messungen.

## Vorsicht – was das Ergebnis nicht beweist

- **Viele Versuche:** 7 Versionen in 9 Läufen. Das Labor selbst kannte die Testjahre nicht, aber wer die Versionen gebaut hat, hat die Ergebnisse gesehen. Ein Teil des Vorsprungs kann deshalb Anpassung an diese Jahre sein. Die eigentliche Probe ist das **Übungsdepot des Labors** mit Kursen, die es noch nicht gibt.
- **Überlebende:** Die Aktienlisten sind von heute. Das hilft dem Tech-Labor vermutlich mehr als dem Swing-Bot mit 8 Branchen.
- **Höhere absolute Rückgänge:** 2022–2026 fiel das Labor zwischendurch um 20,4 %, der Swing-Bot nur um 12,1 %. Besser ist es je Prozent Rückgang, nicht in jeder Hinsicht.
- **Frühe Jahre schwächer:** 2010 (−4 %) und 2011 (−11 %) waren schwache Testjahre des Labors (nicht Teil der vorher festgelegten Zeiträume).
- **Ziel 30 % pro Jahr nicht erreicht** (17,6 % bzw. 20,4 %).
