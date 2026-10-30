"""Lernmodell des Swing-Bots: Daten holen und im Zwischenspeicher halten.

- Aktienliste: S&P 500 und Nasdaq-100 von Wikipedia (mit Branche nach GICS). Klappt das nicht, gilt die zuletzt
  gespeicherte Liste – mit Warnung.
- Kurse: Tageskerzen von Yahoo (dividendenbereinigt). Im Zwischenspeicher; neu geholt werden nur die letzten Tage.
  Hat Yahoo ältere Kurse umgerechnet (Dividende, Split), wird die ganze Reihe neu geholt.
- Quartalszahlen: Termine mit erwartetem und gemeldetem Gewinn je Aktie (Gewinnüberraschung) von Yahoo, einmal je Woche.
- Bilanzdaten: von der US-Börsenaufsicht SEC (EDGAR „companyfacts“), einmal je Woche. Jede Zahl trägt das Datum, an dem
  sie veröffentlicht wurde – nur so lassen sich Bewertung, Wachstum und Qualität im Rückblick ehrlich testen.

Alles, was fehlt oder alt ist, landet in einer Liste von Warnungen, die der Bericht deutlich zeigt.

Aufruf (z. B. im Ablauf lernen.yml):  python lernen/daten.py --cache lern_cache [--nur kurse,termine,bilanzen]
"""
import argparse
import gzip
import io
import json
import os
import sys
import time
import urllib.request

import pandas as pd

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_NDX = ["https://en.wikipedia.org/wiki/Nasdaq-100", "https://en.wikipedia.org/wiki/List_of_Nasdaq-100_companies",
            "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"]
SEC_TICKER = "https://www.sec.gov/files/company_tickers.json"
SEC_FAKTEN = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
# Die SEC verlangt eine Kennung mit Name und E-Mail (Secret LERNEN_SEC_KONTAKT). Ohne sie lehnt die SEC ab (Fehler 403).
KENNUNG = os.environ.get("LERNEN_SEC_KONTAKT") or "Test-Bot Swing-Bot (github.com/sickingmalte-arch/Test-Bot)"
START = "2007-01-01"  # 2007 für 200-Tage-Linie und 12-Monats-Momentum ab 2008
# Markt und Vergleich: S&P 500, Nasdaq-100, Volatilität (VIX), Euro-Kurs und die Branchen-Fonds
ZUSATZ = ["SPY", "QQQ", "^VIX", "EURUSD=X", "XLK", "XLF", "XLV", "XLE", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE",
          "XLC"]

# Bilanzposten: je Gruppe mehrere mögliche Namen (Firmen benutzen verschiedene, die Reihenfolge ist der Vorrang)
POSTEN = {
    "umsatz": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
               "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet",
               "SalesRevenueServicesNet"],
    "gewinn": ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "eps": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted", "EarningsPerShareBasic"],
    "brutto": ["GrossProfit"],
    "operativ": ["OperatingIncomeLoss"],
    "eigenkapital": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "schulden": ["Liabilities"],
    "vermoegen": ["Assets"],
    "cashflow": ["NetCashProvidedByUsedInOperatingActivities",
                 "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "investitionen": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "aktien": ["WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"],
}
EINHEIT = {"eps": "USD/shares", "aktien": "shares"}  # sonst USD
FORMULARE = {"10-K", "10-Q", "10-K/A", "10-Q/A", "10-KT"}


def yahoo_name(symbol):
    """Wikipedia schreibt BRK.B, Yahoo BRK-B."""
    return str(symbol).strip().replace(".", "-")


