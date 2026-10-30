"""Bilanzdaten nur so, wie sie damals bekannt waren (Point-in-time)."""
import numpy as np
import pandas as pd

import daten as D
import merkmale as M


def _fakt(start, ende, wert, eingereicht, form="10-Q"):
    return {"start": start, "end": ende, "val": wert, "filed": eingereicht, "form": form}


def test_nur_erste_veroeffentlichung_zaehlt():
    fakten = {"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
        _fakt("2020-01-01", "2020-12-31", 100, "2021-02-10", "10-K"),
        _fakt("2020-01-01", "2020-12-31", 90, "2022-02-10", "10-K"),  # später korrigiert
        _fakt("2020-01-01", "2020-12-31", 80, "2021-03-01", "8-K"),  # keine Quartals-/Jahresmeldung
    ]}}}}}
    z = D.bilanz_zeilen(fakten)
    assert len(z) == 1
    assert z.iloc[0]["wert"] == 100 and z.iloc[0]["eingereicht"] == "2021-02-10"


def test_vorrang_bei_gleichem_tag():
    fakten = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [_fakt("2020-01-01", "2020-03-31", 50, "2020-05-01")]}},
        "SalesRevenueNet": {"units": {"USD": [_fakt("2020-01-01", "2020-03-31", 49, "2020-05-01")]}},
    }}}
    z = D.bilanz_zeilen(fakten)
    assert list(z["wert"]) == [50]  # „Revenues“ hat Vorrang


def _zeilen(liste):
    df = pd.DataFrame(liste, columns=["gruppe", "start", "ende", "wert", "eingereicht"])
    for c in ("start", "ende", "eingereicht"):
        df[c] = pd.to_datetime(df[c])
    df["dauer"] = (df["ende"] - df["start"]).dt.days
    return df


def test_ttm_aus_jahr_halbjahr_und_quartalen():
    r = _zeilen([
        ("umsatz", "2020-01-01", "2020-12-31", 400, "2021-02-10"),  # Jahr 2020
        ("umsatz", "2020-01-01", "2020-06-30", 190, "2020-08-01"),  # 1. Halbjahr 2020
        ("umsatz", "2021-01-01", "2021-06-30", 230, "2021-08-01"),  # 1. Halbjahr 2021
    ])
    ende = pd.Timestamp("2021-06-30")
    # nach der Halbjahresmeldung: 230 + 400 − 190 = 440
    assert M._ttm(r, ende, pd.Timestamp("2021-08-01")) == 440
    # einen Tag vorher war das Halbjahr 2021 noch nicht veröffentlicht
    assert np.isnan(M._ttm(r, ende, pd.Timestamp("2021-07-31")))
    assert M._ttm(r, pd.Timestamp("2020-12-31"), pd.Timestamp("2021-03-01")) == 400
    q = _zeilen([("gewinn", f"2020-{m:02d}-01", e, 10 * k, "2021-01-30")
                 for k, (m, e) in enumerate([(1, "2020-03-31"), (4, "2020-06-30"), (7, "2020-09-30"),
                                             (10, "2020-12-31")], start=1)])
    assert M._ttm(q, pd.Timestamp("2020-12-31"), pd.Timestamp("2021-02-01")) == 100  # 4 Quartale


def test_merkmale_erst_ab_dem_tag_nach_der_veroeffentlichung():
    tage = pd.bdate_range("2021-01-04", "2021-03-31")
    roh = pd.Series(10.0, index=tage)
    split = pd.Series(0.0, index=tage)
    bilanz = _zeilen([
        ("umsatz", "2020-01-01", "2020-12-31", 1000, "2021-02-10"),
        ("gewinn", "2020-01-01", "2020-12-31", 100, "2021-02-10"),
        ("aktien", "2020-01-01", "2020-12-31", 50, "2021-02-10"),
        ("eigenkapital", None, "2020-12-31", 400, "2021-02-10"),
    ]).drop(columns="dauer")
    m = M.bilanz_reihen(tage, bilanz, roh, split)
    assert m.loc[:"2021-02-10", "gewinnrendite"].isna().all()
    # Börsenwert 10 × 50 = 500, Gewinn 100 -> Gewinnrendite 20 %, Buchwert 400 -> 0,8, Marge 10 %
    assert m.loc["2021-02-11", "gewinnrendite"] == 0.2
    assert m.loc["2021-02-11", "buchwertrendite"] == 0.8
    assert m.loc["2021-02-11", "nettomarge"] == 0.1


def test_aktienzahl_nach_split_auf_heutige_basis():
    tage = pd.bdate_range("2021-01-04", "2021-04-30")
    roh = pd.Series(10.0, index=tage)  # Kurs schon splitbereinigt
    split = pd.Series(0.0, index=tage)
    split[pd.Timestamp("2021-03-01")] = 2.0  # 2:1-Split nach dem Periodenende
    bilanz = _zeilen([("gewinn", "2020-01-01", "2020-12-31", 100, "2021-02-10"),
                      ("aktien", "2020-01-01", "2020-12-31", 50, "2021-02-10")]).drop(columns="dauer")
    m = M.bilanz_reihen(tage, bilanz, roh, split)
    # 50 Aktien damals = 100 Aktien heute -> Börsenwert 1000, Gewinnrendite 10 % (nicht 20 %)
    assert m.loc["2021-04-01", "gewinnrendite"] == 0.1
