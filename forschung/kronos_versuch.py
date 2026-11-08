"""Kronos-Versuch nach vorne (Wunsch des Nutzers vom 08.11.2026) – nur eine Messung, der Bot kauft nicht danach.

Kronos (github.com/shiyu-coder/Kronos, AAAI 2026) ist eine KI, die mit über 12 Milliarden Kerzen von 45 Börsen
trainiert wurde und viele mögliche Zukünfte eines Kursverlaufs ausrechnet. Ein Rückblick wäre unehrlich, weil das
Modell die Kurse von 2010–2026 im Training schon gesehen haben kann. Deshalb nur NACH VORNE:

- Jeden Abend nach dem Bot-Lauf: Für jedes neue Kauf-Signal rechnet Kronos-small 50 Zukünfte über 20 Handelstage
  (so lange hält der Bot höchstens) aus den letzten 256 Tageskerzen. Gezählt wird, wie viele Zukünfte zuerst das Ziel
  erreichen und wie viele zuerst den Stop (am selben Tag beides: Stop zuerst – wie im Bot).
- Vergleich: dieselbe Frage mit einem Zufallsweg (Brownsche Bewegung ohne Richtung, Schwankung der letzten 250 Tage),
  also die einfache „Formel“. Kronos ist nur nützlich, wenn es besser vorhersagt als dieser Zufallsweg.
- Nach 20 Handelstagen wird mit den echten Kursen nachgesehen, was wirklich zuerst kam.

Vorher festgelegt (zählt erst ab 30 ausgewerteten Signalen): Kronos ist besser, wenn sein Brier-Wert (mittlerer
quadratischer Fehler der Wahrscheinlichkeit „Ziel vor Stop“, kleiner = besser) unter dem des Zufallswegs liegt und
das 90-%-Bootstrap-Intervall des Unterschieds ganz unter 0 liegt. Sonst: nicht besser.

Aufruf: python forschung/kronos_versuch.py --modus pruefen   (nur: gibt es etwas zu tun? für GitHub Actions)
        python forschung/kronos_versuch.py --modus lauf [--probe] [--ausgabe ordner]"""
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
MODELL = os.environ.get("KRONOS_MODELL", "NeoQuasar/Kronos-small")
TOKENIZER = os.environ.get("KRONOS_TOKENIZER", "NeoQuasar/Kronos-Tokenizer-base")
PFADE = int(os.environ.get("KRONOS_PFADE", "50"))
RUECKBLICK = int(os.environ.get("KRONOS_RUECKBLICK", "256"))
MAX_SIGNALE = int(os.environ.get("KRONOS_MAX_SIGNALE", "8"))


# ---------------------------------------------------------------- Dateien
def pfade(ausgabe=None):
    ordner = ausgabe or HIER
    return os.path.join(ordner, "kronos_log.json"), os.path.join(ordner, "kronos_ergebnis.md")


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


def lade_predictor():
    sys.path.insert(0, os.path.join(HIER, "kronos_modell"))
    import torch  # noqa: F401  (erst hier – der Bot braucht torch nicht)
    from model import Kronos, KronosPredictor, KronosTokenizer
    tok = KronosTokenizer.from_pretrained(TOKENIZER)
    mod = Kronos.from_pretrained(MODELL)
    return KronosPredictor(mod, tok, device="cpu", max_context=512)


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


def kronos_zukuenfte(predictor, df, n, seed):
    """n einzelne Zukünfte (Kronos mittelt mehrere Proben sonst zu einem Pfad – deshalb n Kopien mit je 1 Probe)."""
    import torch
    torch.manual_seed(seed)
    x = df.tail(RUECKBLICK)
    x_df = x[["open", "high", "low", "close", "volume"]].reset_index(drop=True).astype(float)
    x_ts = pd.Series(x.index)
    y_ts = pd.Series(pd.bdate_range(pd.Timestamp(x.index[-1]) + pd.DateOffset(days=1), periods=TAGE))
    return predictor.predict_batch([x_df] * n, [x_ts] * n, [y_ts] * n, pred_len=TAGE, T=1.0, top_p=0.9,
                                   sample_count=1, verbose=False)


