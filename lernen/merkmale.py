"""Lernmodell des Swing-Bots: Merkmale je Kauf-Signal und das spätere Ergebnis jedes Signals.

Kauf-Signale sind die acht Long-Strategien des jetzigen Bots (nur lesend aus swing_scanner.py benutzt). Zu jedem
Signal sammelt das Lernmodell Merkmale, die am Signaltag zum Schlusskurs schon bekannt waren:
- Chart: RSI, Abstand zu den Durchschnittslinien, Ausbruch, Volumen, wie weit die Aktie schon gelaufen ist, Lücken.
- Momentum: Anstieg über 3, 6 und 12 Monate, Stärke gegenüber dem S&P 500.
- Bewertung (Value), Wachstum (Growth), Qualität: aus den SEC-Bilanzen, jeweils erst ab dem Tag NACH der
  Veröffentlichung. Fehlt eine Zahl, bleibt das Feld leer – das Lernmodell kommt damit zurecht.
- Quartalszahlen: Gewinnüberraschung der letzten Berichte, Tage seit und bis zu den Zahlen.
- Markt und Branche: S&P 500 über der 200-Tage-Linie, VIX, Anteil der Aktien über ihrer 50-Tage-Linie, Stärke der
  eigenen Branche.
Das Ergebnis eines Signals ist der gedachte Trade nach den Regeln des Bots (Kauf zur nächsten Eröffnung bis zum
Limit, Stop, Ziel, vor Quartalszahlen raus, Zeitstopp) in R (1 R = geplanter Verlust bis zum Stop), mit Kosten.
Es steht erst am Ausstiegstag fest – das Lernmodell darf es erst danach benutzen.
"""
import os
import sys

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))
import swing_scanner as sw  # noqa: E402  (nur lesend: Indikatoren, Signale, Ein- und Ausstiegsregeln)

sys.path.insert(0, HIER)
import daten as D  # noqa: E402
import fehler as F  # noqa: E402

GEBUEHR_IN_R = 2 * 1.0 / (10_000 * 1.0 / 100)  # 1 € je Order bei 10.000 € und 1 % Risiko
LANG = [k for k, s in sw.STRATEGIEN.items() if s["richtung"] > 0]

# Bilanz: Zeiträume in Tagen
JAHR, QUARTAL = (330, 380), (80, 100)


# ----------------------------------------------------------------------------
# Vorbereitung je Aktie (wie bereite_vor im Bot, aber ohne Marktfilter – die Marktlage ist ein Merkmal)
# ----------------------------------------------------------------------------
def vorbereiten(ticker, df, fx, termine):
    df = sw.calculate_indicators(df.copy())
    signale, _, _ = sw.strategie_signale(df, False)
    n = len(df)
    d = {"ticker": ticker, "df": df, "idx": df.index, "n": n, "n_fertig": n,
         "O": df["Open"].to_numpy(float), "H": df["High"].to_numpy(float), "L": df["Low"].to_numpy(float),
         "C": df["Close"].to_numpy(float), "ATR": df["ATR"].to_numpy(float),
         "FX": sw.kurs_umrechner(fx, df.index).to_numpy(float), "signale": signale,
         "pos": {tag: i for i, tag in enumerate(df.index)}, "termine": None}
    d["morgen"] = d["gesperrt"] = d["gerade"] = np.zeros(n, bool)
    if termine is not None and len(termine):
        t = sw.zahlen_termine(termine)
        d["termine"] = t
        d["morgen"], d["gesperrt"], d["gerade"], _, _ = sw.zahlen_regeln(t, df.index, sw.handelstag(ticker))
    return d


