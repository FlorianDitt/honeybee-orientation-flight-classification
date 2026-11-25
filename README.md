# Orientierungsflug oder Sammelflug?

**Klassifikation von Flugbahnen junger Bienen vor dem Flugloch**
Studienarbeit WDS224 *Machine Learning System Design and Operations* (DHBW Ravensburg, Prof. Mark Schutera) · Florian Dittmann

Bevor junge Honigbienen Nektar und Pollen sammeln, lernen sie in **Orientierungsflügen** die Lage ihres Stocks:
Sie fliegen Schleifen und Bögen vor dem Flugloch, statt direkt abzufliegen. Dieses Projekt erzeugt aus
ungelabelten Flugloch-Videos automatisch Flugbahnen und trainiert auf Handlabels einen Trajektorien-Klassifikator, der **Orientierungsflüge**, **direkte Sammelabflüge** und
**suchende Landeanflüge** unterscheidet. Der Anteil der Orientierungsflüge über die Zeit ist ein
nicht-invasiver Indikator für den Nachschub an neuen Sammlerinnen und damit für die Vitalität des Volkes.

Getestet wird zweistufig: auf einem späteren Zeitblock desselben Stocks (**Test A**) und auf einem zweiten
Stock mit anderem Holz, Licht und Kamera-Abstand (**Test B**).

**Status:** abgeschlossen und präsentiert (November 2026). Eingefroren ist ein Ensemble aus 5 ResNets auf der
Flugbahn mit einem YOLO26s-Vorfilter gegen Artefakte. Einmalige Testauswertung (Balanced Accuracy):

| Testset | Modell | Regel-Baseline |
|---|---|---|
| Test A (gleicher Stock, später) | 0,657 | 0,642 |
| Test B (anderer Stock) | 0,758 | 0,677 |

F1 für `orientierung` liegt auf beiden Testsets bei etwa 0,58. Alles danach (z. B. BoT-SORT) ist nur auf val
ausgewertet.

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

**Handlabels** in der Web-App: `cd labeler && npm install && npm run dev`, dann http://127.0.0.1:4321.
Freunde labeln online unter https://florianditt.github.io/BeeHive/ (Clips mit `uv run beeflight-clips`,
Deploy mit `npm run deploy:web`), `uv run beeflight-vote` bildet daraus Mehrheitslabels
(Details in [labeler/README.md](labeler/README.md)).

Eine Sequenz braucht etwa eine Minute (8 Kerne) und rund 1 GB RAM.

## Projektstruktur

```
src/beeflight/
  splits.py      Train/Val/Test-Split (einzige Quelle der Wahrheit), Download
  tracks.py      Vordergrund, Gras-Maske, Tracking, Bahnmerkmale, Start-/Zielzonen
  figures.py     Abbildungen für die Folien
  sample.py      stratifizierte Label-Warteschlangen
  clips.py       zugeschnittene Clips und Pakete für die Online-Version
  vote.py        Mehrheitsentscheid über alle Labelnden, Krippendorffs α
  metrics.py     Metriken, Cluster-Bootstrap, Wilson-Intervalle
  evaluate.py    Auswertung von Vorhersagedateien, Test nur mit --test
  baselines.py   Regel, immer eine Klasse, Zufall
  resnet.py      Kandidat 1: ResNet auf der Bahn (gewählt)
  image_features.py  Kandidat 2: DINOv2 auf Ausschnitten
  fusion.py      Kandidaten 3 und 4: Fusion und G-Blend
labeler/         Astro-Web-App zum Handlabeln (lokal und als GitHub-Pages-Seite)
labels/          Warteschlangen, Handlabels, votes/ (Exporte der Helfenden), final_*.jsonl
tests/           Split-Invarianten, Bahnmerkmale, Tracker, Stichprobe, Mehrheitsentscheid
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

## Danke

Großer Dank an [@dariandieck](https://github.com/dariandieck) für die Bienen-Labels, auf denen das YOLO für den
Vorfilter trainiert ist. Die Labels selbst sind nicht Teil dieses Repos. Danke auch an die beiden Freiwilligen
(Labeler 2 und 3), die die Testsets mitgelabelt haben.

## Lizenz

- **Code:** MIT, siehe [LICENSE](LICENSE).
- **Daten, Labels, Abbildungen und Clips:** abgeleitet aus [mrkschtr/thehiveisreal](https://huggingface.co/datasets/mrkschtr/thehiveisreal)
  und daher wie der Datensatz unter [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
  Quelle: Schutera, Mark, *thehiveisreal* (2026).
- **Videos, Clips und Einzelbilder** aus dem Datensatz sind nicht enthalten, weil der Datensatz gated ist. Zugang
  wie unter [Setup](#setup) beschrieben; danach erzeugen `uv run beeflight-figures` und `presentation/make_figures.py`
  die Bilder und Clips der Präsentation lokal.
