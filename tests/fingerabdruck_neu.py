"""Fingerabdruck der Kaufregeln neu erzeugen – NUR nach einer absichtlichen Regeländerung.

Aufruf (im Ordner des Repositorys):  python tests/fingerabdruck_neu.py

Die Kaufregeln sind bis Ende Januar 2027 eingefroren, damit das Übungsdepot ehrlich messen kann. Wer den
Fingerabdruck trotzdem neu erzeugt, muss das im Pull Request deutlich schreiben („Regeländerung: Fingerabdruck neu
erzeugt“) und begründen. Der Test tests/test_fingerabdruck.py vergleicht danach mit der neuen Datei."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hilfe  # noqa: E402

alt = hilfe.lade_fingerabdruck() if hilfe.FINGERABDRUCK.exists() else None
neu = hilfe.fingerabdruck()
hilfe.speichere_fingerabdruck(neu)
print(f"Fingerabdruck geschrieben: {hilfe.FINGERABDRUCK.relative_to(hilfe.WURZEL)}")
print(f"  Tagebuch: {neu['tagebuch']['anzahl']} gedachte Trades · Depot: {neu['depot']['anzahl']} Trades · "
      f"Endwert {neu['depot']['end_wert']:.2f} €")
if alt is not None and alt != neu:
    print("  ⚠️ Anders als vorher – das ist eine Regeländerung. Im Pull Request deutlich vermerken!")
elif alt is not None:
    print("  Unverändert.")
