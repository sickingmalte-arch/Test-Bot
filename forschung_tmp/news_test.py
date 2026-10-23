"""Temporär: Was liefert Yahoo bei GitHub für Schlagzeilen? (wird wieder gelöscht)"""
import json, logging, sys
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format="LOG %(name)s %(levelname)s %(message)s")
for name in ("urllib3", "peewee", "curl_cffi"):
    logging.getLogger(name).setLevel(logging.WARNING)
print("yfinance", yf.__version__, "pandas", pd.__version__)
sys.path.insert(0, ".")
import swing_scanner as sw  # noqa: E402

ab = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=4)
for t in ("AAPL", "PLTR", "TSLA"):
    for art, holen in (("get_news(count=10)", lambda tk: tk.get_news(count=10)),
                       ("get_news(count=10, tab='news')", lambda tk: tk.get_news(count=10, tab="news")),
                       ("news-Eigenschaft", lambda tk: tk.news)):
        try:
            n = holen(yf.Ticker(t))
        except Exception as e:
            print(f"== {t} {art}: FEHLER {type(e).__name__}: {e}")
            continue
        print(f"== {t} {art}: Typ {type(n).__name__}, Anzahl {len(n) if hasattr(n, '__len__') else '?'}")
        if n:
            erstes = n[0]
            print("   Schlüssel:", list(erstes)[:12])
            c = erstes.get("content") if isinstance(erstes, dict) else None
            if isinstance(c, dict):
                print("   content-Schlüssel:", list(c)[:20])
                print("   Beispiel:", json.dumps({k: c.get(k) for k in ("title", "pubDate", "displayTime", "contentType")}, default=str)[:300])
                print("   provider:", json.dumps(c.get("provider"), default=str)[:200])
            else:
                print("   Beispiel:", json.dumps(erstes, default=str)[:400])
            lesbar = sw.lies_schlagzeilen(n, ab)
            print(f"   lies_schlagzeilen (letzte 4 Tage): {len(lesbar)}", [s["titel"][:60] for s in lesbar[:3]])
try:
    s = yf.Search("PLTR", news_count=8)
    print("== Search('PLTR').news:", len(s.news or []), [x.get("title", "")[:60] for x in (s.news or [])[:3]])
except Exception as e:
    print("== Search FEHLER", type(e).__name__, e)
