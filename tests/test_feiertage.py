"""US-Feiertage für die Übersichtsseite: an handelsfreien Tagen der New Yorker Börse zeigt sie „Börse geschlossen“."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hilfe  # noqa: E402

sw = hilfe.bot()


def test_feiertage_der_naechsten_wochen():
    tage = sw.us_feiertage_bald(40, heute="2026-11-26")
    assert tage["2026-11-26"] == "Thanksgiving"
    assert tage["2026-12-25"] == "Weihnachten"
    assert "2026-11-27" not in tage  # Tag nach Thanksgiving: Börse offen (nur kürzer)
    assert all(d <= "2027-01-05" for d in tage)


def test_feiertag_am_wochenende_wird_verschoben():
    tage = sw.us_feiertage_bald(10, heute="2027-07-01")  # 4. Juli 2027 ist ein Sonntag
    assert tage == {"2027-07-05": "Unabhängigkeitstag"}
    assert sw.us_feiertage_bald(5, heute="2027-01-14") == {"2027-01-18": "Martin-Luther-King-Tag"}  # 3. Montag
    assert sw.us_feiertage_bald(5, heute="2027-02-01") == {}
