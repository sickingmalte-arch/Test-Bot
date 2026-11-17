---
tags: [forschung, tagebuch]
---
# 🔬 Forschung – Tagebuch

Hier schreibt der Forschungs-Bot jede geprüfte Idee auf, auch die, die durchfallen. Neueste oben. Zurück zur [[Start|Startseite]] · alle Tests auf einen Blick: [[Notizen/Was der Bot schon weiß]] · wie der Forschungs-Bot arbeitet: `forschung/README.md`.

> [!info] So wird geprüft
> - Echter Bot auf der Watchlist, 2010–2014, 2015–2021, 2022–2026, mit Gebühr und Spread.
> - Übernommen wird nur, was überall hilft. Ideen, die nur sortieren oder auswählen, müssen zusätzlich den Zufall schlagen (Gegenprobe), weil schon die Reihenfolge die Rendite um bis zu ±2 Punkte im Jahr verschiebt.
> - Eingebaut wird nur per Pull Request nach deinem „Ja“.

## 13.11.2026 (Freitag) · Monatswechsel-Effekt

**Idee** (Freitags-Idee aus der Forschung): McConnell & Xu (2008, *Financial Analysts Journal*) – von 1926 bis 2005 entstand fast die ganze Rendite des US-Aktienmarkts am letzten und an den ersten drei Handelstagen eines Monats (zuerst Lakonishok & Smidt 1988). Vermutung: Käufe kurz vor dem Monatswechsel laufen besser als Käufe in der Monatsmitte. 2 Varianten, vorher festgelegt, je mit 6 Gegenproben (gleich viele Signale zufällig weglassen).

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +11,5 % / −15 % | +12,0 % / −17 % | +8,3 % / −14 % |
| 1) nur an den letzten 4 Handelstagen kaufen | +9,7 % / −10 % | +6,9 % / −11 % | +3,1 % / −15 % |
| 2) an den letzten 4 und den ersten 3 Handelstagen | +10,7 % / −10 % | +9,0 % / −12 % | +2,8 % / −16 % |
| beste Gegenprobe mit Zufall (zu 1 / zu 2) | +12,4 / +12,9 % | +13,6 / +13,7 % | +9,5 / +9,2 % |

**Ergebnis:** nicht übernommen. Beide Varianten sind in allen drei Zeiträumen schlechter als der jetzige Bot (−1,8 / −5,1 / −5,2 und −0,8 / −3,1 / −5,5 Punkte) und nicht besser als zufälliges Weglassen gleich vieler Signale – 2015–2026 sogar schlechter als jede Gegenprobe. Der kleinere Rückgang 2010–2021 kommt nur daher, dass weniger Geld investiert war. Für die Signale des Bots gibt es keinen nutzbaren Monatswechsel-Effekt; dazu passt, dass eine Arbeit von 2025 den Titel „The disappearing turn-of-month effect“ trägt.

## 11.11.2026 (Mittwoch) · Day-Trader-Skill: 10 Ideen aus einem fremden Projekt

**Idee** (Wunsch des Nutzers): alles aus [github.com/Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) kontrollieren, das Prüfbare testen und einbauen, was den Bot verbessert. Von 11 Bausteinen waren 5 mit Kursen prüfbar, daraus 10 Tests, alles vorher festgelegt. Die übrigen hat der Bot schon (Stop/Ziel vorher, Größe nach Risiko), sie sind verboten (Broker für echtes Geld) oder nicht prüfbar (Kongress-Käufe: keine sauberen Daten). Details: [[Notizen/Wissen – Day-Trader-Skill]].

| Test (Pkt Rendite pro Jahr gegen den jetzigen Bot) | 2010–2014 | 2015–2021 | 2022–2026 | Ergebnis |
|---|---:|---:|---:|---|
| Bullen-Flagge als neue Strategie | +1,3 | +1,1 | +0,2 | überall besser, aber nicht besser als Zufall |
| Überverkauft (RSI 14 unter 30) | −0,1 | +0,6 | +0,9 | nicht überall besser |
| Abpraller nach Überverkauft | +0,3 | −0,6 | ±0,0 | nicht überall besser |
| 20-Tage-Schlusshoch-Ausbruch | −0,9 | −0,4 | +0,3 | nicht überall besser |
| Zurück über die 20-Tage-Linie | −1,2 | +0,8 | ±0,0 | nicht überall besser |
| Höchstens 3 Käufe am Tag | +0,9 | −1,0 | +1,4 | nicht überall besser |
| Chance-Risiko mindestens 1,0 | −2,2 | +0,2 | −0,1 | nicht überall besser |
| Zeitmaschine als Filter | −2,6 | +0,9 | +2,4 | nicht überall besser |
| Geschichte als Filter | −3,6 | −3,2 | +0,3 | deutlich schlechter |

