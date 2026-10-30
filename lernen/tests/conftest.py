"""Gemeinsame Hilfen für die Tests des Lernmodells."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

HIER = os.path.dirname(os.path.abspath(__file__))
LERNEN = os.path.dirname(HIER)
sys.path.insert(0, LERNEN)
DATEN = os.path.join(HIER, "daten")


def kunst_kurse(n=900, start="2015-01-02", seed=0, trend=0.0004):
    """Erfundene, aber feste Tageskerzen (Zufallsweg mit Startwert) für Tests ohne echte Daten."""
    rng = np.random.default_rng(seed)
    tage = pd.bdate_range(start, periods=n)
    r = rng.normal(trend, 0.018, n)
    c = 50 * np.exp(np.cumsum(r))
    o = c * np.exp(rng.normal(0, 0.006, n))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.008, n)))
    l = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.008, n)))
    v = rng.integers(1_000_000, 3_000_000, n).astype(float)
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}, index=tage)


@pytest.fixture
def daten_ordner():
    return DATEN
