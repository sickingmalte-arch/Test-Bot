"""Tests für den Broker-Bot (broker/broker_bot.py) mit einem nachgebauten Alpaca-Konto: Probelauf sendet nichts,
Kauf zur Eröffnung nur bis zum Limit, Stop und Ziel als OCO, Verkauf zum Schluss vor Quartalszahlen und am
Zeitstopp, kein doppeltes Senden, Obergrenze je Order. Echte Orders oder Internet gibt es hier nicht."""
import copy
import importlib.util
import json
import pathlib

WURZEL = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("broker_bot", WURZEL / "broker" / "broker_bot.py")
bb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bb)

DEPOT = json.loads((WURZEL / "tests" / "daten" / "broker_depot.json").read_text(encoding="utf-8"))
VOR_OEFFNUNG = {"is_open": False, "timestamp": "2026-10-28T08:00:00-04:00",
                "next_open": "2026-10-28T09:30:00-04:00", "next_close": "2026-10-28T16:00:00-04:00"}


class FakeAlpaca:
    """Merkt sich Positionen und Orders wie ein Alpaca-Paper-Konto (nur was der Bot nutzt)."""

    def __init__(self, positionen=(), uhr=VOR_OEFFNUNG):
        self.pos = [{"symbol": t, "qty": str(q), "side": "long" if q > 0 else "short", "avg_entry_price": str(e),
                     "market_value": str(q * e)} for t, q, e in positionen]
        self.orders, self.gesendet, self.storniert, self.geschlossen, self._uhr = [], [], [], [], uhr

    def konto(self):
        return {"equity": "100000", "cash": "90000", "trading_blocked": False}

    def uhr(self):
        return self._uhr

    def positionen(self):
        return self.pos

    def offene_orders(self):
        return self.orders

    def order(self, daten):
        if any(o["client_order_id"] == daten["client_order_id"] for o in self.orders):
            raise bb.BrokerFehler(422, "client_order_id must be unique")
        o = dict(daten, id=f"o{len(self.gesendet)}", status="new")
        if daten.get("order_class") == "oco":
            o["limit_price"] = daten["take_profit"]["limit_price"]
            o["legs"] = [{"stop_price": daten["stop_loss"]["stop_price"]}]
        self.orders.append(o)
        self.gesendet.append(o)
        return o

    def storniere(self, order_id):
        self.storniert.append(order_id)
        self.orders = [o for o in self.orders if o["id"] != order_id]

    def schliesse(self, sym):
        self.geschlossen.append(sym)


def lauf(tmp_path, api, depot, uebersicht=None, scharf=True, monkeypatch=None, max_order=None):
    (tmp_path / "depot.json").write_text(json.dumps(depot), encoding="utf-8")
    (tmp_path / "daten.json").write_text(json.dumps(uebersicht or {"daten_bis": depot["bis"], "signale": [
        {"ticker": "PLTR", "art": "kaufen", "stueck": 4.0}]}), encoding="utf-8")
    monkeypatch.setenv("BROKER_AN", "ja" if scharf else "nein")
    if max_order:
        monkeypatch.setenv("BROKER_MAX_ORDER", str(max_order))
    else:
        monkeypatch.delenv("BROKER_MAX_ORDER", raising=False)
    return bb.main(["--depot", str(tmp_path / "depot.json"), "--uebersicht", str(tmp_path / "daten.json"),
                    "--bericht", str(tmp_path / "BERICHT.md"), "--protokoll", str(tmp_path / "protokoll.json")],
                   api=api)


def wie_im_depot(depot):
    return [(p["ticker"], p["stueck"], round(p["einstieg_usd"], 2)) for p in depot["positionen"]]


def test_probelauf_sendet_nichts(tmp_path, monkeypatch):
    api = FakeAlpaca(wie_im_depot(DEPOT))
    erg = lauf(tmp_path, api, DEPOT, scharf=False, monkeypatch=monkeypatch)
    assert erg["aktionen"] and all(a["status"] == "Probe" for a in erg["aktionen"])
    assert api.gesendet == [] and api.storniert == []
    assert "Probelauf" in (tmp_path / "BERICHT.md").read_text(encoding="utf-8")


def test_vor_quartalszahlen_zum_schluss_und_sonst_stop_und_ziel(tmp_path, monkeypatch):
    api = FakeAlpaca(wie_im_depot(DEPOT))
    erg = lauf(tmp_path, api, DEPOT, monkeypatch=monkeypatch)
    nach = {o["symbol"]: o for o in api.gesendet}
    # NOW meldet am 28.10. nach Börsenschluss, LLY am 29.10. vor Börsenbeginn: beide heute zum Schluss raus
    for t, stueck in (("NOW", "8"), ("LLY", "1")):
        assert nach[t]["time_in_force"] == "cls" and nach[t]["side"] == "sell" and nach[t]["qty"] == stueck
    for p in DEPOT["positionen"]:
        if p["ticker"] in ("NOW", "LLY"):
            continue
        o = nach[p["ticker"]]
        assert o["order_class"] == "oco" and o["time_in_force"] == "gtc" and o["side"] == "sell"
        assert o["take_profit"]["limit_price"] == f"{p['ziel']:.2f}"
        assert o["stop_loss"]["stop_price"] == f"{p['stop']:.2f}"
    assert "PLTR" not in nach  # Depot voll (5/5): verfällt wie im Übungsdepot
    assert any("Depot voll" in h for h in erg["hinweise"])


