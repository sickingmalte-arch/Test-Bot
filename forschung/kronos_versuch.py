"""Kronos-Versuch nach vorne (Wunsch des Nutzers vom 08.11.2026, erweitert am 09.11.) – nur eine Messung, der Bot
kauft nicht danach.

Kronos (github.com/shiyu-coder/Kronos, AAAI 2026) ist eine KI, die mit über 12 Milliarden Kerzen von 45 Börsen
trainiert wurde und viele mögliche Zukünfte eines Kursverlaufs ausrechnet. Ein Rückblick wäre unehrlich, weil das
Modell die Kurse von 2010–2026 im Training schon gesehen haben kann. Deshalb nur NACH VORNE:

- Nach jedem Bot-Lauf rechnet Kronos für jedes neue Kauf-Signal je 50 Zukünfte über 20 Handelstage (so lange hält der
  Bot höchstens), in vier vorher festgelegten Varianten (VARIANTEN unten):
    small-256      Kronos-small, Rückblick 256 Tageskerzen (Probeläufe: starker Zug zum Durchschnitt des Rückblicks)
    small-64       Kronos-small, Rückblick 64 Tageskerzen
    small-64-T15   wie small-64, aber mehr Zufall beim Rechnen (Temperatur 1,5, ohne Abschneiden) – gegen übermütige
                   0-%/100-%-Aussagen
    base-256       das größere Kronos-base (102 Mio. Parameter), Rückblick 256 – rechnet lange, deshalb nur die ersten
                   3 Signale am Tag
- Frage 1 (Richtung): Wie oft kommt zuerst das Ziel, wie oft zuerst der Stop (am selben Tag beides: Stop zuerst – wie
  im Bot)? Vergleich: ein Zufallsweg ohne Richtung (Schwankung der letzten 250 Tage) – die einfache „Formel“.
- Frage 2 (Schwankung, laut Paper die Stärke von Kronos): Wie groß sind die Tageskerzen (Hoch−Tief) und wie stark
  schwankt der Schluss in den 20 Tagen? Vergleich: einfach die letzten 20 Tage fortschreiben.
- Nach 20 Handelstagen wird mit den echten Kursen nachgesehen.

Vorher festgelegt (zählt erst ab 30 ausgewerteten Signalen, je Variante): Eine Variante ist besser, wenn ihr Fehler
(Richtung: Brier-Wert der Wahrscheinlichkeit „Ziel zuerst“; Schwankung: mittlere Abweichung der Tagesspanne) unter dem
des Vergleichs liegt und das Bootstrap-Intervall des Unterschieds ganz unter 0 liegt. Sonst: nicht besser.

Erweiterung am 09.11.2026 abends (Wunsch „bau alles“), festgelegt bevor ein einziges Signal ausgewertet war:
- Abgeleitete Vorhersagen ohne eigene Rechnung: „Mittel“ = Durchschnitt aller Varianten, die für das Signal gerechnet
  haben; „Mittel ½ + Zufall ½“ = halb Mittel, halb Zufallsweg (gegen Übermut); „Mittel geeicht“ (Schwankung) = Mittel
  geteilt durch den Faktor, um den Kronos bisher danebenlag – gemessen nur an Signalen, die zum Signaltag schon
  ausgewertet waren (Median, mindestens 10), also ohne Blick in die Zukunft.
- Zweiter Vergleich bei der Richtung: die Ziel-Chance des Bots (Black-Scholes, rechnet ohne Stop und liegt deshalb eher
  zu hoch – aber das ist, was der Bot heute schon anzeigt). Kronos nützt dem Bot nur, wenn es auch die schlägt.
- Watchlist täglich: Für alle Aktien der Watchlist rechnen die beiden schnellen Varianten (small-64, small-64-T15) mit
  festem Stop −2 ATR und Ziel +2 ATR (ATR 14). Weil Aktien am selben Tag ähnlich laufen, wird hier nach Tagen gezogen
  (Bootstrap über Tage) und erst ab 15 ausgewerteten Tagen geurteilt.
- Weil es jetzt viele Vergleiche sind, gilt für alle die strengere Hürde: 98-%-Intervall (vorher 90 %).

Für die Webseite (docs/kronos.json): je Signal und Variante der „Fächer“ (10-%-, 50-%- und 90-%-Linie der 50 Zukünfte
für jeden der 20 Tage) und nach der Auswertung der echte Verlauf.

Aufruf: python forschung/kronos_versuch.py --modus pruefen   (nur: gibt es etwas zu tun? für GitHub Actions)
        python forschung/kronos_versuch.py --modus lauf [--probe] [--ausgabe ordner]
        python forschung/kronos_versuch.py --modus seite     (nur Bericht und docs/kronos.json neu schreiben)"""
