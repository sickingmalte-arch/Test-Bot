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
des Vergleichs liegt und das 90-%-Bootstrap-Intervall des Unterschieds ganz unter 0 liegt. Sonst: nicht besser.
4 Varianten × 2 Fragen – bei so vielen Vergleichen kann einer zufällig gut aussehen, das steht im Bericht dabei.

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
PFADE = int(os.environ.get("KRONOS_PFADE", "50"))
MAX_SIGNALE = int(os.environ.get("KRONOS_MAX_SIGNALE", "8"))
ZEITBUDGET_SEK = 60 * int(os.environ.get("KRONOS_ZEITBUDGET_MIN", "80"))  # danach keine langsamen Varianten mehr
VARIANTEN = [
    {"name": "small-256", "modell": "NeoQuasar/Kronos-small", "rueckblick": 256, "T": 1.0, "top_p": 0.9, "max": 8},
    {"name": "small-64", "modell": "NeoQuasar/Kronos-small", "rueckblick": 64, "T": 1.0, "top_p": 0.9, "max": 8},
    {"name": "small-64-T15", "modell": "NeoQuasar/Kronos-small", "rueckblick": 64, "T": 1.5, "top_p": 1.0, "max": 8},
    {"name": "base-256", "modell": "NeoQuasar/Kronos-base", "rueckblick": 256, "T": 1.0, "top_p": 0.9, "max": 3},
]
_PREDICTOREN = {}


# ---------------------------------------------------------------- Dateien
def pfade(ausgabe=None):
    """Log, Bericht und Webseiten-Daten – im Repo oder (GitHub-Lauf ohne Schreibrechte) in einem eigenen Ordner."""
    if ausgabe:
        return tuple(os.path.join(ausgabe, n) for n in ("kronos_log.json", "kronos_ergebnis.md", "kronos.json"))
    return (os.path.join(HIER, "kronos_log.json"), os.path.join(HIER, "kronos_ergebnis.md"),
            os.path.join(WURZEL, "docs", "kronos.json"))


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
        tok = KronosTokenizer.from_pretrained(TOKENIZER)
        _PREDICTOREN[modell] = KronosPredictor(Kronos.from_pretrained(modell), tok, device="cpu", max_context=512)
    return _PREDICTOREN[modell]


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


def vorhersage(daten, log, predictor_fn=lade_predictor, kurse_fn=kurse, probe=False):
    t_start = time.time()
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
    start = (dt.date.fromisoformat(tag) - dt.timedelta(days=700)).isoformat()
    ende = (dt.date.fromisoformat(tag) + dt.timedelta(days=1)).isoformat()
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
            t1 = time.time()
            wege = kronos_zukuenfte(predictor_fn(v["modell"]), df, PFADE, seed, v["rueckblick"], v["T"], v["top_p"])
            erg = [ausgang(w["open"].to_numpy(), w["high"].to_numpy(), w["low"].to_numpy(), stop, ziel)[0] for w in wege]
            verlauf = np.array([w["close"].to_numpy(float) / kurs_usd - 1 for w in wege]) * 100  # Zukünfte × Tage
            ende20 = verlauf[:, -1]
            sv = np.array([spanne_und_vola(w, start_kurs=kurs_usd) for w in wege])
            varianten[v["name"]] = {
                "p_ziel": round(erg.count("ziel") / len(erg), 3), "p_stop": round(erg.count("stop") / len(erg), 3),
                "nach_20_tagen_prozent": {"q10": round(float(np.percentile(ende20, 10)), 2),
                                          "mitte": round(float(np.median(ende20)), 2),
                                          "q90": round(float(np.percentile(ende20, 90)), 2)},
                "tagesspanne_prozent": round(float(sv[:, 0].mean()), 3), "vola_prozent": round(float(sv[:, 1].mean()), 3),
                "abstand_zum_mittel_prozent": round((kurs_usd / float(df["close"].tail(v["rueckblick"]).mean()) - 1) * 100, 1),
                "faecher": {k: [round(float(x), 2) for x in np.percentile(verlauf, q, axis=0)]
                            for k, q in (("q10", 10), ("mitte", 50), ("q90", 90))},
                "sekunden": round(time.time() - t1, 1)}
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


