"""Lernmodell des Swing-Bots: täglicher Lern-Lauf (Ablauf .github/workflows/lernen.yml – nach dem US-Börsenschluss
und noch einmal vor dem Morgen-Lauf des Bots).

Hier lernt der Bot aus seinen Fehlern – nicht nur, indem er schwache Strategien pausiert, sondern aus jedem einzelnen
Trade:
1. Daten auffrischen: alle Aktien aus S&P 500 und Nasdaq-100 und die Watchlist des Bots (Kurse, Quartalszahlen,
   SEC-Bilanzen) im Zwischenspeicher. Was fehlt oder alt ist, steht deutlich im Bericht.
2. Jedes Kauf-Signal jeder Aktie wird als gedachter Trade nach den Regeln des Bots durchgespielt; jeder Verlust
   bekommt Fehler-Gründe (Kurslücke, Markt, Branche, Quartalszahlen, zu spät, Stop zu eng, Nachricht …).
3. Lernmodell: einmal im Monat neu, nur mit Trades, deren Ergebnis vorher feststand (Walk-forward). Es gibt jedem
   neuen Signal eine Punktzahl.
4. Fehler-Analyse jedes abgeschlossenen Trades im Übungsdepot des Bots (papier/papier_depot.json, nur gelesen).
5. Ergebnis für den Bot: lernen/punkte.json (Punktzahl je Signal), lernen/lernstand.json (was gelernt wurde, Güte,
   häufigste Fehler, Fehler-Analyse der Trades) und die Seite lernen/LERNEN.md.

Die Kaufregeln des Bots ändern sich dadurch NICHT – er zeigt die Punktzahl nur an. Nach der Punktzahl kauft er erst,
wenn der Rückblick (RUECKBLICK.md) zeigt, dass es besser ist, und du Ja sagst.

Aufruf: python lernen/lernlauf.py [--cache lern_cache] [--ohne-download]
"""
import argparse
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import daten as D  # noqa: E402
import fehler as F  # noqa: E402
import merkmale as M  # noqa: E402
import modell as L  # noqa: E402

sw = M.sw
WURZEL = os.path.dirname(HIER)
ANTEIL = 0.3  # „würde kaufen“: Punktzahl unter den besten 30 % der 12 Monate davor
MONATE = 14  # Punktzahlen so vieler Monate zurück (für die Schwelle und die Auswertung)
FEHLER_MONATE = 15  # Fehler-Gründe aller gedachten Trades nur für die letzten Monate (spart Zeit)
NACHLAUF = 10  # Handelstage nach dem Verkauf, bis die Fehler-Analyse feststeht („Stop zu eng?“)
MINDESTENS = 0.9  # ein Tag zählt erst, wenn so viele Aktien seine Kurse haben
PUNKTE_TAGE = 5  # Punktzahlen der letzten Börsentage (falls der Bot einen Tag hinterher ist)


# ----------------------------------------------------------------------------
# Daten
# ----------------------------------------------------------------------------
def erwarteter_tag(jetzt=None):
    """Letzter US-Börsentag, dessen Kerze es geben sollte (nach 16:30 Uhr New York der heutige)."""
    ny = (jetzt or pd.Timestamp.now(tz="America/New_York")).tz_convert("America/New_York")
    tag = ny.normalize().tz_localize(None)
    if ny.weekday() >= 5 or ny.hour * 60 + ny.minute < 16 * 60 + 30:
        tag -= pd.offsets.BDay(1)
    while tag.weekday() >= 5:
        tag -= pd.offsets.BDay(1)
    return pd.Timestamp(tag)


def kurse_bis(cache, tickers):
    aus = {}
    for t in tickers:
        df = D.lies_kurse(cache, t)
        aus[t] = df.index[-1] if df is not None and len(df) else None
    return aus


