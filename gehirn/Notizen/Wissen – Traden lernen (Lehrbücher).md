---
tags: [wissen, grundlagen]
---
# 📚 Wissen: Traden lernen (zwei Lehrbücher)

Stand: 27.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

Diese Notiz ändert der Bot nie. Sie fasst zwei Einsteiger-Lehrbücher zusammen und sagt bei jedem Punkt, was der Bot davon schon macht, was getestet wurde und was nicht passt. Testergebnisse: [[Notizen/Gelernt – Muster und Lehrbücher]]. Zurück zur [[Start|Startseite]] · siehe auch [[Lehren]] und [[Notizen/Wissen – Kerzen- und Chartmuster]].

Quellen:
- „Traden lernen – so klappt der Einstieg in den Börsenhandel“ (Philipp Berger, GodmodeTrader, 2017)
- „Die ultimative Forex Trading lernen PDF“ (Trading.de)

## 1. Grundlagen

- **Trading oder Investieren:** Trader nutzen Kursschwankungen über Tage bis Wochen; Investoren halten Monate bis Jahre. Der Bot ist ein **Swingtrader**: Er handelt die nächste Bewegung („Swing“) und hält höchstens 20 Handelstage.
- **Arten von Strategien:**
  - **Prozyklisch (mit dem Trend, z. B. Ausbrüche):** Der Bot nutzt Ausbruch, Squeeze-Ausbruch, ATR-Ausbruch, MACD-Wende, EMA-Kreuz und Rücksetzer im Trend.
  - **Antizyklisch (gegen eine Übertreibung):** Der Bot nutzt RSI-2-Rücksetzer und Gegenbewegung, beide nur im langen Aufwärtstrend.
- **Startkapital und Instrumente:** Mit Hebelprodukten (CFDs, Zertifikate, Futures, Optionen) geht Traden mit wenig Geld, aber das Risiko ist höher. Der Bot rechnet mit echten Aktien, ohne Hebel.

## 2. Werkzeuge der technischen Analyse

| Werkzeug | Was es zeigt | Beim Bot |
| --- | --- | --- |
| Unterstützung und Widerstand | Preiszonen, an denen der Kurs oft dreht; ein gebrochener Widerstand wird oft zur Unterstützung | Ausbruch über das 20-Tage-Hoch; Ziel am Widerstand getestet → schlechter |
| Trendlinien und Trendkanäle | Linie durch Tiefs (Aufwärtstrend) bzw. Hochs (Abwärtstrend) | Trend über die 50- und 200-Tage-Linie |
| Chart- und Kerzenmuster | Doppelboden, Kopf-Schulter, Keil, Rechteck, Wimpel, Dreieck; Kerzen wie Hammer | siehe [[Notizen/Wissen – Kerzen- und Chartmuster]] – nur Info |
| Bollinger-Bänder | Schwankung; enge Bänder = Ausbruch steht bevor („Squeeze“) | Strategie Squeeze-Ausbruch, Gegenbewegung am unteren Band |
| MACD | Kreuzung zweier gleitender Durchschnitte = neuer Trend | Strategie MACD-Wende |
| RSI und Stochastik | über 70 bzw. 80 überkauft, unter 30 bzw. 20 überverkauft | RSI-2-Rücksetzer, Gegenbewegung; Hinweis „überhitzt“ nur als Info – danach verkaufen war im Test schlechter (siehe [[Notizen/Gelernt – Stop nachziehen und absichern]]) |
| ADX | Stärke eines Trends (unter 20 schwach, über 50 stark) | getestet als Filter → schlechter |
| Parabolic SAR | Ende eines Trends, Zeitpunkt zum Ausstieg | ähnlich wie nachgezogener Stop – getestet, schlechter |
| Ichimoku | Trend und Unterstützung in einem Bild | ähnlich wie die Trend-Linien des Bots |
| Fibonacci | Rücksetzer enden oft bei 38,2 %, 50 % oder 61,8 % der letzten Bewegung | als Strategie getestet → schlechter |
| Zeitrahmen | erst den langen Zeitrahmen (Woche), dann den kurzen (Tag) ansehen | Wochentrend als Filter getestet → nicht überall besser |

**Wichtigster Satz aus beiden Büchern:** Kein Werkzeug ist ein „heiliger Gral“. Ein Signal ist erst gut, wenn es über viele Trades nach Kosten Geld bringt – genau das prüft der Bot im 16-Jahres-Test, bevor er etwas übernimmt.

## 3. Nachrichten und Fundamentalanalyse

- Nachrichten bewegen Kurse; vor wichtigen Terminen (Zinsentscheid, Quartalszahlen) kann der Kurs stark springen.
- Beim Bot:
  - Er kauft nicht kurz vor **Quartalszahlen** und verkauft vorher.
  - Er sperrt Käufe bei **schlechten Schlagzeilen** (Herabstufung, Kapitalerhöhung, Klage).
  - Er zählt gute und schlechte Schlagzeilen und prüft auf [[Lehren]], ob die Stimmung etwas voraussagt.
- Rückwirkend lässt sich das nicht testen, weil es alte Schlagzeilen nicht gibt. Deshalb sammelt der Bot ab jetzt.

## 4. Risiko- und Moneymanagement

- **1-%-Regel:** Pro Trade nur so viel riskieren, dass der Stop höchstens 1 % des Kontos kostet. Der Bot macht genau das, dazu höchstens 5 Positionen und 5 % Risiko zusammen.
- **Trefferquote und Chance-Risiko gehören zusammen:** Auch 40 % Treffer können Geld bringen, wenn die Gewinne groß genug sind. Der Bot trifft gut 55 % mit Ziel etwa so weit wie der Stop; größere Ziele wurden getestet und trafen zu selten.
- **Stop-Loss bei jedem Trade:** nicht zu nah (normale Schwankung löst ihn aus), nicht zu weit. Der Bot setzt ihn 2,5–3 ATR entfernt.
- **Strategie regelmäßig prüfen:** Läuft eine Strategie schlecht, pausiert der Bot sie (Lernregel).

## 5. Psychologie und Tagebuch

- **Regeln einhalten, auch nach Verlusten:** Eine Strategie mit Plus im Schnitt hat trotzdem Verlustserien. Die häufigsten Fehler sind kleine Abweichungen vom Plan: zu früh einsteigen (Hoffnung), zu früh aussteigen (Gier oder Angst), schnell eine neue, ungetestete Strategie probieren. Ein Bot hat keine Gefühle – das ist sein großer Vorteil.
- **Tradingtagebuch:** Jeder Trade wird mit Einstieg, Stop, Ziel, Ausstieg, bestem und schlechtestem Kurs während des Trades (MFE und MAE) festgehalten. Das macht der Bot in jeder Trade-Notiz, und auf [[Lehren]] wertet er alle Trades aus.

## 6. Was nicht passt

- Forex-Besonderheiten (Währungspaare, Pips, Hebel, Handelszeiten rund um die Uhr) gelten für Aktien nicht.
- Daytrading und Scalping (Minuten- und Stundencharts) passen nicht zu einem Bot, der einmal am Morgen mit Tageskursen rechnet.

## Meine Gedanken

