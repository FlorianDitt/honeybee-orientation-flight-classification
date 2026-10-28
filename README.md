# Orientierungsflug oder Sammelflug?

**Klassifikation von Flugbahnen junger Bienen vor dem Flugloch**
Studienarbeit WDS224 *Machine Learning System Design and Operations* (DHBW Ravensburg, Prof. Mark Schutera) · Florian Dittmann

<img src="presentation/assets/flights_seq050.jpg" width="360" align="right" alt="Getrackte Flugbahnen vor Stock A: kurvige Bahnen orange, gerade blau">

Bevor junge Honigbienen Nektar und Pollen sammeln, lernen sie in **Orientierungsflügen** die Lage ihres Stocks:
Sie fliegen Schleifen und Bögen vor dem Flugloch, statt direkt abzufliegen. Dieses Projekt erzeugt aus
ungelabelten Flugloch-Videos automatisch Flugbahnen, leitet daraus Selbst-Labels ab (Start und Ziel der Bahn)
und trainiert einen Trajektorien-Klassifikator, der **Orientierungsflüge**, **direkte Sammelabflüge** und
**suchende Landeanflüge** unterscheidet. Der Anteil der Orientierungsflüge über die Zeit ist ein
nicht-invasiver Indikator für den Nachschub an neuen Sammlerinnen und damit für die Vitalität des Volkes.

Getestet wird zweistufig: auf einem späteren Zeitblock desselben Stocks (**Test A**) und auf einem zweiten
Stock mit anderem Holz, Licht und Kamera-Abstand (**Test B**).

**Status:** Machbarkeitsstudie abgeschlossen ([docs/vorstudie.md](docs/vorstudie.md)). Auf 7 × 30 s von Stock A
finden sich 509 Flugbahnen, davon 21 kurvige Abflüge vom Flugbrett als Orientierungsflug-Kandidaten.
Größte offene Baustelle: 71 % der Bahnen reißen über dem Gras ab.

<br clear="right">

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/idee.md](docs/idee.md) | Biologischer Hintergrund, Forschungsfragen, Hypothesen, Literatur, Abgrenzung zu anderen Themen |
| [docs/methode.md](docs/methode.md) | Pipeline, Selbst-Labels, Modelle, Metriken, Split und Evaluationsprotokoll |
| [docs/vorstudie.md](docs/vorstudie.md) | Ergebnisse der Machbarkeitsprüfung, Beobachtungen, verworfene Themen |
| [docs/labeling.md](docs/labeling.md) | Label-Leitfaden für die vier Klassen |
| [docs/roadmap.md](docs/roadmap.md) | Weg zum Endprodukt: Phasen, Wochenplan, Entscheidungspunkte |
| [presentation/](presentation/) | Marp-Präsentation (3 Folien, deutsch) |

## Setup

```bash
uv sync                               # legt .venv an und installiert das Paket editierbar
uv sync --extra ml                    # zusätzlich PyTorch für den Klassifikator
.venv/bin/hf auth login               # der Datensatz ist gated: Bedingungen auf Hugging Face akzeptieren
uv run beeflight-splits --download train
uv run beeflight-splits --download val
```

Datensatz: [mrkschtr/thehiveisreal](https://huggingface.co/datasets/mrkschtr/thehiveisreal), 96 Sequenzen à 30 s,
59,94 fps, 1080 × 1920 (Hochformat), H.264. Ein Video ≈ 100 MB, Training + Validierung ≈ 6,5 GB.
Die Testsets erst ganz am Ende herunterladen und genau einmal auswerten.

## Benutzung

```bash
uv run beeflight-splits                                  # Split-Übersicht, schreibt splits.json
uv run beeflight-tracks rec2123_seq050 rec2123_seq060    # Flugbahnen -> outputs/flights/<seq>.json + .jpg
uv run beeflight-figures                                 # Abbildungen für die Präsentation
uv run beeflight-sample --split train --n 300            # Label-Warteschlange -> labels/queue_train.json
uv run pytest                                            # Tests
```

**Handlabels** in der Web-App: `cd labeler && npm install && npm run dev`, dann http://127.0.0.1:4321
(Details in [labeler/README.md](labeler/README.md)).

Eine Sequenz braucht etwa eine Minute (8 Kerne) und rund 1 GB RAM.

## Projektstruktur

```
src/beeflight/
  splits.py      Train/Val/Test-Split (einzige Quelle der Wahrheit), Download
  tracks.py      Vordergrund, Gras-Maske, Tracking, Bahnmerkmale, Start-/Zielzonen
  figures.py     Abbildungen für die Folien
  sample.py      stratifizierte Label-Warteschlangen
labeler/         Astro-Web-App zum Handlabeln
labels/          Warteschlangen und Handlabels (versioniert)
tests/           Split-Invarianten, Bahnmerkmale, Tracker
docs/            Dokumentation der Idee und Methode
presentation/    Marp-Folien (slides.md, theme/hive.css, assets/)
outputs/         erzeugte Flugbahnen (nicht versioniert)
data/            Videos (nicht versioniert)
archive/         Prototypen verworfener Themen (Bewegungsunschärfe, Leichenträger), nicht gepflegt
```

## Split

| Split | Sequenzen | Dauer | Zweck |
|---|---|---|---|
| train | rec2123 Seq. 015–069 | 27,5 min | Training, Handlabels |
| val | rec2123 Seq. 071–084 | 7 min | Hyperparameter, Schwellen, Early Stopping |
| test_same_hive (A) | rec2123 Seq. 086–089 | 2 min | Generalisierung über die Zeit |
| test_other_hive (B) | rec2125 Seq. 000–020 | 10,5 min | Generalisierung auf einen neuen Stock |

Zwischen den Blöcken liegt je eine verworfene Puffersequenz (070, 085), damit keine Flugbahn eine Split-Grenze
überquert. Details und Begründung in [docs/methode.md](docs/methode.md#split-und-evaluationsprotokoll).
