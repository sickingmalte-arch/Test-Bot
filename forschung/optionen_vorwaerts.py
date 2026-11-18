"""Vorwärts-Test „Gedeckter Call am Kursziel“ mit echten Optionspreisen (Wunsch des Nutzers vom 18.11.2026: „Ja teste“).

Der Rückblick (forschung/ergebnisse/optionen_gedeckter_call.md) zeigte: Ob der gedeckte Call hilft, hängt allein am
Preis der Calls. Kosten sie so viel, wie die Kurse danach schwanken (Schwankung der letzten 20 Tage ×1,0), bringt er
nichts; sind sie um ein Viertel teurer (×1,25), bringt er 3 bis 4 Punkte im Jahr. Alte Preise gibt es nicht kostenlos.
Deshalb misst dieser Test nach vorne: Werktags während der US-Börsenzeit holt er für jeden Kauf-Auftrag des
Übungsdepots für heute den echten Call am Kursziel (kleinster Basispreis ab dem Ziel, Verfall möglichst nah am
Zeitstopp nach etwa 4 Wochen) von Yahoo und vergleicht ihn mit der Rechnung aus dem Rückblick. Ab 30 Messungen gibt es
eine Aussage, welche Annahme stimmt; dann lässt sich der Rückblick mit dem gemessenen Preisniveau nachrechnen.

Nur Messung: Die Depots werden nur gelesen, gehandelt wird nichts. Ergebnis: forschung/optionen_vorwaerts.json und
forschung/OPTIONEN_VORWAERTS.md."""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
sys.path.insert(0, HIER)
import optionen_hilfe as O  # noqa: E402

DEPOT = os.path.join(WURZEL, "papier", "papier_depot.json")
DATEI = os.path.join(HIER, "optionen_vorwaerts.json")
BERICHT = os.path.join(HIER, "OPTIONEN_VORWAERTS.md")
NY = "America/New_York"
ZIEL_TAGE = 27   # so viele Kalendertage liegen etwa zwischen Einstieg und Zeitstopp (20 Börsentage)
MIN_TAGE = 20
AUSSAGE_AB = 30


def lies_json(pfad, leer):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return leer


def auftraege_fuer_heute(depot, heute):
    """Kauf-Aufträge des Übungsdepots für den heutigen Handelstag (Signal am letzten fertigen Tag)."""
    bis = pd.Timestamp(depot.get("bis") or "1900-01-01")
    if not (bis < heute <= bis + pd.Timedelta(days=4)):
        return bis, []
    return bis, [a for a in depot.get("auftraege") or [] if a.get("richtung", 1) > 0 and a.get("ziel")]


def verfall_waehlen(verfaelle, heute):
    """Verfall möglichst nah an etwa 4 Wochen (Zeitstopp), aber nicht unter 20 Tagen."""
    beste = None
    for v in verfaelle:
        tage = (pd.Timestamp(v) - heute).days
        if tage >= MIN_TAGE and (beste is None or abs(tage - ZIEL_TAGE) < abs(beste[1] - ZIEL_TAGE)):
            beste = (v, tage)
    return beste


def implizite_schwankung(preis, s, k, t):
    """Schwankung, bei der der Call nach Black-Scholes genau `preis` kostet (Halbierungsverfahren)."""
    if not (preis > 0 and s > 0 and k > 0 and t > 0) or preis >= s:
        return float("nan")
    unten, oben = 0.01, 5.0
    if float(O.bs(True, s, k, t, oben)) < preis:
        return float("nan")
    for _ in range(80):
        mitte = (unten + oben) / 2
        if float(O.bs(True, s, k, t, mitte)) < preis:
            unten = mitte
        else:
            oben = mitte
    return (unten + oben) / 2


def schwankung_20(schluss, heute):
    """Schwankung der letzten 20 Tage pro Jahr, nur mit Schlusskursen vor heute (wie im Rückblick)."""
    s = schluss.dropna()
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_convert(NY).tz_localize(None)
    s.index = idx.normalize()
    s = s[s.index < heute]
    r = np.log(s[s > 0]).diff().dropna().tail(20)
    return float(r.std() * np.sqrt(252)) if len(r) >= 15 else float("nan")


