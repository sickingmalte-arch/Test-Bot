"""Temporärer Test (wird wieder gelöscht): Schlagzeilen holen, Links zeigen, mit zwei Diensten übersetzen."""
import json, time, urllib.parse, urllib.request
import yfinance as yf

def hole(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Swing-Bot)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def mymemory(text):
    d = hole("https://api.mymemory.translated.net/get?" + urllib.parse.urlencode({"q": text, "langpair": "en|de"}))
    return d.get("responseStatus"), d.get("quotaFinished"), d["responseData"]["translatedText"], d["responseData"].get("match")

def google(texte):
    url = "https://translate.googleapis.com/translate_a/t?" + urllib.parse.urlencode([("client", "gtx"), ("sl", "en"), ("tl", "de"), ("dj", "1")] + [("q", t) for t in texte])
    return hole(url)

titel = []
for t in ["TSLA", "NOW", "LLY", "PLTR", "AMD", "MSFT"]:
    news = yf.Search(t, max_results=1, news_count=10).news or []
    news = [n for n in news if t in (n.get("relatedTickers") or [])][:2]
    for n in news:
        print(t, "|", n.get("title"), "|", n.get("link"), "|", n.get("publisher"), "| Felder:", sorted(n.keys()))
        titel.append(n.get("title"))
print("\n--- MyMemory ---")
start = time.time()
for x in titel:
    try:
        print(mymemory(x))
    except Exception as e:
        print("Fehler", type(e).__name__, e)
print("Dauer", round(time.time() - start, 1), "s")
print("\n--- Google (inoffiziell) ---")
start = time.time()
try:
    print(json.dumps(google(titel), ensure_ascii=False)[:3000])
except Exception as e:
    print("Fehler", type(e).__name__, e)
print("Dauer", round(time.time() - start, 1), "s")
