---
tags: [wissen, forschung, tageshandel]
---
# 📦 Wissen – Day-Trader-Skill (11 Bausteine für den Tageshandel)

Stand: 11.11.2026 · Wunsch des Nutzers: „alles kontrollieren, einbauen, was den Bot verbessert – vorher prüfen und dann entscheiden“. Zurück zur [[Start|Startseite]] · alle Tests: [[Notizen/Was der Bot schon weiß]] · Tagebuch: [[Notizen/Forschung – Tagebuch]].

**Quelle:** [github.com/Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT-Lizenz, Version vom 20.10.2026, „The Trader skill v2“). Elf Claude-Skills mit einfachen Python-Skripten, die freie Daten lesen (Yahoo, Nasdaq Trader, SEC EDGAR, House Clerk). Der Skill sagt selbst: „Most people who day trade lose money“, und sein eigenes Beispiel (Tesla am 19.10.2026) endet in der Zeitmaschine bei „close to a coin flip“.

## Was drin ist

| Baustein | Was er macht | Für unseren Bot |
|---|---|---|
| Scanner | 5 Tages-Setups (20-Tage-Schlusshoch, Bullen-Flagge, zurück über die 20-Tage-Linie, überverkauft, Abpraller) und der Ausbruch aus der Eröffnungsspanne | **geprüft** (6 Tests) |
| Einstieg (entry) | Einstieg erst, wenn eine Kerze über der Marke **schließt**, auf Wunsch mit Volumen-Bestätigung | macht der Bot schon (Schlusskurs); Volumen schon früher geprüft, nicht übernommen |
| Ausstieg (exit) | Stop und Ziel vor dem Kauf, Stop in der Mitte der Eröffnungsspanne, Ziel 1R oder 2R, raus vor Börsenschluss | macht der Bot schon (Stop/Ziel vorher); 1R/2R und „raus zum Schluss“ im Tageshandel-Test geprüft |
| Zeitmaschine | spielt den Trade 10.000-mal mit den eigenen letzten 60 Tagen der Aktie nach und zeigt, wie dieselbe Regel früher bei dieser Aktie lief | **geprüft** (2 Tests: Nachspielen, Geschichte) |
| Risiko (risk) | höchstens 3 Käufe am Tag, Tagesverlust-Grenze, Chance-Risiko mindestens 1,0, Barreserve | **geprüft** (2 Tests); Tagesverlust-Grenze entspricht bei 1 % Risiko je Trade genau den 3 Käufen |
| Budget | Stückzahl aus dem höchsten Verlust je Trade | macht der Bot schon genauso (1 % Risiko je Trade) |
| Broker | schickt Aufträge an Alpaca oder Interactive Brokers | **verboten** – keine Anbindung für echtes Geld, auch nicht vorbereitet |
| Preis-Alarme | meldet Stop, Ziel und Börsenschluss | Komfort, keine bessere Rendite; Live rechnet schon alle 15 Minuten |
| Nachrichten | Schlagzeilen und 8-K-Meldungen bei der SEC, mit Schlagworten | der Bot hat schon die Nachrichten-Regel; ein Rückblick mit 8-K-Meldungen über 16 Jahre wäre sehr aufwendig – nicht geprüft |
| Quartalszahlen (analyst) | liest Umsatz, Marge und Gewinn aus SEC-Daten | das Lernmodell nutzt SEC-Bilanzdaten schon (geprüft, nicht übernommen) |
| Pelosi-Tracker | Aktienkäufe von Kongress-Mitgliedern | **nicht prüfbar**: Die Daten gibt es nur als PDFs beim House Clerk, gemeldet bis zu 45 Tage nach dem Kauf, beim Senat nur von Hand, und Quiver (unser Datendienst) liefert sie ohne Abo nicht |

## Was geprüft wurde – 10 Tests, alles vorher festgelegt

Rückblick 2010–2026 mit dem echten Bot auf der Watchlist, mit Gebühr und Spread, 8 Läufe je Zeitraum, je 6 Gegenproben mit Zufall. Übernommen würde nur, was in **allen drei Zeiträumen** besser ist und **den Zufall schlägt**. Die Regeln des Skills sind neu geschrieben (`forschung/skill_hilfe.py`, `forschung/ideen/skill_*.py`); der fremde Code wurde nicht ausgeführt.

