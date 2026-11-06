"""Ehrlicher Bot-Check (Wunsch vom 06.11.2026): Wie gut ist der Swing-Bot mit Aktien, die man zu Beginn eines Zeitraums
ohne Rückblick hätte wählen können? Keine Regeländerung, nur eine Messung. Die heutige Watchlist ist mit dem Wissen
von heute gewählt – ihr Rückblick ist deshalb vermutlich zu gut (siehe Nacht-Forschung vom 05.11.2026)."""
import importlib
import os

import numpy as np
import pandas as pd

NAME = "Ehrlicher Bot-Check: Swing-Bot mit zufälligen Aktien aus dem damaligen S&P 500 statt der heutigen Watchlist"
QUELLE = "Nacht-Forschung 05.11.2026 (Verzerrung durch die heutige Aktienliste)"
BESCHREIBUNG = ("Zu Beginn jedes Zeitraums (2010, 2015, 2022) zieht der Test 8-mal zufällig so viele Aktien, wie die "
                "Watchlist hat, aus allen Aktien, die an diesem Tag im S&P 500 waren (Liste github.com/fja05680/sp500) "
                "und genug Kurse haben. Mit jeder Liste handelt der unveränderte Swing-Bot den ganzen Zeitraum, mit "
                "Spread und Gebühr. Zum Vergleich: dieselben Aktien einfach zu gleichen Teilen halten (monatlich "
                "ausgeglichen), die heutige Watchlist halten, S&P 500 und Nasdaq-100 halten.")
VERMUTUNG = ("Mit Aktien, die man damals ohne Rückblick hätte wählen können, bringt der Swing-Bot deutlich weniger als "
             "mit der heutigen Watchlist.")
WIDERLEGT_WENN = ("Der Bot liegt mit den zufälligen damaligen Listen im Mittel (Median) in allen drei Zeiträumen höchstens "
                  "1 Punkt pro Jahr unter seinem Ergebnis mit der heutigen Watchlist.")
VARIANTEN = "1 Messung, je Zeitraum 8 zufällige Listen. Keine Regeländerung, nichts wird übernommen."
ZIEHUNGEN = 8


def _kandidaten(ROT, T, i):
    """Aktien, die am Tag i im S&P 500 waren und das Jahr davor fast lückenlos Kurse haben."""
    tag = T["tage"][i]
    return [t for t in T["aktien"]
            if ROT.im_index(T, t, tag) and T["roh"][t].iloc[max(0, i - 260):i + 1].notna().sum() >= 250]


def pruefen(P, a, watch, sektor_von):
    R, ROT = P.R, P.ROT
    basis = P.lauf(a.cache, watch, sektor_von, a.laeufe)  # der Bot mit der heutigen Watchlist, wie bei jeder Idee
    T = ROT.tabellen(a.cache)
    if T["wechsel"] is None:
        T["wechsel"] = ROT.index_wechsel(a.cache)
    importlib.reload(R.sw)
    R.sw.GEBUEHR = float(os.environ.get("GEBUEHR", "0"))
    watch_us = [t for t in watch if t in T["spalte"]]
    erg = {}
    try:
        for von, bis in R.ZEITRAEUME.values():
            bis = min(pd.Timestamp(bis), P.ENDE)
            i = int(T["tage"].searchsorted(pd.Timestamp(von))) - 1  # Abend vor dem Start
            kand = _kandidaten(ROT, T, i)
            listen = [sorted(np.random.default_rng([z, T["tage"][i].year]).choice(kand, len(watch), replace=False))
                      for z in range(ZIEHUNGEN)]
            erg[von] = {
                "kandidaten": len(kand), "listen": listen,
                "bot": [R.jetziger_bot(a.cache, liste, sektor_von, von, bis, a.laeufe) for liste in listen],
                "halten": [ROT.kennzahlen(ROT.depot(a.cache, von, bis, "fest", len(liste), filter_ticker=None,
                                                    feste=liste)) for liste in listen],
                "watch_halten": ROT.kennzahlen(ROT.depot(a.cache, von, bis, "fest", len(watch_us), filter_ticker=None,
                                                         feste=watch_us)) if watch_us else None,
                "spy": ROT.kennzahlen(ROT.halten(a.cache, "SPY", von, bis)),
                "qqq": ROT.kennzahlen(ROT.halten(a.cache, "QQQ", von, bis)),
            }
            print(f"{von}: {len(kand)} Kandidaten, Bot Mitte {np.median([b['rendite'] for b in erg[von]['bot']]):+.1f} %")
    finally:
        importlib.reload(R.sw)
    mitte = {v: float(np.median([b["rendite"] for b in e["bot"]])) for v, e in erg.items()}
    plus = {v: mitte[v] - basis[v]["rendite"] for v in basis}
    if all(x >= -1 for x in plus.values()):
        text = "Vermutung widerlegt: mit damaligen Aktien ist der Bot kaum schlechter als mit der heutigen Watchlist"
    else:
        text = ("Vermutung bestätigt: mit damaligen Aktien bringt der Bot weniger (" +
                " / ".join(f"{plus[v]:+.1f}".replace(".", ",") for v in basis) + " Punkte pro Jahr)")
    return text, plus, {"basis": basis, "zeitraeume": erg, "watch_halten_aktien": len(watch_us)}, \
        _markdown(P, basis, erg, text, len(watch), len(watch_us))


