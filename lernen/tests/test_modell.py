"""Lernmodell: lernt nur aus der Vergangenheit (Walk-forward) und erkennt ein eingebautes Muster."""
import numpy as np
import pandas as pd
import pytest

import merkmale as M
import modell as L


@pytest.fixture
def kand():
    """Erfundene gedachte Trades 2012–2016: Gewinn wahrscheinlicher bei hohem 6-Monats-Momentum."""
    rng = np.random.default_rng(1)
    n = 6000
    tage = pd.Timestamp("2012-01-02") + pd.to_timedelta(np.sort(rng.integers(0, 5 * 365, n)), unit="D")
    k = pd.DataFrame({c: rng.normal(size=n) for c in M.MERKMALE if c != "sektor_code"})
    k["mom126"] = rng.normal(size=n)
    gewinn = rng.random(n) < 1 / (1 + np.exp(-1.5 * k["mom126"]))
    k["R"] = np.where(gewinn, 1.0, -1.0)
    k["tag"] = tage
    k["ausstieg_tag"] = tage + pd.to_timedelta(rng.integers(1, 40, n), unit="D")
    k["status"] = "fertig"
    k["sektor"] = rng.choice(L.SEKTOREN[:-1], n)
    k["ticker"] = "T" + pd.Series(rng.integers(0, 50, n)).astype(str)
    return k


def test_bekannt_vor_nimmt_nur_abgeschlossene_trades(kand):
    tag = pd.Timestamp("2014-01-01")
    b = L.bekannt_vor(kand, tag)
    assert (b["ausstieg_tag"] < tag).all() and len(b) > 0
    assert len(L.bekannt_vor(kand.assign(status="laeuft"), tag)) == 0


def test_walk_forward_sieht_die_zukunft_nicht(kand, monkeypatch):
    monkeypatch.setattr(L, "MIN_TRAINING", 1000)
    p1 = L.walk_forward(kand, "2015-01-01", "2015-03-31")
    # Alles, was erst ab März 2015 feststand, wird verfälscht: Februar und Januar dürfen sich nicht ändern
    grenze = pd.Timestamp("2015-03-01")
    falsch = kand.copy()
    spaet = falsch["ausstieg_tag"] >= grenze
    falsch.loc[spaet, "R"] = -falsch.loc[spaet, "R"]
    falsch.loc[falsch["tag"] >= grenze, "mom126"] = 99.0
    p2 = L.walk_forward(falsch, "2015-01-01", "2015-03-31")
    vorher = (kand["tag"] < grenze) & (kand["tag"] >= pd.Timestamp("2015-01-01"))
    assert vorher.sum() > 100
    np.testing.assert_array_equal(p1[vorher].to_numpy(), p2[vorher].to_numpy())
    assert p1[kand["tag"] < pd.Timestamp("2015-01-01")].isna().all()  # davor keine Punktzahl


def test_modell_erkennt_das_muster(kand, monkeypatch):
    monkeypatch.setattr(L, "MIN_TRAINING", 1000)
    p = L.walk_forward(kand, "2015-01-01", "2016-12-31")
    g = L.guete(kand, p)
    assert g["auc"] > 0.65
    f = {x["fuenftel"]: x for x in g["fuenftel"]}
    assert f[5]["treffer"] > f[1]["treffer"]
    gelernt = L.was_gelernt(kand, pd.Timestamp("2016-12-31"))
    assert gelernt[0]["merkmal"] == "mom126" and gelernt[0]["richtung"] > 0


def test_schwelle_aus_den_zwoelf_monaten_davor(kand):
    k = kand.assign(punkte=np.linspace(0, 1, len(kand)))  # Punktzahl steigt mit der Zeit
    s = L.monats_schwellen(k, 0.3)
    m = pd.Period("2015-01", "M")
    vorher = k[(k["tag"] >= pd.Timestamp("2014-01-01")) & (k["tag"] < pd.Timestamp("2015-01-01"))]["punkte"]
    assert s[m] == pytest.approx(np.quantile(vorher, 0.7))
    assert s[pd.Period("2012-01", "M")] == np.inf  # ohne Vorgeschichte wird nichts gekauft


def test_leere_merkmale_stoeren_nicht(kand, monkeypatch):
    k = kand.copy()
    k["gewinnrendite"] = np.nan  # z. B. Bilanzdaten vor 2009
    m = L.trainiere(k)
    assert "gewinnrendite" not in m.lern_merkmale
    assert np.isfinite(L.punktzahl(m, k.head(5))).all()