def test_kauf_zur_eroeffnung_bis_zum_limit(tmp_path, monkeypatch):
    depot = copy.deepcopy(DEPOT)
    depot["positionen"] = [p for p in depot["positionen"] if p["ticker"] in ("HIMS", "LLY")]
    api = FakeAlpaca(wie_im_depot(depot))
    lauf(tmp_path, api, depot, monkeypatch=monkeypatch)
    kauf = [o for o in api.gesendet if o["symbol"] == "PLTR"]
    assert len(kauf) == 1
    assert kauf[0]["time_in_force"] == "opg" and kauf[0]["type"] == "limit" and kauf[0]["side"] == "buy"
    assert kauf[0]["qty"] == "4" and kauf[0]["limit_price"] == f"{depot['auftraege'][0]['limit']:.2f}"


def test_zweiter_lauf_sendet_nichts_doppelt(tmp_path, monkeypatch):
    depot = copy.deepcopy(DEPOT)
    depot["positionen"] = [p for p in depot["positionen"] if p["ticker"] in ("HIMS", "LLY", "NOW")]
    api = FakeAlpaca(wie_im_depot(depot))
    lauf(tmp_path, api, depot, monkeypatch=monkeypatch)
    vorher = len(api.gesendet)
    assert vorher == 4  # Schutz HIMS und LLY, NOW zum Schluss, Kauf PLTR
    erg = lauf(tmp_path, api, depot, monkeypatch=monkeypatch)
    assert len(api.gesendet) == vorher and erg["aktionen"] == []


def test_depot_nicht_aktuell_nur_schutz(tmp_path, monkeypatch):
    spaeter = {"is_open": False, "timestamp": "2026-10-29T08:00:00-04:00",
               "next_open": "2026-10-29T09:30:00-04:00", "next_close": "2026-10-29T16:00:00-04:00"}
    api = FakeAlpaca(wie_im_depot(DEPOT) + [("TSLA", 3, 400.0)], uhr=spaeter)
    erg = lauf(tmp_path, api, DEPOT, monkeypatch=monkeypatch)
    assert {a["art"] for a in erg["aktionen"]} == {"schutz"}
    assert any("Stand vom 2026-10-27" in h for h in erg["hinweise"])


def test_position_nicht_mehr_im_depot_wird_verkauft(tmp_path, monkeypatch):
    api = FakeAlpaca(wie_im_depot(DEPOT) + [("TSLA", 3, 400.0)])
    lauf(tmp_path, api, DEPOT, monkeypatch=monkeypatch)
    tsla = [o for o in api.gesendet if o["symbol"] == "TSLA"]
    assert len(tsla) == 1 and tsla[0]["type"] == "market" and tsla[0]["side"] == "sell" and tsla[0]["qty"] == "3"


def test_obergrenze_je_order(tmp_path, monkeypatch):
    depot = copy.deepcopy(DEPOT)
    depot["positionen"] = []
    api = FakeAlpaca()
    erg = lauf(tmp_path, api, depot, monkeypatch=monkeypatch, max_order=500)
    assert api.gesendet == [] and any("Obergrenze" in h for h in erg["hinweise"])


def test_zeitstopp_am_zwanzigsten_handelstag(tmp_path, monkeypatch):
    depot = copy.deepcopy(DEPOT)
    depot["positionen"] = [dict(p, kauf_tag="2026-09-30") for p in depot["positionen"] if p["ticker"] == "HIMS"]
    depot["termine"] = {}
    api = FakeAlpaca(wie_im_depot(depot))
    erg = lauf(tmp_path, api, depot, monkeypatch=monkeypatch)
    (hims,) = [a for a in erg["aktionen"] if a["ticker"] == "HIMS"]
    assert hims["art"] == "schliessen_zum_schluss" and hims["grund"] == "Zeitstopp"


def test_short_wird_mit_kauf_abgesichert(tmp_path, monkeypatch):
    depot = copy.deepcopy(DEPOT)
    (p,) = [dict(p) for p in depot["positionen"] if p["ticker"] == "HIMS"]
    p.update(richtung=-1, stop=p["ziel"], ziel=p["stop"])
    depot["positionen"], depot["auftraege"], depot["termine"] = [p], [], {}
    api = FakeAlpaca([("HIMS", -p["stueck"], 29.4)])
    lauf(tmp_path, api, depot, monkeypatch=monkeypatch)
    (o,) = api.gesendet
    assert o["order_class"] == "oco" and o["side"] == "buy"
