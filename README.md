# Automatisches Trading-System

## Streamlit-Dashboard starten

In PowerShell im Projektordner ausführen:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

Das Dashboard lädt abgeschlossene öffentliche Spot-Kerzen von der Binance-API (Standard: BTCUSDT, 5 Minuten) und aktualisiert die Ansicht automatisch. Das SMA-System simuliert Trades lokal mit Paper-Kapital. Es werden keine echten Orders gesendet und es werden keine API-Schlüssel benötigt.

Die ersten bis zu 200 abgeschlossenen Kerzen werden beim Start verarbeitet. Das ist eine Paper-Simulation mit den jüngsten Kursdaten, kein echter Live-Orderverlauf. Gebühren, Slippage und Ausführung sind vereinfachte Modellannahmen.

Für echte Orders muss zuerst eine konkrete Börse, ein Handelspaar und ein sicherer API-Zugang festgelegt werden. Die Orderübermittlung ist in diesem Projekt absichtlich nicht implementiert.

## Offline-Konsolendemonstration

```powershell
py -3 Automatisches_trading_system.py --candles 180
```

## Swing-Scanner für die Aktien-Watchlist

### In Google Colab (ohne Installation)

Neue Zelle anlegen, einfügen und mit Umschalt + Enter ausführen:

```
!pip install -q -U yfinance
!curl -fsSL -o swing_scanner.py https://raw.githubusercontent.com/sickingmalte-arch/Test-Bot/main/swing_scanner.py
%run swing_scanner.py --konto 10000 --risiko 1
```

Mit `%run` erscheinen farbige Tabellen und ein Diagramm; mit `!python swing_scanner.py` die Textversion.

Das Skript kommt aus dem Hauptzweig `main` – das klappt erst, wenn der Pull Request übernommen ist (**Merge**, siehe GitHub Actions Schritt 1); bis dahin steht statt `main` noch `claude/new-session-hbq1tg` in der Adresse (sonst Fehler 404). In älteren Notebooks (auch `Trading_bot.ipynb`) danach die ganze `wget`-Zeile durch die `curl`-Zeile oben ersetzen, nicht nur den Zweig – `wget -q` verschweigt Fehler und hinterlässt eine leere Datei, dann zeigt `%run` gar nichts. Den Zweig `claude/new-session-hbq1tg` erst löschen, wenn alle Notebooks umgestellt sind.

Mit Papier-Depot (Vorwärtstest mit virtuellem Geld, Stand in deinem Google Drive) – Colab fragt beim ersten Mal nach der Erlaubnis für Drive. Am besten jeden Börsentag einmal morgens vor 15:30 Uhr starten (dann hat Yahoo den US-Handelstag vom Vortag sicher fertig – abends oder nachts fehlt er oft noch). `--papier-neu` nur einmal zum Neuanfangen anhängen und danach wieder weglassen:

```
!pip install -q -U yfinance
!curl -fsSL -o swing_scanner.py https://raw.githubusercontent.com/sickingmalte-arch/Test-Bot/main/swing_scanner.py
%run swing_scanner.py --konto 10000 --risiko 1 --papier
```

### Lokal (PowerShell)

```powershell
python -m pip install -U yfinance pandas numpy
python swing_scanner.py
```

### Automatisch jeden Morgen (GitHub Actions – ohne PC, ohne Colab)

Der Ablauf `.github/workflows/swing-bot.yml` startet den Bot am Morgen nach jedem US-Börsentag kostenlos in der Cloud bei GitHub (Di–Sa): um 6:47 Uhr UTC, also 8:47 Uhr deutscher Sommerzeit bzw. 7:47 Uhr Winterzeit. GitHub startet geplante Läufe oft später, manchmal Stunden. Deshalb gibt es zwei Ersatz-Termine um 9:17 und 11:17 Uhr UTC (11:17 und 13:17 Uhr Sommerzeit, 10:17 und 12:17 Uhr Winterzeit), beide vor dem US-Börsenstart. Weil GitHub geplante Läufe manchmal ganz auslässt, stößt zusätzlich die Live-Kette (siehe Übersichtsseite, „Live während der Börsenzeit“) den Morgen-Lauf um 6:47 Uhr UTC an. Ein Ersatz-Termin oder angestoßener Lauf rechnet nur, wenn es heute noch keinen vollständigen Bericht gibt – sonst ist er nach wenigen Sekunden fertig. Fehlten beim ersten Lauf noch Kurse von Yahoo, holt er sie nach. Von Hand starten musst du also nichts mehr. Nicht schon nachts, weil Yahoo die Kurse eines Tages oft erst Stunden nach Börsenschluss liefert. Fehlt der letzte Handelstag trotzdem noch, steht oben im Bericht eine Warnung, und es kommt keine Nachricht aufs Handy. Du musst keine Seite offen lassen und nichts neu laden. Einrichten und Einstellungen gehen nur im Browser (am Handy notfalls „Desktop-Website“), nicht in der GitHub-App; lesen kannst du den Bericht auch in der App.

1. **Einmalig:** Die Änderungen müssen im Hauptzweig `main` sein (Pull Request → **Merge**). Zeitgesteuerte Abläufe laufen bei GitHub nur aus `main`. Willst du ein anderes Startkapital als 10.000 €, trag es vorher ein (Schritt 5).
2. **Sofort testen:** **Actions → Swing-Bot → Run workflow**. Ein Lauf dauert einige Minuten. Danach gibt es die Ordner `bericht` und `papier`.
3. **Ergebnis ansehen:** Im Repository die Datei `bericht/README.md` öffnen (auch in der GitHub-App: Code → `bericht` → `README.md`). Dort stehen Signale, Handelsplan, Lernstand, Papier-Depot und Rückblick; ein Klick auf einen Ticker öffnet den Chart bei TradingView. Jeder Lauf zeigt den Bericht außerdem unter **Actions → Swing-Bot → Lauf anklicken** (Zusammenfassung). Steht dort ❌, steht der Grund gleich dabei. Das Gehirn für Obsidian (Tagebuch, Lehren, deine Regeln) liegt im Ordner `gehirn` – siehe unten.
4. **Papier-Depot:** liegt in `papier/papier_depot.json` und wird nach jedem Lauf gespeichert. Der Bot holt verpasste Tage nach, falls GitHub einen Lauf auslässt oder Yahoo einmal nicht antwortet. Dein bisheriges Depot aus Google Drive weiterführen: erst einmal Schritt 2, dann `MyDrive/swing_scanner/papier_depot.json` aus Drive herunterladen, im Repository den Ordner `papier` öffnen → **Add file → Upload files** → Datei hineinziehen (sie muss genau `papier_depot.json` heißen und ersetzt die vom ersten Lauf) → **Commit changes**. Nicht hochladen, während gerade ein Lauf arbeitet (sonst wird dieser Lauf nicht gespeichert; der nächste rechnet weiter). Drive-Depot und GitHub-Depot sind danach zwei getrennte Dateien – wenn du beide fortschreibst, laufen sie auseinander.
5. **Einstellungen ohne Code:** **Settings → Secrets and variables → Actions → Tab „Variables“ → New repository variable**:

| Name | Beispiel | Bedeutung |
| --- | --- | --- |
| `KONTO` | `10000` | Kontogröße / Startkapital in € (Standard 10000; auch `10.000 €` oder `10.000,00` geht). Fürs Papier-Depot zählt der Betrag nur beim Anlegen – also am besten **vor** dem ersten Lauf eintragen; später geändert: `papier/papier_depot.json` löschen, dann fängt es mit dem neuen Betrag an (der Bericht weist darauf hin). |
| `RISIKO` | `1` | Risiko je Trade in % (Standard 1; auch `1,5 %` geht) |
| `TICKER` | `AAPL, NFLX, SOFI` | eigene Watchlist (leer = Liste im Skript) |
| `OPTIONEN` | `--bruchstuecke --gebuehr 0` | nur diese Schalter, mit Leerzeichen getrennt: `--mit-short`, `--ohne-lernen`, `--ohne-marktfilter`, `--ohne-news`, `--ohne-zahlen`, `--bruchstuecke`, `--nur-schluss`, `--gebuehr 0`, `--rueckblick 6` |

