"""Kalender-Bausteine für Ideen auf dem Prüfstand (Forschung vom 13.11.2026: Monatswechsel-Effekt).

Die Lage eines Handelstags im Monat hängt nur vom Börsenkalender ab, und der steht vorher fest – deshalb ist das kein
Blick in die Zukunft. Nur für den letzten, noch nicht fertigen Monat der Daten schätzt monatslage() die restlichen
Handelstage über die Werktage bis Monatsende (Feiertage dort nicht berücksichtigt; betrifft höchstens die letzten Tage
des Rückblicks)."""
import numpy as np
import pandas as pd

_CACHE = {}


def monatslage(idx):
    """Für jeden Handelstag: der wievielte Handelstag im Monat er ist (1 = erster) und wie viele Handelstage im Monat
    noch folgen (0 = letzter)."""
    idx = pd.DatetimeIndex(idx)
    schluessel = (len(idx), idx[0], idx[-1]) if len(idx) else (0,)
    if schluessel in _CACHE:
        return _CACHE[schluessel]
    tage = pd.Series(np.arange(len(idx)), index=idx)
    monat = idx.to_period("M")
    nr = tage.groupby(monat).cumcount().to_numpy() + 1
    rest = tage.groupby(monat).cumcount(ascending=False).to_numpy()
    if len(idx):
        letzter = idx[-1]
        ende = (letzter + pd.offsets.MonthEnd(0)).normalize()
        if letzter.normalize() < ende:  # letzter Monat noch nicht fertig: Werktage bis Monatsende dazuzählen
            fehlen = int(np.busday_count((letzter + pd.Timedelta(days=1)).date(), (ende + pd.Timedelta(days=1)).date()))
            rest = rest + np.where(monat == monat[-1], fehlen, 0)
    _CACHE[schluessel] = (nr, rest)
    return nr, rest


def nur_kauftage(fenster):
    """weg_fn für skill_hilfe.filtern: Ein Signal am Tag i führt zum Kauf am Tag i+1 (Eröffnung). Es fällt weg, wenn
    dieser Kauftag nicht im Fenster liegt. fenster(nr, rest) -> bool-Array je Handelstag."""
    def weg(ticker, d, key, feuert, stop, ziel):
        nr, rest = monatslage(d["idx"])
        drin = np.asarray(fenster(nr, rest), dtype=bool)
        kauftag_drin = np.append(drin[1:], True)  # letzter Tag: kein Kauf mehr im Rückblick
        return ~kauftag_drin
    return weg