def letzter_voller_tag(spy_index, bis):
    """Letzter Handelstag, für den (fast) alle Aktien Kurse haben."""
    werte = [b for b in bis.values() if b is not None]
    for tag in reversed(spy_index[-5:]):
        if werte and np.mean([b >= tag for b in werte]) >= MINDESTENS:
            return tag
    return spy_index[-1]


def daten_warnungen(cache, uni, bis, letzter, erwartet):
    w = []
    if letzter < erwartet:
        w.append(f"Die Kurse vom {erwartet:%d.%m.%Y} fehlen noch (Yahoo liefert manchmal erst später, oder es war ein "
                 f"US-Feiertag). Gerechnet wurde bis {letzter:%d.%m.%Y}; der nächste Lauf holt sie nach.")
    fehlen = [t for t, b in bis.items() if b is None]
    alt = [t for t, b in bis.items() if b is not None and b < letzter]
    if fehlen:
        w.append(f"Keine Kurse für {len(fehlen)} Aktien: {', '.join(sorted(fehlen)[:15])}"
                 + (" …" if len(fehlen) > 15 else "") + ".")
    if alt:
        w.append(f"Alte Kurse (nicht bis {letzter:%d.%m.%Y}) bei {len(alt)} Aktien: {', '.join(sorted(alt)[:15])}"
                 + (" …" if len(alt) > 15 else "") + " – sie werden heute nicht gehandelt.")
    ohne_bilanz = [t for t in uni["ticker"] if not os.path.exists(D.bilanz_datei(cache, t))]
    ohne_termine = [t for t in uni["ticker"] if not os.path.exists(D.termin_datei(cache, t))]
    if ohne_bilanz:
        w.append(f"Ohne SEC-Bilanzdaten: {len(ohne_bilanz)} Aktien (z. B. {', '.join(sorted(ohne_bilanz)[:8])}) – "
                 "Bewertung, Wachstum und Qualität bleiben dort leer.")
    if ohne_termine:
        w.append(f"Ohne Quartalszahlen-Termine: {len(ohne_termine)} Aktien (z. B. {', '.join(sorted(ohne_termine)[:8])})"
                 " – die Regel „vor Quartalszahlen raus“ fehlt dort.")
    return w


# ----------------------------------------------------------------------------
# Lernmodell: einmal im Monat neu, Punktzahlen und Schwelle
# ----------------------------------------------------------------------------
def modell_fuer(kand, monat, ordner):
    """Modell für einen Monat: trainiert mit allem, was vor Monatsbeginn feststand (aus dem Zwischenspeicher)."""
    datei = os.path.join(ordner, f"modell_{monat}.pkl")
    if os.path.exists(datei):
        try:
            with open(datei, "rb") as f:
                m = pickle.load(f)
            if hasattr(m, "lern_merkmale"):
                return m
        except Exception:  # noqa: BLE001 – z. B. andere scikit-learn-Version: dann neu lernen
            pass
    train = L.bekannt_vor(kand, monat.to_timestamp())
    if len(train) < L.MIN_TRAINING:
        return None
    m = L.trainiere(train)
    m.lern_training = int(len(train))
    m.lern_bis = str(train["ausstieg_tag"].max().date())
    with open(datei, "wb") as f:
        pickle.dump(m, f)
    return m


