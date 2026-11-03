# 🔬 Forschungs-Bot

Der Forschungs-Bot sucht jeden Tag eine neue Idee für bessere Käufe oder Verkäufe, zum Beispiel aus Fachartikeln,
Forschungsarbeiten oder Trading-Büchern, und testet sie ehrlich. **Eingebaut wird eine Idee nur per Pull Request und
erst nach deinem „Ja“.**

## So läuft ein Tag

1. **Idee suchen** (Claude, geplante Aufgabe): Er liest vorher, was schon geprüft wurde
   (`gehirn/Notizen/Was der Bot schon weiß.md`), damit nichts doppelt getestet wird. Dann schreibt er die Idee als
   kleine Datei nach `forschung/ideen/<name>.py`. Wie so eine Datei aussieht, zeigt
   [beispiel_tagesbremse.py](ideen/beispiel_tagesbremse.py).
2. **Rechnen** (GitHub, kostet kein Claude-Limit): Der Ablauf [forschung.yml](../.github/workflows/forschung.yml)
   startet von selbst, sobald eine neue Idee hochgeladen ist. Er rechnet den Rückblick mit dem echten Bot auf der
   Watchlist (2010–2014, 2015–2021, 2022–2026, mit Gebühr und Spread) und legt das Ergebnis in `forschung/ergebnisse/`
   ab.
3. **Auswerten** (Claude, am nächsten Tag): Ergebnis lesen, im Gehirn festhalten
   (`gehirn/Notizen/Forschung – Tagebuch.md` und `Was der Bot schon weiß.md`), kurze Meldung im Thema
   „🔬 Forschungs-Bot“ (Tab Issues).

## Ehrlich prüfen

- **Kein Blick in die Zukunft:** Jede Information zählt erst ab dem Tag nach ihrer Veröffentlichung.
- **Bestanden** hat eine Idee nur, wenn sie in allen drei Zeiträumen besser ist und der größte Rückgang nirgends
  deutlich größer wird.
- **Gegenprobe mit Zufall:** Schon die Reihenfolge, in der gleich gute Signale gekauft werden, verschiebt die Rendite
  zufällig um bis zu ±2 Punkte im Jahr. Ideen, die nur auswählen oder sortieren, bekommen deshalb eine Gegenprobe mit
  zufälligen Signalen (`gegenprobe` in der Ideen-Datei). Schlägt die Idee den Zufall nicht, gilt sie als nicht
  bewiesen.

## Experimentier-Depot

- **Eigenes Übungsdepot mit 10.000 € Spielgeld** in `forschung/experiment_depot.json`, gleiche Grenzen wie das
  Übungsdepot: 1 % Risiko je Trade, höchstens 7 Positionen, 5 % Gesamtrisiko.
- **Es handelt die Idee aus [experiment.json](experiment.json).** Zum Start ist das „Lernmodell: beste Punktzahl
  zuerst“.
- **Es läuft nach jedem Morgen-Lauf des Bots.** Bericht: [BERICHT.md](BERICHT.md). Auf der Webseite steht es im
  Bereich „Forschung“ neben dem Übungsdepot.
- Übungsdepot und Claude-Depot werden dabei nur gelesen, nie verändert.
- **Erst nach mindestens 3 Monaten** sagt der Vergleich etwas. Läuft eine Idee dort nicht schlechter, schlägt der
  Forschungs-Bot sie als Pull Request vor.

## Dateien

| Datei | Inhalt |
|---|---|
| [pruefstand.py](pruefstand.py) | testet eine Idee gegen den jetzigen Bot (`python forschung/pruefstand.py forschung/ideen/<name>.py --cache lern_cache`) |
| [experiment.py](experiment.py) | rechnet das Experimentier-Depot weiter und schreibt `docs/forschung.json` |
| `ideen/` | die Ideen als kleine Python-Dateien |
| `ergebnisse/` | Ergebnis je Idee (Tabelle) und `uebersicht.json` für die Webseite |

Simulation mit Spielgeld, keine Anlageberatung.
