---
tags: [lernen, forschung]
---
# 🧪 Gelernt: Muster, Lehrbücher und weitere Ideen

Stand: 27.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

Diese Notiz ändert der Bot nie. Sie hält fest, was aus dem Poster „Candlestick Patterns & Chart Patterns“, dem Blatt „Chart Pattern“ von Finanzradar, den beiden Lehrbüchern und weiteren Ideen vom Oktober 2026 getestet wurde. So werden dieselben Ideen nicht noch einmal ungeprüft eingebaut. Zurück zur [[Start|Startseite]] · siehe auch [[Notizen/Wissen – Kerzen- und Chartmuster]], [[Notizen/Wissen – Traden lernen (Lehrbücher)]] und [[Lehren]].

## So wurde getestet

- **Zeiträume:** 2010–2014, 2015–2021 und 2022–2026
- **Aktien:** jeweils die Watchlist und 60 andere Aktien
- **Rechnung:** Mittel aus 16 Läufen, mit Gebühren und Spread, ohne Shorts
- **Regel:** Übernommen wird nur, was überall hilft oder zumindest nirgends erkennbar schadet.

## Poster: Kerzen- und Chartmuster

| Idee | Rendite besser | Ø Rendite pro Jahr | größter Rückgang größer |
| --- | --- | --- | --- |
| nur kaufen, wenn ein bullisches Kerzenmuster bestätigt | 2 von 6 | −0,9 Punkte (−4,9 bis +4,1) | 2 von 6 |
| nicht kaufen bei bärischem Kerzenmuster | 1 von 6 | −1,5 (−4,9 bis +1,0) | 5 von 6 |
| Signale mit bullischem Kerzenmuster zuerst kaufen | 2 von 6 | −0,7 (−2,9 bis +0,4) | 0 von 6 |
| variables Ziel bei Ausbrüchen (Höhe der Seitwärtsphase) | 4 von 6 | +0,3 (−1,9 bis +3,3) | 1 von 6 |
| variables Ziel am nächsten Widerstand (6-Monats-Hoch) | 1 von 6 | −1,8 (−5,8 bis +2,4) | 6 von 6 |
| neue Strategie Doppelboden (W), Ziel = Nackenlinie + Höhe | 1 von 6 | −0,7 (−1,8 bis +0,5) | 1 von 6 |

- **Doppelboden allein:** 35–60 % Treffer. Das Ziel lag im Mittel 2- bis 2,5-mal so weit weg wie der Stop. Ergebnis je Trade von −0,14 bis +0,34 R, in 3 von 6 Fällen im Minus.
- **Variables Ziel bei Ausbrüchen:** Das kam am nächsten heran. 2015–2021 mit den 60 anderen Aktien waren es aber −1,9 Punkte, deshalb nicht übernommen.

## Finanzradar-Blatt: Chartmuster als eigene Strategien

Das Blatt zeigt 20 Chartmuster mit Einstieg, Stop und Ziel: rechts die Muster zum Kaufen, links die gespiegelten Muster für Shorts. Getestet wurden 8 Mustergruppen in beide Richtungen: Doppel-, Dreifachboden, Kopf-Schulter, Rechteck, Dreieck, Flagge, Keil und Tasse. Gekauft wird am Tag des Ausbruchs, das Ziel ist die Höhe des Musters.

- **Stop vom Blatt (1 ATR hinter der Ausbruchslinie):** Er ist zu eng und wird oft ausgelöst. Flagge, Tasse, Dreieck und Rechteck waren damit schlechter.
- **Stop wie beim Bot (3 ATR vom Schlusskurs):** Damit sind die Muster zum Kaufen leicht im Plus, aber nicht besser als die Strategien, die der Bot schon hat.

| Muster zum Kaufen (Stop wie beim Bot) | im Plus | Ø Ergebnis je Trade |
| --- | --- | --- |
| Flagge/Wimpel | 6 von 6 | +0,14 R |
| Dreieck | 6 von 6 | +0,10 R |
| Keil | 6 von 6 | +0,09 R |
| Dreifachboden | 5 von 6 | +0,11 R |
| Rechteck (nur 43 Trades in 16 Jahren) | 5 von 6 | +0,18 R |
| Tasse/Rounding Bottom | 5 von 6 | +0,13 R |
| Doppelboden | 3 von 6 | +0,01 R |
| umgekehrte Kopf-Schulter | 3 von 6 | +0,07 R |

**Shorts mit der linken Seite:** Alle 8 Short-Muster verlieren im Schnitt.
- Mit Marktfilter sind sie in 0 bis 2 von 6 Fällen im Plus, im Schnitt −0,06 bis −0,34 R je Trade.
- Ohne Marktfilter sind sie ebenfalls im Minus. Nur das fallende Rechteck lag in 3 von 6 Fällen im Plus, aber mit nur 20 Trades in 16 Jahren.

**Im Übungsdepot:**