def punkte_und_schwellen(kand, letzter, ordner, anteil=ANTEIL):
    """Punktzahl für alle Signale der letzten Monate (jeder Monat mit seinem eigenen Modell) und je Monat die
    Kauf-Schwelle. Abgeschlossene Monate kommen aus dem Zwischenspeicher, damit sie sich nie mehr ändern."""
    os.makedirs(ordner, exist_ok=True)
    jetzt = letzter.to_period("M")
    monate = pd.period_range(jetzt - MONATE, jetzt, freq="M")
    schluessel = kand["ticker"] + "|" + kand["tag"].dt.strftime("%Y-%m-%d")
    punkte = pd.Series(np.nan, index=kand.index)
    modell = None
    for monat in monate:
        maske = (kand["tag"].dt.to_period("M") == monat).to_numpy()
        datei = os.path.join(ordner, f"punkte_{monat}.pkl")
        if monat < jetzt and os.path.exists(datei):
            alt = pd.read_pickle(datei)
            punkte[maske] = schluessel[maske].map(alt).to_numpy(float)
            continue
        m = modell_fuer(kand, monat, ordner)
        if m is None:
            continue
        if maske.any():
            punkte[maske] = L.punktzahl(m, kand[maske])
        if monat < jetzt:
            pd.Series(punkte[maske].to_numpy(), index=schluessel[maske].to_numpy()).to_pickle(datei)
        else:
            modell = m
    # Alte Dateien weg (der Zwischenspeicher soll nicht wachsen)
    for name in os.listdir(ordner):
        teile = name.rsplit("_", 1)
        if len(teile) == 2 and teile[1].endswith(".pkl"):
            try:
                if pd.Period(teile[1][:-4], freq="M") < monate[0]:
                    os.remove(os.path.join(ordner, name))
            except ValueError:
                pass
    k = kand.assign(punkte=punkte)
    schwellen = L.monats_schwellen(k[k["tag"] >= monate[0].to_timestamp()], anteil)
    return punkte, schwellen, modell


# ----------------------------------------------------------------------------
# Fehler-Analyse der Trades im Übungsdepot des Bots
# ----------------------------------------------------------------------------
def bot_trades(pfad):
    """Abgeschlossene Long-Trades aus dem Übungsdepot des Bots (nur lesen)."""
    try:
        with open(pfad, encoding="utf-8") as f:
            stand = json.load(f)
    except (OSError, ValueError):
        return []
    return [t for t in stand.get("trades", []) if t.get("richtung", 1) > 0 and t.get("verkauf_tag")]


def aktien_daten(cache, tickers, fx, letzter):
    daten = {}
    for t in sorted(set(tickers)):
        df = D.lies_kurse(cache, t)
        if df is None or len(df) < 300:
            continue
        daten[t] = M.vorbereiten(t, df[df.index <= letzter], fx, D.lies_termine(cache, t))
    return daten


def fehler_der_bot_trades(trades, daten, spy_c, branche, sektor_von):
    """Je Trade: Ergebnis in R und die Fehler-Gründe (bei Gewinnern keine). „fertig“ erst NACHLAUF Handelstage nach
    dem Verkauf (vorher lässt sich „Stop zu eng“ noch nicht beurteilen)."""
    aus = []
    for t in trades:
        d = daten.get(t["ticker"])
        r = (t["erloes"] - t["kosten"]) / t["risiko_eur"] if t.get("risiko_eur") else np.nan
        z = {"ticker": t["ticker"], "strategie": t.get("strategie"), "kauf_tag": str(t["kauf_tag"])[:10],
             "verkauf_tag": str(t["verkauf_tag"])[:10], "grund": t.get("grund", ""), "R": r, "fehler": None,
             "fertig": False}
        if d is not None:
            pos = d["pos"]
            a, b = pos.get(pd.Timestamp(z["kauf_tag"])), pos.get(pd.Timestamp(z["verkauf_tag"]))
            if a is not None and b is not None and a >= 1:
                gelaufen = M.chart_reihen(d)["gelaufen10"].iloc[a - 1]
                tr = {"einstieg_i": a, "ausstieg_i": b, "signal_i": a - 1, "einstieg": t["einstieg_usd"],
                      "grund": z["grund"], "R": r}
                z["fehler"] = F.gruende(tr, d, spy_c, branche.get(sektor_von.get(t["ticker"])), gelaufen)
                z["fehler_text"] = [F.GRUENDE[g] for g in z["fehler"]]
                z["fertig"] = bool(d["n"] - 1 - b >= NACHLAUF)
        aus.append(z)
    return aus