**Tageshandel** (Ausbruch aus der Eröffnungsspanne, Stunden-Kerzen 2 Jahre und 5-Minuten-Kerzen 60 Tage): im Schnitt −0,18 bis −0,30 R je Trade nach Spread, genauso schlecht wie zufällige Einstiege zur gleichen Uhrzeit (5.440 bzw. 755 Trades).

**Ergebnis:** nichts übernommen. Die Bullen-Flagge war knapp überall besser, aber zufällige Zusatz-Käufe brachten genauso viel – der Gewinn kommt vom öfter Kaufen, nicht vom Muster. Der Tageshandel verliert nach Kosten.

## 06.11.2026 (Freitag) · Kaufzeit

**Idee** (Wunsch des Nutzers): Heute entscheidet der Bot am Abend und kauft am nächsten Tag zur Eröffnung bis zum Limit. Drei andere Kaufzeiten, vorher festgelegt; Rechnung mit der heutigen Kaufzeit exakt nachgeprüft (gleiches Ergebnis wie der Bot).

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot (Eröffnung am nächsten Tag) | +12,9 % / −13 % | +12,6 % / −17 % | +8,3 % / −15 % |
| 1) zum Schluss des Signaltags | +12,4 % / −17 % | +12,8 % / −21 % | +8,0 % / −13 % |
| 2) zum Schluss des nächsten Tages | +11,6 % / −18 % | +13,2 % / −16 % | +7,3 % / −15 % |
| 3) Eröffnung, aber nicht nach einer Lücke nach oben | +13,6 % / −14 % | +14,6 % / −17 % | +4,8 % / −18 % |
| … Gegenprobe: gleich oft zufällig auslassen (6×) | +10,1 bis +13,6 % | +10,4 bis +13,6 % | +5,9 bis +9,2 % |

**Ergebnis:** keine Kaufzeit ist überall besser – nicht übernommen. 1) −0,5 / +0,1 / −0,3 Punkte (Rückgänge größer), 2) −1,2 / +0,5 / −1,0, 3) +0,8 / +1,9 / −3,6 (2022–2026 deutlich schlechter). Variante 4 (1 Stunde nach der Eröffnung) entfiel: Stundenkerzen gibt es nur für etwa 2 Jahre, der Prüfstand rechnet 2010–2026.

## 06.11.2026 (Abend) · Ehrlicher Check 2: Watchlist nach Regel, halb Bot halb S&P 500, echte Stärke je Strategie

**Frage** (der Nutzer gab freie Hand): Alles mit Aktien, die zu Beginn des Zeitraums wirklich im S&P 500 waren. Vorher festgelegt: (1) Regel-Liste muss 7 von 8 Zufallslisten schlagen, (2) die Mischung muss mehr Rendite pro Rückgang haben als S&P 500 allein und Bot allein, (3) eine Strategie hat nur dann echten Vorteil, wenn sie in allen drei Zeiträumen zufällige Käufe mit denselben Stop- und Zielabständen schlägt.

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot mit 24 zufälligen damaligen Aktien (Mitte aus 8) | +12,3 % / −16 % | +4,4 % / −18 % | +3,1 % / −14 % |
| Bot mit den 24 meistgehandelten | +10,3 % / −18 % | +3,3 % / −22 % | +4,0 % / −15 % |
| Bot mit den 24 stärksten (12 Monate) | +6,2 % / −20 % | +2,8 % / −20 % | +4,0 % / −15 % |
| Halb Bot, halb S&P 500 (Mitte) | +15,4 % / −17 % | +11,3 % / −26 % | +8,0 % / −17 % |
| S&P 500 halten | +19,2 % / −21 % | +15,8 % / −33 % | +12,1 % / −23 % |

