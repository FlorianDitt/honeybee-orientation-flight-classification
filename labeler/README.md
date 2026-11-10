# Labeler

Web-App (Astro 5) zum Handlabeln von Flugbahnen. Spielt jede Bahn als vergrößerten Ausschnitt ab, zeichnet die Bahn
synchron ein und speichert ein Label pro Tastendruck. Es gibt sie in zwei Varianten mit derselben Oberfläche:

| | lokal (`astro.config.mjs`) | online (`astro.config.web.mjs`) |
|---|---|---|
| für | dich | Freundinnen und Freunde, Mehrheitsentscheid |
| Videos | Originalvideos aus `data/`, per HTTP-Range | kurze zugeschnittene Clips aus `beeflight-clips` |
| Labels | `labels/<split>.jsonl` über die lokale API | `localStorage`, Export als Datei |
| Hosting | `127.0.0.1:4321` | GitHub Pages, Branch `gh-pages` |

## Start

```bash
# einmalig im Projekt-Root: Bahnen erzeugen und Warteschlangen ziehen
uv run beeflight-tracks --split train --split val --skip-existing
uv run beeflight-sample --split train --n 300 --all
uv run beeflight-sample --split val --n 80 --all

# im Ordner labeler/
npm install
npm run dev          # http://127.0.0.1:4321
```

Alternativ gebaut: `npm run build && npm start` (gleicher Port, schneller beim Laden).
Benötigt Node ≥ 22 und Chrome, Edge oder Firefox ≥ 132 (für `requestVideoFrameCallback`; ältere Browser laufen
mit ungenauerer Synchronisation).

## Online-Version für Freunde (GitHub Pages)

```bash
# einmalig: Zufallsstichproben der Testsets ziehen
uv run beeflight-sample --split test_same_hive --n 100 --flights outputs/flights_chiron_linked
uv run beeflight-sample --split test_other_hive --n 100 --flights outputs/flights_chiron_linked

uv run beeflight-clips        # Clips + public-web/data/site.json (Testsets, mit --split train --split val die alten Pakete)
cd labeler
npm run dev:web               # Test: http://127.0.0.1:4322/BeeHive/
npm run deploy:web            # baut und pusht nach gh-pages -> https://florianditt.github.io/BeeHive/
```

**Ablauf für die Helfenden:** Name eingeben → Tutorial (8 Beispielbahnen aus `labels/tutorial.json`, je Klasse
mit Erklärung, nur anschauen) → das Paket labeln, das du ihnen nennst (≈ 50 Bahnen) → „Ergebnisse senden“ öffnet
das Teilen-Menü des Handys (WhatsApp, Signal, Mail) mit der `.jsonl`-Datei; ohne Teilen-Funktion wird sie
heruntergeladen. Die Pakete sind erst nach dem Tutorial freigeschaltet (oder nach der früheren Übungsrunde).

**Pakete verteilen:** Paket 1–2 sind Test A, Paket 3–4 Test B; die Seite zeigt nur die Nummern. Für drei Stimmen
pro Bahn braucht jedes Paket zwei Helfende plus dich. Bei 4 Helfenden mit je 2 Paketen (eins aus A, eins aus B) ist
alles doppelt abgedeckt.

