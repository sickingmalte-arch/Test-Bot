"""Optionen auf dem Prüfstand (Wunsch des Nutzers vom 18.11.2026: „Vielleicht wäre der Handel mit Optionen wirklich noch
was für dich“ – gewählt: Put-Verkauf mit freiem Geld, gedeckter Call am Ziel, Call statt Aktie, Put statt Short).

Alte Optionspreise für einzelne Aktien gibt es nicht kostenlos. Deshalb rechnet der Test dieselben Trades des Bots mit
berechneten Optionspreisen nach (Black-Scholes):
- Schwankung der Option (implizite Volatilität) = Faktor × Schwankung der letzten 20 Tage. Zwei Annahmen: „günstig“
  (Faktor 1,0) und „teuer“ (Faktor 1,25 – Optionen auf Einzelaktien kosten im Schnitt etwas mehr, als die Kurse danach
  wirklich schwanken). Eine Idee besteht nur, wenn sie mit BEIDEN Annahmen besteht.
- Zins 2 % im Jahr, Dividenden nicht gerechnet.
- Spread: Kauf zum Modellpreis plus 2 % (mindestens 2 Cent je Aktie), Verkauf zum Modellpreis minus 2 %; Gebühr je Order
  wie bei Aktien. Bruchteile von Kontrakten sind erlaubt (wie Bruchstücke bei Aktien).
Die Trades selbst (Signal, Einstiegstag, Stop, Ziel, Zeitstopp, Ausstieg vor Quartalszahlen) bleiben die des Bots. Jeder
Depot-Lauf wird Tag für Tag nachbewertet, so stimmen Rendite und größter Rückgang. Vereinfachung: Die Größe späterer
Trades richtet sich weiter nach dem Depotwert des Bots.

Geprüft auf denselben 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum wie die Short-Tests vom 18.11.
(forschung/short_fair_hilfe.py)."""
import datetime as dt
import importlib
import os
import time

import numpy as np
import pandas as pd
from scipy.special import ndtr

import short_fair_hilfe as F

ZINS = 0.02
SPREAD_ANTEIL = 0.02
SPREAD_MIN = 0.02
FAKTOREN = {"günstig": 1.0, "teuer": 1.25}
MIN_TRADES = 30


# ----------------------------------------------------------------------------
# Preise
# ----------------------------------------------------------------------------
def bs(call, S, K, T, sigma, r=ZINS):
    """Black-Scholes-Preis je Aktie, T in Jahren; ohne Restlaufzeit der innere Wert."""
    S, K, T, sigma = (np.asarray(x, dtype=float) for x in (S, K, T, sigma))
    innen = np.maximum(S - K, 0.0) if call else np.maximum(K - S, 0.0)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        st = sigma * np.sqrt(np.maximum(T, 0.0))
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / st
        d2 = d1 - st
        if call:
            wert = S * ndtr(d1) - K * np.exp(-r * T) * ndtr(d2)
        else:
            wert = K * np.exp(-r * T) * ndtr(-d2) - S * ndtr(-d1)
    return np.where((T > 0) & (st > 0) & np.isfinite(wert), np.maximum(wert, 0.0), innen)


def briefkurs(preis):
    """Kaufkurs einer Option: Modellpreis plus Spread."""
    return preis + np.maximum(SPREAD_ANTEIL * preis, SPREAD_MIN)


def geldkurs(preis):
    """Verkaufskurs einer Option: Modellpreis minus Spread (nie unter 0)."""
    return np.maximum(preis - np.maximum(SPREAD_ANTEIL * preis, SPREAD_MIN), 0.0)


