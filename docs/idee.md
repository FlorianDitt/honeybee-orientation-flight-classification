# Idee: Orientierungsflüge als Vitalitätsindikator

## Thema

> **Orientierungsflug oder Sammelflug? Klassifikation von Flugbahnen junger Bienen vor dem Flugloch**

Angemeldet im Moodle-Forum WDS224 (Themenanmeldung), Oktober 2026.

## Biologischer Hintergrund

Eine Arbeiterin arbeitet zuerst im Stock (Brutpflege, Wabenbau, Wächterdienst) und wird erst später Sammlerin.
Vorher muss sie lernen, wo ihr Stock liegt. Dazu macht sie, oft schon während der Stockdienste, mehrere
**Orientierungsflüge**:

- Sie verlässt das Flugloch, **dreht sich zum Stock um** und fliegt in **Bögen und Schleifen** vor dem Eingang,
  die mit der Zeit größer werden.
- Mit jedem Flug fliegt sie schneller und deckt eine größere Fläche ab, meist in einem schmalen Sektor um den
  Stock; das hängt von der Zahl der Flüge ab, nicht vom Alter (Capaldi et al. 2000, per Harmonic Radar vermessen).
- Dabei lernt sie Landschaftsmerkmale, mit denen sie später heimfindet (Degen et al. 2016).
- An warmen Tagen sieht man oft viele junge Bienen gleichzeitig vor dem Stock schweben (Imkersprache:
  „Vorspiel“).

Eine **Sammlerin** dagegen fliegt nach dem Start zügig und relativ gerade in Richtung ihrer Trachtquelle ab.
Eine **heimkehrende** Biene nähert sich dem Flugloch, kurvt eventuell suchend und landet.

Ausführlicher, mit dem, was davon im Video sichtbar ist: [biologie.md](biologie.md).

## Warum das wichtig ist