def vorhersage(daten, log, predictor_fn=lade_predictor, kurse_fn=kurse, probe=False):
    tag = daten["daten_bis"]
    if daten.get("vorlaeufig"):
        print("Daten noch vorläufig – nichts zu tun.")
        return 0
    sigs = kauf_signale(daten)
    if probe and not sigs:  # Probelauf ohne Signal: zwei Aktien mit ±5 % (nur zum Messen der Rechenzeit)
        sigs = [{"ticker": s["ticker"], "strategie": "Probe ±5 %", "kurs": 1.0, "stop": 0.95, "ziel": 1.05,
                 "chance": None} for s in daten.get("signale", [])[:2]]
    schon = {(e["signal_tag"], e["ticker"]) for e in log}
    neu = [s for s in sigs if (tag, s["ticker"]) not in schon][:MAX_SIGNALE]
    if not neu:
        print(f"Signale vom {tag}: nichts Neues.")
        return 0
    predictor = predictor_fn()
    start = (dt.date.fromisoformat(tag) - dt.timedelta(days=700)).isoformat()
    ende = (dt.date.fromisoformat(tag) + dt.timedelta(days=1)).isoformat()
    for s in neu:
        t0 = time.time()
        df = kurse_fn(s["ticker"], start, ende)
        if df is None or df.empty or df.index[-1].date().isoformat() != tag or len(df) < RUECKBLICK:
            print(f"{s['ticker']}: keine passenden Kurse bis {tag} – übersprungen")
            continue
        kurs_usd = float(df["close"].iloc[-1])
        stop, ziel = kurs_usd * s["stop"] / s["kurs"], kurs_usd * s["ziel"] / s["kurs"]
        seed = sum(map(ord, s["ticker"] + tag))
        wege = kronos_zukuenfte(predictor, df, PFADE, seed)
        erg = [ausgang(w["open"].to_numpy(), w["high"].to_numpy(), w["low"].to_numpy(), stop, ziel)[0] for w in wege]
        ende20 = np.array([w["close"].iloc[-1] / kurs_usd - 1 for w in wege]) * 100
        p_zufall, vola = zufallsweg(df["close"].to_numpy(), kurs_usd, stop, ziel, seed=seed)
        e = {"signal_tag": tag, "ticker": s["ticker"], "strategie": s.get("strategie"), "kurs_usd": round(kurs_usd, 4),
             "stop_abstand": round((stop / kurs_usd - 1) * 100, 2), "ziel_abstand": round((ziel / kurs_usd - 1) * 100, 2),
             "p_ziel_kronos": round(erg.count("ziel") / len(erg), 3), "p_stop_kronos": round(erg.count("stop") / len(erg), 3),
             "p_ziel_zufall": round(p_zufall, 3), "ziel_chance_bot": s.get("chance"),
             "kronos_20t_prozent": {"q10": round(float(np.percentile(ende20, 10)), 2),
                                    "mitte": round(float(np.median(ende20)), 2),
                                    "q90": round(float(np.percentile(ende20, 90)), 2)},
             "vola_tag_prozent": round(vola * 100, 2), "modell": MODELL, "pfade": len(erg), "rueckblick": RUECKBLICK,
             "sekunden": round(time.time() - t0, 1), "erstellt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")}
        if probe:
            e["probe"] = True
        log.append(e)
        print(f"{s['ticker']}: Kronos Ziel zuerst {e['p_ziel_kronos']:.0%}, Stop zuerst {e['p_stop_kronos']:.0%} · "
              f"Zufallsweg Ziel zuerst {p_zufall:.0%} · {e['sekunden']} s")
        # Prüfung der Kerzen: Spanne (Hoch−Tief) der Kronos-Zukünfte gegen die echten letzten 60 Tage, Richtung
        spanne_k = float(np.mean([((w["high"] - w["low"]) / w["close"]).mean() for w in wege])) * 100
        spanne_echt = float(((df["high"] - df["low"]) / df["close"]).tail(60).mean()) * 100
        tag1 = float(np.mean([w["close"].iloc[0] / kurs_usd - 1 for w in wege])) * 100
        e["pruefung"] = {"spanne_kronos_prozent": round(spanne_k, 2), "spanne_echt_prozent": round(spanne_echt, 2),
                         "tag1_schnitt_prozent": round(tag1, 2),
                         "abstand_mittel_rueckblick_prozent": round((kurs_usd / float(df["close"].tail(RUECKBLICK).mean()) - 1) * 100, 1)}
        print(f"   Stop {e['stop_abstand']:+.1f} %, Ziel {e['ziel_abstand']:+.1f} % · Kronos nach 20 Tagen "
              f"{e['kronos_20t_prozent']} · Tagesspanne Kronos {spanne_k:.2f} % / echt {spanne_echt:.2f} % · "
              f"Tag 1 Ø {tag1:+.2f} % · Kurs über Ø der {RUECKBLICK} Tage {e['pruefung']['abstand_mittel_rueckblick_prozent']:+.1f} %")
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
        stop, ziel = k * (1 + e["stop_abstand"] / 100), k * (1 + e["ziel_abstand"] / 100)
        if abs(df["open"].iloc[0] / k - 1) > 0.5:
            e["ergebnis"], e["hinweis"] = "unklar", "Kurssprung über 50 % (Split?) – nicht gewertet"
            continue
        e["ergebnis"], e["tag_ausgang"] = ausgang(df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy(),
                                                  stop, ziel)
        n += 1
    return n


def de(x, fmt):
    return format(x, fmt).replace(".", ",")