def schwankung(d):
    """Schwankung der letzten 20 Tage pro Jahr (Wert am Tag i nutzt nur Schlusskurse bis i)."""
    c = np.asarray(d["C"], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.diff(np.log(np.where(c > 0, c, np.nan)), prepend=np.nan)
    s = pd.Series(r).rolling(20, min_periods=15).std().to_numpy() * np.sqrt(252)
    return np.clip(np.nan_to_num(s, nan=0.3), 0.10, 2.0)


def _jahre(bis, tage):
    return np.maximum((pd.Timestamp(bis) - pd.DatetimeIndex(tage)).days.to_numpy(), 0) / 365.0


# ----------------------------------------------------------------------------
# Bot laufen lassen und jeden Depot-Lauf nachrechnen
# ----------------------------------------------------------------------------
def auswerten(P, a, sektor_von, zr, anpassen, auswerter):
    """Bot (mit Variante) auf allen Listen. Je Liste: auswerter(deps, daten) -> {Name: Wert}, gemittelt über die Läufe."""
    R = P.R
    gemerkt = F._mit_variante(P, anpassen)
    daten = {}
    original = R.sw.bereite_vor

    def merken(ticker, *x, **k):
        d = original(ticker, *x, **k)
        daten[ticker] = d
        return d
    R.sw.bereite_vor = merken
    aus = {}
    try:
        for von, z in zr.items():
            aus[von] = []
            for liste in z["listen"]:
                gemerkt.clear()
                daten.clear()
                R.jetziger_bot(a.cache, liste, sektor_von, von, z["bis"], a.laeufe)
                aus[von].append(auswerter(list(gemerkt), dict(daten)))
    finally:
        importlib.reload(R.sw)
    return aus


def mittel(erg_je_lauf):
    """[{Name: Zahl oder {Kennzahl: Zahl}}] je Lauf -> Mittel je Name."""
    aus = {}
    for name in erg_je_lauf[0]:
        werte = [e[name] for e in erg_je_lauf]
        if isinstance(werte[0], dict):
            aus[name] = {k: float(np.nanmean([w[k] for w in werte])) for k in werte[0]}
        else:
            aus[name] = float(np.nanmean(werte))
    return aus


def positionen(dep):
    """Alle Positionen eines Depot-Laufs: abgeschlossene Trades und die am Ende noch offenen."""
    return [(p, True) for p in dep["trades"]] + [(p, False) for p in dep.get("offen", [])]


def _pfad(n, i0, i_ende, gehalten, danach):
    """Ergebnis-Pfad über die Kurstage einer Aktie: 0 vor dem Einstieg, gehalten[i0:i_ende], danach fest."""
    aus = np.zeros(n)
    ende = n if i_ende is None else i_ende
    aus[i0:ende] = gehalten[:ende - i0]
    if i_ende is not None:
        aus[i_ende:] = danach
    return aus


def bot_pfad(sw, d, p, geschlossen):
    """Ergebnis der Aktien-Position des Bots in € je Schlusskurs (wie der Depotwert sie zählt)."""
    n, i0 = d["n_fertig"], p["start"]
    i1 = d["pos"][p["verkauf_tag"]] if geschlossen else None
    ende = n if i1 is None else i1
    werte = np.array([sw.positionswert(p, d["C"][j], d["FX"][j]) for j in range(i0, ende)]) - p["kosten"]
    return _pfad(n, i0, i1, werte, p["erloes"] - p["kosten"] if geschlossen else 0.0), i1


def ausstiegskurs(sw, d, p, i1):
    """Kurs, zu dem der Bot die Aktie am Tag i1 verlassen hat (vor Spread), mit seiner eigenen Ausstiegsregel."""
    preis, _ = sw.pruefe_ausstieg(d, i1, p["richtung"], p)
    return float(preis) if preis is not None else float(d["C"][i1])


def neue_kurve(dep, daten, pfade):
    """Depotwert des Bots plus die Unterschiede aller umgerechneten Positionen."""
    kurve = dep["verlauf"].astype(float).copy()
    for t, pfad in pfade:
        s = pd.Series(pfad, index=daten[t]["idx"][:len(pfad)])
        kurve = kurve + s.reindex(kurve.index, method="ffill").fillna(0.0).to_numpy()
    return kurve


def option_statt_aktie(sw, dep, daten, faktor, call, gebuehr, tage=60):
    """Jede Position der Richtung (call: Long, sonst Short) wird zu einer gekauften Option am Geld mit `tage`
    Restlaufzeit. Die Prämie ist so groß wie das geplante Risiko des Trades (1 % des Kontos) – mehr kann nicht verloren
    gehen. Ausstieg am selben Tag wie der Bot. Gibt (neue Kurve, Anzahl, Summe R der Optionen, Summe R der Aktien)."""
    pfade, anzahl, r_opt, r_aktie = [], 0, 0.0, 0.0
    for p, geschlossen in positionen(dep):
        if (p["richtung"] > 0) != call:
            continue
        t = p["ticker"]
        d = daten[t]
        vola = schwankung(d) * faktor
        alt, i1 = bot_pfad(sw, d, p, geschlossen)
        i0, n = p["start"], d["n_fertig"]
        tag0 = d["idx"][i0]
        verfall = tag0 + pd.Timedelta(days=tage)
        s0 = float(d["O_ersatz"][i0])
        kauf = float(briefkurs(bs(call, s0, s0, tage / 365.0, vola[max(i0 - 1, 0)])))
        if not (kauf > 0 and p["risiko_eur"] > 0):
            continue
        stueck = p["risiko_eur"] * d["FX"][i0] / kauf
        kosten = stueck * kauf / d["FX"][i0] + gebuehr
        ende = n if i1 is None else i1
        j = np.arange(i0, ende)
        mitte = bs(call, d["C"][j], s0, _jahre(verfall, d["idx"][j]), vola[j])
        gehalten = stueck * mitte / d["FX"][j] - kosten
        danach = 0.0
        if i1 is not None:
            s1 = ausstiegskurs(sw, d, p, i1)
            erloes = stueck * float(geldkurs(bs(call, s1, s0, _jahre(verfall, [d["idx"][i1]])[0],
                                                 vola[i1 - 1]))) / d["FX"][i1] - gebuehr
            danach = erloes - kosten
            r_opt += danach / p["risiko_eur"]
            r_aktie += (p["erloes"] - p["kosten"]) / p["risiko_eur"]
            anzahl += 1
        pfade.append((t, _pfad(n, i0, i1, gehalten, danach) - alt))
    return neue_kurve(dep, daten, pfade), anzahl, r_opt, r_aktie


def gedeckter_call(sw, dep, daten, faktor, gebuehr):
    """Zu jedem Long verkauft der Bot einen Call je Aktie mit Basispreis = Kursziel, fällig am Tag des Zeitstopps. Das
    Ziel ist damit kein Ausstieg mehr: Liegt der Kurs am Verfallstag über dem Ziel, wird die Aktie zum Ziel abgegeben
    (die Prämie bleibt), sonst verkauft der Bot sie zum Schlusskurs. Stop und Ausstieg vor Quartalszahlen gelten wie
    immer; dann kauft er den Call zurück. Gibt (neue Kurve, Anzahl, Summe der Extra-R gegenüber dem Bot)."""
    pfade, anzahl, r_extra = [], 0, 0.0
    for p, geschlossen in positionen(dep):
        if p["richtung"] < 0:
            continue
        t = p["ticker"]
        d = daten[t]
        vola = schwankung(d) * faktor
        alt, _ = bot_pfad(sw, d, p, geschlossen)
        i0, n = p["start"], d["n_fertig"]
        tag0 = d["idx"][i0]
        verfall = d["idx"][min(i0 + sw.ZEITSTOPP_TAGE - 1, n - 1)]  # Börsentage stehen vorher fest
        k, stueck = float(p["ziel"]), float(p["stueck"])
        s0 = float(d["O_ersatz"][i0])
        t0 = max((verfall - tag0).days, 1) / 365.0
        praemie = stueck * float(geldkurs(bs(True, s0, k, t0, vola[max(i0 - 1, 0)]))) / d["FX"][i0] - gebuehr
        pos = {"start": i0, "stop": p["stop"], "ziel": np.inf}
        i_ende, erloes = None, 0.0
        for i in range(i0, n):
            preis, grund = sw.pruefe_ausstieg(d, i, 1, pos)
            am_verfall = d["idx"][i] >= verfall
            if preis is not None and not (am_verfall and grund == "Zeitstopp"):
                # Stop oder Quartalszahlen: Aktie raus, Call zurückkaufen
                rueck = float(briefkurs(bs(True, preis, k, _jahre(verfall, [d["idx"][i]])[0], vola[max(i - 1, 0)])))
                erloes = stueck * (sw.mit_spread(preis, 1, False) - rueck) / d["FX"][i] - 2 * gebuehr
                i_ende = i
                break
            if am_verfall:
                c = float(d["C"][i])
                if c >= k:  # Abgabe zum Ziel, die Prämie bleibt
                    erloes = stueck * k / d["FX"][i] - gebuehr
                else:  # Call verfällt wertlos, Aktie zum Schlusskurs verkaufen
                    erloes = stueck * sw.mit_spread(c, 1, False) / d["FX"][i] - gebuehr
                i_ende = i + 1  # zum Schluss verkauft: ab dem nächsten Tag nur noch Geld
                break
        if i_ende is not None and i_ende >= n:
            i_ende = None  # Datenende: als offen bewerten
        ende = n if i_ende is None else i_ende
        j = np.arange(i0, ende)
        mitte = bs(True, d["C"][j], k, _jahre(verfall, d["idx"][j]), vola[j])
        kosten = p["kosten"] - praemie
        gehalten = stueck * (d["C"][j] - mitte) / d["FX"][j] - kosten
        pfade.append((t, _pfad(n, i0, i_ende, gehalten, erloes - kosten) - alt))
        if geschlossen and i_ende is not None:
            anzahl += 1
            r_extra += ((erloes - kosten) - (p["erloes"] - p["kosten"])) / p["risiko_eur"]
    return neue_kurve(dep, daten, pfade), anzahl, r_extra


def freies_geld(sw, dep, daten):
    """Geld, das der Bot an jedem Abend nicht in Aktien hat (in €, auf dem Kalender des Depotwerts)."""
    kurve = dep["verlauf"].astype(float)
    in_aktien = pd.Series(0.0, index=kurve.index)
    for p, geschlossen in positionen(dep):
        d = daten[p["ticker"]]
        n, i0 = d["n_fertig"], p["start"]
        i1 = d["pos"][p["verkauf_tag"]] if geschlossen else None
        ende = n if i1 is None else i1
        werte = np.zeros(n)
        werte[i0:ende] = [sw.positionswert(p, d["C"][j], d["FX"][j]) for j in range(i0, ende)]
        s = pd.Series(werte, index=d["idx"][:n])
        # an Tagen ohne Kurs zählt der letzte Wert, nach dem Ausstieg 0
        in_aktien = in_aktien + s.reindex(kurve.index, method="ffill").fillna(0.0).to_numpy()
    return (kurve - in_aktien).clip(lower=0.0)


def ueberlagern(kurve, frei, r):
    """Depotwert plus Ertrag, wenn das freie Geld vom Vorabend (und der Ertrag selbst) mit der Tagesrendite r arbeitet."""
    r = r.reindex(kurve.index).fillna(0.0).to_numpy()
    frei = frei.shift(1).fillna(0.0).to_numpy()
    g, gewinn = 0.0, np.zeros(len(kurve))
    for i in range(len(kurve)):
        g += (frei[i] + g) * r[i]
        gewinn[i] = g
    return kurve + gewinn


# ----------------------------------------------------------------------------
# Urteil und Bericht
# ----------------------------------------------------------------------------
def stufe(lang, werte, anzahl=None):
    """Vergleich je Zeitraum: Mitte der Unterschiede, Zahl besserer Listen, Mitte des Mehr-Rückgangs."""
    je = {}
    for von in lang:
        dr = [w["rendite"] - b["rendite"] for b, w in zip(lang[von], werte[von])]
        dd = [w["rueckgang"] - b["rueckgang"] for b, w in zip(lang[von], werte[von])]
        je[von] = {"plus": float(np.median(dr)), "besser": int(sum(x > 0 for x in dr)), "tiefer": float(np.median(dd)),
                   "trades": float(sum(anzahl[von])) if anzahl else float("nan")}
    return je


def besteht(je, mehrheit):
    return all(x["plus"] > 0 and x["besser"] >= mehrheit and x["tiefer"] <= 1 for x in je.values())


def mitte(werte, k="rendite"):
    return float(np.median([w[k] for w in werte]))


def zahl(x, st=1):
    return "–" if x is None or not np.isfinite(x) else f"{x:+.{st}f}".replace(".", ",")


def kopf_md(idee, text, zr, n_aktien, R):
    vs = list(zr)
    anzahl = len(zr[vs[0]]["listen"])
    return [f"# 🔬 {idee.NAME}", "", f"Getestet am {dt.date.today():%d.%m.%Y} · Quelle: {getattr(idee, 'QUELLE', '–')}",
            "", idee.BESCHREIBUNG, "", f"- **Vermutung:** {idee.VERMUTUNG}",
            f"- **Widerlegt, wenn:** {idee.WIDERLEGT_WENN}", f"- **Varianten:** {idee.VARIANTEN}", "",
            f"**Ergebnis: {text}**", "",
            f"Je Zeitraum {anzahl} Zufallslisten mit je {n_aktien} Aktien aus dem damaligen S&P 500 (zur Wahl standen "
            + ", ".join(f"{k}: {zr[v]['kandidaten']}" for k, v in zip(R.ZEITRAEUME, vs))
            + f" Aktien). Werte: Mitte (Median) der {anzahl} Listen, Rendite pro Jahr / größter Rückgang.", "",
            "| | " + " | ".join(R.ZEITRAEUME) + " |", "|---|" + "---:|" * len(vs)]


def kz_zelle(werte):
    return f"{mitte(werte):+.1f} % / −{mitte(werte, 'rueckgang'):.0f} %".replace(".", ",")


def fuss_md():
    return ["", "So gelesen: Optionspreise sind berechnet (Black-Scholes, Schwankung der letzten 20 Tage mal 1,0 bzw. "
            "1,25, Zins 2 %, Spread 2 %), nicht echt gehandelt – echte Preise können anders sein. „R“ ist das geplante "
            "Risiko eines Trades (1 % des Kontos). Die Trades sind die des Bots auf Zufallslisten aus dem damaligen "
            "S&P 500; Pleitefirmen fehlen darin. Simulation mit Spielgeld, keine Anlageberatung."]


def laufzeit_text(t0):
    return f"{time.time() - t0:.0f} s"


def gebuehr():
    return float(os.environ.get("GEBUEHR", "0"))


# ----------------------------------------------------------------------------
# Reihen für den Put-Verkauf mit freiem Geld (echte Börsendaten, sonst eigene Rechnung)
# ----------------------------------------------------------------------------
CBOE_PUT = "https://cdn.cboe.com/api/global/us_indices/daily_prices/PUT_History.csv"
KOSTEN_PUT_JAHR = 0.01  # Spreads und Gebühren beim monatlichen Rollen


def _ohne_zone(s):
    s = s.dropna().astype(float)
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    s.index = idx.normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()


def yahoo_reihe(ticker, spalte="Close", start="2007-01-01"):
    """Tagesreihe von Yahoo (None, wenn nicht zu laden)."""
    try:
        import yfinance as yf
        df = yf.download(ticker, start=start, auto_adjust=False, progress=False, threads=False)
        s = df[spalte]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        s = _ohne_zone(s)
    except Exception:  # noqa: BLE001 – keine Daten oder Netzfehler
        return None
    return s if len(s) > 250 else None


def cboe_reihe(url=CBOE_PUT):
    """Tagesreihe eines CBOE-Index als CSV (erste Spalte Datum, letzte Spalte Wert). Bewusst ohne die SEC-Kennung."""
    import io
    import urllib.request
    try:
        anfrage = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Forschung Swing-Bot)"})
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            df = pd.read_csv(io.StringIO(antwort.read().decode("utf-8", "replace")))
        s = pd.Series(pd.to_numeric(df.iloc[:, -1], errors="coerce").to_numpy(),
                      index=pd.to_datetime(df.iloc[:, 0], errors="coerce"))
        s = _ohne_zone(s[s.index.notna()])
    except Exception:  # noqa: BLE001
        return None
    return s if len(s) > 250 else None