def ergebnis(d, i, stop, ziel, limit, kurs):
    """Gedachter Trade ab dem Signal am Tag i. Gibt dict mit R, Grund, Ausstiegstag … oder einen Status zurück."""
    n, j = d["n"], i + 1
    if j >= n:
        return {"status": "neu"}  # Signal von heute: Kauf erst zur nächsten Eröffnung
    if not sw.einstieg_moeglich(d, j, 1, stop, limit):
        return {"status": "kein_einstieg"}
    einstieg = sw.mit_spread(d["O"][j], 1, True)
    pos = {"start": j, "stop": stop, "ziel": ziel}
    k = j
    while k < n:
        preis, grund = sw.pruefe_ausstieg(d, k, 1, pos)
        if preis is not None:
            break
        k += 1
    if k >= n:
        return {"status": "laeuft", "einstieg_i": j, "einstieg": einstieg}
    roh = (sw.mit_spread(preis, 1, False) - einstieg) / (kurs - stop)
    return {"status": "fertig", "einstieg_i": j, "einstieg": einstieg, "ausstieg_i": k, "ausstieg": preis,
            "grund": grund, "R": float(np.clip(roh, -sw.R_GRENZE, sw.R_GRENZE) - GEBUEHR_IN_R)}


# ----------------------------------------------------------------------------
# Chart- und Momentum-Merkmale (Tagesreihen je Aktie)
# ----------------------------------------------------------------------------
def chart_reihen(d):
    df = d["df"]
    c, o, l, atr = df["Close"], df["Open"], df["Low"], df["ATR"]
    atr_v = atr.shift()
    m = pd.DataFrame(index=df.index)
    m["rsi14"] = df["RSI"]
    m["rsi2"] = df["RSI_2"]
    m["atr_prozent"] = atr / c * 100
    m["abst_sma50"] = (c - df["SMA_50"]) / atr
    m["abst_sma200"] = (c - df["SMA_200"]) / atr
    m["abst_ema20"] = (c - df["EMA_20"]) / atr
    m["abst_hoch20"] = (c - df["Hoch_20"]) / atr
    band = df["Upper_Band"] - df["Lower_Band"]
    m["bollinger_lage"] = (c - df["Lower_Band"]) / band.where(band > 0)
    m["bandbreite"] = df["BB_Breite"]
    m["volumen_faktor"] = df["Volume"] / df["Volumen_20"].where(df["Volumen_20"] > 0)
    m["macd_atr"] = (df["MACD"] - df["MACD_Signal"]) / atr
    m["ret5"] = c / c.shift(5) - 1
    m["ret20"] = c / c.shift(20) - 1
    m["gelaufen10"] = (c - l.rolling(10).min()) / atr  # wie weit schon vom 10-Tage-Tief weg (Signal zu spät?)
    m["luecken60"] = ((o - c.shift()).abs() / atr_v).rolling(60).mean()  # wie oft große Kurslücken
    m["schocks60"] = ((c - c.shift()) <= -3 * atr_v).astype(float).rolling(60).sum()  # Absturz-Tage
    m["mom63"] = c / c.shift(63) - 1
    m["mom126"] = c / c.shift(126) - 1
    m["mom252"] = c / c.shift(252) - 1
    m["mom12_1"] = c.shift(21) / c.shift(252) - 1
    m["abst_hoch52"] = c / c.rolling(252).max() - 1
    m["ueber_sma50"] = (c > df["SMA_50"]).astype(float).where(df["SMA_50"].notna())
    return m


