"""52-Wochen-Hoch (George & Hwang 2004, „The 52-Week High and Momentum Investing“, Journal of Finance 59(5),
2145–2176): Wie nah eine Aktie an ihrem 52-Wochen-Hoch steht, sagt künftige Renditen besser voraus als die vergangene
Rendite selbst. Erklärung: Anleger nehmen das alte Hoch als Anker und kaufen gute Nachrichten nahe dem Hoch zu
zögerlich – der Kurs zieht verzögert nach. Für den Bot: Kauf-Signale weit unter dem 52-Wochen-Hoch weglassen.

Gemessen am Signaltag: Schlusskurs geteilt durch das höchste Tageshoch der letzten 252 Börsentage bis einschließlich
dieses Tages – am Abend bekannt, kein Blick in die Zukunft. Mit weniger als 200 Tagen Vorlauf zählt kein Wert (das
Signal bleibt)."""
import numpy as np
import pandas as pd

QUELLE = ("George & Hwang (2004), „The 52-Week High and Momentum Investing“, Journal of Finance 59(5), 2145–2176 – "
          "Nähe zum 52-Wochen-Hoch sagt künftige Renditen voraus (Anker-Effekt); Folgearbeiten sehen den Effekt vor "
          "allem in zuversichtlichen Marktphasen.")


def naehe(d):
    """Schluss / höchstes Hoch der letzten 252 Börsentage (bis einschließlich Tag i); NaN bei zu kurzem Vorlauf."""
    c = np.asarray(d["C"], dtype=float)
    h = np.asarray(d.get("H", d["C"]), dtype=float)
    hoch = pd.Series(h).rolling(252, min_periods=200).max().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        return c / hoch


def weg_unter(anteil):
    """weg_fn für skill_hilfe.filtern: Signal fällt weg, wenn der Schluss unter `anteil` des 52-Wochen-Hochs liegt."""
    def weg(ticker, d, key, feuert, stop, ziel):
        n = naehe(d)
        with np.errstate(invalid="ignore"):
            return np.nan_to_num(n, nan=1.0) < anteil
    return weg
