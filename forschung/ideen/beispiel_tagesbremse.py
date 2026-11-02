"""Beispiel-Idee (schon geprüft am 30.10.2026, nicht übernommen): nach einem Tag mit −2 % im Depot alles zum
Schlusskurs verkaufen. Zeigt, wie eine Idee den Bot für den Test verändert."""
import inspect

NAME = "Tagesbremse: nach −2 % alles verkaufen"
QUELLE = "eigene Idee (Chat vom 30.10.2026)"
BESCHREIBUNG = ("Fällt das Depot an einem Tag um 2 % oder mehr, verkauft der Bot alle Positionen zum Schlusskurs und "
                "kauft am nächsten Tag nichts Neues.")

BLOCK = '''        if verlauf:
            _wert = bargeld + sum(positionswert(p, *letzter_kurs[t]) for t, p in positionen.items())
            if _wert / verlauf[-1][1] - 1 <= -0.02:
                for t in list(positionen):
                    p, d = positionen[t], daten[t]
                    i = d["pos"].get(tag)
                    if i is None or i >= d["n_fertig"]:
                        continue
                    rate = d["FX"][i]
                    ausfuehrung = mit_spread(d["C"][i], p["richtung"], False)
                    erloes = positionswert(p, ausfuehrung, rate) - gebuehr
                    bargeld += erloes
                    gebuehren += gebuehr
                    spread_kosten += p["stueck"] * d["C"][i] * SPREAD / rate
                    p["erloes"] += erloes
                    del positionen[t]
                    trades.append({**p, "verkauf_tag": tag, "verkauf_preis": in_euro(p, ausfuehrung, rate),
                                   "grund": "Bremse"})
                auftraege = []
'''


def anpassen(sw):
    src = inspect.getsource(sw.simuliere_depot)
    anker = "        # 4) Depotwert zum Schlusskurs\n"
    assert src.count(anker) == 1
    exec(compile(src.replace(anker, BLOCK + anker), "simuliere_depot_idee", "exec"), sw.__dict__)
