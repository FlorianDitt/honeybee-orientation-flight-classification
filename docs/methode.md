# Methode

```
Video ─► Vordergrund ─► Detektionen ─► Tracking ─► Flugbahnen ─► Merkmale + Selbst-Labels ─┐
                                                                                           ├─► Klassifikator ─► Anteil Orientierungsflüge / Zeit
                                                         Handlabels (~300 Bahnen) ────────┘
```

## 1. Vordergrund und Detektion (`beeflight.tracks.detect`)

Stand der Vorstudie: klassisches Hintergrundmodell, später durch einen gelernten Detektor ersetzt.

| Schritt | Umsetzung | Parameter |
|---|---|---|
| Auflösung | Graustufen, halbe Auflösung (540 × 960) | `SCALE = 0.5` |
| Bildausschnitt | ab Oberkante Flugbrett abwärts | `BOARD = {"2123": (820, 1000), "2125": (770, 1040)}` (volle Auflösung) |
| Hintergrund | Median über jeden 15. Frame der Sequenz | |
| Vordergrund | Abweichung vom Hintergrund > Schwelle, Opening 2×2, Closing 5×5 | `thr = 18` (Vorstudie: 22) |
| Blobs | Zusammenhangskomponenten | Fläche 25–3000 px (halbe Auflösung) |
| Gras-Maske | Pixel, die in > 8 % aller Frames Vordergrund sind, um 7 × 7 dilatiert; Blobs darin werden verworfen | |

Die Gras-Maske ist der wichtigste Trick: Eine vorbeifliegende Biene ist an einer Stelle nur wenige Frames
Vordergrund, wehendes Gras und das dicht besetzte Flugbrett fast immer.

