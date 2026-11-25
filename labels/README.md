# Labels

**Das Ergebnis sind die `final_*.jsonl`.** Alles andere sind Warteschlangen, Rohlabels und Nebenexperimente, aus denen
die finalen Dateien entstanden sind. Klassen und Regeln: [docs/labeling.md](../docs/labeling.md).

## Final (für Training und Auswertung)

| Datei | Inhalt |
|---|---|
| `final_train.jsonl`, `final_val.jsonl` | 600 und 204 Bahnen, eigene Labels |
| `final_test_same_hive.jsonl`, `final_test_other_hive.jsonl` | Test A und Test B: Mehrheit aus drei Labelnden (`beeflight-vote --test`), mit allen Stimmen |

## Rohlabels und Warteschlangen

| Datei | Inhalt |
|---|---|
| `train.jsonl`, `val.jsonl`, `test_*.jsonl` | Rohlabels aus dem lokalen Labeler (eine Zeile pro Bahn, mit Geometrie) |
| `queue_<split>.json` | Bahnen, die zum Labeln vorgelegt werden (`beeflight-sample`) |
| `own/` | eigene Labels aus der Online-Version (`beeflight-own`) |
| `votes/` | Exporte der Freiwilligen (Labeler 2 und 3), Eingabe für `beeflight-vote` |
| `recheck.jsonl`, `recheck_val.jsonl`, `queue_recheck*.json` | blindes Zweitlabeln von je 50 Bahnen (Intra-Rater-κ) |
| `id_map_<split>.json` | Zuordnung alter Bahn-IDs (Tracker v3) zu den neuen (Chiron + Huang) |
| `practice.json`, `tutorial.json` | Übungsrunde und Tutorial der Online-Version |

## Nebenexperimente

| Datei | Inhalt |
|---|---|
| `tracker_eval.jsonl` | blinde Handprüfung der Tracker (korrekt oder nicht) |
| `biene.jsonl`, `biene_queue.json` | „Ist eine Honigbiene auf der Bahn?“ für den Vorfilter (`beeflight.biene`) |
| `pose.jsonl`, `pose_queue.json` | Pilot Körperachse (Kopf und Hinterleib) im Einzelbild (`beeflight.pose`) |
| `archive/` | ältere Stände: Labels auf früheren Trackern, Testwarteschlangen, Stand vor der Recheck-Korrektur |