Alles andere stellt der Ablauf selbst ein: `--papier`, `--papier-neu`, `--bericht`, `--gehirn`, `--nachricht`, `--claude-depot`, `--claude-entscheidungen`, `--uebersicht`, `--csv`, `--ticker`, `--konto` und `--risiko` bitte **nicht** in `OPTIONEN` eintragen (für Ticker, Konto und Risiko gibt es die eigenen Variablen). Verschriebene Angaben meldet der Bericht oben mit ⚠️. Zum Neuanfang des Papier-Depots einfach `papier/papier_depot.json` im Repository löschen (die Historie bei GitHub behält den alten Stand).

**Nachricht aufs Handy bei Kauf-Signalen.** Hat der Bot ein Signal, schreibt er nach dem Lauf einen Kommentar ins Thema **„📲 Swing-Bot: Signale“** (Tab **Issues**; das Thema legt er bei der ersten Nachricht selbst an): Aktie, Strategie, Stückzahl, Limit, Stop, Ziel und bis wann verkaufen – dazu ein Link zum Bericht. GitHub schickt dir dazu eine E-Mail, und mit der **GitHub-App** kommt eine Push-Nachricht. Außerdem kommen dort zwei weitere Nachrichten:

- **Wochenrückblick:** am Samstagmorgen mit dem Morgen-Lauf, denn erst dann ist der Freitag im Übungsdepot gebucht. Bei einem Feiertag am Freitag kommt er schon nach dem Donnerstag. Darin steht in drei Zeilen, wie sich das Übungsdepot in der Woche verändert hat (in € und %, dazu seit dem Start), wie viele Käufe und Verkäufe es gab und wie viele davon im Plus waren, und wie der Nasdaq-100 (QQQ, in €) im selben Zeitraum lief.
- **Fehlermeldung, wenn der Morgen-Lauf abbricht:** mit dem Grund und einem Link zum Lauf, höchstens eine am Tag. Das ist nötig, weil die Live-Kette den Morgen-Lauf anstößt: Dann kommt GitHubs eigene Fehler-Mail meist nicht mehr bei dir an.

Einmalig einrichten:

1. App **GitHub** (Android oder iPhone) installieren und mit deinem Konto anmelden.
2. In der App (sie ist auf Englisch): **Profile → Zahnrad (Settings) → Notifications** → Push-Nachrichten einschalten und dort **Direct mentions** (direkte Erwähnungen) anhaken. In den Handy-Einstellungen Benachrichtigungen für die GitHub-App erlauben.
3. E-Mails: im Browser **github.com/settings/notifications** → bei **Participating, @mentions and custom** „Email“ angehakt lassen (Standard). Keine E-Mails gewünscht: Haken weg, die Push-Nachricht kommt trotzdem.
4. Fertig – der Bot erwähnt dich (@Benutzername) in jedem Kommentar, damit die Nachricht sicher ankommt. Läuft der Bot mehrmals mit denselben Kursen (z. B. von Hand gestartet und später noch der geplante Lauf), schickt er dieselbe Nachricht nicht ein zweites Mal.

Keine Nachrichten mehr: im Thema rechts **Unsubscribe**. Signale kommen fast jeden Börsentag, weil 24 Aktien beobachtet werden; die Nachricht nennt die besten nach denselben Grenzen wie der Handelsplan im Bericht. Steht der Tab „Issues“ nicht im Repository, ist er ausgeschaltet: **Settings → General → Features → Issues** anhaken. Klappt das Senden einmal nicht, bleibt der Lauf trotzdem grün und Bericht, Papier-Depot und Gehirn werden normal gespeichert.

**Claude-Depot (Versuch): Kann Claude besser auswählen als der Bot?** Ein zweites Übungsdepot in `papier/claude_depot.json`, das fair gegen das Übungsdepot antritt:

- **Start:** beim ersten Lauf eine genaue Kopie des Übungsdepots (gleicher Depotwert, gleiche Positionen und Aufträge).
- **Gleiche Regeln:** derselbe Einstieg zur Eröffnung bis zum Limit, dieselben Stops, Ziele, Grenzen und Kosten.
- **Einziger Unterschied:** Claude liest jeden Börsentag den Bericht und die Nachrichten und darf einzelne Kauf-Signale **auslassen** – mit Begründung. Neue Signale, eigene Stops oder vorzeitige Verkäufe gibt es nicht. Ohne Entscheidung nimmt das Claude-Depot alle Signale wie der Bot. Jeder Signaltag braucht seine eigene Entscheidung.
- **Fälschungssicher:** Claude schreibt seine Entscheidung als Kommentar ins Thema **„🧠 Claude-Depot: Entscheidungen“** (Tab Issues, Label `claude-depot`). Es zählen nur Kommentare des Repository-Besitzers, die vor der Eröffnung des nächsten US-Handelstags geschrieben und danach nicht mehr geändert wurden – mit dem Zeitstempel von GitHub. Was später kommt, steht im Bericht als „nicht gezählt“. Fremde Kommentare im öffentlichen Repository zählen nie.
- **Auswertung:** Im Bericht stehen unter „🧠 CLAUDE-DEPOT (Versuch)“ der Vergleich seit Versuchsbeginn (Claude-Depot, Übungsdepot, Nasdaq-100) und Claudes letzte Entscheidung. Der Unterschied zum Übungsdepot ist allein die Wirkung von Claudes Entscheidungen. Ehrlich: Erst nach vielen Monaten und Hunderten Trades lässt sich ein kleiner Vorteil von Glück unterscheiden.
- **Beenden:** im Ablauf `.github/workflows/swing-bot.yml` die Optionen `--claude-depot` und `--claude-entscheidungen` entfernen. Neu anfangen: `papier/claude_depot.json` löschen (dann wieder eine Kopie des Übungsdepots).

**Übersichtsseite: alles auf einen Blick, auch am Handy.** Der Bot schreibt bei jedem Lauf die Daten für eine dunkle Übersichtsseite (`docs/index.html`, Daten in `docs/daten.json`). Darauf stehen:

- **Fazit:** Was hat das Übungsdepot am letzten Börsentag verdient oder verloren, was hat der Bot gekauft und verkauft, und welche Aktie hat wie viel beigetragen? Umschaltbar auf Woche, Monat und alles, mit Pfeilen zum Zurückblättern, Vergleich mit dem Nasdaq-100 und dem Claude-Depot, Balken für jeden Tag und einem Kalender mit dem Ergebnis jedes Börsentags (antippen zeigt den Tag oder die Woche).
- **Live während der Börsenzeit:** Mo–Fr von 12 bis 22 Uhr läuft der Ablauf `.github/workflows/live.yml`. Bis zum US-Börsenstart (15:30 Uhr, in den Wochen der Zeitumstellung 14:30 Uhr) steht oben nur „Live läuft“ mit der Uhrzeit des Börsenstarts; danach holt er etwa alle 15 Minuten die aktuellen Kurse von Yahoo (etwa 15 Minuten verzögert) und **rechnet Käufe und Verkäufe jedes Mal neu** – nach denselben Regeln wie am Morgen: Kauf zur Eröffnung bis zum Limit, Verkauf an Stop oder Ziel; Zeitstopp und Verkauf vor Quartalszahlen gelten zum Schlusskurs. Oben steht dann „LIVE“ mit Uhrzeit und ein Bereich **Live**: was Übungs- und Claude-Depot gerade wert sind, was heute gekauft und verkauft wurde (vorläufig), die Positionen mit Kurs und Ergebnis und ob die Kauf-Signale gerade unter oder über ihrem Limit liegen. Endgültig bucht der Bot beim Morgen-Lauf mit den Schlusskursen, fast immer mit demselben Ergebnis (anders nur, wenn eine Aktie am selben Tag Stop und Ziel berührt – dann zählt wie im Test der Stop); neue Signale gibt es weiter nur am Morgen, weil die Strategien mit Schlusskursen getestet sind. Lässt du die Seite offen, aktualisiert sie sich alle 5 Minuten. Der Ablauf speichert nichts im Repository (keine Commits, nichts Neues für Obsidian). Weil GitHub geplante Läufe oft auslässt (am 26.10.2026 kam von 48 nur einer), **startet jeder Live-Lauf am Ende selbst den nächsten** – eine Kette, die Tag und Nacht weiterläuft und zwischen den Terminen wartet. Du startest sie einmal mit **Actions → Live-Kurse → Run workflow** (das holt auch sofort die aktuellen Kurse); reißt sie ab, startet sie ein geplanter Ersatz-Lauf neu. Anhalten: **Actions → Live-Kurse → „…“ → Disable workflow**.
- **Gehirn-Kern:** was heute reinkam (Aktien, Strategien, Tagebuch, Termine) und was rauskam (Signale, Warten, Gewinne sichern)
- **Kennzahlen:** Übungsdepot, Vergleich mit dem Nasdaq-100, Trefferquote, Rendite und größter Rückgang im Rückblick
- **Signale als Karten:** Limit, Stop und Ziel mit Balken. Auf jeder Karte steht, was das Übungsdepot damit macht (wird gekauft, schon im Depot, Depot voll). Quartalszahlen in weniger als 7 Tagen sind rot markiert, auch bei den offenen Positionen. Dazu die **Ziel-Chance**, erkannte **Kerzenmuster**, bei Ausbrüchen und Doppelböden das **Musterziel** und wie viele gute und schlechte Schlagzeilen es gab (alles nur zur Info, siehe Gehirn unten).
- **Depotkurve:** gegen den Nasdaq-100, mit Fadenkreuz und Rückgang vom Hoch
- **Strategien:** mit Mini-Kurven und den letzten 10 Trades
- offene Positionen zwischen Stop und Ziel und das Claude-Depot
- **Nachrichten auf Deutsch:** Der Bot übersetzt die Schlagzeilen maschinell mit dem kostenlosen Dienst MyMemory, jede hat einen Link „Artikel lesen“ und „Original“ (zeigt die englische Überschrift). Börsen-Ausdrücke, die der Dienst oft falsch versteht, schreibt der Bot vorher in einfaches Englisch um (z. B. „loads up on“ → „kauft viel“ statt „belastet“, „stock“ → „Aktie“ statt „Lager“, „guidance“ → „Prognose“ statt „Anleitung“). Die Artikel selbst sind meist englisch; Chrome übersetzt sie über das Menü ⋮ → **Übersetzen**. Klappt die Übersetzung einmal nicht (Tageslimit des Dienstes), steht die Schlagzeile englisch da. Die Nachrichten-Regel prüft immer das englische Original.
- **Chat-Fenster:** Tipps und Fragen an Claude (siehe unten)
- **Erklärungen:** Ein kleines (i) erklärt Fachwörter wie CRV, R pro Trade oder Pkt, wenn du draufdrückst. Am Handy sind lange Abschnitte (Strategien, Positionen, Claude-Depot, Nachrichten) anfangs zugeklappt; ein Tipp auf die Überschrift klappt sie auf.

