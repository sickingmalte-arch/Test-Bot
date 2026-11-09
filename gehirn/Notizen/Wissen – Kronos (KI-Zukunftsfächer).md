---
tags: [wissen, ki, forschung]
---
# 🔮 Wissen – Kronos (KI rechnet viele Zukünfte)

Stand: 09.11.2026 · Anlass: TikTok-Video „Kronos: KI rechnet 100 Bitcoin-Zukünfte durch und liegt trotzdem …“. Zurück zur [[Start|Startseite]] · Versuch im Bot: `forschung/kronos_ergebnis.md` · alle Tests: [[Notizen/Was der Bot schon weiß]].

## Was Kronos ist
- **Ein „Grundmodell“ für Kerzen-Charts** (K-Linien) von der Tsinghua-Universität, offen (MIT-Lizenz): [github.com/shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos). Paper „Kronos: A Foundation Model for the Language of Financial Markets“ (arXiv 2508.02739, August 2025), angenommen bei der Konferenz AAAI 2026.
- **Trainiert mit über 12 Milliarden Kerzen von 45 Börsen.** Einen Zeitraum der Trainingsdaten nennen Seite und Code nicht – deshalb kann man nicht sicher sagen, welche Jahre das Modell „noch nicht kennt“.
- **So funktioniert es:** Ein „Tokenizer“ übersetzt jede Kerze (Eröffnung, Hoch, Tief, Schluss, Volumen) in Zeichen wie Wörter, ein Transformer (wie bei Sprach-KIs) sagt dann Kerze für Kerze die nächste voraus – mit Zufall, deshalb kommt bei jedem Durchgang eine andere Zukunft heraus. Viele Durchgänge ergeben den „Fächer“ aus dem Video.
- **Modelle:** Kronos-mini (4,1 Mio. Parameter, 2048 Kerzen Rückblick), Kronos-small (24,7 Mio., 512), Kronos-base (102,3 Mio., 512); Kronos-large (499 Mio.) ist nicht veröffentlicht. Gewichte auf Hugging Face (NeoQuasar).
- **Wichtiges Detail im Code:** Mit `sample_count` werden mehrere Zukünfte gerechnet, aber gemittelt zurückgegeben – für einen echten Fächer braucht man die einzelnen Pfade (im Versuch: 50 Kopien mit je einer Probe).

## Was die Erfinder behaupten
- Gegenüber dem besten anderen Zeitreihen-Grundmodell 93 % bessere Rangfolge-Treffsicherheit (RankIC), 9 % kleinerer Fehler bei der Schwankung, 22 % bessere künstliche Kerzen. Das sind eigene Angaben; in einer Tabelle des Papers liegt der RankIC von Kronos-small z. B. bei 0,0617 (chinesische Aktien) – also eine sehr schwache, wenn auch messbare Ordnung.
- Die mitgelieferte Handelsstrategie ist ausdrücklich nur eine Vorführung, „kein fertiges Handelssystem“, ohne Gebühren, Spread und Risiko-Regeln.

## Was unabhängige Tests zeigen (soweit gefunden)
- **Bitcoin, 5-Minuten-Kerzen, 497 Trades, zeitlich getrennt:** Treffsicherheit statistisch nicht von einer Brownschen Bewegung (Zufallsweg) zu unterscheiden (Brier-Wert 0,189 gegen 0,188).
- **Indische Aktien, nachtrainiert:** besser „geeicht“, aber keine Vorhersagekraft (RankIC −0,011 über 100 Testtage).
- **Nutzerberichte auf GitHub:** Richtung nahe am Münzwurf, Hang zur Rückkehr zum Mittelwert, ein Datenleck-Fehler im Nachtrainieren.
- Allgemein: Kein bekanntes System sagt die Richtung einzelner Aktien deutlich besser als etwa 55 % voraus.

