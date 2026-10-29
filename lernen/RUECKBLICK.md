# 📜 Lernmodell des Swing-Bots – Rückblick 2010–2026

Stand: 2026-10-29 · 518 Aktien aus S&P 500 und Nasdaq-100 · 490.135 Kauf-Signale seit 2008, davon 463.420 mit Ergebnis

So wurde gerechnet:

- **Walk-forward:** Das Lernmodell wird für jeden Monat neu trainiert, und zwar nur mit Trades, deren Ergebnis vor Monatsbeginn schon feststand. Die Signale des Monats selbst hat es nie gesehen.
- **Depot wie beim Übungsdepot:** 10.000 €, 1 % Risiko je Trade, höchstens 5 Positionen und 2 aus derselben Branche, höchstens 25 % je Position und 5 % Risiko zusammen, Kauf zur nächsten Eröffnung bis zum Limit, 1 € Gebühr und 0,1 % Spread je Order, Kurse in Euro.
- **16 Läufe je Zeitraum:** Bei Gleichstand entscheidet eine zufällige Reihenfolge der Aktien; gezeigt ist der Durchschnitt.

## Rendite pro Jahr / größter Rückgang

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| **Jetziger Bot** (Watchlist, Marktfilter, Lernregel) | +9,2 % / −17 % | +10,5 % / −17 % | +7,0 % / −16 % |
| **Bot + Lernmodell:** beste Punktzahl zuerst (kein Filter) | +6,1 % / −19 % | +14,6 % / −16 % | +10,1 % / −18 % |
| **Bot + Lernmodell:** nur beste 50 %, beste zuerst | +2,7 % / −21 % | +11,7 % / −13 % | +5,7 % / −13 % |
| **Bot + Lernmodell:** nur beste 30 %, beste zuerst | +3,2 % / −13 % | +7,6 % / −12 % | +3,9 % / −11 % |
| **Bot + Lernmodell:** nur beste 30 % (Reihenfolge wie heute) | +3,8 % / −14 % | +6,2 % / −14 % | +4,3 % / −13 % |
| Watchlist: Signale wie heute, ohne Modell | +12,7 % / −16 % | +10,1 % / −21 % | +6,0 % / −15 % |
| Watchlist: Lernmodell beste 50 % | +9,6 % / −20 % | +13,4 % / −15 % | +8,8 % / −13 % |
| Watchlist: Lernmodell beste 30 % | +5,7 % / −11 % | +9,7 % / −13 % | +6,1 % / −12 % |
| Watchlist: ohne Modell · Stop zum Schluss | +7,5 % / −10 % | +8,9 % / −13 % | +3,2 % / −10 % |
| Watchlist: ohne Modell · Panik-Regel | +7,6 % / −11 % | +7,1 % / −12 % | +2,8 % / −11 % |
| Watchlist: ohne Modell · starke Aktien halten | +9,9 % / −14 % | +11,9 % / −15 % | +4,4 % / −12 % |
| Watchlist: Lernmodell 30 % · Stop zum Schluss | +3,2 % / −10 % | +6,8 % / −9 % | +4,6 % / −7 % |
| Watchlist: Lernmodell 30 % · Panik-Regel | +3,3 % / −8 % | +6,8 % / −9 % | +3,5 % / −8 % |
| Watchlist: Lernmodell 30 % · starke Aktien halten | +4,5 % / −9 % | +9,5 % / −10 % | +4,2 % / −12 % |
| Alle Aktien: Signale wie heute, ohne Modell | +8,3 % / −24 % | +5,7 % / −26 % | +0,3 % / −20 % |
| Alle Aktien: Lernmodell beste 30 % | +11,6 % / −16 % | +3,2 % / −18 % | +4,0 % / −23 % |
| Alle Aktien: Lernmodell 30 % + Marktfilter | +10,2 % / −18 % | +2,2 % / −17 % | +3,2 % / −21 % |
| Alle Aktien: Lernmodell 30 % · Panik-Regel | +7,4 % / −12 % | +1,9 % / −14 % | +3,3 % / −15 % |
| Watchlist: Lernmodell 30 % ohne Bilanzdaten | +7,9 % / −15 % | +10,6 % / −11 % | +6,5 % / −13 % |
| Alle Aktien: Lernmodell 30 % ohne Bilanzdaten | +10,7 % / −17 % | +6,8 % / −23 % | +8,6 % / −25 % |
| S&P 500 kaufen und halten | +19,2 % / −21 % | +15,8 % / −33 % | +12,3 % / −23 % |
| Nasdaq-100 kaufen und halten | +22,9 % / −20 % | +23,3 % / −31 % | +13,9 % / −30 % |

## Trefferquote / Ø Ergebnis je Trade / Trades pro Jahr

