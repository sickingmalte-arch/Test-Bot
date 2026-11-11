"""Prüfung „day-trader-skill“ (Wunsch vom 11.11.2026): der eigentliche Tageshandel des Skills – Ausbruch aus der
Eröffnungsspanne (trader-scanner orb, trader-entry, trader-exit). Eigener Prüfablauf (pruefen), weil der Bot mit
Tageskerzen handelt: Hier werden Stunden- und 5-Minuten-Kerzen der Watchlist bei Yahoo geholt und jeder Handelstag nach
den Regeln des Skills durchgespielt – und gegen Zufalls-Einstiege zur gleichen Uhrzeit mit gleichem Risiko geprüft.

Regeln wie im Skill: Spanne = Hoch und Tief der ersten Minuten (5-Minuten-Kerzen: 15 Minuten wie im Skill; Stunden-
Kerzen: die erste Stunde). Einstieg zum Schluss der ersten Kerze, die ÜBER dem Hoch der Spanne schließt, nicht nach
15:30 Uhr New York. Stop = Mitte der Spanne (abgerundet), Ziel = 1R oder 2R, raus spätestens zum Schluss (5-Minuten:
15:55 Uhr; Stunden-Kerzen: zum Tagesschluss). Stop vor Ziel in derselben Kerze. Spread 0,1 % je Order wie im Bot."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skill_hilfe as H  # noqa: E402

NAME = "Day-Trader-Skill: Tageshandel mit dem Ausbruch aus der Eröffnungsspanne"
QUELLE = H.QUELLE
BESCHREIBUNG = ("Der Tageshandel des Skills: Kauf, wenn eine Kerze über dem Hoch der Eröffnungsspanne schließt, Stop in "
                "der Mitte der Spanne, Ziel 1R oder 2R, raus spätestens zum Schluss. Geprüft mit Stunden-Kerzen der "
                "letzten 2 Jahre (Spanne = erste Stunde) und 5-Minuten-Kerzen der letzten 60 Tage (Spanne = erste 15 "
                "Minuten, wie im Skill) für alle Aktien der Watchlist. Gegenprobe: für jeden Trade 20 Einstiege an "
                "zufälligen anderen Tagen derselben Aktie zur gleichen Uhrzeit, mit gleichem Stop-Abstand und Ziel.")
VERMUTUNG = ("Der Ausbruch aus der Eröffnungsspanne bringt nach Spread im Schnitt mehr als 0 R je Trade und mehr als "
             "zufällige Einstiege zur gleichen Uhrzeit mit gleichem Risiko.")
WIDERLEGT_WENN = ("Je Variante: im Schnitt höchstens 0 R nach Spread, oder der Unterschied zu den Zufalls-Einstiegen ist "
                  "nicht klar positiv (98-%-Intervall, nach Handelstagen gezogen, nicht ganz über 0). Unter 30 Trades: "
                  "keine Aussage.")
VARIANTEN = ("4, vor dem Rechnen festgelegt: Stunden-Kerzen (2 Jahre) und 5-Minuten-Kerzen (60 Tage), je Ziel 1R "
             "(Beispiel im Skill) und 2R (Standard im Skill). Selbst wenn eine besteht: nur ein Zeitraum statt drei, und "
             "der Bot kann nicht minutengenau handeln (Live-Kurse 15 Minuten verzögert) – also höchstens eine Vermutung, "
             "kein Einbau.")
SPREAD = 0.001
ZUFALL_JE_TRADE = 20
DATENSAETZE = (("Stunden-Kerzen, 2 Jahre", "60m", "730d", 60, 1), ("5-Minuten-Kerzen, 60 Tage", "5m", "60d", 5, 3))
ZIELE = (1.0, 2.0)
SCHLUSS_EINSTIEG = 15 * 60 + 30   # keine Einstiege nach 15:30 Uhr New York
FLAT_5M = 15 * 60 + 55            # 5-Minuten-Kerzen: raus zum Schluss der 15:50-Kerze (15:55 Uhr)


def _laden(tickers, intervall, zeitraum):
    import yfinance as yf
    aus = {}
    for t in tickers:
        try:
            df = yf.download(t, interval=intervall, period=zeitraum, auto_adjust=False, prepost=False, progress=False,
                             threads=False)
        except Exception as fehler:  # noqa: BLE001 – eine fehlende Aktie bricht die Prüfung nicht ab
            print(f"{t} {intervall}: {fehler}")
            continue
        if df is None or df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
        idx = pd.DatetimeIndex(df.index)
        df.index = (idx.tz_localize("UTC") if idx.tz is None else idx).tz_convert("America/New_York")
        aus[t] = df
    return aus


def _sitzungen(df, laenge):
    """Nur volle Handelstage (9:30 bis 16:00 ohne Lücke): {Datum: (Startminuten, O, H, L, C)}."""
    voll = 390 // laenge + (1 if 390 % laenge else 0)
    aus = {}
    for tag, teil in df.groupby(df.index.date):
        minuten = teil.index.hour * 60 + teil.index.minute
        teil = teil[(minuten >= 570) & (minuten < 960)]
        m = teil.index.hour * 60 + teil.index.minute
        if len(teil) != voll or int(m[0]) != 570 or np.any(np.diff(m) != laenge):
            continue
        aus[tag] = (np.asarray(m), *(teil[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close")))
    return aus


def _ausgang(o, h, lo, c, start, ein, stop, ziel, letzte):
    """Von der Kerze nach dem Einstieg bis zur letzten erlaubten Kerze: Stop zuerst, dann Ziel, sonst zum Schluss."""
    for k in range(start, letzte + 1):
        if o[k] <= stop:
            return o[k], "stop"
        if lo[k] <= stop:
            return stop, "stop"
        if o[k] >= ziel:
            return o[k], "ziel"
        if h[k] >= ziel:
            return ziel, "ziel"
    return c[letzte], "schluss"


def _r_netto(ein, aus, risiko):
    return (aus * (1 - SPREAD) - ein * (1 + SPREAD)) / risiko


def _letzte(m, laenge):
    erlaubt = np.flatnonzero(m + laenge <= FLAT_5M) if laenge == 5 else np.arange(len(m))
    return int(erlaubt[-1])


def _orb_trades(sitz, laenge, n_spanne, r_ziel):
    """Alle Ausbrüche einer Aktie: Liste (Datum, Einstiegskerze, Risiko-Anteil, R netto, Ausgang)."""
    trades = []
    for tag, (m, o, h, lo, c) in sitz.items():
        hoch, tief = h[:n_spanne].max(), lo[:n_spanne].min()
        stop = np.floor((hoch + tief) / 2 * 100) / 100
        letzte = _letzte(m, laenge)
        for k in range(n_spanne, len(c)):
            if m[k] + laenge > SCHLUSS_EINSTIEG:
                break
            if c[k] > hoch:
                ein = c[k]
                risiko = ein - stop
                if risiko < 0.0005 * ein or k >= letzte:
                    break
                ziel = np.floor((ein + r_ziel * risiko) * 100 + 0.5) / 100
                aus, grund = _ausgang(o, h, lo, c, k + 1, ein, stop, ziel, letzte)
                trades.append((tag, k, risiko / ein, _r_netto(ein, aus, risiko), grund))
                break  # ein Einstieg je Tag: der erste Schluss über dem Hoch
    return trades


def _zufall_r(sitz, tag, k, anteil, r_ziel, laenge, rng):
    """Mittleres R von 20 Einstiegen an zufälligen anderen Tagen derselben Aktie zur gleichen Uhrzeit (Kerze k)."""
    tage = [x for x in sitz if x != tag]
    werte = []
    for wahl in rng.choice(len(tage), min(ZUFALL_JE_TRADE, len(tage)), replace=False):
        m, o, h, lo, c = sitz[tage[wahl]]
        letzte = _letzte(m, laenge)
        if k >= letzte:
            continue
        ein = c[k]
        risiko = ein * anteil
        aus, _ = _ausgang(o, h, lo, c, k + 1, ein, ein - risiko, ein + r_ziel * risiko, letzte)
        werte.append(_r_netto(ein, aus, risiko))
    return float(np.mean(werte)) if werte else np.nan


def _intervall(diff, tage, seed=0):
    """98-%-Intervall des mittleren Unterschieds, ganze Handelstage gezogen (Aktien am selben Tag laufen ähnlich)."""
    s = pd.Series(diff).groupby(np.asarray(tage))
    summe, anzahl = s.sum().to_numpy(), s.size().to_numpy()
    rng = np.random.default_rng(seed)
    werte = [summe[z].sum() / anzahl[z].sum() for z in (rng.integers(0, len(summe), len(summe)) for _ in range(2000))]
    return float(np.percentile(werte, 1)), float(np.percentile(werte, 99))


def pruefen(P, a, watch, sektor_von):
    tickers = list(watch)
    erg = {}
    for titel, intervall, zeitraum, laenge, n_spanne in DATENSAETZE:
        daten = _laden(tickers, intervall, zeitraum)
        sitz = {t: _sitzungen(df, laenge) for t, df in daten.items()}
        sitz = {t: s for t, s in sitz.items() if len(s) >= 20}
        n_tage = sum(len(s) for s in sitz.values())
        for r_ziel in ZIELE:
            name = f"{titel}, Ziel {r_ziel:.0f}R"
            alle = []
            for t, s in sitz.items():
                rng = np.random.default_rng([19, sum(map(ord, t)), int(r_ziel), laenge])
                for tag, k, anteil, r, grund in _orb_trades(s, laenge, n_spanne, r_ziel):
                    alle.append((t, tag, r, _zufall_r(s, tag, k, anteil, r_ziel, laenge, rng), grund))
            if not alle:
                erg[name] = {"n": 0}
                continue
            r = np.array([x[2] for x in alle])
            z = np.array([x[3] for x in alle])
            gut = np.isfinite(z)
            diff = r[gut] - z[gut]
            lo, hi = _intervall(diff, [x[1] for x, g in zip(alle, gut) if g])
            n = len(alle)
            gruende = pd.Series([x[4] for x in alle]).value_counts(normalize=True)
            besteht = n >= 30 and r.mean() > 0 and lo > 0
            urteil = ("keine Aussage (unter 30 Trades)" if n < 30 else "besteht" if besteht else "besteht nicht")
            erg[name] = {"aktien": len(sitz), "handelstage": n_tage, "n": n, "r_schnitt": round(float(r.mean()), 3),
                         "r_zufall": round(float(np.nanmean(z)), 3), "unterschied": round(float(diff.mean()), 3),
                         "lo": round(lo, 3), "hi": round(hi, 3), "treffer": round(float(np.mean(r > 0)), 3),
                         "ziel": round(float(gruende.get("ziel", 0)), 3), "stop": round(float(gruende.get("stop", 0)), 3),
                         "schluss": round(float(gruende.get("schluss", 0)), 3), "urteil": urteil}
            print(f"{name}: {n} Trades, Schnitt {r.mean():+.3f} R, Zufall {np.nanmean(z):+.3f} R, Unterschied "
                  f"{diff.mean():+.3f} ({lo:+.3f} bis {hi:+.3f}) -> {urteil}")
    bestanden = [k for k, v in erg.items() if v.get("urteil") == "besteht"]
    text = ("Tageshandel (ORB): " + (f"besteht in {len(bestanden)} von {len(erg)} Varianten – nur eine Vermutung, kein "
                                     "Einbau" if bestanden else "besteht in keiner Variante"))
    plus = {k: v.get("unterschied", 0.0) for k, v in erg.items()}
    return text, plus, {"basis": erg, "varianten": erg}, _markdown(erg, text)


def _markdown(erg, text):
    de = lambda x, f="+.3f": format(x, f).replace(".", ",")  # noqa: E731
    z = [f"# 🔬 {NAME}", "", f"Getestet am {dt.date.today():%d.%m.%Y} · Quelle: {QUELLE}", "", BESCHREIBUNG, "",
         f"- **Vermutung:** {VERMUTUNG}", f"- **Widerlegt, wenn:** {WIDERLEGT_WENN}", f"- **Varianten:** {VARIANTEN}", "",
         f"**Ergebnis:** {text}", "",
         "| Variante | Aktien / Handelstage | Trades | Ziel / Stop / Schluss | Gewinner | Ø R nach Spread | Ø R Zufall | "
         "Unterschied (98-%-Intervall) | Urteil |", "|---|---:|---:|---|---:|---:|---:|---|---|"]
    for k, v in erg.items():
        if not v.get("n"):
            z.append(f"| {k} | – | 0 | – | – | – | – | – | keine Daten |")
            continue
        z.append(f"| {k} | {v['aktien']} / {v['handelstage']} | {v['n']} | {v['ziel']:.0%} / {v['stop']:.0%} / "
                 f"{v['schluss']:.0%} | {v['treffer']:.0%} | {de(v['r_schnitt'])} | {de(v['r_zufall'])} | "
                 f"{de(v['unterschied'])} ({de(v['lo'])} bis {de(v['hi'])}) | {v['urteil']} |")
    z += ["", "R = Gewinn oder Verlust in Vielfachen des geplanten Risikos (Einstieg bis Stop), nach 0,1 % Spread je Order. "
          "Stunden-Kerzen sind gröber als im Skill (Spanne = erste Stunde, Ausstieg zum Tagesschluss). Nur die letzten 2 "
          "Jahre bzw. 60 Tage und die heutige Watchlist – ein einziger Zeitraum. Simulation, keine Anlageberatung."]
    return "\n".join(z) + "\n"
