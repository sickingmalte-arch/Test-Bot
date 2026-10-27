---
typ: "lehren"
---
%% BOT-ANFANG – diesen Teil schreibt der Bot bei jedem Lauf neu. %%
# 🎓 Lehren

Hier sammelt der Bot, was er aus seinen Fehlern und Erfolgen zieht. **Automatisch ändert er dabei nur, welche Strategien er handelt** (Lernregel unten) – und hält sich an [[Meine Regeln]]. Muster wie „auf Aktie X läuft es schlecht“ zeigt er dir nur: Bei wenigen Trades ist das oft Zufall, und wer jedem Zufall hinterherläuft, verliert am Ende mehr.

## Was der Bot gerade daraus macht (Lernregel)

Ab 20 gedachten Trades pausiert er eine Strategie, wenn sie im Schnitt mehr als 0,1 R je Trade verliert, und nimmt sie wieder, sobald der Schnitt im Plus ist. Ab 50 Trades muss sie über ihre ganze Geschichte im Plus sein.

- [[Strategien/Ausbruch Long|Ausbruch ↑]]: ✅ aktiv (Ø -0,05 R über die letzten 60 Trades)
- [[Strategien/Abbruch Short|Abbruch ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/RSI-2-Rücksetzer Long|RSI-2-Rücksetzer ↑]]: ✅ aktiv (Ø +0,06 R über die letzten 60 Trades)
- [[Strategien/RSI-2-Übertreibung Short|RSI-2-Übertreibung ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/Gegenbewegung Long|Gegenbewegung ↑]]: ✅ aktiv (Ø +0,08 R über die letzten 60 Trades)
- [[Strategien/Rückfall Short|Rückfall ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/MACD-Wende Long|MACD-Wende ↑]]: ⏸ pausiert – die letzten 60 Trades liefen schlecht (Ø -0,06 R)
- [[Strategien/MACD-Wende Short|MACD-Wende ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/Rücksetzer Long|Rücksetzer ↑]]: ✅ aktiv (Ø -0,02 R über die letzten 60 Trades)
- [[Strategien/Erholung Short|Erholung ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/Squeeze-Ausbruch Long|Squeeze-Ausbruch ↑]]: ✅ aktiv (Ø +0,17 R über die letzten 60 Trades)
- [[Strategien/Squeeze-Abbruch Short|Squeeze-Abbruch ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/EMA-Kreuz Long|EMA-Kreuz ↑]]: ✅ aktiv (Ø -0,04 R über die letzten 60 Trades)
- [[Strategien/EMA-Kreuz Short|EMA-Kreuz ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/ATR-Ausbruch Long|ATR-Ausbruch ↑]]: ✅ aktiv (Ø +0,03 R über die letzten 60 Trades)
- [[Strategien/ATR-Abbruch Short|ATR-Abbruch ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)

### Änderungen der letzten 30 Tage

- keine

## Muster im Strategie-Tagebuch (alle Strategien, alle Aktien)

- Insgesamt: 2844 Trades · Ø +0,10 R · Treffer 57 %
- Ziel: 947× (33 %), Ø +0,89 R
- Zeitstopp: 666× (23 %), Ø -0,01 R
- Stop: 547× (19 %), Ø -1,01 R
- vor Quartalszahlen: 459× (16 %), Ø -0,04 R
- Ziel (Kurslücke): 126× (4 %), Ø +1,05 R
- Stop (Kurslücke): 99× (3 %), Ø -1,17 R
- Long: 2844 Trades · Ø +0,10 R · Treffer 57 %

### Rangliste der Aktien (ab 20 Trades, nach Ø R)

1. [[Aktien/NBIS|NBIS]]: 60 Trades · Ø +0,26 R · Treffer 65 %
2. [[Aktien/NVDA|NVDA]]: 137 Trades · Ø +0,25 R · Treffer 68 %
3. [[Aktien/AMD|AMD]]: 115 Trades · Ø +0,23 R · Treffer 62 %
…
22. [[Aktien/AMZN|AMZN]]: 145 Trades · Ø -0,02 R · Treffer 52 %
23. [[Aktien/MELI|MELI]]: 115 Trades · Ø -0,05 R · Treffer 48 %
24. [[Aktien/CRWV|CRWV]]: 29 Trades · Ø -0,25 R · Treffer 45 %
- Hinweis: Selbst 20–50 Trades je Aktie sind wenig. Sperren kannst du eine Aktie in [[Meine Regeln]].

### Trefferquote je Aktie (Ziel: über 50 %)

- 19 von 24 Aktien (ab 20 Trades) treffen öfter als jedes zweite Mal.
- Bei 50 % oder darunter: [[Aktien/CRWV|CRWV]] 45 % (29 Trades, Ø -0,25 R), [[Aktien/TSLA|TSLA]] 45 % (120 Trades, Ø -0,01 R), [[Aktien/SOFI|SOFI]] 48 % (107 Trades, Ø -0,01 R), [[Aktien/MELI|MELI]] 48 % (115 Trades, Ø -0,05 R), [[Aktien/LLY|LLY]] 48 % (129 Trades, Ø +0,01 R). Ein paar Prozentpunkte unter 50 % können auch bei über 100 Trades Zufall sein – und die Trefferquote allein sagt nicht, ob eine Aktie Geld bringt (dafür zählt Ø R, siehe Rangliste oben).

## 📐 Selbstkontrolle: Ziel-Chance nach Black-Scholes

Bei jedem Signal rechnet der Bot nach dem Black-Scholes-Modell aus dem Optionsskript aus, wie wahrscheinlich der Kurs das Ziel innerhalb von 20 Handelstagen mindestens einmal berührt (aus der Schwankung der letzten 20 Tage). Er kauft **nicht** danach – im Test über 16 Jahre hat das nichts gebracht (siehe [[Notizen/Gelernt aus dem Optionsskript]]). Hier prüft er an allen gedachten Trades, ob die Formel stimmt. Bei jedem Signal zeigt er neben der Formel auch, wie oft das Ziel in dessen Gruppe wirklich berührt wurde (Spalte „Ziel wirklich berührt“).

| Ziel-Chance laut Formel | Signale | Ø vorhergesagt | Ziel wirklich berührt | Trades im Plus | Ø je Trade |
| --- | --- | --- | --- | --- | --- |
| unter 30 % | 512 | 26 % | 43 % | 58 % | +0,11 R |
| 30–40 % | 1028 | 35 % | 41 % | 56 % | +0,09 R |
| 40–50 % | 824 | 45 % | 48 % | 56 % | +0,10 R |
| ab 50 % | 453 | 55 % | 52 % | 57 % | +0,12 R |

- Zusammen: 2817 Signale, vorhergesagt Ø 39 %, berührt 45 % – die Formel liegt deutlich daneben: Die Aktien schwanken anders, als das Modell annimmt (je Gruppe im Schnitt 7 Prozentpunkte Abstand).
- Trades im Plus je Gruppe: 56 bis 58 %. Die Formel sagt, wie weit eine Aktie schwankt – nicht, in welche Richtung. Ob ein Trade gewinnt, hängt davon ab, ob das Ziel vor dem Stop kommt.

## 🕯️ Selbstkontrolle: Kerzenmuster

Bei jedem Signal zeigt der Bot die Kerzenmuster vom Poster (z. B. Hammer, Bullish Engulfing, Shooting Star) und bei Ausbrüchen und Doppelböden das Musterziel. Er kauft **nicht** danach – als Bestätigung, Warnung, Vorrang oder Ziel hat das im Test über 16 Jahre nicht geholfen (siehe [[Notizen/Gelernt – Muster und Lehrbücher]]). Hier prüft er an allen gedachten Kauf-Trades weiter, ob sich das ändert.

| Gruppe | Trades | im Plus | Ø je Trade |
| --- | --- | --- | --- |
| bullisches Kerzenmuster (am Signaltag oder Tag davor) | 914 | 56 % | +0,10 R |
| bärisches Kerzenmuster am Signaltag | 518 | 57 % | +0,10 R |
| kein Kerzenmuster | 1412 | 57 % | +0,10 R |

- Mit und ohne Muster liegen nah beieinander – die Muster sagen bei diesen Strategien wenig voraus.

## 📰 Selbstkontrolle: Nachrichten-Stimmung

Zu jedem Signal zählt der Bot die guten und schlechten Schlagzeilen der letzten Tage (z. B. Hochstufung, gute Quartalszahlen bzw. Herabstufung, Klage). Schlechte sperren den Kauf wie bisher; gute ändern nichts. Alte Schlagzeilen gibt es nicht, darum sammelt er ab jetzt und prüft hier, ob Signale mit guten Nachrichten wirklich besser laufen. Mitentscheiden dürfte die Stimmung erst, wenn jede Gruppe mindestens 30 Trades hat und der Unterschied deutlich ist.

- Gesammelt: 1 Signal mit Schlagzeilen, davon noch keins mit abgeschlossenem Trade.

## Aus dem Übungsdepot (echte Vorwärts-Trades)

- Noch keine abgeschlossenen Trades – das Übungsdepot läuft seit 2026-10-20.

Übersicht: [[Start]] · [[Meine Regeln]]
%% BOT-ENDE %%