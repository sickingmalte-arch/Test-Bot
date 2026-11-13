"""Gemeinsame Bausteine für die Prüfung des „day-trader-skill“ (Wunsch des Nutzers vom 11.11.2026).

Quelle: github.com/Jakeschincariol/day-trader-skill (MIT-Lizenz, Stand 20.10.2026, „The Trader skill v2“). Elf Bausteine
für den Tageshandel. Was davon mit Tageskerzen 2010–2026 ehrlich prüfbar ist, liegt als Idee in forschung/ideen/skill_*.py:

  Scanner (trader-scanner)       fünf Tages-Setups als neue Kauf-Strategien (Regeln wörtlich aus scan.py, find_setups)
  Risiko (trader-risk)           höchstens 3 Käufe am Tag, Chance-Risiko mindestens 1,0
  Zeitmaschine (trader-timemachine)  Signal nur, wenn das Nachspielen mit den eigenen letzten 60 Kerzen zum Ziel neigt,
                                 bzw. wenn dieselbe Regel bei dieser Aktie bisher Gewinn brachte („die Geschichte“)
  Tageshandel (scanner orb, entry, exit)  Ausbruch aus der Eröffnungsspanne mit Stunden- und 5-Minuten-Kerzen

Kein Blick in die Zukunft: Jede Regel nutzt für Tag i nur Kurse bis zum Schluss von Tag i. Der fremde Code wird nicht
ausgeführt – die Regeln sind hier neu geschrieben (Python, numpy)."""
import inspect

import numpy as np
import pandas as pd

QUELLE = "github.com/Jakeschincariol/day-trader-skill (MIT, Stand 20.10.2026), Wunsch des Nutzers vom 11.11.2026"


# ------------------------------------------------------------------ Scanner: die fünf Tages-Setups (nur Schlusskurse)
def rsi_wilder(c, n=14):
    """RSI nach Wilder (wie scan.py: erster Mittelwert über n Tage, danach geglättet)."""
    c = np.asarray(c, dtype=float)
    out = np.full(len(c), np.nan)
    if len(c) < n + 1:
        return out
    d = np.diff(c)
    g, v = np.clip(d, 0, None), np.clip(-d, 0, None)
    ag, av = g[:n].mean(), v[:n].mean()
    out[n] = 100.0 if av == 0 else 100 - 100 / (1 + ag / av)
    for k in range(n, len(d)):
        ag = (ag * (n - 1) + g[k]) / n
        av = (av * (n - 1) + v[k]) / n
        out[k + 1] = 100.0 if av == 0 else 100 - 100 / (1 + ag / av)
    return out


def setups(c):
    """Die fünf Setups aus scan.py (find_setups) für jeden Tag i, nur mit Schlusskursen bis Tag i."""
    s = pd.Series(np.asarray(c, dtype=float))
    hoch20 = s.shift(1).rolling(20).max()                  # höchster Schluss der 20 Tage davor
    ma20, ma20_vor = s.rolling(20).mean(), s.shift(1).rolling(20).mean()
    lauf = s.shift(5) / s.shift(15) - 1                    # c[-6] / c[-16] - 1
    spanne5 = (s.rolling(5).max() - s.rolling(5).min()) / s
    r = pd.Series(rsi_wilder(s.to_numpy()))
    return {
        "ausbruch_20": (s > hoch20).to_numpy(),
        "bullenflagge": ((lauf > 0.10) & (spanne5 < 0.05)).to_numpy(),
        "ma20_zurueck": ((s.shift(1) < ma20_vor) & (s > ma20)).to_numpy(),
        "ueberverkauft": (r < 30).to_numpy(),
        "abpraller": ((r.shift(1) < 30) & (s > s.shift(1))).to_numpy(),
    }


def liquide(d):
    """Wie der Scanner: Kurs mindestens 5 $ und mindestens 1 Mio. Stück Umsatz am Tag."""
    c, v = np.asarray(d["C"], dtype=float), np.asarray(d["V"], dtype=float)
    return (c >= 5) & (np.nan_to_num(v) >= 1_000_000)


def grundlage(d, markt, einst, sw):
    """An welchen Tagen der Bot überhaupt kaufen darf: ATR bekannt, liquide, Marktfilter wie bei allen Long-Strategien."""
    atr = np.asarray(d["ATR"], dtype=float)
    ok = np.isfinite(atr) & (atr > 0) & liquide(d)
    if markt is not None and getattr(einst, "marktfilter", True):
        ok &= sw.markt_vortag(markt, d["idx"]) != 0
    return ok


