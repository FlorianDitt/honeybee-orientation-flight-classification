# Roadmap zum Endprodukt

Stand 28.10.2026. Präsentationstermine im Kurs: 25.11. oder 01.12. Der Plan rechnet mit dem **25.11.**;
beim 01.12. wird Woche 5 zum Puffer.

## Endprodukt

Am Ende stehen drei Dinge:

1. **Ein lauffähiges System**: Video rein, pro Sequenz die klassifizierten Flugbahnen und der Anteil
   Orientierungsflüge raus (`beeflight-run <seq>`), reproduzierbar aus diesem Repository.
2. **Eine ehrliche Auswertung**: Macro-F1 und Recall „Orientierung“ auf Test A und Test B mit
   Konfidenzintervallen, Vergleich gegen die Regel-Baseline, Lernkurve, Domain-Shift-Analyse.
3. **Die Präsentation**: drei Folien, 15 min plus Fragen, mit echten Zahlen statt Platzhaltern.

```
 Woche 1          Woche 2           Woche 3            Woche 4            Termin
 28.10.–03.11.    04.11.–10.11.     11.11.–17.11.      18.11.–24.11.      25.11.
 ─────────────────────────────────────────────────────────────────────────────────
 Bahnen für alle  Detektor          Modelle            Test einmal        Vortrag
 Label-Tool       Labels 300+80     Lernkurve          Folien, Proben
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

71 % der Bahnen reißen über dem Gras ab. Ein gelernter Detektor soll das senken.

- [ ] **Bootstrap-Labels**: Bounding Boxes aus vollständigen Bahnen der Vorstudie (sichere Detektionen) als
      Trainingsdaten, ein paar hundert Frames von Hand korrigiert
- [ ] Kleiner Detektor (YOLO, Nano-Variante) auf Ausschnitten der Flugzone trainieren, Bewegungskanal
      (Differenzbild) als Zusatzinput testen, weil getarnte Bienen vor allem durch Bewegung auffallen
- [ ] Detektor als Backend in `tracks.py` einhängen (`--detector yolo|background`)
- [ ] Messen auf Validierung: Anteil vollständiger Bahnen vorher und nachher

> **Gate 1 (Ende Woche 2):** Steigt der Anteil vollständiger Bahnen nicht deutlich (Ziel: von 29 % auf > 50 %),
> bleibt das Hintergrundmodell. Fragmente werden dann als eigene Auswertung berichtet, und die Präsentation
> erzählt den Detektor als ehrlichen Negativbefund. Nicht länger als eine Woche investieren.

## Phase 3: Labels (Woche 2)

- [x] **Online-Labeler** für Freunde (GitHub Pages, Übungsrunde, Pakete, Export) und `beeflight-vote`
- [ ] **300 Trainingsbahnen** und **80 Validierungsbahnen** gelabelt (≈ 3–4 h, auf mehrere Tage verteilt)
- [ ] 8 Pakete an Helfende verteilen (je zwei pro Paket), Exporte nach `labels/votes/`, `beeflight-vote`
- [ ] Mindestens **40 Orientierungsflüge** im Training, sonst gezielt kurvige Abflüge nachziehen
- [ ] Übereinstimmung berichten: Krippendorffs α über alle Labelnden (Zweitlabeln für Cohen's κ nur noch optional)

## Phase 4: Modelle (Woche 3)

- [ ] **Datensatz-Modul**: Bahn → Tensor `(x, y, Δx, Δy, |v|, Δθ)`, normiert auf die Brettbreite,
      Augmentierung (Spiegeln, Rotation, Abschneiden)
- [ ] **Regel-Baseline** (Geradheit, Dauer, Startzone): Schwellen nur auf Validierung wählen
- [ ] **Merkmals-Modell** (Gradient Boosting auf den Bahnmerkmalen)
- [ ] **GRU**: Vortraining auf Selbst-Labels aller Bahnen, Feintuning auf Handlabels
- [ ] **Ablation GRU nur Form** (ohne Position, Hypothese H2)
- [ ] **Lernkurve**: 25 / 50 / 100 / 200 / 300 Handlabels, je 5 Seeds
- [ ] Experimente als JSON in `outputs/runs/` (Konfiguration, Seed, Git-Hash, Metriken), damit jede Zahl auf den
      Folien reproduzierbar ist
- [ ] Zweitlabeln der 50 Bahnen, κ berechnen

> **Gate 2 (Ende Woche 3):** Schlägt die GRU die Baseline auf Validierung nicht, wird trotzdem eingefroren. Dann
> lautet das Ergebnis: Handmerkmale reichen, und die Diskussion erklärt, warum.

## Phase 5: Einfrieren und Test (Anfang Woche 4)

- [ ] **Freeze**: bestes Modell, alle Schwellen und Zonen festschreiben, Commit taggen (`v1.0-freeze`)
- [ ] Testsets herunterladen (`beeflight-splits --download test_same_hive`, `… test_other_hive`)
- [ ] Zonen für Stock B aus einem einzelnen Frame setzen, nicht anhand von Ergebnissen
- [ ] Testbahnen erzeugen und **erst jetzt** labeln (Test A: 4 Sequenzen, Test B: 21 Sequenzen)
- [ ] **Genau eine Auswertung** pro Testset: Macro-F1, Recall Orientierung, Konfusionsmatrix,
      95-%-KI per Cluster-Bootstrap über Sequenzen
- [ ] **Indikator**: Anteil Orientierungsflüge pro Sequenz über die 37 min, Modell gegen Handzählung
- [ ] **Domain Shift / Monitoring** (Kursteil VIII): Verteilung der Bahnmerkmale A gegen B vergleichen
      (Geschwindigkeit, Länge, Fragmentanteil). Lässt sich der Leistungsabfall *ohne Labels* vorab erkennen?

## Phase 6: Präsentation (Woche 4)

- [ ] Folie 3 mit echten Zahlen füllen: Test A, Test B, Domain Shift, Baseline-Vergleich
- [ ] Neue Abbildungen: Konfusionsmatrix, Lernkurve, Indikator über die Zeit
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
2. Merkmals-Modell (Baseline und GRU reichen)
3. Ablation „nur Form“
4. Lernkurve mit 5 Seeds → 1 Seed
5. Detektor komplett (Gate 1), dann bleibt das Hintergrundmodell

**Nie gestrichen:** sauberer Split, einmalige Testauswertung, Konfidenzintervalle, Baseline-Vergleich.
