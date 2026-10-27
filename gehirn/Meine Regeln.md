# 📝 Meine Regeln für den Bot

Der Bot liest diese Seite bei jedem Lauf. **Haken setzen = Regel gilt.** Er versteht nur die Kästchen – für eigene Gedanken ist unten Platz.

> [!tip] So geht's
> - Kästchen antippen, damit ein Haken erscheint. Haken weg = Regel aus.
> - Eine andere Aktie sperren: unter „Aktien sperren“ eine neue Zeile `- [x] KÜRZEL`, z. B. `- [x] TSLA` (das Kürzel wie im Bot, nicht der Firmenname).
> - Ein kurzer Grund darf dahinter stehen: `- [x] HIMS – zu wild`.
> - Damit der Bot den Haken sieht, muss die Seite bei GitHub ankommen: in Obsidian danach **Git: Commit-and-sync** (braucht den Zugangs-Token aus der Anleitung) – oder gleich auf GitHub abhaken. Ob es angekommen ist, steht nach dem nächsten Lauf auf der Startseite unter „Deine Regeln“.
> - Ab dem nächsten Lauf gilt die Regel für Signale und Papier-Depot; offene Aufträge dafür werden gestrichen, offene Positionen laufen bis Stop, Ziel, Zeitstopp oder vor Quartalszahlen weiter. Im Rückblick (Simulation der letzten Monate) gilt sie auch rückwirkend.

> [!info] 🧊 Die Kaufregeln des Bots sind bis Ende Januar 2027 eingefroren
> - Das Übungsdepot läuft seit dem 20.10.2026 als echter Test mit virtuellem Geld. Ehrlich messen kann es nur, wenn sich die Regeln des Bots dabei nicht ändern: keine neuen oder geänderten Strategien, Stops, Ziele, Limits, Lernregel, Positionsgrößen oder Grenzen bis zum 31.01.2027.
> - Webseite, Nachrichten und Handy dürfen weiter verbessert werden.
> - Ein automatischer Sicherheits-Check bei GitHub prüft das bei jeder Änderung am Bot (siehe README, „Sicherheits-Check“).
> - Deine Haken unten bleiben deine Entscheidung. Aber jeder neue Haken ändert, was das Übungsdepot kauft – dann misst es nicht mehr nur den Bot.

## Aktien sperren (der Bot kauft oder shortet sie nicht)

- [ ] SE
- [ ] HIMS
- [ ] NOW
- [ ] INTU
- [ ] CRWV
- [ ] NBIS
- [ ] MELI
- [ ] IREN
- [ ] NFLX
- [ ] AAPL
- [ ] ASTS
- [ ] SOFI
- [ ] NVDA
- [ ] MSFT
- [ ] AMZN
- [ ] META
- [ ] GOOGL
- [ ] TSLA
- [ ] AMD
- [ ] PLTR
- [ ] JPM
- [ ] LLY
- [ ] XOM
- [ ] COST

## Strategien ausschalten (zusätzlich zur Lernregel des Bots)

- [ ] Ausbruch ↑
- [ ] Abbruch ↓
- [ ] RSI-2-Rücksetzer ↑
- [ ] RSI-2-Übertreibung ↓
- [ ] Gegenbewegung ↑
- [ ] Rückfall ↓
- [ ] MACD-Wende ↑
- [ ] MACD-Wende ↓
- [ ] Rücksetzer ↑
- [ ] Erholung ↓
- [ ] Squeeze-Ausbruch ↑
- [ ] Squeeze-Abbruch ↓
- [ ] EMA-Kreuz ↑
- [ ] EMA-Kreuz ↓
- [ ] ATR-Ausbruch ↑
- [ ] ATR-Abbruch ↓

## Meine Notizen

Hier kannst du frei schreiben – der Bot liest diesen Teil nicht.
