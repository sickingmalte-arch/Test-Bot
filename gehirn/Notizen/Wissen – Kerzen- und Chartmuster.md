---
tags: [wissen, chartanalyse]
---
# 🕯️ Wissen: Kerzen- und Chartmuster

Stand: 27.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

Diese Notiz ändert der Bot nie. Sie fasst das Poster „Candlestick Patterns & Chart Patterns“ zusammen und sagt, was der Bot davon nutzt. Was im Test herauskam: [[Notizen/Gelernt – Muster und Lehrbücher]]. Zurück zur [[Start|Startseite]] · siehe auch [[Lehren]].

## Was eine Kerze zeigt

Jede Kerze ist ein Handelstag. Der **Körper** reicht von der Eröffnung bis zum Schluss. Grün (oder weiß) heißt, der Kurs schloss höher als er eröffnete. Rot (oder schwarz) heißt, er schloss tiefer. Die **Dochte** (Schatten) zeigen das Hoch und das Tief des Tages. Ein langer unterer Docht heißt: Die Verkäufer drückten den Kurs, aber die Käufer holten ihn zurück.

## Kerzenmuster, die der Bot erkennt

**Bullisch** (nach dem Poster ein Zeichen, dass der Kurs steigen könnte):

| Muster | So sieht es aus |
| --- | --- |
| Bullish Engulfing | eine grüne Kerze, deren Körper die rote Kerze vom Vortag ganz umschließt |
| Hammer | nach einem Rückgang: kleiner Körper oben, langer unterer Docht (mindestens doppelt so lang wie der Körper) |
| Bullish Harami | nach einer langen roten Kerze eine kleine grüne, die ganz im Körper der roten liegt |
| Piercing Line | nach einer langen roten Kerze eröffnet der Kurs tiefer und schließt über der Mitte der roten Kerze |
| Morning Star | lange rote Kerze, dann eine kleine Kerze, dann eine grüne, die über der Mitte der ersten schließt |
| Three White Soldiers | drei grüne Kerzen hintereinander, jede schließt höher als die davor |

**Bärisch** (ein Zeichen, dass der Kurs fallen könnte):

| Muster | So sieht es aus |
| --- | --- |
| Bearish Engulfing | eine rote Kerze, deren Körper die grüne Kerze vom Vortag ganz umschließt |
| Shooting Star | nach einem Anstieg: kleiner Körper unten, langer oberer Docht |
| Hanging Man | nach einem Anstieg: sieht aus wie ein Hammer – aber an einem Hoch |
| Evening Star | lange grüne Kerze, dann eine kleine Kerze, dann eine rote, die unter der Mitte der ersten schließt |
| Dark Cloud Cover | nach einer langen grünen Kerze eröffnet der Kurs höher und schließt unter der Mitte der grünen Kerze |
| Three Black Crows | drei rote Kerzen hintereinander, jede schließt tiefer als die davor |

Das Poster zeigt noch viele weitere (Doji Star, Kicking, Tasuki Gap, Abandoned Baby …). Sie sind selten oder ähneln den obigen. Der Bot erkennt die zwölf häufigsten.

## Chartmuster vom Poster

- **Umkehrmuster:** Doppeltop (M) und Doppelboden (W), Kopf-Schulter und umgekehrte Kopf-Schulter, steigender und fallender Keil. Einstieg beim Bruch der **Nackenlinie**, Ziel = Höhe des Musters von der Nackenlinie aus gemessen.
- **Fortsetzungsmuster:** Rechteck, Wimpel (Flagge), Keil. Nach einer Seitwärtsphase geht es meist in die alte Richtung weiter. Ziel = Höhe der Seitwärtsphase nach dem Ausbruch noch einmal.
- **Dreiecke:** steigendes Dreieck (oft Ausbruch nach oben), fallendes Dreieck (oft nach unten), symmetrisches (beide Richtungen möglich).

## Was der Bot damit macht

- **Ausbrüche aus Seitwärtsphasen** handelt er schon lange: Strategien „Ausbruch“ (über das 20-Tage-Hoch mit viel Volumen), „Squeeze-Ausbruch“ (nach einer ruhigen Phase) und „ATR-Ausbruch“. Das entspricht Rechteck, Wimpel und Dreieck auf dem Poster.
- **Bei jedem Signal zeigt er die Kerzenmuster** des Tages, bei Ausbrüchen und Doppelböden das **Musterziel**, und in der Trade-Notiz das Muster am Signaltag.
- **Er kauft und verkauft nicht danach.** Als Bestätigung, Warnung, Vorrang oder als Ziel hat das im Test über 16 Jahre nicht geholfen. Die Selbstkontrolle auf [[Lehren]] zeigt laufend, ob Signale mit Muster besser laufen.

## Warum Muster weniger bringen, als das Poster verspricht

1. **Sie sind auf dem Poster sauber gezeichnet.** In echten Kursen sind sie unscharf, und dieselbe Kerze kann man unterschiedlich lesen.
2. **Jeder kennt sie.** Was alle sehen, ist meist schon im Kurs drin.
3. **Ein Muster sagt nichts über den Stop.** Auch ein schöner Hammer endet oft am Stop. Ob ein Trade gewinnt, entscheidet, ob das Ziel vor dem Stop kommt.
4. **Bei Tageskursen sind sie Rauschen.** Im Test lagen Trades mit bullischem, bärischem und ohne Muster fast gleich (alle etwa 56–57 % im Plus).

## Meine Gedanken