def termin_reihen(d, termine):
    """Quartalszahlen: Tage seit und bis zu den Zahlen (Handelstage), Gewinnüberraschung der letzten Berichte."""
    idx = d["idx"]
    m = pd.DataFrame(index=idx, columns=["tage_seit_zahlen", "tage_bis_zahlen", "ueberraschung", "ueberraschung4",
                                         "treffer4"], dtype=float)
    if termine is None or not len(termine):
        return m
    t = termine[pd.DatetimeIndex(termine.index).notna()].copy()
    t.index = pd.DatetimeIndex(t.index)
    if t.index.tz is None:
        t.index = t.index.tz_localize("America/New_York")
    t["reak"] = [sw.reaktionstag(x) for x in t.index.tz_convert("America/New_York")]
    t = t.sort_values("reak")
    reak = pd.DatetimeIndex(t["reak"]).values.astype("datetime64[D]")
    tage = idx.values.astype("datetime64[D]")
    # seit: letzter Reaktionstag <= heute; bis: nächster danach (Termine stehen meist Wochen vorher fest),
    # jeweils in Handelstagen (Mo–Fr)
    k = np.searchsorted(reak, tage, side="right") - 1
    seit = np.busday_count(reak[np.clip(k, 0, None)], tage)
    m["tage_seit_zahlen"] = np.where(k >= 0, seit, np.nan)
    k2 = k + 1
    bis = np.busday_count(tage, reak[np.clip(k2, None, len(reak) - 1)])
    m["tage_bis_zahlen"] = np.where(k2 < len(reak), np.minimum(bis, 40), np.nan)
    if "Surprise(%)" in t:
        gemeldet = t[t["Surprise(%)"].notna()]
        if len(gemeldet):
            s = gemeldet["Surprise(%)"].clip(-100, 100).to_numpy(float)
            pos = idx.searchsorted(pd.DatetimeIndex(gemeldet["reak"]))
            ser = pd.Series(np.nan, index=range(len(idx)))
            s4 = pd.Series(s).rolling(4, min_periods=1).mean().to_numpy()
            t4 = pd.Series((s > 0).astype(float)).rolling(4, min_periods=1).sum().to_numpy()
            for spalte, werte in (("ueberraschung", s), ("ueberraschung4", s4), ("treffer4", t4)):
                ser = pd.Series(np.nan, index=range(len(idx)))
                for p, w in zip(pos, werte):
                    if p < len(idx):
                        ser.iloc[p] = w  # bekannt ab dem Reaktionstag (zum Schluss)
                m[spalte] = ser.ffill().to_numpy()
    return m


# ----------------------------------------------------------------------------
# Bilanz-Merkmale zum Veröffentlichungsdatum (Value, Growth, Qualität)
# ----------------------------------------------------------------------------
def _dauer(z):
    return (z["ende"] - z["start"]).dt.days


def _ttm(rows, ende, bekannt_bis):
    """Wert der letzten 12 Monate bis 'ende' aus allem, was bis 'bekannt_bis' veröffentlicht war:
    Jahreswert, sonst Jahresanfang-bis-heute + Vorjahr − gleicher Zeitraum im Vorjahr, sonst 4 Quartale."""
    r = rows[rows["eingereicht"] <= bekannt_bis]
    if r.empty:
        return np.nan
    tol = pd.Timedelta(days=12)
    nahe = r[(r["ende"] - ende).abs() <= tol]
    jahr = nahe[nahe["dauer"].between(*JAHR)]
    if len(jahr):
        return float(jahr["wert"].iloc[-1])
    ytd = nahe[(nahe["dauer"] > QUARTAL[0]) & (nahe["dauer"] < JAHR[0])].sort_values("dauer")
    if len(ytd):
        y = ytd.iloc[-1]
        vj = r[((r["ende"] - (y["start"] - pd.Timedelta(days=1))).abs() <= tol) & r["dauer"].between(*JAHR)]
        vytd = r[((r["ende"] - (ende - pd.DateOffset(years=1))).abs() <= tol)
                 & ((r["dauer"] - y["dauer"]).abs() <= 12)]
        if len(vj) and len(vytd):
            return float(y["wert"] + vj["wert"].iloc[-1] - vytd["wert"].iloc[-1])
    if len(nahe[nahe["dauer"].between(*QUARTAL)]):
        summe = 0.0
        for q in range(4):
            e = ende - pd.DateOffset(months=3 * q)
            qq = r[((r["ende"] - e).abs() <= tol) & r["dauer"].between(*QUARTAL)]
            if qq.empty:
                return np.nan
            summe += float(qq["wert"].iloc[-1])
        return summe
    return np.nan