def _markdown(P, basis, erg, text, n, n_us):
    import datetime as dt
    q = lambda e: e["rendite"] / max(e["rueckgang"], 0.1)  # noqa: E731
    f = lambda e: f"{e['rendite']:+.1f} % / −{e['rueckgang']:.0f} % ({q(e):.2f})".replace(".", ",")  # noqa: E731

    def mitte(liste):
        return {k: float(np.median([x[k] for x in liste])) for k in ("rendite", "rueckgang")}

    def spanne(liste):
        r = [x["rendite"] for x in liste]
        return f"{min(r):+.1f} bis {max(r):+.1f} %".replace(".", ",")
    vs = list(basis)
    z = [f"# 🔬 {NAME}", "", f"Getestet am {dt.date.today():%d.%m.%Y} · {QUELLE}", "", BESCHREIBUNG, "",
         f"- **Vermutung:** {VERMUTUNG}", f"- **Widerlegt, wenn:** {WIDERLEGT_WENN}", f"- **Varianten:** {VARIANTEN}",
         "", f"**Ergebnis: {text}**", "",
         "| Rendite pro Jahr / größter Rückgang (Rendite pro Rückgang) | " + " | ".join(P.R.ZEITRAEUME) + " |",
         "|---|" + "---:|" * len(vs),
         "| Swing-Bot mit der heutigen Watchlist | " + " | ".join(f(basis[v]) for v in vs) + " |",
         f"| **Swing-Bot mit {n} zufälligen damaligen S&P-500-Aktien (Mitte aus {ZIEHUNGEN} Listen)** | "
         + " | ".join(f(mitte(erg[v]["bot"])) for v in vs) + " |",
         "| … Spanne der Rendite | " + " | ".join(spanne(erg[v]["bot"]) for v in vs) + " |",
         "| Dieselben zufälligen Aktien einfach halten (Mitte) | " + " | ".join(f(mitte(erg[v]["halten"])) for v in vs) + " |",
         *([f"| Heutige Watchlist einfach halten ({n_us} US-Aktien) | "
            + " | ".join(f(erg[v]["watch_halten"]) for v in vs) + " |"] if n_us else []),
         "| S&P 500 halten | " + " | ".join(f(erg[v]["spy"]) for v in vs) + " |",
         "| Nasdaq-100 halten | " + " | ".join(f(erg[v]["qqq"]) for v in vs) + " |", "",
         "| Bot-Kennzahlen | " + " | ".join(P.R.ZEITRAEUME) + " |", "|---|" + "---:|" * len(vs),
         "| Treffer heutige Watchlist / damalige Listen | " + " | ".join(
             f"{basis[v]['treffer']:.0f} % / {np.median([b['treffer'] for b in erg[v]['bot']]):.0f} %" for v in vs) + " |",
         "| Schnitt je Trade in R (heutige / damalige) | " + " | ".join(
             f"{basis[v]['schnitt_r']:+.2f} / {np.median([b['schnitt_r'] for b in erg[v]['bot']]):+.2f}".replace(".", ",")
             for v in vs) + " |",
         "| Trades pro Jahr (heutige / damalige) | " + " | ".join(
             f"{basis[v]['trades_jahr']:.0f} / {np.median([b['trades_jahr'] for b in erg[v]['bot']]):.0f}" for v in vs) + " |",
         "| Aktien im S&P 500 mit Kursen zum Start (Auswahl) | " + " | ".join(str(erg[v]["kandidaten"]) for v in vs) + " |",
         "", "Verbleibende Verzerrung: Aktien, die seitdem aus dem Index geflogen sind, haben meist keine Kurse mehr und "
         "fehlen in der Auswahl – auch dieses Ergebnis ist eher noch etwas zu gut. Simulation, keine Anlageberatung."]
    return "\n".join(z) + "\n"
