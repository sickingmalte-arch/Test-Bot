---
tags: [lernen, forschung]
---
# 📘 Gelernt aus dem Optionsskript

Stand: 23.10.2026 · Simulation mit Spielgeld, keine Anlageberatung.

Diese Notiz ändert der Bot nie. Sie hält fest, was aus dem Vorlesungsskript zu Optionen (Kapitel 6) für den Bot geprüft wurde – damit dieselben Ideen nicht noch einmal ungeprüft eingebaut werden. Das ganze Wissen aus dem Skript: [[Notizen/Wissen – Optionen]]. Zurück zur [[Start|Startseite]] · siehe auch [[Lehren]].

## Was im Skript steht (kurz)

- **Call und Put:** das Recht, eine Aktie zu einem festen Preis (Basispreis) zu kaufen bzw. zu verkaufen. Wert einer Option = innerer Wert + Zeitwert.
- **Protective Put:** Aktie + Put = Absicherung nach unten. Der Stop-Loss des Bots macht etwas Ähnliches – ohne Prämie, dafür ohne Schutz bei Kurslücken.
- **Black-Scholes-Modell:** Der Kurs schwankt zufällig (geometrische Brownsche Bewegung), wie stark, sagt die **Volatilität** σ. Daraus folgt der faire Preis eines Calls: C = S · N(d1) − K · e^(−rT) · N(d2).
- **Historische Volatilität:** Schwankung der täglichen Log-Renditen. **Implizite Volatilität:** die Schwankung, die die Optionspreise erwarten (für den ganzen Markt z. B. der VIX).
- **Greeks:** Delta, Gamma, Vega, Theta (Zeitwert schmilzt mit jedem Tag) und Rho.

## Was der Bot damit ausprobiert hat

Aus der Volatilität der letzten 20 Tage rechnet das Modell (Spiegelungsprinzip), wie wahrscheinlich der Kurs sein Ziel innerhalb von 20 Handelstagen mindestens einmal berührt. Die Formel wurde mit einer Zufalls-Simulation gegengeprüft.

Test: 2010–2014, 2015–2021 und 2022–2026, je mit der Watchlist und 60 anderen Aktien, Mittel aus 16 Läufen, mit Gebühren und Spread, ohne Shorts, alle anderen Regeln gleich.

| Idee | Rendite besser | Ø Rendite pro Jahr | größter Rückgang größer |
| --- | --- | --- | --- |
| Bei mehreren Signalen zuerst das mit der höchsten Ziel-Wahrscheinlichkeit kaufen (fairer Nachtest) | 3 von 6 | ±0,0 Prozentpunkte | 2 von 6 |
| Dasselbe, aber vor dem CRV | 3 von 6 | −0,9 | 4 von 6 |
| Signale unter 28 % Wahrscheinlichkeit weglassen | 2 von 6 | −0,2 | 3 von 6 |
| Verkaufen, wenn das Ziel kaum noch erreichbar ist (unter 10 %) | 0 von 6 | −5,9 | 5 von 6 |
| Dasselbe schon unter 20 % | 0 von 6 | −6,8 | 6 von 6 |

Ergebnis: **Beim Kaufen und Verkaufen wurde nichts davon übernommen.** Die Handelsregeln bleiben, wie sie sind.

**Was der Bot stattdessen macht:** Er zeigt die Ziel-Chance bei jedem Signal als Info an – im Handelsplan, auf der Übersichtsseite und in den Trade-Notizen –, daneben, wie oft das Ziel bei ähnlichen Signalen bisher wirklich erreicht wurde. Auf [[Lehren]] prüft er laufend an allen gedachten Trades, ob die Formel stimmt (vorhergesagt gegen wirklich berührt) und ob sie etwas über Gewinner sagt.

## Was daraus folgt

1. **Black-Scholes kennt keine Richtung.** Das Modell nimmt an, dass man nicht vorhersagen kann, ob ein Kurs steigt oder fällt. Für den Preis einer Option ist das richtig. Der Bot verdient aber gerade an dem kleinen Vorteil, den das Modell weglässt: Trends und Erholungen. Die Formel sagt gut, wie stark eine Aktie schwankt – aber nicht, welcher Trade gewinnt.
2. **Zeitwert gibt es nur bei Optionen.** Bei einer Option schmilzt der Zeitwert wirklich (Theta). Bei den Trades des Bots nicht: Viele Aktien, die tagelang stillstehen, erreichen ihr Ziel später doch noch. Früh zu verkaufen machte aus Gewinnern kleine Verluste – die Trefferquote fiel von etwa 56 % auf 45 %.
3. **Die Schwankung steckt schon drin.** Stop und Ziel hängen an der ATR, also schon an der Schwankung der Aktie. Eine zweite Schwankungs-Zahl bringt darum kaum Neues. Auch das Risiko nach dem VIX (implizite Volatilität) hatte schon nicht geholfen (siehe README unter „Geprüft und nicht übernommen“).
4. **Ein einzelner guter Lauf ist kein Beweis.** Die Rangfolge sah im ersten Test mit +0,4 Prozentpunkten gut aus – war aber nur ein Durchlauf. Im fairen Vergleich mit derselben Aktien-Auswahl war sie in 51 von 96 Läufen besser: wie ein Münzwurf.
5. **Die Formel selbst liegt daneben.** In der ersten Selbstkontrolle (Oktober 2026, 2 814 gedachte Trades) sagte sie im Schnitt 39 % voraus, berührt wurde das Ziel in 45 % der Fälle – bei Formel-Chancen unter 30 % sogar in 43 % statt 26 %. Ein möglicher Grund: Die Formel rechnet mit der Schwankung der Schlusskurse, innerhalb des Tages schwanken Aktien aber stärker. Und Trades im Plus gab es in jeder Gruppe etwa gleich oft (56–59 %).

## Meine Gedanken