def _stand(rows, ende, bekannt_bis):
    r = rows[(rows["eingereicht"] <= bekannt_bis) & ((rows["ende"] - ende).abs() <= pd.Timedelta(days=12))]
    return float(r["wert"].iloc[-1]) if len(r) else np.nan


def bilanz_reihen(idx, bilanz, roh, split):
    """Je Kurstag die Bilanz-Merkmale, die am Vortag schon veröffentlicht waren. roh = Schlusskurs nur
    splitbereinigt, split = Split-Faktor je Tag (für Aktienzahlen auf heutiger Basis)."""
    spalten = ["gewinnrendite", "buchwertrendite", "fcf_rendite", "umsatz_wachstum", "gewinn_wachstum",
               "nettomarge", "bruttomarge", "operative_marge", "verschuldung", "eigenkapitalrendite",
               "gewinn_stabil", "verlust"]
    m = pd.DataFrame(np.nan, index=idx, columns=spalten)
    if bilanz is None or roh is None:
        return m
    b = bilanz.copy()
    b["dauer"] = _dauer(b)
    gruppen = {g: z.sort_values("eingereicht") for g, z in b.groupby("gruppe")}
    leer = b.iloc[:0]
    G = lambda g: gruppen.get(g, leer)  # noqa: E731
    # Berichte: je Einreichungstag das Periodenende (größtes Ende unter den Umsatz-/Gewinnzahlen)
    berichte = b[b["gruppe"].isin(["umsatz", "gewinn", "vermoegen"])].groupby("eingereicht")["ende"].max()
    berichte = berichte[berichte.index.notna()].sort_index()
    if berichte.empty:
        return m
    # Splits nach einem Tag: Aktienzahlen von damals auf heutige Basis bringen
    splits = split[split > 0] if split is not None else pd.Series(dtype=float)
    schnappschuesse, gewinn_hist = [], []
    for eingereicht, ende in berichte.items():
        um, ge = _ttm(G("umsatz"), ende, eingereicht), _ttm(G("gewinn"), ende, eingereicht)
        um_v = _ttm(G("umsatz"), ende - pd.DateOffset(years=1), eingereicht)
        ge_v = _ttm(G("gewinn"), ende - pd.DateOffset(years=1), eingereicht)
        cf, inv = _ttm(G("cashflow"), ende, eingereicht), _ttm(G("investitionen"), ende, eingereicht)
        br, op = _ttm(G("brutto"), ende, eingereicht), _ttm(G("operativ"), ende, eingereicht)
        ek, sch, ver = (_stand(G(g), ende, eingereicht) for g in ("eigenkapital", "schulden", "vermoegen"))
        akt = G("aktien")
        akt = akt[(akt["eingereicht"] <= eingereicht) & ((akt["ende"] - ende).abs() <= pd.Timedelta(days=12))]
        aktien = float(akt.sort_values("dauer")["wert"].iloc[0]) if len(akt) else np.nan
        if np.isfinite(aktien) and len(splits):
            aktien *= float(splits[splits.index > ende].prod())
        gewinn_hist.append(ge)
        letzte = [x for x in gewinn_hist[-8:] if np.isfinite(x)]
        schnappschuesse.append({
            "ab": eingereicht + pd.Timedelta(days=1), "aktien": aktien, "gewinn": ge, "umsatz": um, "eigenkapital": ek,
            "fcf": cf - inv if np.isfinite(cf) and np.isfinite(inv) else (cf if np.isfinite(cf) else np.nan),
            "umsatz_wachstum": um / um_v - 1 if um_v and np.isfinite(um_v) and um_v > 0 else np.nan,
            "gewinn_wachstum": np.clip((ge - ge_v) / abs(ge_v), -3, 3) if ge_v and np.isfinite(ge_v) else np.nan,
            "nettomarge": ge / um if um and np.isfinite(um) and um > 0 else np.nan,
            "bruttomarge": br / um if um and np.isfinite(um) and um > 0 else np.nan,
            "operative_marge": op / um if um and np.isfinite(um) and um > 0 else np.nan,
            "verschuldung": sch / ver if ver and np.isfinite(ver) and ver > 0 else np.nan,
            "eigenkapitalrendite": np.clip(ge / ek, -2, 2) if ek and np.isfinite(ek) and ek > 0 else np.nan,
            "gewinn_stabil": float(np.mean([x > 0 for x in letzte])) if letzte else np.nan,
            "verlust": float(ge <= 0) if np.isfinite(ge) else np.nan})
    s = pd.DataFrame(schnappschuesse).drop_duplicates("ab", keep="last").set_index("ab").sort_index()
    s = s.reindex(idx.union(s.index)).ffill().reindex(idx)
    mcap = roh.reindex(idx) * s["aktien"]
    mcap = mcap.where(mcap > 0)
    m["gewinnrendite"] = (s["gewinn"] / mcap).clip(-1, 1)
    m["buchwertrendite"] = (s["eigenkapital"] / mcap).clip(-2, 5)
    m["fcf_rendite"] = (s["fcf"] / mcap).clip(-1, 1)
    for c in ["umsatz_wachstum", "gewinn_wachstum", "nettomarge", "bruttomarge", "operative_marge", "verschuldung",
              "eigenkapitalrendite", "gewinn_stabil", "verlust"]:
        m[c] = s[c]
    m["umsatz_wachstum"] = m["umsatz_wachstum"].clip(-1, 5)
    m["nettomarge"] = m["nettomarge"].clip(-2, 1)
    return m


