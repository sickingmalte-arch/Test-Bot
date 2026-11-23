"""MAX-Effekt (Bali, Cakici & Whitelaw 2011, „Maxing Out: Stocks as Lotteries and the Cross-Section of Expected
Returns“, Journal of Financial Economics 99(2), 427–446): Aktien mit dem größten Tagesplus im letzten Monat brachten
danach im Schnitt über 1 % im Monat weniger als Aktien mit dem kleinsten. Die Autoren erklären das mit Anlegern, die
wie beim Lotto für die kleine Chance auf einen großen Sprung zu viel bezahlen; Gorman u. a. (2022, Critical Finance
Review) sehen eher eine Übertreibung nach dem Sprung. Für den Bot: Kauf-Signale nach so einem Sprung weglassen.

Gemessen am Signaltag: größtes Tagesplus (Schluss zu Schluss) der letzten 21 Börsentage bis einschließlich dieses
Tages – am Abend bekannt, kein Blick in die Zukunft."""
import numpy as np
import pandas as pd

QUELLE = ("Bali, Cakici & Whitelaw (2011), „Maxing Out: Stocks as Lotteries and the Cross-Section of Expected "
          "Returns“, Journal of Financial Economics 99(2), 427–446; Gegenstimme: Gorman, Akhtar, Durand & Gould "
          "(2022), Critical Finance Review (eher Übertreibung als Lotto-Lust).")


def max21(d):
    """Größtes Tagesplus der letzten 21 Börsentage (bis einschließlich Tag i)."""
    c = np.asarray(d["C"], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.r_[np.nan, c[1:] / c[:-1] - 1]
    return pd.Series(r).rolling(21, min_periods=15).max().to_numpy()


def weg_absolut(grenze):
    """weg_fn für skill_hilfe.filtern: Signal fällt weg, wenn das größte Tagesplus mindestens `grenze` war."""
    def weg(ticker, d, key, feuert, stop, ziel):
        with np.errstate(invalid="ignore"):
            return np.nan_to_num(max21(d), nan=0.0) >= grenze
    return weg


def weg_relativ(faktor):
    """weg_fn: Signal fällt weg, wenn das größte Tagesplus mindestens `faktor` × ATR (in % vom Kurs) war."""
    def weg(ticker, d, key, feuert, stop, ziel):
        c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            schwelle = faktor * atr / c
            return np.nan_to_num(max21(d), nan=0.0) >= np.nan_to_num(schwelle, nan=np.inf)
    return weg