import argparse
import datetime as dt
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
DATEN = os.path.join(WURZEL, "docs", "daten.json")
TAGE = 20
MIN_AUSWERTUNG = 30
WARTEN_KALENDERTAGE = 32  # nach so vielen Kalendertagen sind 20 Handelstage sicher vorbei
SEITE_SIGNALE = 40  # so viele Signale (die neuesten) zeigt die Webseite
TOKENIZER = "NeoQuasar/Kronos-Tokenizer-base"
# Fester Modell-Stand bei Hugging Face (Commit). So ändern sich die Gewichte nicht unbemerkt, auch nicht, wenn das
# fremde Konto gekapert würde. Einen neuen Stand nur bewusst eintragen; den aktuellen zeigt jeder Lauf am Ende an.
MODELL_STAND = {  # Stand vom 13.11.2026 (aus dem Probelauf an diesem Tag)
    "NeoQuasar/Kronos-Tokenizer-base": "0e0117387f39004a9016484a186a908917e22426",
    "NeoQuasar/Kronos-small": "901c26c1332695a2a8f243eb2f37243a37bea320",
    "NeoQuasar/Kronos-base": "2b554741eca47781b64468546e77fef3e85130e6",
}
PFADE = int(os.environ.get("KRONOS_PFADE", "50"))
MAX_SIGNALE = int(os.environ.get("KRONOS_MAX_SIGNALE", "8"))
ZEITBUDGET_SEK = 60 * int(os.environ.get("KRONOS_ZEITBUDGET_MIN", "80"))  # danach keine langsamen Varianten mehr
VARIANTEN = [
    {"name": "small-256", "modell": "NeoQuasar/Kronos-small", "rueckblick": 256, "T": 1.0, "top_p": 0.9, "max": 8},
    {"name": "small-64", "modell": "NeoQuasar/Kronos-small", "rueckblick": 64, "T": 1.0, "top_p": 0.9, "max": 8},
    {"name": "small-64-T15", "modell": "NeoQuasar/Kronos-small", "rueckblick": 64, "T": 1.5, "top_p": 1.0, "max": 8},
    {"name": "base-256", "modell": "NeoQuasar/Kronos-base", "rueckblick": 256, "T": 1.0, "top_p": 0.9, "max": 3},
]
MISCHUNG = 0.5  # Anteil Kronos in „Mittel ½ + Zufall ½“
EICH_MIN = 10  # so viele schon ausgewertete Signale braucht der Eich-Faktor
INTERVALL = (1, 99)  # Bootstrap-Intervall in Prozent (98 %)
LISTE_VARIANTEN = ["small-64", "small-64-T15"]  # täglich für alle Aktien der Watchlist (je etwa 30 s)
LISTE_ATR = 2.0  # Watchlist: Stop −2 ATR, Ziel +2 ATR
LISTE_MIN_TAGE = 15  # Urteil erst ab so vielen ausgewerteten Tagen
LISTE_BUDGET_SEK = 60 * int(os.environ.get("KRONOS_LISTE_BUDGET_MIN", "115"))  # ab Laufbeginn, danach Schluss
_PREDICTOREN = {}


# ---------------------------------------------------------------- Dateien
def pfade(ausgabe=None):
    """Log, Bericht, Webseiten-Daten und Watchlist-Log – im Repo oder (GitHub-Lauf ohne Schreibrechte) in einem eigenen
    Ordner."""
    if ausgabe:
        return tuple(os.path.join(ausgabe, n) for n in ("kronos_log.json", "kronos_ergebnis.md", "kronos.json",
                                                         "kronos_liste_log.json"))
    return (os.path.join(HIER, "kronos_log.json"), os.path.join(HIER, "kronos_ergebnis.md"),
            os.path.join(WURZEL, "docs", "kronos.json"), os.path.join(HIER, "kronos_liste_log.json"))