def auswertung(log, heute, kurse_fn=kurse):
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
        k = e["kurs_usd"]
        if abs(df["open"].iloc[0] / k - 1) > 0.5:
            e["ergebnis"], e["hinweis"] = "unklar", "Kurssprung über 50 % (Split?) – nicht gewertet"
            continue
        stop, ziel = k * (1 + e["stop_abstand"] / 100), k * (1 + e["ziel_abstand"] / 100)
        e["ergebnis"], e["tag_ausgang"] = ausgang(df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy(),
                                                  stop, ziel)
        spanne, vola = spanne_und_vola(df, start_kurs=k)
        e["echt"] = {"tagesspanne_prozent": round(spanne, 3), "vola_prozent": round(vola, 3)}
        e["echt_verlauf"] = [round((float(c) / k - 1) * 100, 2) for c in df["close"]]
        n += 1
    return n


def de(x, fmt):
    return format(x, fmt).replace(".", ",")


def brier(p, y):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def _bootstrap(fehler_a, fehler_b, seed=0):
    """90-%-Intervall des Unterschieds mittlerer Fehler (a − b), wenn man die Signale neu zieht."""
    a, b = np.asarray(fehler_a, float), np.asarray(fehler_b, float)
    rng = np.random.default_rng(seed)
    d = [float(np.mean(a[i] - b[i])) for i in (rng.integers(0, len(a), len(a)) for _ in range(2000))]
    return float(np.percentile(d, 5)), float(np.percentile(d, 95))


def _urteil(n, a, b, hi):
    if n < MIN_AUSWERTUNG:
        return f"noch zu wenig Signale ({n} von {MIN_AUSWERTUNG})"
    return "besser" if a < b and hi < 0 else "nicht besser"


def _rang(a, b):
    """Spearman-Korrelation ohne scipy; None, wenn sie nicht berechnet werden kann."""
    r = pd.Series(a).rank().corr(pd.Series(b).rank()) if len(a) > 2 else np.nan
    return round(float(r), 2) if np.isfinite(r) else None


def teile(log):
    eigene = [e for e in log if not e.get("probe") and "kronos" in e]
    return (eigene, [e for e in eigene if e.get("ergebnis") in ("ziel", "stop", "zeit")],
            [e for e in eigene if "ergebnis" not in e])


def tabellen(log):
    """Zwischenstand je Variante für beide Fragen (Bericht und Webseite rechnen damit gleich)."""
    _, fertig, _ = teile(log)
    y = {id(e): 1 if e["ergebnis"] == "ziel" else 0 for e in fertig}
    out = {"richtung": [], "schwankung": []}
    for v in VARIANTEN:
        name = v["name"]
        teil = [e for e in fertig if name in e["kronos"]]
        if teil:
            fk = [(e["kronos"][name]["p_ziel"] - y[id(e)]) ** 2 for e in teil]
            fz = [(e["p_ziel_zufall"] - y[id(e)]) ** 2 for e in teil]
            lo, hi = _bootstrap(fk, fz)
            out["richtung"].append({
                "variante": name, "n": len(teil), "fehler_kronos": round(float(np.mean(fk)), 4),
                "fehler_vergleich": round(float(np.mean(fz)), 4), "lo": round(lo, 4), "hi": round(hi, 4),
                "chance_kronos": round(float(np.mean([e["kronos"][name]["p_ziel"] for e in teil])), 3),
                "wirklich_ziel": round(float(np.mean([y[id(e)] for e in teil])), 3),
                "urteil": _urteil(len(teil), np.mean(fk), np.mean(fz), hi)})
        teil = [e for e in teil if "echt" in e and "tagesspanne_prozent" in e["kronos"][name]]
        if teil:
            echt = [e["echt"]["tagesspanne_prozent"] for e in teil]
            kr = [e["kronos"][name]["tagesspanne_prozent"] for e in teil]
            fb_basis = [e["letzte_20_tage"]["tagesspanne_prozent"] for e in teil]
            fk = [abs(a - b) for a, b in zip(kr, echt)]
            fb = [abs(a - b) for a, b in zip(fb_basis, echt)]
            lo, hi = _bootstrap(fk, fb)
            out["schwankung"].append({
                "variante": name, "n": len(teil), "fehler_kronos": round(float(np.mean(fk)), 3),
                "fehler_vergleich": round(float(np.mean(fb)), 3), "lo": round(lo, 3), "hi": round(hi, 3),
                "kronos_mittel": round(float(np.mean(kr)), 3), "echt_mittel": round(float(np.mean(echt)), 3),
                "rang_kronos": _rang(kr, echt), "rang_vergleich": _rang(fb_basis, echt),
                "urteil": _urteil(len(teil), np.mean(fk), np.mean(fb), hi)})
    return out


