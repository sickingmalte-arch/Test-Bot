"""Schlechte Nachrichten mit Datum für den Short-Test (Wunsch des Nutzers vom 18.11.2026: „wenn schlechte Nachrichten
kommen, direkt shorten“). Alte Schlagzeilen gibt es nicht (siehe „Was der Bot schon weiß“), aber zwei Arten schlechter
Nachrichten haben eine echte, datierte Geschichte:

1. Herabstufungen durch Analysten: Yahoo führt jede Änderung einer Analysten-Empfehlung mit Zeitpunkt (über yfinance,
   Aktion „down“ = herabgestuft).
2. Pflichtmeldungen an die US-Börsenaufsicht (SEC, Formular 8-K): Wichtige Nachrichten – Chefwechsel, gesenkte
   Prognose, Abschreibung, Klage, Bilanzkorrektur – muss eine Firma dort melden, mit Eingangszeit auf die Sekunde. Ob
   die Nachricht schlecht war, zeigt der Kurs am Meldungstag. Meldungen mit Quartalszahlen (Punkt 2.02) zählen nicht –
   die prüft „Short nach schlechten Zahlen“.

Zeitpunkt: Eine Nachricht bis 16:00 New Yorker Zeit zählt für diesen Börsentag, eine spätere für den nächsten. Der Bot
entscheidet am Abend und geht zur nächsten Eröffnung short – früher geht es mit Tageskursen nicht. Die SEC verlangt
eine Kennung mit Kontakt; sie kommt wie beim Lern-Lauf aus dem Secret LERNEN_SEC_KONTAKT und steht nie im Code."""
import json
import os
import time

import numpy as np
import pandas as pd

SEC_EINGANG = "https://data.sec.gov/submissions/{}"
AB = "2009-06-01"  # ältere Nachrichten braucht der Rückblick (ab 2010) nicht
FRIST = 25 * 60     # Sekunden je Datenquelle: danach zählen die übrigen Aktien als „nicht geladen“ (Zeitgrenze)


def _tag_ny(zeiten_ny):
    """Zeitpunkte in New Yorker Zeit (ohne Zone) -> Tag, an dem die Nachricht bis Börsenschluss bekannt ist."""
    zeiten_ny = pd.DatetimeIndex(zeiten_ny)
    spaet = np.asarray(zeiten_ny.hour >= 16, dtype=int)
    return zeiten_ny.normalize() + pd.to_timedelta(spaet, unit="D")


def _abbrechen(t0, versucht, fehler):
    """Zeit um oder die ersten 15 Abrufe alle gescheitert (z. B. Sperre oder fehlende Kennung): nicht weiter warten."""
    return time.time() - t0 > FRIST or (versucht >= 15 and len(fehler) >= versucht)


def herabstufungen(tickers, pause=0.3):
    """{Ticker: Tage mit Herabstufung} aus Yahoo (yfinance). Dazu Angaben, wie vollständig die Daten sind."""
    import yfinance as yf
    aus, fehler, erste, t0 = {}, [], [], time.time()
    for i, t in enumerate(tickers):
        if _abbrechen(t0, i, fehler):
            fehler += list(tickers[i:])
            break
        df = None
        for versuch in range(3):
            try:
                df = yf.Ticker(t).upgrades_downgrades
                break
            except Exception as e:  # noqa: BLE001 – keine Daten, Netzfehler oder Yahoo bremst
                df = None
                if "rate" not in str(e).lower() and "too many" not in str(e).lower():
                    break
                time.sleep(20 * (versuch + 1))
        time.sleep(pause)
        if df is None or not len(df) or "Action" not in df:
            fehler.append(t)
            continue
        zeiten = pd.DatetimeIndex(pd.to_datetime(df.index, errors="coerce"))
        gut = ~zeiten.isna()
        zeiten, aktion = zeiten[gut], df["Action"].astype(str).str.lower().to_numpy()[gut]
        if not len(zeiten):
            fehler.append(t)
            continue
        if zeiten.tz is None:
            zeiten = zeiten.tz_localize("UTC")  # yfinance liefert Sekunden seit 1970 in UTC
        ny = zeiten.tz_convert("America/New_York").tz_localize(None)
        erste.append(ny.min())
        tage = _tag_ny(ny[aktion == "down"])
        aus[t] = np.array(sorted(set(tage[tage >= pd.Timestamp(AB)])), dtype="datetime64[ns]")
    return aus, {"art": "Herabstufungen", "fehler": fehler, "erste": erste}


