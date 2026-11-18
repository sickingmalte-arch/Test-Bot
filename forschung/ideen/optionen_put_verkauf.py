"""Wunsch des Nutzers vom 18.11.2026 („Vielleicht wäre der Handel mit Optionen wirklich noch was für dich“ – gewählt
u. a.: „Put-Verkauf mit freiem Geld“). Daten und Rechnung: forschung/optionen_hilfe.py (put_reihen)."""
import os
import sys
import types

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import optionen_hilfe as O  # noqa: E402
import short_fair_hilfe as F  # noqa: E402

NAME = "Optionen 1: Put-Verkauf mit dem freien Geld (S&P 500, wie der CBOE-PutWrite-Index)"
QUELLE = ("Whaley (2002), „Return and Risk of CBOE Buy Write Monthly Index“, Journal of Derivatives 10; Ungar & Moran "
          "(2009), „The Cash-Secured PutWrite Strategy and Performance of Related Benchmark Indexes“, Journal of "
          "Alternative Investments 11 – verkaufte Index-Puts brachten etwa so viel wie der S&P 500 bei weniger "
          "Schwankung (eine Art Versicherungsprämie).")
BESCHREIBUNG = ("Der Bot handelt wie immer. Mit dem Geld, das am Vorabend nicht in Aktien steckt (oft über die Hälfte), "
                "verkauft er Puts auf den S&P 500 – voll mit Geld gedeckt und jeden Monat neu, so wie der "
                "CBOE-PutWrite-Index (echte Börsendaten; nur wenn sie fehlen, eigene Rechnung mit dem VIX). Abzüglich "
                "1 % Kosten im Jahr für Spreads und Gebühren. Zum Vergleich: dasselbe freie Geld nur verzinst "
                "(US-Geldmarkt) und im S&P 500. Wie bei den anderen Tests auf 8 Zufallslisten aus dem damaligen "
                "S&P 500 je Zeitraum.")
VERMUTUNG = ("Verkaufte Puts verdienen eine Versicherungsprämie. Mit dem freien Geld bringt das in allen drei Zeiträumen "
             "mehr Rendite als der Bot allein und mehr als dasselbe Geld nur verzinst, bei höchstens 1 Punkt mehr "
             "Rückgang.")
WIDERLEGT_WENN = ("In einem Zeitraum: Mitte der 8 Listen nicht besser als der Bot allein, weniger als 6 von 8 Listen "
                  "besser, mehr als 1 Punkt mehr Rückgang (Mitte) oder nicht mehr Rendite (Mitte) als das freie Geld nur "
                  "verzinst.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: Puts über 100 % bzw. 50 % des freien Geldes (der Rest verzinst); Kosten "
             "1 % im Jahr fest.")
VARIANTE = {"put100": "Puts mit 100 % des freien Geldes", "put50": "Puts mit 50 % des freien Geldes, Rest verzinst"}


def pruefen(P, a, watch, sektor_von):
    zr = F.listen(P, a, len(watch))
    reihen, quellen = O.put_reihen(P, a)
    print("Daten:", quellen)
    put = reihen["put"] - O.KOSTEN_PUT_JAHR / 252
    raten = {"zins": reihen["zins"], "put100": put, "put50": 0.5 * put + 0.5 * reihen["zins"], "spy": reihen["spy"]}

    def auswerter(deps, daten):
        je = []
        for dep in deps:
            kurve = dep["verlauf"].astype(float)
            frei = O.freies_geld(P.R.sw, dep, daten)
            e = {"bot": P.ROT.kennzahlen(kurve), "frei": float((frei / kurve).mean() * 100)}
            for name, r in raten.items():
                e[name] = P.ROT.kennzahlen(O.ueberlagern(kurve, frei, r))
            je.append(e)
        return O.mittel(je)
    werte = O.auswerten(P, a, sektor_von, zr, None, auswerter)
    lang = O.je_liste(werte, "bot")
    vs, anzahl = list(zr), len(zr[list(zr)[0]]["listen"])
    stufen, urteile = {}, {}
    for key in VARIANTE:
        je = O.stufe(lang, O.je_liste(werte, key))
        for v in vs:
            je[v]["gegen_zins"] = O.mitte(O.je_liste(werte, key)[v]) - O.mitte(O.je_liste(werte, "zins")[v])
        stufen[key] = je
        if not O.besteht(je, F.MEHRHEIT):
            urteile[key] = "nicht überall besser als der Bot allein"
        elif not all(x["gegen_zins"] > 0 for x in je.values()):
            urteile[key] = "besser als der Bot allein, aber nicht besser als das Geld nur zu verzinsen"
        else:
            urteile[key] = "besteht"
    text = "; ".join(f"{VARIANTE[k]}: {u}" for k, u in urteile.items())
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG, VERMUTUNG=VERMUTUNG,
                                 WIDERLEGT_WENN=WIDERLEGT_WENN, VARIANTEN=VARIANTEN)
    z = O.kopf_md(idee, text, zr, len(watch), P.R)
    z += ["| Bot allein, freies Geld ohne Zins (wie heute) | " + " | ".join(O.kz_zelle(lang[v]) for v in vs) + " |",
          "| … freies Geld im Schnitt (Anteil am Depot) | " + " | ".join(
              f"{np.median(O.je_liste(werte, 'frei')[v]):.0f} %" for v in vs) + " |",
          "| Freies Geld nur verzinst (Vergleich) | " + " | ".join(
              O.kz_zelle(O.je_liste(werte, "zins")[v]) for v in vs) + " |"]
    for key, titel in VARIANTE.items():
        je = stufen[key]
        z += [f"| **{titel}** | " + " | ".join(O.kz_zelle(O.je_liste(werte, key)[v]) for v in vs) + " |",
              "| … Unterschied zum Bot allein (Mitte, Punkte) · Listen besser · gegen „nur verzinst“ | " + " | ".join(
                  f"{O.zahl(je[v]['plus'])} · {je[v]['besser']} von {anzahl} · {O.zahl(je[v]['gegen_zins'])}"
                  for v in vs) + " |"]
    z += ["| Freies Geld im S&P 500 (zur Info) | " + " | ".join(
        O.kz_zelle(O.je_liste(werte, "spy")[v]) for v in vs) + " |", "",
          "**Urteile:**", ""] + [f"- **{VARIANTE[k]}:** {u}" for k, u in urteile.items()]
    z += ["", f"Daten: PutWrite – {quellen['put']} (ab {quellen['put_ab']}); Zins – {quellen['zins']}. Zins und "
          "Prämien in Dollar gerechnet und auf das freie Geld in Euro angewandt (Wechselkurs außen vor). Im echten "
          "Konto bräuchte man dafür ein Margin-Konto, weil dasselbe Geld zugleich für neue Aktienkäufe bereitsteht. "
          "Pleitefirmen fehlen in den Listen. Simulation mit Spielgeld, keine Anlageberatung."]
    md = "\n".join(z) + "\n"
    basis = {v: {"rendite": O.mitte(lang[v]), "rueckgang": O.mitte(lang[v], "rueckgang")} for v in vs}
    beste = max(VARIANTE, key=lambda k: min(stufen[k][v]["plus"] for v in vs))
    plus = {v: stufen[beste][v]["plus"] for v in vs}
    return text, plus, {"basis": basis, "stufen": stufen, "werte": werte, "quellen": quellen}, md
