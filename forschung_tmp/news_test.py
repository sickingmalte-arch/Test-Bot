"""Temporär: Schlagzeilen mit den Funktionen des Bots bei GitHub abrufen (wird wieder gelöscht)"""
import sys
import pandas as pd
sys.path.insert(0, ".")
import swing_scanner as sw  # noqa: E402

ticker = ["PLTR", "NOW", "TSLA", "LLY", "AMD", "MSFT", "AAPL", "META"]
with sw.YahooRuhig(False) as sammler:
    erg = sw.hole_zusatzdaten([], ticker, sammler)
for t in ticker:
    e = erg[t]
    print(f"{t}: {e['news_info']}, {len(e['news'] or [])} Meldungen")
heute = pd.Timestamp("2026-10-22")
zeilen = [{"Ticker": t, "Signal": sw.KAUFEN, "_stand": heute} for t in ticker]
news = sw.werte_news(erg, heute, zeilen)
for t, n in news.items():
    print(f"== {t} | Spalte: {n['spalte']!r} | warnt: {n.get('warnung')}")
    for z in n["zeilen"]:
        print(f"   {z['zeit']:%d.%m. %H:%M} {z['quelle']}: {z['titel'][:90]} {z['ereignisse']}")
