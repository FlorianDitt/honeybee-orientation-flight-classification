# Literatur

Alle Arbeiten, die in [methode.md](methode.md), [idee.md](idee.md) und [labeling.md](labeling.md) für Methode,
Auswertung oder Abgrenzung zitiert werden. Biologische Quellen stehen in [biologie.md](biologie.md#literatur).

**Volltextprüfung am 07.11.2026:** Die Arbeiten unten wurden als PDF geladen und an den Stellen gelesen, die für
unsere Aussage zählen (Abstract, Methode, Ergebnisse, Empfehlungen). Nicht jedes Paper wurde vollständig gelesen.
Seitenangaben beziehen sich auf die gelesene Fassung, meist arXiv, nicht die Verlagsfassung. Die in der Spalte
„Zitat“ genannten Stellen sind **wörtlich bestätigt** (aus dem PDF-Text, nur Silbentrennung aufgelöst); andere
Formulierungen in unseren Docs sind Paraphrasen.

| Status | Bedeutung |
|---|---|
| **bestätigt** | unsere Aussage stimmt so |
| **teilweise** | stimmt im Kern, aber mit einer Einschränkung, die wir mitnennen müssen |
| **widerlegt** | trägt unsere Aussage nicht |
| **nicht gelesen** | nur Metadaten oder Sekundärquelle |

## Vorarbeiten und Abgrenzung

**Uns ist keine Arbeit bekannt, die Orientierungsflüge von Honigbienen automatisch aus Video oder Flugbahnen
klassifiziert**, und kein öffentlicher Benchmark dafür. Das ist das Ergebnis einer begrenzten Suche (drei Websuchen
am 07.11.2026 plus die Arbeiten unten), kein Beweis. So und nicht als „erste Arbeit“ formulieren. Die nächsten
Arbeiten nennen Orientierungsflüge nur:

| Arbeit | Was sie macht | Orientierungsflüge |
|---|---|---|
| Morton Williams 2024 | Flugbahnen vor dem Flugloch: rein / raus / schweben; Hummeln mit Harmonic Radar | nur als Ausblick und Vermutung |
| Sledevič et al. 2025 | Verhalten auf dem Flugbrett, regelbasiert auf YOLOv8-Tracks | nur in der Einleitung |
| Rodriguez et al. 2022 | Ein- und Ausflug über Start- und Endpunktregeln auf der Rampe | nicht behandelt |

| Zitation | Status | Wofür wir es nutzen | Zitat |
|---|---|---|---|
| Morton Williams, S. (2024). *Tracking and Predicting Bee Behaviour and Movement Using Machine Learning.* PhD-Thesis, Bangor University, School of Computer Science and Electronic Engineering. https://pure.bangor.ac.uk/ws/portalfiles/portal/71982953/2024MortonWilliamsPhD.pdf | bestätigt (Abstract, Kap. 4, 5 auszugsweise) | Nächstverwandte Arbeit: Regel gegen ML auf Bahnen vor dem Flugloch; Orientierungsflüge dort ausdrücklich Zukunftsarbeit, stützt die Neuheit. | Abstract („inwards, outwards, and hovering“); Kap. 4.7 S. 144 („investigation to correlate flight behaviour with younger bees, particularly investigating orientation loops …“); Kap. 5 („… can be attributed to bee orientation flights“) |
| Morton Williams, S., Aldabashi, N., Palego, C., Woodgate, J., Makinson, J., Cross, P. (2021). Early prediction of bumblebee flight task using machine learning. *Computers and Electronics in Agriculture.* doi:10.1016/j.compag.2021.106065 | nicht gelesen | Nur falls zitiert: Kap. 3 der Dissertation ist eine Fassung davon. Achtung: Der CORE-Link `core.ac.uk/download/511307054.pdf` ist dieser Artikel, nicht die Dissertation. | – |
| Sledevič, T., Serackis, A., Matuzevičius, D., Plonis, D., Vdoviak, G. (2025). Visual recognition of honeybee behavior patterns at the hive entrance. *PLOS ONE* 20(2): e0318401. doi:10.1371/journal.pone.0318401. Datensatz: Mendeley Data, doi:10.17632/8gb9r2yhfc.6 (Version 6) | bestätigt | Gegenstück auf dem Flugbrett (Laufen, Schwellenregeln, keine Flugbahnen vor dem Flugloch); Datensatz für den YOLO-Versuch (Negativbefund). DOI mit Version angeben. | S. 13 („Parameters such as speed thresholds … are derived from observed bee behavior patterns.“); Einleitung („… and orientation flights of young bees.“) |
| Rodriguez, I. F., Chan, J., Alvarez Rios, M., Branson, K., Agosto-Rivera, J. L., Giray, T., Mégret, R. (2022). Automated Video Monitoring of Unmarked and Marked Honey Bees at the Hive Entrance. *Frontiers in Computer Science* 3:769338. doi:10.3389/fcomp.2021.769338 | bestätigt | Ein- und Ausflug wird bisher über Start- und Endpunkt bestimmt, wie unsere Selbst-Labels und die Regel-Baseline. | §3.4.1 („We perform the detection of entrance and exit events using the starting and ending points of the tracks …“) |
| Halilovic, M. (2019). *Predicting bee trajectories using Recurrent Neural Networks.* Masterarbeit, Freie Universität Berlin, Biorobotics Lab. https://www.mi.fu-berlin.de/inf/groups/ag-ki/Theses/Completed-theses/Master_Diploma-theses/2019/Halilovic/MA-Halilovic.pdf | **teilweise bis widerlegt** | **Nicht als Beleg für Vortraining verwenden.** Die „Klassifikation“ ist eine Regression auf simulierten Agenten; auf echten Bienendaten (Laufbahnen im Stock, BeesBook) lernte das Vorhersagemodell laut Autorin nichts Brauchbares. Höchstens als Herkunft der Idee „Vorhersagemodell vortrainieren, Hidden States als Merkmale“. | Abstract („The Prediction model was not able to predict realistic bee trajectories.“); §5.3 („Only on the bee data it was not shown that the Prediction model learned anything meaningful.“) |

Suchtreffer, nur per Stichwort „orientation“ geprüft: Tozkar et al., „Continuous Non-Invasive Monitoring of Hive
Entrance Activity Reveals Honey Bee Colony Dynamics“, *Biology* 15, doi:10.3390/biology15090731 (Orientierungsflüge
nur als Deutung von Verkehrszahlen, keine Klassifikation; Jahr vor dem Zitieren prüfen). Nguyen & Reschke, „Bee
Detection and Tracking at Hive Entrance using YOLO11 and ByteTrack“, arXiv:2608.23213 (Detektion und Tracking,
„orientation“ meint dort die Flugrichtung).

## Modelle

| Zitation | Status | Wofür wir es nutzen | Zitat |
|---|---|---|---|
| Ismail Fawaz, H., Forestier, G., Weber, J., Idoumghar, L., Muller, P.-A. (2019). Deep learning for time series classification: a review. *Data Mining and Knowledge Discovery* 33, 917–963. doi:10.1007/s10618-019-00619-1. arXiv:1809.04356 | **teilweise** | Vorlage für das ResNet auf der Bahn. Richtig formuliert: ResNet ist die stärkste von **neun DL-Architekturen** auf dem UCR-Archiv, aber **nicht signifikant verschieden von HIVE-COTE/COTE** (HIVE-COTE bleibt dort am genauesten). Auf den 12 **multivariaten** Datensätzen fand der Test **keinen signifikanten Unterschied** zwischen den neun Modellen. Für x/y-Bahnen gibt es also keinen belegten Sieger; das spricht für den Vergleich mit einfachen Baselines. | §5.1 („The ResNet significantly outperforms the other approaches …“, gemeint sind die DL-Modelle); §5.2 („The statistical test failed to find any significant difference between COTE/HIVE-COTE and ResNet“); §5.3 („… failed to find any significant difference between the nine classifiers which is mainly due to the small number of datasets“) |
| Oquab, M., Darcet, T., Moutakanni, T., Vo, H., Szafraniec, M., Khalidov, V., et al. (2024). DINOv2: Learning Robust Visual Features without Supervision. *Transactions on Machine Learning Research* (01/2024). arXiv:2304.07193 | bestätigt | Eingefrorene Merkmale mit linearer Probe (Anhang B.3), Video über 8 gleichmäßig verteilte Frames (§7.2). Zu Objekten von ~30 px sagt das Paper nichts: Eignung für unsere Bienen ist eine offene empirische Frage. Die Rechnung „30-px-Biene ≈ 2 × 2 Patches à 14 px, Ausschnitt muss hochskaliert werden“ ist unsere, nicht aus dem Paper. | Table 4 („Linear evaluation on ImageNet-1k of frozen pretrained features“); §7.2 („we pick 8 evenly spaced frames in the video and train a linear classifier …“); §4 („… where small objects disappear at low resolutions.“) |
| Wang, W., Tran, D., Feiszli, M. (2020). What Makes Training Multi-Modal Classification Networks Hard? *CVPR 2020.* arXiv:1905.12681 | bestätigt für den untersuchten Fall | Fusion muss gegen die beste Einzelmodalität antreten; G-Blend. Einschränkung: Befunde aus End-to-End-Training auf großen Videodatensätzen (Kinetics, 240k Videos). Ansätze mit getrennt vortrainierten, eingefrorenen Zweigen nennen die Autoren „not comparable“, unser eingefrorener Bildzweig fällt darunter. | Abstract („the best uni-modal network often outperforms the multi-modal network“; „… We address these two problems with a technique we call Gradient-Blending“) |
| Bohnslav, J. P., Wimalasena, N. K., Clausing, K. J., Dai, Y. Y., Yarmolinsky, D. A., Cruz, T., Kashlan, A. D., Chiappe, M. E., Orefice, L. L., Woolf, C. J., Harvey, C. D. (2021). DeepEthogram, a machine learning pipeline for supervised behavior classification from raw pixels. *eLife* 10:e63377. doi:10.7554/eLife.63377 | bestätigt | Referenz für Verhaltensklassifikation aus Video. Übernehmbar: Shuffle-Baseline als Zufallsniveau und Vergleich mit der Übereinstimmung zwischen Menschen. Datenmengen sind Frames, nicht Bahnen, und die Tiere sind viel größer als 30 px. | Methods, „Shuffle“ („we randomly circularly permuted each video's labels 100 times …“); S. 10 („… statistically indistinguishable from human-level performance“) |
| Katona, Z., Mohammadi Ziabari, S. S. (2024). MARINE: A Computer Vision Model for Detecting Rare Predator-Prey Interactions in Animal Videos. arXiv:2407.18289. Preprint (Masterarbeit, University of Amsterdam), ohne Venue | bestätigt | Beispiel: eingefrorene DINOv2-Merkmale plus kleiner Kopf funktionieren bei wenigen hundert Clips. Nicht begutachtet, Tiere nicht auf 30 px beschränkt. | §3.2.2 („… from the DINOv2 backbone's output, without fine-tuning the model …“) |
| Wang, Y., Yu, H., Blau, A., Zhang, Y., International Brain Laboratory, Paninski, L., Hurwitz, C., Whiteway, M. R. (2026). Animal behavioral analysis and neural encoding with transformer-based self-supervised pretraining (BEAST). *ICLR 2026.* arXiv:2507.09513 | **teilweise** | Nur als **Ausblick**: Vortraining auf den eigenen ungelabelten Videos. Das Schema (MAE + temporales kontrastives Lernen, Start von ImageNet-Gewichten) ist bestätigt. Der Vorsprung vor DINOv2 und vor den Einzelverlusten ist gemischter als im Fließtext: Auf IBL ist der Keypoint-TCN gleichauf, auf CalMS21 ist MAE allein etwa gleich gut (0,82 gegen 0,81), schon ImageNet-MAE-Patches kommen nahe an Keypoint-Methoden. Laborvideos mit großen Tieren und statischem Hintergrund. | §3 („BEAST combines masked autoencoding with temporal contrastive learning …“); Diskussion („Notably, BEAST outperforms DINOv2 …“); Table 15 |
| Wang, L., Qiao, Y., Tang, X. (2015). Action Recognition with Trajectory-Pooled Deep-Convolutional Descriptors (TDD). *CVPR 2015.* arXiv:1505.04868 | **teilweise** | Nur **Analogie** für „Bildmerkmale entlang der Bahn ausschneiden und poolen“. Dort sind die Trajektorien dichte Punkt-Trajektorien (15 Frames lang), keine Objektbahnen; Kodierung über Fisher-Vektoren. Als Übertragung formulieren, nicht als Vorlage. | Abstract („… conduct trajectory-constrained pooling …“); §4 („we conduct sum-pooling of the normalized feature maps over the 3D volume centered at the trajectory“) |
| Zhao, Y., Xiong, Y., Lin, D. (2018). Trajectory Convolution for Action Recognition. *NeurIPS 2018* | **teilweise** | Nur **verwandter Ansatz** („Merkmale entlang der Bewegung ausrichten“). Es ist kein Pooling, sondern eine temporale Faltung entlang dichter Pfade aus optischem Fluss; kein Vorbild für objektzentrierte Ausschnitte. | Abstract („… allowing the visual features to be aggregated along the the motion paths, trajectories.“) |

## Auswertung und Metriken

| Zitation | Status | Wofür wir es nutzen | Zitat |
|---|---|---|---|
| Opitz, J. (2024). A Closer Look at Classification Evaluation Metrics and a Critical Reflection of Common Evaluation Practice. *Transactions of the Association for Computational Linguistics* 12. doi:10.1162/tacl_a_00675. arXiv:2404.16958 (gelesen: v2) | bestätigt, mit Einschränkung | Macro-Recall als Hauptmetrik (alle fünf Eigenschaften, Zufall 1/n), Macro-F1 ist nicht streng zufallskorrigiert, Formel angeben, Klassen-Recalls berichten. **Einschränkung:** Dass Balanced Accuracy gleich Macro-Recall ist, sagt Opitz nur in Fußnote 11 mit Verweis auf scikit-learn. Die Gleichsetzung begründen wir über die Formel selbst. DOI aus den arXiv-Metadaten, TACL-Fassung nicht gelesen. | §4.2 („Macro Recall has all five properties …“); Fn. 11 („We did not find a formula. As per scikit-learn (…) it may equal macro Recall.“); §8 („State the evaluation metric clearly, best use a formula.“) |
| Opitz, J., Burst, S. (2019/2021). Macro F1 and Macro F1. arXiv:1911.03347 (gelesen: v3). arXiv-Note ohne Venue | bestätigt | Es gibt zwei „Macro-F1“; wir nutzen „averaged F1“ (Mittel der Klassen-F1, sklearn `average='macro'`) und benennen das. | Abschnitt 4 („At the very least, researchers should indicate which formula they are using.“) |
| Maier-Hein, L., Reinke, A., Godau, P., Tizabi, M. D., et al. (2024). Metrics Reloaded: Recommendations for image analysis validation. *Nature Methods* 21, 195–212. doi:10.1038/s41592-023-02151-z. arXiv:2206.01653 (gelesen: v8) | bestätigt, mit Präzisierungen | Bei gleichen Fehlerkosten Balanced Accuracy (oder MCC), weil die Klassenanteile nicht der Zielpopulation entsprechen. **Multi-Threshold-Metriken (Default AUROC, pro Klasse) „always recommended“**, Zählmetriken pro Klasse nur „optional“, volle Konfusionsmatrix bei wenigen Klassen. Bei kleinem Testset Konfidenzintervalle für alle Metriken; die Methode (Bootstrap) ist unsere Wahl. Für Bildanalyse geschrieben, Übertragung auf Bahnen ist unsere Entscheidung. Die arXiv-Stelle „AP can be more suitable in the case of high class balance“ ist vermutlich ein Tippfehler, nicht wörtlich übernehmen. | „Image-level classification“ („… per-class counting metrics (optional) and multi-threshold metrics (always recommended).“); Suppl. Note 2.2 („we always recommend the selection of a multi-threshold metric …“); Table 1 („Recommendation of confidence intervals for all metrics.“) |
| Bouthillier, X., Delaunay, P., Bronzi, M., Trofimov, A., Nichyporuk, B., Szeto, J., Sepah, N., Raff, E., Madan, K., Voleti, V., Ebrahimi Kahou, S., Michalski, V., Serdyuk, D., Arbel, T., Pal, C., Varoquaux, G., Vincent, P. (2021). Accounting for Variance in Machine Learning Benchmarks. *Proceedings of Machine Learning and Systems (MLSys 2021).* arXiv:2103.03098 | bestätigt, mit Nuance | Möglichst viele Zufallsquellen variieren (Seeds, Datenauswahl); die Datenauswahl trägt mehr Varianz als die Initialisierung; Vergleich über P(A > B). **Gepaarte Auswertung steht nur im Anhang C.2 und ist dort „optional but highly recommended“**, keine Pflicht. **Venue vor dem Zitieren prüfen:** Der PDF-Kopf der arXiv-Fassung nennt „Proceedings of the 3rd MLSys Conference“, MLSys 2021 war aber die vierte. | §1 („As many sources of variation as possible should be randomized …“); §2.2 („Bootstrapping data stands out as the most important source of variance.“); App. C.2 („Pairing is optional but is highly recommended to increase statistical power.“) |

## Tracking

Diese Arbeiten stehen in [roadmap.md](roadmap.md) und wurden in der Prüfung vom 07.11.2026 **nicht** erneut gelesen.
Vollständige Angaben vor der Abgabe ergänzen.

- Zhang, Y., et al. (2022). ByteTrack. arXiv:2110.06864
- Ratnayake, M. N., et al. (2021). HyDaT. *PLOS ONE*
- Bewley, A., et al. (2016). SORT. arXiv:1602.00763
- Chiron, G., Gomez-Krämer, P., Ménard, M. (2013). *EURASIP Journal on Image and Video Processing* 2013:59 (Tracker der Labels)
- Yang, F., et al. (2023). C-BIoU. *WACV 2023*
- Huang, C., Wu, B., Nevatia, R. (2008). Tracklet-Verknüpfung, *ECCV 2008* (Titel ergänzen)
- Polytrack (in roadmap.md, Abschnitt 5.1 zitiert): Angaben ergänzen