**Vitalität des Volkes.** Wie viele Orientierungsflüge stattfinden, zeigt, wie viele neue Sammlerinnen
nachkommen. Das Signal ist aber nicht einfach „mehr ist besser“: Ein Volk mit wenig Nachwuchs (Brutkrankheiten,
Königinnenverlust) zeigt wenige, ein Volk, das Sammlerinnen verliert (Varroa, Pestizide), schickt junge Bienen
früher los und zeigt *mehr*. Aussagekräftig ist die Abweichung vom Normalwert des Volkes, und Tageszeit und Wetter
müssen herausgerechnet werden (siehe [biologie.md](biologie.md#was-der-indikator-kann-und-was-nicht)).

**Pestizide und Naturschutz.** Neonicotinoide stören die Heimfindung: In einem Feldversuch kehrten
mit Thiamethoxam behandelte Sammlerinnen deutlich seltener zurück (Henry et al. 2012). Ein automatischer
Monitor, der die Form der Flugbahnen am Flugloch auswertet, wäre ein **nicht-invasives Frühwarnsignal**:
ohne RFID-Chips, ohne Radar-Transponder, ohne das Volk zu öffnen, nur mit einer Kamera.

**Warum am Flugloch.** Orientierungsflüge beginnen und enden am Eingang. Das ist der einzige Ort, an dem eine
feste Kamera sie zuverlässig sieht, und genau den zeigt der Datensatz.

## Forschungsfragen

1. **Machbarkeit:** Lassen sich aus ungelabelten Flugloch-Videos genug vollständige Flugbahnen extrahieren?
   *(Vorstudie: ja, mit Einschränkungen, siehe [vorstudie.md](vorstudie.md).)*
2. **Klassifikation:** Unterscheidet ein gelerntes Trajektorien-Modell Orientierungsflüge von Sammelabflügen und
   suchenden Landeanflügen besser als eine einfache Krümmungsschwelle?
3. **Bild und Bahn:** Bringen eingefrorene Bildmerkmale (DINOv2) zusätzlich zur Bahn etwas, einzeln oder in einer
   Fusion?
4. **Generalisierung:** Wie stark fällt die Leistung vom selben Stock (Test A) zum fremden Stock (Test B) ab,
   und liegt das an der Bahnform oder am Tracking (anderes Holz, Licht, Abstand)?
5. **Indikator:** Wie verändert sich der Anteil der Orientierungsflüge über die 37 min Aufnahme? (Beschreibend:
   über so kurze Zeit misst das vor allem Schübe und Wetter, kein Gesundheitsurteil.)

## Hypothesen

- **H1:** Orientierungsflüge starten auf dem Flugbrett und haben eine deutlich geringere Geradheit
  (Netto-Weg / Pfadlänge) und mehr Windung als Sammelabflüge.
- **H2:** Die Bahnform allein reicht nicht, um Orientierungsflüge von suchenden Landungen zu trennen; Start- und
  Zielpunkt sind entscheidend. Ein Modell mit Zugriff auf die Position relativ zum Flugloch schlägt ein Modell
  nur auf der Form.
- **H3:** Ein sequenzielles Modell (ResNet auf der Bahn) schlägt die Krümmungs-Baseline vor allem bei fragmentierten Bahnen, weil
  es Geschwindigkeits- und Richtungsverläufe nutzt und nicht nur eine Summe.
- **H4:** Der Abfall von Test A zu Test B entsteht hauptsächlich beim Tracking (andere Bildstatistik), weniger
  beim Klassifikator (Bahnen in normierten Koordinaten).

## Warum das ein ML-Thema ist

- **Detektion über Gras:** Die Bienen sind 25–35 px groß und auf dem Gras-Hintergrund getarnt; das
  Hintergrundmodell verliert auch nach zwei Runden Nachbesserung noch ein Drittel der Bahnen an einem Ende. Ein gelernter Detektor ist nötig, um ganze Bahnen
  zu bekommen.
- **Klassifikation von Sequenzen:** variable Länge, Rauschen, Lücken, Klassen, die sich nur im Verlauf
  unterscheiden.
- **Wenig Labels:** Start- und Zielzone helfen beim Ziehen der Stichprobe; das Modell lernt aus rund 300 Handlabels.
  Das ist ein realistischer ML-System-Aufbau mit wenig Annotationsbudget.
- **Domain Shift:** zwei Stöcke, zwei Lichtsituationen, zwei Kamera-Abstände.

## Abgrenzung zu anderen Themen im Kurs

| Thema (Person) | Unterschied |
|---|---|
| Landepunktvorhersage anfliegender Bienen (D. Dieck) | Dort: *wo* landet eine Biene. Hier: *welchen Zweck* hat eine ganze Bahn. Keine Vorhersage zukünftiger Positionen. |
| Abflugvorhersage (C. Buck) | Dort: Biene auf dem Brett, fliegt sie in 1–3 s los? Hier: die Bahn *nach* dem Abflug. |
| Clustering Fliegen/Sitzen/Krabbeln (V. Merl) | Dort: Bewegungsart unüberwacht. Hier: nur fliegende Bienen, überwachte Klassifikation des Flugzwecks. |
| Bewegungsrichtung und Bildrate (V. Schudy) | Dort: Richtung in den nächsten 0,25 s auf dem Brett. Hier: Gestalt der gesamten Flugbahn. |
| Tracker-Vergleich (V. Holst) | Tracking ist hier Mittel zum Zweck, kein Methodenvergleich. |
| Job-Erkennung Wächter/Sammler (J. Holley) | Dort: Rollen auf dem Brett aus Interaktionen. Hier: Flugverhalten aus der Flugbahn, nicht das Alter. |
| Altersklassifikator über Flügel (M. Timmermann) | Dort: Aussehen der Flügel (alte Bienen). Hier: Verhalten junger Bienen. |

## Risiken

| Risiko | Gegenmaßnahme |
|---|---|
| Kurvige Bahnen sind nicht immer Orientierungsflüge (suchende Anflüge, Räuberinnen, Ausweichen, Wind) | Eigene Klasse „suchender Anflug“; Startpunkt als Merkmal (H2); Handlabels für Grenzfälle |
| Bahnen reißen über Gras ab | Detektor für die Flugzone trainieren; Fragmente über Bewegungsvorhersage verbinden; Ergebnis getrennt für vollständige und fragmentierte Bahnen berichten |
| Blickrichtung zum Stock ist bei ~30 px kaum messbar | Nicht als Label verwenden, nur Bahnform und Position |
| Stock B (bedeckt) hat wenig Flugverkehr: ~9 Bahnen / 30 s | Test B als kleines Set mit Konfidenzintervall berichten; Wetter als Störgröße diskutieren |
| Keine echte Ground Truth über das Alter der Bienen | Ehrlich formulieren: das Modell erkennt *Flugverhalten, das Orientierungsflügen entspricht*, nicht das Alter |

## Literatur

- Capaldi, E. A., Smith, A. D., Osborne, J. L., et al. (2000). Ontogeny of orientation flight in the honeybee
  revealed by harmonic radar. *Nature*, 403, 537–540. doi:10.1038/35000564
- Degen, J., Kirbach, A., Reiter, L., et al. (2016). Honeybees learn landscape features during exploratory
  orientation flights. *Current Biology*, 26(20), 2800–2804. doi:10.1016/j.cub.2016.08.013
- Degen, J., Kirbach, A., Reiter, L., et al. (2015). Exploratory behaviour of honeybees during orientation flights.
  *Animal Behaviour*, 102, 45–57.
- Henry, M., Béguin, M., Requier, F., et al. (2012). A common pesticide decreases foraging success and survival in
  honey bees. *Science*, 336, 348–350.

Vor der Abgabe Seitenzahlen und Autorenlisten noch einmal an den Originalen prüfen.
