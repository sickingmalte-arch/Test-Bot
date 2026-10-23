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
- [[Strategien/RSI-2-Rücksetzer Long|RSI-2-Rücksetzer ↑]]: ✅ aktiv (Ø +0,08 R über die letzten 60 Trades)
- [[Strategien/RSI-2-Übertreibung Short|RSI-2-Übertreibung ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/Gegenbewegung Long|Gegenbewegung ↑]]: ✅ aktiv (Ø +0,08 R über die letzten 60 Trades)
- [[Strategien/Rückfall Short|Rückfall ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/MACD-Wende Long|MACD-Wende ↑]]: ⏸ pausiert – die letzten 60 Trades liefen schlecht (Ø -0,06 R)
- [[Strategien/MACD-Wende Short|MACD-Wende ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/Rücksetzer Long|Rücksetzer ↑]]: ✅ aktiv (Ø -0,01 R über die letzten 60 Trades)
- [[Strategien/Erholung Short|Erholung ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/Squeeze-Ausbruch Long|Squeeze-Ausbruch ↑]]: ✅ aktiv (Ø +0,17 R über die letzten 60 Trades)
- [[Strategien/Squeeze-Abbruch Short|Squeeze-Abbruch ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/EMA-Kreuz Long|EMA-Kreuz ↑]]: ✅ aktiv (Ø +0,02 R über die letzten 60 Trades)
- [[Strategien/EMA-Kreuz Short|EMA-Kreuz ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)
- [[Strategien/ATR-Ausbruch Long|ATR-Ausbruch ↑]]: ✅ aktiv (Ø +0,01 R über die letzten 60 Trades)
- [[Strategien/ATR-Abbruch Short|ATR-Abbruch ↓]]: – aus (Short-Signale sind ausgeschaltet – im Test im Schnitt mit Verlust)

### Änderungen der letzten 30 Tage

- Fr 25.09.: [[Strategien/MACD-Wende Long|MACD-Wende ↑]] ⏸ pausiert/aus

## Muster im Strategie-Tagebuch (alle Strategien, alle Aktien)

- Insgesamt: 2839 Trades · Ø +0,10 R · Treffer 57 %
- Ziel: 947× (33 %), Ø +0,89 R
- Zeitstopp: 668× (24 %), Ø -0,01 R
- Stop: 541× (19 %), Ø -1,01 R
- vor Quartalszahlen: 460× (16 %), Ø -0,04 R
- Ziel (Kurslücke): 126× (4 %), Ø +1,05 R
- Stop (Kurslücke): 97× (3 %), Ø -1,16 R
- Long: 2839 Trades · Ø +0,10 R · Treffer 57 %

### Rangliste der Aktien (ab 20 Trades, nach Ø R)

1. [[Aktien/NBIS|NBIS]]: 60 Trades · Ø +0,26 R · Treffer 65 %
2. [[Aktien/NVDA|NVDA]]: 137 Trades · Ø +0,25 R · Treffer 68 %
3. [[Aktien/GOOGL|GOOGL]]: 129 Trades · Ø +0,24 R · Treffer 61 %
…
22. [[Aktien/AMZN|AMZN]]: 146 Trades · Ø -0,02 R · Treffer 51 %
23. [[Aktien/MELI|MELI]]: 115 Trades · Ø -0,04 R · Treffer 48 %
24. [[Aktien/CRWV|CRWV]]: 29 Trades · Ø -0,25 R · Treffer 45 %
- Hinweis: Selbst 20–50 Trades je Aktie sind wenig. Sperren kannst du eine Aktie in [[Meine Regeln]].

### Trefferquote je Aktie (Ziel: über 50 %)

- 19 von 24 Aktien (ab 20 Trades) treffen öfter als jedes zweite Mal.
- Bei 50 % oder darunter: [[Aktien/CRWV|CRWV]] 45 % (29 Trades, Ø -0,25 R), [[Aktien/TSLA|TSLA]] 45 % (121 Trades, Ø -0,01 R), [[Aktien/SOFI|SOFI]] 48 % (107 Trades, Ø -0,01 R), [[Aktien/MELI|MELI]] 48 % (115 Trades, Ø -0,04 R), [[Aktien/LLY|LLY]] 49 % (129 Trades, Ø +0,02 R). Ein paar Prozentpunkte unter 50 % können auch bei über 100 Trades Zufall sein – und die Trefferquote allein sagt nicht, ob eine Aktie Geld bringt (dafür zählt Ø R, siehe Rangliste oben).

## Aus dem Übungsdepot (echte Vorwärts-Trades)

- Noch keine abgeschlossenen Trades – das Übungsdepot läuft seit 2026-10-20.

Übersicht: [[Start]] · [[Meine Regeln]]
%% BOT-ENDE %%