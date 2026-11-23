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

## Labelregeln für Grenzfälle – ENTWURF, Entscheidung durch Florian

> **Nichts in diesem Abschnitt ist beschlossen.** Es sind Vorschläge vom 07.11.2026, abgeleitet aus
> [biologie.md](biologie.md#abgrenzung-zu-den-anderen-klassen), den Klassen oben und der Fehleranalyse
> ([methode.md](methode.md#7-fehleranalyse-und-labelqualität)). Bis zur Entscheidung gelten die Klassen und die
> Grenzfall-Tabelle oben. Offene Fragen sind mit **Offen** markiert.

Anlass: Die Fehleranalyse fand drei Stellen, an denen gleich aussehende Bahnen verschieden gelabelt sind (kreisende
Abflüge, gerade Rand-zu-Rand-Bahnen, Brett-zu-Brett-Bahnen), dazu Bienenwechsel, die teils nur im Video zu sehen sind.
Die Regeln sollen vor dem Zweitlabeln feststehen, sonst misst das Recheck die eigene Drift mit.

Grundsätze, aus denen die Vorschläge abgeleitet sind:

- Laut [biologie.md](biologie.md#abgrenzung-zu-den-anderen-klassen) entscheiden **Start und Ende**, nicht die
  Kurvigkeit. `orientierung` und `sammelabflug` starten am Flugbrett, `anflug` endet dort.
- Die Blickrichtung ist bei etwa 30 px kaum zu sehen ([idee.md](idee.md#risiken)). Die Vorschläge stützen sich
  deshalb auf die **Flugrichtung relativ zum Flugloch**, nicht auf den Blick.
- Was nur im Video zu sehen ist, bekommt eine **Notiz**. So lässt sich später trennen, ob ein Label aus der Bahn
  oder aus dem Video folgt.

### G1: Kreisender Abflug gegen Orientierungsflug

Startet auf dem Brett, verlässt das Bild, ist aber nicht gerade.

| Vorschlag | Label |
|---|---|
| Die Biene fliegt nach dem Start mindestens einmal **wieder auf das Flugloch zu** (der Abstand zum Flugloch nimmt erkennbar wieder ab), bevor sie das Bild verlässt | `orientierung` |
| Die Bahn biegt nur **vom Flugloch weg** ab, auch mehrfach oder in einem großen Bogen, ohne Rückwendung | `sammelabflug` |
| Nur ein Bogen direkt nach dem Start oder am Bildrand (wie bisher) | `sammelabflug` |
| Rückwendung angedeutet, aber nicht klar | Klasse nach Mehrheit der Merkmale, Flag `unsicher` (Pflicht) |

- **Offen:** Ab wann ist „erkennbar wieder näher“? Eine feste Schwelle (z. B. volle Schleife, \|`turn_deg`\| ≥ 360°)
  wäre gut reproduzierbar, koppelt das Label aber an ein Merkmal der Regel-Baseline. Das könnte den Vergleich
  Modell gegen Regel verzerren.
- **Offen:** Eine Biene, die vor dem Flugloch langsam schwebt und dann gerade wegfliegt (ohne Bogen): `orientierung`
  wegen des Schwebens (biologie.md: „schwebt davor“) oder `sammelabflug` wegen der Bahn?

### G2: Gerader Rand-zu-Rand-Vorbeiflug

Kommt vom Bildrand, verlässt das Bild am Rand, fast gerade. In Train und Val bisher etwa hälftig `sammelabflug`
und `artefakt`.

| Vorschlag | Label |
|---|---|
| Kein Start vom Brett zu sehen, weder in der Bahn noch im Video | `artefakt`, Notiz „Vorbeiflug“ |
| Im Video ist klar zu sehen, dass die Biene vom Brett gestartet ist; der Tracker hat den Start verpasst | `sammelabflug`, Flag `fragment`, Notiz „Start nur im Video“ |
| Kommt von außen, wendet sich vor dem Flugloch zu ihm hin, fliegt wieder weg | wie bisher: `orientierung`, Flag `unsicher` |

- Abgeleitet daraus, dass `sammelabflug` laut Klassendefinition am Flugbrett startet. Die bisherige Bedingung
  „weit weg vom Flugloch“ beim Vorbeiflug entfiele: Auch ein Vorbeiflug nah am Flugloch ohne Zuwendung wäre `artefakt`.
- **Offen:** Soll „weit weg vom Flugloch“ als Bedingung bleiben? Wenn ja, was gilt für einen geraden Durchflug nah
  am Flugloch?
- **Offen:** Ein Vorbeiflug ist eine echte Bahn. Als `artefakt` fällt er aus dem Indikator heraus (Anteil =
  `orientierung` / alles außer `artefakt`). Ist das gewollt, oder braucht er später eine eigene Auswertung?

### G3: Brett zu Brett

Bahn beginnt und endet am Brett.

| Vorschlag | Label |
|---|---|
| Biene hebt sichtbar ab, fliegt mindestens einen Bogen unterhalb des Bretts und landet wieder | `orientierung` (wie bisher) |
| Kaum Flug: Hüpfen, Krabbeln oder kurzes Aufflattern am Brettrand, Bahn bleibt in Brettnähe und ist langsam | `artefakt`, Notiz „Krabbeln“ |
| Im Video kommt die Biene von außen; der Tracker hat den Anfang verpasst oder mit einer sitzenden Biene verbunden | `anflug`, Flag `fragment`, Notiz „Start nur im Video“ bzw. G4 |
| Bahn verbindet zwei Bienen (eine startet, eine andere landet) | nach G4 |

- `anflug` von Brett zu Brett nur mit Notiz, weil `anflug` laut Definition von außerhalb kommt. Ohne Notiz wäre das
  Label aus der Bahn nicht nachvollziehbar.
- **Offen:** Mindestgröße eines Bogens für `orientierung` gegen „Aufflattern“ (z. B. in Bienenlängen).
- **Offen:** Biene landet kurz und startet sofort wieder (Touch-and-go): ein Flug oder zwei, und welche Klasse?

### G4: Bienenwechsel

Der Tracker hat zwei oder mehr Bienen zu einer Bahn verbunden.

| Vorschlag | Label |
|---|---|
| Der größte Teil der Bahn (Vorschlag: mindestens etwa 80 % der Dauer) gehört klar zu einer Biene, deren Klasse erkennbar ist | Klasse dieser Biene, Flag `fragment`, Notiz „Bienenwechsel Anfang“ oder „… Ende“ |
| Sonst | `artefakt`, Notiz „Bienenwechsel“ mit Anzahl |
| Wechsel nur im Video zu sehen, in der Bahn kein Sprung | wie oben, zusätzlich Notiz „nur im Video“ |

- Präzisiert die bisherige Regel „Wechsel nur in den letzten Frames“ durch einen Anteil. Die 80 % sind eine eigene
  Festlegung ohne Quelle.
- **Offen:** Sollen `artefakt`-Bahnen mit Bienenwechsel überhaupt ins Training? Die Bahn sieht dann oft wie ein
  echter Flug aus, und das Modell lernt einen Widerspruch. Alternative: im Training weglassen, in der Auswertung
  getrennt zählen.

### Übergreifend

- **Pflichtnotiz bei jedem `artefakt`** mit der Art: „Vorbeiflug“, „Bienenwechsel“, „zu kurz“, „Krabbeln“,
  „Gras/Schatten“, „sonst“. Bisher hat in Train kein einziges Artefakt eine Notiz.
- **Offen:** Gelten beschlossene Regeln rückwirkend? Dann müssten die betroffenen Bahnen in Train und Val (etwa die
  geraden Rand-zu-Rand-Bahnen) neu gelabelt werden, mit Archiv der alten Labels.
- **Offen:** Die Helfenden labeln die Testsets seit dem 05.11.2026 nach der bisherigen Kurzfassung. Ändert sich die
  Online-Kurzfassung jetzt, sind die Testlabels in sich uneinheitlich; ändert sie sich nicht, labeln Test und
  Training nach verschiedenen Regeln. Zu entscheiden, und in der Arbeit zu nennen.
- **Offen:** Bis wann? Das Val-Recheck soll am 10.11. beginnen, die Regeln sollten vorher feststehen.

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
   Daraus Cohen's κ berichten. Aktueller Durchgang: [Zweitlabeln (Recheck)](#zweitlabeln-recheck).
4. Labels liegen in `labels/<split>.jsonl`, je Zeile Klasse, Flags, Notiz und die komplette Bahn.
   Test-Bahnen erst nach dem Einfrieren des Modells selbst labeln und auswerten (siehe unten).

## Zweitlabeln (Recheck)

Vorbereitet am 07.11.2026. Misst meine **Selbstübereinstimmung** (Test-Retest) auf Train und Validierung, die nur ich
gelabelt habe. Anlass ist die Fehleranalyse ([methode.md](methode.md#7-fehleranalyse-und-labelqualität)). Ein Recheck
mit Video misst nicht, ob die Bahn die Information enthält; dafür ist der zweite Durchgang unten gedacht.

| | Train | Validierung |
|---|---|---|
| Queue | `labels/queue_recheck.json` | `labels/queue_recheck_val.json` |
| Inhalt | 50 zufällige gelabelte Bahnen (Seed 0) | 15 verdächtige + 35 zufällige gelabelte Bahnen, gemischt (Seed 1107) |
| Split in der App | `recheck` („Zweitlabeln (blind)“) | `recheck_val` („Zweitlabeln Validierung (blind)“) |
| Ergebnis | `labels/recheck.jsonl` | `labels/recheck_val.jsonl` |
| frühestens ab | **12.11.2026** | **10.11.2026** |

- Erzeugt mit `uv run beeflight-sample --recheck 50` bzw.
  `uv run beeflight-sample --recheck 50 --recheck-split val --seed 1107 --force <ids.json>`. `--force` mischt
  vorgegebene IDs unter die Zufallsbahnen. Gibt es Queue oder Ergebnisdatei schon, bricht das Skript ab.
- **Verdächtig** sind die 15 Val-Bahnen, die alle alten Modelle in allen Seeds falsch hatten. Welche das sind, steht
  in keiner Doku und nicht in der Queue (dort nur Geometrie und das Tracker-`stratum`); die Liste liegt außerhalb des
  Repositorys. Vor der Auswertung nicht nachsehen.
- **Blind:** Die Recheck-Seiten lesen nur ihre eigene Ergebnisdatei. Erstes Label, Notizen und Modellvorhersagen sind
  nicht zu sehen; geschrieben wird nie nach `train.jsonl` oder `val.jsonl`. Recheck-Splits zeigen keine
  Klassenverteilung.
- **Wochenabstand:** Regel ist mindestens 1 Woche ([Ablauf](#ablauf), Schritt 3). 40 der 50 Train-Bahnen sind seit
  dem 31.10. gelabelt, darum Train erst ab 12.11. Wer früher zweitlabelt, erinnert sich an Bahnen, κ fällt zu hoch
  aus. Alternative: Queue löschen und nur aus Labels ziehen, die mindestens 7 Tage alt sind.
- Labelregeln: Vor dem Recheck sollten die [Regeln für Grenzfälle](#labelregeln-für-grenzfälle--entwurf-entscheidung-durch-florian)
  feststehen. Gilt im Recheck eine neue Regel, misst κ Regeländerung plus Inkonsistenz; das in der Auswertung nennen.

### Auswertungsregel (vor dem Aufdecken festgelegt)

Stand 07.11.2026, vorgeschlagen bei der Vorbereitung. Gilt so, wenn sie vor dem ersten Zweitlabel nicht mehr geändert
wird; spätere Änderungen nur mit Datum und Begründung.

1. **Intra-Rater-κ:** Cohens κ ohne Gewichte über die 4 Klassen, erstes gegen zweites Label derselben Bahn. Dazu
   95-%-Bootstrap-Intervall (2000 Ziehungen über Bahnen), Anteil gleicher Labels und Konfusionsmatrix. Flags zählen
   nicht.
   - Train: alle 50 Bahnen.
   - Validierung: **nur die 35 Zufallsbahnen.** Die 15 Verdächtigen sind nach Modellfehlern ausgewählt und würden κ
     nach unten verzerren.
   - Train-κ und Val-κ getrennt angeben, bei ähnlichen Werten zusätzlich gepoolt (n = 85).
2. **Verdächtige gegen Zufallsbahnen:** Änderungsrate (zweites Label ≠ erstes) der 15 gegen die 35, exakter Test nach
   Fisher, einseitig. Deutlich höher bei den Verdächtigen: Labelfehler erklären einen Teil der Modellfehler. Etwa
   gleich: Die Fehler liegen bei den Modellen bzw. an fehlender Information.
3. **Einordnung pro Bahn:** zweites Label ≠ erstes und nicht `unsicher` → „Label war falsch“. Abweichend und
   `unsicher` → „mehrdeutig“, bleibt in `val.jsonl` unverändert und wird getrennt gezählt. Gleich → „bestätigt“, auch
   wenn die Modelle sich irren.
4. **Korrekturen** an `val.jsonl` erst nach der Auswertung und nur für „Label war falsch“, als eigener, dokumentierter
   Schritt (alte Version archivieren). Danach nicht erneut auf Validierung tunen. In der Arbeit beide
   Val-Ergebnisse berichten, mit alten und mit korrigierten Labels.

Genauigkeit: Bei n = 50 ist κ auf etwa ±0,15 bis ±0,18 genau, bei den 35 Val-Zufallsbahnen auf etwa ±0,2. Der Test
in Punkt 2 erkennt nur einen großen Unterschied (Power etwa 0,83 bei Änderungsrate 0,5 gegen 0,15, etwa 0,38 bei 0,3).

### Vorschlag: zwei Durchgänge und Pflichtnotiz (noch nicht beschlossen)

Aus der Fehleranalyse. Damit sich „Label inkonsistent“ von „Information nur im Video“ trennen lässt:

| Durchgang | Was ich sehe | Weicht vom ersten Label ab → |
|---|---|---|
| **B: nur Bahn** | eingezeichnete Bahn ohne Video | die Bahn allein reicht für dieses Label nicht (wenn A stabil bleibt) |
| **A: mit Video** | wie beim ersten Labeln | Inkonsistenz bzw. Drift |

- In Durchgang A ist bei jedem `artefakt` eine Notiz zur Art **Pflicht** (Bienenwechsel, Vorbeiflug, zu kurz,
  Krabbeln, Gras/Schatten, sonst).
- Selbstübereinstimmung aus A ist zugleich eine grobe Obergrenze für die erreichbare Accuracy.
- **Offen:** Reihenfolge. B vor A, sonst erinnert das Video die Bahn. Beide in derselben Woche oder B zuerst ab 10.11.?
- **Offen:** Die App hat noch keinen Modus „nur Bahn“; das wäre eine Änderung am Labeler (eigener Split, Video
  ausgeblendet). Ohne ihn bleibt es beim einen Durchgang A.
- **Offen:** Gilt die Auswertungsregel oben für B genauso, oder nur für A?

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
Übungsergebnis und Übereinstimmung mit der Mehrheit. α gilt aber nur für die Testsets. Train und Validierung labele
ich allein, darum ist das Zweitlabeln seit dem 07.11.2026 wieder fest eingeplant
([Zweitlabeln (Recheck)](#zweitlabeln-recheck)).

Trainiert wird auf den Mehrheitslabels; `strittig` und `unsicher` können als Gewicht oder für eine Auswertung
„nur eindeutige Bahnen“ dienen.
