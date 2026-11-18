"""Wunsch des Nutzers vom 18.11.2026 („Vielleicht wäre der Handel mit Optionen wirklich noch was für dich“ – gewählt
u. a.: „Gedeckter Call am Ziel“). Rechnung und Annahmen: forschung/optionen_hilfe.py."""
import os
import sys
import types

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import optionen_hilfe as O  # noqa: E402
import short_fair_hilfe as F  # noqa: E402

NAME = "Optionen 2: Gedeckter Call am Kursziel"
QUELLE = ("Whaley (2002), „Return and Risk of CBOE Buy Write Monthly Index“, Journal of Derivatives 10; Israelov & "
          "Nielsen (2014), „Covered Call Strategies: One Fact and Eight Myths“, Financial Analysts Journal 70 – "
          "gedeckte Calls verdienen eine Prämie, geben dafür starke Anstiege ab.")
BESCHREIBUNG = ("Zu jedem Kauf verkauft der Bot einen Call je Aktie mit Basispreis genau am Kursziel, fällig am Tag des "
                "Zeitstopps (20 Börsentage). Das Ziel ist damit kein Ausstieg mehr: Liegt der Kurs am Verfallstag über "
                "dem Ziel, wird die Aktie zum Ziel abgegeben und die Prämie bleibt; sonst verkauft der Bot zum "
                "Schlusskurs. Stop und Ausstieg vor Quartalszahlen gelten wie immer, dann kauft er den Call zurück. "
                "Optionspreise berechnet (Black-Scholes) mit zwei Annahmen: Schwankung der letzten 20 Tage ×1,0 und "
                "×1,25, Spread 2 %. Gleiche Trades des Bots auf 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum.")
VERMUTUNG = ("Die Call-Prämie bringt bei jedem Trade etwas dazu; weil der Bot am Ziel ohnehin verkauft, kostet sie "
             "kaum etwas. Mit beiden Preis-Annahmen in allen drei Zeiträumen mehr Rendite als der Bot.")
WIDERLEGT_WENN = ("Mit einer der beiden Preis-Annahmen in einem Zeitraum: Mitte der 8 Listen nicht besser als der Bot, "
                  "weniger als 6 von 8 Listen besser, mehr als 1 Punkt mehr Rückgang (Mitte) oder unter 30 Trades.")
VARIANTEN = ("1 Regel (Basispreis = Kursziel, Verfall am Tag des Zeitstopps), gerechnet mit 2 festen "
             "Preis-Annahmen; bestehen muss sie mit beiden.")


def pruefen(P, a, watch, sektor_von):
    zr = F.listen(P, a, len(watch))

    def auswerter(deps, daten):
        je = []
        for dep in deps:
            e = {"bot": P.ROT.kennzahlen(dep["verlauf"])}
            for name, faktor in O.FAKTOREN.items():
                kurve, n, r_extra = O.gedeckter_call(P.R.sw, dep, daten, faktor, O.gebuehr())
                e[name], e["n"] = P.ROT.kennzahlen(kurve), n
                e[f"r_{name}"] = r_extra / n if n else np.nan
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
    z += ["| Bot ohne Call (wie heute) | " + " | ".join(O.kz_zelle(lang[v]) for v in vs) + " |"]
    z += O.zeilen_annahmen("Gedeckter Call am Ziel", werte, stufen, vs, anzahl)
    z += ["| … Trades je Zeitraum (alle Listen) · Ø Extra je Trade durch den Call: günstig / teuer | " + " | ".join(
        f"{stufen['günstig'][v]['trades']:.0f} · " + " / ".join(
            O.zahl(O.gewichtet(werte, v, k), 2) for k in ("r_günstig", "r_teuer")) + " R" for v in vs) + " |"]
    md = "\n".join(z + O.fuss_md()) + "\n"
    basis = {v: {"rendite": O.mitte(lang[v]), "rueckgang": O.mitte(lang[v], "rueckgang")} for v in vs}
    return text, O.schlechter_plus(stufen), {"basis": basis, "stufen": stufen, "werte": werte}, md
