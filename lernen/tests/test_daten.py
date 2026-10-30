"""Datenteil: Aktienliste von Wikipedia (plus Watchlist), Kurse im Zwischenspeicher, Warnungen bei fehlenden Daten."""
import json
import os

import numpy as np
import pandas as pd
import pytest

import daten as D
import lernlauf as LAB


def _wiki_sp500(n=450):
    t = pd.DataFrame({"Symbol": [f"S{i}" for i in range(n - 2)] + ["BRK.B", "AAPL"],
                      "Security": [f"Firma {i}" for i in range(n)],
                      "GICS Sector": ["Information Technology"] * n, "GICS Sub-Industry": ["Software"] * n,
                      "Headquarters Location": ["X"] * n, "Date added": ["2000-01-01"] * n,
                      "CIK": list(range(1000, 1000 + n - 1)) + [320193]})
    aenderungen = pd.DataFrame({"Date": ["March 1, 2021"], "Added": ["S1"], "Removed": ["ALT"]})
    return "<html>" + t.to_html(index=False) + aenderungen.to_html(index=False) + "</html>"


def _wiki_ndx(n=101):
    t = pd.DataFrame({"Company": [f"N {i}" for i in range(n - 1)] + ["Apple"],
                      "Ticker": [f"N{i}" for i in range(n - 1)] + ["AAPL"],
                      "GICS Sector": ["Communication Services"] * n, "GICS Sub-Industry": ["Medien"] * n})
    klein = pd.DataFrame({"Jahr": [2020, 2021], "Wert": [1, 2]})  # andere Tabelle auf der Seite
    return "<html>" + klein.to_html(index=False) + t.to_html(index=False) + "</html>"


@pytest.fixture
def netz(monkeypatch):
    seiten = {D.WIKI_SP500: _wiki_sp500(), D.WIKI_NDX[1]: _wiki_ndx(),
              D.SEC_TICKER: json.dumps({"0": {"cik_str": 4242, "ticker": "N5", "title": "N 5"}})}

    def hole(url, versuche=3, pause=2.0):
        if url not in seiten:
            raise OSError("nicht erreichbar")
        return seiten[url]
    monkeypatch.setattr(D, "hole", hole)
    return seiten


def test_aktienliste(netz, tmp_path):
    uni, warnungen = D.lade_universum(str(tmp_path))
    assert warnungen == []
    assert len(uni) == 450 + 100  # AAPL steht in beiden Listen, zählt einmal
    zeile = uni.set_index("ticker")
    assert "BRK-B" in zeile.index  # Yahoo-Schreibweise
    assert zeile.loc["AAPL", "index"] == "S&P 500, Nasdaq-100"
    assert zeile.loc["N5", "cik"] == 4242  # CIK von der SEC ergänzt
    assert np.isnan(zeile.loc["N6", "cik"])
    assert os.path.exists(tmp_path / "universum.csv") and os.path.exists(tmp_path / "sp500_aenderungen.csv")


def test_aktienliste_ohne_nasdaq_und_ohne_netz(netz, tmp_path, monkeypatch):
    del netz[D.WIKI_NDX[1]]
    uni, warnungen = D.lade_universum(str(tmp_path))
    assert len(uni) == 450 and "Nasdaq-100-Liste" in warnungen[0]
    netz.clear()  # Wikipedia gar nicht erreichbar: gespeicherte Liste mit Warnung
    uni2, warnungen2 = D.lade_universum(str(tmp_path))
    assert len(uni2) == 450 and "gespeicherte Liste" in warnungen2[0]
    with pytest.raises(RuntimeError):
        D.lade_universum(str(tmp_path / "leer"))


def _kurse(tage, faktor=1.0):
    tage = pd.DatetimeIndex(tage)
    c = (10 + (tage - pd.Timestamp("2020-01-01")).days.to_numpy() / 1000) * faktor  # fester Kurs je Datum
    return pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c, "Volume": 1.0, "Roh": c, "Split": 0.0},
                        index=pd.DatetimeIndex(tage, name="Date"))