def messen(yf, auftrag, heute):
    """Ein Auftrag -> Messung (dict) oder (None, Grund)."""
    t = auftrag["ticker"]
    tk = yf.Ticker(t)
    wahl = verfall_waehlen(tk.options or (), heute)
    if wahl is None:
        return None, "keine passenden Optionen"
    verfall, tage = wahl
    kette = tk.option_chain(verfall)
    unten = getattr(kette, "underlying", None) or {}
    if unten.get("marketState") not in (None, "REGULAR"):
        return None, f"Börse nicht offen ({unten.get('marketState')})"
    kurs = float(unten.get("regularMarketPrice") or np.nan)
    if not np.isfinite(kurs):
        kurs = float(tk.fast_info["last_price"])
    calls = kette.calls
    calls = calls[calls["strike"] >= float(auftrag["ziel"])].sort_values("strike")
    if not len(calls):
        return None, "kein Basispreis am Ziel"
    c = calls.iloc[0]
    geld, brief = float(c.get("bid") or 0), float(c.get("ask") or 0)
    rv = schwankung_20(tk.history(period="3mo", interval="1d", auto_adjust=True)["Close"], heute)
    k, jahre = float(c["strike"]), tage / 365.0
    mitte = (geld + brief) / 2 if geld > 0 and brief > 0 else float("nan")
    iv = implizite_schwankung(mitte, kurs, k, jahre)
    modell = {name: float(O.geldkurs(O.bs(True, kurs, k, jahre, rv * f))) for name, f in O.FAKTOREN.items()}
    return {"datum": f"{heute.date()}", "ticker": t, "strategie": auftrag.get("strategie"), "kurs": kurs,
            "ziel": float(auftrag["ziel"]), "stop": float(auftrag.get("stop") or np.nan), "basis": k,
            "verfall": verfall, "tage": int(tage), "geld": geld, "brief": brief,
            "letzter": float(c.get("lastPrice") or 0), "umsatz": float(c.get("volume") or 0),
            "offene": float(c.get("openInterest") or 0), "iv_yahoo": float(c.get("impliedVolatility") or np.nan),
            "rv20": rv, "iv_mitte": iv, "verhaeltnis": iv / rv if rv and np.isfinite(iv) else float("nan"),
            "modell_geld_guenstig": modell["günstig"], "modell_geld_teuer": modell["teuer"]}, None


def zahl(x, st=2):
    return "–" if x is None or not np.isfinite(x) else f"{x:.{st}f}".replace(".", ",")


def tag(iso):
    return pd.Timestamp(iso).strftime("%d.%m.%Y")


