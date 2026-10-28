"""Broker-Bot: führt die Entscheidungen des Swing-Bots als echte Orders im Paper-Konto von Alpaca aus.

Der Bot erfindet keine eigenen Signale. Er spiegelt das Übungsdepot des Swing-Bots (papier/papier_depot.json) in
ein Alpaca-Konto mit Spielgeld und misst, wie weit echte Ausführungen von der Simulation abweichen:

- Kauf zur Eröffnung nur bis zum Limit (Limit-Order für die Eröffnungsauktion), Stückzahl aus dem Handelsplan
  (docs/daten.json), nur Aufträge, die das Übungsdepot zur Eröffnung wirklich ausführt (gleiche Grenzen).
- Stop und Ziel liegen beim Broker als OCO-Order (eine streicht die andere), solange die Position läuft.
- Vor Quartalszahlen und nach 20 Handelstagen: Verkauf zum Schlusskurs (Schlussauktion), wie im Übungsdepot.
- Hat das Übungsdepot eine Position geschlossen, die beim Broker noch offen ist: Verkauf zum nächsten Kurs.
- Verpasste Käufe werden nicht nachgeholt (kein Hinterherlaufen).

Sicherheit: nur die Paper-Adresse von Alpaca (Spielgeld). Ohne BROKER_AN=ja nur Probelauf (zeigt, was er täte).
Höchstbetrag je Order (BROKER_MAX_ORDER, Standard 5.000 $). Er fasst nur Orders an, die er selbst angelegt hat.

Aufruf:
    ALPACA_KEY_ID=… ALPACA_SECRET_KEY=… BROKER_AN=ja python broker/broker_bot.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

WURZEL = pathlib.Path(__file__).resolve().parents[1]
PAPER_URL = "https://paper-api.alpaca.markets"  # nur Spielgeld; echtes Geld bewusst nicht vorgesehen
PRAEFIX = "tb-"                                  # client_order_id aller Orders dieses Bots
MAX_ORDER_USD = 5_000.0
PREIS_TOLERANZ = 0.005                           # Stop/Ziel beim Broker weichen mehr ab: Schutz-Order erneuern


def swing_bot():
    """swing_scanner.py als Modul (nur lesend: Börsenkalender, Quartalszahlen-Regel, Grenzen des Depots)."""
    spec = importlib.util.spec_from_file_location("swing_scanner", WURZEL / "swing_scanner.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class BrokerFehler(Exception):
    def __init__(self, status, text):
        super().__init__(f"Alpaca antwortet {status}: {text}")
        self.status = status


class Alpaca:
    """Kleiner Client für die Trading-API v2 von Alpaca (nur das, was der Bot braucht)."""

    def __init__(self, schluessel, geheim, url=PAPER_URL):
        self.url, self.kopf = url.rstrip("/"), {"APCA-API-KEY-ID": schluessel, "APCA-API-SECRET-KEY": geheim,
                                               "Content-Type": "application/json"}

    def _anfrage(self, methode, pfad, daten=None, parameter=None):
        url = self.url + pfad + ("?" + urllib.parse.urlencode(parameter) if parameter else "")
        koerper = json.dumps(daten).encode() if daten is not None else None
        anfrage = urllib.request.Request(url, data=koerper, headers=self.kopf, method=methode)
        try:
            with urllib.request.urlopen(anfrage, timeout=20) as antwort:
                text = antwort.read().decode()
        except urllib.error.HTTPError as fehler:
            raise BrokerFehler(fehler.code, fehler.read().decode(errors="replace")[:300]) from fehler
        except urllib.error.URLError as fehler:
            raise BrokerFehler("keine Verbindung", str(fehler.reason)) from fehler
        return json.loads(text) if text else None

    def konto(self):
        return self._anfrage("GET", "/v2/account")

    def uhr(self):
        return self._anfrage("GET", "/v2/clock")

    def positionen(self):
        return self._anfrage("GET", "/v2/positions")

    def offene_orders(self):
        return self._anfrage("GET", "/v2/orders", parameter={"status": "open", "nested": "true", "limit": 500})

    def order(self, daten):
        return self._anfrage("POST", "/v2/orders", daten)

    def storniere(self, order_id):
        return self._anfrage("DELETE", f"/v2/orders/{order_id}")

    def schliesse(self, symbol):
        return self._anfrage("DELETE", f"/v2/positions/{urllib.parse.quote(symbol)}")


# ---------------------------------------------------------------------------------------------------------------
# Lage lesen
# ---------------------------------------------------------------------------------------------------------------

def symbol(ticker):
    return ticker.replace("-", ".")  # Yahoo BRK-B -> Alpaca BRK.B


def preis(x):
    """Alpaca nimmt ab 1 $ höchstens 2, darunter 4 Nachkommastellen."""
    return f"{x:.2f}" if x >= 1 else f"{x:.4f}"


def menge(x):
    """Stückzahl für Alpaca: ganze Stück ohne Nachkommastellen."""
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def broker_lage(api):
    """Positionen und offene Orders des Bots beim Broker, je Symbol."""
    positionen = {}
    for p in api.positionen():
        r = -1 if p.get("side") == "short" or float(p["qty"]) < 0 else 1
        positionen[p["symbol"]] = {"richtung": r, "stueck": abs(float(p["qty"])),
                                   "einstand": float(p["avg_entry_price"]), "wert": float(p.get("market_value", 0))}
    orders = {}
    for o in api.offene_orders():
        if str(o.get("client_order_id", "")).startswith(PRAEFIX):
            orders.setdefault(o["symbol"], []).append(o)
    return positionen, orders


def handelstag(uhr):
    """Der Handelstag, um den es geht: heute, wenn die Börse offen ist, sonst der nächste Börsentag."""
    if uhr["is_open"]:
        return pd.Timestamp(uhr["timestamp"]).tz_convert("America/New_York").normalize().tz_localize(None)
    return pd.Timestamp(uhr["next_open"]).tz_convert("America/New_York").normalize().tz_localize(None)


def schutz_order(orders):
    """Die OCO-Order (Stop + Ziel) des Bots für ein Symbol: (Order, Ziel, Stop) oder None."""
    for o in orders:
        if o.get("order_class") == "oco":
            beine = o.get("legs") or []
            stop = next((float(b["stop_price"]) for b in beine if b.get("stop_price")), None)
            return o, float(o["limit_price"]), stop
    return None


def raus_zum_schluss(sw, position, termine, tag):
    """Muss die Position heute zum Schluss raus? Gleiche Regel wie im Übungsdepot: am letzten Handelstag vor dem
    Reaktionstag der Quartalszahlen oder am 20. Handelstag (Einstiegstag mitgezählt)."""
    naechster = tag + sw.NYSE_TAG
    for termin in termine or []:
        reak = sw.reaktionstag(pd.Timestamp(termin).tz_convert(sw.NY))
        if tag < reak <= naechster:
            return "vor Quartalszahlen"
    tage = len(pd.date_range(pd.Timestamp(position["kauf_tag"]), tag, freq=sw.NYSE_TAG))
    if tage >= sw.ZEITSTOPP_TAGE:
        return "Zeitstopp"
    return None


# ---------------------------------------------------------------------------------------------------------------
# Plan: was heute zu tun ist
# ---------------------------------------------------------------------------------------------------------------

def plane(sw, depot, uebersicht, positionen, orders, uhr, max_order=MAX_ORDER_USD):
    """Vergleicht Übungsdepot und Broker und gibt (Aktionen, Hinweise) zurück. Rechnet nur, sendet nichts."""
    tag = handelstag(uhr)
    vortag = tag - sw.NYSE_TAG
    aktuell = depot.get("bis") == vortag.strftime("%Y-%m-%d")
    aktionen, hinweise = [], []
    if not aktuell:
        hinweise.append(f"Das Übungsdepot ist auf dem Stand vom {depot.get('bis')}, für den Handelstag "
                        f"{tag:%d.%m.%Y} wäre {vortag:%d.%m.%Y} nötig. Heute nur Stop und Ziel pflegen, keine Käufe "
                        f"und Verkäufe nach dem Depot (der Morgen-Lauf des Swing-Bots fehlt noch).")
    im_depot = {symbol(p["ticker"]): p for p in depot["positionen"]}

    # 1. Positionen, die das Übungsdepot nicht mehr hat: verkaufen
    for sym, b in positionen.items():
        if sym in im_depot:
            continue
        if aktuell:
            aktionen.append({"art": "schliessen", "ticker": sym, "richtung": b["richtung"], "stueck": b["stueck"],
                             "grund": "nicht mehr im Übungsdepot (dort Stop, Ziel, Zeitstopp oder Zahlen)"})
        else:
            hinweise.append(f"{sym}: beim Broker offen, im Übungsdepot nicht – wartet auf den Morgen-Lauf.")

    # 2. Gemeinsame Positionen: heute zum Schluss raus oder Stop und Ziel absichern
    for sym, p in im_depot.items():
        b = positionen.get(sym)
        if b is None:
            hinweise.append(f"{sym}: im Übungsdepot, beim Broker nicht (Kauf verpasst oder Limit nicht erreicht) – "
                            f"wird nicht nachgekauft.")
            continue
        if b["stueck"] != p["stueck"]:
            hinweise.append(f"{sym}: Broker {b['stueck']:g} Stück, Übungsdepot {p['stueck']:g} Stück.")
        eigene = orders.get(sym, [])
        grund = raus_zum_schluss(sw, p, depot.get("termine", {}).get(p["ticker"]), tag) if aktuell else None
        if grund:
            if not any(o.get("time_in_force") == "cls" for o in eigene):
                aktionen.append({"art": "schliessen_zum_schluss", "ticker": sym, "richtung": b["richtung"],
                                 "stueck": b["stueck"], "grund": grund})
            continue
        schutz = schutz_order(eigene)
        passt = (schutz is not None and schutz[2] is not None
                 and abs(schutz[1] / p["ziel"] - 1) <= PREIS_TOLERANZ and abs(schutz[2] / p["stop"] - 1) <= PREIS_TOLERANZ
                 and float(schutz[0]["qty"]) == b["stueck"])
        if not passt:
            aktionen.append({"art": "schutz", "ticker": sym, "richtung": b["richtung"], "stueck": b["stueck"],
                             "stop": p["stop"], "ziel": p["ziel"],
                             "grund": "Stop und Ziel fehlen" if schutz is None else "Stop und Ziel angepasst"})

    # 3. Neue Käufe zur Eröffnung: nur, was das Übungsdepot zur Eröffnung wirklich ausführt
    if aktuell and uhr["is_open"] and depot["auftraege"]:
        hinweise.append("Die Börse ist schon offen: Käufe zur Eröffnung sind für heute verpasst (der Lauf kam zu spät).")
    elif aktuell:
        ok, verfallen, nachruecker = sw.ausfuehrbare_auftraege(depot)
        for grund, ticker in verfallen.items():
            hinweise.append(f"Verfällt wie im Übungsdepot ({grund}): {', '.join(ticker)}")
        if nachruecker:
            hinweise.append(f"Nachrücker (nur wenn ein Kauf davor nicht klappt, wird nicht gespiegelt): "
                            f"{', '.join(a['ticker'] for a in nachruecker)}")
        stueck_plan = {s["ticker"]: s.get("stueck") for s in (uebersicht or {}).get("signale", [])
                       if s.get("art") in ("kaufen", "short")}
        plan_aktuell = (uebersicht or {}).get("daten_bis") == depot.get("bis")
        for a in ok:
            sym = symbol(a["ticker"])
            stueck = stueck_plan.get(a["ticker"]) if plan_aktuell else None
            if sym in positionen or any(o.get("time_in_force") == "opg" for o in orders.get(sym, [])):
                continue
            if not stueck:
                hinweise.append(f"{sym}: keine Stückzahl im Handelsplan (docs/daten.json) – nicht gekauft.")
                continue
            if stueck * a["limit"] > max_order:
                hinweise.append(f"{sym}: {stueck:g} × {a['limit']:.2f} $ = {stueck * a['limit']:,.0f} $ liegt über "
                                f"der Obergrenze von {max_order:,.0f} $ je Order – nicht gekauft.")
                continue
            aktionen.append({"art": "kaufen", "ticker": sym, "richtung": a["richtung"], "stueck": stueck,
                             "limit": a["limit"], "stop": a["stop"], "ziel": a["ziel"],
                             "grund": f"Signal {a['strategie']} aus dem Übungsdepot"})
    return aktionen, hinweise, tag


# ---------------------------------------------------------------------------------------------------------------
# Ausführen
# ---------------------------------------------------------------------------------------------------------------

def ausfuehren(api, aktionen, orders, uhr, tag, scharf, jetzt=None):
    """Sendet die Aktionen an Alpaca (nur wenn scharf). Gibt je Aktion das Ergebnis zurück."""
    stempel = (jetzt or dt.datetime.now(dt.timezone.utc)).strftime("%H%M%S")
    ergebnisse = []
    for a in aktionen:
        sym, r, stueck = a["ticker"], a["richtung"], a["stueck"]
        weg = "sell" if r > 0 else "buy"  # Seite zum Schließen
        cid = f"{PRAEFIX}{tag:%Y%m%d}-{sym}-{a['art']}-{stempel}"
        ergebnis = {**a, "status": "Probe" if not scharf else "gesendet", "order": None}
        if not scharf:
            ergebnisse.append(ergebnis)
            continue
        try:
            if a["art"] in ("schliessen", "schliessen_zum_schluss", "schutz"):
                for o in orders.get(sym, []):
                    if a["art"] != "schutz" or o.get("order_class") == "oco":
                        api.storniere(o["id"])
            if a["art"] == "kaufen":
                ergebnis["order"] = api.order({
                    "symbol": sym, "qty": menge(stueck), "side": "buy" if r > 0 else "sell", "type": "limit",
                    "limit_price": preis(a["limit"]), "time_in_force": "opg", "client_order_id": cid})
            elif a["art"] == "schutz":
                ergebnis["order"] = api.order({
                    "symbol": sym, "qty": menge(stueck), "side": weg, "type": "limit", "time_in_force": "gtc",
                    "order_class": "oco", "take_profit": {"limit_price": preis(a["ziel"])},
                    "stop_loss": {"stop_price": preis(a["stop"])}, "client_order_id": cid})
            elif a["art"] == "schliessen_zum_schluss":
                try:
                    ergebnis["order"] = api.order({"symbol": sym, "qty": menge(stueck), "side": weg, "type": "market",
                                                   "time_in_force": "cls", "client_order_id": cid})
                except BrokerFehler:
                    if not uhr["is_open"]:
                        raise
                    ergebnis["order"] = api.schliesse(sym)  # zu spät für die Schlussauktion: sofort verkaufen
                    ergebnis["status"] = "sofort verkauft (Schlussauktion nicht mehr möglich)"
            elif a["art"] == "schliessen":
                if uhr["is_open"]:
                    ergebnis["order"] = api.schliesse(sym)
                else:  # Marktorder für den Tag: wird zur Eröffnung ausgeführt
                    ergebnis["order"] = api.order({"symbol": sym, "qty": menge(stueck), "side": weg, "type": "market",
                                                   "time_in_force": "day", "client_order_id": cid})
        except BrokerFehler as fehler:
            ergebnis["status"] = f"Fehler: {fehler}"
        ergebnisse.append(ergebnis)
    return ergebnisse


# ---------------------------------------------------------------------------------------------------------------
# Bericht
# ---------------------------------------------------------------------------------------------------------------

ART_TEXT = {"kaufen": "Kauf zur Eröffnung (Limit)", "schutz": "Stop und Ziel setzen (OCO)",
            "schliessen_zum_schluss": "Verkauf zum Schlusskurs", "schliessen": "Verkauf zum nächsten Kurs"}


def bericht(konto, positionen, depot, ergebnisse, hinweise, tag, scharf, max_order):
    z = ["# 🏦 Broker-Bot · Alpaca Paper-Konto", "",
         f"Stand: {dt.datetime.now(dt.timezone.utc):%d.%m.%Y %H:%M} UTC · Handelstag {tag:%d.%m.%Y} · "
         f"{'scharf (sendet Orders)' if scharf else 'Probelauf (sendet nichts, BROKER_AN ist nicht ja)'} · "
         "Spielgeld, keine Anlageberatung.", ""]
    if konto:
        z += [f"**Konto:** {float(konto['equity']):,.2f} $ · Bargeld {float(konto['cash']):,.2f} $ · "
              f"Obergrenze je Order {max_order:,.0f} $", ""]
    z += ["## Positionen: Broker gegen Übungsdepot", "",
          "| Aktie | Broker Stück | Einstand Broker | Übungsdepot Stück | Einstand Depot | Abweichung | Stop | Ziel |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    im_depot = {symbol(p["ticker"]): p for p in depot["positionen"]}
    for sym in sorted(set(positionen) | set(im_depot)):
        b, p = positionen.get(sym), im_depot.get(sym)
        abw = f"{(b['einstand'] / p['einstieg_usd'] - 1) * 100:+.2f} %" if b and p else "–"
        z.append(f"| {sym} | {b['stueck']:g} | {b['einstand']:.2f} $ | " if b else f"| {sym} | – | – | ")
        z[-1] += (f"{p['stueck']:g} | {p['einstieg_usd']:.2f} $ | {abw} | {p['stop']:.2f} $ | {p['ziel']:.2f} $ |"
                  if p else "– | – | – | – | – |")
    z += ["", "„Abweichung“: echter Einstand beim Broker gegen den simulierten Einstieg im Übungsdepot.", "",
          "## Aktionen", ""]
    if not ergebnisse:
        z.append("- keine")
    for e in ergebnisse:
        teile = [f"{e['ticker']}: {ART_TEXT[e['art']]}", f"{e['stueck']:g} Stück"]
        if e.get("limit"):
            teile.append(f"Limit {e['limit']:.2f} $")
        if e["art"] == "schutz":
            teile.append(f"Stop {e['stop']:.2f} $ · Ziel {e['ziel']:.2f} $")
        z.append(f"- {' · '.join(teile)} – {e['grund']} – **{e['status']}**")
    z += ["", "## Hinweise", ""] + ([f"- {h}" for h in hinweise] or ["- keine"])
    return "\n".join(z) + "\n"


def protokoll_merken(pfad, eintrag, maximal=500):
    alt = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else []
    pfad.write_text(json.dumps((alt + [eintrag])[-maximal:], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv=None, api=None):
    p = argparse.ArgumentParser(description="Broker-Bot: Übungsdepot des Swing-Bots bei Alpaca spiegeln (Paper)")
    p.add_argument("--depot", default=str(WURZEL / "papier" / "papier_depot.json"))
    p.add_argument("--uebersicht", default=str(WURZEL / "docs" / "daten.json"))
    p.add_argument("--bericht", default=str(WURZEL / "broker" / "BERICHT.md"))
    p.add_argument("--protokoll", default=str(WURZEL / "broker" / "protokoll.json"))
    a = p.parse_args(argv)

    scharf = os.environ.get("BROKER_AN", "").strip().lower() == "ja"
    max_order = float(os.environ.get("BROKER_MAX_ORDER") or MAX_ORDER_USD)
    if api is None:
        schluessel, geheim = os.environ.get("ALPACA_KEY_ID"), os.environ.get("ALPACA_SECRET_KEY")
        if not schluessel or not geheim:
            print("🏦 ALPACA_KEY_ID und ALPACA_SECRET_KEY fehlen – der Broker-Bot ist noch nicht eingerichtet "
                  "(Anleitung: README, Abschnitt Broker-Bot). Nichts zu tun.")
            return None
        api = Alpaca(schluessel, geheim)
    sw = swing_bot()
    depot = json.loads(pathlib.Path(a.depot).read_text(encoding="utf-8"))
    uebersicht_pfad = pathlib.Path(a.uebersicht)
    uebersicht = json.loads(uebersicht_pfad.read_text(encoding="utf-8")) if uebersicht_pfad.exists() else None

    try:
        konto = api.konto()
        uhr = api.uhr()
        positionen, orders = broker_lage(api)
    except BrokerFehler as fehler:
        raise SystemExit(f"🏦 Alpaca nicht erreichbar oder Schlüssel falsch ({fehler}) – nichts gesendet.") from fehler
    if konto.get("trading_blocked") or konto.get("account_blocked"):
        raise SystemExit("🏦 Das Alpaca-Konto ist für den Handel gesperrt – nichts gesendet.")
    aktionen, hinweise, tag = plane(sw, depot, uebersicht, positionen, orders, uhr, max_order)
    ergebnisse = ausfuehren(api, aktionen, orders, uhr, tag, scharf)
    text = bericht(konto, positionen, depot, ergebnisse, hinweise, tag, scharf, max_order)
    pathlib.Path(a.bericht).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.bericht).write_text(text, encoding="utf-8")
    protokoll_merken(pathlib.Path(a.protokoll), {
        "zeit": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "handelstag": f"{tag:%Y-%m-%d}",
        "scharf": scharf, "konto": round(float(konto["equity"]), 2), "aktionen": [
            {k: v for k, v in e.items() if k != "order"} | {"order_id": (e.get("order") or {}).get("id")}
            for e in ergebnisse], "hinweise": hinweise})
    print(text)
    return {"aktionen": ergebnisse, "hinweise": hinweise, "tag": tag}


if __name__ == "__main__":
    main()