def test_kurse_nur_neue_tage_und_bei_dividende_ganz_neu(tmp_path, monkeypatch):
    heute = pd.Timestamp.today().normalize()
    alt_tage = pd.bdate_range(end=heute - pd.Timedelta(days=3), periods=300)
    alle_tage = pd.bdate_range(start=alt_tage[0], end=heute)
    cache = str(tmp_path)
    os.makedirs(os.path.join(cache, "kurse"))
    for t in ("A", "B"):
        _kurse(alt_tage).to_csv(D.kurs_datei(cache, t), compression="gzip")
    aufrufe = []

    def lade(tickers, start):
        aufrufe.append((tuple(tickers), start))
        ganz = start == D.START
        aus = {}
        for t in tickers:
            df = _kurse(alle_tage, 0.98 if t == "B" else 1.0)  # B: Yahoo hat alte Kurse umgerechnet
            aus[t] = df if ganz else df[df.index >= pd.Timestamp(start)]
        return aus
    monkeypatch.setattr(D, "_lade_yahoo", lade)
    _, warnungen = D.aktualisiere_kurse(["A", "B"], cache)
    assert warnungen == []
    assert aufrufe[0][0] == ("A", "B") and aufrufe[0][1] != D.START  # zuerst nur die letzten Tage
    assert aufrufe[1] == (("B",), D.START)  # B ganz neu
    a, b = D.lies_kurse(cache, "A"), D.lies_kurse(cache, "B")
    assert a.index[-1] == alle_tage[-1] and len(a) == len(alle_tage)
    assert b["Close"].iloc[-1] == pytest.approx(_kurse(alle_tage, 0.98)["Close"].iloc[-1])


def test_warnungen_bei_fehlenden_und_alten_kursen(tmp_path):
    uni = pd.DataFrame({"ticker": ["A", "B", "C"]})
    letzter = pd.Timestamp("2026-10-28")
    bis = {"A": letzter, "B": pd.Timestamp("2026-10-20"), "C": None}
    w = LAB.daten_warnungen(str(tmp_path), uni, bis, letzter, pd.Timestamp("2026-10-29"))
    text = " ".join(w)
    assert "Die Kurse vom 29.10.2026 fehlen noch" in text
    assert "Keine Kurse für 1 Aktien: C" in text
    assert "Alte Kurse (nicht bis 28.10.2026) bei 1 Aktien: B" in text
    assert "Ohne SEC-Bilanzdaten: 3 Aktien" in text


def test_erwarteter_tag_und_voller_tag():
    ny = "America/New_York"
    assert LAB.erwarteter_tag(pd.Timestamp("2026-10-29 17:00", tz=ny)) == pd.Timestamp("2026-10-29")
    assert LAB.erwarteter_tag(pd.Timestamp("2026-10-29 10:00", tz=ny)) == pd.Timestamp("2026-10-28")
    assert LAB.erwarteter_tag(pd.Timestamp("2026-11-01 12:00", tz=ny)) == pd.Timestamp("2026-10-30")  # Sonntag
    tage = pd.bdate_range("2026-10-20", "2026-10-29")
    bis = {f"T{i}": tage[-1] for i in range(8)} | {"X": tage[-2], "Y": tage[-2]}
    assert LAB.letzter_voller_tag(tage, bis) == tage[-2]  # nur 80 % haben den 29.10.
    bis["Y"] = tage[-1]
    assert LAB.letzter_voller_tag(tage, bis) == tage[-1]


def test_watchlist_kommt_dazu(netz, tmp_path):
    uni, _ = D.lade_universum(str(tmp_path), {"AAPL": "Information Technology", "SOFI": "Financials"})
    z = uni.set_index("ticker")
    assert z.loc["SOFI", "index"] == "Watchlist" and z.loc["SOFI", "sektor"] == "Financials"
    assert z.loc["AAPL", "index"] == "S&P 500, Nasdaq-100, Watchlist"
    assert len(uni) == 551
    assert D.watchlist("aapl, SOFI , xyz") == {"AAPL": "Information Technology", "SOFI": "Financials",
                                               "XYZ": "Unbekannt"}


def test_nasdaq_branchen_nach_icb_werden_gics(netz, tmp_path):
    t = pd.DataFrame({"Company": [f"N {i}" for i in range(100)], "Ticker": [f"N{i}" for i in range(100)],
                      "ICB Industry": ["Technology"] * 50 + ["Telecommunications"] * 50,
                      "ICB Subsector": ["Software"] * 50 + ["Telecommunications Services"] * 50})
    netz[D.WIKI_NDX[1]] = "<html>" + t.to_html(index=False) + "</html>"
    uni, _ = D.lade_universum(str(tmp_path), {"N1": "Communication Services"})
    z = uni.set_index("ticker")
    assert z.loc["N0", "sektor"] == "Information Technology" and z.loc["N0", "branche"] == "Software"
    assert z.loc["N60", "sektor"] == "Communication Services"
    assert z.loc["N1", "sektor"] == "Information Technology"  # schon ein GICS-Name: bleibt
