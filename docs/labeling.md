# Label-Leitfaden

Gelabelt wird **eine ganze Flugbahn**, nicht ein einzelner Frame. Grundlage ist das Video in Originalgeschwindigkeit
und verlangsamt (0,25×), mit eingezeichneter Bahn. Im Zweifel die Bahn als `unsicher` markieren statt zu raten.

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

Zusatzflag `fragment`: Bahn ist echt, aber Anfang oder Ende fehlen. Die Klasse wird trotzdem vergeben, wenn sie
erkennbar ist.

## Grenzfälle

| Situation | Entscheidung |
|---|---|
| Biene startet, fliegt eine Schleife, landet wieder | `orientierung` |
| Biene kommt von außen, kreist vor dem Flugloch, landet | `anflug` |
| Biene kommt von außen, kreist, fliegt wieder weg | `orientierung`, Flag `unsicher` |
| Gerader Abflug mit einem einzelnen Bogen am Bildrand | `sammelabflug` |
| Wespe | `artefakt` (Wespen-Erkennung ist ein anderes Thema) |

## Ablauf

1. **Stichprobe ziehen** mit `uv run beeflight-sample --split train --n 300` (und `--split val --n 80`):
   stratifiziert nach Selbst-Label, kurvige Abflüge überrepräsentiert (30 %), Reihenfolge gemischt.
   Das Selbst-Label wird beim Labeln nicht angezeigt (sonst Anker-Effekt).
2. **Labeln** in der Web-App ([labeler/README.md](../labeler/README.md)): `cd labeler && npm run dev`,
   dann http://127.0.0.1:4321. Etwa 10–15 s pro Bahn, also ~1 h für 300 Bahnen; besser in Blöcken von 50.
3. **Zweitlabeln** nach ≥ 1 Woche: `uv run beeflight-sample --recheck 50`, in der App „Zweitlabeln (blind)“.
   Daraus Cohen's κ berichten.
4. Labels liegen in `labels/<split>.jsonl`, je Zeile Klasse, Flags, Notiz und die komplette Bahn.
   Test-Bahnen erst nach dem Einfrieren des Modells labeln.
