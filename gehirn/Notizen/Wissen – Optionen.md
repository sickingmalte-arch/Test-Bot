---
tags: [wissen, optionen]
---
# 📚 Wissen: Optionen

Zusammenfassung des Vorlesungsskripts zu Optionen (Kapitel 6) in eigenen Worten, mit Rechenbeispielen. Diese Notiz ändert der Bot nie. Was der Bot davon nutzt, steht ganz unten. Was getestet wurde und warum er nicht danach kauft: [[Notizen/Gelernt aus dem Optionsskript]]. Zurück zur [[Start|Startseite]].

## 1. Was ist eine Option?

- **Call (Kaufoption):** das Recht, aber nicht die Pflicht, eine Aktie (den Basiswert) zu einem festen Preis zu kaufen – dem **Basispreis K** – bis zum oder am **Verfallstag T**.
- **Put (Verkaufsoption):** das Recht, die Aktie zum Basispreis zu verkaufen.
- Der **Käufer** (Long) zahlt dafür eine **Prämie** (den Optionspreis). Der **Verkäufer** (Stillhalter, Short) bekommt die Prämie und muss liefern bzw. abnehmen, wenn der Käufer sein Recht nutzt.
- **Europäische** Optionen kann man nur am Verfallstag ausüben, **amerikanische** jederzeit bis dahin.
- **Auszahlung am Verfallstag** (S_T = Aktienkurs am Verfallstag):
  - Call: max(S_T − K; 0)
  - Put: max(K − S_T; 0)
  - **Gewinn** = Auszahlung − gezahlte Prämie
- **Beispiel:** Call mit K = 100 €, Prämie 5 €. Steht die Aktie am Ende bei 120 €: Auszahlung 20 €, Gewinn 15 €. Steht sie bei 90 €: Auszahlung 0, Verlust 5 € (mehr als die Prämie kann der Käufer nicht verlieren). Der Verkäufer hat genau das Spiegelbild – sein Verlust kann beim Call unbegrenzt sein.

## 2. Absichern und Strategien

- **Protective Put:** Aktie + Put kaufen. Fällt die Aktie unter K, gleicht der Put den Verlust aus – wie eine Versicherung, deren Beitrag die Prämie ist. Nach oben bleibt der Gewinn offen (minus Prämie).
- **Bull Spread:** Call mit kleinem Basispreis K1 kaufen und Call mit größerem K2 verkaufen. Billiger als ein Call allein (die verkaufte Prämie hilft), dafür ist der Gewinn auf K2 − K1 gedeckelt. Für „leicht steigend“.
- **Straddle:** Call und Put mit gleichem Basispreis kaufen. Gewinn bei einer **großen Bewegung in egal welche Richtung**, Verlust (beide Prämien), wenn der Kurs stehen bleibt. Man setzt also auf Schwankung, nicht auf eine Richtung.

## 3. Was eine Option mindestens und höchstens wert ist (ohne Modell)

- **Innerer Wert:** was die Option sofort ausgeübt bringen würde – Call max(S − K; 0), Put max(K − S; 0).
- **Zeitwert** = Optionspreis − innerer Wert. Er bezahlt die Chance, dass es bis zum Verfall noch besser wird, und schmilzt bis zum Verfallstag auf 0.
- **Im Geld** (in the money): innerer Wert > 0 (Call: S > K). **Am Geld** (at the money): S ≈ K. **Aus dem Geld** (out of the money): innerer Wert 0 (Call: S < K).
- **Wertgrenzen** (europäisch, ohne Dividende, r = Zins, e^(−rT) = Abzinsung):
  - Call: max(S − K·e^(−rT); 0) ≤ C ≤ S
  - Put: max(K·e^(−rT) − S; 0) ≤ P ≤ K·e^(−rT)
- **Put-Call-Parität:** C − P = S − K·e^(−rT). Grund: „Call kaufen + Put verkaufen“ zahlt am Ende genau dasselbe wie „Aktie kaufen und K·e^(−rT) leihen“. Zwei Dinge mit gleicher Auszahlung müssen heute gleich viel kosten – sonst gäbe es risikolosen Gewinn (Arbitrage).
- **Satz von Merton:** Einen amerikanischen Call auf eine Aktie ohne Dividende übt man nie vorzeitig aus – man würde den Zeitwert verschenken (Verkaufen ist besser als Ausüben). Darum ist er genauso viel wert wie der europäische.

