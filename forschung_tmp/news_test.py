"""Temporär: Welche Aktien nennt Yahoo zu den Suchtreffern? (wird wieder gelöscht)"""
import yfinance as yf

for t in ("TSLA", "NOW", "MSFT", "AAPL", "PLTR"):
    treffer = yf.Search(t, max_results=1, news_count=10).news or []
    mit = sum(1 for n in treffer if t in (n.get("relatedTickers") or []))
    ohne_feld = sum(1 for n in treffer if "relatedTickers" not in n)
    print(f"== {t}: {len(treffer)} Treffer, davon {mit} mit {t} in relatedTickers, {ohne_feld} ohne das Feld")
    for n in treffer:
        print(f"   {t in (n.get('relatedTickers') or [])!s:5} {n.get('relatedTickers')} | {n.get('title', '')[:80]}")