| Gedachte Trades auf Zufallslisten, Ø R nach Kosten | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Gegenbewegung ↑ | +0,13 | +0,12 | +0,05 |
| übrige 8 Strategien | +0,05 bis +0,11 | +0,02 bis +0,07 | +0,03 bis +0,06 |
| 🎲 Zufall mit Trend-Ausstieg (±3 ATR) | +0,12 | +0,06 | −0,03 |
| 🎲 Zufall mit Gegen-Ausstieg (−2,5/+2 ATR) | +0,09 | +0,05 | −0,01 |

**Ergebnis:**
- (1) Watchlist nach Regel: **besteht nicht** – meistgehandelte und stärkste Aktien liefen sogar schlechter als zufällige.
- (2) Halb Bot, halb S&P 500: **besteht nicht** – besser als der Bot allein, aber der S&P 500 allein hatte in allen drei Zeiträumen die beste Rendite pro Rückgang.
- (3) Nur **Gegenbewegung** schlug zufällige Käufe in allen drei Zeiträumen. Die anderen 8 Strategien verdienen meist nur, was jeder Kauf am steigenden Markt verdient (2010–2014 lagen fast alle unter dem Zufall). Bei 9 Strategien kann eine Glück sein – deshalb der Nachtest:

**Nachtest Gegenbewegung** (8 neue Zufallslisten, andere Aktien; vorher festgelegt):

| Mitte aus 8 neuen Listen | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Gegenbewegung, Ø R je gedachtem Trade | +0,11 | +0,10 | −0,03 |
| 🎲 Zufall mit demselben Ausstieg | +0,09 | +0,06 | −0,04 |
| Voller Bot (9 Strategien) | +12,7 % / −16 % | +4,7 % / −18 % | +2,5 % / −15 % |
| Bot nur mit Gegenbewegung | +3,4 % / −12 % | +1,5 % / −17 % | −1,1 % / −11 % |

- Gegenbewegung schlägt den Zufall auch auf neuen Aktien – aber nur knapp (+0,01 bis +0,04 R je Trade).
- Ein Bot nur mit ihr ist viel schlechter: Er handelt nur 24–42-mal im Jahr und ist meist nicht investiert. Der volle Bot verdient vor allem, weil er oft im steigenden Markt investiert ist – nicht, weil seine Käufe besser sind als zufällige.
- **Gesamtbild nach allen ehrlichen Tests:** Die Regeln des Bots sind kaum besser als zufällige Käufe mit denselben Ausstiegen. Einfach den S&P 500 zu halten hatte in allen drei Zeiträumen die beste Rendite pro Rückgang. Nicht übernommen, der Bot bleibt, wie er ist (Spielgeld, Lernprojekt).

## 06.11.2026 · Chart-Zeichnungen: Trendlinien-Regel (C), Anzeige (A), Chart-Agent (B)

**Wunsch des Nutzers:** ein Agent, der den Chart analysiert, Linien zeichnet und danach handelt. Drei Teile:

**C – Trendlinien-Ausbruch als Regel (Rückblick):** neues Kauf-Signal, wenn der Schluss eine fallende Trendlinie (durch die letzten zwei bestätigten Hochpunkte, das zweite tiefer) nach oben durchbricht, über der 200-Tage-Linie, Stop/Ziel ±3 ATR. 1 Variante, vorher festgelegt, Gegenprobe 6× Zufall.

| Rendite pro Jahr / größter Rückgang | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Jetziger Bot | +13,3 % / −14 % | +11,9 % / −18 % | +7,9 % / −15 % |
| Trendlinien-Ausbruch | +12,9 % / −13 % | +12,6 % / −17 % | +8,3 % / −15 % |
| Gegenprobe Zufall (6×) | +10,9 bis +15,2 % | +10,9 bis +12,5 % | +7,0 bis +9,2 % |

**Ergebnis C:** −0,5 / +0,7 / +0,4 Punkte – nicht überall besser, mitten im Zufallsbereich. Nach den Regeln nicht übernommen – **auf ausdrücklichen Wunsch des Besitzers trotzdem als 9. Kauf-Strategie eingebaut** (06.11.2026). Sie unterliegt wie alle Strategien der Lernregel: Läuft sie schlecht, pausiert der Bot sie von selbst.