**Auswerten:** Exportdateien auf der lokalen Startseite über **Exporte hochladen** einspielen (oder von Hand nach `labels/votes/` legen), dann `uv run beeflight-vote` (Test-Stimmen erst nach dem Einfrieren mit `--test`)
(Mehrheitsregel und Ausgabe siehe [docs/labeling.md](../docs/labeling.md#mehrere-labelnde)).

**Selbst online labeln (langsame Verbindung):** `uv run beeflight-clips --own 200 100` legt zusätzlich Pakete
„Eigene Train 1–4“ und „Eigene Validierung 1–2“ an: die nächsten ungelabelten Bahnen der vollen Train- und
Val-Warteschlange, in derselben Reihenfolge wie lokal. Sie erscheinen nur mit `?own` in der URL (bleibt im Browser
gespeichert, `?own=0` beendet es); in diesem Modus sind die Testpakete ausgeblendet. Den Export **nicht** nach
`labels/votes/` legen, sondern `uv run beeflight-own <datei.jsonl>`: schreibt die Labels mit Geometrie nach
`labels/<split>.jsonl`, wie die lokale App, mit `"source": "online"`.

Die früheren Übungsbahnen (`labels/practice.json`) und die Tutorial-Bahnen kommen in keinem Paket vor; eine
Tutorial-Bahn wird nachträglich aus ihrem Paket genommen, die anderen Bahnen bleiben in ihrem Paket. Die Pages-Seite ist öffentlich,
auch wenn das Repository privat ist: Den Link nur direkt weitergeben. Die Clips landen nur im Branch `gh-pages`
(ein einziger Commit, wird bei jedem Deploy ersetzt), nicht in der Historie von `main`.

## Bedienung

| Taste | Aktion |
|---|---|
| `1` – `4` | Klasse speichern (orientierung, sammelabflug, anflug, artefakt), weiter zur nächsten offenen Bahn |
| `F` / `U` | Flag Fragment / unsicher umschalten (vor der Klasse setzen) |
| `Leertaste` | Pause / Abspielen |
| `R` | Bahn von vorn |
| `S` | Tempo ¼× → ½× → 1× |
| `Z` | Ausschnitt weiter / enger |
| `←` / `→` | vorherige / nächste Bahn (auch bereits gelabelte, zum Korrigieren) |
| `N` | nächste offene Bahn |

Im Zoom: weiß gestrichelt die ganze Bahn, farbig der bereits geflogene Teil, weißer Kreis die aktuelle Position,
weißes Quadrat der Startpunkt. Rechts oben das Gesamtbild mit dem Ausschnitt. Abgespielt wird die Bahn mit
20 Frames Vorlauf und Nachlauf in Schleife.

## Daten

| Datei | Inhalt |
|---|---|
| `labels/queue_<split>.json` | Warteschlange von `beeflight-sample`: zuerst die Stichprobe (`core`), dann alle übrigen Bahnen, mit Geometrie |
| `labels/<split>.jsonl` | ein Label pro Zeile: Klasse, Flags, Notiz, Zeitstempel **plus die komplette Bahn** |

Weil jedes Label die Bahn selbst enthält, bleiben die Labels gültig, auch wenn der Tracker später ausgetauscht wird
(z. B. durch den gelernten Detektor). Speichern schreibt die Datei atomar neu; `labels/` gehört ins Git.

Der Split `recheck` (blindes Zweitlabeln für Cohen's κ) sieht die Labels aus `train` nicht, ebenso `recheck_val`
(`beeflight-sample --recheck 50 --recheck-split val`) die aus `val`.

## Aufbau

```
src/lib/labeler.ts               gemeinsam: Abspielen, Overlay, Tastatur, Navigation (Browser)
src/components/LabelView.astro   gemeinsam: Markup und Stil der Label-Ansicht
src/lib/store.ts                 lokal: Pfade, Warteschlangen lesen, Labels atomar schreiben
src/pages/index.astro            lokal: Übersicht, Fortschritt pro Split
src/pages/label/[split].astro    lokal: Label-Ansicht mit Originalvideo
src/pages/api/[split]/labels.ts  lokal: GET/POST/DELETE Labels
src/pages/video/[seq].ts         lokal: Video-Streaming mit HTTP-Range (Springen in 100-MB-Dateien)
src/lib/webstore.ts              online: localStorage, Export/Import
web/pages/index.astro            online: Name, Tutorial, Pakete, Senden
web/pages/label.astro            online: Label-Ansicht mit Clips (?p=<paket>|practice)
web/pages/leitfaden.astro        online: Kurzfassung von docs/labeling.md für Laien
scripts/deploy-pages.sh          Build + Push nach gh-pages
public-web/                      von beeflight-clips erzeugt (nicht versioniert)
```

`BEEHIVE_ROOT` setzt das Projektverzeichnis, falls die App nicht aus `labeler/` gestartet wird.
Die lokale App lauscht nur auf `127.0.0.1` und ist nicht für den Betrieb im Netz gedacht.