## Was das für den Bot heißt
- Das deckt sich mit unseren eigenen Tests: Schwankung lässt sich vorhersagen, Richtung kaum (Lernmodell, Muster-Gedächtnis, Ziel-Chance).
- **Ein Rückblick mit Kronos wäre unehrlich** – das Modell kann die Jahre 2010–2026 im Training gesehen haben.
- **Deshalb läuft seit dem 08.11.2026 ein Versuch nur nach vorne** (`forschung/kronos_versuch.py`, GitHub-Lauf „Kronos-Versuch“): Für jedes neue Kauf-Signal rechnet Kronos-small 50 Zukünfte über 20 Handelstage. Verglichen wird mit einem Zufallsweg, ob zuerst das Ziel oder der Stop kommt. Vorher festgelegt: Ab 30 ausgewerteten Signalen zählt Kronos nur als besser, wenn sein Brier-Wert klar unter dem des Zufallswegs liegt (90-%-Intervall ganz unter 0). Der Bot kauft nicht danach.

## Erweiterung am 09.11.2026 (Wunsch: „bau alles“)
Aus dem Befund oben drei Verbesserungen, alle vor dem Rechnen festgelegt und nur als Messung:
1. **Schwankung statt Richtung:** Das Paper nennt die Schwankung als Stärke (9 % kleinerer Fehler). Jetzt wird auch die vorhergesagte Tagesspanne (Hoch−Tief) und die Schwankung der Schlusskurse gespeichert und nach 20 Tagen mit der echten verglichen. Vergleich: einfach die letzten 20 Tage fortschreiben. Zusätzlich ohne Urteil: die Rangfolge – erkennt Kronos wenigstens, welche Aktien unruhiger werden, auch wenn seine Kerzen zu groß sind?
2. **Weniger übermütig:** Variante „small-64-T15“ rechnet mit mehr Zufall (Temperatur 1,5 statt 1,0, ohne Abschneiden der unwahrscheinlichen Zeichen). Wenn die festen 0-%/100-%-Aussagen nur daher kommen, dass das Modell zu sicher würfelt, sollte der Brier-Wert hier besser werden.
3. **Das größere Modell:** Variante „base-256“ mit Kronos-base (102 Mio. statt 24,7 Mio. Parameter). Es rechnet etwa viermal so lange, deshalb nur die ersten 3 Signale am Tag und nur, solange das Zeitbudget (80 Minuten) reicht.

**Auf der Webseite** (Bereich „Kronos“, Daten in `docs/kronos.json`): Zwischenstand je Variante und für jedes Signal der Fächer – die Fläche, in der 8 von 10 Zukünften liegen, die mittlere Zukunft, Stop und Ziel und nach 20 Tagen der echte Verlauf.

Damit sind es 4 Varianten × 2 Fragen = 8 Vergleiche. Bei so vielen kann einer zufällig gut aussehen – das steht im Bericht dabei. Urteil je Variante erst ab 30 ausgewerteten Signalen.

## Probeläufe am 08.11.2026 (Signale vom 05.11., noch ohne Ergebnis)
Kronos-small, je 50 Zukünfte über 20 Handelstage, gerechnet bei GitHub (etwa 2,5 Minuten je Aktie):

| Aktie | Stop / Ziel | Kronos 256 Tage: Ziel / Stop zuerst · Mitte nach 20 Tagen | Kronos 64 Tage: Ziel / Stop zuerst · Mitte | Zufallsweg: Ziel zuerst |
|---|---|---|---|---:|
| AAPL | −7,7 / +7,7 % | 2 % / 96 % · −8,9 % (Kurs 18 % über Ø) | 0 % / 8 % · −1,1 % (4 % über Ø) | 27 % |
| AMZN | −10,9 / +10,9 % | 6 % / 6 % · +0,9 % (8 % über Ø) | 2 % / 2 % · −1,3 % (2 % über Ø) | 25 % |
| COST | −5,7 / +5,7 % | 0 % / 100 % · −9,5 % (12 % über Ø) | 0 % / 100 % · −10,6 % (12 % über Ø) | 32 % |
| PLTR | −15,7 / +12,5 % | 44 % / 50 % · −3,2 % (3 % unter Ø) | 100 % / 0 % · +17,4 % (16 % unter Ø) | 46 % |
| XOM | −7,3 / +5,9 % | 4 % / 72 % · −2,6 % (13 % über Ø) | 80 % / 14 % · +5,9 % (1 % unter Ø) | 43 % |