def abstaende(sw, art, c, atr):
    """Stop und Ziel wie bei den Bot-Strategien derselben Art (Trend ±3 ATR, Gegenbewegung −2,5/+2 ATR)."""
    if art == "trend":
        return c - sw.STOP_TREND_ATR * atr, c + sw.ZIEL_TREND_ATR * atr
    return c - sw.STOP_GEGEN_ATR * atr, c + sw.ZIEL_GEGEN_ATR * atr


def neue_strategie(sw, key, name, art, regel, signal):
    """Hängt eine Strategie an den Bot an. signal(ticker, d, ok) -> (feuert, stop, ziel)."""
    sw.STRATEGIEN[key] = {"name": name, "richtung": 1, "art": art, "regel": regel}
    sw.VORRANG[key] = len(sw.VORRANG)
    original = sw.bereite_vor

    def neu(ticker, df, fx, zahlen_df, einst, markt=None):
        d = original(ticker, df, fx, zahlen_df, einst, markt)
        werte = signal(ticker, d, grundlage(d, markt, einst, sw))
        d["signale_roh"][key] = werte
        d["signale"][key] = werte
        return d
    sw.bereite_vor = neu


def setup_strategie(sw, key, setup, name, art, regel, zufall_seed=None):
    """Ein Scanner-Setup als Strategie – oder (zufall_seed) gleich viele Käufe je Aktie an zufälligen erlaubten Tagen
    mit denselben Stop- und Zielabständen (Gegenprobe)."""
    def signal(t, d, ok):
        c, atr = np.asarray(d["C"], dtype=float), np.asarray(d["ATR"], dtype=float)
        feuert = setups(c)[setup] & ok
        if zufall_seed is not None:
            frei = np.flatnonzero(ok & ~feuert)
            n = int(feuert.sum())
            feuert = np.zeros(len(c), bool)
            if n and len(frei):
                tage = np.random.default_rng([zufall_seed, sum(map(ord, t))]).choice(frei, min(n, len(frei)),
                                                                                     replace=False)
                feuert[tage] = True
        stop, ziel = abstaende(sw, art, c, atr)
        return feuert, np.where(feuert, stop, np.nan), np.where(feuert, ziel, np.nan)
    neue_strategie(sw, key, name, art, regel, signal)


# ------------------------------------------------------------------ Filter auf alle Signale (Risiko, Zeitmaschine)
def filtern(sw, weg_fn, zufall_seed=None):
    """Ersetzt bereite_vor: weg_fn(ticker, d, key, feuert, stop, ziel) -> bool-Array der Signale, die wegfallen.
    Mit zufall_seed fallen je Aktie genauso viele Signale weg, aber zufällig unter allen Signalen dieser Aktie
    (über alle Strategien) – die Gegenprobe."""
    original = sw.bereite_vor

    def neu(ticker, *a, **k):
        d = original(ticker, *a, **k)
        sig = {key: (np.asarray(f, dtype=bool).copy(), np.asarray(s, dtype=float), np.asarray(z, dtype=float))
               for key, (f, s, z) in d["signale"].items()}
        weg = {key: weg_fn(ticker, d, key, f, s, z) & f for key, (f, s, z) in sig.items()}
        if zufall_seed is not None:
            n = sum(int(w.sum()) for w in weg.values())
            orte = [(key, i) for key, (f, _, _) in sig.items() for i in np.flatnonzero(f)]
            weg = {key: np.zeros(len(f), bool) for key, (f, _, _) in sig.items()}
            if n and orte:
                rng = np.random.default_rng([zufall_seed, sum(map(ord, ticker))])
                for j in rng.choice(len(orte), min(n, len(orte)), replace=False):
                    key, i = orte[j]
                    weg[key][i] = True
        for key, (f, s, z) in sig.items():
            d["signale"][key] = (f & ~weg[key], s, z)
        return d
    sw.bereite_vor = neu


def crv(c, stop, ziel):
    with np.errstate(divide="ignore", invalid="ignore"):
        return (ziel - c) / (c - stop)