def putwrite_modell(spy, vix, zins_tag):
    """Eigene Rechnung, falls die CBOE-Reihe fehlt: alle 21 Börsentage einen Put am Geld auf den S&P 500 (SPY)
    verkaufen, voll mit Geld gedeckt; Preis nach Black-Scholes mit 0,9 × VIX, Spread 2 %. Gibt den Wertverlauf."""
    s = spy.dropna()
    tage = s.index
    v = (vix.reindex(tage).ffill().bfill() / 100 * 0.9).to_numpy()
    z = zins_tag.reindex(tage).fillna(0.0).to_numpy()
    kurs = s.to_numpy()
    werte = np.full(len(s), np.nan)
    u, i = 1.0, 0
    werte[0] = u
    while i < len(s) - 1:
        ende = min(i + 21, len(s) - 1)
        k, verfall = kurs[i], tage[ende]
        menge = u / k
        geld = u + menge * float(geldkurs(bs(False, k, k, (verfall - tage[i]).days / 365.0, v[i])))
        for j in range(i + 1, ende + 1):
            geld *= 1 + z[j]
            werte[j] = geld - menge * float(bs(False, kurs[j], k, (verfall - tage[j]).days / 365.0, v[j]))
        u, i = werte[ende], ende
    return pd.Series(werte, index=tage)