def bericht(daten):
    m = [x for x in daten["messungen"] if np.isfinite(x.get("verhaeltnis", np.nan))]
    stand = tag(daten["messungen"][-1]["datum"]) if daten["messungen"] else "noch keine"
    n = len(m)
    verh = float(np.median([x["verhaeltnis"] for x in m])) if n else float("nan")
    zu_guenstig = [x["geld"] / x["modell_geld_guenstig"] for x in m if x["modell_geld_guenstig"] > 0]
    teuer_oder_mehr = [x["geld"] >= x["modell_geld_teuer"] for x in m]
    if n < AUSSAGE_AB:
        urteil = f"Noch keine Aussage: {n} von {AUSSAGE_AB} Messungen."
    else:
        naeher = "„teuer“ (×1,25)" if abs(verh - 1.25) < abs(verh - 1.0) else "„günstig“ (×1,0)"
        urteil = (f"Echte Calls am Kursziel kosten im Schnitt so viel wie die Schwankung der letzten 20 Tage "
                  f"×{zahl(verh)} – näher an {naeher}. Nächster Schritt: den Rückblick mit diesem Faktor nachrechnen.")
    z = ["# 🔬 Vorwärts-Test: gedeckter Call am Kursziel mit echten Optionspreisen", "",
         f"Letzte Messung: {stand} · Messungen: {n} · Eine Aussage gibt es ab {AUSSAGE_AB}.", "",
         "Frage aus dem Rückblick vom 18.11.2026: Kosten Calls am Kursziel so viel, wie die Kurse danach schwanken "
         "(Rechnung „günstig“, Schwankung der letzten 20 Tage ×1,0 – dann bringt der gedeckte Call nichts), oder ein "
         "Viertel mehr („teuer“, ×1,25 – dann +3 bis +4 Punkte im Jahr)? Gemessen wird werktags während der "
         "US-Börsenzeit an jedem Kauf-Auftrag des Übungsdepots: echter Call von Yahoo, kleinster Basispreis ab dem "
         "Kursziel, Verfall nah am Zeitstopp. Nur Messung, gehandelt wird nichts.", "",
         f"**Ergebnis: {urteil}**", "",
         "| Kennzahl | Wert |", "|---|---:|",
         f"| Messungen | {n} |",
         f"| Echte Schwankung im Optionspreis ÷ Schwankung der letzten 20 Tage (Mitte) | {zahl(verh)} |",
         f"| Echter Geldkurs ÷ Rechnung „günstig“ (Mitte) | "
         f"{zahl(float(np.median(zu_guenstig)) if zu_guenstig else float('nan'))} |",
         "| Anteil der Calls, deren Geldkurs mindestens die Rechnung „teuer“ erreicht | "
         + (f"{100 * np.mean(teuer_oder_mehr):.0f} %" if teuer_oder_mehr else "–") + " |", ""]
    if daten["messungen"]:
        z += ["**Letzte Messungen:**", "",
              "| Tag | Aktie | Kurs | Ziel | Basis | Verfall | Geld / Brief | Rechnung günstig / teuer | Verhältnis |",
              "|---|---|---:|---:|---:|---|---:|---:|---:|"]
        for x in daten["messungen"][-12:][::-1]:
            z.append(f"| {tag(x['datum'])} | {x['ticker']} | {zahl(x['kurs'])} | {zahl(x['ziel'])} | {zahl(x['basis'])} | "
                     f"{tag(x['verfall'])} | {zahl(x['geld'])} / {zahl(x['brief'])} | {zahl(x['modell_geld_guenstig'])} / "
                     f"{zahl(x['modell_geld_teuer'])} | {zahl(x['verhaeltnis'])} |")
    if daten.get("ausgelassen"):
        z += ["", "Nicht gemessen (zuletzt): " + "; ".join(
            f"{tag(x['datum'])} {x['ticker']}: {x['grund']}" for x in daten["ausgelassen"][-8:])]
    z += ["", "Preise je Aktie in Dollar. Simulation mit Spielgeld, keine Anlageberatung."]
    return "\n".join(z) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--nur-bericht", action="store_true", help="nichts holen, nur den Bericht neu schreiben")
    a = p.parse_args(argv)
    daten = lies_json(DATEI, {"messungen": [], "ausgelassen": []})
    heute = pd.Timestamp.now(tz=NY).tz_localize(None).normalize()
    if not a.nur_bericht:
        import yfinance as yf
        bis, auftraege = auftraege_fuer_heute(lies_json(DEPOT, {}), heute)
        schon = {(x["datum"], x["ticker"]) for x in daten["messungen"] + daten["ausgelassen"]}
        print(f"Daten bis {bis.date()}, {len(auftraege)} Kauf-Aufträge für {heute.date()}")
        for auftrag in auftraege:
            if (f"{heute.date()}", auftrag["ticker"]) in schon:
                continue
            try:
                messung, grund = messen(yf, auftrag, heute)
            except Exception as e:  # noqa: BLE001 – Yahoo liefert nichts: als ausgelassen merken
                messung, grund = None, f"Fehler beim Abruf ({type(e).__name__})"
            if messung is None:
                daten["ausgelassen"].append({"datum": f"{heute.date()}", "ticker": auftrag["ticker"], "grund": grund})
                print(f"{auftrag['ticker']}: {grund}")
            else:
                daten["messungen"].append(messung)
                print(f"{auftrag['ticker']}: Basis {messung['basis']} bis {messung['verfall']}, Geld {messung['geld']}"
                      f", Verhältnis {messung['verhaeltnis']:.2f}")
        daten["ausgelassen"] = daten["ausgelassen"][-200:]
        with open(DATEI, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, indent=1)
    with open(BERICHT, "w", encoding="utf-8") as f:
        f.write(bericht(daten))


if __name__ == "__main__":
    main()