def hole(url, versuche=3, pause=2.0):
    """Text einer Adresse (gzip wird entpackt). Wirft nach mehreren Fehlversuchen die letzte Ausnahme."""
    fehler = None
    for n in range(versuche):
        try:
            anfrage = urllib.request.Request(url, headers={"User-Agent": KENNUNG, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                roh = antwort.read()
                if antwort.headers.get("Content-Encoding") == "gzip":
                    roh = gzip.decompress(roh)
                return roh.decode("utf-8")
        except Exception as e:  # noqa: BLE001 – Netzfehler aller Art: erneut versuchen
            fehler = e
            time.sleep(pause * (n + 1))
    raise fehler


# ----------------------------------------------------------------------------
# Aktienliste
# ----------------------------------------------------------------------------
def _spaltennamen(t):
    return [" ".join(str(x) for x in c) if isinstance(c, tuple) else str(c) for c in t.columns]


def _tabelle_mit(html, mindestens, hoechstens=10_000):
    """Die Tabelle mit einer Ticker-Spalte und passender Zeilenzahl (die Spaltennamen auf Wikipedia ändern sich
    gelegentlich – deshalb tolerant: „Symbol“ oder „Ticker“)."""
    gesehen = []
    for t in pd.read_html(io.StringIO(html)):
        t.columns = _spaltennamen(t)
        gesehen.append((len(t), list(t.columns)[:6]))
        if any(n.lower() in ("symbol", "ticker") or n.lower().startswith(("symbol", "ticker")) for n in t.columns) \
                and mindestens <= len(t) <= hoechstens:
            return t
    raise ValueError(f"Tabelle nicht gefunden (gesehen: {gesehen[:8]})")


def _spalte(t, *teile):
    for c in t.columns:
        if any(teil.lower() in str(c).lower() for teil in teile):
            return t[c]
    return pd.Series([None] * len(t))


def _mit_watchlist(uni, extra):
    """Aktien der Watchlist des Bots, die in keinem der beiden Indizes sind, kommen dazu (Branche aus dem Bot)."""
    neu = [{"ticker": t, "name": t, "sektor": s, "branche": None, "cik": None, "index": "Watchlist"}
           for t, s in (extra or {}).items() if t not in set(uni["ticker"])]
    for t, s in (extra or {}).items():  # Branche ohne GICS-Namen: die aus dem Bot
        if s != "Unbekannt" and t in set(uni["ticker"]) and uni.loc[uni["ticker"] == t, "sektor"].iloc[0] not in GICS.values():
            uni.loc[uni["ticker"] == t, "sektor"] = s
    if "index" in uni:
        maske = uni["ticker"].isin(list(extra or {})) & ~uni["index"].astype(str).str.contains("Watchlist")
        uni.loc[maske, "index"] = uni.loc[maske, "index"].astype(str) + ", Watchlist"
    return pd.concat([uni, pd.DataFrame(neu)], ignore_index=True) if neu else uni


# Die Nasdaq-100-Seite nennt die Branche nach ICB statt GICS: auf GICS umschreiben (für Branchen-Grenze und Merkmale)
ICB = {"Technology": "Information Technology", "Telecommunications": "Communication Services",
       "Health Care": "Health Care", "Financials": "Financials", "Real Estate": "Real Estate",
       "Consumer Discretionary": "Consumer Discretionary", "Consumer Staples": "Consumer Staples",
       "Industrials": "Industrials", "Basic Materials": "Materials", "Energy": "Energy", "Utilities": "Utilities"}


def _branchen(t):
    """(Sektor nach GICS, feinere Branche) einer Wikipedia-Tabelle."""
    for c in t.columns:
        if "gics sector" in c.lower():
            return t[c], _spalte(t, "Sub-Industry")
    for c in t.columns:
        if "icb industry" in c.lower():
            return t[c].map(lambda x: ICB.get(str(x).strip(), x)), _spalte(t, "Subsector")
    return _spalte(t, "Sector"), _spalte(t, "Sub-Industry", "Industry")


def lade_universum(cache, extra=None):
    """Aktienliste mit Branche (GICS) und SEC-Nummer (CIK). extra: Watchlist des Bots {Ticker: Branche}.
    Gibt (DataFrame, Warnungen) zurück."""
    warnungen = []
    datei = os.path.join(cache, "universum.csv")
    try:
        sp = _tabelle_mit(hole(WIKI_SP500), 400, 700)
        ndx, ndx_fehler = None, []
        for url in WIKI_NDX:
            try:
                ndx = _tabelle_mit(hole(url, versuche=2), 90, 130)
                break
            except Exception as e:  # noqa: BLE001
                ndx_fehler.append(f"{url.rsplit('/', 1)[-1]}: {str(e)[:80]}")
        if ndx is None:
            warnungen.append("Nasdaq-100-Liste auf Wikipedia nicht gefunden – nur S&P 500 ("
                             + "; ".join(ndx_fehler) + ").")
        zeilen = {}
        for t, index in ((sp, "S&P 500"), (ndx, "Nasdaq-100")):
            if t is None:
                continue
            sektoren, branchen = _branchen(t)
            for sym, name, sektor, branche, cik in zip(_spalte(t, "Symbol", "Ticker"), _spalte(t, "Security", "Company"),
                                                       sektoren, branchen, _spalte(t, "CIK")):
                y = yahoo_name(sym)
                z = zeilen.setdefault(y, {"ticker": y, "name": name, "sektor": sektor, "branche": branche,
                                          "cik": cik if pd.notna(cik) else None, "index": index})
                if index not in z["index"]:
                    z["index"] += ", " + index
        uni = _mit_watchlist(pd.DataFrame(list(zeilen.values())), extra)
        try:  # SEC-Nummer für Aktien ohne CIK in der Wikipedia-Tabelle (z. B. nur im Nasdaq-100)
            sec = json.loads(hole(SEC_TICKER))
            cik_von = {v["ticker"].upper().replace(".", "-"): int(v["cik_str"]) for v in sec.values()}
            uni["cik"] = [int(c) if pd.notna(c) and str(c).strip() not in ("", "None") else cik_von.get(t)
                          for t, c in zip(uni["ticker"], uni["cik"])]
        except Exception as e:  # noqa: BLE001
            warnungen.append(f"SEC-Nummern (CIK) nicht geladen: {e}")
        os.makedirs(cache, exist_ok=True)
        uni.to_csv(datei, index=False)
        try:  # Änderungen am S&P 500 (für den Hinweis auf die Verzerrung durch verschwundene Aktien)
            aend = pd.read_html(io.StringIO(hole(WIKI_SP500)))[1]
            aend.to_csv(os.path.join(cache, "sp500_aenderungen.csv"), index=False)
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001
        if not os.path.exists(datei):
            raise RuntimeError(f"Aktienliste nicht ladbar und nichts gespeichert: {e}") from e
        uni = _mit_watchlist(pd.read_csv(datei), extra)
        alter = (time.time() - os.path.getmtime(datei)) / 86400
        warnungen.append(f"Aktienliste von Wikipedia nicht geladen ({e}) – benutze die gespeicherte Liste "
                         f"({len(uni)} Aktien, {alter:.0f} Tage alt).")
    uni["cik"] = pd.to_numeric(uni["cik"], errors="coerce")
    return uni, warnungen


# ----------------------------------------------------------------------------
# Kurse
# ----------------------------------------------------------------------------
def kurs_datei(cache, t):
    return os.path.join(cache, "kurse", f"{t.replace('^', '_')}.csv.gz")


def lies_kurse(cache, t):
    f = kurs_datei(cache, t)
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, index_col=0, parse_dates=True)
    df.index.name = "Date"
    return df


def _tabelle(roh, t, mehrere):
    """Yahoo-Rohdaten -> Open/High/Low/Close/Volume dividenden- und splitbereinigt (wie auto_adjust) und dazu
    Roh = Schluss nur splitbereinigt (für Bewertungen mit Bilanzzahlen) und Split = Split-Faktor an dem Tag."""
    try:
        df = roh[t] if mehrere else roh
    except KeyError:
        return None
    if "Close" not in df or df["Close"].dropna().empty:
        return None
    df = df.dropna(subset=["Close"])
    faktor = (df["Adj Close"] / df["Close"]) if "Adj Close" in df else 1.0
    aus = pd.DataFrame({"Open": df["Open"] * faktor, "High": df["High"] * faktor, "Low": df["Low"] * faktor,
                        "Close": df["Adj Close"] if "Adj Close" in df else df["Close"], "Volume": df["Volume"],
                        "Roh": df["Close"],
                        "Split": df["Stock Splits"] if "Stock Splits" in df else 0.0})
    aus.index = pd.DatetimeIndex(aus.index).tz_localize(None).normalize()
    aus.index.name = "Date"
    return aus.astype(float)


def _lade_yahoo(tickers, start):
    import yfinance as yf
    roh = yf.download(tickers, start=start, auto_adjust=False, actions=True, group_by="ticker", threads=True,
                      progress=False)
    return {t: _tabelle(roh, t, True) for t in tickers}


def aktualisiere_kurse(tickers, cache, start=START, block=60):
    """Kurse aller Ticker auf den neuesten Stand. Gibt (Anzahl aktualisiert, Warnungen) zurück."""
    warnungen, neu_voll, anhaengen = [], [], {}
    os.makedirs(os.path.join(cache, "kurse"), exist_ok=True)
    for t in tickers:
        alt = lies_kurse(cache, t)
        if alt is None or len(alt) < 50:
            neu_voll.append(t)
        else:
            anhaengen[t] = alt
    # Neue Tage: die letzten 10 Kalendertage – die Überlappung zeigt, ob Yahoo umgerechnet hat
    ab = (pd.Timestamp.today() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    kurz = list(anhaengen)
    for i in range(0, len(kurz), block):
        teil = kurz[i:i + block]
        try:
            frisch = _lade_yahoo(teil, ab)
        except Exception as e:  # noqa: BLE001
            warnungen.append(f"Yahoo-Kurse für {len(teil)} Aktien nicht geladen: {e}")
            continue
        for t in teil:
            df, alt = frisch.get(t), anhaengen[t]
            if df is None:
                continue
            gemeinsam = df.index.intersection(alt.index)
            if len(gemeinsam):
                faktor = (df.loc[gemeinsam, "Close"] / alt.loc[gemeinsam, "Close"]).median()
                if abs(faktor - 1) > 1e-4:
                    neu_voll.append(t)  # Dividende oder Split: ganze Reihe neu
                    continue
            df = pd.concat([alt[~alt.index.isin(df.index)], df]).sort_index()
            df.to_csv(kurs_datei(cache, t), compression="gzip")
    for i in range(0, len(neu_voll), block):
        teil = neu_voll[i:i + block]
        try:
            frisch = _lade_yahoo(teil, start)
        except Exception as e:  # noqa: BLE001
            warnungen.append(f"Yahoo-Kurse (ganze Reihe) für {len(teil)} Aktien nicht geladen: {e}")
            continue
        for t in teil:
            if frisch.get(t) is not None:
                frisch[t].to_csv(kurs_datei(cache, t), compression="gzip")
    return len(tickers), warnungen


def kurs_pruefung(tickers, cache, letzter_handelstag):
    """Welche Aktien haben gar keine Kurse oder keine vom letzten Handelstag?"""
    fehlen, alt = [], []
    for t in tickers:
        df = lies_kurse(cache, t)
        if df is None or df.empty:
            fehlen.append(t)
        elif df.index[-1] < letzter_handelstag:
            alt.append(t)
    return fehlen, alt


# ----------------------------------------------------------------------------
# Quartalszahlen (Termine und Gewinnüberraschung)
# ----------------------------------------------------------------------------
def termin_datei(cache, t):
    return os.path.join(cache, "termine", f"{t}.csv")


def aktualisiere_termine(tickers, cache, max_alter_tage=7, pause=0.4):
    import yfinance as yf
    os.makedirs(os.path.join(cache, "termine"), exist_ok=True)
    warnungen, fehler = [], []
    for t in tickers:
        f = termin_datei(cache, t)
        if os.path.exists(f) and (time.time() - os.path.getmtime(f)) / 86400 < max_alter_tage:
            continue
        try:
            df = yf.Ticker(t).get_earnings_dates(limit=100)
            if df is not None and len(df):
                df.to_csv(f)
            else:
                fehler.append(t)
        except Exception:  # noqa: BLE001
            fehler.append(t)
        time.sleep(pause)
    if fehler:
        warnungen.append(f"Quartalszahlen-Termine fehlen für {len(fehler)} Aktien (z. B. {', '.join(fehler[:8])}).")
    return warnungen


def lies_termine(cache, t):
    f = termin_datei(cache, t)
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, index_col=0)
    df.index = pd.to_datetime(df.index, utc=True, errors="coerce").tz_convert("America/New_York")
    df = df[df.index.notna()]
    df.index.name = "Earnings Date"
    return df


# ----------------------------------------------------------------------------
# Bilanzdaten von der SEC (mit Veröffentlichungsdatum)
# ----------------------------------------------------------------------------
def bilanz_datei(cache, t):
    return os.path.join(cache, "bilanzen", f"{t}.csv.gz")


def bilanz_zeilen(fakten):
    """companyfacts-JSON -> Zeilen (gruppe, vorrang, start, ende, wert, eingereicht, form). Nur Quartals- und
    Jahresberichte. Jede Zahl so, wie sie ZUERST veröffentlicht wurde (spätere Korrekturen zählen erst ab ihrem
    eigenen Datum nicht – das wäre Wissen aus der Zukunft)."""
    zeilen = []
    gaap = (fakten.get("facts") or {}).get("us-gaap") or {}
    for gruppe, namen in POSTEN.items():
        einheit = EINHEIT.get(gruppe, "USD")
        for vorrang, name in enumerate(namen):
            eintraege = ((gaap.get(name) or {}).get("units") or {}).get(einheit) or []
            for e in eintraege:
                if e.get("form") not in FORMULARE or "end" not in e or "filed" not in e:
                    continue
                zeilen.append((gruppe, vorrang, e.get("start"), e["end"], e.get("val"), e["filed"], e["form"]))
    df = pd.DataFrame(zeilen, columns=["gruppe", "vorrang", "start", "ende", "wert", "eingereicht", "form"])
    if df.empty:
        return df
    df = df.sort_values(["gruppe", "start", "ende", "eingereicht", "vorrang"])
    # je Posten und Zeitraum: erste Veröffentlichung, bei gleichem Datum der Name mit Vorrang
    df = df.drop_duplicates(["gruppe", "start", "ende"], keep="first")
    return df.reset_index(drop=True)


def aktualisiere_bilanzen(uni, cache, max_alter_tage=7, pause=0.15):
    os.makedirs(os.path.join(cache, "bilanzen"), exist_ok=True)
    warnungen, ohne_cik, fehler = [], [], []
    for t, cik in zip(uni["ticker"], uni["cik"]):
        f = bilanz_datei(cache, t)
        if os.path.exists(f) and (time.time() - os.path.getmtime(f)) / 86400 < max_alter_tage:
            continue
        if pd.isna(cik):
            ohne_cik.append(t)
            continue
        try:
            df = bilanz_zeilen(json.loads(hole(SEC_FAKTEN.format(cik=int(cik)), versuche=2)))
            df.to_csv(f, index=False, compression="gzip")
        except Exception:  # noqa: BLE001
            fehler.append(t)
        time.sleep(pause)
    if ohne_cik:
        warnungen.append(f"Keine SEC-Nummer (meist ausländische Firmen ohne US-Bilanz): {len(ohne_cik)} Aktien – "
                         f"Bewertung und Wachstum bleiben dort leer.")
    if fehler:
        warnungen.append(f"Bilanzdaten der SEC nicht geladen für {len(fehler)} Aktien (z. B. {', '.join(fehler[:8])})"
                         + ("." if os.environ.get("LERNEN_SEC_KONTAKT") else
                            " – das Secret LERNEN_SEC_KONTAKT (Name und E-Mail für die SEC) fehlt."))
    return warnungen


def lies_bilanz(cache, t):
    f = bilanz_datei(cache, t)
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, parse_dates=["start", "ende", "eingereicht"])
    return df if len(df) else None