def webseite(log):
    """Daten für den Kronos-Bereich der Übersichtsseite (docs/kronos.json)."""
    eigene, fertig, offen = teile(log)
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
            "naechste_auswertung": naechste.isoformat() if naechste else None,
            "auswertung": tabellen(log), "signale": signale}


def bericht(log):
    eigene, fertig, offen = teile(log)
    namen = [v["name"] for v in VARIANTEN]
    z = ["# 🔮 Kronos-Versuch (nach vorne)", "",
         f"Stand {dt.date.today():%d.%m.%Y} · {PFADE} Zukünfte je Signal und Variante, {TAGE} Handelstage. Varianten: "
         + "; ".join(f"{v['name']} ({v['modell'].split('/')[-1]}, Rückblick {v['rueckblick']}, Temperatur "
                     f"{de(v['T'], '.1f')}{', nur 3 Signale am Tag' if v['max'] < MAX_SIGNALE else ''})" for v in VARIANTEN)
         + ". Nur eine Messung – der Bot kauft nicht danach.", "",
         "**Fragen:** (1) Sagt Kronos besser voraus, ob zuerst das Ziel oder zuerst der Stop kommt, als ein Zufallsweg "
         "ohne Richtung? (2) Sagt Kronos die Schwankung der nächsten 20 Tage besser voraus, als einfach die letzten 20 "
         "Tage fortzuschreiben?", "",
         f"**Vorher festgelegt:** Ab {MIN_AUSWERTUNG} ausgewerteten Signalen je Variante gilt sie als besser, wenn ihr "
         "Fehler kleiner ist und das 90-%-Bootstrap-Intervall des Unterschieds ganz unter 0 liegt. 4 Varianten × 2 "
         "Fragen = 8 Vergleiche – einer davon kann zufällig gut aussehen.", "",
         "**Schon in den Probeläufen sichtbar (08.11.):** Kronos zieht den Kurs stark zum Durchschnitt des Rückblicks "
         "zurück (oft alle 50 Zukünfte in dieselbe Richtung), und seine Tageskerzen sind 1,2- bis 1,7-mal so groß wie "
         "echte.", ""]
    if fertig:
        T = tabellen(log)
        z += ["## 1. Richtung: Ziel oder Stop zuerst?", "",
              "| Variante | Signale | Brier Kronos | Brier Zufallsweg | Unterschied (90-%-Intervall) | Ø Chance Kronos | "
              "wirklich Ziel zuerst | Urteil |", "|---|---:|---:|---:|---|---:|---:|---|"]
        for r in T["richtung"]:
            z.append(f"| {r['variante']} | {r['n']} | {de(r['fehler_kronos'], '.3f')} | {de(r['fehler_vergleich'], '.3f')} | "
                     f"{de(r['fehler_kronos'] - r['fehler_vergleich'], '+.3f')} ({de(r['lo'], '+.3f')} bis "
                     f"{de(r['hi'], '+.3f')}) | {r['chance_kronos']:.0%} | {r['wirklich_ziel']:.0%} | {r['urteil']} |")
        z += ["", "## 2. Schwankung: mittlere Tagesspanne der nächsten 20 Tage", "",
              "Zusatz ohne Urteil: „Rangfolge“ = Spearman-Korrelation mit der echten Spanne – erkennt Kronos wenigstens, "
              "welche Aktien unruhiger werden, auch wenn seine Kerzen zu groß sind?", "",
              "| Variante | Signale | Fehler Kronos | Fehler „letzte 20 Tage“ | Unterschied (90-%-Intervall) | Ø Kronos | "
              "Ø echt | Rangfolge Kronos / letzte 20 T. | Urteil |", "|---|---:|---:|---:|---|---:|---:|---:|---|"]
        rang = lambda r: "–" if r is None else de(r, "+.2f")  # noqa: E731
        for r in T["schwankung"]:
            z.append(f"| {r['variante']} | {r['n']} | {de(r['fehler_kronos'], '.2f')} % | {de(r['fehler_vergleich'], '.2f')} % | "
                     f"{de(r['fehler_kronos'] - r['fehler_vergleich'], '+.2f')} ({de(r['lo'], '+.2f')} bis "
                     f"{de(r['hi'], '+.2f')}) | {de(r['kronos_mittel'], '.2f')} % | {de(r['echt_mittel'], '.2f')} % | "
                     f"{rang(r['rang_kronos'])} / {rang(r['rang_vergleich'])} | {r['urteil']} |")
        z.append("")
    else:
        z += ["**Ergebnis:** noch keine Signale ausgewertet (das geht frühestens 20 Handelstage nach dem Signal).", ""]
    z += ["## Alle Signale", "", "| Signaltag | Aktie | Stop / Ziel | "
          + " | ".join(f"{n}: Ziel / Stop · Mitte 20 T." for n in namen) + " | Zufallsweg Ziel | Ergebnis |",
          "|---|---|---|" + "---|" * len(namen) + "---:|---|"]
    for e in sorted(eigene, key=lambda e: (e["signal_tag"], e["ticker"]), reverse=True):
        zellen = []
        for n in namen:
            v = e["kronos"].get(n)
            zellen.append(f"{v['p_ziel']:.0%} / {v['p_stop']:.0%} · {de(v['nach_20_tagen_prozent']['mitte'], '+.1f')} %"
                          if v else "–")
        z.append(f"| {e['signal_tag']} | {e['ticker']} | {de(e['stop_abstand'], '+.1f')} / "
                 f"{de(e['ziel_abstand'], '+.1f')} % | " + " | ".join(zellen)
                 + f" | {e['p_ziel_zufall']:.0%} | {e.get('ergebnis', 'offen')} |")
    z += ["", f"Offen: {len(offen)} Signale warten auf ihre 20 Handelstage. Kronos-Code: `forschung/kronos_modell/` "
          "(MIT-Lizenz). Hintergrund: `gehirn/Notizen/Wissen – Kronos (KI-Zukunftsfächer).md`. Simulation, keine "
          "Anlageberatung."]
    return "\n".join(z) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--modus", choices=["pruefen", "lauf", "seite"], default="lauf")
    p.add_argument("--probe", action="store_true", help="Probelauf: nichts im Repo speichern")
    p.add_argument("--ausgabe", default=None, help="Ordner für Log und Bericht (Standard: forschung/)")
    a = p.parse_args(argv)
    log_datei, bericht_datei, seite_datei = pfade(a.ausgabe)
    log = lies_log(pfade()[0])  # immer vom gespeicherten Log ausgehen
    with open(DATEN, encoding="utf-8") as f:
        daten = json.load(f)
    heute = dt.date.today()
    if a.modus == "pruefen":
        neu = [s for s in kauf_signale(daten) if (daten["daten_bis"], s["ticker"]) not in
               {(e["signal_tag"], e["ticker"]) for e in log}] and not daten.get("vorlaeufig")
        noetig = bool(neu) or any(faellig(e, heute) for e in log if not e.get("probe")) or a.probe
        print(f"noetig={'true' if noetig else 'false'}")
        return
    if a.modus == "seite":
        schreibe(bericht_datei, bericht(log))
        schreibe(seite_datei, webseite(log))
        return
    n_neu = vorhersage(daten, log, probe=a.probe)
    n_aus = auswertung(log, heute)
    schreibe(log_datei, log)
    schreibe(bericht_datei, bericht(log))
    schreibe(seite_datei, webseite(log))
    print(f"Fertig: {n_neu} neue Signale, {n_aus} ausgewertet.")


if __name__ == "__main__":
    main()
