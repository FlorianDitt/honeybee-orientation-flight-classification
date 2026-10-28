# Labeler

Lokale Web-App (Astro 5, Node-Adapter) zum Handlabeln von Flugbahnen. Spielt jede Bahn als vergrößerten Ausschnitt
aus dem Originalvideo ab, zeichnet die Bahn synchron ein und speichert ein Label pro Tastendruck.

## Start

```bash
# einmalig im Projekt-Root: Bahnen erzeugen und Warteschlangen ziehen
uv run beeflight-tracks --split train --split val --skip-existing
uv run beeflight-sample --split train --n 300
uv run beeflight-sample --split val --n 80

# im Ordner labeler/
npm install
npm run dev          # http://127.0.0.1:4321
```

Alternativ gebaut: `npm run build && npm start` (gleicher Port, schneller beim Laden).
Benötigt Node ≥ 22 und Chrome, Edge oder Firefox ≥ 132 (für `requestVideoFrameCallback`; ältere Browser laufen
mit ungenauerer Synchronisation).

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
| `labels/queue_<split>.json` | Warteschlange von `beeflight-sample`, gemischt, mit Geometrie (Frames + Koordinaten) |
| `labels/<split>.jsonl` | ein Label pro Zeile: Klasse, Flags, Notiz, Zeitstempel **plus die komplette Bahn** |

Weil jedes Label die Bahn selbst enthält, bleiben die Labels gültig, auch wenn der Tracker später ausgetauscht wird
(z. B. durch den gelernten Detektor). Speichern schreibt die Datei atomar neu; `labels/` gehört ins Git.

Der Split `recheck` (blindes Zweitlabeln für Cohen's κ) sieht die Labels aus `train` nicht.

## Aufbau

```
src/lib/store.ts                 Pfade, Warteschlangen lesen, Labels atomar schreiben
src/pages/index.astro            Übersicht: Fortschritt pro Split
src/pages/label/[split].astro    Label-Ansicht (Canvas-Zoom, Overlay, Tastatur)
src/pages/api/[split]/labels.ts  GET/POST/DELETE Labels
src/pages/video/[seq].ts         Video-Streaming mit HTTP-Range (Springen in 100-MB-Dateien)
```

`BEEHIVE_ROOT` setzt das Projektverzeichnis, falls die App nicht aus `labeler/` gestartet wird.
Die App lauscht nur auf `127.0.0.1` und ist nicht für den Betrieb im Netz gedacht.
