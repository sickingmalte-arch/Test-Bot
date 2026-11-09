"""Hilfe für die Kaufzeit-Ideen (Wunsch des Nutzers für Fr 06.11.2026): ändert nur für den Test, WANN und ZU WELCHEM
KURS der Bot einsteigt – im Strategie-Tagebuch (Lernregel) und im Depot gleich.

  kurs(d, j)  Einstiegskurs am Ausführungstag j (heute: Eröffnung d["O"][j])
  start_off   Position zählt ab Tag j + start_off (−1 = schon ab dem Signaltag, Kauf zu dessen Schluss)
  versatz     Stop/Ziel erst ab Tag start + versatz prüfen (1 = Kauf zu einem Schlusskurs: der Kauftag zählt nicht mehr)
Kein Blick in die Zukunft: Der Kurs eines Tages wird nur benutzt, wenn der Kauf an diesem Tag wirklich möglich war."""
import inspect

ANKER_TB = [('einstieg = mit_spread(d["O"][j], r, True)', 'einstieg = mit_spread(EINSTIEG_KURS(d, j), r, True)'),
            ('pos = {"start": j, "stop": stop, "ziel": ziel}', 'pos = {"start": j + START_OFF, "stop": stop, "ziel": ziel}'),
            ('                k = j\n', '                k = j + START_OFF + VERSATZ\n')]
ANKER_DEPOT = [('ausfuehrung = mit_spread(d["O"][i], r, True)', 'ausfuehrung = mit_spread(EINSTIEG_KURS(d, i), r, True)'),
               ('spread_kosten += stueck * d["O"][i] * SPREAD / rate', 'spread_kosten += stueck * EINSTIEG_KURS(d, i) * SPREAD / rate'),
               ('"ziel": auftrag["ziel"], "start": i,', '"ziel": auftrag["ziel"], "start": i + START_OFF,'),
               ('letzter_kurs[t] = (d["O"][i], rate)', 'letzter_kurs[t] = (EINSTIEG_KURS(d, i), rate)'),
               ('            preis, grund = pruefe_ausstieg(d, i, p["richtung"], p)',
                '            if i < p["start"] + VERSATZ:\n                continue  # gekauft zum Schluss: dieser Tag zählt nicht mehr\n'
                '            preis, grund = pruefe_ausstieg(d, i, p["richtung"], p)')]


def _patch(sw, funktion, anker):
    src = inspect.getsource(getattr(sw, funktion))
    for alt, neu in anker:
        if src.count(alt) != 1:
            raise RuntimeError(f"{funktion}: Stelle nicht eindeutig gefunden: {alt!r}")
        src = src.replace(alt, neu)
    exec(compile(src, f"{funktion}_kaufzeit", "exec"), sw.__dict__)


def kaufzeit(sw, kurs, start_off=0, versatz=0):
    sw.EINSTIEG_KURS, sw.START_OFF, sw.VERSATZ = kurs, start_off, versatz

    def moeglich(d, i, r, stop, limit):
        k = kurs(d, i)
        return r * (k - stop) > 0 and r * (limit - k) >= 0
    sw.einstieg_moeglich = moeglich
    _patch(sw, "strategie_tagebuch", ANKER_TB)
    _patch(sw, "simuliere_depot", ANKER_DEPOT)