def brier(p, y):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def bericht(log):
    fertig = [e for e in log if not e.get("probe") and e.get("ergebnis") in ("ziel", "stop", "zeit")]
    offen = [e for e in log if not e.get("probe") and "ergebnis" not in e]
    z = ["# 🔮 Kronos-Versuch (nach vorne)", "",
         f"Stand {dt.date.today():%d.%m.%Y} · Modell {MODELL}, {PFADE} Zukünfte je Signal, {TAGE} Handelstage, "
         f"Rückblick {RUECKBLICK} Tageskerzen. Nur eine Messung – der Bot kauft nicht danach.", "",
         "**Frage:** Sagt Kronos besser voraus, ob ein Kauf-Signal zuerst das Ziel oder zuerst den Stop erreicht, als "
         "ein Zufallsweg ohne Richtung (die einfache Formel)?", "",
         f"**Vorher festgelegt:** Ab {MIN_AUSWERTUNG} ausgewerteten Signalen gilt Kronos als besser, wenn sein Brier-Wert "
         "kleiner ist als der des Zufallswegs und das 90-%-Bootstrap-Intervall des Unterschieds ganz unter 0 liegt.", ""]
    if fertig:
        y = [1 if e["ergebnis"] == "ziel" else 0 for e in fertig]
        bk, bz = brier([e["p_ziel_kronos"] for e in fertig], y), brier([e["p_ziel_zufall"] for e in fertig], y)
        rng = np.random.default_rng(0)
        diffs = []
        for _ in range(2000):
            idx = rng.integers(0, len(fertig), len(fertig))
            diffs.append(brier([fertig[i]["p_ziel_kronos"] for i in idx], [y[i] for i in idx])
                         - brier([fertig[i]["p_ziel_zufall"] for i in idx], [y[i] for i in idx]))
        lo, hi = np.percentile(diffs, [5, 95])
        if len(fertig) < MIN_AUSWERTUNG:
            urteil = f"noch zu wenig Signale ({len(fertig)} von {MIN_AUSWERTUNG}) – noch keine Aussage"
        elif bk < bz and hi < 0:
            urteil = "Kronos sagt besser voraus als der Zufallsweg"
        else:
            urteil = "Kronos ist nicht besser als der Zufallsweg"
        z += [f"**Ergebnis:** {urteil}", "", "| | Kronos | Zufallsweg |", "|---|---:|---:|",
              f"| Brier-Wert (kleiner = besser) | {de(bk, '.3f')} | {de(bz, '.3f')} |",
              f"| Ø vorhergesagte Chance „Ziel zuerst“ | {np.mean([e['p_ziel_kronos'] for e in fertig]):.0%} | "
              f"{np.mean([e['p_ziel_zufall'] for e in fertig]):.0%} |",
              f"| Wirklich Ziel zuerst | {np.mean(y):.0%} | {np.mean(y):.0%} |", "",
              f"Unterschied Kronos − Zufallsweg: {de(bk - bz, '+.3f')}, 90-%-Intervall {de(lo, '+.3f')} bis "
              f"{de(hi, '+.3f')} ({len(fertig)} Signale).", ""]
    else:
        z += ["**Ergebnis:** noch keine Signale ausgewertet (das geht frühestens 20 Handelstage nach dem Signal).", ""]
    z += ["## Alle Signale", "", "| Signaltag | Aktie | Strategie | Kronos: Ziel / Stop zuerst | Zufallsweg: Ziel zuerst "
          "| Kronos in 20 Tagen (10 % / Mitte / 90 %) | Ergebnis |", "|---|---|---|---:|---:|---|---|"]
    for e in sorted((e for e in log if not e.get("probe")), key=lambda e: (e["signal_tag"], e["ticker"]), reverse=True):
        q = e["kronos_20t_prozent"]
        z.append(f"| {e['signal_tag']} | {e['ticker']} | {e.get('strategie') or ''} | {e['p_ziel_kronos']:.0%} / "
                 f"{e['p_stop_kronos']:.0%} | {e['p_ziel_zufall']:.0%} | {de(q['q10'], '+.1f')} / "
                 f"{de(q['mitte'], '+.1f')} / {de(q['q90'], '+.1f')} % | {e.get('ergebnis', 'offen')} |")
    z += ["", f"Offen: {len(offen)} Signale warten auf ihre 20 Handelstage. Kronos-Code: `forschung/kronos_modell/` "
          "(MIT-Lizenz). Simulation, keine Anlageberatung."]
    return "\n".join(z) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--modus", choices=["pruefen", "lauf"], default="lauf")
    p.add_argument("--probe", action="store_true", help="Probelauf: nichts im Repo speichern")
    p.add_argument("--ausgabe", default=None, help="Ordner für Log und Bericht (Standard: forschung/)")
    a = p.parse_args(argv)
    log_datei, bericht_datei = pfade(a.ausgabe)
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
    n_neu = vorhersage(daten, log, probe=a.probe)
    n_aus = auswertung(log, heute)
    schreibe(log_datei, log)
    schreibe(bericht_datei, bericht(log))
    print(f"Fertig: {n_neu} neue Signale, {n_aus} ausgewertet.")


if __name__ == "__main__":
    main()
