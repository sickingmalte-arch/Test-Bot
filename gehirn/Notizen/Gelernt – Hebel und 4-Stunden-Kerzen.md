---
tags: [lernen, forschung]
---
# ⚡ Gelernt: Hebel und 4-Stunden-Kerzen

Stand: 27.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

Diese Notiz ändert der Bot nie. Sie hält zwei Ideen fest, die getestet und **nicht übernommen** wurden, damit sie nicht noch einmal ungeprüft eingebaut werden. Zurück zur [[Start|Startseite]] · alle Tests auf einen Blick: [[Notizen/Was der Bot schon weiß]].

> [!summary] Kurz gesagt
> - **Hebel** macht den Bot nicht besser, nur größer: mehr Rendite, aber etwa doppelt so tiefe Rückgänge. Pro Prozent Rückgang verdient er nicht mehr.
> - **4-Stunden-Kerzen** statt Tageskerzen: fast doppelt so viele Trades, doppelte Kosten, das Ergebnis je Trade fällt auf ungefähr null.

## 1. Hebel: mit geliehenem Geld handeln

**Wie der Bot es heute macht:** 1 % Risiko je Trade, eine Position höchstens 25 % des Depots, höchstens 5 Positionen, kein Kredit. Im Schnitt steckt nur **36–62 % des Geldes** in Aktien, der Rest liegt still.

**Test:** 2010–2014, 2015–2021 und 2022–2026, je mit der Watchlist und 60 anderen Aktien, Mittel aus 16 Läufen, mit Gebühren und Spread. Beim Hebel wurden Risiko je Trade und alle Obergrenzen im gleichen Verhältnis vergrößert. Auf geliehenes Geld fallen **6 % Zinsen im Jahr** an (Annahme).

| Variante (Oktober 2026) | Rendite pro Jahr (Ø der 6 Fälle) | Rendite besser | größter Rückgang |
| --- | --- | --- | --- |
| heute: 1 % Risiko, kein Kredit | 8,4 % | – | 10–16 % |
| 2 % Risiko je Trade, nur eigenes Geld | 12,9 % | 6 von 6 | 18–27 % |
| Hebel 1,5 | 12,4 % | 6 von 6 | 15–24 % |
| Hebel 2 | 15,6 % | 6 von 6 | 21–30 % |
| zum Vergleich: Nasdaq-100 (QQQ) einfach halten | 14,6–23,3 % (je Zeitraum) | – | 20–31 % |

- **Trefferquote und Ø Ergebnis je Trade bleiben gleich.** Gewinne und Verluste werden nur größer.
- **Der größte Rückgang wurde in allen 6 Fällen größer**, mit Hebel 2 etwa doppelt so groß. Aus 10.000 € wären zwischendurch etwa 7.000 € geworden.
- **Die Zinsen kosten rund 2 Prozentpunkte im Jahr.** Hebel 2 ohne Zinsen hätte +9,2 statt +7,2 Punkte gebracht.
- **Mehr Risiko mit eigenem Geld** (2 % statt 1 %) bringt fast so viel wie Hebel 1,5 – ganz ohne Kredit und Zinsen, weil heute viel Geld still liegt.
- **Der Vorteil des Bots ginge verloren.** Selbst mit Hebel 2 schafft er ungefähr nur, was einfaches Halten des Nasdaq-100 gebracht hat, bei ähnlich tiefen Rückgängen. Sein Vorteil sind die kleineren Rückgänge.
- **Der Vorsprung ist noch nicht bewiesen.** Laut Test sind es etwa +0,12 R je Trade, im Übungsdepot noch nicht bestätigt. Ist er kleiner, vervielfacht ein Hebel vor allem Kosten und Verluste.
- **Echte Hebel** (CFDs mit höchstens 5-fach bei Einzelaktien, Knock-out-Scheine, Wertpapierkredit) kosten Zinsen und Aufschläge. Eine Kurslücke kann einen Knock-out-Schein ganz wertlos machen.

**Ergebnis:** nicht übernommen. Frühestens nach dem 31.01.2027 und nur, wenn das Übungsdepot ungefähr die Erwartung trifft: als erster Schritt **1,5 % Risiko mit eigenem Geld** prüfen, einen echten Hebel erst danach, wenn überhaupt.

## 2. 4-Stunden-Kerzen statt Tageskerzen

**Idee:** Der Bot entscheidet nicht einmal am Tag mit dem Schlusskurs, sondern alle 4 Stunden mit dem aktuellen Kurs, wie beim 4H-Chart bei TradingView.

**Test:** Yahoo liefert Stundenkerzen nur für die letzten knapp 3 Jahre (ab 30.11.2023). Daraus wurden 4-Stunden-Kerzen gebaut wie bei TradingView: 9:30–13:30 und 13:30–16:00 Uhr New Yorker Zeit, also zwei Kerzen am Tag. Verglichen im selben Zeitraum: Mai–Dez. 2024, 2025 und Jan.–Okt. 2026, je mit der Watchlist und 60 anderen Aktien (ohne NBIS, dafür fehlten die Stundenkerzen), 16 Läufe, mit Gebühren und Spread. Gekauft wurde perfekt zur Eröffnung jeder 4-Stunden-Kerze – in echt wäre es schlechter (Kurse 15 Minuten verzögert, GitHub startet Läufe unzuverlässig).

| Variante | Rendite pro Jahr (Ø) | besser als heute | Trades im Jahr | Kosten im Jahr | Ø Ergebnis je Trade |
| --- | --- | --- | --- | --- | --- |
| heute: Tageskerzen | **+6,8 %** | – | 90 | 4 % des Kontos | +0,07 R |
| 4 Stunden, alles in Kerzen (wie Umschalten bei TradingView) | −1,6 % | 1 von 6 | 153 | 8 % | −0,02 R |
| 4 Stunden, aber Zeitstopp, Zahlen-Sperre und Marktfilter in Tagen wie heute | −0,3 % | 2 von 6 | 152 | 8 % | 0,00 R |

- **Mehr Rauschen:** Auf kurzen Kerzen springen die Strategien öfter an, die Signale taugen aber weniger.
- **Doppelte Kosten:** fast doppelt so viele Trades, Gebühren und Spread fressen den kleinen Vorsprung auf.
- **Engere Stops:** 3 ATR auf 4-Stunden-Kerzen liegen viel näher am Kurs, Kurssprünge und Spread wiegen schwerer.
- **Live-Kurs:** Der Bot kauft schon heute zum Live-Kurs (Eröffnung, nur bis zum Limit), und die Live-Kette verfolgt Stop und Ziel etwa alle 15 Minuten. Nur die Entscheidung, *ob* er kauft, fällt mit dem fertigen Tageskurs, weil die Strategien so getestet sind.
- **Vorsicht:** Nur knapp 3 Jahre Daten, also eine einzige Marktphase. Das Ergebnis ist trotzdem deutlich.

**Ergebnis:** nicht übernommen. Der Bot bleibt bei Tageskerzen.

## Meine Gedanken