# Zeitmaschine: 1.000 Wiederholungen der nächsten 20 Handelstage aus den eigenen letzten 60 Tageskerzen
ZM_KERZEN, ZM_WIEDERHOLUNGEN, ZM_TAGE, ZM_NEIGUNG = 60, 1000, 20, 0.05
_ZM_CACHE = {}


def zeitmaschine(t, d, i, stop, ziel):
    """Wie timemachine.py, nur mit Tageskerzen: Jede Kerze der letzten 60 Tage wird zu vier Verhältnissen zum Schluss
    davor (Eröffnung, Hoch, Tief, Schluss). Eine Wiederholung zieht für jeden der nächsten 20 Tage zufällig eine dieser
    Kerzen und setzt sie an den Kurs an; Stop vor Ziel, wenn beides am selben Tag. Ergebnis: (Ziel zuerst, Stop zuerst)."""
    schluessel = (t, int(i), round(float(stop), 6), round(float(ziel), 6))
    if schluessel in _ZM_CACHE:
        return _ZM_CACHE[schluessel]
    O, H, L, C = (np.asarray(d[k], dtype=float) for k in ("O_ersatz", "H", "L", "C"))
    von = max(1, i - ZM_KERZEN + 1)
    vor = C[von - 1:i]
    o, h, lo, c = O[von:i + 1] / vor, H[von:i + 1] / vor, L[von:i + 1] / vor, C[von:i + 1] / vor
    gut = np.isfinite(o) & np.isfinite(h) & np.isfinite(lo) & np.isfinite(c) & (c > 0)
    o, h, lo, c = o[gut], h[gut], lo[gut], c[gut]
    if len(c) < 20:
        _ZM_CACHE[schluessel] = (np.nan, np.nan)
        return _ZM_CACHE[schluessel]
    rng = np.random.default_rng([19, sum(map(ord, t)), int(i)])   # Seed 19 wie im Skill, je Aktie und Tag fest
    z = rng.integers(0, len(c), (ZM_WIEDERHOLUNGEN, ZM_TAGE))
    schluss = C[i] * np.cumprod(c[z], axis=1)
    vorher = np.concatenate([np.full((ZM_WIEDERHOLUNGEN, 1), C[i]), schluss[:, :-1]], axis=1)
    tief = np.minimum(vorher * lo[z], vorher * o[z])
    hoch = np.maximum(vorher * h[z], vorher * o[z])
    s_tag = np.where((tief <= stop).any(axis=1), (tief <= stop).argmax(axis=1), ZM_TAGE + 1)
    z_tag = np.where((hoch >= ziel).any(axis=1), (hoch >= ziel).argmax(axis=1), ZM_TAGE + 1)
    p_ziel = float(np.mean(z_tag < s_tag))
    p_stop = float(np.mean((s_tag <= z_tag) & (s_tag <= ZM_TAGE)))
    _ZM_CACHE[schluessel] = (p_ziel, p_stop)
    return _ZM_CACHE[schluessel]


def neigt_zum_ziel(p_ziel, p_stop, r):
    """Urteil wie im Skill: Unter den Wiederholungen, die eine Seite erreichen, muss das Ziel um mindestens 5 Punkte
    öfter zuerst kommen als zum Ausgleich nötig (1 / (1 + R)) – „leans toward the target“ oder stärker."""
    entschieden = p_ziel + p_stop
    if not np.isfinite(entschieden) or entschieden <= 0 or not np.isfinite(r) or r <= 0:
        return False
    return p_ziel / entschieden - 1 / (1 + r) >= ZM_NEIGUNG


# „Die Geschichte“: dieselbe Regel bei derselben Aktie, nur Trades, die am Signaltag schon zu Ende waren
HIST_MINDEST, SPREAD_RUND = 5, 0.002