def lies_log(datei):
    try:
        with open(datei, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def schreibe(datei, inhalt):
    os.makedirs(os.path.dirname(datei), exist_ok=True)
    tmp = datei + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if isinstance(inhalt, str):
            f.write(inhalt)
        else:
            json.dump(inhalt, f, ensure_ascii=False, indent=1)
    os.replace(tmp, datei)


def kauf_signale(daten):
    """Kauf-Signale des letzten fertigen Tages (Long, mit Stop und Ziel)."""
    return [s for s in daten.get("signale", [])
            if s.get("stop") is not None and s.get("ziel") is not None and s.get("kurs")
            and s["stop"] < s["kurs"] < s["ziel"]]


def faellig(e, heute):
    return "ergebnis" not in e and (heute - dt.date.fromisoformat(e["signal_tag"])).days >= WARTEN_KALENDERTAGE


# ---------------------------------------------------------------- Rechnen
def ausgang(o, h, lo, stop, ziel):
    """Was kommt zuerst? Kurslücke zur Eröffnung über Stop/Ziel zählt sofort, im Tagesverlauf Stop vor Ziel (wie im
    Bot). Gibt ("ziel"|"stop"|"zeit", Tag ab 1) zurück."""
    for i in range(len(h)):
        if np.isfinite(o[i]) and o[i] <= stop:
            return "stop", i + 1
        if np.isfinite(o[i]) and o[i] >= ziel:
            return "ziel", i + 1
        if lo[i] <= stop:
            return "stop", i + 1
        if h[i] >= ziel:
            return "ziel", i + 1
    return "zeit", len(h)


def zufallsweg(schluss, kurs, stop, ziel, n=4000, schritte=13, seed=0):
    """Wahrscheinlichkeit „Ziel vor Stop“, wenn der Kurs ohne Richtung schwankt (Brownsche Bewegung mit der
    Tagesschwankung der letzten 250 Tage). Je Tag 13 Teilschritte für Tageshoch und -tief."""
    r = np.diff(np.log(np.asarray(schluss, float)[-251:]))
    vola = float(np.std(r[np.isfinite(r)]))
    rng = np.random.default_rng(seed)
    wege = kurs * np.exp(np.cumsum(rng.normal(0, vola / np.sqrt(schritte), (n, TAGE * schritte)), axis=1))
    tage = wege.reshape(n, TAGE, schritte)
    hoch, tief = tage.max(axis=2), tage.min(axis=2)
    erg = [ausgang(np.full(TAGE, np.nan), hoch[k], tief[k], stop, ziel)[0] for k in range(n)]
    return erg.count("ziel") / n, vola


def spanne_und_vola(df, start_kurs=None):
    """Mittlere Tagesspanne (Hoch−Tief)/Schluss und Schwankung der Schlusskurse (Standardabweichung der täglichen
    Log-Renditen), beides in Prozent."""
    c = df["close"].to_numpy(float)
    if start_kurs is not None:
        c = np.concatenate([[start_kurs], c])
    spanne = float(((df["high"] - df["low"]) / df["close"]).mean()) * 100
    return spanne, float(np.std(np.diff(np.log(c)))) * 100


def lade_predictor(modell):
    if modell not in _PREDICTOREN:
        sys.path.insert(0, os.path.join(HIER, "kronos_modell"))
        import torch  # noqa: F401  (erst hier – der Bot braucht torch nicht)
        from model import Kronos, KronosPredictor, KronosTokenizer
        tok = KronosTokenizer.from_pretrained(TOKENIZER, revision=MODELL_STAND.get(TOKENIZER))
        netz = Kronos.from_pretrained(modell, revision=MODELL_STAND.get(modell))
        _PREDICTOREN[modell] = KronosPredictor(netz, tok, device="cpu", max_context=512)
    return _PREDICTOREN[modell]


def modell_stand_melden():
    """Schreibt ins Protokoll, welcher Modell-Stand fest eingestellt ist und welcher bei Hugging Face aktuell ist."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return
    for name, fest in MODELL_STAND.items():
        try:
            jetzt = HfApi().model_info(name).sha
        except Exception as fehler:  # noqa: BLE001 – nur zur Info, darf den Lauf nicht stoppen
            jetzt = f"unbekannt ({fehler.__class__.__name__})"
        anders = fest and jetzt != fest and not jetzt.startswith("unbekannt")
        hinweis = " – dort gibt es einen neueren Stand, es bleibt beim festen" if anders else ""
        print(f"Modell-Stand {name}: fest {fest or 'noch nicht festgelegt'} · bei Hugging Face jetzt {jetzt}{hinweis}")


def kurse(ticker, start, ende=None, roh=False):
    """Tageskerzen von Yahoo, Index = Datum ohne Zeitzone. Für Kronos bereinigt (Splits, Dividenden – am letzten Tag
    gleich dem echten Kurs); für die Auswertung roh, sonst würden spätere Dividenden die Kurse nachträglich verschieben."""
    import yfinance as yf
    df = yf.download(ticker, start=start, end=ende, auto_adjust=not roh, progress=False, threads=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])
    idx = pd.DatetimeIndex(df.index)
    df.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize()
    return df


def kronos_zukuenfte(predictor, df, n, seed, rueckblick, T, top_p):
    """n einzelne Zukünfte (Kronos mittelt mehrere Proben sonst zu einem Pfad – deshalb n Kopien mit je 1 Probe)."""
    import torch
    torch.manual_seed(seed)
    x = df.tail(rueckblick)
    x_df = x[["open", "high", "low", "close", "volume"]].reset_index(drop=True).astype(float)
    x_ts = pd.Series(x.index)
    y_ts = pd.Series(pd.bdate_range(pd.Timestamp(x.index[-1]) + pd.DateOffset(days=1), periods=TAGE))
    return predictor.predict_batch([x_df] * n, [x_ts] * n, [y_ts] * n, pred_len=TAGE, T=T, top_p=top_p,
                                   sample_count=1, verbose=False)


def kronos_variante(predictor, df, kurs_usd, stop, ziel, seed, v, faecher=True):
    """Eine Variante für ein Signal: Ziel/Stop zuerst, Ende nach 20 Tagen, Tagesspanne, Schwankung (und der Fächer)."""
    t1 = time.time()
    wege = kronos_zukuenfte(predictor, df, PFADE, seed, v["rueckblick"], v["T"], v["top_p"])
    erg = [ausgang(w["open"].to_numpy(), w["high"].to_numpy(), w["low"].to_numpy(), stop, ziel)[0] for w in wege]
    verlauf = np.array([w["close"].to_numpy(float) / kurs_usd - 1 for w in wege]) * 100  # Zukünfte × Tage
    ende20 = verlauf[:, -1]
    sv = np.array([spanne_und_vola(w, start_kurs=kurs_usd) for w in wege])
    x = {"p_ziel": round(erg.count("ziel") / len(erg), 3), "p_stop": round(erg.count("stop") / len(erg), 3),
         "nach_20_tagen_prozent": {"q10": round(float(np.percentile(ende20, 10)), 2),
                                   "mitte": round(float(np.median(ende20)), 2),
                                   "q90": round(float(np.percentile(ende20, 90)), 2)},
         "tagesspanne_prozent": round(float(sv[:, 0].mean()), 3), "vola_prozent": round(float(sv[:, 1].mean()), 3),
         "abstand_zum_mittel_prozent": round((kurs_usd / float(df["close"].tail(v["rueckblick"]).mean()) - 1) * 100, 1)}
    if faecher:
        x["faecher"] = {k: [round(float(q), 2) for q in np.percentile(verlauf, qq, axis=0)]
                        for k, qq in (("q10", 10), ("mitte", 50), ("q90", 90))}
    x["sekunden"] = round(time.time() - t1, 1)
    return x


def atr_prozent(df, n=14):
    """Mittlere wahre Spanne der letzten n Tage in Prozent vom letzten Schluss."""
    h, lo, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    tr = np.maximum(h[1:] - lo[1:], np.maximum(abs(h[1:] - c[:-1]), abs(lo[1:] - c[:-1])))
    return float(np.mean(tr[-n:]) / c[-1] * 100)


def zeitraum(tag):
    return ((dt.date.fromisoformat(tag) - dt.timedelta(days=700)).isoformat(),
            (dt.date.fromisoformat(tag) + dt.timedelta(days=1)).isoformat())


def vorhersage(daten, log, predictor_fn=lade_predictor, kurse_fn=kurse, probe=False, t_start=None):
    t_start = t_start or time.time()
    tag = daten["daten_bis"]
    if daten.get("vorlaeufig"):
        print("Daten noch vorläufig – nichts zu tun.")
        return 0
    sigs = kauf_signale(daten)
    if probe and not sigs:  # Probelauf ohne Signal: zwei Aktien mit ±5 % (nur zum Messen der Rechenzeit)
        sigs = [{"ticker": s["ticker"], "strategie": "Probe ±5 %", "kurs": 1.0, "stop": 0.95, "ziel": 1.05,
                 "chance": None} for s in daten.get("signale", [])[:2]]
    schon = {(e["signal_tag"], e["ticker"]) for e in log}
    neu = [s for s in sigs if (tag, s["ticker"]) not in schon][:3 if probe else MAX_SIGNALE]
    if not neu:
        print(f"Signale vom {tag}: nichts Neues.")
        return 0
    start, ende = zeitraum(tag)
    laenge = max(v["rueckblick"] for v in VARIANTEN)
    for nr, s in enumerate(neu):
        t0 = time.time()
        df = kurse_fn(s["ticker"], start, ende)
        if df is None or df.empty or df.index[-1].date().isoformat() != tag or len(df) < laenge:
            print(f"{s['ticker']}: keine passenden Kurse bis {tag} – übersprungen")
            continue
        kurs_usd = float(df["close"].iloc[-1])
        stop, ziel = kurs_usd * s["stop"] / s["kurs"], kurs_usd * s["ziel"] / s["kurs"]
        seed = sum(map(ord, s["ticker"] + tag))
        p_zufall, vola = zufallsweg(df["close"].to_numpy(), kurs_usd, stop, ziel, seed=seed)
        spanne20, vola20 = spanne_und_vola(df.tail(TAGE + 1).iloc[1:], start_kurs=float(df["close"].iloc[-TAGE - 1]))
        varianten = {}
        for v in VARIANTEN:
            if nr >= v["max"] or (v["max"] < MAX_SIGNALE and time.time() - t_start > ZEITBUDGET_SEK):
                continue
            varianten[v["name"]] = kronos_variante(predictor_fn(v["modell"]), df, kurs_usd, stop, ziel, seed, v)
        e = {"signal_tag": tag, "ticker": s["ticker"], "strategie": s.get("strategie"), "kurs_usd": round(kurs_usd, 4),
             "stop_abstand": round((stop / kurs_usd - 1) * 100, 2), "ziel_abstand": round((ziel / kurs_usd - 1) * 100, 2),
             "kronos": varianten, "p_ziel_zufall": round(p_zufall, 3), "ziel_chance_bot": s.get("chance"),
             "vola_tag_prozent": round(vola * 100, 2),
             "letzte_20_tage": {"tagesspanne_prozent": round(spanne20, 3), "vola_prozent": round(vola20, 3)},
             "pfade": PFADE, "sekunden": round(time.time() - t0, 1),
             "erstellt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")}
        if probe:
            e["probe"] = True
        log.append(e)
        print(f"{s['ticker']}: Stop {e['stop_abstand']:+.1f} %, Ziel {e['ziel_abstand']:+.1f} % · Zufallsweg Ziel "
              f"zuerst {p_zufall:.0%} · letzte 20 Tage: Spanne {spanne20:.2f} %, Schwankung {vola20:.2f} %")
        for name, v in varianten.items():
            print(f"   {name}: Ziel zuerst {v['p_ziel']:.0%}, Stop zuerst {v['p_stop']:.0%} · Mitte nach 20 Tagen "
                  f"{v['nach_20_tagen_prozent']['mitte']:+.1f} % · Spanne {v['tagesspanne_prozent']:.2f} %, Schwankung "
                  f"{v['vola_prozent']:.2f} % · Kurs über Ø {v['abstand_zum_mittel_prozent']:+.1f} % · {v['sekunden']} s")
    return len(neu)


def liste_vorhersage(daten, liste, predictor_fn=lade_predictor, kurse_fn=kurse, probe=False, t_start=None):
    """Alle Aktien der Watchlist (die Zeilen in daten.json) mit den schnellen Varianten, Stop −2 ATR, Ziel +2 ATR."""
    t_start = t_start or time.time()
    tag = daten["daten_bis"]
    if daten.get("vorlaeufig"):
        return 0
    schon = {(e["signal_tag"], e["ticker"]) for e in liste}
    ticker = [s["ticker"] for s in daten.get("signale", []) if (tag, s["ticker"]) not in schon][:3 if probe else None]
    start, ende = zeitraum(tag)
    varianten = [v for v in VARIANTEN if v["name"] in LISTE_VARIANTEN]
    n = 0
    for t in ticker:
        if time.time() - t_start > LISTE_BUDGET_SEK:
            print(f"Watchlist: Zeitbudget erreicht – {len(ticker) - n} Aktien heute nicht gerechnet.")
            break
        df = kurse_fn(t, start, ende)
        if df is None or df.empty or df.index[-1].date().isoformat() != tag or len(df) < 260:
            print(f"Watchlist {t}: keine passenden Kurse bis {tag} – übersprungen")
            continue
        kurs_usd = float(df["close"].iloc[-1])
        atr = atr_prozent(df)
        stop, ziel = kurs_usd * (1 - LISTE_ATR * atr / 100), kurs_usd * (1 + LISTE_ATR * atr / 100)
        seed = sum(map(ord, t + tag))
        p_zufall, _ = zufallsweg(df["close"].to_numpy(), kurs_usd, stop, ziel, seed=seed)
        spanne20, vola20 = spanne_und_vola(df.tail(TAGE + 1).iloc[1:], start_kurs=float(df["close"].iloc[-TAGE - 1]))
        k = {}
        for v in varianten:
            x = kronos_variante(predictor_fn(v["modell"]), df, kurs_usd, stop, ziel, seed, v, faecher=False)
            k[v["name"]] = {key: x[key] for key in ("p_ziel", "p_stop", "tagesspanne_prozent", "vola_prozent")}
            k[v["name"]]["mitte_20"] = x["nach_20_tagen_prozent"]["mitte"]
        e = {"signal_tag": tag, "ticker": t, "kurs_usd": round(kurs_usd, 4), "atr_prozent": round(atr, 2),
             "stop_abstand": round((stop / kurs_usd - 1) * 100, 2), "ziel_abstand": round((ziel / kurs_usd - 1) * 100, 2),
             "kronos": k, "p_ziel_zufall": round(p_zufall, 3),
             "letzte_20_tage": {"tagesspanne_prozent": round(spanne20, 3), "vola_prozent": round(vola20, 3)}}
        if probe:
            e["probe"] = True
        liste.append(e)
        n += 1
        print(f"Watchlist {t}: ±{LISTE_ATR * atr:.1f} % · Zufallsweg {p_zufall:.0%} · "
              + " · ".join(f"{name} {v['p_ziel']:.0%}/{v['p_stop']:.0%}, Spanne {v['tagesspanne_prozent']:.2f} %"
                           for name, v in k.items()) + f" (letzte 20 T. {spanne20:.2f} %)")
    return n


def auswertung(log, heute, kurse_fn=kurse, verlauf=True):
    n = 0
    for e in log:
        if e.get("probe") or not faellig(e, heute):
            continue
        tag = dt.date.fromisoformat(e["signal_tag"])
        df = kurse_fn(e["ticker"], (tag + dt.timedelta(days=1)).isoformat(), (tag + dt.timedelta(days=50)).isoformat(),
                      roh=True)
        if df is None or len(df) < TAGE:
            continue
        df = df[df.index > pd.Timestamp(tag)].head(TAGE)
        if len(df) < TAGE:
            continue
        k = e["kurs_usd"]
        if abs(df["open"].iloc[0] / k - 1) > 0.5:
            e["ergebnis"], e["hinweis"] = "unklar", "Kurssprung über 50 % (Split?) – nicht gewertet"
            continue
        stop, ziel = k * (1 + e["stop_abstand"] / 100), k * (1 + e["ziel_abstand"] / 100)
        e["ergebnis"], e["tag_ausgang"] = ausgang(df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy(),
                                                  stop, ziel)
        spanne, vola = spanne_und_vola(df, start_kurs=k)
        e["echt"] = {"tagesspanne_prozent": round(spanne, 3), "vola_prozent": round(vola, 3)}
        if verlauf:
            e["echt_verlauf"] = [round((float(c) / k - 1) * 100, 2) for c in df["close"]]
        n += 1
    return n


def de(x, fmt):
    return format(x, fmt).replace(".", ",")


def brier(p, y):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def _bootstrap(fehler_a, fehler_b, gruppen=None, seed=0):
    """Intervall (INTERVALL) des Unterschieds mittlerer Fehler (a − b), wenn man die Signale neu zieht – bei der
    Watchlist die Tage (gruppen), weil Aktien am selben Tag ähnlich laufen."""
    d_alle = np.asarray(fehler_a, float) - np.asarray(fehler_b, float)
    rng = np.random.default_rng(seed)
    if gruppen is None:
        d = [float(np.mean(d_alle[i])) for i in (rng.integers(0, len(d_alle), len(d_alle)) for _ in range(2000))]
    else:
        g = pd.Series(d_alle).groupby(np.asarray(gruppen))
        summe, anzahl = g.sum().to_numpy(), g.size().to_numpy()
        d = [float(summe[i].sum() / anzahl[i].sum()) for i in (rng.integers(0, len(summe), len(summe))
                                                                  for _ in range(2000))]
    return float(np.percentile(d, INTERVALL[0])), float(np.percentile(d, INTERVALL[1]))


def _urteil(n, a, b, hi, minimum=MIN_AUSWERTUNG, einheit="Signale"):
    if n < minimum:
        return f"noch zu wenig {einheit} ({n} von {minimum})"
    return "besser" if a < b and hi < 0 else "nicht besser"


def _rang(a, b):
    """Spearman-Korrelation ohne scipy; None, wenn sie nicht berechnet werden kann."""
    r = pd.Series(a).rank().corr(pd.Series(b).rank()) if len(a) > 2 else np.nan
    return round(float(r), 2) if np.isfinite(r) else None


def teile(log):
    eigene = [e for e in log if not e.get("probe") and "kronos" in e]
    return (eigene, [e for e in eigene if e.get("ergebnis") in ("ziel", "stop", "zeit")],
            [e for e in eigene if "ergebnis" not in e])


ABGELEITET = {"mittel": "Mittel aller Varianten", "mischung": "Mittel ½ + Zufall ½",
              "mittel-geeicht": "Mittel geeicht"}


def _mittel(e, feld):
    w = [v[feld] for v in e["kronos"].values() if v.get(feld) is not None]
    return float(np.mean(w)) if w else None


def p_ziel(e, name):
    """Vorhergesagte Chance „Ziel zuerst“ einer Variante oder abgeleiteten Vorhersage."""
    if name == "mittel":
        return _mittel(e, "p_ziel")
    if name == "mischung":
        m = _mittel(e, "p_ziel")
        return None if m is None else MISCHUNG * m + (1 - MISCHUNG) * e["p_ziel_zufall"]
    return e["kronos"].get(name, {}).get("p_ziel")


def eich_faktoren(fertig):
    """Je Signal der Eich-Faktor für „Mittel geeicht“: Median von (Mittel ÷ echt) über alle Signale, die am Signaltag
    schon ausgewertet waren (Signaltag + 32 Kalendertage), mindestens EICH_MIN – sonst None."""
    basis = sorted(((dt.date.fromisoformat(e["signal_tag"]), _mittel(e, "tagesspanne_prozent") / e["echt"]["tagesspanne_prozent"])
                    for e in fertig if "echt" in e and _mittel(e, "tagesspanne_prozent") and e["echt"]["tagesspanne_prozent"] > 0))
    out = {}
    for e in fertig:
        bis = dt.date.fromisoformat(e["signal_tag"]) - dt.timedelta(days=WARTEN_KALENDERTAGE)
        r = [x for d, x in basis if d <= bis]
        out[id(e)] = float(np.median(r)) if len(r) >= EICH_MIN else None
    return out


def spanne(e, name, faktoren=None):
    if name == "mittel":
        return _mittel(e, "tagesspanne_prozent")
    if name == "mittel-geeicht":
        m, f = _mittel(e, "tagesspanne_prozent"), (faktoren or {}).get(id(e))
        return None if m is None or not f else m / f
    return e["kronos"].get(name, {}).get("tagesspanne_prozent")


def tabellen(log, namen=None, liste=False):
    """Zwischenstand je Variante und abgeleiteter Vorhersage für beide Fragen (Bericht und Webseite rechnen gleich).
    liste=True: Watchlist – Urteil erst ab LISTE_MIN_TAGE Tagen, Bootstrap über Tage, ohne Bot-Formel."""
    _, fertig, _ = teile(log)
    namen = namen or [v["name"] for v in VARIANTEN]
    minimum, einheit = (LISTE_MIN_TAGE, "Tage") if liste else (MIN_AUSWERTUNG, "Signale")
    zahl = (lambda teil: len({e["signal_tag"] for e in teil})) if liste else len  # noqa: E731
    grp = (lambda teil: [e["signal_tag"] for e in teil]) if liste else (lambda teil: None)  # noqa: E731
    y = {id(e): 1 if e["ergebnis"] == "ziel" else 0 for e in fertig}
    faktoren = eich_faktoren(fertig)
    out = {"richtung": [], "schwankung": []}
    for name in namen + ["mittel", "mischung"]:
        teil = [e for e in fertig if p_ziel(e, name) is not None]
        if not teil:
            continue
        fk = [(p_ziel(e, name) - y[id(e)]) ** 2 for e in teil]
        fz = [(e["p_ziel_zufall"] - y[id(e)]) ** 2 for e in teil]
        lo, hi = _bootstrap(fk, fz, grp(teil))
        r = {"variante": name, "n": len(teil), "tage": len({e["signal_tag"] for e in teil}),
             "fehler_kronos": round(float(np.mean(fk)), 4), "fehler_vergleich": round(float(np.mean(fz)), 4),
             "lo": round(lo, 4), "hi": round(hi, 4),
             "chance_kronos": round(float(np.mean([p_ziel(e, name) for e in teil])), 3),
             "wirklich_ziel": round(float(np.mean([y[id(e)] for e in teil])), 3),
             "urteil": _urteil(zahl(teil), np.mean(fk), np.mean(fz), hi, minimum, einheit)}
        mit_bot = [e for e in teil if e.get("ziel_chance_bot") is not None]
        if not liste and mit_bot:
            fk2 = [(p_ziel(e, name) - y[id(e)]) ** 2 for e in mit_bot]
            fb = [(e["ziel_chance_bot"] / 100 - y[id(e)]) ** 2 for e in mit_bot]
            lo2, hi2 = _bootstrap(fk2, fb)
            r.update({"n_bot": len(mit_bot), "fehler_kronos_bot": round(float(np.mean(fk2)), 4),
                      "fehler_bot": round(float(np.mean(fb)), 4), "lo_bot": round(lo2, 4), "hi_bot": round(hi2, 4),
                      "urteil_bot": _urteil(len(mit_bot), np.mean(fk2), np.mean(fb), hi2)})
        out["richtung"].append(r)
    for name in namen + ["mittel", "mittel-geeicht"]:
        teil = [e for e in fertig if "echt" in e and spanne(e, name, faktoren) is not None]
        if not teil:
            continue
        echt = [e["echt"]["tagesspanne_prozent"] for e in teil]
        kr = [spanne(e, name, faktoren) for e in teil]
        fb_basis = [e["letzte_20_tage"]["tagesspanne_prozent"] for e in teil]
        fk = [abs(a - b) for a, b in zip(kr, echt)]
        fb = [abs(a - b) for a, b in zip(fb_basis, echt)]
        lo, hi = _bootstrap(fk, fb, grp(teil))
        out["schwankung"].append({
            "variante": name, "n": len(teil), "tage": len({e["signal_tag"] for e in teil}),
            "fehler_kronos": round(float(np.mean(fk)), 3), "fehler_vergleich": round(float(np.mean(fb)), 3),
            "lo": round(lo, 3), "hi": round(hi, 3),
            "kronos_mittel": round(float(np.mean(kr)), 3), "echt_mittel": round(float(np.mean(echt)), 3),
            "rang_kronos": _rang(kr, echt), "rang_vergleich": _rang(fb_basis, echt),
            "urteil": _urteil(zahl(teil), np.mean(fk), np.mean(fb), hi, minimum, einheit)})
    return out


def webseite(log, liste=()):
    """Daten für den Kronos-Bereich der Übersichtsseite (docs/kronos.json)."""
    eigene, fertig, offen = teile(log)
    l_eigene, l_fertig, l_offen = teile(list(liste))
    weg = {"sekunden", "erstellt", "pfade"}
    signale = []
    for e in sorted(eigene, key=lambda e: (e["signal_tag"], e["ticker"]), reverse=True)[:SEITE_SIGNALE]:
        x = {k: w for k, w in e.items() if k not in weg}
        x["kronos"] = {n: {k: w for k, w in v.items() if k != "sekunden"} for n, v in e["kronos"].items()}
        signale.append(x)
    naechste = min((dt.date.fromisoformat(e["signal_tag"]) + dt.timedelta(days=WARTEN_KALENDERTAGE) for e in offen),
                   default=None)
    return {"stand": dt.date.today().isoformat(), "pfade": PFADE, "tage": TAGE, "min_auswertung": MIN_AUSWERTUNG,
            "varianten": [{"name": v["name"], "modell": v["modell"].split("/")[-1], "rueckblick": v["rueckblick"],
                           "T": v["T"], "nur_erste": v["max"] if v["max"] < MAX_SIGNALE else None} for v in VARIANTEN],
            "zaehler": {"gerechnet": len(eigene), "ausgewertet": len(fertig), "offen": len(offen)},
            "naechste_auswertung": naechste.isoformat() if naechste else None, "intervall": INTERVALL[1] - INTERVALL[0],
            "auswertung": tabellen(log), "signale": signale,
            "liste": {"varianten": LISTE_VARIANTEN, "atr": LISTE_ATR, "min_tage": LISTE_MIN_TAGE,
                      "zaehler": {"gerechnet": len(l_eigene), "ausgewertet": len(l_fertig), "offen": len(l_offen),
                                  "tage": len({e["signal_tag"] for e in l_eigene}),
                                  "tage_ausgewertet": len({e["signal_tag"] for e in l_fertig})},
                      "naechste_auswertung": min((dt.date.fromisoformat(e["signal_tag"]) + dt.timedelta(
                          days=WARTEN_KALENDERTAGE) for e in l_offen), default=dt.date.min).isoformat() if l_offen else None,
                      "auswertung": tabellen(list(liste), LISTE_VARIANTEN, liste=True)}}


def _name(n):
    return ABGELEITET.get(n, n)


def _tabellen_md(T, mit_bot):
    """Markdown-Tabellen für Richtung und Schwankung aus tabellen()."""
    i = INTERVALL[1] - INTERVALL[0]
    z = ["**Richtung: Ziel oder Stop zuerst?** (Fehler = Brier-Wert, kleiner ist besser)", "",
         f"| Vorhersage | Anzahl | Brier Kronos | Brier Zufallsweg | Unterschied ({i}-%-Intervall) | Ø Chance Kronos | "
         "wirklich Ziel zuerst | Urteil gegen Zufallsweg |" + (" Brier Bot-Formel | Urteil gegen Bot-Formel |" if mit_bot else ""),
         "|---|---:|---:|---:|---|---:|---:|---|" + ("---:|---|" if mit_bot else "")]
    for r in T["richtung"]:
        zeile = (f"| {_name(r['variante'])} | {r['n']} | {de(r['fehler_kronos'], '.3f')} | {de(r['fehler_vergleich'], '.3f')} | "
                 f"{de(r['fehler_kronos'] - r['fehler_vergleich'], '+.3f')} ({de(r['lo'], '+.3f')} bis {de(r['hi'], '+.3f')}) | "
                 f"{r['chance_kronos']:.0%} | {r['wirklich_ziel']:.0%} | {r['urteil']} |")
        if mit_bot:
            zeile += (f" {de(r['fehler_bot'], '.3f')} (Kronos {de(r['fehler_kronos_bot'], '.3f')}, {r['n_bot']}) | {r['urteil_bot']} |"
                      if "fehler_bot" in r else " – | – |")
        z.append(zeile)
    z += ["", "**Schwankung: mittlere Tagesspanne der nächsten 20 Tage** (Fehler = mittlere Abweichung; „Rangfolge“ = "
          "Spearman-Korrelation mit der echten Spanne, ohne Urteil)", "",
          f"| Vorhersage | Anzahl | Fehler Kronos | Fehler „letzte 20 Tage“ | Unterschied ({i}-%-Intervall) | Ø Kronos | "
          "Ø echt | Rangfolge Kronos / letzte 20 T. | Urteil |", "|---|---:|---:|---:|---|---:|---:|---:|---|"]
    rang = lambda r: "–" if r is None else de(r, "+.2f")  # noqa: E731
    for r in T["schwankung"]:
        z.append(f"| {_name(r['variante'])} | {r['n']} | {de(r['fehler_kronos'], '.2f')} % | {de(r['fehler_vergleich'], '.2f')} % | "
                 f"{de(r['fehler_kronos'] - r['fehler_vergleich'], '+.2f')} ({de(r['lo'], '+.2f')} bis {de(r['hi'], '+.2f')}) | "
                 f"{de(r['kronos_mittel'], '.2f')} % | {de(r['echt_mittel'], '.2f')} % | "
                 f"{rang(r['rang_kronos'])} / {rang(r['rang_vergleich'])} | {r['urteil']} |")
    return z + [""]


def bericht(log, liste=()):
    eigene, fertig, offen = teile(log)
    l_eigene, l_fertig, l_offen = teile(list(liste))
    namen = [v["name"] for v in VARIANTEN]
    i = INTERVALL[1] - INTERVALL[0]
    z = ["# 🔮 Kronos-Versuch (nach vorne)", "",
         f"Stand {dt.date.today():%d.%m.%Y} · {PFADE} Zukünfte je Signal und Variante, {TAGE} Handelstage. Varianten: "
         + "; ".join(f"{v['name']} ({v['modell'].split('/')[-1]}, Rückblick {v['rueckblick']}, Temperatur "
                     f"{de(v['T'], '.1f')}{', nur 3 Signale am Tag' if v['max'] < MAX_SIGNALE else ''})" for v in VARIANTEN)
         + ". Dazu abgeleitet: Mittel aller Varianten, Mittel ½ + Zufall ½, Mittel geeicht (Schwankung). Nur eine "
         "Messung – der Bot kauft nicht danach.", "",
         "**Fragen:** (1) Sagt Kronos besser voraus, ob zuerst das Ziel oder zuerst der Stop kommt, als ein Zufallsweg "
         "ohne Richtung – und als die Ziel-Chance, die der Bot schon anzeigt? (2) Sagt Kronos die Schwankung der nächsten "
         "20 Tage besser voraus, als einfach die letzten 20 Tage fortzuschreiben?", "",
         f"**Vorher festgelegt:** Ab {MIN_AUSWERTUNG} ausgewerteten Signalen je Vorhersage (Watchlist: ab "
         f"{LISTE_MIN_TAGE} ausgewerteten Tagen) gilt sie als besser, wenn ihr Fehler kleiner ist und das {i}-%-"
         "Bootstrap-Intervall des Unterschieds ganz unter 0 liegt. Es sind viele Vergleiche – deshalb die strenge Hürde "
         "(seit 09.11. abends, vorher 90 %, festgelegt bevor ein Signal ausgewertet war). Die Bot-Formel rechnet ohne "
         "Stop und liegt deshalb eher zu hoch.", "",
         "**Schon in den Probeläufen sichtbar (08./09.11.):** Kronos zieht den Kurs stark zum Durchschnitt des Rückblicks "
         "zurück (oft fast alle Zukünfte in dieselbe Richtung), und seine Tageskerzen sind größer als echte. Mehr Zufall "
         "(T15) macht die Aussagen vorsichtiger.", "",
         "## 1. Kauf-Signale des Bots", ""]
    if fertig:
        z += _tabellen_md(tabellen(log), mit_bot=True)
    else:
        z += ["Noch keine Signale ausgewertet (das geht frühestens 20 Handelstage nach dem Signal).", ""]
    z += [f"## 2. Alle Aktien der Watchlist täglich ({', '.join(LISTE_VARIANTEN)}, Stop −{de(LISTE_ATR, '.0f')} ATR, "
          f"Ziel +{de(LISTE_ATR, '.0f')} ATR)", "",
          f"Gerechnet: {len(l_eigene)} an {len({e['signal_tag'] for e in l_eigene})} Tagen · ausgewertet: "
          f"{len(l_fertig)} an {len({e['signal_tag'] for e in l_fertig})} Tagen · offen: {len(l_offen)}. "
          "Aktien am selben Tag laufen ähnlich – deshalb zählt die Zahl der Tage, und das Intervall zieht ganze Tage.", ""]
    if l_fertig:
        z += _tabellen_md(tabellen(list(liste), LISTE_VARIANTEN, liste=True), mit_bot=False)
    z += ["## Alle Kauf-Signale", "", "| Signaltag | Aktie | Stop / Ziel | "
          + " | ".join(f"{n}: Ziel / Stop · Mitte 20 T." for n in namen) + " | Zufallsweg Ziel | Bot-Formel | Ergebnis |",
          "|---|---|---|" + "---|" * len(namen) + "---:|---:|---|"]
    for e in sorted(eigene, key=lambda e: (e["signal_tag"], e["ticker"]), reverse=True):
        zellen = []
        for n in namen:
            v = e["kronos"].get(n)
            zellen.append(f"{v['p_ziel']:.0%} / {v['p_stop']:.0%} · {de(v['nach_20_tagen_prozent']['mitte'], '+.1f')} %"
                          if v else "–")
        bot = "–" if e.get("ziel_chance_bot") is None else f"{e['ziel_chance_bot']:.0f} %"
        z.append(f"| {e['signal_tag']} | {e['ticker']} | {de(e['stop_abstand'], '+.1f')} / "
                 f"{de(e['ziel_abstand'], '+.1f')} % | " + " | ".join(zellen)
                 + f" | {e['p_ziel_zufall']:.0%} | {bot} | {e.get('ergebnis', 'offen')} |")
    z += ["", f"Offen: {len(offen)} Signale warten auf ihre 20 Handelstage. Watchlist-Einzelwerte: "
          "`forschung/kronos_liste_log.json`. Kronos-Code: `forschung/kronos_modell/` (MIT-Lizenz). Hintergrund: "
          "`gehirn/Notizen/Wissen – Kronos (KI-Zukunftsfächer).md`. Simulation, keine Anlageberatung."]
    return "\n".join(z) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--modus", choices=["pruefen", "lauf", "seite"], default="lauf")
    p.add_argument("--probe", action="store_true", help="Probelauf: nichts im Repo speichern")
    p.add_argument("--ausgabe", default=None, help="Ordner für Logs, Bericht und Seiten-Daten (Standard: im Repo)")
    a = p.parse_args(argv)
    log_datei, bericht_datei, seite_datei, liste_datei = pfade(a.ausgabe)
    log, liste = lies_log(pfade()[0]), lies_log(pfade()[3])  # immer vom gespeicherten Stand ausgehen
    with open(DATEN, encoding="utf-8") as f:
        daten = json.load(f)
    heute = dt.date.today()
    if a.modus == "pruefen":
        tag, frisch = daten["daten_bis"], not daten.get("vorlaeufig")
        neu = frisch and any((tag, s["ticker"]) not in {(e["signal_tag"], e["ticker"]) for e in log}
                             for s in kauf_signale(daten))
        liste_neu = frisch and bool(daten.get("signale")) and tag not in {e["signal_tag"] for e in liste}
        noetig = (neu or liste_neu or a.probe
                  or any(faellig(e, heute) for e in log + liste if not e.get("probe")))
        print(f"noetig={'true' if noetig else 'false'}")
        return
    if a.modus == "seite":
        schreibe(bericht_datei, bericht(log, liste))
        schreibe(seite_datei, webseite(log, liste))
        return
    t_start = time.time()
    n_neu = vorhersage(daten, log, probe=a.probe, t_start=t_start)
    n_liste = liste_vorhersage(daten, liste, probe=a.probe, t_start=t_start)
    n_aus = auswertung(log, heute)
    n_l_aus = auswertung(liste, heute, verlauf=False)
    schreibe(log_datei, log)
    schreibe(liste_datei, liste)
    schreibe(bericht_datei, bericht(log, liste))
    schreibe(seite_datei, webseite(log, liste))
    print(f"Fertig: {n_neu} neue Signale, {n_liste} Watchlist-Aktien, {n_aus} Signale und {n_l_aus} Watchlist-Werte "
          f"ausgewertet ({(time.time() - t_start) / 60:.0f} Minuten).")
    modell_stand_melden()


if __name__ == "__main__":
    main()
