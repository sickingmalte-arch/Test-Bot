"""Wunsch des Nutzers vom 18.11.2026 („Er soll auch mal ausprobieren, wenn schlechte Nachrichten kommen für eine Aktie,
direkt zu shorten“). Alte Schlagzeilen gibt es nicht; geprüft werden die zwei Arten schlechter Nachrichten mit echter,
datierter Geschichte (forschung/nachrichten_hilfe.py), auf Zufallslisten aus dem damaligen S&P 500 wie im fairen
Short-Test (forschung/short_fair_hilfe.py)."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import nachrichten_hilfe as N  # noqa: E402
import short_fair_hilfe as F  # noqa: E402
import short_hilfe as S  # noqa: E402

NAME = "Short direkt nach schlechten Nachrichten: Herabstufung durch Analysten oder Pflichtmeldung mit Kursrutsch"
QUELLE = ("Womack (1996), „Do Brokerage Analysts' Recommendations Have Investment Value?“, Journal of Finance 51 – "
          "nach Herabstufungen fallen Kurse noch Wochen weiter; Chan (2003), „Stock price reaction to news and no-news: "
          "drift and reversal after headlines“, Journal of Financial Economics 70 – nach schlechten Nachrichten fällt "
          "der Kurs weiter, nach einem Rutsch ohne Nachricht erholt er sich eher.")
BESCHREIBUNG = ("Neue Short-Strategie in zwei Varianten. Alte Schlagzeilen gibt es nicht, aber zwei Arten schlechter "
                "Nachrichten haben eine echte, datierte Geschichte. (1) Ein Analyst stuft die Aktie herunter (Daten von "
                "Yahoo) – der Bot geht zur nächsten Eröffnung short. (2) Die Firma meldet der US-Börsenaufsicht SEC eine "
                "wichtige Nachricht (Formular 8-K, ohne Quartalszahlen) und die Aktie fällt an dem Tag um mindestens "
                "2 ATR – die Börse fand die Nachricht also schlecht; Short zur nächsten Eröffnung, nicht am Zahlen-Tag. "
                "Eine Nachricht bis 16:00 New Yorker Zeit zählt für denselben Tag, eine spätere für den nächsten. In "
                "jeder Marktlage, Stop +3 ATR, Ziel −3 ATR, Zeitstopp wie immer, höchstens 2 Shorts gleichzeitig, mit "
                "Gebühr und Spread, auf den 8 Zufallslisten aus dem damaligen S&P 500 je Zeitraum. Gegenprobe: je Aktie "
                "gleich viele Shorts an zufälligen Tagen.")
VERMUTUNG = ("Nach schlechten Nachrichten fällt eine Aktie weiter. Wer direkt danach shortet, verdient Geld und macht den "
             "Bot in allen drei Zeiträumen besser – und besser als Shorts an zufälligen Tagen.")
WIDERLEGT_WENN = ("Keine Variante schafft in jedem Zeitraum alles davon: Mitte der 8 Listen mehr Rendite als der Bot nur "
                  "mit Long, mindestens 6 von 8 Listen besser, höchstens 1 Punkt mehr Rückgang (Mitte), mindestens 30 "
                  "Short-Trades und mehr Rendite als die beste von 6 Zufalls-Gegenproben.")
VARIANTEN = ("2, vor dem Rechnen festgelegt: (N1) Herabstufung durch einen Analysten → Short, (N2) 8-K-Meldung ohne "
             "Quartalszahlen und am selben Tag ein Rutsch von mindestens 2 ATR → Short. Beide in jeder Marktlage.")


def _short(key, name, feuert, seed=None):
    return lambda sw: S.short_strategie(sw, key, name, feuert, marktfilter=False, zufall_seed=seed)


def pruefen(P, a, watch, sektor_von):
    zr = F.listen(P, a, len(watch))
    tickers = sorted({t for z in zr.values() for liste in z["listen"] for t in liste})
    herab, info_h = N.herabstufungen(tickers)
    print(N.abdeckung_md(zr, herab, info_h, tickers))
    meld, info_m = N.meldungen_8k(P.D, a.cache, tickers)
    print(N.abdeckung_md(zr, meld, info_m, tickers))

    def n1(d):
        return F.tage_maske(d, herab)

    def n2(d):
        return F.tage_maske(d, meld) & N.rutsch(d) & ~N.zahlen_tag(d)
    varianten = [
        {"key": "herabstufung", "kurz": "N1", "name": "+ Short nach Herabstufung durch einen Analysten",
         "anpassen": _short("herabstufung_short", "Herabstufung", n1),
         "zufall": lambda sw, s: _short("herabstufung_short", "Herabstufung", n1, s)(sw)},
        {"key": "meldung_rutsch", "kurz": "N2", "name": "+ Short nach Pflichtmeldung mit Kursrutsch",
         "anpassen": _short("meldung_short", "Meldung mit Rutsch", n2),
         "zufall": lambda sw, s: _short("meldung_short", "Meldung mit Rutsch", n2, s)(sw)},
    ]
    extra = "**Daten der Nachrichten:**\n\n" + "\n".join([N.abdeckung_md(zr, herab, info_h, tickers),
                                                         N.abdeckung_md(zr, meld, info_m, tickers)])
    idee = types.SimpleNamespace(NAME=NAME, QUELLE=QUELLE, BESCHREIBUNG=BESCHREIBUNG, VERMUTUNG=VERMUTUNG,
                                 WIDERLEGT_WENN=WIDERLEGT_WENN, VARIANTEN=VARIANTEN)
    return F.pruefen(P, a, sektor_von, idee, zr, varianten, len(watch), extra)