1. **Einmalig einschalten:** **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. **Einmal starten:** **Actions → Übersichtsseite → Run workflow**. Danach wird die Seite nach jedem Lauf des Bots von selbst neu veröffentlicht.
3. **Öffnen:** `https://<Benutzername>.github.io/<Repository>/`, hier also https://sickingmalte-arch.github.io/Test-Bot/. Am Handy im Browser **„Zum Home-Bildschirm“** wählen, dann öffnet sie sich wie eine App.

Die Seite ist öffentlich wie das Repository.

**Chat-Fenster: Tipps an Claude.** Oben rechts auf der Übersichtsseite („Tipps an Claude“, am Handy die Sprechblase) schreibst du Claude Tipps, Fragen oder Ideen für den Bot. Dafür musst du keine Sitzung bei Claude öffnen. Direkt-Link fürs Lesezeichen: https://sickingmalte-arch.github.io/Test-Bot/#chat

- **So geht's:** Text eintippen → **Senden** → GitHub öffnet sich mit deinem Text als neues Thema (Label `tipp`) → dort **Create** tippen. Dafür musst du bei GitHub angemeldet sein. Fehlt der Text, weil sich die GitHub-App öffnet: Er ist schon in der Zwischenablage, einfach einfügen.
- **Antworten:** Claude schaut Di–Sa vormittags (zusammen mit der Entscheidung fürs Claude-Depot) und jeden Abend ab ca. 18:45 Uhr rein. Es antwortet im selben Thema. Die Antwort steht dann im Fenster, und der Knopf zeigt neue Antworten mit einer Zahl. Antworten kannst du auch direkt im Thema bei GitHub.
- **Was Claude damit macht:**
  - Fragen beantwortet es.
  - Tipps zur Auswahl beachtet es im Claude-Depot, solange das Thema offen ist. Zurückziehen: Thema schließen oder „vergiss das“ schreiben.
  - Aktien sperren oder Strategien ausschalten bereitet es für `gehirn/Meine Regeln.md` vor. Live geht das erst, wenn du dazu „Ja“ schreibst. Oder du hakst es selbst ab (siehe „Regeln abhaken“).
  - Änderungen an den Regeln des Bots testet es erst ehrlich und übernimmt sie nur nach deinem „Ja“.
- **Sicherheit:** Es zählen nur Nachrichten des Repository-Besitzers. Fremde Themen und Kommentare zeigt die Seite nicht, und Claude befolgt sie nicht. Alles ist öffentlich lesbar – nichts Persönliches schreiben. Die Seite liest ohne Anmeldung (GitHub erlaubt 60 Abfragen pro Stunde und Netz), Abschicken geht nur bei GitHub selbst.

Gut zu wissen: GitHub startet zeitgesteuerte Läufe oft einige Minuten später und lässt bei hoher Last selten einen aus. Yahoo begrenzt manchmal Abfragen von Cloud-Servern – dann steht ❌ im Bericht, das Papier-Depot bleibt unverändert und der nächste Lauf holt alles nach. Mit Krypto in `TICKER` rechnet das Papier-Depot einen Tag später weiter (der Krypto-Tag endet erst um 2:00 Uhr deutscher Sommerzeit). Schaltet GitHub den Ablauf doch einmal ab (Hinweis im Tab Actions), dort „Enable workflow“ klicken. Neue Versionen des Skripts nutzt der automatische Lauf erst, wenn sie in `main` übernommen sind.

### Gehirn in Obsidian: Tagebuch, Lehren und deine Regeln