# ----------------------------------------------------------------------------
# Markt, Breite und Branche
# ----------------------------------------------------------------------------
def markt_reihen(spy, qqq, vix):
    """Marktlage je Tag (S&P 500, Nasdaq-100, VIX)."""
    m = pd.DataFrame(index=spy.index)
    c = spy["Close"]
    m["spy_ueber200"] = (c > c.rolling(200).mean()).astype(float)
    m["spy_ret5"] = c / c.shift(5) - 1
    m["spy_ret20"] = c / c.shift(20) - 1
    m["spy_ret63"] = c / c.shift(63) - 1
    m["spy_tag"] = c / c.shift(1) - 1
    if qqq is not None:
        q = qqq["Close"].reindex(spy.index).ffill()
        m["qqq_ueber200"] = (q > q.rolling(200).mean()).astype(float)
    if vix is not None:
        v = vix["Close"].reindex(spy.index).ffill()
        m["vix"] = v
        m["vix_ret5"] = v / v.shift(5) - 1
    return m


def merkmale_aktie(t, df, fx, termine, bilanz):
    """Alles je Aktie: Kandidaten (Signaltage) mit Merkmalen und Ergebnis, dazu Tagesreihen für Breite/Branche."""
    d = vorbereiten(t, df, fx, termine)
    chart = chart_reihen(d)
    termin = termin_reihen(d, termine)
    roh = df["Roh"] if "Roh" in df else None
    split = df["Split"] if "Split" in df else None
    bilanz_m = bilanz_reihen(d["idx"], bilanz, roh, split)
    feuert = np.zeros(d["n"], bool)
    for ok, _, _ in d["signale"].values():
        feuert |= ok
    zeilen = []
    for i in np.nonzero(feuert)[0]:
        wahl, _ = sw.kandidaten(d, i)
        if wahl is None:
            continue
        ok, stop_a, ziel_a = d["signale"][wahl]
        stop, ziel, kurs = stop_a[i], ziel_a[i], d["C"][i]
        limit = sw.limit_kurs(1, kurs, d["ATR"][i], stop, ziel)
        z = {"ticker": t, "i": int(i), "tag": d["idx"][i], "strategie": wahl, "kurs": kurs, "stop": stop, "ziel": ziel,
             "limit": limit, "crv": (ziel - kurs) / (kurs - stop), "anzahl_signale": 0}
        for k in LANG:
            an = bool(d["signale"][k][0][i]) if k in d["signale"] else False
            z["sig_" + k] = float(an)
            z["anzahl_signale"] += an
        z.update(ergebnis(d, i, stop, ziel, limit, kurs))
        for schluessel in ("einstieg", "ausstieg"):
            if schluessel + "_i" in z:
                z[schluessel + "_tag"] = d["idx"][z[schluessel + "_i"]]
        zeilen.append(z)
    kand = pd.DataFrame(zeilen)
    if len(kand):
        ii = kand["i"].to_numpy()
        for teil in (chart, termin, bilanz_m):
            for c in teil.columns:
                if c != "ueber_sma50":
                    kand[c] = teil[c].to_numpy()[ii]
    reihen = pd.DataFrame({"ueber_sma50": chart["ueber_sma50"], "ret20": chart["ret20"]})
    return d, kand, reihen


