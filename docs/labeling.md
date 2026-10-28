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

1. Bahnen aus `outputs/flights/*.json` stratifiziert ziehen: über Sequenzen verteilt, alle Selbst-Labels vertreten,
   kurvige Abflüge überrepräsentiert.
2. Reihenfolge mischen, ohne Selbst-Label anzeigen (sonst Anker-Effekt).
3. 50 Bahnen nach ≥ 1 Woche ein zweites Mal labeln, Cohen's κ berichten.
4. Labels als CSV `seq,t0,label,flags` neben den Bahnen ablegen; Test-Bahnen erst nach dem Einfrieren des Modells.