**A – Zeichnung nur anzeigen:** Zu jedem Kauf-Signal zeigt der Bot jetzt auch den nächsten Widerstand darüber (letzter Hochpunkt über dem Kurs) und die fallende Trendlinie – im Handelsplan und im Chart der Webseite (W-Linie, gestrichelte Trendlinie in der Tagesansicht). Geprüft: Die Zeichnung ist mit abgeschnittenen Kursen gleich, schaut also nicht in die Zukunft. Kauft und verkauft nicht danach.

**B – Claude-Depot als Chart-Agent (Versuch nach vorne):** Ab dem 07.11. beurteilt die tägliche Claude-Depot-Entscheidung auch das Chart-Bild und darf Signale mit dem Grund „Chart: …“ auslassen. Ein Rückblick ist bei einem KI-Agenten nicht ehrlich möglich (er kennt den späteren Kursverlauf aus dem Training), deshalb nur mit Spielgeld nach vorne. Auswertung frühestens nach 30 Trades: Claude-Depot gegen Übungsdepot.

## 06.11.2026 · Ehrlicher Bot-Check: Wie gut ist der Bot ohne Rückblick-Watchlist?

**Frage** (Folge der Nacht-Forschung): Die Watchlist ist mit dem Wissen von heute gewählt. Wie viel vom Rückblick des Bots kommt nur daher? Zu Beginn jedes Zeitraums 8-mal 24 zufällige Aktien aus dem damaligen S&P 500 (Liste github.com/fja05680/sp500), damit handelt der unveränderte Bot den ganzen Zeitraum. Keine Regeländerung, nur eine Messung.

- **Vermutung:** Mit damaligen Aktien bringt der Bot deutlich weniger als mit der heutigen Watchlist.
- **Widerlegt, wenn** er im Mittel in allen drei Zeiträumen höchstens 1 Punkt pro Jahr schlechter ist.

| Rendite pro Jahr (größter Rückgang) | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Bot mit der heutigen Watchlist | +13,3 % (−14 %) | +11,9 % (−18 %) | +8,1 % (−15 %) |
| **Bot mit 24 zufälligen damaligen S&P-500-Aktien** (Mitte aus 8) | **+11,6 % (−16 %)** | **+3,2 % (−19 %)** | **+3,3 % (−15 %)** |
| … Spanne | +7,4 bis +13,1 % | +1,5 bis +7,0 % | −0,4 bis +8,8 % |
| Dieselben zufälligen Aktien einfach halten | +22,8 % (−22 %) | +16,2 % (−38 %) | +10,9 % (−21 %) |
| Heutige Watchlist einfach halten (Rückblick!) | +28,5 % (−20 %) | +42,8 % (−32 %) | +27,7 % (−32 %) |
| S&P 500 halten | +19,2 % (−21 %) | +15,8 % (−33 %) | +12,1 % (−23 %) |
| Nasdaq-100 halten | +22,9 % (−20 %) | +23,3 % (−31 %) | +13,0 % (−30 %) |

Schnitt je Trade: mit der Watchlist +0,15 / +0,13 / +0,10 R, mit damaligen Aktien +0,14 / +0,04 / +0,05 R.

**Ergebnis: Vermutung bestätigt** (−1,7 / −8,7 / −4,8 Punkte pro Jahr).
- Seit 2015 kommt der größte Teil des Rückblicks von der Watchlist, nicht von den Regeln. Ohne sie bleiben 3 % im Jahr, je Trade fast nichts (+0,04 bis +0,05 R).
- Dieselben Aktien einfach zu halten brachte überall deutlich mehr (+11 bis +23 %), allerdings mit größeren Rückgängen. Auch die Rendite pro Rückgang war beim einfachen Halten des S&P 500 in allen drei Zeiträumen besser als beim Bot.
- 2010–2014 lief der Bot auch mit damaligen Aktien ordentlich (+11,6 %) – ein kleiner echter Vorteil der Regeln ist möglich, aber unsicher.
- Verbleibende Verzerrung: Aktien, die seitdem aus dem Index geflogen sind, fehlen in der Auswahl. Das wahre Ergebnis ist eher noch etwas schlechter.

