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

**Nächster Schritt:** Detektor (z. B. YOLO, kleine Variante) auf Bienen in der Flugzone trainieren. Labels dafür
liefern die Vorstudien-Bahnen selbst (Bounding Boxes um sichere Detektionen auf vollständigen Bahnen), ergänzt
um von Hand korrigierte Frames.

## 2. Tracking (`beeflight.tracks.track`)

- Zuordnung per **Hungarian-Algorithmus** (`scipy.optimize.linear_sum_assignment`) zwischen vorhergesagten
  Positionen und Detektionen.
- **Konstantgeschwindigkeits-Modell**, geglättet: `v ← 0,5·v + 0,5·Δx/Δt`.
- Gate 45 px (halbe Auflösung), Lücken bis **3 Frames** werden überbrückt.
- **Verbinden von Fragmenten** (`beeflight.tracks.stitch`): Eine Bahn, die im Gras endet, wird mit einer Bahn
  verbunden, die bis zu 40 Frames später im Gras beginnt, wenn Anfang und Ende zur Vorhersage mit konstanter
  Geschwindigkeit passen (Toleranz 12 px + 2 px pro Frame Lücke, in beide Richtungen geprüft). Gierig nach
  Abweichung, jede Bahn höchstens einmal fortgesetzt; Bahnen am Brett oder Bildrand nie.
- Bahnen mit < 15 Detektionen werden danach verworfen (vorher, damit auch kurze Stücke verbunden werden).
- Version `background-v2` (steht in jeder Ausgabe und jedem Label); `background-v1` war der Stand der Vorstudie.

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
[labeling.md](labeling.md). Jede Bahn bekommt **drei Stimmen**: meine und die von zwei Helfenden aus einer
Online-Version des Label-Tools, nach einer Übungsrunde mit Rückmeldung. Das finale Label ist die Mehrheit; ohne
Mehrheit entscheidet mein Label, markiert als `strittig`. Die Übereinstimmung zwischen den Labelnden
(Krippendorffs α) quantifiziert, wie eindeutig die Klassen überhaupt sind, und begrenzt damit die erreichbare
Modellgüte. Optional werden 50 Bahnen nach einer Woche von mir ein zweites Mal gelabelt (Cohen's κ).

Zusätzlich 60–100 Bahnen aus der Validierung für die Modellauswahl. Testbahnen werden erst gelabelt,
wenn das Modell eingefroren ist.

## 5. Modelle

| Modell | Eingabe | Zweck |
|---|---|---|
| **Regel-Baseline** | Geradheit, Dauer, Startzone | untere Schranke, das „10-Minuten-Modell“ |
| **Merkmals-Modell** | Merkmalsvektor (Tabelle oben) → Gradient Boosting / logistische Regression | zeigt, wie weit Handmerkmale tragen |
| **GRU** | Sequenz `(x, y, Δx, Δy, |v|, Δθ)` relativ zum Flugloch, normiert auf die Brettbreite | eigentliches Modell |
| **GRU nur Form** | wie oben, aber ohne absolute Position (nur Δx, Δy, \|v\|, Δθ) | Ablation zu H2 |

**Training:** Vortraining auf allen Bahnen mit Selbst-Labels (Abflug / Anflug / Kurzflug), dann Feintuning auf
den Handlabels. Lernkurve über 25 / 50 / 100 / 200 / 300 Handlabels (Forschungsfrage 3).

**Augmentierung:** horizontale Spiegelung, kleine Rotation und Skalierung, zufälliges Abschneiden von Anfang und
Ende (simuliert Fragmente).

## 6. Metriken

- **Macro-F1** über die vier Klassen (Klassen sind unbalanciert: Orientierungsflüge sind selten).
- **Recall Orientierungsflug** separat, denn das ist die Klasse, die der Indikator braucht.
- **Konfusionsmatrix**, besonders Orientierung vs. suchender Anflug.
- **Indikator:** geschätzter Anteil Orientierungsflüge pro Sequenz, Fehler gegen den von Hand gezählten Anteil.
- **Tracking-Qualität:** Anteil vollständiger Bahnen (Start und Ende in `board` oder `edge`) vor und nach dem
  gelernten Detektor.

Alle Kennzahlen mit 95-%-Konfidenzintervall per **Cluster-Bootstrap über Sequenzen** (Bahnen derselben
Sequenz sind nicht unabhängig).

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
