---
tags: [wissen, ki, forschung]
---
# 🔮 Wissen – Kronos (KI rechnet viele Zukünfte)

Stand: 08.11.2026 · Anlass: TikTok-Video „Kronos: KI rechnet 100 Bitcoin-Zukünfte durch und liegt trotzdem …“. Zurück zur [[Start|Startseite]] · Versuch im Bot: `forschung/kronos_ergebnis.md` · alle Tests: [[Notizen/Was der Bot schon weiß]].

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

## Quellen
- Repository und Code: https://github.com/shiyu-coder/Kronos
- Paper: https://arxiv.org/abs/2508.02739 · AAAI: https://ojs.aaai.org/index.php/AAAI/article/view/39730
- Bitcoin-Test gegen Brownsche Bewegung: https://1023jack.com/market/week-three-foundation-model-vs-brownian-motion-kronos-on-five-minute-btc-2/
- Nachtraining Indien („improved calibration and produced no alpha“): https://huggingface.co/sahil007123/kronos-nse-1d
- Vergleich von Zeitreihen-Grundmodellen in der Finanzwelt: https://arxiv.org/abs/2511.18578