## 4. Binomialmodell

- Idee: In einem Schritt steigt der Kurs auf S·u oder fällt auf S·d. Aus Aktie und Kredit kann man die Auszahlung der Option genau nachbauen (**Duplikation**). Der Preis der Option ist dann der Preis dieses Nachbaus – ohne zu wissen, wie wahrscheinlich „hoch“ oder „runter“ wirklich ist.
- Rechnerisch: **risikoneutrale Wahrscheinlichkeit** p = (1 + r − d) / (u − d). Optionspreis = Erwartungswert der Auszahlung mit p, abgezinst.
- **Beispiel:** S = 100, u = 1,2, d = 0,8, r = 5 %, Call mit K = 100. Auszahlung oben 20, unten 0. p = (1,05 − 0,8) / 0,4 = 0,625. C = 0,625 · 20 / 1,05 ≈ **11,90 €**.
- Mit vielen kleinen Schritten (u = e^(σ·√(T/n)), d = 1/u) nähert sich das Ergebnis der Black-Scholes-Formel.

## 5. Black-Scholes-Merton-Modell

- **Annahmen:** Der Kurs folgt einer **geometrischen Brownschen Bewegung**: S(t) = S0 · exp((μ − σ²/2)·t + σ·W(t)). Die Log-Renditen sind also normalverteilt. Volatilität σ und Zins r sind konstant, es gibt keine Kosten und man kann jederzeit handeln.
- **Formel:**
  - Call: C = S·N(d1) − K·e^(−rT)·N(d2)
  - Put: P = K·e^(−rT)·N(−d2) − S·N(−d1)
  - d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T), d2 = d1 − σ·√T
  - N(x) = Verteilungsfunktion der Standardnormalverteilung
- **N(d2)** ist die (risikoneutrale) Wahrscheinlichkeit, dass der Call am Ende im Geld ist.
- Wichtig: Der erwartete Ertrag μ der Aktie kommt in der Formel **nicht** vor. Für den Optionspreis spielt es keine Rolle, ob man die Aktie für gut oder schlecht hält.
- **Beispiel:** S = K = 100 €, T = 1 Jahr, r = 0, σ = 20 %: d1 = 0,1, d2 = −0,1, C = 100 · (0,5398 − 0,4602) ≈ **7,97 €**. Wegen der Put-Call-Parität (r = 0, S = K) kostet der Put genauso viel.

## 6. Hebel und Aufgeld

- **Einfacher Hebel** = Aktienkurs / Optionspreis. Im Beispiel 100 / 7,97 ≈ 12,5: Für das Geld einer Aktie bekommt man etwa 12,5 Calls.
- **Echter Hebel** (Elastizität, Omega) = Delta · S / C ≈ 0,54 · 100 / 7,97 ≈ 6,8: Steigt die Aktie um 1 %, steigt der Call um etwa 6,8 %. In die andere Richtung gilt das genauso.
- **Aufgeld** = (Optionspreis + Basispreis − Aktienkurs) / Aktienkurs. Es sagt, wie viel teurer der Kauf über den Call ist als der direkte Kauf der Aktie. Im Beispiel (7,97 + 100 − 100) / 100 ≈ 8 %.

## 7. Volatilität

- **Historische Volatilität:** Standardabweichung der täglichen Log-Renditen ln(S_t / S_(t−1)). Fürs Jahr mal √252 (Handelstage).
- **Implizite Volatilität:** das σ, bei dem die Black-Scholes-Formel genau den Marktpreis der Option ergibt – also die Schwankung, die der Markt erwartet. Man findet es nur schrittweise, z. B. mit dem **Newton-Verfahren**: σ_neu = σ_alt − (Formelpreis(σ_alt) − Marktpreis) / Vega(σ_alt).
- **Smile und Skew:** Die implizite Volatilität ist je nach Basispreis verschieden. Bei Aktien ist sie für tiefe Basispreise meist höher, weil Anleger sich gegen Crashs absichern. Die Annahme „ein σ für alles“ stimmt also nicht ganz. Trägt man sie über Basispreis und Laufzeit auf, ergibt das die **Volatilitätsfläche**.
- Der **VIX** ist die implizite Volatilität des S&P 500 für die nächsten 30 Tage („Angstbarometer“).

