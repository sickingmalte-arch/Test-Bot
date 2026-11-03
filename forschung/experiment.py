"""Experimentier-Depot des Forschungs-Bots: derselbe Bot mit einer Idee aus forschung/experiment.json, eigenes
Übungsdepot mit Spielgeld (forschung/experiment_depot.json). Danach Vergleich mit dem Übungsdepot für die Webseite
(docs/forschung.json). Haupt-Depot und Claude-Depot werden nur gelesen, nie verändert."""
import argparse
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)


def lies(pfad, standard=None):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return standard


def schalter_setzen(sw, schalter):
    """Nur vorhandene Schalter des Bots (GROSS geschrieben) – nichts anderes lässt sich so verändern."""
    for name, wert in (schalter or {}).items():
        if not name.isupper() or not hasattr(sw, name):
            raise SystemExit(f"Unbekannter Schalter in experiment.json: {name}")
        setattr(sw, name, wert)


def wert_am(verlauf, tag):
    """Depotwert am Tag 'tag' oder am letzten Tag davor."""
    vorher = [w for t, w in verlauf if t <= tag]
    return vorher[-1] if vorher else None


def vergleich(experiment, papier, idee):
    """Beide Depots seit dem Start des Experimentier-Depots, in % – für die Webseite."""
    if not experiment or not experiment.get("verlauf"):
        return None
    ev = experiment["verlauf"]
    start = ev[0][0]
    pv = (papier or {}).get("verlauf") or []
    p0, p1 = wert_am(pv, start), (pv[-1][1] if pv else None)
    kurve = [{"tag": t, "experiment": round((w / ev[0][1] - 1) * 100, 2),
              "papier": round((wert_am(pv, t) / p0 - 1) * 100, 2) if p0 and wert_am(pv, t) else None} for t, w in ev]
    trades = experiment.get("trades") or []
    return {"name": idee.get("name"), "beschreibung": idee.get("beschreibung"), "seit": start, "bis": ev[-1][0],
            "experiment_prozent": round((ev[-1][1] / ev[0][1] - 1) * 100, 2),
            "papier_prozent": round((p1 / p0 - 1) * 100, 2) if p0 and p1 else None,
            "depotwert": round(ev[-1][1], 2), "positionen": len(experiment.get("positionen") or []),
            "trades": len(trades), "gewinner": sum(1 for t in trades if t.get("erloes", 0) > t.get("kosten", 0)),
            "kurve": kurve}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--konto", default="10000")
    p.add_argument("--risiko", default="1")
    p.add_argument("--ticker")
    p.add_argument("--nur-vergleich", action="store_true", help="nur docs/forschung.json neu schreiben")
    a = p.parse_args(argv)
    idee = lies(os.path.join(HIER, "experiment.json"), {})
    depot = os.path.join(HIER, "experiment_depot.json")
    if not a.nur_vergleich:
        sys.path.insert(0, WURZEL)
        import swing_scanner as sw
        schalter_setzen(sw, idee.get("schalter"))
        sys.argv = ["swing_scanner.py", "--konto", a.konto, "--risiko", a.risiko, "--rueckblick", "0",
                    "--papier", depot, "--bericht", os.path.join(HIER, "BERICHT.md"),
                    "--lernmodell", os.path.join(WURZEL, "lernen")] + (["--ticker", a.ticker] if a.ticker else [])
        sw.main()
    erg = vergleich(lies(depot), lies(os.path.join(WURZEL, "papier", "papier_depot.json")), idee)
    tagebuch = lies(os.path.join(HIER, "ergebnisse", "uebersicht.json"), [])
    with open(os.path.join(WURZEL, "docs", "forschung.json"), "w", encoding="utf-8") as f:
        json.dump({"experiment": erg, "ideen": tagebuch[-10:]}, f, ensure_ascii=False, indent=1)
    print("Forschung:", json.dumps({k: v for k, v in (erg or {}).items() if k != "kurve"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
