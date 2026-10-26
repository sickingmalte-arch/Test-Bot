---
tags: [lernen, forschung]
---
# 🛡️ Gelernt: Stop nachziehen und absichern

Stand: 26.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

Diese Notiz ändert der Bot nie. Sie hält fest, welche Arten von Absicherung getestet wurden, bei denen der Stop-Loss während des Trades angehoben oder früher verkauft wird – damit dieselben Ideen nicht noch einmal ungeprüft eingebaut werden. Zurück zur [[Start|Startseite]] · siehe auch [[Lehren]] und [[Notizen/Gelernt aus dem Optionsskript]].

## Wie der Bot es heute macht

Stop und Ziel stehen ab dem Kauf fest. Bei den Trend-Strategien liegen beide 3 ATR vom Kurs entfernt, bei den Gegenbewegungen liegt der Stop 2,5 ATR und das Ziel 2 ATR entfernt. Dazu kommen der Zeitstopp nach 20 Handelstagen und der Verkauf vor Quartalszahlen. Der Stop wird nie angehoben.

## Was getestet wurde

Test: 2010–2014, 2015–2021 und 2022–2026, je mit der Watchlist und 60 anderen Aktien, Mittel aus 16 Läufen, mit Gebühren und Spread, ohne Shorts. Ein angehobener Stop gilt erst ab dem nächsten Tag und wird nie wieder gesenkt.

| Variante (Oktober 2026) | Rendite besser | Ø Rendite pro Jahr | größter Rückgang größer |
| --- | --- | --- | --- |
| Stop auf den Kaufkurs (Einstand), sobald der Kurs ¾ des Wegs zum Ziel geschafft hat, Ziel bleibt | 1 von 6 | −0,7 Prozentpunkte | 2 von 6 |
| Stop zieht ab halbem Weg mit 2 ATR Abstand zum Schlusskurs nach, Ziel bleibt | 2 von 6 | −1,3 | 3 von 6 |
| Stop auf Einstand schon ab halbem Weg, Ziel bleibt | 0 von 6 | −2,2 | 4 von 6 |
| Stop zieht ab halbem Weg eng mit 1 ATR nach, Ziel bleibt | 1 von 6 | −2,6 | 4 von 6 |

Schon früher getestet (siehe README unter „Geprüft und nicht übernommen“):

- **Gewinner laufen lassen:** nachgezogener Stop statt Ziel bei den Trend-Strategien. Mehr Gewinn je Trade, aber die Trefferquote fiel auf etwa 50 %, und die Rendite war nur in der Hälfte der Fälle besser.
- **Halb verkaufen am Ziel, Rest laufen lassen:** Stop der zweiten Hälfte erst auf den Einstand, dann 3 ATR unter dem höchsten Schluss. Rendite nur in 1 von 6 Fällen besser, im Schnitt −1,2 Prozentpunkte. Die zweite Hälfte blockierte einen der 5 Plätze.

Ergebnis: **Keine der sechs Arten wurde übernommen.** Stop und Ziel bleiben fest.

## Gewinne sichern, wenn die Aktie überhitzt ist

Der Bot zeigt bei manchen Aktien „⚠️ ÜBERHITZT“ (früher „Gewinne sichern“): Der RSI liegt über 70, oder der Kurs steht am oberen Bollinger-Band. Getestet wurde im Oktober 2026, ob das Übungsdepot dann verkaufen sollte. Verkauft wird zur nächsten Eröffnung, weil der Bot „überhitzt“ erst nach Börsenschluss sieht. Gleicher Test wie oben.

| Variante | Rendite besser | Ø Rendite pro Jahr | Trefferquote | größter Rückgang größer |
| --- | --- | --- | --- | --- |
| immer verkaufen, wenn überhitzt | 0 von 6 | −5,6 Prozentpunkte (−6,4 bis −4,2) | +1,9 Punkte | 4 von 6 |
| nur wenn die Position im Plus ist | 0 von 6 | −5,4 (−6,4 bis −4,6) | +3,9 | 6 von 6 |
| nur stark überhitzt (RSI über 70 und am oberen Band), im Plus | 1 von 6 | −2,0 (−4,0 bis +1,4) | +2,1 | 5 von 6 |
| nur bei RSI über 80, im Plus | 1 von 6 | −0,9 (−1,8 bis +0,1) | +0,1 | 3 von 6 |

Beispiel 2015–2021 mit der Watchlist, „nur im Plus“: 7,5 % statt 12,7 % Rendite pro Jahr. Der größte Rückgang war 2010–2014 bis 28 % statt 14 %.

**Warum es schlechter ist, obwohl die Trefferquote steigt:**
- **Kleine Gewinne, volle Verluste:** Gewinner werden mit einem kleinen Plus verkauft, statt das Ziel zu erreichen. Verlierer werden nie überhitzt und laufen weiter bis zum Stop.
- **Überhitzt heißt oft: Der Trend ist stark.** Gerade nach einem Ausbruch steigt eine überhitzte Aktie oft weiter bis zum Ziel. Die Strategie ATR-Ausbruch kauft sogar absichtlich, wenn der Kurs weit über der EMA 20 liegt.
- **Im Depot bleiben die schwachen Positionen.** Die Gewinner sind schnell weg, deshalb wird der größte Rückgang größer.

Ergebnis: **Nicht übernommen.** „⚠️ ÜBERHITZT“ bleibt nur eine Info, im Bericht, auf der Übersichtsseite und in TradingView.

## Warum Absicherung hier nicht hilft

1. **Rücksetzer gehören dazu.** Viele Aktien laufen erst Richtung Ziel, kommen kurz zurück und erreichen das Ziel dann doch. Mit angehobenem Stop fliegt der Trade bei diesem Rücksetzer raus – mit fast nichts statt dem vollen Gewinn.
2. **Zahlenbeispiel** (2015–2021, Watchlist, Stop auf Einstand ab halbem Weg): 764 Trades endeten am angehobenen Stop mit im Schnitt −0,05 R (Spread und Gebühren). Dafür erreichten 132 Trades weniger ihr Ziel, je etwa +0,9 R. Unterm Strich weniger Gewinn.
3. **Der Abstand ist Absicht.** Stop und Ziel liegen so weit auseinander, dass das normale Schwanken den Trade selten beendet. Das Nachziehen macht genau das wieder kaputt – je enger, desto schlimmer (1 ATR war am schlechtesten).
4. **Mehr Trades sind nicht automatisch besser.** Weil Trades früher enden, macht der Bot mehr Trades (bis zu gut ein Viertel mehr). Das kostet mehr Gebühren und Spread, und die frei gewordenen Plätze bekommen nicht automatisch bessere Signale.

## Wann es sich lohnt, neu zu testen

Die Seite [[Lehren]] zählt im Übungsdepot, wie oft ein Trade erst mehr als den halben Weg zum Ziel im Plus lag und am Ende doch im Minus („Gewinn wieder abgegeben“). Wird das über viele Trades deutlich häufiger als bisher, lohnt sich ein neuer Test – nicht wegen eines einzelnen ärgerlichen Trades.

## Meine Gedanken

