# 🔮 Kronos-Versuch (nach vorne)

Stand 09.11.2026 · 50 Zukünfte je Signal und Variante, 20 Handelstage. Varianten: small-256 (Kronos-small, Rückblick 256, Temperatur 1,0); small-64 (Kronos-small, Rückblick 64, Temperatur 1,0); small-64-T15 (Kronos-small, Rückblick 64, Temperatur 1,5); base-256 (Kronos-base, Rückblick 256, Temperatur 1,0, nur 3 Signale am Tag). Nur eine Messung – der Bot kauft nicht danach.

**Fragen:** (1) Sagt Kronos besser voraus, ob zuerst das Ziel oder zuerst der Stop kommt, als ein Zufallsweg ohne Richtung? (2) Sagt Kronos die Schwankung der nächsten 20 Tage besser voraus, als einfach die letzten 20 Tage fortzuschreiben?

**Vorher festgelegt:** Ab 30 ausgewerteten Signalen je Variante gilt sie als besser, wenn ihr Fehler kleiner ist und das 90-%-Bootstrap-Intervall des Unterschieds ganz unter 0 liegt. 4 Varianten × 2 Fragen = 8 Vergleiche – einer davon kann zufällig gut aussehen.

**Schon in den Probeläufen sichtbar (08.11.):** Kronos zieht den Kurs stark zum Durchschnitt des Rückblicks zurück (oft alle 50 Zukünfte in dieselbe Richtung), und seine Tageskerzen sind 1,2- bis 1,7-mal so groß wie echte.

**Ergebnis:** noch keine Signale ausgewertet (das geht frühestens 20 Handelstage nach dem Signal).

## Alle Signale

| Signaltag | Aktie | Stop / Ziel | small-256: Ziel / Stop · Mitte 20 T. | small-64: Ziel / Stop · Mitte 20 T. | small-64-T15: Ziel / Stop · Mitte 20 T. | base-256: Ziel / Stop · Mitte 20 T. | Zufallsweg Ziel | Ergebnis |
|---|---|---|---|---|---|---|---:|---|

Offen: 0 Signale warten auf ihre 20 Handelstage. Kronos-Code: `forschung/kronos_modell/` (MIT-Lizenz). Hintergrund: `gehirn/Notizen/Wissen – Kronos (KI-Zukunftsfächer).md`. Simulation, keine Anlageberatung.