def gedachte_trades(d, feuert, stop, ziel, tage=20):
    """Für jedes Signal j: Kauf zur nächsten Eröffnung, raus am Stop (zuerst), am Ziel oder nach 20 Handelstagen
    zum Schluss. Gibt (Signaltag, Ausstiegstag, R nach Spread) zurück; Signale ohne möglichen Kauf fehlen."""
    O, H, L, C = (np.asarray(d[k], dtype=float) for k in ("O_ersatz", "H", "L", "C"))
    n = len(C)
    j = np.flatnonzero(feuert[:n - 1])
    if not len(j):
        return np.array([], int), np.array([], int), np.array([])
    ein = O[j + 1]
    st, zi = stop[j], ziel[j]
    ok = np.isfinite(ein) & (ein > st) & np.isfinite(st) & np.isfinite(zi)
    j, ein, st, zi = j[ok], ein[ok], st[ok], zi[ok]
    k = np.minimum(j[:, None] + 1 + np.arange(tage)[None, :], n - 1)
    gueltig = (j[:, None] + 1 + np.arange(tage)[None, :]) <= n - 1
    o, h, lo, c = O[k], H[k], L[k], C[k]
    s_hit = gueltig & ((lo <= st[:, None]) | (o <= st[:, None]))
    z_hit = gueltig & (h >= zi[:, None]) & ~s_hit
    s_tag = np.where(s_hit.any(axis=1), s_hit.argmax(axis=1), tage + 1)
    z_tag = np.where(z_hit.any(axis=1), z_hit.argmax(axis=1), tage + 1)
    letzter = gueltig.sum(axis=1) - 1
    fertig = (np.minimum(s_tag, z_tag) <= tage) | (letzter >= tage - 1)
    zeile = np.arange(len(j))
    aus_tag = np.where(s_tag <= z_tag, s_tag, z_tag)
    aus_tag = np.where(aus_tag > tage, letzter, aus_tag)
    aus = np.where(s_tag <= z_tag, np.minimum(o[zeile, np.minimum(s_tag, tage - 1)], st), zi)
    aus = np.where((s_tag > tage) & (z_tag > tage), c[zeile, np.maximum(letzter, 0)], aus)
    r = ((aus * (1 - SPREAD_RUND / 2)) - ein * (1 + SPREAD_RUND / 2)) / (ein - st)
    return j[fertig], k[zeile, np.maximum(aus_tag, 0)][fertig], r[fertig]


def geschichte_schlecht(t, d, key, feuert, stop, ziel):
    """True an Signaltagen, an denen dieselbe Regel bei dieser Aktie schon mindestens 5 fertige Trades hatte und
    deren Schnitt (nach Spread) nicht über 0 R lag."""
    sig, aus, r = gedachte_trades(d, feuert, stop, ziel)
    weg = np.zeros(len(feuert), bool)
    if not len(sig):
        return weg
    reihen = np.argsort(aus)
    aus_s, r_s = aus[reihen], r[reihen]
    summe = np.concatenate([[0.0], np.cumsum(r_s)])
    for i in np.flatnonzero(feuert):
        m = int(np.searchsorted(aus_s, i, side="left"))   # nur Trades, die vor Tag i zu Ende waren
        if m >= HIST_MINDEST and summe[m] / m <= 0:
            weg[i] = True
    return weg


# ------------------------------------------------------------------ Risiko: höchstens N Käufe am Tag
def max_kaeufe_am_tag(sw, n, zufall_seed=None):
    """Höchstens n neue Positionen je Handelstag (Rest verfällt wie bei vollem Depot). Gegenprobe: die Aufträge des
    Tages in zufälliger statt in der Bot-Reihenfolge, dann ebenfalls höchstens n."""
    src = inspect.getsource(sw.simuliere_depot)
    anker = [
        ("        warten = []\n        for auftrag in auftraege:\n",
         "        warten = []\n        kaeufe_heute = 0\n        for auftrag in REIHENFOLGE(auftraege, tag):\n"),
        ("            if stueck <= 0 or einsatz < MIN_EINSATZ:\n                continue\n",
         "            if stueck <= 0 or einsatz < MIN_EINSATZ or kaeufe_heute >= MAX_KAEUFE_AM_TAG:\n"
         "                continue\n            kaeufe_heute += 1\n"),
    ]
    for alt, neu in anker:
        if src.count(alt) != 1:
            raise RuntimeError(f"simuliere_depot: Stelle nicht eindeutig gefunden: {alt!r}")
        src = src.replace(alt, neu)
    sw.MAX_KAEUFE_AM_TAG = n
    if zufall_seed is None:
        sw.REIHENFOLGE = lambda auftraege, tag: list(auftraege)
    else:
        def zufaellig(auftraege, tag):
            rng = np.random.default_rng([zufall_seed, int(pd.Timestamp(tag).value // 86_400_000_000_000)])
            return [auftraege[k] for k in rng.permutation(len(auftraege))]
        sw.REIHENFOLGE = zufaellig
    exec(compile(src, "simuliere_depot_skill", "exec"), sw.__dict__)
