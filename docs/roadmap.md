# Roadmap zum Endprodukt

Stand 28.10.2026. Präsentationstermine im Kurs: 25.11. oder 01.12. Der Plan rechnet mit dem **25.11.**;
beim 01.12. wird Woche 5 zum Puffer.

## Endprodukt

Am Ende stehen drei Dinge:

1. **Ein lauffähiges System**: Video rein, pro Sequenz die klassifizierten Flugbahnen und der Anteil
   Orientierungsflüge raus (`beeflight-run <seq>`), reproduzierbar aus diesem Repository.
2. **Eine ehrliche Auswertung**: Balanced Accuracy, Recall und Precision „Orientierung“ auf Test A und Test B mit
   Konfidenzintervallen, Vergleich gegen die Regel-Baseline, Domain-Shift-Analyse.
3. **Die Präsentation**: drei Folien, 15 min plus Fragen, mit echten Zahlen statt Platzhaltern.

```
 Woche 1          Woche 2           Woche 3            Woche 4            Termin
 28.10.–03.11.    04.11.–10.11.     11.11.–17.11.      18.11.–24.11.      25.11.
 ─────────────────────────────────────────────────────────────────────────────────
 Bahnen für alle  Detektor          Modelle            Test einmal        Vortrag
 Label-Tool       Labels 300+80     Vergleich auf Val  Folien, Proben
 erste 100 Labels ▲ Gate 1          ▲ Gate 2           ▲ Freeze
```

## Phase 0: erledigt

- [x] Thema gefunden, Machbarkeit geprüft, im Moodle angemeldet
- [x] Split nach Zeitblöcken mit Puffern, zwei Testsets
- [x] Tracking-Prototyp (Hintergrundmodell, Gras-Maske, Hungarian-Tracking, Selbst-Labels)
- [x] Vorstudie: 509 Bahnen, 21 kurvige Abflüge in 7 × 30 s ([vorstudie.md](vorstudie.md))
- [x] Projektstruktur, Tests, Dokumentation, Folienentwurf

## Phase 1: Daten und Label-Tool (Woche 1)

- [x] `beeflight-tracks` auf **alle 69 Trainings- und Validierungssequenzen**
- [x] **Label-App** (`labeler/`, Astro): Bahn als vergrößerter Clip mit synchron eingezeichneter Bahn,
      Tasten 1–4, Flags, schreibt `labels/<split>.jsonl` inklusive Geometrie
- [x] Stichprobe ziehen nach [labeling.md](labeling.md): stratifiziert, gemischt, ohne Selbst-Label
- [ ] **Erste 100 Bahnen labeln** (≈ 1 h): zeigt früh, ob die Klassen trennbar sind und wie oft
      `artefakt` vorkommt

**Ergebnis:** alle Bahnen als JSON, 100 Labels, erste Klassenverteilung.

## Phase 2: Detektor gegen die Fragmente (Woche 1–2)