# ----------------------------------------------------------------------------
# Punktzahlen für den Bot
# ----------------------------------------------------------------------------
def sperre_fuer_den_bot(kand, schwellen, watchlist):
    """Je Börsentag die Aktien der Watchlist, deren Kauf-Signal unter der Kauf-Schwelle lag (jeweils mit dem Modell,
    das damals galt). Der Bot kauft sie nicht – im Übungsdepot und in seinem Rückblick der letzten 12 Monate."""
    k = kand[kand["ticker"].isin(list(watchlist)) & kand["punkte"].notna()]
    unter = k["punkte"].to_numpy() < k["tag"].dt.to_period("M").map(schwellen).fillna(np.inf).to_numpy()
    aus = {}
    for (tag, t) in zip(k["tag"][unter], k["ticker"][unter]):
        aus.setdefault(f"{tag:%Y-%m-%d}", []).append(t)
    return {tag: sorted(liste) for tag, liste in sorted(aus.items())}


def verlauf_fuer_den_bot(kand, watchlist):
    """Je Börsentag die Punktzahl jedes Kauf-Signals der Watchlist (für die Reihenfolge der Käufe im Rückblick des
    Bots über die letzten 12 Monate)."""
    k = kand[kand["ticker"].isin(list(watchlist)) & kand["punkte"].notna()]
    aus = {}
    for tag, t, p in zip(k["tag"], k["ticker"], k["punkte"]):
        aus.setdefault(f"{tag:%Y-%m-%d}", {})[t] = round(float(p), 4)
    return dict(sorted(aus.items()))


def punkte_fuer_den_bot(kand, schwellen, tage, watchlist):
    """Je Börsentag und Aktie mit Kauf-Signal: Punktzahl, ob sie zu den besten 30 % gehört („würde kaufen“) und der
    Rang gegenüber allen Punktzahlen der 12 Monate davor (100 = besser als alle)."""
    aus = {}
    for tag in tage:
        k = kand[(kand["tag"] == tag) & kand["punkte"].notna()]
        monat = tag.to_period("M")
        vorher = kand[(kand["tag"] < monat.to_timestamp()) & (kand["tag"] >= (monat - 12).to_timestamp())]["punkte"]
        vorher = np.sort(vorher.dropna().to_numpy())
        schwelle = float(schwellen.get(monat, np.inf))
        aus[f"{tag:%Y-%m-%d}"] = {
            z["ticker"]: {"strategie": z["strategie"], "punkte": round(float(z["punkte"]), 4),
                          "rang": round(100 * np.searchsorted(vorher, z["punkte"]) / len(vorher)) if len(vorher) else None,
                          "beste": bool(z["punkte"] >= schwelle), "watchlist": z["ticker"] in watchlist}
            for _, z in k.iterrows()}
    return aus


# ----------------------------------------------------------------------------
# Seite LERNEN.md
# ----------------------------------------------------------------------------
def _k(x, stellen=2):
    return "–" if x is None or not np.isfinite(x) else f"{x:.{stellen}f}".replace(".", ",")


def _anteil(x):
    return "–" if x is None or not np.isfinite(x) else f"{100 * x:.0f} %"


def _r(x):
    return "–" if x is None or not np.isfinite(x) else f"{x:+.2f} R".replace(".", ",")


def _rang(r):
    return "–" if r is None else f"{r:.0f}"


def _name(k):
    return sw.STRATEGIEN.get(k, {}).get("name", k)


def richtung_text(r):
    if r is None or not np.isfinite(r):
        return "gemischt"
    if r >= 0.15:
        return "je höher, desto besser"
    if r <= -0.15:
        return "je niedriger, desto besser"
    return "wirkt nur zusammen mit anderen Merkmalen"


