"""Sicherheits-Check: Rechnet der Bot mit den festen Testdaten genauso wie im gespeicherten Fingerabdruck?

Schlägt dieser Test fehl, hat eine Änderung die Kaufregeln verändert (Signale, Stop, Ziel, Limit, Lernregel,
Positionsgröße, Grenzen, Kosten …). Ist die Änderung absichtlich (nach einem ehrlichen Test):
python tests/fingerabdruck_neu.py ausführen und das im Pull Request deutlich vermerken."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hilfe  # noqa: E402

HINWEIS = ("Die Kaufregeln rechnen anders als im gespeicherten Fingerabdruck. Nur wenn die Änderung absichtlich ist "
           "(nach einem ehrlichen Test): python tests/fingerabdruck_neu.py und im Pull Request deutlich vermerken.")


def unterschiede(alt, neu, pfad="", n=8):
    """Die ersten paar Unterschiede als lesbare Zeilen."""
    aus = []
    if isinstance(alt, dict) and isinstance(neu, dict):
        for k in list(alt) + [k for k in neu if k not in alt]:  # Reihenfolge wie in der Datei: Regel-Zahlen zuerst
            if alt.get(k) != neu.get(k):
                aus += unterschiede(alt.get(k), neu.get(k), f"{pfad}.{k}", n - len(aus))
            if len(aus) >= n:
                break
    elif isinstance(alt, list) and isinstance(neu, list) and alt and isinstance(alt[0], list):
        for i in range(max(len(alt), len(neu))):
            a = alt[i] if i < len(alt) else None
            b = neu[i] if i < len(neu) else None
            if a != b:
                aus.append(f"{pfad}[{i}]: vorher {a} · jetzt {b}")
            if len(aus) >= n:
                break
    else:
        aus.append(f"{pfad}: vorher {alt} · jetzt {neu}")
    return aus


def test_kaufregeln_unveraendert():
    gespeichert = hilfe.lade_fingerabdruck()
    jetzt = hilfe.fingerabdruck()
    if jetzt != gespeichert:
        raise AssertionError(HINWEIS + "\n" + "\n".join(unterschiede(gespeichert, jetzt)))


def test_fingerabdruck_ist_aussagekraeftig():
    """Der Fingerabdruck soll wirklich etwas prüfen: viele Trades, mehrere Strategien, Pausen der Lernregel."""
    f = hilfe.lade_fingerabdruck()
    assert f["tagebuch"]["anzahl"] > 500
    assert f["depot"]["anzahl"] > 50
    assert len({t[1] for t in f["tagebuch"]["trades"]}) >= 6
    assert f["lernregel"], "die Lernregel sollte in den Testdaten mindestens einmal pausieren"
    assert any(t[4] == "vor Quartalszahlen" for t in f["depot"]["trades"]), "Quartalszahlen-Regel kommt nicht vor"