def _eingang_tag(zeit):
    """Eingangszeit der SEC („acceptanceDateTime“: New Yorker Zeit, trotz „Z“ am Ende – die SEC nimmt Meldungen von
    6 bis 22 Uhr New Yorker Zeit an) -> Tag, an dem die Meldung bis Börsenschluss bekannt ist. Wäre es doch UTC, läge
    die echte Zeit früher – der Bot handelte dann nur später, nie mit Wissen aus der Zukunft."""
    try:
        ts = pd.Timestamp(str(zeit)[:19])
    except (TypeError, ValueError):
        return None
    if ts is pd.NaT:
        return None
    return ts.normalize() + pd.Timedelta(days=1) if ts.hour >= 16 else ts.normalize()


def meldungen_8k(D, cache, tickers, pause=0.15):
    """{Ticker: Tage mit 8-K-Meldung ohne Quartalszahlen} von der SEC (Liste aller Einreichungen je Firma)."""
    uni = pd.read_csv(os.path.join(cache, "universum.csv"))
    cik_von = dict(zip(uni["ticker"].astype(str), pd.to_numeric(uni["cik"], errors="coerce")))
    aus, fehler, ohne, t0 = {}, [], [], time.time()
    for i, t in enumerate(tickers):
        if _abbrechen(t0, i - len(ohne), fehler):
            fehler += [x for x in tickers[i:] if x not in ohne]
            break
        cik = cik_von.get(t)
        if cik is None or not np.isfinite(cik):
            ohne.append(t)
            continue
        try:
            haupt = json.loads(D.hole(SEC_EINGANG.format(f"CIK{int(cik):010d}.json"), versuche=2))
            teile = [(haupt.get("filings") or {}).get("recent") or {}]
            for datei in (haupt.get("filings") or {}).get("files") or []:
                if str(datei.get("filingTo", "9999")) >= AB:
                    time.sleep(pause)
                    teile.append(json.loads(D.hole(SEC_EINGANG.format(datei["name"]), versuche=2)))
            tage = set()
            for teil in teile:
                formen = teil.get("form") or []
                punkte = teil.get("items") or [""] * len(formen)
                zeiten = teil.get("acceptanceDateTime") or [""] * len(formen)
                for form, items, zeit in zip(formen, punkte, zeiten):
                    if form != "8-K" or "2.02" in str(items).replace(" ", "").split(","):
                        continue
                    tag = _eingang_tag(zeit)
                    if tag is not None and tag >= pd.Timestamp(AB):
                        tage.add(tag)
            aus[t] = np.array(sorted(tage), dtype="datetime64[ns]")
        except Exception:  # noqa: BLE001 – Netzfehler oder fehlende Kennung: Aktie zählt als „nicht geladen“
            fehler.append(t)
        time.sleep(pause)
    return aus, {"art": "Pflichtmeldungen", "fehler": fehler, "ohne_cik": ohne}


def rutsch(d, faktor=2.0):
    """Schluss mindestens faktor × ATR (vom Vortag) unter dem Vortagesschluss – am Abend bekannt."""
    c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
    vor, atr_vor = np.r_[np.nan, c[:-1]], np.r_[np.nan, atr[:-1]]
    with np.errstate(invalid="ignore"):
        return (vor - c) >= faktor * atr_vor


def zahlen_tag(d):
    """Tage, an denen Quartalszahlen auf den Kurs wirken (aus dem Bot, ohne Termine: keine)."""
    n = len(d["C"])
    aus = np.zeros(n, bool)
    reak = d.get("reak")
    if reak is not None:
        r = np.asarray(reak, dtype=bool)[:n]
        aus[:len(r)] = r
    return aus


def abdeckung_md(zr, ereignisse, info, tickers):
    """Eine Zeile: wie vollständig die Nachrichten-Daten sind und wie viele Ereignisse je Zeitraum vorkommen."""
    mit = [t for t in tickers if t in ereignisse]
    je = []
    for von, z in zr.items():
        bis = pd.Timestamp(z["bis"])
        auswahl = {t for liste in z["listen"] for t in liste}
        n = sum(int(((ereignisse[t] >= np.datetime64(pd.Timestamp(von))) & (ereignisse[t] <= np.datetime64(bis))).sum())
                for t in auswahl if t in ereignisse)
        je.append(f"{von[:4]}–{bis.year}: {n}")
    teile = [f"{info['art']}: Daten für {len(mit)} von {len(tickers)} Aktien"]
    if info.get("erste"):
        erste = pd.DatetimeIndex(info["erste"])
        mitte = erste.sort_values()[len(erste) // 2]
        teile.append(f"früheste vom {erste.min():%d.%m.%Y}, bei der Hälfte der Aktien ab {mitte:%Y}")
    if info.get("ohne_cik"):
        teile.append(f"ohne SEC-Nummer: {len(info['ohne_cik'])}")
    if info.get("fehler"):
        teile.append(f"nicht geladen: {len(info['fehler'])}")
    return ("- " + ", ".join(teile) + ". Ereignisse in den gezogenen Aktien je Zeitraum: " + ", ".join(je) + ".")
