# Label-Leitfaden

Gelabelt wird **eine ganze Flugbahn**, nicht ein einzelner Frame. Grundlage ist das Video in Originalgeschwindigkeit
und verlangsamt (0,25×), mit eingezeichneter Bahn. Im Zweifel die Bahn als `unsicher` markieren statt zu raten.
Biologischer Hintergrund und Abgrenzung der Klassen: [biologie.md](biologie.md).

**Kurvig allein ist kein Orientierungsflug.** Auch suchende Anflüge kurven. Entscheidend ist, wo die Bahn beginnt
und endet (siehe Abgrenzung in [biologie.md](biologie.md#abgrenzung-zu-den-anderen-klassen)). Diese Regel steht seit
dem 02.11.2026 auch prominent auf der Online-Seite, weil Zweitlabelnde kurvige Bahnen sonst fast immer als
`orientierung` einordnen.

## Klassen

### 1. `orientierung`: Orientierungsflug

- Startet auf dem Flugbrett oder schwebt direkt davor.
- Die Biene **dreht sich zum Stock** und fliegt **Bögen, Schleifen oder Zickzack quer zum Flugloch**,
  meist langsam und in der Nähe des Eingangs.
- Die Bögen werden oft größer, bevor die Biene die Flugzone verlässt oder wieder landet.
- Häufig mehrere Bienen gleichzeitig.

### 2. `sammelabflug`: direkter Abflug

- Startet auf dem Flugbrett.
- Verlässt die Flugzone **zügig und ohne Schleife**; eine kurze Kurve direkt nach dem Start ist erlaubt.

### 3. `anflug`: suchender oder direkter Landeanflug

- Kommt von außerhalb und **endet auf dem Flugbrett**, oder ist erkennbar auf dem Weg dorthin.
- Darf kurven, abbremsen und suchen; entscheidend ist das **Ziel Flugloch**.
- Abgebrochene Landungen mit neuem Anflug gehören auch hierher.

### 4. `artefakt`: keine echte Flugbahn

- Gras, Blätter, Schatten, Lichtwechsel.
- Zwei Bienen, die der Tracker zu einer Bahn vertauscht hat (ID-Wechsel), wenn die Bahn dadurch ihren Charakter
  ändert.
- Krabbelnde Bienen am Brettrand.
- **Vorbeiflug** (seit 03.11.2026): eine Biene fliegt durchs Bild, weit weg vom Flugloch und ohne sich ihm
  zuzuwenden, auch wenn sie dabei Schleifen fliegt. Streng genommen eine echte Bahn, aber ohne Bezug zum Stock;
  lokal mit Notiz „Vorbeiflug“, damit sie sich später von Gras und Schatten trennen lässt.

Notizen für Artefakte: „Vorbeiflug“, „Bienenwechsel“ (mit Anzahl, z. B. „2× Bienenwechsel“), „zu kurz“.

Zusatzflag `fragment`: Bahn ist echt, aber Anfang oder Ende fehlen. Die Klasse wird trotzdem vergeben, wenn sie
erkennbar ist.

## Grenzfälle

| Situation | Entscheidung |
|---|---|
| Biene startet, fliegt eine Schleife, landet wieder | `orientierung` |
| Biene kommt von außen, kreist vor dem Flugloch, landet | `anflug` |
| Biene kommt von außen, kreist **vor dem Flugloch** (wendet sich ihm zu), fliegt wieder weg | `orientierung`, Flag `unsicher` |
| Biene fliegt eine Schleife durchs Bild, weit weg vom Flugloch, ohne Bezug zum Stock | `artefakt`, Notiz „Vorbeiflug“ |
| Bahn springt zwischen mehreren Bienen (Bienenwechsel), Flug nicht mehr einer Biene zuzuordnen | `artefakt`, Notiz „Bienenwechsel“ |
| Wechsel nur in den letzten Frames, Rest klar eine Biene | Klasse der Biene, Flag `fragment` |
| Gerader Abflug mit einem einzelnen Bogen am Bildrand | `sammelabflug` |
| Wespe, Hornisse | `artefakt` (Wespen-Erkennung ist ein anderes Thema) |
| Biene pendelt von außen kommend zickzack vor dem Eingang (mögliche Räuberin) | `anflug`, Flag `unsicher` |
| Auffällig große, plumpe Biene (Drohne) | nach Bahnform, Notiz „Drohne“ |

## Ablauf

1. **Stichprobe ziehen** mit `uv run beeflight-sample --split train --n 300 --all` (und `--split val --n 80 --all`):
   stratifiziert nach Selbst-Label, kurvige Abflüge überrepräsentiert (30 %), Reihenfolge gemischt.
   Mit `--all` folgen danach alle übrigen Bahnen des Splits (lokal labelbar, online nur die Stichprobe).
   Das Selbst-Label wird beim Labeln nicht angezeigt (sonst Anker-Effekt).
   Nach einem Tracker-Wechsel überträgt `--carry labels/archive/<version>/train.jsonl` die alten Labels auf
   dieselben Flüge im neuen Tracking; stark gewachsene Bahnen (verbundene Fragmente) werden neu gelabelt.
   `--flights outputs/flights_<tracker>` wählt das Tracking (Standard v3); seit 02.11.2026 wird auf
   Chiron + Huang (`flights_chiron_linked`) gelabelt. Liegt die alte Queue neben den alten Labels, entsteht
   zusätzlich `labels/id_map_<split>.json`, über die `beeflight-vote` die Stimmen der Helfenden mitnimmt.
   Die Label-Ansicht zeigt oben an, mit welchem Tracking die Bahnen entstanden sind.
2. **Labeln** in der Web-App ([labeler/README.md](../labeler/README.md)): `cd labeler && npm run dev`,
   dann http://127.0.0.1:4321. Etwa 10–15 s pro Bahn, also ~1 h für 300 Bahnen; besser in Blöcken von 50.
3. **Zweitlabeln** nach ≥ 1 Woche: `uv run beeflight-sample --recheck 50`, in der App „Zweitlabeln (blind)“.
   Daraus Cohen's κ berichten.
4. Labels liegen in `labels/<split>.jsonl`, je Zeile Klasse, Flags, Notiz und die komplette Bahn.
   Test-Bahnen erst nach dem Einfrieren des Modells selbst labeln und auswerten (siehe unten).

## Mehrere Labelnde

Damit die Labels nicht nur an einer Person hängen, labeln Freundinnen und Freunde dieselben Bahnen in der
Online-Version ([labeler/README.md](../labeler/README.md#online-version-für-freunde-github-pages)). Sie sehen den
Leitfaden in Kurzform und sehen zuerst ein **Tutorial** (seit 03.11.2026): 8 Beispielbahnen aus meinen sicheren
Labels, je zwei pro Klasse, mit kurzer Begründung (`labels/tutorial.json`). Es wird nur gezeigt, nicht geprüft:
Die frühere Übungsrunde verglich die Helfenden mit meiner Meinung, das passt nicht zu unabhängigen Stimmen.

Die Bahnen sind in Pakete zu etwa 50 aufgeteilt (gleiche gemischte Reihenfolge wie die Warteschlange). Jedes Paket
bekommt zwei Helfende, zusammen mit meinen Labels sind das **drei Stimmen pro Bahn**.

**Online gelabelt werden seit dem 05.11.2026 die Testsets** (je 100 Bahnen als reine Zufallsstichprobe, Test A =
Pakete 1–2, Test B = Pakete 3–4): Ihre Labels bestimmen das berichtete Ergebnis, Training und Validierung labele ich
selbst weiter. Die Helfenden sehen nur „Paket 1–4“. Sie können schon vor dem Einfrieren labeln, weil weder ich noch
das Modell ihre Stimmen sehen; `beeflight-vote` wertet Test-Stimmen erst mit `--test` aus, nach dem Einfrieren.
Weil zwei Helfende mich überstimmen können und Zweitlabelnde `orientierung` häufiger vergeben, wird der Test dreifach
berichtet: gegen die Mehrheit, gegen meine Labels und nur auf einstimmigen Bahnen.

`uv run beeflight-vote` führt `labels/<split>.jsonl` (meine Labels) und alle Exporte in `labels/votes/` zusammen:

| Fall | Ergebnis |
|---|---|
| strikte Mehrheit (2 von 3, 3 von 4, …) | Mehrheitsklasse |
| keine Mehrheit, ich habe abgestimmt | meine Klasse, Flag `strittig` |
| keine Mehrheit, ohne mich | offen, wird nicht geschrieben |
| Flag `fragment` / `unsicher` | gesetzt, wenn mindestens die Hälfte es gesetzt hat |

Ergebnis ist `labels/final_<split>.jsonl` (mit Geometrie und allen Einzelstimmen). Berichtet werden
**Krippendorffs α** (nominal, verträgt fehlende Stimmen) als Übereinstimmung zwischen den Labelnden, sowie pro Person
Übungsergebnis und Übereinstimmung mit der Mehrheit. Damit ersetzt α das Zweitlabeln für Cohen's κ; das
Zweitlabeln bleibt optional als Maß für meine eigene Konsistenz.

Trainiert wird auf den Mehrheitslabels; `strittig` und `unsicher` können als Gewicht oder für eine Auswertung
„nur eindeutige Bahnen“ dienen.
