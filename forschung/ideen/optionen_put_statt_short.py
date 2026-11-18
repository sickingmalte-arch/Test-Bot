"""Wunsch des Nutzers vom 18.11.2026 („Vielleicht wäre der Handel mit Optionen wirklich noch was für dich“ – gewählt
u. a.: „Put statt Short“). Rechnung und Annahmen: forschung/optionen_hilfe.py."""
import os
import sys
import time
import types

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import optionen_hilfe as O  # noqa: E402
import short_fair_hilfe as F  # noqa: E402

NAME = "Optionen 4: Put statt Short"
QUELLE = ("Coval & Shumway (2001), „Expected Option Returns“, Journal of Finance 56; dazu die Short-Tests vom 17. und "
          "18.11.2026 (alle Short-Signale verloren).")
BESCHREIBUNG = ("Der Bot nimmt die 8 alten Short-Signale dazu, setzt aber nicht mit einem Short auf fallende Kurse, "
                "sondern kauft einen Put am Geld mit 60 Tagen Laufzeit. Die Prämie ist so groß wie das geplante Risiko "
                "(1 % des Kontos), Ausstieg am selben Tag wie beim Short. Vergleich: der Bot nur mit Long; zur Info "
                "auch der Bot mit echten Shorts. Gegenprobe: gleich viele Puts an zufälligen erlaubten Tagen. "
                "Optionspreise berechnet (Black-Scholes) mit zwei Annahmen: Schwankung der letzten 20 Tage ×1,0 und "
                "×1,25, Spread 2 %. 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum.")
VERMUTUNG = ("Mit Puts ist der Verlust je Trade begrenzt, große Abstürze bringen viel. So machen die Short-Signale den "
             "Bot mit beiden Preis-Annahmen in allen drei Zeiträumen besser – und besser als Puts an zufälligen Tagen.")
WIDERLEGT_WENN = ("Mit einer der beiden Preis-Annahmen in einem Zeitraum: Mitte der 8 Listen nicht besser als der Bot "
                  "nur mit Long, weniger als 6 von 8 Listen besser, mehr als 1 Punkt mehr Rückgang (Mitte), unter 30 "
                  "Puts oder nicht besser als die beste von 6 Zufalls-Gegenproben.")
VARIANTEN = ("1 Regel (Put am Geld, 60 Tage, Prämie = 1 % des Kontos, Signale der 8 alten Short-Strategien), "
             "gerechnet mit 2 festen Preis-Annahmen.")


def pruefen(P, a, watch, sektor_von):
    t0 = time.time()
    zr = F.listen(P, a, len(watch))

    def nur_bot(deps, daten):
        return O.mittel([{"bot": P.ROT.kennzahlen(dep["verlauf"])} for dep in deps])

    def mit_puts(deps, daten):
        je = []
        for dep in deps:
            e = {"aktie": P.ROT.kennzahlen(dep["verlauf"])}
            for name, faktor in O.FAKTOREN.items():
                kurve, n, r_opt, r_short = O.option_statt_aktie(P.R.sw, dep, daten, faktor, False, O.gebuehr())
                e[name], e["n"] = P.ROT.kennzahlen(kurve), n
                e[f"r_{name}"] = r_opt / n if n else np.nan
                e["r_aktie"] = r_short / n if n else np.nan
            je.append(e)
        return O.mittel(je)
    lang = O.je_liste(O.auswerten(P, a, sektor_von, zr, None, nur_bot), "bot")
    werte = O.auswerten(P, a, sektor_von, zr, F.alte_shorts, mit_puts)
    stufen, ok = O.stufen_annahmen(lang, werte)
    seeds = P.ZUFALL_LAEUFE if ok else (F.VERGLEICH_SEEDS if time.time() - t0 < F.VERGLEICH_FRIST else 0)
    zufall = [O.auswerten(P, a, sektor_von, zr, lambda sw, s=s: F.alte_shorts(sw, seed=s), mit_puts)
              for s in range(seeds)]
    vs, anzahl = list(zr), len(zr[list(zr)[0]]["listen"])
    zufall_beste = {name: {v: max(O.mitte(O.je_liste(z, name)[v]) for z in zufall) for v in vs} if zufall else None
                    for name in O.FAKTOREN}
    if not ok:
        text = "nicht überall besser (" + "; ".join(
            f"Preise {name}: " + " / ".join(O.zahl(x["plus"]) for x in je.values()) + " Punkte"
            for name, je in stufen.items()) + ")"
    elif len(zufall) < P.ZUFALL_LAEUFE:
        text = "überall besser, aber Gegenprobe fehlt"
    elif all(O.mitte(O.je_liste(werte, name)[v]) > zufall_beste[name][v] for name in O.FAKTOREN for v in vs):
        text = "besteht mit beiden Preis-Annahmen, auch besser als Zufall"
    else:
        text = "überall besser, aber nicht besser als Zufall"
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG, VERMUTUNG=VERMUTUNG,
                                 WIDERLEGT_WENN=WIDERLEGT_WENN, VARIANTEN=VARIANTEN)
    z = O.kopf_md(idee, text, zr, len(watch), P.R)
    z += ["| Bot nur mit Long (wie heute) | " + " | ".join(O.kz_zelle(lang[v]) for v in vs) + " |",
          "| Bot mit den alten Shorts als echte Shorts (zur Info) | "
          + " | ".join(O.kz_zelle(O.je_liste(werte, "aktie")[v]) for v in vs) + " |"]
    z += O.zeilen_annahmen("Put statt Short", werte, stufen, vs, anzahl)
    z += ["| … Puts je Zeitraum (alle Listen) · Ø je Trade: Short / Put günstig / Put teuer | " + " | ".join(
        f"{stufen['günstig'][v]['trades']:.0f} · " + " / ".join(
            O.zahl(O.gewichtet(werte, v, k), 2) for k in ("r_aktie", "r_günstig", "r_teuer")) + " R" for v in vs) + " |"]
    if zufall:
        z += [f"| … Gegenprobe: gleich viele Puts an Zufallstagen (beste von {len(zufall)}): günstig / teuer | "
              + " | ".join(" / ".join(f"{zufall_beste[name][v]:+.1f} %".replace(".", ",") for name in O.FAKTOREN)
                           for v in vs) + " |"]
    md = "\n".join(z + O.fuss_md()) + "\n"
    basis = {v: {"rendite": O.mitte(lang[v]), "rueckgang": O.mitte(lang[v], "rueckgang")} for v in vs}
    return text, O.schlechter_plus(stufen), {"basis": basis, "stufen": stufen, "werte": werte,
                                             "zufall_beste": zufall_beste}, md