def markt_und_branche(kand, reihen_je_aktie, sektor_von, markt):
    """Ergänzt je Kandidat: Marktlage, Breite (Anteil der Aktien über der 50-Tage-Linie), Stärke der Branche."""
    ueber = pd.DataFrame({t: r["ueber_sma50"] for t, r in reihen_je_aktie.items()})
    ret20 = pd.DataFrame({t: r["ret20"] for t, r in reihen_je_aktie.items()})
    breite = ueber.mean(axis=1)
    markt_ret20 = ret20.mean(axis=1)
    sektoren = pd.Series(sektor_von)
    branche_ret, branche_breite = {}, {}
    for s in sorted(set(sektoren.dropna())):
        mitglieder = [t for t in sektoren[sektoren == s].index if t in ret20]
        if mitglieder:
            branche_ret[s] = ret20[mitglieder].mean(axis=1) - markt_ret20
            branche_breite[s] = ueber[mitglieder].mean(axis=1)
    kand = kand.copy()
    tage = pd.DatetimeIndex(kand["tag"])
    kand["breite50"] = breite.reindex(tage).to_numpy()
    for c in markt.columns:
        kand[c] = markt[c].reindex(tage).to_numpy()
    kand["sektor"] = kand["ticker"].map(sektor_von).fillna("Unbekannt")
    kand["branche_ret20"] = np.nan
    kand["branche_breite"] = np.nan
    for s, ser in branche_ret.items():
        maske = (kand["sektor"] == s).to_numpy()
        kand.loc[maske, "branche_ret20"] = ser.reindex(tage[maske]).to_numpy()
        kand.loc[maske, "branche_breite"] = branche_breite[s].reindex(tage[maske]).to_numpy()
    kand["rs63"] = (1 + kand["mom63"]) / (1 + kand["spy_ret63"]) - 1
    return kand


# ----------------------------------------------------------------------------
# Alle Aktien (parallel): Kandidaten mit Merkmalen, Ergebnis und Fehler-Gründen
# ----------------------------------------------------------------------------
# Branchen-Fonds je GICS-Branche (für „Branche schwach“ in der Fehler-Analyse)
BRANCHEN_FONDS = {"Information Technology": "XLK", "Financials": "XLF", "Health Care": "XLV", "Energy": "XLE",
                  "Consumer Discretionary": "XLY", "Consumer Staples": "XLP", "Industrials": "XLI",
                  "Materials": "XLB", "Utilities": "XLU", "Real Estate": "XLRE", "Communication Services": "XLC"}
_G = {}  # Daten für die Arbeitsprozesse (per fork geteilt)


def markt(cache):
    """S&P 500, Nasdaq-100 und Marktlage je Tag aus dem Zwischenspeicher."""
    spy, qqq, vix = (D.lies_kurse(cache, t) for t in ("SPY", "QQQ", "^VIX"))
    return spy, qqq, markt_reihen(spy, qqq, vix)