Tracker v2 und v3 haben den Anteil vollständiger Bahnen von 32 % auf 67 % gehoben
([Nachtrag](vorstudie.md#nachtrag-tracker-v2-und-v3)). Ein gelernter Detektor soll den Rest angehen.

- [x] Tracker v2: Schwelle 18, Zonen 30 px, Verbinden von Fragmenten; Labels auf v2 übertragen
  (`beeflight-sample --carry`), alte Stände in `labels/archive/background-v1/`
- [x] Tracker v3: Blobs zusammenfassen, keine Neugeburt neben einer Bahn, Kurven, Überlappungen verbinden

### Zwei-Paper-Plan: ByteTrack + HyDaT

Für die Präsentation stützt sich der Detektor-Tracker auf genau zwei Paper:

1. **ByteTrack** (Zhang et al. 2022, arXiv 2110.06864) ist der Tracker, unverändert aus Ultralytics übernommen.
   Kernidee BYTE: Detektionen mit hoher Konfidenz setzen Bahnen fort und starten neue, solche mit niedriger
   Konfidenz dürfen nur Bahnen fortsetzen, die sonst verloren gingen.
2. **HyDaT** (Ratnayake et al. 2021, PLOS ONE) ist die Verbesserung: Hintergrundmodell und gelernter Detektor
   zusammen statt Detektor allein (dort 86,6 % gegen 60,7 % der Frames mit YOLO allein, bei gleich wenig
   Trainingsdaten). Umsetzung: Die Blobs des Hintergrundmodells (Tracker v3) gehen als Boxen mit niedriger
   Konfidenz in ByteTrack ein. So füllen sie Lücken, wo YOLO eine getarnte Biene verliert, starten aber nie
   eine Bahn.

Eine Anpassung, kein drittes Paper: ByteTrack ordnet über die Überlappung (IoU) zu. Auf den v3-Bahnen fallen
mit bienengroßen Boxen (30 px) 5,4 % der Schritte unter IoU 0,2, mit **60-px-Boxen** 0,5 %. Darum sind alle
Boxen 60 px groß. Schwachstelle bleibt der erste Schritt einer neuen Bahn (noch keine Geschwindigkeit:
27 % unter IoU 0,2). Als Variante ordnet `--match center` über den Mittelpunktsabstand zu (Kosten
Abstand / 112 px, gedeckelt bei 1; ByteTracks Schwellen entsprechen dann 90, 78 und 56 px). C-BIoU
(Yang et al., WACV 2023) zeigt, dass vergrößerte Boxen ein etablierter Ansatz sind.

Ablation auf den 14 Validierungssequenzen (`beeflight-detector compare --split val`), vollständig = weder
Start noch Ende „lost“, kurvig = Gesamtdrehung > 360°:

| Tracker | Bahnen | vollständig | kurvig | übrige | Bahnzeit | Start lost |
|---|---|---|---|---|---|---|
| v3 (Hintergrundmodell) | 884 | **80,0 %** | 81,7 % | 78,8 % | 696 s | 12 % |
| ByteTrack (IoU) | 340 | 19,1 % | 29,0 % | 14,6 % | 189 s | 71 % |
| ByteTrack + HyDaT (IoU) | 386 | 19,4 % | 31,1 % | 14,2 % | 216 s | 71 % |
| ByteTrack (Mittelpunkt) | 603 | 33,7 % | 39,2 % | 30,7 % | 437 s | 53 % |
| ByteTrack + HyDaT (Mittelpunkt) | 719 | 36,4 % | 39,5 % | 34,6 % | 527 s | 54 % |

Befund: Der Detektor sieht die Bienen auch im unteren Bildteil, ByteTrack verknüpft sie dort aber kaum
(v3: 8 495 Bahnpunkte unterhalb von 300 px halber Auflösung unter der Brettoberkante, ByteTrack: 193). Nahe der
Kamera fliegt eine Biene ≈ 40 px pro Frame (volle Auflösung). Zwei 60-px-Boxen mit diesem Versatz haben IoU 0,2,
genau ByteTracks Grenze. `fuse_score` multipliziert die IoU zusätzlich mit der Konfidenz, und unscharfe Bienen
haben wenig davon. Neue Bahnen brauchen im zweiten Frame einen Treffer. Die Bahnen beginnen deshalb erst nahe
dem Brett, mitten im Bild. ByteTrack ist für Fußgänger gebaut (scharf, groß, langsam). HyDaT hilft
(+0,3 bzw. +2,7 Punkte), Mittelpunktszuordnung hilft mehr (+14 bis +17 Punkte), beides bleibt weit unter v3.

- [x] `beeflight-detector bootstrap`: Kacheln der Flugzone (640 px, volle Auflösung) mit 60-px-Boxen um die
      Punkte der v3-Bahnen, jede zweite Trainingssequenz, alle 2 s ein Frame
- [ ] Bootstrap-Labels stichprobenartig prüfen: entfällt nach Gate 1 (Detektor nicht weiterverfolgt)
- [x] `beeflight-detector train`: YOLO11n auf der CPU, 30 Epochen (YOLO-Val: P 0,79, R 0,61, mAP50 ≈ 0,7)
- [x] `beeflight-detector track --mode bytetrack|hybrid --match iou|center`: schreibt
      `outputs/flights_{bytetrack,hybrid}[_center]/` im selben Format wie v3; die Handlabels auf v3 bleiben unberührt
- [x] `beeflight-detector compare --split val`: Ablation gemessen (Tabelle oben)
- [ ] Zahlen in die Vorstudie und auf Folie 2
- [ ] ~~Bewegungskanal (Differenzbild) als Zusatzinput~~ entfällt nach Gate 1

> **Gate 1 (Ende Woche 2), entschieden:** ByteTrack + HyDaT erreicht auf Validierung 36 % vollständige Bahnen,
> v3 80 %. **Das Hintergrundmodell (v3) bleibt.** Die Präsentation erzählt den Detektor als ehrlichen
> Negativbefund: Die Zuordnung von ByteTrack setzt kleine Bewegung zwischen Frames voraus, schnelle Insekten nahe
> der Kamera brechen diese Annahme.

### Zitierbarer Tracker: SORT auf den Blobs des Hintergrundmodells

v3 ist im Kern ein Standardverfahren, nur ohne Paper als Vorlage. Deshalb ersetzt `beeflight-sort` (`src/beeflight/sort.py`)
nur den Zuordnungsschritt durch **SORT** (Bewley et al. 2016, arXiv 1602.00763): Kalman-Filter mit konstanter
Geschwindigkeit, Hungarian-Zuordnung, neue Bahn je unzugeordneter Detektion. Detektion, Stitching und Merkmale
bleiben die von v3, die Blobs werden in `outputs/blobs/` gecacht (v3 darauf reproduziert die gespeicherten Bahnen
exakt). Domänen-Paper ist **Chiron et al. 2013** (EURASIP JIVP 2013:59): Bienen vor dem Flugloch,
Median-Hintergrund, Kalman-Filter und Global Nearest Neighbor per Hungarian-Methode auf Abstand statt Überlappung,
Bahn gelöscht nach 3 Fehlframes. MHT war dort kaum besser als GNN, verpasste Detektionen schaden weit mehr als
Fehlalarme.

Anpassungen, einzeln auf Validierung gemessen (vollständige Bahnen):

| Schritt | vollständig |
|---|---|
| SORT wie veröffentlicht (Mittelpunktsabstand statt IoU, Bahn stirbt nach 1 Fehlframe) | 62,1 % |
| Bahn übersteht 5 Fehlframes (wie v3) | 66,8 % |
| + Geschwindigkeitsrauschen 1 statt 0,01 (Biene wendet in wenigen Frames, Fußgänger nicht) | 76,6 % |
| + kein Bahnstart innerhalb 20 px einer gerade zugeordneten Biene (Flügel/Schatten) = **SORT für Bienen** | 79,7 % |
| (+ v3s Kosten über die letzte Position, nicht übernommen) | 80,3 % |

Gewählt wurde auf Validierung, darum Bestätigung auf den 55 Trainingssequenzen, an denen nichts eingestellt wurde:

| | v3 Val | SORT Val | SORT für Bienen Val | v3 Train | SORT Train | SORT für Bienen Train |
|---|---|---|---|---|---|---|
| Bahnen | 884 | 972 | 898 | 4 039 | 4 159 | 4 061 |
| vollständig | 80,0 % | 62,1 % | 79,7 % | 63,6 % | 51,3 % | **64,5 %** |
| Zeit in vollständigen Bahnen | 571 s | 397 s | 550 s | 1 875 s | 1 267 s | 1 838 s |
| Bahnen > 1 s | 23,6 % | 15,9 % | 22,7 % | 22,3 % | 13,8 % | 20,7 % |
| kurvig vollständig | 81,7 % | 66,4 % | 78,7 % | 57,0 % | 48,5 % | 57,9 % |
| übrige vollständig | 78,8 % | 59,9 % | 80,5 % | 68,6 % | 52,7 % | 68,9 % |

SORT für Bienen und v3 sind gleichauf (Train +0,9 Punkte vollständig, 2 % weniger Zeit in vollständigen Bahnen).
SORT wie veröffentlicht ist überall klar schlechter.

**Stückelungs-Bias:** Auf Train sind kurvige Bahnen bei beiden Trackern deutlich seltener vollständig als übrige
(57 % gegen 69 %), auf Validierung nicht. Genau davor warnt Polytrack (Abschnitt 5.1). Der Indikator
„Anteil Orientierungsflüge“ unterschätzt Orientierungsflüge also eher. In der Auswertung berichten und
Fragmente als eigene Kategorie mitzählen.

- [x] `beeflight-sort track|compare`: SORT und SORT für Bienen, Ablation und Train-Bestätigung (Tabellen oben)
- [x] Entscheiden, ob die Labels umziehen: **ja, auf Chiron + Huang (`flights_chiron_linked`)**, 02.11.2026.
      v3-Stand in `labels/archive/background-v3/`; 140 von 205 eigenen Labels übertragen (Rest: Bahn stark
      verändert, neu labeln), 237 von 321 Stimmen von Labeler3 über `labels/id_map_<split>.json`. Online-Seite
      bleibt bis zum Ende der laufenden Runde auf v3.
- [ ] Optional nach Chiron: Mahalanobis- statt euklidischer Abstand als Kosten

## Phase 3: Labels (Woche 2)

- [x] **Online-Labeler** für Freunde (GitHub Pages, Übungsrunde, Pakete, Export) und `beeflight-vote`
- [ ] **300 Trainingsbahnen** und **80 Validierungsbahnen** gelabelt (≈ 3–4 h, auf mehrere Tage verteilt)
- [ ] 8 Pakete an Helfende verteilen (je zwei pro Paket), Exporte nach `labels/votes/`, `beeflight-vote`
- [ ] Mindestens **40 Orientierungsflüge** im Training, sonst gezielt kurvige Abflüge nachziehen
- [ ] Übereinstimmung berichten: Krippendorffs α über alle Labelnden (Zweitlabeln für Cohen's κ nur noch optional)

## Phase 4: Modelle (Woche 3)

Modelle und Begründung in [methode.md](methode.md#5-modelle).

- [x] **Baselines** (`beeflight-baselines`): Regel mit Schwellen auf Train, feste Regel, immer eine Klasse, Zufall
- [x] **Kandidat 1: ResNet auf der Bahn** (`beeflight-resnet`)
- [x] **Kandidat 2: DINOv2 auf Ausschnitten** (`beeflight-dinov2`)
- [x] **Kandidaten 3 und 4: Fusion und G-Blend** (`beeflight-fusion`)
- [x] Vergleich auf Validierung: **ResNet gewählt**, aber nicht klar besser als die Regel
- [ ] Details des ResNet am Volltext von Fawaz et al. 2019 prüfen (arXiv 1809.04356), bevor sie zitiert werden
- [ ] Experimente als JSON in `outputs/runs/` (Konfiguration, Seed, Git-Hash, Metriken), damit jede Zahl auf den
      Folien reproduzierbar ist
- [ ] Zweitlabeln der 50 Bahnen, κ berechnen

> **Gate 2 (Ende Woche 3):** Schlägt das Modell die Baseline auf Validierung nicht klar, wird trotzdem eingefroren. Dann
> lautet das Ergebnis: Die einfache Regel reicht fast, und die Diskussion erklärt, warum.

## Phase 5: Einfrieren und Test (Anfang Woche 4)

- [ ] **Freeze**: bestes Modell, alle Schwellen und Zonen festschreiben, Commit taggen (`v1.0-freeze`)
- [ ] Testsets herunterladen (`beeflight-splits --download test_same_hive`, `… test_other_hive`)
- [ ] Zonen für Stock B aus einem einzelnen Frame setzen, nicht anhand von Ergebnissen
- [ ] Testbahnen erzeugen und **erst jetzt** labeln (Test A: 4 Sequenzen, Test B: 21 Sequenzen)
- [ ] **Genau eine Auswertung** pro Testset mit `beeflight-evaluate --test`: Balanced Accuracy, Recall und Precision
      Orientierung, Konfusionsmatrix, Intervalle nach [methode.md](methode.md#6-metriken)
      (Test B Cluster-Bootstrap, Test A Wilson und Weglassen je einer Sequenz)
- [ ] **Indikator**: vorhergesagter gegen wahren Anteil auf der gelabelten Stichprobe, Verlauf über die 37 min aus den
      Vorhersagen (beschreibend)
- [ ] **Domain Shift / Monitoring** (Kursteil VIII): Verteilung der Bahnmerkmale A gegen B vergleichen
      (Geschwindigkeit, Länge, Fragmentanteil). Lässt sich der Leistungsabfall *ohne Labels* vorab erkennen?

## Phase 6: Präsentation (Woche 4)

- [ ] Folie 3 mit echten Zahlen füllen: Test A, Test B, Domain Shift, Baseline-Vergleich
- [ ] Neue Abbildungen: Konfusionsmatrix, Indikator über die Zeit
- [ ] Kurzer Clip: ein Orientierungsflug und ein Sammelabflug nebeneinander, langsam (als Einstieg oder für Fragen)
- [ ] `beeflight-run` als Ein-Befehl-Demo
- [ ] PDF exportieren, auf einem fremden Rechner testen
- [ ] Zweimal laut proben mit Uhr (15 min), Fragen vorbereiten:
  - Woher weißt du, dass es junge Bienen sind? *(gar nicht direkt; Verhalten, nicht Alter)*
  - Warum nicht einfach Krümmung? *(Baseline-Vergleich, Grenzfälle suchender Anflug)*
  - Wie verlässlich sind deine Labels? *(Mehrheit aus drei Stimmen, Krippendorffs α)*
  - Warum ist Test B so klein? *(Wetter, Verkehr; KI zeigt die Unsicherheit)*

## Was gestrichen wird, wenn die Zeit knapp wird

In dieser Reihenfolge:

1. Bewegungskanal im Detektor
2. Detektor komplett (Gate 1), dann bleibt das Hintergrundmodell

**Nie gestrichen:** sauberer Split, einmalige Testauswertung, Konfidenzintervalle, Baseline-Vergleich.