def put_reihen(P, a):
    """Tagesrenditen: PutWrite (Quelle im Text), US-Geldmarkt, S&P 500 (SPY mit Dividenden)."""
    spy = _ohne_zone(P.D.lies_kurse(a.cache, "SPY")["Close"])
    vix = _ohne_zone(P.D.lies_kurse(a.cache, "^VIX")["Close"])
    zins = yahoo_reihe("^IRX")
    if zins is not None:
        zins_tag, zins_quelle = (zins / 100 / 252).reindex(spy.index).ffill().fillna(0.0), "13-Wochen-T-Bill (^IRX)"
    else:
        bil = yahoo_reihe("BIL", "Adj Close")
        if bil is not None:
            zins_tag, zins_quelle = bil.pct_change().reindex(spy.index).fillna(0.0), "T-Bill-Fonds BIL"
        else:
            zins_tag, zins_quelle = pd.Series(0.0, index=spy.index), "nicht geladen (0 %)"
    put, quelle = yahoo_reihe("^PUT"), "CBOE-PutWrite-Index (^PUT, Yahoo)"
    if put is None:
        put, quelle = cboe_reihe(), "CBOE-PutWrite-Index (Börse CBOE)"
    if put is None:
        put, quelle = putwrite_modell(spy, vix, zins_tag), "eigene Rechnung mit SPY und VIX (CBOE-Reihe nicht geladen)"
    return {"put": put.pct_change().fillna(0.0), "zins": zins_tag, "spy": spy.pct_change().fillna(0.0)}, \
        {"put": quelle, "zins": zins_quelle, "put_ab": str(put.index[0].date())}