def branchen_index(cache):
    aus = {}
    for s, t in BRANCHEN_FONDS.items():
        df = D.lies_kurse(cache, t)
        if df is not None and len(df):
            aus[s] = df["Close"]
    return aus


def fehler_der_kandidaten(d, kand, spy_c, branche, ab=None):
    """Fehler-Gründe für jeden gedachten Verlust-Trade (ab dem Signaltag 'ab')."""
    aus = pd.Series("", index=kand.index, dtype=object)
    for n, z in kand.iterrows():
        if z["status"] != "fertig" or not z["R"] < 0 or (ab is not None and z["tag"] < ab):
            continue
        tr = {"einstieg_i": int(z["einstieg_i"]), "ausstieg_i": int(z["ausstieg_i"]), "signal_i": int(z["i"]),
              "einstieg": z["einstieg"], "grund": z["grund"], "R": z["R"]}
        aus[n] = "|".join(F.gruende(tr, d, spy_c, branche, z["gelaufen10"]))
    return aus


def _eine_aktie(t):
    c = _G["cache"]
    df = D.lies_kurse(c, t)
    if df is None or len(df) < 300:
        return t, None, None
    df = df[df.index <= _G["ende"]]
    try:
        d, kand, reihen = merkmale_aktie(t, df, _G["fx"], D.lies_termine(c, t), D.lies_bilanz(c, t))
        if len(kand):
            branche = _G["branche"].get(_G["sektor_von"].get(t))
            kand["fehler"] = fehler_der_kandidaten(d, kand, _G["spy_c"], branche, _G["fehler_ab"])
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ {t}: {e}", flush=True)
        return t, None, None
    return t, kand, reihen


def alle_kandidaten(cache, tickers, ende, sektor_von, markt_df, fehler_ab=None, prozesse=4):
    """Kandidaten aller Aktien mit Merkmalen (auch Markt und Branche), Ergebnis und Fehler-Gründen.
    Gibt (kand, reihen je Aktie) zurück."""
    spy = D.lies_kurse(cache, "SPY")
    _G.update(cache=cache, fx=D.lies_kurse(cache, "EURUSD=X")["Close"], ende=pd.Timestamp(ende),
              sektor_von=sektor_von, spy_c=spy["Close"], branche=branchen_index(cache),
              fehler_ab=pd.Timestamp(fehler_ab) if fehler_ab is not None else None)
    kand, reihen = [], {}
    with ProcessPoolExecutor(prozesse) as ex:
        for t, k, r in ex.map(_eine_aktie, tickers, chunksize=4):
            if k is not None and len(k):
                kand.append(k)
                reihen[t] = r
    kand = markt_und_branche(pd.concat(kand, ignore_index=True), reihen, sektor_von, markt_df)
    for c in ("tag", "einstieg_tag", "ausstieg_tag"):
        kand[c] = pd.to_datetime(kand[c])
    return kand, reihen


# Merkmale für das Lernmodell (Reihenfolge = Spalten der Eingabe)
MERKMALE = (["crv", "anzahl_signale"] + ["sig_" + k for k in LANG]
            + ["rsi14", "rsi2", "atr_prozent", "abst_sma50", "abst_sma200", "abst_ema20", "abst_hoch20",
               "bollinger_lage", "bandbreite", "volumen_faktor", "macd_atr", "ret5", "ret20", "gelaufen10",
               "luecken60", "schocks60"]
            + ["mom63", "mom126", "mom252", "mom12_1", "abst_hoch52", "rs63"]
            + ["gewinnrendite", "buchwertrendite", "fcf_rendite", "umsatz_wachstum", "gewinn_wachstum",
               "nettomarge", "bruttomarge", "operative_marge", "verschuldung", "eigenkapitalrendite",
               "gewinn_stabil", "verlust"]
            + ["tage_seit_zahlen", "tage_bis_zahlen", "ueberraschung", "ueberraschung4", "treffer4"]
            + ["spy_ueber200", "qqq_ueber200", "spy_ret5", "spy_ret20", "spy_ret63", "spy_tag", "vix", "vix_ret5",
               "breite50", "branche_ret20", "branche_breite", "sektor_code"])
