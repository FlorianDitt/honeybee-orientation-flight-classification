# Biologie: Orientierungsflüge und wie man sie vor dem Flugloch erkennt

Hintergrund für das Labeln ([labeling.md](labeling.md)), die Label-Webseite und Folie 1. Kurzfassung in
[idee.md](idee.md#biologischer-hintergrund). Hauptquellen sind **Capaldi et al. (2000)** und **Degen et al. (2016)**;
was nur aus anderen Quellen oder aus der Imkerpraxis stammt, ist als solches markiert.

## Überblick in fünf Sätzen

1. Eine Arbeiterin arbeitet zuerst im Stock und wird erst später Sammlerin.
2. Bevor sie sammelt, fliegt sie mehrere **Orientierungsflüge**: kurze Erkundungsflüge rund um den Stock, die mit
   jedem Flug schneller werden und eine größere Fläche abdecken (Capaldi et al. 2000).
3. Auf diesen Flügen lernt sie die **Landschaft um den Stock** und findet damit später heim (Degen et al. 2016).
4. Vor dem Flugloch sieht man davon nur den Anfang: Die Biene startet, wendet sich dem Stock zu und fliegt
   **Bögen und Schleifen** quer zum Eingang, statt zügig abzufliegen.
5. Diesen Anfang soll das Modell von direkten Abflügen und von suchenden Landeanflügen unterscheiden.

## Vom Stockdienst zum Sammeln

Arbeiterinnen durchlaufen eine Abfolge von Tätigkeiten (Altersarbeitsteilung): Putzen, Brutpflege, Wabenbau,
Futterabnahme, Wächterdienst, dann Sammeln. Die Orientierungsflüge liegen **am Übergang**, sie beginnen aber
schon, während die Biene noch Stockdienste macht, und ziehen sich über mehrere Tage. Junge Bienen fliegen also
schon aus, lange bevor sie Sammlerinnen sind.

Capaldi et al. zeigen, dass die Flüge sich mit der **Zahl der bisherigen Flüge** verändern, nicht mit dem Alter.
Für das Projekt heißt das: Wir erkennen **Flugverhalten, das einem Orientierungsflug entspricht**, nicht das Alter
der Biene.

*Zu prüfen:* genaue Altersangaben (häufig genannt: erste Orientierungsflüge ab etwa dem 3.–14. Lebenstag, Sammeln
ab etwa der dritten Woche). Nicht ohne Quelle auf Folien übernehmen.

## Was Orientierungsflüge sind: Capaldi et al. (2000)

Markierte Arbeiterinnen tragen einen Harmonic-Radar-Transponder; ihre Flüge werden im Gelände über Hunderte Meter
verfolgt. Ergebnisse (Abstract):

- Bienen machen **mehrere** Orientierungsflüge, bevor sie sammeln.
- Die **Dauer** eines Flugs bleibt mit zunehmender Erfahrung etwa gleich, die Bienen fliegen aber **schneller** und
  decken eine **größere Fläche** ab.
- Jeder Flug bleibt meist in einem **schmalen Sektor** um den Stock; aufeinanderfolgende Flüge erkunden die
  Umgebung Stück für Stück.
- Die Veränderung hängt von der **Erfahrung** (Zahl der Flüge) ab, nicht vom Alter.

## Wozu sie dienen: Degen et al. (2016)

Bienen wurden nach Orientierungsflügen an andere Stellen versetzt und ihr Heimflug per Harmonic Radar verfolgt. Ihre
Heimflüge zeigen, dass sie auf den Orientierungsflügen **Strukturen am Boden und deren Lage zueinander** gelernt
haben und diese Landschaftsmerkmale zum Heimfinden nutzen. Orientierungsflüge sind also echtes **exploratives
Lernen**, kein bloßes Einfliegen.

**Für das Projekt:** Eine Biene ohne diese Flüge findet nicht zuverlässig heim. Wie viele Orientierungsflüge ein
Volk zeigt, sagt deshalb etwas darüber, wie viele Bienen gerade ins Sammeln nachrücken.

## Was davon in unserem Video sichtbar ist

Die Kamera zeigt nur den Bereich **direkt vor dem Flugloch** (Flugbrett und etwa eine Handbreit bis wenige
Dezimeter davor). Ein Orientierungsflug reicht Dutzende bis Hunderte Meter weit; wir sehen also nur den
**Anfang** (und manchmal das Ende) des Flugs.

| Merkmal aus der Literatur | Im Video sichtbar? | Wie wir es nutzen |
|---|---|---|
| Start am Flugloch, Biene wendet sich dem Stock zu und schwebt davor | **ja** | Kernmerkmal der Klasse `orientierung` |
| Bögen und Schleifen quer zum Flugloch, die größer werden | **ja**, solange sie im Bild bleiben | Geradheit, Netto-Windung (`straight`, `turn_deg`) |
| Langsamer als ein direkter Abflug | **ja**, relativ (px/Frame, nicht m/s) | Merkmal `speed` |
| Rückkehr zum Flugloch nach dem Flug | manchmal (Brett → Brett) | Selbst-Label `board_board` |
| Reichweite, Fläche, Sektor im Gelände | nein | nicht nutzbar |
| Lernen der Landmarken | nein | nicht nutzbar |
| Blickrichtung der Biene | kaum (~30 px) | nur beim Labeln als Hinweis, kein Merkmal |
| Pollenhöschen bei heimkehrenden Sammlerinnen | kaum (Auflösung) | nicht genutzt |

Absolute Geschwindigkeiten in m/s aus Radar-Studien lassen sich nicht übertragen: Sie messen den Flug im
Gelände, wir nur die ersten Dezimeter, und unsere Bahnen sind in Pixeln ohne Kalibrierung.

## Abgrenzung zu den anderen Klassen

| | `orientierung` | `sammelabflug` | `anflug` | `artefakt` |
|---|---|---|---|---|
| **Start** | Flugbrett oder direkt davor | Flugbrett | außerhalb des Bildes | – |
| **Ende** | verlässt das Bild oder landet wieder | verlässt das Bild | Flugbrett | – |
| **Form** | Bögen, Schleifen, Zickzack quer zum Flugloch | zügig, fast gerade | darf kurven und suchen, Ziel ist das Flugloch | keine echte Flugbahn |
| **Blickrichtung** | zum Stock gedreht | vom Stock weg | zum Stock | – |
| **Tempo** | eher langsam, schwebend | schnell | bremst vor der Landung | – |

**Kurvig allein ist kein Orientierungsflug.** Der schwierigste Fall ist Orientierung gegen suchenden Anflug:
Beide kurven vor dem Flugloch und blicken zum Stock. Entscheidend sind **Start und Ende**: Ein Orientierungsflug
beginnt am Flugloch, ein Anflug endet dort. Wo Anfang oder Ende fehlen (Tracking-Abriss, Flag `fragment`), wird es
mehrdeutig. Deshalb wiegt die Fragmentierung gerade bei dieser Klasse schwer.

Das zeigt sich schon in den ersten Zweitstimmen: Von 89 doppelt gelabelten Bahnen stimmen 65 % überein, und
22 der 31 Abweichungen sind Bahnen, die ich als Abflug, Anflug oder Artefakt gelabelt habe und die Zweitlabelnde
als `orientierung`. Ohne Hintergrund wird „kurvig“ zu „Orientierung“.

Tätigkeiten direkt auf dem Brett (Fächeln, Wächterinnen, Krabbeln) erzeugen keine Flugbahn unterhalb des Bretts
und fallen schon im Flugfilter heraus; was durchrutscht, ist `artefakt`.

## Was sonst noch vor dem Flugloch fliegt

Aus der Imkerpraxis, nicht aus den beiden Hauptquellen. Diese Flüge können wie Orientierungsflüge aussehen:

| Flug | Wie er aussieht | Label |
|---|---|---|
| **Räuberinnen** (fremde Bienen, die Honig stehlen wollen) | pendeln suchend und zickzackend vor dem Eingang, oft an den Brettkanten; typisch bei Trachtmangel im Spätsommer/Herbst | kommen von außen → `anflug` bzw. Grenzfall `unsicher` |
| **Drohnen** | machen ebenfalls Orientierungsflüge, sind deutlich größer und fliegen schwerfälliger | Bahn nach Form labeln, Notiz „Drohne“ |
| **Re-Orientierung** erfahrener Sammlerinnen | nach Umstellen oder Störung des Stocks; sieht aus wie ein normaler Orientierungsflug | nicht unterscheidbar, `orientierung` |
| **Wespen, Hornissen** | lauern schwebend vor dem Flugloch | `artefakt` |
| **Bestatterinnen** | tragen eine tote Biene, fliegen tief und gerade weg | `sammelabflug` |

Dass Räuberei und Drohnen im Datensatz vorkommen, hängt von der Jahreszeit der Aufnahme ab. *Offen:* Monat und
Uhrzeit der Aufnahmen aus der Datensatzbeschreibung holen.

## Was der Indikator kann und was nicht

- **Mehr ist nicht automatisch gesünder.** Verliert ein Volk Sammlerinnen (Krankheit, Varroa, Pestizide), rücken
  junge Bienen früher ins Sammeln nach, und es gibt *mehr* frühe Orientierungsflüge, nicht weniger (beschleunigte
  Verhaltensreifung; *zu prüfen:* Perry et al. 2015). Aussagekräftig ist die **Abweichung vom Normalwert des
  Volkes**, z. B. das Verhältnis von Orientierungsflügen zu heimkehrenden Sammlerinnen.
- **Tageszeit und Wetter dominieren.** Orientierungsflüge kommen schubweise, an warmen Tagen meist nachmittags
  (Imkersprache: „Vorspiel“). In 37 min Aufnahme misst der Anteil vor allem diese Schübe und das Wetter, nicht die
  Vitalität. Stock B (bedeckt, ~9 Bahnen pro 30 s) zeigt, wie stark das Wetter wirkt.
- Forschungsfrage 5 beschreibt deshalb den **Verlauf** über die Aufnahme und ist kein Gesundheitsurteil.

## Literatur

### Hauptquellen

- Capaldi, E. A., Smith, A. D., Osborne, J. L., Fahrbach, S. E., Farris, S. M., Reynolds, D. R., Edwards, A. S.,
  Martin, A., Robinson, G. E., Poppy, G. M., & Riley, J. R. (2000). Ontogeny of orientation flight in the honeybee
  revealed by harmonic radar. *Nature*, 403, 537–540. doi:10.1038/35000564
- Degen, J., Kirbach, A., Reiter, L., Lehmann, K., Norton, P., Storms, M., Koblofsky, M., Winter, S.,
  Georgieva, P. B., Nguyen, H., Chamkhi, H., Meyer, H., Singh, P. K., Manz, G., Greggers, U., & Menzel, R. (2016).
  Honeybees learn landscape features during exploratory orientation flights. *Current Biology*, 26(20), 2800–2804.
  doi:10.1016/j.cub.2016.08.013

### Weitere, noch nicht im Volltext gelesen

- Degen, J., et al. (2015). Exploratory behaviour of honeybees during orientation flights. *Animal Behaviour*,
  102, 45–57. doi:10.1016/j.anbehav.2014.12.030
- Henry, M., Béguin, M., Requier, F., et al. (2012). A common pesticide decreases foraging success and survival in
  honey bees. *Science*, 336, 348–350. (Heimkehrrate versetzter Sammlerinnen, nicht Orientierungsflüge.)
- Perry, C. J., Søvik, E., Myerscough, M. R., & Barron, A. B. (2015). Rapid behavioral maturation accelerates
  failure of stressed honey bee colonies. *PNAS*, 112(11), 3427–3432. (Aus dem Gedächtnis, Angaben prüfen.)

### Noch am Original zu prüfen

Diese Zahlen kursieren in Zusammenfassungen, ließen sich aber nicht am frei zugänglichen Text bestätigen. Erst nach
Prüfung im Volltext (vermutlich Capaldi et al. 2000) in Folien oder Arbeit übernehmen:

- im Mittel etwa 5–6 Orientierungsflüge pro Biene (Spanne 1–18), Beginn im Alter von 3–14 Tagen
- Flugdauer im Median etwa 2 min, größte Entfernung im Median etwa 60 m, bis über 300 m
- Bodengeschwindigkeit orientierender Bienen etwa 3,6 m/s gegenüber etwa 5,6 m/s bei Sammlerinnen
- in rund 96 % der Flüge mindestens die Hälfte der Strecke in einem Quadranten, bevorzugt vor dem Flugloch