# ----------------------------------------------------------------------------
# Gemeinsames für die Ideen mit zwei Preis-Annahmen
# ----------------------------------------------------------------------------
def je_liste(werte, name):
    return {v: [w[name] for w in werte[v]] for v in werte}


def stufen_annahmen(lang, werte):
    """Je Preis-Annahme der Vergleich mit dem Bot; besteht nur, wenn er mit BEIDEN Annahmen besteht."""
    stufen = {name: stufe(lang, je_liste(werte, name), je_liste(werte, "n")) for name in FAKTOREN}
    ok = all(besteht(je, F.MEHRHEIT) and all(x["trades"] >= MIN_TRADES for x in je.values())
             for je in stufen.values())
    return stufen, ok


def schlechter_plus(stufen):
    """Für die Übersicht: je Zeitraum der schlechtere der beiden Unterschiede (vorsichtig)."""
    vs = list(next(iter(stufen.values())))
    return {v: min(je[v]["plus"] for je in stufen.values()) for v in vs}


def gewichtet(werte, von, name):
    """Ø je Trade über alle Listen (gewichtet mit der Zahl der Trades)."""
    n = np.array([w["n"] for w in werte[von]], dtype=float)
    x = np.array([w[name] for w in werte[von]], dtype=float)
    gut = np.isfinite(x) & (n > 0)
    return float((n[gut] * x[gut]).sum() / n[gut].sum()) if gut.any() else float("nan")


def zeilen_annahmen(titel, werte, stufen, vs, anzahl):
    z = []
    for name, faktor in FAKTOREN.items():
        je = stufen[name]
        z += [f"| **{titel} – Preise {name} (×{str(faktor).replace('.', ',')})** | "
              + " | ".join(kz_zelle(je_liste(werte, name)[v]) for v in vs) + " |",
              "| … Unterschied zum Vergleich (Mitte, Punkte) · Listen besser | "
              + " | ".join(f"{zahl(je[v]['plus'])} · {je[v]['besser']} von {anzahl}" for v in vs) + " |"]
    return z