| | 2010–2014 | 2015–2021 | 2022–2026 |
|---|---:|---:|---:|
| **Jetziger Bot** (Watchlist, Marktfilter, Lernregel) | 56 % / 0,11 R / 92 | 58 % / 0,11 R / 96 | 57 % / 0,11 R / 82 |
| **Bot + Lernmodell:** beste Punktzahl zuerst (kein Filter) | 55 % / 0,07 R / 94 | 62 % / 0,15 R / 95 | 60 % / 0,57 R / 81 |
| **Bot + Lernmodell:** nur beste 50 %, beste zuerst | 54 % / 0,10 R / 70 | 60 % / 0,17 R / 73 | 58 % / 0,10 R / 66 |
| **Bot + Lernmodell:** nur beste 30 %, beste zuerst | 55 % / 0,06 R / 54 | 60 % / 0,12 R / 56 | 57 % / 0,09 R / 50 |
| **Bot + Lernmodell:** nur beste 30 % (Reihenfolge wie heute) | 56 % / 0,08 R / 53 | 58 % / 0,10 R / 56 | 58 % / 0,10 R / 49 |
| Watchlist: Signale wie heute, ohne Modell | 58 % / 0,13 R / 100 | 57 % / 0,09 R / 107 | 55 % / 0,06 R / 103 |
| Watchlist: Lernmodell beste 50 % | 59 % / 0,16 R / 81 | 62 % / 0,17 R / 84 | 58 % / 0,12 R / 87 |
| Watchlist: Lernmodell beste 30 % | 58 % / 0,09 R / 62 | 61 % / 0,13 R / 68 | 57 % / 0,10 R / 67 |
| Watchlist: ohne Modell · Stop zum Schluss | 59 % / 0,12 R / 95 | 60 % / 0,21 R / 100 | 55 % / 0,05 R / 99 |
| Watchlist: ohne Modell · Panik-Regel | 58 % / 0,12 R / 99 | 58 % / 0,18 R / 105 | 54 % / 0,04 R / 104 |
| Watchlist: ohne Modell · starke Aktien halten | 59 % / 0,12 R / 99 | 60 % / 0,21 R / 103 | 55 % / 0,06 R / 101 |
| Watchlist: Lernmodell 30 % · Stop zum Schluss | 59 % / 0,09 R / 58 | 64 % / 0,28 R / 64 | 60 % / 0,13 R / 63 |
| Watchlist: Lernmodell 30 % · Panik-Regel | 59 % / 0,09 R / 61 | 62 % / 0,28 R / 66 | 57 % / 0,10 R / 67 |
| Watchlist: Lernmodell 30 % · starke Aktien halten | 58 % / 0,10 R / 61 | 63 % / 0,29 R / 66 | 57 % / 0,10 R / 65 |
| Alle Aktien: Signale wie heute, ohne Modell | 57 % / 0,09 R / 98 | 55 % / 0,03 R / 101 | 51 % / 0,00 R / 96 |
| Alle Aktien: Lernmodell beste 30 % | 61 % / 0,15 R / 98 | 58 % / 0,03 R / 98 | 54 % / 0,06 R / 101 |
| Alle Aktien: Lernmodell 30 % + Marktfilter | 60 % / 0,13 R / 91 | 57 % / 0,01 R / 89 | 56 % / 0,07 R / 78 |
| Alle Aktien: Lernmodell 30 % · Panik-Regel | 61 % / 0,13 R / 98 | 58 % / -0,00 R / 96 | 55 % / 0,07 R / 101 |
| Watchlist: Lernmodell 30 % ohne Bilanzdaten | 59 % / 0,18 R / 63 | 61 % / 0,16 R / 67 | 55 % / 0,64 R / 66 |
| Alle Aktien: Lernmodell 30 % ohne Bilanzdaten | 60 % / 0,16 R / 98 | 58 % / 0,06 R / 100 | 57 % / 0,11 R / 104 |

1 R = der geplante Verlust bis zum Stop. Kaufen und halten hat keine Trades.

## Trennt das Lernmodell gute von schlechten Signalen?

Alle 411.712 Signale seit 2010 mit Ergebnis, nach der Punktzahl in fünf gleich große Gruppen geteilt:

| Punktzahl | Trefferquote | Ø Ergebnis |
|---|---:|---:|
| bestes Fünftel | 58 % | 0,06 R |
| 2. Fünftel | 56 % | 0,05 R |
| Mitte | 54 % | 0,03 R |
| 4. Fünftel | 54 % | 0,03 R |
| schlechtestes Fünftel | 57 % | 0,09 R |

Trennschärfe (AUC): **0,506** (0,50 = Münzwurf). Je Jahr: 2010: 0,42, 2011: 0,51, 2012: 0,54, 2013: 0,50, 2014: 0,49, 2015: 0,55, 2016: 0,58, 2017: 0,52, 2018: 0,49, 2019: 0,57, 2020: 0,48, 2021: 0,56, 2022: 0,46, 2023: 0,45, 2024: 0,57, 2025: 0,53, 2026: 0,51.

Ohne Bilanzdaten (nur Chart, Momentum, Quartalszahlen-Termine, Markt, Branche): AUC 0,505.

## Bilanzdaten (Value, Growth, Qualität)

