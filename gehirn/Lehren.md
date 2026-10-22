---
typ: "lehren"
---
%% BOT-ANFANG – diesen Teil schreibt der Bot bei jedem Lauf neu. %%
# 🎓 Lehren

Hier sammelt der Bot, was er aus seinen Fehlern und Erfolgen zieht. **Automatisch ändert er dabei nur, welche Strategien er handelt** (Lernregel unten) – und hält sich an [[Meine Regeln]]. Muster wie „auf Aktie X läuft es schlecht“ zeigt er dir nur: Bei wenigen Trades ist das oft Zufall, und wer jedem Zufall hinterherläuft, verliert am Ende mehr.

## Was der Bot gerade daraus macht (Lernregel)

Ab 20 gedachten Trades pausiert er eine Strategie, wenn sie im Schnitt mehr als 0,1 R je Trade verliert, und nimmt sie wieder, sobald der Schnitt im Plus ist. Ab 50 Trades muss sie über ihre ganze Geschichte im Plus sein.

- [[Strategien/Ausbruch Long|Ausbruch ↑]]: ⏸ pausiert – die letzten 60 Trades liefen schlecht (Ø -0,05 R)
- [[Strategien/Abbruch Short|Abbruch ↓]]: ⏸ aus – über ihre ganze Geschichte im Minus (Ø -0,02 R über 78 Trades)
- [[Strategien/RSI-2-Rücksetzer Long|RSI-2-Rücksetzer ↑]]: ✅ aktiv (Ø +0,22 R über die letzten 60 Trades)
- [[Strategien/RSI-2-Übertreibung Short|RSI-2-Übertreibung ↓]]: ⏸ aus – über ihre ganze Geschichte im Minus (Ø -0,10 R über 79 Trades)
- [[Strategien/Gegenbewegung Long|Gegenbewegung ↑]]: ✅ aktiv (Ø +0,14 R über die letzten 60 Trades)
- [[Strategien/Rückfall Short|Rückfall ↓]]: ⏸ pausiert – die letzten 34 Trades liefen schlecht (Ø -0,28 R)
- [[Strategien/MACD-Wende Long|MACD-Wende ↑]]: ⏸ pausiert – die letzten 60 Trades liefen schlecht (Ø -0,26 R)
- [[Strategien/MACD-Wende Short|MACD-Wende ↓]]: ⏸ aus – über ihre ganze Geschichte im Minus (Ø -0,11 R über 114 Trades)
- [[Strategien/Rücksetzer Long|Rücksetzer ↑]]: ✅ aktiv (Ø -0,01 R über die letzten 60 Trades)
- [[Strategien/Erholung Short|Erholung ↓]]: ⏸ aus – über ihre ganze Geschichte im Minus (Ø -0,05 R über 198 Trades)
- [[Strategien/Squeeze-Ausbruch Long|Squeeze-Ausbruch ↑]]: ✅ aktiv (Ø +0,07 R über die letzten 60 Trades)
- [[Strategien/Squeeze-Abbruch Short|Squeeze-Abbruch ↓]]: ⏸ pausiert – die letzten 42 Trades liefen schlecht (Ø -0,26 R)
- [[Strategien/EMA-Kreuz Long|EMA-Kreuz ↑]]: ⏸ aus – über ihre ganze Geschichte im Minus (Ø -0,02 R über 332 Trades)
- [[Strategien/EMA-Kreuz Short|EMA-Kreuz ↓]]: ⏸ pausiert – die letzten 60 Trades liefen schlecht (Ø -0,09 R)
- [[Strategien/ATR-Ausbruch Long|ATR-Ausbruch ↑]]: ✅ aktiv (Ø +0,08 R über die letzten 60 Trades)
- [[Strategien/ATR-Abbruch Short|ATR-Abbruch ↓]]: ⏸ aus – über ihre ganze Geschichte im Minus (Ø -0,05 R über 115 Trades)

### Änderungen der letzten 30 Tage

- Fr 02.10.: [[Strategien/Rücksetzer Long|Rücksetzer ↑]] ⏸ pausiert/aus
- Mi 14.10.: [[Strategien/Rücksetzer Long|Rücksetzer ↑]] ✅ wieder aktiv

## Muster im Strategie-Tagebuch (alle Strategien, alle Aktien)

- Insgesamt: 3574 Trades · Ø +0,08 R · Treffer 45 %
- Stop: 1443× (40 %), Ø -1,00 R
- Ziel: 766× (21 %), Ø +1,73 R
- Zeitstopp: 571× (16 %), Ø +0,52 R
- vor Quartalszahlen: 425× (12 %), Ø +0,26 R
- Stop (Kurslücke): 233× (7 %), Ø -1,21 R
- Ziel (Kurslücke): 136× (4 %), Ø +1,92 R
- Long: 2825 Trades · Ø +0,11 R · Treffer 46 %
- Short: 749 Trades · Ø -0,07 R · Treffer 40 %

### Rangliste der Aktien (ab 20 Trades, nach Ø R)

1. [[Aktien/AMD|AMD]]: 143 Trades · Ø +0,33 R · Treffer 50 %
2. [[Aktien/NVDA|NVDA]]: 167 Trades · Ø +0,29 R · Treffer 55 %
3. [[Aktien/JPM|JPM]]: 170 Trades · Ø +0,22 R · Treffer 52 %
…
22. [[Aktien/XOM|XOM]]: 143 Trades · Ø -0,13 R · Treffer 38 %
23. [[Aktien/MELI|MELI]]: 146 Trades · Ø -0,21 R · Treffer 34 %
24. [[Aktien/CRWV|CRWV]]: 32 Trades · Ø -0,44 R · Treffer 25 %
- Hinweis: Selbst 20–50 Trades je Aktie sind wenig. Sperren kannst du eine Aktie in [[Meine Regeln]].

## Aus dem Übungsdepot (echte Vorwärts-Trades)

- Noch keine abgeschlossenen Trades – das Übungsdepot läuft seit 2026-10-20.

Übersicht: [[Start]] · [[Meine Regeln]]
%% BOT-ENDE %%