| Test | Pkt 2010–14 / 2015–21 / 2022–26 | Ergebnis |
|---|---|---|
| Bullen-Flagge als neue Strategie | +1,3 / +1,1 / +0,2 | überall besser, **aber nicht besser als Zufall**: zufällige Zusatz-Käufe waren genauso gut (bis +13,9 % und +7,9 % statt +13,7 % und +7,4 %) |
| Überverkauft (RSI 14 unter 30) | −0,1 / +0,6 / +0,9 | nicht überall besser |
| Abpraller nach Überverkauft | +0,3 / −0,6 / ±0,0 | nicht überall besser |
| 20-Tage-Schlusshoch-Ausbruch | −0,9 / −0,4 / +0,3 | nicht überall besser |
| Zurück über die 20-Tage-Linie | −1,2 / +0,8 / ±0,0 | nicht überall besser |
| Höchstens 3 Käufe am Tag | +0,9 / −1,0 / +1,4 | nicht überall besser |
| Chance-Risiko mindestens 1,0 | −2,2 / +0,2 / −0,1 | nicht überall besser (ohne die Gegenbewegungs-Strategien fehlen deren Gewinne) |
| Zeitmaschine als Filter (1.000 Wiederholungen aus 60 Tagen) | −2,6 / +0,9 / +2,4 | nicht überall besser |
| Geschichte als Filter (Regel lief bei dieser Aktie schlecht → nicht kaufen) | −3,6 / −3,2 / +0,3 | deutlich schlechter |

**Tageshandel mit dem Ausbruch aus der Eröffnungsspanne** (eigener Test, Stunden-Kerzen der letzten 2 Jahre und 5-Minuten-Kerzen der letzten 60 Tage, 24 Aktien, Spread 0,1 % je Order):

| Variante | Trades | Ø Ergebnis je Trade nach Spread | Zufalls-Einstiege zur gleichen Uhrzeit | Urteil |
|---|---:|---:|---:|---|
| Stunden-Kerzen, Ziel 1R | 5.440 | −0,18 R | −0,19 R | nicht besser als Zufall |
| Stunden-Kerzen, Ziel 2R | 5.440 | −0,18 R | −0,19 R | nicht besser als Zufall |
| 5-Minuten-Kerzen, Ziel 1R | 755 | −0,30 R | −0,26 R | nicht besser als Zufall |
| 5-Minuten-Kerzen, Ziel 2R | 755 | −0,28 R | −0,27 R | nicht besser als Zufall |

R = Vielfaches des geplanten Risikos. −0,18 R heißt: Bei 100 € Risiko je Trade gehen im Schnitt 18 € verloren – vor allem durch den Spread, der im Tageshandel im Verhältnis zum engen Stop sehr teuer ist.

## Ergebnis

- **Nichts davon kommt in den Bot.** Keine der 10 Ideen war in allen drei Zeiträumen besser und zugleich besser als Zufall.
- **Am nächsten dran war die Bullen-Flagge.** Sie war überall etwas besser, aber zufällige Zusatz-Käufe brachten genauso viel. Der Gewinn kommt also wohl daher, dass der Bot öfter kauft, nicht vom Muster selbst. Bei 13 Vergleichen kann außerdem einer zufällig gut aussehen.
- **Der Tageshandel verliert nach Kosten** und ist nicht besser als zufällige Einstiege zur gleichen Uhrzeit. Das passt zum Skill selbst, dessen eigenes Beispiel ein Münzwurf war. Außerdem könnte unser Bot gar nicht minutengenau handeln: Die Live-Kurse kommen 15 Minuten verzögert.
- **Das deckt sich mit allem bisher:** Feste Kaufregeln sind kaum besser als Zufall. Mehr bringt ehrliches Messen und Kosten sparen als neue Muster.

## Gut zu wissen

- Die guten Grundsätze des Skills hat der Bot schon: Stop und Ziel vor dem Kauf, Positionsgröße aus dem Risiko, Schlusskurs statt Docht, nichts ohne Prüfung, Papierhandel.
- Ehrlich ist der Skill an einer Stelle besonders: Die Zeitmaschine sagt offen „Münzwurf“, wenn es einer ist. Genau so prüft auch unser Prüfstand – mit Gegenprobe.

## Quellen

- Skill und Code: https://github.com/Jakeschincariol/day-trader-skill (README, trader-*/SKILL.md, trader-scanner/scan.py)
- Ergebnisse: `forschung/ergebnisse/skill_*.md`