def seite(ls, punkte, letzter):
    """Die ausführliche Seite zum Lernmodell (der Bericht des Bots zeigt eine Kurzfassung)."""
    L_ = []
    a = L_.append
    a("# 🧠 Lernmodell des Swing-Bots")
    a("")
    a(f"Stand: {ls['stand']} · Kurse bis {letzter:%d.%m.%Y} · {ls['aktien']} Aktien (S&P 500, Nasdaq-100 und "
      "Watchlist)")
    a("")
    a("> Der Bot lernt hier aus jedem Trade – auch aus den nur gedachten: Jedes Kauf-Signal jeder Aktie wird nach "
      "seinen Regeln durchgespielt, jeder Verlust bekommt Gründe, und ein Lernmodell lernt jeden Monat neu, welche "
      "Signale gut laufen. **Die Kaufregeln ändern sich dadurch noch nicht** – der Bot zeigt die Punktzahl nur an. "
      "Nach der Punktzahl kauft er erst, wenn der [Rückblick](RUECKBLICK.md) zeigt, dass es besser ist, und du Ja "
      "sagst.")
    a("")
    a("## ⚠️ Daten")
    a("")
    for w in ls["warnungen"] or ["✅ Alle Kurse, Termine und Bilanzen sind da."]:
        a(f"- {'⚠️ ' if not w.startswith('✅') else ''}{w}")
    a("")
    # Signale
    heute = punkte.get(f"{letzter:%Y-%m-%d}", {})
    a(f"## 📋 Kauf-Signale vom {letzter:%d.%m.%Y} mit Punktzahl")
    a("")
    a(f"Punktzahl = vom Modell geschätzte Chance, dass der Trade im Plus endet. Rang = besser als so viel Prozent der "
      f"Signale der 12 Monate davor. ✅ = unter den besten {int(ANTEIL * 100)} % (Kauf-Schwelle diesen Monat: "
      f"{_anteil(ls['schwelle'])}).")
    a("")
    liste = sorted(heute.items(), key=lambda x: -x[1]["punkte"])
    wl = [(t, z) for t, z in liste if z["watchlist"]]
    if wl:
        a("**Deine Watchlist** (nur aus ihr kauft der Bot):")
        a("")
        a("| Aktie | Strategie | Punktzahl | Rang | |")
        a("|---|---|---:|---:|---|")
        for t, z in wl:
            a(f"| {t} | {_name(z['strategie'])} | {_anteil(z['punkte'])} | {_rang(z['rang'])} | "
              f"{'✅' if z['beste'] else '–'} |")
        a("")
    else:
        a("Keine Kauf-Signale in der Watchlist.")
        a("")
    if liste:
        a(f"**Ganzer Markt – die {min(15, len(liste))} besten von {len(liste)} Signalen** (nur zum Lernen und "
          "Vergleichen):")
        a("")
        a("| Aktie | Strategie | Punktzahl | Rang | |")
        a("|---|---|---:|---:|---|")
        for t, z in liste[:15]:
            a(f"| {t} | {_name(z['strategie'])} | {_anteil(z['punkte'])} | {_rang(z['rang'])} | "
              f"{'✅' if z['beste'] else '–'} |")
        a("")
    # Gelernt
    a("## 🧠 Was das Modell gelernt hat")
    a("")
    if ls.get("training"):
        anzahl = f"{ls['training']:,}".replace(",", ".")
        a(f"Modell für {ls['monat']}: trainiert am Monatsanfang mit **{anzahl} abgeschlossenen gedachten Trades** "
          f"(alle Kauf-Signale aller Aktien seit 2008, Ergebnis bekannt bis {ls['training_bis']}).")
        a("")
    g = ls.get("guete") or {}
    if g:
        f5 = {int(x["fuenftel"]): x for x in g["fuenftel"]}
        a(f"**Trennt es gute von schlechten Signalen?** Letzte 12 Monate ({g['n']} gedachte Trades, jeder Monat mit dem "
          "Modell, das damals galt – also ohne Blick in die Zukunft):")
        a("")
        a("| Punktzahl | Trefferquote | Ø Ergebnis |")
        a("|---|---:|---:|")
        for q, text in ((5, "bestes Fünftel"), (4, "2. Fünftel"), (3, "Mitte"), (2, "4. Fünftel"),
                        (1, "schlechtestes Fünftel")):
            if q in f5:
                a(f"| {text} | {_anteil(f5[q]['treffer'])} | {_r(f5[q]['R'])} |")
        a("")
        a(f"Trennschärfe (AUC): {_k(g['auc'])} – 0,50 wäre Münzwurf, ab etwa 0,55 ist es für Börsenkurse brauchbar.")
        a("")
    if ls.get("gelernt"):
        a(f"**Worauf es am meisten achtet** (Modell bis {ls['gelernt_bis']}, geprüft an den 12 Monaten danach: Wie viel "
          "schlechter wird die Vorhersage, wenn man das Merkmal durcheinanderwürfelt?):")
        a("")
        a("| Merkmal | Wichtigkeit | Richtung |")
        a("|---|---|---|")
        top = [x for x in ls["gelernt"] if x["wichtigkeit"] > 0][:12]
        groesste = max([x["wichtigkeit"] for x in top] or [1])
        for x in top:
            a(f"| {x['name']} | {'█' * max(1, round(8 * x['wichtigkeit'] / groesste))} | "
              f"{richtung_text(x['richtung'])} |")
        a("")
    # Fehler
    fv = ls.get("fehler") or {}
    a("## 🔎 Häufigste Fehler")
    a("")
    if fv.get("tabelle"):
        a(f"Alle gedachten Trades der letzten 12 Monate: {fv['n_alle']} Signale, davon verloren "
          f"{_anteil(fv['verlust_alle'])}. Von den {fv['n_ausgewaehlt']} Signalen mit ✅ verloren "
          f"{_anteil(fv['verlust_ausgewaehlt'])}. Lernt das Modell aus den Fehlern, kommen sie bei ✅ seltener vor:")
        a("")
        a("| Warum verloren? | bei allen Signalen | bei ✅ |")
        a("|---|---:|---:|")
        for x in fv["tabelle"]:
            if x["alle"] and x["alle"] >= 0.005:
                pfeil = (" ↓" if x["ausgewaehlt"] < 0.85 * x["alle"] else
                         " ↑" if x["ausgewaehlt"] > 1.15 * x["alle"] else "")
                a(f"| {x['text']} | {_anteil(x['alle'])} | {_anteil(x['ausgewaehlt'])}{pfeil} |")
        a("")
        a("Anteil an allen Trades; ein Trade kann mehrere Gründe haben. ↓ = das Modell meidet diesen Fehler deutlich, "
          "↑ = es tappt öfter hinein.")
        a("")
    bt = ls.get("bot_trades") or []
    a("## 📒 Fehler-Analyse der Trades im Übungsdepot")
    a("")
    if bt:
        a("| Aktie | Kauf | Verkauf | Ergebnis | Verkauft wegen | Warum verloren? |")
        a("|---|---|---|---:|---|---|")
        for t in list(reversed(bt))[:25]:
            gruende = ", ".join(F.GRUENDE.get(x, x) for x in (t["fehler"] or []))
            if t["R"] is not None and t["R"] < 0 and not t["fertig"]:
                gruende += " (vorläufig)"
            a(f"| {t['ticker']} | {pd.Timestamp(t['kauf_tag']):%d.%m.%y} | {pd.Timestamp(t['verkauf_tag']):%d.%m.%y} | "
              f"{_r(t['R'])} | {t['grund']} | {gruende or ('–' if (t['R'] or 0) >= 0 else 'keine Kurse')} |")
        a("")
    else:
        a("Noch keine abgeschlossenen Trades.")
        a("")
    a("## Ehrlich bleiben")
    a("")
    a("- **Bilanzdaten** (Bewertung, Wachstum, Qualität) kommen von der SEC mit dem Tag der Veröffentlichung; das "
      "Modell sieht jede Zahl erst ab dem Tag danach. Vor 2009 gibt es sie nicht, und Firmen ohne US-Bilanz haben "
      "keine.")
    a("- **Überlebens-Verzerrung:** Die Aktienliste ist die von heute. Firmen, die früher pleite gingen oder aus dem "
      "Index flogen, fehlen beim Lernen und im Rückblick – beides sieht dadurch etwas zu gut aus.")
    a("- **Nur Papier.** Kein echtes Geld, keine Anlageberatung.")
    a("")
    return "\n".join(L_) + "\n"


