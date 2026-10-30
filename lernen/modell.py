"""Lernmodell des Swing-Bots: das Modell.

Ein Gradient-Boosting-Modell (scikit-learn, viele kleine Entscheidungsbäume hintereinander) lernt aus allen
Merkmalen, welche Kauf-Signale später im Plus geendet haben. Es gibt jedem neuen Signal eine Punktzahl
(geschätzte Gewinn-Wahrscheinlichkeit), gekauft werden nur die besten.

Ehrlich bleiben: Das Modell wird jeden Monat neu trainiert, und zwar NUR mit Trades, deren Ergebnis vor
Monatsbeginn schon feststand (Walk-forward). Die Signale des neuen Monats hat es nie gesehen.
"""
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score

import merkmale as M

SEKTOREN = ["Communication Services", "Consumer Discretionary", "Consumer Staples", "Energy", "Financials",
            "Health Care", "Industrials", "Information Technology", "Materials", "Real Estate", "Utilities",
            "Unbekannt"]
EINSTELLUNGEN = dict(max_iter=150, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=300,
                     l2_regularization=1.0, early_stopping=False, random_state=0)
MIN_TRAINING = 3000  # erst ab so vielen abgeschlossenen gedachten Trades lernen


def eingabe(kand, merkmale=None):
    x = kand.copy()
    x["sektor_code"] = x["sektor"].map({s: i for i, s in enumerate(SEKTOREN)}).fillna(len(SEKTOREN) - 1)
    return x[merkmale or M.MERKMALE].astype(float)


def neues_modell(merkmale=None):
    namen = merkmale or M.MERKMALE
    kategorie = [n == "sektor_code" for n in namen]
    return HistGradientBoostingClassifier(categorical_features=kategorie if any(kategorie) else None,
                                          **EINSTELLUNGEN)


def trainiere(train, merkmale=None):
    """Lernt aus abgeschlossenen gedachten Trades. Merkmale ohne einen einzigen Wert (z. B. Bilanzdaten vor 2009)
    bleiben weg; welche benutzt wurden, steht in modell.lern_merkmale."""
    x = eingabe(train, merkmale)
    genutzt = [c for c in x.columns if x[c].notna().sum() >= 50]
    modell = neues_modell(genutzt)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modell.fit(x[genutzt], (train["R"] > 0).astype(int))
    modell.lern_merkmale = genutzt
    return modell


def punktzahl(modell, kand):
    return modell.predict_proba(eingabe(kand, modell.lern_merkmale))[:, 1]


def bekannt_vor(kand, tag):
    """Abgeschlossene gedachte Trades, deren Ergebnis vor 'tag' feststand."""
    return kand[(kand["status"] == "fertig") & (kand["ausstieg_tag"] < tag)]


def walk_forward(kand, start, ende, merkmale=None, protokoll=None):
    """Punktzahl für jeden Kandidaten ab 'start': je Monat ein neues Modell aus der Zeit davor."""
    kand = kand.sort_values("tag")
    punkte = pd.Series(np.nan, index=kand.index)
    for m0 in pd.date_range(pd.Timestamp(start), pd.Timestamp(ende), freq="MS"):
        m1 = m0 + pd.offsets.MonthBegin(1)
        test = kand[(kand["tag"] >= m0) & (kand["tag"] < m1)]
        train = bekannt_vor(kand, m0)
        if test.empty or len(train) < MIN_TRAINING:
            continue
        modell = trainiere(train, merkmale)
        punkte.loc[test.index] = punktzahl(modell, test)
        if protokoll is not None:
            protokoll.append({"monat": m0.strftime("%Y-%m"), "training": len(train), "neu": len(test)})
    return punkte


def schwelle(punkte_vorher, anteil):
    """Kauf-Schwelle: Nur Signale, die zu den besten 'anteil' der Punktzahlen der letzten 12 Monate gehören
    (aus Punktzahlen, die damals schon vergeben waren)."""
    p = punkte_vorher.dropna()
    return float(np.quantile(p, 1 - anteil)) if len(p) >= 200 else 0.0


def monats_schwellen(kand, anteil):
    """Je Monat die Kauf-Schwelle aus den Punktzahlen aller Signale der 12 Monate davor."""
    k = kand[kand["punkte"].notna()][["tag", "punkte"]].sort_values("tag")
    aus = {}
    if k.empty:
        return pd.Series(aus, dtype=float)
    for m0 in pd.date_range(k["tag"].min().to_period("M").to_timestamp(), k["tag"].max(), freq="MS"):
        vorher = k[(k["tag"] < m0) & (k["tag"] >= m0 - pd.DateOffset(months=12))]["punkte"]
        aus[m0.to_period("M")] = schwelle(vorher, anteil) if len(vorher) >= 200 else np.inf
    return pd.Series(aus, dtype=float)


def guete(kand, punkte):
    """Wie gut trennt die Punktzahl gute von schlechten Signalen? (nur Signale mit Ergebnis)"""
    k = kand.assign(punkte=punkte)
    k = k[(k["status"] == "fertig") & k["punkte"].notna()]
    if len(k) < 100:
        return {}
    k["fuenftel"] = pd.qcut(k["punkte"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    tab = k.groupby("fuenftel", observed=True)["R"].agg(["mean", "size", lambda r: (r > 0).mean()])
    tab.columns = ["R", "n", "treffer"]
    jahre = {}
    for j, g in k.groupby(k["tag"].dt.year):
        if g["R"].gt(0).nunique() == 2:
            jahre[int(j)] = float(roc_auc_score(g["R"] > 0, g["punkte"]))
    return {"auc": float(roc_auc_score(k["R"] > 0, k["punkte"])), "fuenftel": tab.reset_index().to_dict("records"),
            "auc_je_jahr": jahre, "n": int(len(k))}


def was_gelernt(kand, bis, merkmale=None, letzte_monate=12):
    """Welche Merkmale sind dem Modell am wichtigsten? Modell aus allem bis 12 Monate vor 'bis', geprüft auf den
    12 Monaten danach (Permutation: wie viel schlechter wird die Vorhersage, wenn man ein Merkmal durcheinander
    würfelt). Dazu die Richtung: Steigt die Punktzahl mit dem Merkmal oder fällt sie?"""
    namen = merkmale or M.MERKMALE
    grenze = pd.Timestamp(bis) - pd.DateOffset(months=letzte_monate)
    train = bekannt_vor(kand, grenze)
    test = kand[(kand["status"] == "fertig") & (kand["tag"] >= grenze) & (kand["ausstieg_tag"] < pd.Timestamp(bis))]
    if len(train) < MIN_TRAINING or len(test) < 200:
        return []
    modell = trainiere(train, namen)
    namen = modell.lern_merkmale
    x = eingabe(test, namen)
    y = (test["R"] > 0).astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        imp = permutation_importance(modell, x, y, scoring="roc_auc", n_repeats=5, random_state=0, n_jobs=1)
    p = modell.predict_proba(x)[:, 1]
    aus = []
    for n, w, s in zip(namen, imp.importances_mean, imp.importances_std):
        richtung = (pd.Series(x[n].to_numpy()).corr(pd.Series(p), method="spearman")
                    if x[n].notna().sum() > 50 else np.nan)
        aus.append({"merkmal": n, "name": M.NAMEN.get(n, n), "wichtigkeit": float(w), "streuung": float(s),
                    "richtung": float(richtung) if pd.notna(richtung) else None})
    return sorted(aus, key=lambda z: -z["wichtigkeit"])