# Branchen des Bots (deutsch) -> GICS
GICS = {"Technologie": "Information Technology", "Kommunikation": "Communication Services",
        "Konsum": "Consumer Discretionary", "Finanzen": "Financials", "Gesundheit": "Health Care", "Energie": "Energy",
        "Basiskonsum": "Consumer Staples", "Industrie": "Industrials"}


def watchlist(text=None):
    """Watchlist des Bots {Ticker: GICS-Branche}: aus der Variable TICKER (wie im Ablauf swing-bot.yml), sonst die
    Standardliste in swing_scanner.py."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import swing_scanner as sw
    text = text if text is not None else os.environ.get("TICKER", "")
    tickers = sw.ticker_aus_text(text) if text.strip() else list(sw.TICKER_LISTE)
    return {t: GICS.get(sw.BRANCHE.get(t), "Unbekannt") for t in tickers}


def main():
    p = argparse.ArgumentParser(description="Lernmodell des Swing-Bots: Daten in den Zwischenspeicher holen")
    p.add_argument("--cache", default="lern_cache")
    p.add_argument("--nur", default="kurse,termine,bilanzen")
    p.add_argument("--max", type=int, default=0, help="nur die ersten N Aktien (zum Ausprobieren)")
    p.add_argument("--alter", type=int, default=7, help="Termine und Bilanzen erst nach so vielen Tagen neu holen")
    p.add_argument("--watchlist", action="store_true", help="auch die Aktien der Watchlist des Bots")
    p.add_argument("--nur-ticker", default="", help="nur diese Aktien holen (z. B. zum Nachladen)")
    a = p.parse_args()
    teile = set(a.nur.split(","))
    uni, warnungen = lade_universum(a.cache, watchlist() if a.watchlist else None)
    zusatz = ZUSATZ
    if a.nur_ticker:
        uni = uni[uni["ticker"].isin([t.strip().upper() for t in a.nur_ticker.split(",")])]
        zusatz = []
    tickers = list(uni["ticker"])[: a.max or None]
    print(f"Aktienliste: {len(uni)} Aktien", flush=True)
    if "kurse" in teile:
        _, w = aktualisiere_kurse(tickers + zusatz, a.cache)
        warnungen += w
        print("Kurse fertig", flush=True)
    if "termine" in teile:
        warnungen += aktualisiere_termine(tickers, a.cache, a.alter)
        print("Termine fertig", flush=True)
    if "bilanzen" in teile:
        warnungen += aktualisiere_bilanzen(uni.head(a.max or len(uni)), a.cache, a.alter)
        print("Bilanzen fertig", flush=True)
    with open(os.path.join(a.cache, "warnungen.json"), "w", encoding="utf-8") as f:
        json.dump({"stand": pd.Timestamp.now(tz="Europe/Berlin").isoformat(timespec="minutes"),
                   "warnungen": warnungen}, f, ensure_ascii=False, indent=1)
    for w in warnungen:
        print("⚠️", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