| Idee | Rendite besser | Ø Rendite pro Jahr | Trefferquote | größter Rückgang größer |
| --- | --- | --- | --- | --- |
| alle 8 Muster zum Kaufen als neue Strategien | 2 von 6 | −0,1 Punkte (−2,2 bis +1,9) | +0,3 Punkte | 3 von 6 |
| nur die 6 Muster, die 2015–2021 gut waren | 2 von 6 | −0,5 (−2,7 bis +1,9) | +0,2 | 2 von 6 |
| alle 8 mit dem engen Stop vom Blatt | 3 von 6 | +0,2 (−1,8 bis +1,6) | −1,2 | 3 von 6 |
| Mitsprechen als Bestätigung: alte Strategien kaufen nur, wenn in den letzten 10 Tagen ein Muster ausbrach | 1 von 6 | −4,1 (−9,3 bis +0,6) | +0,6 | 3 von 6 |
| Mitsprechen als Vorrang: Signale mit Muster zuerst kaufen | 2 von 6 | −0,3 (−1,2 bis +0,5) | +0,1 | 0 von 6 |

**Warum es nichts bringt:**
- Der Bot hat schon genug gute Signale. Die Grenze ist das Risiko pro Trade, nicht die Zahl der Signale. Neue Muster verdrängen nur andere, ähnlich gute Käufe.
- Als Bestätigung lassen die Muster rund 40 % der Käufe weg, auch viele gute.

## Lehrbücher

| Idee | Rendite besser | Ø Rendite pro Jahr | größter Rückgang größer |
| --- | --- | --- | --- |
| Trend-Strategien nur bei ADX ab 20 (Trend stark genug) | 2 von 6 | −1,5 (−4,0 bis +1,4) | 3 von 6 |
| … nur bei ADX ab 25 | 1 von 6 | −3,5 (−6,1 bis +2,8) | 4 von 6 |
| Wochentrend: nur kaufen über der steigenden 150-Tage-Linie (≈ 30 Wochen) | 3 von 6 | +0,1 (−2,3 bis +2,6) | 4 von 6 |
| neue Strategie Fibonacci-Rücksetzer (38,2–61,8 %, Ziel = letztes Hoch) | 2 von 6 | −1,4 (−4,0 bis +2,5) | 5 von 6 |

Vieles aus den Büchern macht der Bot schon, z. B. die 1-%-Regel, den Stop bei jedem Trade, das Tagebuch und Ausbrüche. Mehrere Indikatoren zur Bestätigung und Ausstiege nach Signal (z. B. Parabolic SAR) waren schon früher getestet und nicht besser.

## Weitere Ideen vom Oktober 2026

- **Mehr Aktien (84 statt 24):** Die Rendite war in allen drei Zeiträumen schlechter:
  - 2010–2014: 9,2 → 8,2 %
  - 2015–2021: 12,7 → 7,5 %
  - 2022–2026: 6,4 → 4,4 %

  Der Bot macht damit kaum mehr Trades. Das freie Geld kommt von den Risikogrenzen, nicht von zu wenig Signalen.
- **Mehr Positionen (bis 15):**
  - Nur die Zahl erhöhen: −0,6 Punkte.
  - Mit 10–15 % Risiko zusammen: im Schnitt +1,3 bis +2,1 Punkte, aber nur in 4 von 6 Fällen. Der größte Rückgang wird in 5–6 von 6 Fällen größer, bis 24 % statt 16 %.
  - 15 kleine Positionen mit ⅓ % Risiko: −6,3 Punkte, weil die Gebühren den Gewinn fressen.
- **Shorts (auf fallende Kurse):** Alle 8 Short-Strategien verlieren in allen 6 Fällen (−0,47 bis −0,02 R je Trade). Ebenfalls getestet und nicht besser:
  - sieben Verbesserungen: nur im echten Abwärtsmarkt, nur schwache Aktien, näheres Ziel, nur Gegenbewegungen und Kombinationen
  - drei Short-Strategien aus einem Bild: Bruch der 200-Tage-Linie, Bruch der Unterstützung, RSI über 70

  Bis die Abwärtsphase erkennbar ist, ist der Rückgang meist vorbei. Danach erholen sich Aktien oft schnell.
- **Absicherung mit einem Nasdaq-100-Short** (unter der 200-Tage-Linie, 25–100 % des Depots): überall weniger Rendite und größere Rückgänge. Der Short brachte nur 2022 Geld (+12 %) und verlor sonst in jedem Jahr mit Short-Phasen.
- **Insider-Käufe als Zusatzinformation:** Der Datendienst (Quiver) braucht ein bezahltes Abo, deshalb nicht getestet.

## Was der Bot jetzt stattdessen macht

- **Kerzenmuster, Musterziel und Nachrichten-Stimmung** zeigt er bei jedem Signal als Info: im Handelsplan, auf der Übersichtsseite und in der Trade-Notiz.
- **Auf [[Lehren]] prüft er laufend**, ob Signale mit Muster oder mit guten Nachrichten besser laufen. Die Nachrichten-Stimmung sammelt er ab jetzt.
- **Neu getestet wird erst**, wenn eine Gruppe dort über viele Trades deutlich besser ist.

## Meine Gedanken