## 8. Die Griechen (Greeks)

Sie sagen, wie stark sich der Optionspreis ändert, wenn sich eine Größe ändert (Zahlen fürs Beispiel aus Abschnitt 5):

- **Delta** = N(d1) beim Call (Put: N(d1) − 1): Änderung je 1 € Aktienkurs. Beispiel: 0,54 – steigt die Aktie um 1 €, steigt der Call um etwa 0,54 €.
- **Gamma** = n(d1) / (S·σ·√T): wie schnell sich Delta ändert. Beispiel: 0,02. Am größten am Geld kurz vor dem Verfall.
- **Vega** = S·√T·n(d1): Änderung bei mehr Volatilität. Beispiel: etwa 0,40 € je Prozentpunkt mehr σ.
- **Theta:** Wertverlust mit der Zeit – der Zeitwert schmilzt. Beispiel: etwa 1 Cent je Kalendertag, kurz vor Verfall am Geld viel schneller.
- **Rho:** Änderung, wenn sich der Zins ändert.
- (n(x) ist die Dichte der Standardnormalverteilung.)

## 9. Delta-Hedging

- Wer einen Call verkauft hat, kauft je Option **Delta Stück Aktien**. Kleine Kursbewegungen heben sich dann auf: Was die Option teurer wird, gewinnt die Aktie.
- Weil sich Delta ständig ändert (Gamma), muss man immer wieder nachkaufen bzw. verkaufen. Das kostet Gebühren, und bei Kurssprüngen bleibt ein Rest-Risiko.

## 10. Was der Bot davon nutzt

- **Ziel-Chance:** Bei jedem Kauf-Signal rechnet der Bot mit dem Black-Scholes-Modell aus, wie wahrscheinlich der Kurs das Ziel innerhalb von 20 Handelstagen **mindestens einmal berührt**. Er nimmt dazu die historische Volatilität der letzten 20 Tage und keinen Vorteil für eine Richtung (Zins 0). Die Formel (Spiegelungsprinzip):
  - P = N((ν·T − b) / (σ·√T)) + e^(2·ν·b/σ²) · N((−b − ν·T) / (σ·√T))
  - b = Abstand zum Ziel = |ln(Ziel / Kurs)|, ν = −σ²/2 (bei Shorts +σ²/2), σ = Tagesvolatilität, T = 20 Tage
  - Beispiel: Kurs 100 €, Ziel 106 €, Schwankung 2 % am Tag → etwa 50 %.
- Daneben zeigt er, wie oft das Ziel bei gedachten Trades mit ähnlicher Formel-Chance **bisher wirklich erreicht** wurde. Das ist nötig, weil die Formel daneben liegen kann: In der ersten Selbstkontrolle (Oktober 2026, 2 814 gedachte Trades) sagte sie im Schnitt 39 % voraus, berührt wurde das Ziel in 45 % der Fälle – bei Formel-Chancen unter 30 % sogar in 43 % statt 26 %.
- Zu sehen ist beides im Handelsplan (Bericht und Handy-Nachricht), auf der Übersichtsseite bei jedem Signal und in den Trade-Notizen. Auf [[Lehren]] prüft der Bot laufend an allen gedachten Trades, ob die Formel stimmt.
- **Er kauft nicht danach.** Im Test über 16 Jahre half die Ziel-Chance weder beim Auswählen noch beim Aussteigen. Der Grund steht schon oben in Abschnitt 5: Das Modell kennt keine Richtung (μ fehlt), der Bot verdient aber gerade an Trends und Erholungen.
- **Was es im Bot schon gibt:**
  - Der **Stop-Loss** ist so etwas wie ein Protective Put – ohne Prämie, aber ohne Schutz bei Kurslücken. Ihn während des Trades anzuheben (Absicherung), half im Test nicht: [[Notizen/Gelernt – Stop nachziehen und absichern]].
  - Stop und Ziel hängen an der **ATR**, also schon an der Schwankung der Aktie.
  - **Squeeze-Ausbruch** setzt wie ein Straddle darauf, dass nach einer ruhigen Phase eine große Bewegung kommt (nur nach oben).
  - Das Risiko nach dem **VIX** (implizite Volatilität) zu verkleinern, wurde getestet und nicht übernommen (README, „Geprüft und nicht übernommen“).

## Meine Gedanken

