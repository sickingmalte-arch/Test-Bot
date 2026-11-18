"""Wunsch des Nutzers vom 18.11.2026 („Vielleicht wäre der Handel mit Optionen wirklich noch was für dich“ – gewählt
u. a.: „Call statt Aktie“). Rechnung und Annahmen: forschung/optionen_hilfe.py."""
import os
import sys
import types

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import optionen_hilfe as O  # noqa: E402
import short_fair_hilfe as F  # noqa: E402

NAME = "Optionen 3: Call statt Aktie"
QUELLE = ("Coval & Shumway (2001), „Expected Option Returns“, Journal of Finance 56 – gekaufte Optionen bringen im "
          "Schnitt weniger, als ihr Risiko erwarten lässt; Black & Scholes (1973), Journal of Political Economy 81 – "
          "die Preisformel.")
BESCHREIBUNG = ("Bei jedem Kauf-Signal kauft der Bot statt der Aktie einen Call am Geld (Basispreis = Kurs beim "
                "Einstieg) mit 60 Tagen Laufzeit. Die Prämie ist so groß wie das geplante Risiko des Trades (1 % des "
                "Kontos) – mehr kann nicht verloren gehen. Ausstieg am selben Tag wie bei der Aktie (Stop, Ziel, "
                "Zeitstopp, vor Quartalszahlen). Optionspreise berechnet (Black-Scholes) mit zwei Annahmen: Schwankung "
                "der letzten 20 Tage ×1,0 und ×1,25, Spread 2 %. Gleiche Trades des Bots auf 8 Zufallslisten aus dem "
                "damaligen S&P 500 je Zeitraum.")
VERMUTUNG = ("Mit dem Call verliert der Bot am Stop weniger als 1 R und gewinnt am Ziel mehr. Das bringt mit beiden "
             "Preis-Annahmen in allen drei Zeiträumen mehr Rendite als die Aktie.")
WIDERLEGT_WENN = ("Mit einer der beiden Preis-Annahmen in einem Zeitraum: Mitte der 8 Listen nicht besser als der Bot, "
                  "weniger als 6 von 8 Listen besser, mehr als 1 Punkt mehr Rückgang (Mitte) oder unter 30 Trades.")
VARIANTEN = "1 Regel (Call am Geld, 60 Tage, Prämie = 1 % des Kontos), gerechnet mit 2 festen Preis-Annahmen."


def pruefen(P, a, watch, sektor_von):
    zr = F.listen(P, a, len(watch))

    def auswerter(deps, daten):
        je = []
        for dep in deps:
            e = {"bot": P.ROT.kennzahlen(dep["verlauf"])}
            for name, faktor in O.FAKTOREN.items():
                kurve, n, r_opt, r_aktie = O.option_statt_aktie(P.R.sw, dep, daten, faktor, True, O.gebuehr())
                e[name], e["n"] = P.ROT.kennzahlen(kurve), n
                e[f"r_{name}"] = r_opt / n if n else np.nan
                e["r_aktie"] = r_aktie / n if n else np.nan
            je.append(e)
        return O.mittel(je)
    werte = O.auswerten(P, a, sektor_von, zr, None, auswerter)
    lang = O.je_liste(werte, "bot")
    stufen, ok = O.stufen_annahmen(lang, werte)
    text = ("besteht mit beiden Preis-Annahmen" if ok else "nicht überall besser (" + "; ".join(
        f"Preise {name}: " + " / ".join(O.zahl(x["plus"]) for x in je.values()) + " Punkte"
        for name, je in stufen.items()) + ")")
    vs, anzahl = list(zr), len(zr[list(zr)[0]]["listen"])
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG, VERMUTUNG=VERMUTUNG,
                                 WIDERLEGT_WENN=WIDERLEGT_WENN, VARIANTEN=VARIANTEN)
    z = O.kopf_md(idee, text, zr, len(watch), P.R)
    z += ["| Bot mit Aktien (wie heute) | " + " | ".join(O.kz_zelle(lang[v]) for v in vs) + " |"]
    z += O.zeilen_annahmen("Call statt Aktie", werte, stufen, vs, anzahl)
    z += ["| … Trades je Zeitraum (alle Listen) · Ø je Trade: Aktie / Call günstig / Call teuer | " + " | ".join(
        f"{stufen['günstig'][v]['trades']:.0f} · " + " / ".join(
            O.zahl(O.gewichtet(werte, v, k), 2) for k in ("r_aktie", "r_günstig", "r_teuer")) + " R" for v in vs) + " |"]
    md = "\n".join(z + O.fuss_md()) + "\n"
    basis = {v: {"rendite": O.mitte(lang[v]), "rueckgang": O.mitte(lang[v], "rueckgang")} for v in vs}
    return text, O.schlechter_plus(stufen), {"basis": basis, "stufen": stufen, "werte": werte}, md