**Später geprüft:** Ein YOLO-Detektor mit ByteTrack + HyDaT blieb weit unter dem Hintergrundmodell und wurde als
Tracker nicht weiterverfolgt ([roadmap.md](roadmap.md#zwei-paper-plan-bytetrack--hydat), Gate 1). YOLO kommt im
finalen System nur als Vorfilter gegen Artefakte vor.

## 2. Tracking (`beeflight.tracks.track`)

- Zuordnung per **Hungarian-Algorithmus** (`scipy.optimize.linear_sum_assignment`) zwischen vorhergesagten
  Positionen und Detektionen.
- Blobs näher als 10 px werden vorher zusammengefasst (Körper und Flügel/Schatten einer Biene).
- **Konstantgeschwindigkeits-Modell**, geglättet: `v ← 0,5·v + 0,5·Δx/Δt`. Kosten = kleinerer Abstand zur
  Vorhersage oder zur letzten Position (+5 px), damit enge Kurven nicht abreißen.
- Gate 45 px (halbe Auflösung), Lücken bis **5 Frames** werden überbrückt. Keine neue Bahn innerhalb von 20 px
  einer gerade zugeordneten Detektion (sonst stiehlt ein zweiter Blob derselben Biene die Bahn).
- **Verbinden von Fragmenten** (`beeflight.tracks.stitch`): Eine Bahn, die im Gras endet, wird mit einer Bahn
  verbunden, die bis zu 40 Frames später (oder bis zu 3 Frames früher) im Gras beginnt, wenn Anfang und Ende zur Vorhersage mit konstanter
  Geschwindigkeit passen (Toleranz 12 px + 2 px pro Frame Lücke, in beide Richtungen geprüft). Gierig nach
  Abweichung, jede Bahn höchstens einmal fortgesetzt; Bahnen am Brett oder Bildrand nie.
- Bahnen mit < 15 Detektionen werden danach verworfen (vorher, damit auch kurze Stücke verbunden werden).
- Version `background-v3` (steht in jeder Ausgabe und jedem Label); `background-v1` war der Stand der Vorstudie,
  Verlauf in [vorstudie.md](vorstudie.md#nachtrag-tracker-v2-und-v3).

## 3. Flugbahnen, Merkmale und Selbst-Labels (`beeflight.tracks.features`)

**Flugfilter:** ≥ 60 % der Punkte unterhalb des Flugbretts, Pfadlänge ≥ 60 px, Median-Schritt ≥ 1 px/Frame.

**Zonen** für Start- und Endpunkt:

| Zone | Bedingung |
|---|---|
| `board` | Punkt höchstens 30 px (halbe Auflösung, ≈ 2 Bienenlängen) unterhalb der Brett-Unterkante |
| `edge` | Punkt höchstens 30 px vom linken, rechten oder unteren Bildrand |
| `lost` | sonst: Bahn reißt mitten im Bild ab (Fragment) |

**Merkmale pro Bahn:**

| Merkmal | Bedeutung |
|---|---|
| `dur_s`, `n` | Dauer, Anzahl Detektionen |
| `path`, `net` | Pfadlänge, Luftlinie Start–Ende |
| `straight` | Geradheit = `net / path` (1 = Gerade, ≈ 0 = Kreis) |
| `turn_deg` | Netto-Windung: Richtungsänderung über die ganze Bahn, aus 3-Frame-Sehnen geglättet; \|turn\| ≥ 360° = volle Schleife |
| `abs_turn_deg` | Summe aller Richtungsänderungen (empfindlich für Zittern, nur als Zusatzmerkmal) |
| `speed` | Median-Geschwindigkeit in px/Frame |
| `start`, `end` | Zone von Start und Ende |

**Selbst-Labels** aus Start und Ziel:

| Start → Ende | Selbst-Label |
|---|---|
| `board` → `edge` / `lost` | Abflug |
| `edge` / `lost` → `board` | Anflug |
| `board` → `board` | Kurzflug / Schweben vor dem Flugloch |
| sonst | Durchflug oder Fragment |

Ein Abflug mit `straight < 0,5` und `dur_s > 0,4` gilt in der Vorstudie als **kurviger Abflug**, also als
Orientierungsflug-Kandidat. Diese Regel ist zugleich die **Baseline**, gegen die das gelernte Modell antritt.

## 4. Handlabels

Etwa 300 Bahnen aus dem Trainingsblock, stratifiziert über Zeit und Selbst-Label, in vier Klassen nach
[labeling.md](labeling.md). Zusätzlich 104 Bahnen aus der Validierung für die Modellauswahl. Train und Validierung
labele ich allein. **Drei Stimmen pro Bahn** (meine und die von zwei Helfenden aus der Online-Version) gibt es seit
dem 05.11.2026 nur noch für die Testsets: Das finale Label ist die Mehrheit, ohne Mehrheit entscheidet mein Label,
markiert als `strittig`. Krippendorffs α über die Labelnden zeigt, wie eindeutig die Klassen sind, und begrenzt
damit die erreichbare Modellgüte. Testbahnen werte ich erst aus, wenn das Modell eingefroren ist.

Weil Train und Validierung nur eine Person labelt, wird meine eigene Konsistenz blind nachgemessen: je 50 Bahnen
aus Train und Validierung ein zweites Mal, Ablauf und vorab festgelegte Auswertung in
[labeling.md](labeling.md#zweitlabeln-recheck). Anlass ist die Fehleranalyse in
[Abschnitt 7](#7-fehleranalyse-und-labelqualität).

## 5. Modelle

Die Modellwahl stützt sich nur auf drei Paper; alles andere ist unten als eigene Entscheidung markiert. Vollständige
Zitationen, Status der Volltextprüfung und wörtlich bestätigte Stellen: [literatur.md](literatur.md). Alle Kandidaten
trainieren nur auf `labels/train.jsonl` und schreiben Vorhersagen für `beeflight-evaluate`.

| Kandidat | Eingabe | Quelle | Befehl |
|---|---|---|---|
| **Regel-Baseline** | Geradheit, Dauer, Start- und Zielzone | Vergleichswert, Schwellen auf Train | `beeflight-baselines` |
| **1. Nur Bahn: ResNet** | Sequenz `(x, y, Δx, Δy, |v|, Δθ)` relativ zum Flugloch, normiert auf die Brettbreite | Fawaz et al. 2019 | `beeflight-resnet` |
| **2. Nur Bild: DINOv2** | 8 gleichmäßig verteilte Ausschnitte um die Biene, eingefrorenes ViT-S/14, linearer Klassifikator | Oquab et al. 2024 | `beeflight-dinov2` |
| **3. Fusion einfach** | Merkmale aus 1 und 2 verkettet, zwei FC-Schichten | Wang et al. 2020 | `beeflight-fusion --mode concat` |
| **4. Fusion G-Blend** | wie 3, mit Offline Gradient-Blending | Wang et al. 2020 | `beeflight-fusion --mode gblend` |

**ResNet:** drei Blöcke mit je drei Faltungen (Längen 8, 5, 3; 64 Filter), Batch-Normalisierung vor ReLU, Global Average
Pooling. Adam mit Lernrate 0,001, Batch 16, 1500 Epochen; Lernrate halbiert nach 50 Epochen ohne besseren Trainingsverlust;
Checkpoint nach Trainingsverlust. Jede Bahn wird auf die längste Trainingsbahn interpoliert.

**Was Fawaz et al. 2019 belegt und was nicht:** Das ResNet ist dort die stärkste von neun Deep-Learning-Architekturen
auf dem UCR-Archiv. Gegen HIVE-COTE und COTE findet der Test keinen signifikanten Unterschied, HIVE-COTE bleibt am
genauesten. Auf den 12 multivariaten Datensätzen, die unseren x/y-Bahnen am nächsten kommen, findet er keinen
signifikanten Unterschied zwischen den neun Modellen (§5.1–5.3). Das ResNet ist damit eine begründete Wahl unter den
DL-Modellen, kein belegter Sieger. Deshalb tritt es gegen die Regel-Baseline an.

**DINOv2** (Oquab et al. 2024) begründet eingefrorene Merkmale mit linearer Probe. Zu Objekten von etwa 30 px sagt das
Paper nichts; ob die Merkmale unsere unscharfen Bienen tragen, ist eine offene empirische Frage.

**Fusion** (Wang et al. 2020): Die Befunde stammen aus End-to-End-Training auf großen Videodatensätzen. Ansätze mit
getrennt vortrainierten Zweigen nennen die Autoren „not comparable“; unser eingefrorener Bildzweig fällt darunter.

**DINOv2:** Rastersuche nach Anhang B.3 (13 Lernraten, 1 oder 4 Ausgabeschichten, Klassen-Token allein oder mit gemittelten
Patch-Token), dazu Mitteln oder Verketten der Frames. SGD über 12500 Iterationen. Die Gewichte stammen nicht von Stockvideos.

**G-Blend:** Gewichte `w_i = G_i / O_i² / Z` einmal berechnet, mit Genauigkeit statt Verlust gemessen (laut Paper gleich
wirksam), auf einem Hold-out aus den Trainingslabels. Ergebnis: Bahn 0,05, Bild 0,33, Fusion 0,62.

**Eigene Entscheidungen, nicht aus den Papern:**

- Kanäle der Bahn (aus dem Projekt, nicht von Fawaz) und ihre Standardisierung.
- Ausschnittgröße 64, 128 oder 224 px (auf Val gewählt: 224 px); kein Paper behandelt 30-px-Objekte.
- Full-Batch-SGD (B.3 nennt keine Batchgröße), keine Bild-Augmentierung, ViT-S wegen CPU.
- Fusion: Bildzweig bleibt eingefroren (Wang trainiert alle Zweige), Abbildung auf 64 Dimensionen, Optimierer des ResNet.
- G-Blend: Hold-out aus ganzen Sequenzen (20 %), `T'` so groß wie `V`, Endmodell auf allen Trainingslabels, Vorhersage aus
  dem Fusionskopf, `G ≤ 0` ergibt Gewicht 0, `O` nach unten begrenzt.

**Nicht mehr im Modell:** GRU, Vortraining auf Selbst-Labels, Lernkurve und Augmentierung der Bahnen. Selbst-Labels dienen nur
noch der Stichprobenziehung. Die Bahn-Interpolation verbirgt die Dauer einer Bahn; das ist eine bekannte Schwäche.
Wird Vortraining in der Arbeit als Ausblick genannt: **nicht mit Halilovic 2019 begründen** (dort lernte das
Vorhersagemodell auf echten Bienendaten nichts Brauchbares) und BEAST (Wang, Yu et al. 2026) nur als Ausblick mit
dessen Einschränkungen zitieren, siehe [literatur.md](literatur.md#modelle).

**Auswahl auf Validierung (104 Bahnen, 14 Sequenzen, je 5 Seeds, Stand 06.11.2026):**

| Modell | Balanced Acc. | Intervall | Recall Orient. | Precision Orient. | Anteilsfehler (PP) |
|---|---|---|---|---|---|
| **ResNet (gewählt)** | **0,708** | 0,66–0,76 | 0,648 | 0,506 | +1,7 |
| DINOv2 | 0,647 | 0,54–0,74 | 0,562 | 0,514 | 0,0 |
| Regel | 0,640 | 0,54–0,72 | 0,667 | 0,452 | +10,1 |
| Fusion G-Blend | 0,629 | 0,53–0,71 | 0,467 | 0,458 | −4,1 |
| Fusion einfach | 0,615 | 0,51–0,70 | 0,429 | 0,448 | −6,2 |

Gewählt wird nach höchster Balanced Accuracy; eine Fusion nur, wenn sie den besten Einzelzweig schlägt. Das ResNet ist damit
**nicht klar** besser: Gegen die Regel beträgt die Differenz +0,068 (−0,04 bis +0,19), und auf den 83 vollständigen Bahnen
liegen beide gleichauf (0,705 gegen 0,717). Der Vorsprung kommt aus nur 21 Fragmenten. DINOv2 ist durch die Auswahl aus 312
Einstellungen auf Val zusätzlich begünstigt. Auf dem Hold-out der Gewichtsschätzung (64 Bahnen, ein Seed, Genauigkeit) lag die
Rangfolge umgekehrt (Bahn 0,58, Bild 0,70, Fusion 0,73), die Reihenfolge der Kandidaten ist also nicht stabil belegt.

> Die späteren Läufe auf der GPU (ab 07.11.2026) und das eingefrorene Modell (Ensemble aus 5 ResNets mit
> YOLO26s-Vorfilter) stehen nicht hier, sondern in der [README](../README.md) und auf der Ergebnis-Website.

## 6. Metriken

Festgelegt am 05.11.2026, vor jedem Blick auf Testergebnisse; Validierungsergebnisse mit Macro-F1 kannte ich da
schon. Umgesetzt in `beeflight.metrics` und `beeflight-evaluate`. Grundlagen: Opitz (2024) für Definitionen und
Eigenschaften der Metriken, Metrics Reloaded (Maier-Hein et al. 2024) für Empfehlungen. Metrics Reloaded ist für
Bildanalyse geschrieben; die Übertragung auf Bahnen ist meine Entscheidung. Alles ohne Quelle ist eigene Festlegung.

| Kennzahl | Rolle |
|---|---|
| **Balanced Accuracy** = Macro-Recall, `BA = 1/K · Σ_k TP_k / (TP_k + FN_k)` (Opitz Eq. 7; Zufall = 1/4) | Hauptmetrik, auch für die Modellauswahl auf Validierung |
| **Recall und Precision `orientierung`**, immer mit Zählwerten wie `3/4` | Schlüsselklasse. Beide nötig: Der Indikator hängt auch an den Falsch-Positiven |
| **Accuracy** | Ergänzung, die Testsets sind Zufallsstichproben |
| **Macro-F1** als „averaged F1“ (Mittel der Klassen-F1, Opitz Eq. 10; Opitz & Burst) | nachrangig, zum Vergleich mit früheren Werten |
| **Recall und Precision aller Klassen, Konfusionsmatrix** | zeigt die schwache Klasse, besonders Orientierung vs. suchender Anflug |
| **AUROC `orientierung` gegen Rest** | nur für Modelle mit Wahrscheinlichkeiten, nicht für die Regel |

Zur Gleichsetzung in der ersten Zeile: Opitz begründet Macro-Recall als Metrik mit allen fünf geprüften Eigenschaften
(§4.2). Dass Balanced Accuracy dasselbe ist, schreibt er nur in Fußnote 11 mit Verweis auf scikit-learn. Darum steht
die Formel oben, und in der Arbeit wird sie mitgenannt.

**Abgleich mit Metrics Reloaded** (Volltext geprüft 07.11.2026, [literatur.md](literatur.md#auswertung-und-metriken)):

- Balanced Accuracy passt: Die Empfehlung EC gilt für ungleiche Fehlerkosten; bei gleichen Kosten nennen die Autoren
  BA (oder MCC), ausdrücklich wenn die Klassenanteile nicht der Zielpopulation entsprechen.
- Multi-Threshold-Metriken (Default AUROC, pro Klasse) sind dort **„always recommended“**. Der frühere Plan, AUROC
  als Erstes zu streichen, wäre eine Abweichung von der Empfehlung und müsste in der Arbeit genannt werden.
- Zählmetriken pro Klasse sind dort **optional**, die volle Konfusionsmatrix wird bei wenigen Klassen empfohlen. Dass
  wir die Klassen-Recalls trotzdem immer berichten, folgt Opitz §8 („If the amount of classes n is low, consider
  presenting class-wise recall scores …“).
- Bei kleinem Testset: Konfidenzintervalle für alle Metriken (Table 1). Welche Methode, schreibt Metrics Reloaded nicht
  vor; Cluster-Bootstrap und Wilson unten sind unsere Wahl.

**Warum nicht mehr Macro-F1:** Balanced Accuracy hängt bei gleichen Fehlerraten innerhalb der Klassen nicht von den
Klassenanteilen ab; Train und Validierung sind geschichtet, die Testsets reine Zufallsstichproben, und der Anteil der
Orientierungsflüge ist genau die Größe, die variieren soll. Das schützt nicht vor anderen Verschiebungen, etwa
kurvigen Abflügen im Training oder dem Wechsel zu Stock B.

**Seltene Klassen:** Eine Klasse ohne Beispiele fällt aus Balanced Accuracy und Macro-F1 heraus und wird markiert
(Zufall dann 1/k), sie zählt nie als Recall 0. Bei weniger als 5 Beispielen bleibt der Wert drin, wird aber als „zu
wenige Beispiele“ markiert. Dieselbe Regel gilt in jeder Bootstrap-Stichprobe, ihr Anteil mit fehlender Klasse wird
berichtet. `orientierung` kann in den Testsets selten sein; die Intervalle werden dann breit.

**Unsicherheit:** 95-%-Cluster-Bootstrap über Sequenzen (Perzentile, 2000 Wiederholungen) ab 10 Sequenzen, also für
Validierung und Test B, weil Bahnen einer Sequenz nicht unabhängig sind. Test A hat nur 4 Sequenzen und damit nur 35
verschiedene Stichproben: dort Wilson-Intervalle auf Klassenwerte (ignorieren die Abhängigkeit, also zu eng) und die
Spanne beim Weglassen je einer Sequenz.

**Seeds und Modellvergleich:** Alle Seeds werden ausgewertet, Mittel und Standardabweichung, keine Auswahl des besten
Seeds. Intervalle nutzen das Seed-Mittel pro Stichprobe. Vergleiche sind Differenzen auf denselben gezogenen Bahnen.
Das folgt Bouthillier et al. 2021: möglichst viele Zufallsquellen variieren, die Datenauswahl trägt mehr Varianz als
die Initialisierung (§2.2). Die Paarung empfehlen sie nur im Anhang (C.2, „optional but highly recommended“); ihr
Entscheidungskriterium P(A > B) nutzen wir nicht. Venue vor dem Zitieren prüfen ([literatur.md](literatur.md)).
Hauptvergleich ist das ausgewählte Modell gegen die auf Train abgestimmte Regel, die feste Regel der Vorstudie steht
daneben. Alles ist beschreibend, ohne p-Werte oder Signifikanzaussagen, daher ohne Korrektur für Mehrfachvergleiche.
Die Vergleichswerte (beide Regeln, Zufall gleichverteilt und nach Trainingshäufigkeit, immer dieselbe Klasse) schreibt
`beeflight-baselines --split <split>` nach `outputs/baselines/<split>/`; es liest als Labels nur `labels/train.jsonl`.

**Indikator:** Anteil = `orientierung` / alle Bahnen außer `artefakt`, getrennt aus Labels und aus Vorhersagen.
Berichtet werden wahrer Anteil, vorhergesagter Anteil und der vorzeichenbehaftete Fehler in Prozentpunkten pro Testset.
Fehler pro Sequenz nur, wenn jede Sequenz mindestens 10 gelabelte Bahnen hat (Test A; in Test B sind es 1–12). Referenz
ist die gelabelte Zufallsstichprobe, es gibt keine separate Handzählung. Die Zählwerte werden nicht korrigiert, dafür
reicht die Falsch-Positiv-Rate aus 104 Validierungsbahnen einer Person nicht. Der Verlauf über die Aufnahme kommt aus
den Vorhersagen auf allen Bahnen und ist rein beschreibend.

**Label-Varianten im Test:** Mehrheit ist primär; gegen meine Labels und nur auf einstimmigen Bahnen sind
Gegenproben, einstimmige Bahnen sind dabei die leichtere Teilmenge. Validierung (nur ich) und Test (Mehrheit) sind
deshalb nicht sauber vergleichbar; der Vergleich für den Domain Shift ist A gegen B.

**Fragmente (H3):** vollständig gegen Fragment nach den Zonen (`lost` an Start oder Ende), nicht nach den Flags der
Labelnden; beschreibend.

**Tracking-Qualität:** blinde Handprüfung einer festen Zufallsstichprobe von Val-Bahnen je Tracker
(`labels/tracker_eval.jsonl`): korrekt und ganz, Bruchstück, Bienenwechsel, keine Biene. Der Anteil vollständiger
Bahnen (Start und Ende in `board` oder `edge`) ist keine Qualitätsmetrik: Auch ein Bienenwechsel zählt dort als
vollständig. Er bleibt nur als Beschreibung.

**Grenzen:** Alle Kennzahlen gelten nur für Flüge, die der Tracker gefunden hat. Test B ist ein einzelner anderer
Stock unter anderen Bedingungen, Stock, Wetter und Kamera lassen sich nicht trennen.

## Split und Evaluationsprotokoll

Definiert in `src/beeflight/splits.py`, die einzige Quelle der Wahrheit.

- **Nach Zeitblöcken, nie nach Frames oder Bahnen:** Bei 60 fps sind Nachbarframes fast identisch, und eine
  Biene kann innerhalb von Sekunden mehrmals vor dem Flugloch kreisen. Zufällige Splits würden die Leistung
  überschätzen.
- **Puffersequenzen** 070 und 085 werden verworfen, damit keine Bahn eine Split-Grenze überquert.
- **Test A** (rec2123, Seq. 086–089): gleicher Stock, späterer Zeitpunkt. Misst, wie gut die Methode ist.
- **Test B** (rec2125, alle 21 Sequenzen): anderer Stock, rotes Holz mit Gitter, bedeckt, Kamera näher.
  Misst, wie gut sie übertragbar ist. Die Differenz A → B ist der Domain-Shift-Effekt.
- **Regeln:** Alle Schwellen, Hyperparameter und die Modellauswahl nur auf Validierung. Jedes Testset wird
  genau einmal am Ende ausgewertet.
- **Ausnahme, offen dokumentiert:** In der Vorstudie wurde eine Sequenz von Stock B (rec2125_seq010) nur darauf
  geprüft, ob dort überhaupt Flugverkehr stattfindet. Daraus wurden keine Parameter abgeleitet.

Für Test B müssen die Zonen (`BOARD`) neu gesetzt werden. Sie werden aus einem einzelnen Frame abgelesen, nicht
anhand von Ergebnissen eingestellt.

## 7. Fehleranalyse und Labelqualität

Stand 07.11.2026. Untersucht wurden die Validierungsfehler der **alten, archivierten Modelle** (Lauf
`2026-11-05_0117_full`: GBM, GRU, logistische Regression, GRU ohne Vortraining, je 5 Seeds), die inzwischen durch die
Kandidaten aus [Abschnitt 5](#5-modelle) ersetzt sind. Frage: Liegen die Fehler an inkonsistenten Labels oder an
Information, die in der Bahn fehlt? Testsets wurden nicht geöffnet. Alles ist beschreibend, die Zellen sind klein.

**Befunde:**

| Befund | Zahl |
|---|---|
| Bahnen, die alle 20 Vorhersagen (4 Modelle × 5 Seeds) falsch haben („Dauerfehler“) | 15 von 104 |
| Übereinstimmung mit Labeler 3 auf identischen v3-Bahnen | 101/168 = 0,60, **κ = 0,47** (Bootstrap 0,37–0,56) |
| spezifische Übereinstimmung pro Klasse | anflug 0,83, sammelabflug 0,66, orientierung 0,54, artefakt 0,29 |
| Dauerfehler mit Label von Labeler 3, bei denen Labeler 3 wie das Modell entscheidet | 7 von 9 (erwartet 3,0; p ≈ 0,003) |
| sehr nahe Bahnpaare (21 Handmerkmale, engstes 0,5-%-Quantil) mit verschiedenem Label | 111 von 438 = **25 %**, vor allem ori–sam und art–ori |
| eigene Wiederholungslabels über Tracker-Versionen gleich | 8 von 14 (κ 0,36); 4 der 6 Wechsel gehen von orientierung nach artefakt |
| Artefakte in Train mit Notiz zur Art | 0 von 75 |
| Artefakte in Train mit Flag `unsicher` | 1 von 75 |

- **Unscharfe Klassengrenzen** statt einer schlechten Labelsitzung: Die Fehler hängen nicht am Labeldatum (Dauerfehler
  15 % gegen 14 %, Out-of-fold über Train und Val flach). Sie liegen an drei Stellen, an denen die Bahn wie eine andere
  Klasse aussieht: **kreisende Abflüge** (sammelabflug oder orientierung?), **gerade Rand-zu-Rand-Vorbeiflüge** (in
  Train und Val 8 als sammelabflug, 9 als artefakt gelabelt) und **Brett-zu-Brett-Bahnen** (orientierung, anflug oder
  artefakt; 23 Orientierungen in Train teilen die Signatur der Brett-zu-Brett-Artefakte).
- Labeler 3 vergibt im Zweifel `orientierung` (49 % der eigenen Labels), ich `artefakt` oder `sammelabflug`. Ein Großteil
  der Abweichung ist also **systematisch**, eine Definitionsfrage. Ob sie nach Video oder nach der eingezeichneten
  Bahn entschieden hat, ist nicht bekannt.
- **Bienenwechsel sind teils nur im Video sichtbar.** Die beiden notierten Wechsel haben einen Sprung in der Bahn
  (größter Schritt > 6 × Median), andere hat der Tracker vermutlich glatt verbunden. Was nicht als Sprung auftaucht,
  kann ein Bahnmodell nicht sehen. Wie groß dieser Anteil ist, lässt sich ohne Notizen in Train nicht sagen.
- **Flags werden je Sitzung verschieden benutzt:** `unsicher` in Train 78 von 314, in Val 5 von 104, davon in der
  Val-Sitzung vom 28.10. gar nicht. Weniger Flags in Val heißt also nicht sicherere Labels. Über Train und Val ist
  `unsicher` informativ (höhere Out-of-fold-Fehler bei ori und sam), wird bei `artefakt` aber fast nie gesetzt.

**Einschätzung (Vermutung, nicht belegt):** Der größere Teil der Fehler ist Regelunschärfe bzw. Drift in meiner
Definition, ein kleinerer, unbekannter Teil fehlende Information in der Bahn (Bienenwechsel, verpasster Start). Beides
hinterlässt in den vorhandenen Daten dieselbe Spur. Trennen lässt es sich nur mit einem blinden Zweitlabel, getrennt
nach „nur Bahn“ und „mit Video“.

**Folgen:**

1. Regeln für die drei Grenzfälle und für Bienenwechsel schriftlich festlegen, **bevor** zweitgelabelt wird, sonst misst
   das Recheck die Drift mit. Entwurf: [labeling.md](labeling.md#labelregeln-für-grenzfälle--entwurf-entscheidung-durch-florian).
2. Blindes Zweitlabeln von je 50 Bahnen aus Train und Val, mit Pflichtnotiz zur Artefakt-Art:
   [labeling.md](labeling.md#zweitlabeln-recheck). Die Val-Queue enthält die 15 Dauerfehler, gemischt unter 35
   Zufallsbahnen. Welche das sind, steht absichtlich in keiner Doku.
3. Die Selbstübereinstimmung ist eine grobe Obergrenze für die erreichbare Accuracy. Liegt sie bei etwa 0,8, sind
   Modelle mit 0,7 bis 0,75 schon nahe an dem, was die Labels hergeben. Bei 50 Bahnen ist κ auf etwa ±0,15 bis ±0,18
   genau (Simulation): κ ≈ 0,5 ist von κ ≈ 0,85 unterscheidbar, 0,7 von 0,8 nicht.

Skripte und Ausgaben der Analyse liegen nicht im Repository (Scratchpad der Sitzung vom 07.11.2026); vor der Abgabe
übernehmen, falls Zahlen daraus in die Arbeit gehen.
