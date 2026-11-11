# 🔮 Kronos-Versuch (nach vorne)

Stand 11.11.2026 · 50 Zukünfte je Signal und Variante, 20 Handelstage. Varianten: small-256 (Kronos-small, Rückblick 256, Temperatur 1,0); small-64 (Kronos-small, Rückblick 64, Temperatur 1,0); small-64-T15 (Kronos-small, Rückblick 64, Temperatur 1,5); base-256 (Kronos-base, Rückblick 256, Temperatur 1,0, nur 3 Signale am Tag). Dazu abgeleitet: Mittel aller Varianten, Mittel ½ + Zufall ½, Mittel geeicht (Schwankung). Nur eine Messung – der Bot kauft nicht danach.

**Fragen:** (1) Sagt Kronos besser voraus, ob zuerst das Ziel oder zuerst der Stop kommt, als ein Zufallsweg ohne Richtung – und als die Ziel-Chance, die der Bot schon anzeigt? (2) Sagt Kronos die Schwankung der nächsten 20 Tage besser voraus, als einfach die letzten 20 Tage fortzuschreiben?

**Vorher festgelegt:** Ab 30 ausgewerteten Signalen je Vorhersage (Watchlist: ab 15 ausgewerteten Tagen) gilt sie als besser, wenn ihr Fehler kleiner ist und das 98-%-Bootstrap-Intervall des Unterschieds ganz unter 0 liegt. Es sind viele Vergleiche – deshalb die strenge Hürde (seit 09.11. abends, vorher 90 %, festgelegt bevor ein Signal ausgewertet war). Die Bot-Formel rechnet ohne Stop und liegt deshalb eher zu hoch.

**Schon in den Probeläufen sichtbar (08./09.11.):** Kronos zieht den Kurs stark zum Durchschnitt des Rückblicks zurück (oft fast alle Zukünfte in dieselbe Richtung), und seine Tageskerzen sind größer als echte. Mehr Zufall (T15) macht die Aussagen vorsichtiger.

## 1. Kauf-Signale des Bots

Noch keine Signale ausgewertet (das geht frühestens 20 Handelstage nach dem Signal).

## 2. Alle Aktien der Watchlist täglich (small-64, small-64-T15, Stop −2 ATR, Ziel +2 ATR)

Gerechnet: 72 an 3 Tagen · ausgewertet: 0 an 0 Tagen · offen: 72. Aktien am selben Tag laufen ähnlich – deshalb zählt die Zahl der Tage, und das Intervall zieht ganze Tage.

## Alle Kauf-Signale

| Signaltag | Aktie | Stop / Ziel | small-256: Ziel / Stop · Mitte 20 T. | small-64: Ziel / Stop · Mitte 20 T. | small-64-T15: Ziel / Stop · Mitte 20 T. | base-256: Ziel / Stop · Mitte 20 T. | Zufallsweg Ziel | Bot-Formel | Ergebnis |
|---|---|---|---|---|---|---|---:|---:|---|

Offen: 0 Signale warten auf ihre 20 Handelstage. Watchlist-Einzelwerte: `forschung/kronos_liste_log.json`. Kronos-Code: `forschung/kronos_modell/` (MIT-Lizenz). Hintergrund: `gehirn/Notizen/Wissen – Kronos (KI-Zukunftsfächer).md`. Simulation, keine Anlageberatung.