BILANZ_MERKMALE = ["gewinnrendite", "buchwertrendite", "fcf_rendite", "umsatz_wachstum", "gewinn_wachstum",
                   "nettomarge", "bruttomarge", "operative_marge", "verschuldung", "eigenkapitalrendite",
                   "gewinn_stabil", "verlust"]

# Einfache deutsche Namen für den Bericht
NAMEN = {
    "crv": "Chance/Risiko", "anzahl_signale": "Zahl der Strategien mit Signal", "rsi14": "RSI (14 Tage)",
    "rsi2": "RSI (2 Tage)", "atr_prozent": "Schwankung (ATR in %)", "abst_sma50": "Abstand zur 50-Tage-Linie",
    "abst_sma200": "Abstand zur 200-Tage-Linie", "abst_ema20": "Abstand zur 20-Tage-Linie",
    "abst_hoch20": "Abstand zum 20-Tage-Hoch", "bollinger_lage": "Lage im Bollinger-Band", "bandbreite": "Bandbreite",
    "volumen_faktor": "Volumen gegenüber normal", "macd_atr": "MACD-Schwung", "ret5": "Anstieg 1 Woche",
    "ret20": "Anstieg 1 Monat", "gelaufen10": "schon gelaufen (vom 10-Tage-Tief)", "luecken60": "Kurslücken zuletzt",
    "schocks60": "Absturz-Tage zuletzt", "mom63": "Momentum 3 Monate", "mom126": "Momentum 6 Monate",
    "mom252": "Momentum 12 Monate", "mom12_1": "Momentum 12 Monate ohne letzten Monat",
    "abst_hoch52": "Abstand zum 52-Wochen-Hoch", "rs63": "Stärke gegenüber dem S&P 500 (3 Monate)",
    "gewinnrendite": "Gewinnrendite (1/KGV)", "buchwertrendite": "Buchwert/Börsenwert (1/KBV)",
    "fcf_rendite": "Free-Cashflow-Rendite", "umsatz_wachstum": "Umsatzwachstum", "gewinn_wachstum": "Gewinnwachstum",
    "nettomarge": "Gewinnmarge", "bruttomarge": "Bruttomarge", "operative_marge": "operative Marge",
    "verschuldung": "Verschuldung", "eigenkapitalrendite": "Eigenkapitalrendite", "gewinn_stabil": "stabile Gewinne",
    "verlust": "Firma macht Verlust", "tage_seit_zahlen": "Tage seit den Quartalszahlen",
    "tage_bis_zahlen": "Tage bis zu den Quartalszahlen", "ueberraschung": "letzte Gewinnüberraschung",
    "ueberraschung4": "Gewinnüberraschung (letzte 4)", "treffer4": "Erwartung übertroffen (letzte 4)",
    "spy_ueber200": "S&P 500 über 200-Tage-Linie", "qqq_ueber200": "Nasdaq-100 über 200-Tage-Linie",
    "spy_ret5": "Markt 1 Woche", "spy_ret20": "Markt 1 Monat", "spy_ret63": "Markt 3 Monate", "spy_tag": "Markt heute",
    "vix": "Angst-Index VIX", "vix_ret5": "VIX-Anstieg 1 Woche", "breite50": "Anteil Aktien über 50-Tage-Linie",
    "branche_ret20": "Stärke der Branche (1 Monat)", "branche_breite": "Branche über 50-Tage-Linie",
    "sektor_code": "Branche",
}
for _k in LANG:
    NAMEN["sig_" + _k] = "Signal " + sw.STRATEGIEN[_k]["name"]