# ----------------------------------------------------------------------------
# Hauptablauf
# ----------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="Lernmodell des Swing-Bots: täglicher Lern-Lauf")
    p.add_argument("--cache", default="lern_cache")
    p.add_argument("--ohne-download", action="store_true", help="nur mit den Daten im Zwischenspeicher rechnen")
    p.add_argument("--aus", default=HIER, help="Ordner für punkte.json, lernstand.json und LERNEN.md")
    p.add_argument("--papier", default=os.path.join(WURZEL, "papier", "papier_depot.json"),
                   help="Übungsdepot des Bots (wird nur gelesen)")
    p.add_argument("--ticker", default=None, help="Watchlist (Standard: Variable TICKER bzw. Liste im Bot)")
    p.add_argument("--bis", default=None, help="nur bis zu diesem Tag rechnen (für Tests)")
    p.add_argument("--prozesse", type=int, default=4)
    a = p.parse_args(argv)
    t0 = time.time()
    cache = a.cache
    watchlist = D.watchlist(a.ticker)
    warnungen = []
    if a.ohne_download:
        uni = D._mit_watchlist(pd.read_csv(os.path.join(cache, "universum.csv")), watchlist)
    else:
        uni, w = D.lade_universum(cache, watchlist)
        warnungen += w
        tickers = list(uni["ticker"])
        warnungen += D.aktualisiere_kurse(tickers + D.ZUSATZ, cache)[1]
        warnungen += D.aktualisiere_termine(tickers, cache)
        warnungen += D.aktualisiere_bilanzen(uni, cache)
        print(f"Daten aufgefrischt ({time.time() - t0:.0f} s)", flush=True)
    tickers = list(uni["ticker"])
    sektor_von = dict(zip(uni["ticker"], uni["sektor"].fillna("Unbekannt")))
    spy, qqq, markt_df = M.markt(cache)
    fx = D.lies_kurse(cache, "EURUSD=X")["Close"]
    bis = kurse_bis(cache, tickers)
    # nur fertige Tageskerzen: läuft die US-Börse noch, zählt der heutige Tag nicht
    erwartet = pd.Timestamp(a.bis) if a.bis else erwarteter_tag()
    spy = spy[spy.index <= erwartet]
    bis = {t: (min(b, erwartet) if b is not None else None) for t, b in bis.items()}
    letzter = letzter_voller_tag(spy.index, bis)
    warnungen += daten_warnungen(cache, uni, bis, letzter, erwartet)
    mit_kursen = [t for t in tickers if bis.get(t) is not None]

    # 1) Kauf-Signale aller Aktien als gedachte Trades, mit Merkmalen und Fehler-Gründen
    kand, _ = M.alle_kandidaten(cache, mit_kursen, letzter, sektor_von, markt_df,
                                fehler_ab=letzter - pd.DateOffset(months=FEHLER_MONATE), prozesse=a.prozesse)
    print(f"Kandidaten: {len(kand)} aus {kand['ticker'].nunique()} Aktien ({time.time() - t0:.0f} s)", flush=True)

    # 2) Lernmodell (einmal im Monat neu) und Punktzahlen
    punkte, schwellen, modell = punkte_und_schwellen(kand, letzter, os.path.join(cache, "modell"))
    kand["punkte"] = punkte
    monat = letzter.to_period("M")
    print(f"Punktzahlen fertig ({time.time() - t0:.0f} s)", flush=True)

    # 3) Lernstand: einmal im Monat „was gelernt“, jeden Tag Güte und Fehler der letzten 12 Monate
    datei_ls = os.path.join(a.aus, "lernstand.json")
    alt = {}
    if os.path.exists(datei_ls):
        with open(datei_ls, encoding="utf-8") as f:
            alt = json.load(f)
    ls = {"stand": pd.Timestamp.now(tz="Europe/Berlin").strftime("%d.%m.%Y %H:%M Uhr"),
          "tag": f"{letzter:%Y-%m-%d}", "monat": str(monat), "aktien": len(mit_kursen), "anteil": ANTEIL,
          "schwelle": float(schwellen.get(monat, np.inf)), "warnungen": warnungen}
    if alt.get("monat") == str(monat) and alt.get("gelernt"):
        ls["gelernt"], ls["gelernt_bis"] = alt["gelernt"], alt.get("gelernt_bis")
    else:
        ls["gelernt"] = L.was_gelernt(kand, monat.to_timestamp())
        ls["gelernt_bis"] = str((monat.to_timestamp() - pd.DateOffset(months=12)).date())
    if modell is not None:
        ls["training"] = getattr(modell, "lern_training", None)
        ls["training_bis"] = getattr(modell, "lern_bis", None)
    letzte12 = kand[(kand["tag"] >= (monat - 12).to_timestamp()) & (kand["tag"] < monat.to_timestamp())]
    ls["guete"] = L.guete(letzte12, letzte12["punkte"])
    gewaehlt = (letzte12["punkte"].to_numpy()
                >= letzte12["tag"].dt.to_period("M").map(schwellen).fillna(np.inf).to_numpy())
    fv = F.vergleich(letzte12, gewaehlt)
    ls["fehler"] = {"tabelle": fv.to_dict("records"), **fv.attrs}

    # 4) Fehler-Analyse der Trades im Übungsdepot des Bots
    trades = bot_trades(a.papier)
    daten = aktien_daten(cache, [t["ticker"] for t in trades if bis.get(t["ticker"]) is not None], fx, letzter)
    ls["bot_trades"] = fehler_der_bot_trades(trades, daten, spy["Close"], M.branchen_index(cache), sektor_von)

    # 5) Punktzahlen der letzten Börsentage für den Bot
    tage = spy.index[spy.index <= letzter][-PUNKTE_TAGE:]
    pz = {"stand": ls["stand"], "tag": ls["tag"], "monat": ls["monat"], "anteil": ANTEIL, "schwelle": ls["schwelle"],
          "tage": punkte_fuer_den_bot(kand, schwellen, tage, set(watchlist)),
          "sperre": sperre_fuer_den_bot(kand, schwellen, set(watchlist)),
          "verlauf": verlauf_fuer_den_bot(kand, set(watchlist))}
    os.makedirs(a.aus, exist_ok=True)
    with open(os.path.join(a.aus, "punkte.json"), "w", encoding="utf-8") as f:
        json.dump(als_json(pz), f, ensure_ascii=False, indent=1)
    with open(datei_ls, "w", encoding="utf-8") as f:
        json.dump(als_json(ls), f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.aus, "LERNEN.md"), "w", encoding="utf-8") as f:
        f.write(seite(als_json(ls), pz["tage"], letzter))
    heute = pz["tage"].get(ls["tag"], {})
    print(f"Fertig ({time.time() - t0:.0f} s): {len(heute)} Signale am {letzter:%d.%m.%Y}, davon "
          f"{sum(z['watchlist'] for z in heute.values())} in der Watchlist; {len(ls['bot_trades'])} Trades analysiert")
    for w in warnungen:
        print("⚠️", w)
    return 0


def als_json(x):
    """Für JSON: Zeitpunkte als Datum, numpy-Zahlen als Python-Zahlen, NaN und unendlich als leer."""
    if isinstance(x, dict):
        return {k: als_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [als_json(v) for v in x]
    if isinstance(x, pd.Timestamp):
        return x.strftime("%Y-%m-%d")
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else float(x)
    return x


if __name__ == "__main__":
    sys.exit(main())