## 05.11.2026 (Nacht) · Eigene Monats-Depots: Momentum, Branchen, Trend, ruhige Aktien

**Idee** (Wunsch des Nutzers: „eine Strategie finden, die wirklich funktioniert“): nicht den Swing-Bot umbauen, sondern eine andere Art Strategie – einmal im Monat umschichten. Neu im Prüfstand: „eigene Depots“ (`forschung/rotation.py`), in Euro, mit Spread, Entscheidung am Monatsende, Handel am nächsten Morgen.

- **Vermutung:** Eine Monats-Regel bringt in allen drei Zeiträumen mehr Rendite pro Rückgang als der Swing-Bot und schlägt zufällig gewählte Aktien.
- **Widerlegt, wenn** in einem Zeitraum weniger Rendite pro Rückgang als der Bot, tiefer gefallen als der Nasdaq-100 beim Halten oder mehr als 1 von 20 Zufallsdepots gleich gut.
- **Varianten:** 7, vor dem Rechnen festgelegt, dazu 4 Nachtests mit Stichtag (Bereinigung, keine neue Idee).

| Rendite pro Jahr (größter Rückgang) | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| Swing-Bot (jetzt) | +13,3 % (−14 %) | +11,9 % (−18 %) | +7,7 % (−15 %) |
| Nasdaq-100 einfach halten | +22,9 % (−20 %) | +23,3 % (−31 %) | +12,8 % (−30 %) |
| S&P 500 einfach halten | +19,2 % (−21 %) | +15,8 % (−33 %) | +11,8 % (−23 %) |
| Momentum 12 Monate, 10 Aktien – heutige Aktienliste | +38,8 % (−23 %) | +25,7 % (−34 %) | +46,1 % (−38 %) |
| … **mit Stichtag** (nur Aktien, die damals im S&P 500 waren) | +25,6 % (−25 %) | +7,7 % (−33 %) | +9,1 % (−36 %) |
| Momentum 6 Monate, 10 Aktien – mit Stichtag | +21,1 % (−35 %) | +14,7 % (−30 %) | +9,2 % (−37 %) |
| Momentum 12 Monate, 20 Aktien – mit Stichtag | +18,6 % (−25 %) | +9,6 % (−29 %) | +5,7 % (−34 %) |
| Kombi halb Bot, halb Momentum – mit Stichtag | +19,7 % (−19 %) | +9,4 % (−20 %) | +8,1 % (−22 %) |
| Branchen-Rotation (3 stärkste Branchen-ETFs) | +14,9 % (−23 %) | +6,8 % (−21 %) | +8,0 % (−18 %) |
| Nasdaq-100 nur über der 200-Tage-Linie | +18,0 % (−20 %) | +16,7 % (−31 %) | +12,5 % (−17 %) |
| Ruhige Aktien (20 mit der geringsten Schwankung) | +14,6 % (−12 %) | +9,9 % (−17 %) | +5,9 % (−13 %) |

**Ergebnis:** keine Strategie besteht – nicht übernommen.
- **Die große Lehre:** Mit der heutigen Aktienliste sah Momentum riesig aus (+26 bis +46 % im Jahr, besser als 20 von 20 Zufallsdepots). Das war eine Verzerrung: Aktien wie Palantir, Super Micro oder AppLovin kamen erst *wegen* ihres Anstiegs in den S&P 500 – Momentum kauft rückblickend genau sie. Zählt jede Aktie nur, solange sie wirklich im Index war (Liste github.com/fja05680/sp500), bleiben +8 bis +26 % – weniger als den Nasdaq-100 einfach zu halten, bei tieferen Rückgängen.
- Momentum 6 Monate schlug auch mit Stichtag in allen drei Zeiträumen 19 von 20 Zufallsdepots: ein echter, aber kleiner Auswahl-Vorteil – zu klein gegen die Rückgänge von 30–37 %.
- Branchen-Rotation, Trendfilter und ruhige Aktien waren nirgends überall besser als der Bot.
- **Warnung für alle Rückblicke:** Auch die Watchlist des Bots ist mit heutigem Wissen gewählt. Sein Rückblick (+8 bis +13 %) ist vermutlich ebenfalls etwas zu gut.

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