Der automatische Lauf schreibt jeden Morgen Notizen für [Obsidian](https://obsidian.md) in den Ordner `gehirn/` (lokal mit der Option `--gehirn`):

- **`Start.md`** – Übersicht: heutige Signale, Übungsdepot, was der Bot gelernt hat, deine Regeln.
- **`Tage/2026-10-21.md`** – Tagesnotiz: Marktlage, Entscheidungen, Übungsdepot, Änderungen beim Lernen.
- **`Wochen/2026-W43.md`** – Wochenrückblick: Depotwert am Wochenanfang und jetzt, abgeschlossene und neue Trades der Woche, Trefferquote im Übungsdepot (gesamt und je Aktie), Änderungen beim Lernen und Links zu den Tagesnotizen. Während der Woche schreibt der Bot sie bei jedem Lauf neu, danach bleibt sie stehen. Unten ist unter „Meine Gedanken zur Woche“ Platz für dich – am besten erst, wenn die Woche vorbei ist (dann ändert der Bot die Notiz nicht mehr).
- **`Trades/…`** – je abgeschlossenem Trade im Übungsdepot eine Notiz: warum gekauft, was passiert ist (z. B. Stop durch Kurslücke, Gewinn wieder abgegeben) und **was der Bot daraus lernt**. Darunter ist Platz für deine Gedanken; diese Notiz ändert der Bot danach nie mehr.
- **`Strategien/…`** und **`Aktien/…`** – je eine Seite mit Bilanz, Lernstand (aktiv, pausiert, aus) und allen Trades, alles verlinkt.
- **`Lehren.md`** – was der Bot aus allen Trades zieht: Lernregel, Ausstiegsgründe, Muster und ehrliche Hinweise zum Zufall. Dazu die **Selbstkontrolle der Ziel-Chance** (siehe unten).
- **`Notizen/…`** – Wissen und eigene Gedanken; der Bot ändert sie nie und verlinkt sie auf der Startseite. Schon drin: **`Wissen – Optionen.md`** (das ganze Optionsskript in einfachen Worten: Call und Put, Absicherung, Put-Call-Parität, Binomialmodell, Black-Scholes, Hebel, Volatilität, Greeks, Delta-Hedging) und **`Gelernt aus dem Optionsskript.md`** (was davon im Bot getestet wurde).
- **`Meine Regeln.md`** – die Seite gehört dir, der Bot ändert sie nie: **Haken setzen und hochladen = Regel gilt** (wie das Hochladen geht, steht unten). Dort sperrst du Aktien oder schaltest Strategien aus. Der Bot liest das bei jedem Lauf, meldet im Bericht, was er nicht verstanden hat, und zeigt auf der Startseite unter „Deine Regeln“, welche Regeln bei ihm angekommen sind.

**Was deine Regeln bewirken.** Ab dem nächsten Lauf nimmt der Bot gesperrte Aktien und ausgeschaltete Strategien nicht mehr für neue Signale und das Übungsdepot; offene Aufträge dafür streicht er, offene Positionen laufen normal zu Ende. Im Rückblick (Simulation der letzten 12 Monate) gelten die Regeln auch rückwirkend – wer im Nachhinein die Verlierer sperrt, lässt den Rückblick besser aussehen, als er war. Ehrlich ist nur das Übungsdepot.

**Kerzen- und Chartmuster, Nachrichten-Stimmung (aus dem Poster und zwei Lehrbüchern).** Bei jedem Kauf-Signal nennt der Bot die Kerzenmuster des Tages (z. B. Hammer, Bullish Engulfing, Shooting Star), bei Ausbrüchen und Doppelböden das Musterziel und die Zahl guter und schlechter Schlagzeilen der letzten Tage – im Handelsplan, auf der Übersichtsseite und in der Trade-Notiz. **Er kauft und verkauft nicht danach:** Als Bestätigung, Warnung, Vorrang oder variables Ziel hat das im Test über 16 Jahre nicht geholfen (siehe „Geprüft und nicht übernommen“). Auf `Lehren.md` prüft er laufend, ob Signale mit Muster besser laufen; die Nachrichten-Stimmung speichert er ab jetzt in `papier/nachrichten_log.json` und vergleicht sie dort mit den Ergebnissen, sobald genug Trades da sind. Das Wissen steht in den Notizen „Wissen – Kerzen- und Chartmuster“ und „Wissen – Traden lernen (Lehrbücher)“.

**Ziel-Chance nach Black-Scholes (aus dem Optionsskript).** Bei jedem Kauf-Signal rechnet der Bot aus der Schwankung der letzten 20 Tage aus, wie wahrscheinlich der Kurs das Ziel innerhalb von 20 Handelstagen mindestens einmal berührt. Daneben steht, wie oft das bei gedachten Trades mit ähnlicher Formel-Chance bisher wirklich passiert ist. Zu sehen ist beides im Handelsplan (Bericht und Handy-Nachricht), auf der Übersichtsseite und in neuen Trade-Notizen; auf `Lehren.md` prüft der Bot laufend, ob die Formel stimmt. **Er kauft und verkauft nicht danach** – im Test über 16 Jahre half das nicht (siehe „Geprüft und nicht übernommen“). Der Stop kann vor dem Ziel kommen, und die Formel weiß nicht, in welche Richtung eine Aktie geht.

**So lernt der Bot.** Automatisch ändert er nur, welche Strategien er handelt (Lernregel: schlecht laufende Strategien pausieren), und er hält sich an deine Regeln. Muster wie „auf Aktie X läuft es schlecht“ zeigt er dir nur – bei wenigen Trades ist das oft Zufall. Ob du daraus eine Regel machst, entscheidest du.

**Wo du selbst schreibst.** Am besten in den **Trade-Notizen unter „Meine Gedanken“**, in **abgeschlossenen Wochenrückblicken** (Woche vorbei) oder in eigenen Notizen im Ordner **`gehirn/Notizen`** – die ändert der Bot nicht mehr. Danach **Git: Commit-and-sync**, sonst bleibt der Text nur auf diesem Gerät (dafür braucht es den Zugangs-Token, siehe „Regeln abhaken“). Auf den übrigen Seiten (Start, Tage, Strategien, Aktien, Lehren) besser nichts schreiben: Die schreibt der Bot fast bei jedem Lauf neu, und ein nicht hochgeladener Text dort hält Obsidian davon ab, neue Notizen zu holen. (Was dort zwischen `BOT-ANFANG` und `BOT-ENDE` steht, ersetzt der Bot; Eigenschaften, Tags und hochgeladener Text darüber oder darunter bleiben erhalten.)

> ⚠️ **Alles im Repository ist öffentlich.** Was du mit Commit-and-sync hochlädst – auch eingefügte Bilder –, kann jeder im Internet lesen. Keine persönlichen Daten, Kontonummern oder echten Depotdaten notieren.

**Auf dem Handy einrichten (Android oder iPhone, einmalig ca. 10 Minuten).** Zum Lesen braucht es kein Passwort, weil das Repository öffentlich ist.

1. Die App **Obsidian** installieren (Version 1.13 oder neuer). **Vault erstellen** → Name `Test-Bot`. Bei der Frage nach Synchronisieren **„Vorerst überspringen“** – am iPhone **nicht** „iCloud verwenden“.
2. **Einstellungen** (Zahnrad) → **Externe Erweiterungen** → **Eingeschränkter Modus** ausschalten → bei **Community-Erweiterungen** auf **Durchsuchen** → **Git** (von Vinzent) → **Installieren** → **Aktivieren**.
3. **Befehlspalette** öffnen (vom oberen Bildschirmrand nach unten wischen) → `clone` tippen → **Git: Clone an existing remote repo** → Adresse `https://github.com/sickingmalte-arch/Test-Bot.git` → **Vault Root** wählen → die Frage nach einem `.obsidian`-Ordner mit **NO** beantworten → die Tiefe leer lassen → warten, bis „Please restart Obsidian“ erscheint → die App ganz schließen und neu öffnen.
4. **Einstellungen → Git → Identity**: bei **Repository author name** deinen Vornamen und bei **Repository author email** eine E-Mail-Adresse eintragen (am besten die `…@users.noreply.github.com`-Adresse aus GitHub → Settings → Emails). **Wichtig:** Ohne Name und E-Mail holt die Handy-Version keine neuen Notizen (Fehler „Git author name and email are not set“).
5. **Einstellungen → Git → Sync**: **Pull on startup** einschalten (holt beim Öffnen die neuen Notizen). Unter **Git → Automatic** bei **Auto pull interval (minutes)** z. B. `30` eintragen.
6. Links im Dateibaum `gehirn` → `Start` öffnen und als Lesezeichen setzen (oben rechts **⋯** → **Lesezeichen**).

Hängt oder stürzt das Klonen ab (die Handy-Version des Plugins gilt als experimentell): Die App **GitSync** (Android und iPhone) klont das Repository, danach den Ordner in Obsidian als Vault öffnen.

**Regeln abhaken.** Am einfachsten im Browser: auf GitHub `gehirn/Meine Regeln.md` öffnen → Stift-Symbol → aus `- [ ] HIMS` wird `- [x] HIMS` → **Commit changes**. Eine Aktie, die noch nicht in der Liste steht, schreibst du als neue Zeile unter „Aktien sperren“, mit dem Kürzel wie im Bot (`- [x] TSLA`, nicht „Tesla“). Direkt in Obsidian geht es so (einmalig ein Zugangs-Token):

1. Auf GitHub [diesen Link](https://github.com/settings/personal-access-tokens/new?name=Obsidian+Test-Bot&description=Obsidian+Git+Plugin&contents=write&expires_in=90) öffnen → **Only select repositories** → `Test-Bot` → **Generate token** → den Token (`github_pat_…`) kopieren. Er erscheint nur einmal und gehört **nie** in eine Notiz – alles im Repository ist öffentlich.
2. Am Handy **Einstellungen → Git → Identity**: bei **Username on your Git server** `sickingmalte-arch` eintragen, bei **Git server password or access token** ein Geheimnis hinzufügen (Name nur mit kleinen Buchstaben, Zahlen und Bindestrichen, z. B. `github-token`) und den Token einfügen. Name und E-Mail hast du schon in Schritt 4 eingetragen.
3. Nach dem Abhaken in `Meine Regeln`: Befehlspalette → **Git: Commit-and-sync**. Nicht kurz vor oder während des morgendlichen Laufs (um 8:47 bzw. 7:47 Uhr, oft etwas später) – sonst wird dieser Lauf nicht gespeichert, der nächste rechnet weiter. Nach dem nächsten Lauf steht auf der Startseite unter „Deine Regeln“, ob die Regel angekommen ist.
4. Der Token gilt 90 Tage (GitHub schickt vorher eine E-Mail). Danach den Link oben erneut öffnen, einen neuen Token erzeugen und unter **Git → Identity** das Geheimnis durch den neuen Token ersetzen. Solange das nicht passiert, kommen Haken aus Obsidian nicht beim Bot an.

**Am PC (Windows).** [Git für Windows](https://git-scm.com/download/win) installieren (Standardwerte lassen). In PowerShell (Name und E-Mail wie in Schritt 4 oben):

```powershell
git config --global user.name "Dein Vorname"
git config --global user.email "deine-adresse@users.noreply.github.com"
cd $HOME; mkdir Obsidian; cd Obsidian
git clone https://github.com/sickingmalte-arch/Test-Bot.git
```

Den Ordner nicht in OneDrive anlegen. Obsidian installieren → **Ordner als Vault öffnen** → `Obsidian\Test-Bot` wählen → Plugin **Git** wie oben installieren → **Git → Sync → Pull on startup** einschalten. Beim ersten „Commit-and-sync“ öffnet sich ein Anmeldefenster von GitHub (kein Token nötig).

Tipps: Der Vault ist das ganze Repository. Unter **Einstellungen → Dateien & Links → Ignorierte Dateien** kannst du `bericht/`, `papier/` und `tradingview/` aus Suche und Graph heraushalten (im Dateibaum bleiben sie sichtbar). Obsidian-Einstellungen (`.obsidian/`, also auch dein Token) werden nicht hochgeladen. Am Handy holt Obsidian neue Notizen nur, solange die App offen ist.

### TradingView: Signale direkt im Chart

Die Datei [`tradingview/swing_bot_signale.pine`](tradingview/swing_bot_signale.pine) ist ein Indikator für TradingView (auch im kostenlosen Tarif). Er zeigt im Tageschart jeder Aktie, was der Bot kaufen würde und was nicht – zum Vergleich mit deinen eigenen Linien und Indikatoren:

- **▲ Name = KAUFEN, ▼ Name = SHORT** (▼ nur mit eingeschalteten Short-Signalen; grünes bzw. rotes Schild mit der Strategie): Auftrag für den nächsten Handelstag. Maus darüber (am Handy antippen) zeigt Limit, Stop, Ziel und CRV. Ein blasses ▲/▼ ohne Schild ist ein Signal, während im Chart noch ein Trade läuft – der Bot gibt dann keinen neuen Auftrag (ein Alarm meldet es trotzdem). Vor dem eingestellten Zeitraum (Zahnrad, Standard 12 Monate) rechnet der Indikator keine Trades: Dort stehen Signale nur als kräftige ▲/▼ ohne Schild, ohne Zonen und ohne graue Signale.
- **Jeder Trade wie mit dem Positions-Werkzeug von TradingView:** grüne Zielzone, rote Stop-Zone und Einstiegslinie vom Einstieg bis zum Ausstieg, eine gepunktete Linie zum Ausstiegskurs und dort ein Schild mit dem Ergebnis, z. B. „+0,9 R · Ziel“ (grün; ein Treffer bringt jetzt knapp 1 R, dafür trifft der Bot öfter), „−1,0 R · Stop“ (rot) oder „+0,3 R · Zeitstopp“ (grau, nach 20 Handelstagen). 1 R ist der geplante Verlust bis zum Stop, bei 1 % Risiko und 10.000 € also rund 100 €. Gerechnet wird wie im Papier-Depot des Bots (Einstieg am nächsten Handelstag zur Eröffnung nur bis zum Limit, Stop vor Ziel, Kurslücken zur Eröffnung, nach Spread und Gebühren); das Ergebnis eines Trades zählt wie im Strategie-Tagebuch höchstens ±3 R. Beim laufenden Trade stehen rechts Preisschilder für Ziel, Einstieg (Tag x/20) und Stop.
- **Grau = der Bot handelt nicht**, mit Grund beim Antippen: „⏸ Marktfilter“, „⏸ Long + Short zugleich“ oder „⏸ … aus“ (Strategie ausgeschaltet) am ersten Tag, an den Folgetagen nur graue Punkte; „✕“ = Auftrag verfallen, weil die Eröffnung über dem Limit (Short: darunter) oder schon hinter dem Stop lag.
- **Auftrag für den nächsten Handelstag:** gestrichelte Linien rechts neben der letzten Kerze (Limit, Stop, Ziel).
- **Infotafel** (Ort und Schriftgröße im Zahnrad wählbar): heutige Entscheidung wie in der Tabelle des Bots (KAUFEN, SHORT, WARTEN mit Grund, GEWINNE SICHERN oder BEOBACHTEN), Auftrag für morgen, offener Trade, Marktlage und die Bilanz der letzten 12 Monate (Trades, Trefferquote, Ergebnis in R und ≈ €, nicht genommene Signale). Erklärungen erscheinen beim Antippen der Zeilen.
- Roter Hintergrund = Abwärtsmarkt (Nasdaq-100 unter seiner 200-Tage-Linie). Auf Wunsch zeichnet er auch EMA 20, SMA 50 und SMA 200, die der Bot benutzt.

Einrichten geht nur am PC oder Tablet im Browser (die TradingView-Handy-App hat keinen Pine-Editor); danach ist der Indikator auch in der App unter **Indikatoren → Meine Skripte** verfügbar.

1. Die Datei auf GitHub öffnen und mit dem Kopieren-Knopf („Copy raw file“) kopieren.
2. Bei TradingView einen Chart öffnen, den **Pine-Editor** öffnen (seit 2025 rechts in der Seitenleiste, in älteren Ansichten unten), den Inhalt komplett ersetzen, **Zum Chart hinzufügen** und **Speichern** klicken.
3. Tageschart (**1D**) wählen und unten rechts am Chart **ADJ** einschalten (Kurse für Dividenden bereinigen; in der App in den Chart-Einstellungen). Der Bot rechnet wie Yahoo mit dividendenbereinigten Kursen – ohne ADJ weichen die Signale bei Dividendenwerten wie XOM, JPM oder COST oft ab; die Infotafel zeigt dann rot „ADJ einschalten!“. Signale gelten erst zum Tagesschluss (US-Börsenschluss 22:00 Uhr deutscher Zeit) – wie beim Bot. Solange die Tageskerze läuft, steht in der Infotafel „vorläufig“: Schild und Auftrag können sich bis zum Schluss noch ändern oder verschwinden (Alarme melden sich erst zum Schluss).
4. Zahnrad am Indikator: Short-Signale, Marktfilter, Trades, graue Signale, Infotafel, Zeitraum (Standard 12 Monate, 0 = ganzer Chart), Konto, Risiko und jede Strategie einzeln an/aus. Strategien, die im Bericht des Bots „aus“ oder „pausiert“ sind, hier abschalten. Wird es am Handy zu voll: graue Signale ausschalten oder die Infotafel nach unten bzw. auf „sehr klein“ stellen.
5. Benachrichtigung aufs Handy: Rechtsklick im Chart → **Alarm hinzufügen** → Bedingung „Swing-Bot“ → „Swing-Bot: KAUFEN-Signal“ oder „SHORT-Signal“ → „Einmal pro Balkenschluss“. Ein Alarm gilt nur für eine Aktie; im kostenlosen Tarif gibt es nur wenige Alarme und sie laufen nach einiger Zeit ab – für die ganze Watchlist ist der Bericht des Bots besser. Nach Änderungen im Zahnrad und nach jedem Update des Skripts (Schritt 1–2) die Swing-Bot-Alarme löschen und neu anlegen – ein Alarm rechnet mit der Skript-Version, die beim Anlegen galt; ein alter „SHORT-Signal“-Alarm meldet sich sonst weiter, obwohl Shorts jetzt aus sind. Nach dem Update im Zahnrad prüfen, dass „Short-Signale zeigen“ aus ist (oder unten im Zahnrad „Standard → Einstellungen zurücksetzen“).

Der Indikator kennt nur den einen Chart: Lernregel über die ganze Watchlist, Quartalszahlen-Regel, Schlagzeilen und die Grenzen für Positionen und Risiko gibt es nur im Bot. Die Trades im Chart sind deshalb die eines Depots, das nur diese eine Aktie handelt; wie der Rückblick des Bots beginnt es leer am Anfang des Zeitraums. Die €-Beträge rechnen 1 R = Konto × Risiko – der Bot kauft aber höchstens für 25 % des Kontos und nur ganze Aktien, bei teuren oder ruhigen Aktien riskiert er weniger. Kurse stehen in der Währung des Charts (meist $), nicht in €. In den ersten Monaten eines Charts können Signale durch andere Startwerte der Indikatoren abweichen – maßgeblich ist der Bericht des Bots. Die Bilanz ist ein Vergleich, keine Vorhersage. TradingView handelt damit nicht automatisch; der Bot handelt nur virtuell.

### Was das Skript zeigt

1. **Scanner (heute):** je Ticker 🟢 KAUFEN, 🔴 SHORT (nur mit `--mit-short`), ⏸ WARTEN (mit Grund), ⚠️ GEWINNE SICHERN, BEOBACHTEN oder ❌ FEHLER – mit Strategie, Kurs, Limit (höchster Kaufkurs), Stop, Ziel, Chance-Risiko-Verhältnis (CRV), Stückzahl, Einsatz, Risiko in €, nächstem Quartalszahlen-Termin und erkannten Ereignissen aus den Schlagzeilen. Für die besten Signale steht darunter ein Handelsplan in einem Satz (wann, wie viel, bis zu welchem Kurs, Stop, Ziel, spätestens raus am …) – nach denselben Grenzen wie im Depot: höchstens 5 Positionen, zusammen höchstens 5 % Risiko und nicht mehr Geld als auf dem Konto. Alle Beträge in Euro.
2. **Strategie-Tagebuch („Lernen“):** Jede eingeschaltete Strategie (ohne `--mit-short` die 8 Kauf-Strategien) handelt im Hintergrund gedanklich mit. Läuft eine Strategie über ihre letzten bis zu 60 Trades im Schnitt deutlich schlecht (unter −0,1 R ab 20 Trades), wird sie pausiert, bis sie wieder im Plus ist. Hat sie über ihre ganze Geschichte (ab 50 Trades) nach Kosten Geld verloren, handelt der Bot sie gar nicht. Die Tabelle zeigt ehrlich, wie groß der Zufall dabei sein kann.
3. **Papier-Depot (Vorwärtstest, mit `--papier`):** Der Bot handelt ab dem ersten Lauf vorwärts mit virtuellem Geld nach genau denselben Regeln und speichert den Stand – in Colab in Google Drive (`MyDrive/swing_scanner/papier_depot.json`), sonst in `papier_depot.json`. Jeder Lauf rechnet die neuen Kurstage seit dem letzten Lauf, sobald sie für alle Werte der Liste fertig sind: Aufträge vom Vorabend zur Eröffnung (nur bis zum Limit), Stop, Ziel, Quartalszahlen, Zeitstopp, neue Signale zum Schluss. Verpasste Tage holt er nach, jede Entscheidung nutzt nur Kurse, die es da schon gab. Aktiensplits und Dividenden (Yahoo rechnet alte Kurse um) werden erkannt und verrechnet. Das ist der ehrliche Test: Anders als der Rückblick kennt das Papier-Depot die Zukunft nicht.
4. **Virtuelles Depot (Rückblick):** Der Bot handelt die letzten Monate mit dem Startkapital nach seinen Signalen – einmal mit und einmal ohne Lernen – im Vergleich zu „alle Ticker kaufen und halten“. Es wird kein echtes Geld bewegt.

### Strategien und Regeln

- 8 Strategien für steigende Kurse: Ausbruch (20-Tage-Hoch mit Volumen), RSI-2-Rücksetzer, Gegenbewegung (überverkauft), MACD-Wende, Rücksetzer an der EMA 20, Squeeze-Ausbruch (Bollinger-Bänder erst sehr eng, dann Ausbruch), EMA-Kreuz (EMA 9 kreuzt EMA 21) und ATR-Ausbruch (Schluss mehr als 2 ATR über der EMA 20, Keltner-Kanal).
- Die 8 Gegenstücke für fallende Kurse (Short) sind ausgeschaltet: Im Test mit echten Kursen von 2010 bis 2026 hat jede von ihnen zusammengerechnet Geld verloren. Nur im langen Abwärtsjahr 2022 lagen die meisten knapp im Plus; bei kurzen Rücksetzern (z. B. 2011, 2016, 2020, 2023 und 2026) brachten sie deutliche Verluste – und vorher weiß niemand, welche Art Abwärtsphase kommt. Wer sie trotzdem will: `--mit-short`.
- Stop und Ziel: Trend-Strategien Stop 3 ATR und Ziel 3 ATR vom Schlusskurs, Gegenbewegungen (RSI-2, Gegenbewegung) Stop 2,5 ATR und Ziel 2 ATR. Das Ziel liegt absichtlich nicht weiter weg als der Stop: So trifft der Bot öfter (gut 55 % statt gut 45 %), gewinnt je Treffer aber weniger (siehe Test unten).
- Watchlist (`TICKER_LISTE` im Skript): SE, HIMS, NOW, INTU, CRWV, NBIS, MELI, IREN, NFLX, AAPL, ASTS, SOFI sowie NVDA, MSFT, AMZN, META, GOOGL, TSLA, AMD, PLTR, JPM, LLY, XOM, COST – keine Empfehlung, nur liquide Werte aus mehreren Branchen. Eigene Liste mit `--ticker`.
- Marktfilter: Der Bot kauft nur, wenn der Nasdaq-100 (QQQ) am Vortag über seiner 200-Tage-Linie schloss; darunter wartet er (mit `--mit-short` zählen dann nur Short-Signale) – die meisten Aktien laufen mit dem Gesamtmarkt. Der Rückblick zeigt zum Vergleich, wie es mit deinen Kursen ohne Marktfilter gelaufen wäre (`--ohne-marktfilter` schaltet ihn ab).
- Trendregel: Trendstrategien nur in Richtung der 50-Tage-Linie, Gegenbewegungen nur in Richtung der 200-Tage-Linie; widersprechen sich Signale, wartet der Bot.
- Quartalszahlen: kein Einstieg in den 3 Handelstagen davor, offene Positionen am Abend vorher schließen, kurz danach keine Gegenbewegungs-Trades.
- Einstieg am nächsten Handelstag nur bis zum Limit; Ausstieg an Stop, Ziel, vor Quartalszahlen oder spätestens nach 20 Handelstagen.
- Risiko: 1 % des Kontos je Trade, höchstens 5 Positionen (mit `--mit-short` davon höchstens 2 Short), davon höchstens 2 aus derselben Branche (z. B. Technologie – die Watchlist ist sehr technologielastig; Branchen stehen in `BRANCHEN` oben im Skript, fehlende Ticker zählen als eigene Branche), und 5 % Risiko gleichzeitig, höchstens 25 % des Kontos je Position. Kosten: 1 € Gebühr + 0,1 % Spread je Order.
- Nachrichten: Für jede Aktie mit Signal liest der Bot die Schlagzeilen der letzten 3 Handelstage. Spricht eine erkannte Meldung gegen den Kauf (z. B. Herabstufung durch Analysten, Zahlen oder Prognose schlechter als erwartet, Kapitalerhöhung, Ermittlungen einer Behörde, Insider-Verkauf, Chefwechsel) oder ist es ein Sonderfall (Übernahme, Handelsaussetzung), kauft er nicht: Im Bericht steht dann ⏸ WARTEN mit dem Grund, und auch das Papier-Depot kauft an diesem Tag nicht. Die Wortsuche versteht keinen Zusammenhang, also vor einem Kauf selbst lesen. Alte Schlagzeilen gibt es bei Yahoo nicht, deshalb lässt sich diese Regel nicht rückwirkend testen; im Rückblick gilt sie nur für den letzten Tag. Mit `--ohne-news` ist sie aus.

### Test mit echten Kursen (2010–2026)

Die Regeln wurden mit echten Tageskursen von 2010 bis 2026 geprüft – mit deiner Watchlist und zur Kontrolle mit 60 anderen US-Aktien. Stop- und Zielabstände wurden nur mit 2015–2021 entwickelt; die Jahre 2022–2026 kamen erst ganz am Ende dazu, damit sich der Bot nicht die Vergangenheit „merkt“. Spätere Änderungen (z. B. die Branchen-Grenze) mussten in allen drei Zeiträumen und bei beiden Aktiengruppen bestehen – dadurch ist 2022–2026 kein ganz unberührter Test mehr. Simuliert ist das Depot des Bots (1 % Risiko je Trade, höchstens 5 Positionen, Gebühren und Spread) – jeweils als Mittel aus 16 Durchläufen, denn schon die Reihenfolge der Aktien in der Liste verschiebt ein einzelnes Ergebnis um 1–3 Prozentpunkte. „Vorher“ ist der Bot vor den Verbesserungen (Ziel doppelt so weit wie der Stop, mit Shorts), „jetzt“ die heutige Version. Wichtig: Beide Gruppen sind heute bekannte, noch gehandelte Aktien – viele davon spätere Gewinner oder erst nach 2019 an die Börse gekommen (z. B. APP, COIN, SMCI, RKLB). Aktien, die in dieser Zeit abgestürzt oder verschwunden sind, fehlen. Kauf-Strategien und vor allem Kaufen und Halten sehen dadurch besser aus, als man es damals hätte wissen können. Aussagekräftig ist vor allem der Vergleich vorher → jetzt, nicht die Höhe der Renditen.

| Zeitraum | Aktien | Trefferquote vorher → jetzt | Rendite pro Jahr vorher → jetzt | größter Rückgang vorher → jetzt |
| --- | --- | --- | --- | --- |
| 2010–2014 | Watchlist | 45 % → 56 % | 4,7 % → 9,2 % | 33 % → 14 % |
| 2010–2014 | 60 andere | 46 % → 54 % | 9,1 % → 9,1 % | 18 % → 13 % |
| 2015–2021 | Watchlist | 47 % → 58 % | 10,8 % → 12,7 % | 19 % → 16 % |
| 2015–2021 | 60 andere | 43 % → 57 % | 3,1 % → 8,1 % | 23 % → 16 % |
| 2022–2026 | Watchlist | 48 % → 57 % | 12,2 % → 6,4 % | 22 % → 16 % |
| 2022–2026 | 60 andere | 41 % → 52 % | 5,7 % → 4,8 % | 21 % → 10 % |

Ehrlich zusammengefasst: Die Trefferquote steigt überall deutlich, die Rückgänge werden überall kleiner. Dafür bringt ein Treffer weniger (etwa 1 R statt bis zu 2 R). Ob am Ende mehr Geld herauskommt, hängt vom Zeitraum ab: 2010–2021 meist ja (mit den 60 anderen 2010–2014 gleich), 2022–2026 nein – da hätte die alte Version mehr verdient. Bei 2022–2026 lag die Trefferquote bei 16 von 22 Watchlist-Aktien über 50 % (vorher 7). Dass jede einzelne Aktie über 50 % liegt, lässt sich nicht garantieren: Mit meist 15–23 Trades je Aktie landen einige allein durch Zufall darunter. Alle Aktien zu kaufen und zu halten hätte in jedem Zeitraum mehr gebracht, allerdings mit größeren Rückgängen: 20–35 % statt höchstens 16 %, mit der Watchlist allein 2022 rund −30 %.

**Geprüft und nicht übernommen** (gleicher Test: 2010–2014, 2015–2021, 2022–2026, Watchlist und 60 andere Aktien; übernommen wird nur, was überall hilft oder zumindest nirgends erkennbar schadet):

- *Weniger Strategien* (z. B. nur RSI-2 und Gegenbewegung, oder ohne MACD und EMA-Kreuz): Über 16 Jahre liegen alle 8 Kauf-Strategien im Plus – auch MACD-Wende und EMA-Kreuz. Nur zwei Strategien zu behalten, kostete im Schnitt 5 Prozentpunkte Rendite pro Jahr. Die kurze Tabelle im Bericht (60 Trades) ist für so eine Entscheidung zu zufällig.
- *Ruhigere Lernregel* (erst ab 100 Trades, nur bei „klar im Minus“): im Schnitt 0,5–0,9 Prozentpunkte weniger Rendite. Ganz ohne Lernregel war es in 4 von 6 Fällen schlechter – die jetzige Regel bleibt.
- *Relative Stärke bei der Auswahl* (stärkste Aktien der letzten 3–6 Monate zuerst): leicht schlechter; 12 Monate im Schnitt besser, aber nicht überall.
- *Gewinner laufen lassen* (nachgezogener Stop statt Ziel bei Trend-Strategien): mehr Gewinn je Trade, aber die Trefferquote fällt auf etwa 50 % und die Rendite war nur in der Hälfte der Fälle besser.
- *Chance-Risiko lernen oder aus dem Chart lesen, nur klare Signale* (Bestätigung durch mehrere Strategien, Qualitätspunkte, Filter): halfen höchstens bis 2021 und 2022–2026 nicht.
- *Freies Geld im Nasdaq-100 (QQQ) parken* (immer oder nur über seiner 200-Tage-Linie, mit Gebühr und Spread auch für die QQQ-Orders): mehr Rendite in allen 6 Fällen (immer: im Schnitt +8 Prozentpunkte pro Jahr, nur über der Linie: +2), aber der größte Rückgang wurde überall größer – bei „immer“ fast doppelt so groß und etwa so groß wie bei QQQ allein (bis 31 %). QQQ einfach zu halten brachte trotzdem in 5 von 6 Fällen mehr. Dazu kämen gut 90 zusätzliche Orders pro Jahr und früher fällige Steuern.
- *Kaufen nach guten Quartalszahlen* („Zahlen-Sprung“: am Reaktionstag Kurslücke von mindestens 1 ATR nach oben, Schluss über der Eröffnung, doppeltes Volumen): allein gut – in allen 6 Fällen im Plus, 57–71 % Treffer. Im Bot aber fast ohne Wirkung: An 91 % dieser Tage kauft schon „Ausbruch“ oder „ATR-Ausbruch“ dieselbe Aktie mit demselben Stop und Ziel. Die wenigen neuen Käufe (1–9 in 5–7 Jahren) machten die Rendite in 5 von 6 Fällen etwas schlechter (im Schnitt −0,3 Prozentpunkte).
- *Halb verkaufen am Ziel, Rest laufen lassen* (die Hälfte zum Ziel verkaufen, Stop der zweiten Hälfte erst auf den Einstieg, dann 3 ATR unter dem höchsten Schluss nachziehen; Zeitstopp und Ausstieg vor Quartalszahlen bleiben; für alle oder nur die Trend-Strategien): Die einzelnen Trades wurden etwas besser (im Tagebuch in 5 von 6 Fällen mehr R je Trade), das Depot aber nicht: Rendite nur in 1 von 6 Fällen besser, im Schnitt −1,2 (alle) bzw. −1,4 (nur Trend) Prozentpunkte pro Jahr, bis −2,9. Die zweite Hälfte belegt meist bis zum Zeitstopp einen der 5 Plätze – dadurch gab es 15–20 % weniger Trades. Auch wenn der Rest (nur zur Probe) keinen Platz belegte, blieb es im Schnitt schlechter, und der größte Rückgang wurde in 5 von 6 Fällen größer.
- *Risiko nach der Marktlage* (VIX vom Vortag: 1,5 % Risiko je Trade unter 15, 1 % von 15 bis 25, 0,5 % darüber – oder ohne die 1,5-%-Stufe; alle Obergrenzen blieben): Der größte Rückgang wurde nie größer, teils 1–2 Prozentpunkte kleiner. Die Rendite war aber in 4 bzw. 5 von 6 Fällen niedriger (im Schnitt −0,6 Prozentpunkte, 2015–2021 mit der Watchlist −1,5 bzw. −1,9). Die 1,5 % in ruhigen Zeiten gleichen das nicht aus, auch weil das Gesamtrisiko von 5 % dann nur gut 3 volle Positionen zulässt. Beide Ideen zusammen: im Schnitt −1,8 Prozentpunkte, nur in 1 von 6 Fällen besser.
- *Ideen aus der Optionstheorie* (Black-Scholes-Modell: aus der Schwankung der letzten 20 Tage die Wahrscheinlichkeit, dass der Kurs sein Ziel innerhalb von 20 Handelstagen berührt – mehr dazu in den Notizen `gehirn/Notizen/Gelernt aus dem Optionsskript.md` und `gehirn/Notizen/Wissen – Optionen.md`): Bei mehreren Signalen das wahrscheinlichste zuerst zu kaufen, war im fairen Nachtest (16 Läufe mit je zufällig 80 % der Aktien, für beide Versionen dieselbe Auswahl) im Schnitt gleich gut (+0,0 Prozentpunkte, in 51 von 96 Läufen besser, 2022–2026 mit den 60 anderen Aktien −2,0 und größter Rückgang 11 → 15 %); vor das CRV gestellt im Schnitt −0,9. Signale unter 28 % Wahrscheinlichkeit weglassen: −0,2, nur in 2 von 6 Fällen besser. Wie beim Zeitwert einer Option verkaufen, sobald das Ziel in der restlichen Zeit kaum noch erreichbar ist (unter 10 % bzw. 20 %): in allen 6 Fällen schlechter, im Schnitt −5,9 bzw. −6,8 Prozentpunkte, Trefferquote etwa 45 % statt 56 %. Der Grund: Das Modell nimmt an, dass sich die Richtung eines Kurses nicht vorhersagen lässt – der Bot verdient gerade an Trends und Erholungen, die es weglässt. Und viele Trades, die tagelang stillstehen, erreichen ihr Ziel doch noch. Der Bot zeigt die Ziel-Chance deshalb nur zur Info an (siehe Gehirn).
- *Stop während des Trades anheben* (Absicherung, das Ziel bleibt; der angehobene Stop gilt ab dem nächsten Tag und wird nie gesenkt – mehr dazu in der Notiz `gehirn/Notizen/Gelernt – Stop nachziehen und absichern.md`): Stop auf den Kaufkurs, sobald der Kurs ¾ des Wegs zum Ziel geschafft hat: Rendite nur in 1 von 6 Fällen besser, im Schnitt −0,7 Prozentpunkte. Schon ab halbem Weg: in keinem Fall besser, −2,2. Stop ab halbem Weg mit 2 ATR Abstand nachziehen: −1,3, eng mit 1 ATR: −2,6 (höhere Trefferquote, aber kleinere Gewinne), der größte Rückgang wurde dabei meist größer. Viele Aktien kommen auf dem Weg zum Ziel kurz zurück und erreichen es dann doch – mit angehobenem Stop endet der Trade vorher mit fast nichts (2015–2021, Watchlist, Einstand ab halbem Weg: 764 Trades am angehobenen Stop mit Ø −0,05 R, dafür 132 Ziele weniger).
- *Kerzen- und Chartmuster vom Poster* (mehr dazu in `gehirn/Notizen/Gelernt – Muster und Lehrbücher.md`): nur mit bullischem Kerzenmuster kaufen: im Schnitt −0,9 Prozentpunkte (von −4,9 bis +4,1), bei bärischem Muster nicht kaufen: −1,5, Signale mit Muster zuerst: −0,7. Variables Ziel am nächsten Widerstand: −1,8, größter Rückgang überall größer. Variables Ziel bei Ausbrüchen (Höhe der Seitwärtsphase): +0,3, aber 2015–2021 mit den 60 anderen Aktien −1,9. Neue Strategie Doppelboden (W) mit Musterziel: −0,7, allein in 3 von 6 Fällen im Minus.
- *Ideen aus zwei Lehrbüchern* (Traden lernen, Forex Trading lernen): Trend-Strategien nur bei ADX ab 20 bzw. 25: −1,5 bzw. −3,5. Wochentrend (nur über der steigenden 150-Tage-Linie): +0,1, aber nur in 3 von 6 Fällen besser und der größte Rückgang in 4 von 6 größer. Neue Strategie Fibonacci-Rücksetzer: −1,4, Rückgang in 5 von 6 größer.
- *Mehr Aktien, mehr Positionen, Shorts* (Oktober 2026): 84 statt 24 Aktien war in allen drei Zeiträumen schlechter. Bis 15 Positionen brachte nur mit mehr Gesamtrisiko mehr Rendite (+1,3 bis +2,1, nicht überall) und dann bis 24 % statt 16 % Rückgang. Alle Short-Strategien verlieren, auch zehn verbesserte Varianten (nur im Abwärtsmarkt, nur schwache Aktien, näheres Ziel, Bruch der 200-Tage-Linie, RSI über 70 …); eine Absicherung mit einem Nasdaq-100-Short senkte überall die Rendite und vergrößerte die Rückgänge.
- *Höchstens 2 Positionen je Branche* wurde übernommen: Rendite in 5 von 6 Fällen besser (im Schnitt +0,4 Prozentpunkte, im sechsten innerhalb des Zufalls), größter Rückgang nie schlechter, meist 1–2 Prozentpunkte kleiner.

### Optionen

| Option | Bedeutung |
| --- | --- |
| `--ticker "AAPL, NFLX, SOFI"` | eigene Ticker-Liste statt `TICKER_LISTE` im Skript (US-Werte und Euro-Börsen wie `SAP.DE`) |
| `--konto 10000` | Kontogröße bzw. virtuelles Startkapital in € |
| `--risiko 1` | max. Verlust pro Trade in % des Kontos, wenn der Stop greift (auch `1,5`) |
| `--mit-short` | auch auf fallende Kurse setzen (Short) – im Test im Schnitt mit Verlust, nicht empfohlen |
| `--ohne-lernen` | keine Strategien pausieren |
| `--ohne-marktfilter` | kaufen (und mit `--mit-short` shorten) unabhängig davon, ob der Nasdaq-100 über oder unter seiner 200-Tage-Linie liegt |
| `--ohne-news` | keine Schlagzeilen laden – dann auch keine Nachrichten-Regel (Quartalszahlen-Regel bleibt) |
| `--ohne-zahlen` | keine Quartalszahlen-Termine laden – die Zahlen-Regel ist dann aus |
| `--rueckblick 6` | Monate für das virtuelle Depot (0 = aus, max. 18) |
| `--gebuehr 1` | Ordergebühr in € je Kauf/Verkauf |
| `--bruchstuecke` | auch Bruchteile von Aktien handeln |
| `--nur-schluss` | laufende Tageskerze ignorieren, nur abgeschlossene Tage bewerten |
| `--papier` | Papier-Depot fortschreiben (Vorwärtstest mit virtuellem Geld, Stand wird gespeichert); eigene Datei mit `--papier meine_datei.json` (in Colab ebenfalls im Drive-Ordner `swing_scanner`) |
| `--papier-neu` | Papier-Depot neu anfangen (der bisherige Stand bleibt als Kopie mit Datum erhalten) |
| `--bericht bericht/README.md` | alles zusätzlich als Markdown-Bericht speichern (Ticker als TradingView-Links; nutzt der automatische Lauf) |
| `--gehirn` | Notizen für Obsidian in `gehirn/` schreiben (Tagesnotiz, Trade-Tagebuch mit Lehren, Strategie- und Aktien-Seiten) und dort `Meine Regeln.md` lesen (gesperrte Aktien, ausgeschaltete Strategien); eigener Ordner mit `--gehirn ORDNER` |
| `--claude-depot DATEI` | Claude-Depot (Versuch, nur mit `--papier`): startet als Kopie des Papier-Depots und rechnet mit denselben Regeln weiter – ohne die Signale, die Claude rechtzeitig ausgelassen hat |
| `--claude-entscheidungen DATEI` | Claudes Entscheidungen fürs Claude-Depot (Kommentare aus dem GitHub-Thema als JSON; holt der automatische Lauf) |
| `--uebersicht DATEI` | Daten für die Übersichtsseite (`docs/index.html`) als JSON in DATEI schreiben (nutzt der automatische Lauf: `docs/daten.json`) |
| `--live DATEI` | nur Live-Vorschau: aktuelle Kurse, dazu `--papier` und `--claude-depot` nach denselben Regeln bis jetzt weitergerechnet (Käufe, Stop, Ziel) als JSON in DATEI (nutzt der Ablauf `live.yml`: `docs/live.json`) – ohne neue Signale, speichert sonst nichts |
| `--nachricht DATEI` | bei Kauf-Signalen den Handelsplan als kurze Nachricht in DATEI schreiben, nach dem letzten Handelstag der Woche dazu den Wochenrückblick des Übungsdepots (nutzt der automatische Lauf für die Nachricht aufs Handy; ohne Signal und Wochenrückblick wird die Datei gelöscht) |
| `--csv signale.csv` | Scanner-Tabelle als CSV für Excel speichern, alle Depot-Trades in `signale_trades.csv` |
| `--debug` | Original-Meldungen von yfinance anzeigen |

Die festen Regeln (Positionsgrenzen, Lernregel, Zeitstopp …) stehen als Konstanten oben im Skript. Sie sind bewusst vorab festgelegt: Wer sie so lange verstellt, bis der Rückblick gut aussieht, passt sie nur an den Zufall der Vergangenheit an.

Daten: 5 Jahre Tageskerzen, Quartalszahlen-Termine und Schlagzeilen von Yahoo Finance. Mit `--mit-short`: Short-Positionen (z. B. per CFD oder Turbo-Schein) haben nach oben offene Verluste; Leih- und Finanzierungskosten sind im Rückblick nicht berücksichtigt. Der Rückblick nutzt die heutige Watchlist und sieht deshalb für Kauf-Strategien tendenziell zu gut aus. Vergangene Ergebnisse sind keine Garantie für die Zukunft; die Ausgabe ist keine Anlageberatung.