**Befund:** Auf Tageskerzen von Aktien zieht Kronos den Kurs fast immer zum Durchschnitt des Rückblick-Fensters zurück – egal ob 256 oder 64 Tage – und das mit großer Sicherheit (oft alle 50 Zukünfte in dieselbe Richtung). Seine Tageskerzen sind etwa 1,2- bis 1,7-mal so groß wie echte. Das passt zu den Nutzerberichten („Hang zur Rückkehr zum Mittelwert“). Ob das zufällig manchmal stimmt, zeigt erst der Versuch nach vorne – bei so festen 0-%/100-%-Aussagen wird jeder Irrtum im Brier-Wert teuer.

## Probelauf am 09.11.2026 (alle 4 Varianten, Probe mit Stop und Ziel ±5 %)
Ohne echtes Kauf-Signal an dem Tag – deshalb zwei Aktien mit gedachtem Stop −5 % und Ziel +5 %, nur zum Messen. Je 50 Zukünfte über 20 Handelstage, gerechnet bei GitHub:

| Aktie (Kurs zum Ø 256 / 64 Tage) | small-256 | small-64 | small-64-T15 | base-256 | Zufallsweg |
|---|---|---|---|---|---:|
| INTU (−17,6 % / +5,2 %) | Ziel 26 % / Stop 74 % · Mitte −9,1 % | 72 % / 28 % · −1,1 % | 42 % / 58 % · −4,1 % | 40 % / 60 % · −6,9 % | Ziel 51 % |
| AAPL (+17,2 % / +3,7 %) | 2 % / 98 % · −7,4 % | 22 % / 16 % · −0,3 % | 38 % / 58 % · −2,9 % | 0 % / 100 % · −12,1 % | Ziel 44 % |
| Tagesspanne INTU / AAPL (letzte 20 Tage: 3,9 % / 2,1 %) | 6,1 % / 2,8 % | 4,3 % / 2,3 % | 6,9 % / 3,4 % | 8,8 % / 3,2 % | – |
| Rechenzeit je Signal | 161–165 s | 29 s | 29 s | 508–519 s | – |

**Befund:**
- **Mehr Zufall (T15)** macht die Aussagen weniger übermütig: Bei AAPL sind es 38/58 statt 2/98.
- **Das große Modell (base)** ist bei AAPL genauso fest (0/100) und zieht noch stärker nach unten.
- **Bei der Schwankung** liegt Kronos über den letzten 20 Tagen. Am nächsten kommt die Variante mit 64 Tagen Rückblick.
- **Rechenzeit:** Das große Modell braucht etwa 8,5 Minuten je Signal. Mit 8 Signalen am Tag (die ersten 3 auch mit base) dauert ein Lauf knapp eine Stunde – das passt in das Zeitbudget.

## Quellen
- Repository und Code: https://github.com/shiyu-coder/Kronos
- Paper: https://arxiv.org/abs/2508.02739 · AAAI: https://ojs.aaai.org/index.php/AAAI/article/view/39730
- Bitcoin-Test gegen Brownsche Bewegung: https://1023jack.com/market/week-three-foundation-model-vs-brownian-motion-kronos-on-five-minute-btc-2/
- Nachtraining Indien („improved calibration and produced no alpha“): https://huggingface.co/sahil007123/kronos-nse-1d
- Vergleich von Zeitreihen-Grundmodellen in der Finanzwelt: https://arxiv.org/abs/2511.18578
