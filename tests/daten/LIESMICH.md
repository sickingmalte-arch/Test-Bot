# Feste Testdaten

Diese Dateien ändern sich nie. Mit ihnen rechnet der Sicherheits-Check (`tests/`) immer gleich – ohne Yahoo.

- `kurse/`: Tageskerzen 2017–2024 (Eröffnung, Hoch, Tief, Schluss, Volumen; Kurse wie bei Yahoo um Splits und Dividenden bereinigt, Stand Oktober 2026) für AAPL, NVDA, MSFT, AMD (4 × Technologie, damit die Grenze „höchstens 2 je Branche“ greift), LLY, XOM, JPM, COST, dazu der Nasdaq-100 (QQQ, Marktfilter) und der Euro-Kurs (EURUSD=X).
- `termine/`: Quartalszahlen-Termine dieser Aktien bis März 2025 (für die Quartalszahlen-Regel).
- `papier_depot_2026-10-21.json`: die erste gespeicherte Fassung des Übungsdepots (21.10.2026) – sie muss lesbar bleiben.
- `broker_depot.json`: Stand des Übungsdepots vom 27.10.2026 für die Tests des Broker-Bots (NOW und LLY melden am 28./29.10. Zahlen, PLTR wartet als Auftrag).