Quelle: SEC EDGAR – jede Zahl mit dem Tag, an dem sie veröffentlicht wurde; das Modell sieht sie erst ab dem Tag danach, spätere Korrekturen erst ab ihrem eigenen Datum. Damit dürfen Value und Growth auch im Rückblick getestet werden. Anteil der Signale mit Bewertung (Gewinnrendite) je Jahr:

2008: 0 % · 2009: 1 % · 2010: 37 % · 2011: 73 % · 2012: 88 % · 2013: 88 % · 2014: 90 % · 2015: 91 % · 2016: 91 % · 2017: 90 % · 2018: 91 % · 2019: 92 % · 2020: 92 % · 2021: 93 % · 2022: 96 % · 2023: 95 % · 2024: 96 % · 2025: 97 % · 2026: 98 %

Gewinnüberraschung (von Yahoo, nur die letzten rund 25 Quartale): 2008: 97 % · 2009: 97 % · 2010: 96 % · 2011: 97 % · 2012: 98 % · 2013: 97 % · 2014: 97 % · 2015: 97 % · 2016: 98 % · 2017: 97 % · 2018: 98 % · 2019: 98 % · 2020: 98 % · 2021: 98 % · 2022: 99 % · 2023: 99 % · 2024: 99 % · 2025: 100 % · 2026: 100 %

## Häufigste Fehler – und meidet das Modell sie?

Alle 411.712 gedachten Trades seit 2010: verloren 44 %. Von den 124.566, die das Modell gekauft hätte (beste 30 %): verloren 43 %.

| Warum verloren? | bei allen Signalen | bei der Auswahl des Modells |
|---|---:|---:|
| Absturz des Gesamtmarkts | 12,2 % | 14,4 % |
| Zeitstopp ohne Schwung | 11,5 % | 10,4 % |
| Quartalszahlen | 9,3 % | 6,6 % |
| Normales Auf und Ab (kein besonderer Grund) | 7,8 % | 7,9 % |
| Branche schwach | 5,9 % | 5,4 % |
| Stop zu eng (Kurs war danach schnell wieder über dem Einstieg) | 5,7 % | 6,8 % |
| Signal zu spät (Aktie war schon weit gelaufen) | 3,5 % | 2,0 % |
| Kurslücke unter den Stop (über Nacht) | 3,1 % | 3,1 % |
| Plötzlicher Einbruch nur dieser Aktie (vermutlich eine Nachricht) | 0,9 % | 0,7 % |

Anteil an allen Trades (nicht nur an den Verlusten); ein Trade kann mehrere Gründe haben.

## Was das Modell gelernt hat (die 15 wichtigsten Merkmale)

| Merkmal | Wichtigkeit | Richtung |
|---|---:|---|
| Markt 3 Monate | 11,5 | nur im Zusammenspiel |
| Anteil Aktien über 50-Tage-Linie | 10,7 | je niedriger, desto besser |
| Markt 1 Woche | 5,6 | je niedriger, desto besser |
| Chance/Risiko | 4,8 | je niedriger, desto besser |
| Branche über 50-Tage-Linie | 2,8 | je niedriger, desto besser |
| Tage bis zu den Quartalszahlen | 2,6 | nur im Zusammenspiel |
| VIX-Anstieg 1 Woche | 2,0 | nur im Zusammenspiel |
| Momentum 12 Monate ohne letzten Monat | 1,8 | nur im Zusammenspiel |
| Markt 1 Monat | 1,7 | je niedriger, desto besser |
| letzte Gewinnüberraschung | 1,4 | nur im Zusammenspiel |
| Stärke der Branche (1 Monat) | 1,0 | nur im Zusammenspiel |
| schon gelaufen (vom 10-Tage-Tief) | 1,0 | je niedriger, desto besser |
| Stärke gegenüber dem S&P 500 (3 Monate) | 0,9 | nur im Zusammenspiel |
| Momentum 6 Monate | 0,7 | nur im Zusammenspiel |
| Gewinnrendite (1/KGV) | 0,7 | nur im Zusammenspiel |

Wichtigkeit: Um so viele Tausendstel sinkt die Trennschärfe, wenn man das Merkmal durcheinanderwürfelt (Modell bis 12 Monate vor Schluss, geprüft an den 12 Monaten danach).

## Ehrlich bleiben

- **Überlebens-Verzerrung:** Getestet wurden die Aktien, die HEUTE im S&P 500 oder Nasdaq-100 sind. Firmen, die seit 2010 herausgefallen, übernommen worden oder pleite gegangen sind, fehlen. Dadurch sieht der Rückblick für alle Varianten zu gut aus – auch für den jetzigen Bot. Kaufen und halten ist davon nicht betroffen (der Index-Fonds hatte die Verlierer damals wirklich).
- **Bilanzdaten:** nur mit Veröffentlichungsdatum (SEC). Vor 2009 gibt es keine, Firmen ohne US-Bilanz (z. B. ASML) haben keine. Die Gewinnüberraschung von Yahoo reicht nur einige Jahre zurück.
- **Kosten** (Gebühr und Spread) sind abgezogen, Steuern nicht.

