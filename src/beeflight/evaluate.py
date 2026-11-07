"""Evaluate saved predictions of any classifier against hand labels. Trains nothing and knows no model.

A prediction file is JSON: {"model": "gru", "seed": 0, "predictions": {track id: class},
"probabilities": {track id: {class: p}} (optional), "size": 25 (optional, learning curve)}.
Predictions must cover every labelled trajectory of the split and may not contain ids from elsewhere.

Test sets stay closed unless --test is given, and are always read from labels/final_<split>.jsonl
(beeflight-vote --test). They are reported against the majority (primary), the owner's labels, and on unanimous
trajectories only. Train and val use labels/<split>.jsonl unless --labels final is given.

Intervals: 95 % cluster bootstrap over sequences with at least 10 sequences. With fewer (Test A), Wilson intervals
on class recall and precision, which ignore dependence, and the leave-one-sequence-out range.

Writes outputs/eval/<split>/summary.md and summary.json.

Usage: beeflight-evaluate --split val --predictions outputs/runs/<group> [--baseline rule]
       beeflight-evaluate --split test_same_hive --test --predictions <dir> --baseline rule
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from . import metrics as M
from .splits import ROOT
from .tracks import BOARD, SCALE, zone_of

LABELS = ROOT / "labels"
OUT = ROOT / "outputs" / "eval"
TEST_SPLITS = ["test_same_hive", "test_other_hive"]
FRAME_SIZE = (960, 540)  # (h, w) at half resolution


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_rows(split, source):
    path = LABELS / (f"final_{split}.jsonl" if source == "final" else f"{split}.jsonl")
    if not path.exists():
        raise SystemExit(f"{path} does not exist" + (" (run beeflight-vote first)" if source == "final" else ""))
    return [r for r in read_jsonl(path) if r.get("label") in M.CLASSES]


def queue_ids(split):
    path = LABELS / f"queue_{split}.json"
    return {i["id"] for i in json.loads(path.read_text())["items"]} if path.exists() else set()


def label_variants(rows, owner):
    """Variant name -> (rows, labels). Rows without single votes only have their one label."""
    if not any("votes" in r for r in rows):
        return {"eigene Labels": (rows, [r["label"] for r in rows])}
    authored = [r for r in rows if owner in r.get("votes", {})]
    unanimous = [r for r in rows if len(r.get("votes", {})) >= 2 and len(set(r["votes"].values())) == 1]
    return {"Mehrheit (primär)": (rows, [r["label"] for r in rows]),
            "Autor": (authored, [r["votes"][owner] for r in authored]),
            "einstimmig": (unanimous, [r["label"] for r in unanimous])}


def flight_zone(rec):
    """-> (shape of the flight zone below the board top, board bottom in it), at half resolution."""
    top, bottom = (int(v * SCALE) for v in BOARD[rec])
    return (FRAME_SIZE[0] - top, FRAME_SIZE[1]), bottom - top


def is_fragment(row):
    """A trajectory is a fragment if it starts or ends in the middle of the image (zone `lost`)."""
    shape, board_bottom = flight_zone(row["seq"][3:7])
    return "lost" in (zone_of(row["xy"][0], shape, board_bottom), zone_of(row["xy"][-1], shape, board_bottom))


def load_runs(paths, known_ids, labelled_ids):
    """-> model name -> runs sorted by seed. Any gap or unknown id stops the evaluation."""
    files = []
    for path in map(Path, paths):
        files += sorted(path.glob("*.json")) if path.is_dir() else [path]
    if not files:
        raise SystemExit("no prediction files found")
    runs = {}
    for file in files:
        run = json.loads(file.read_text())
        if not {"model", "seed", "predictions"} <= set(run):
            raise SystemExit(f"{file}: needs the keys model, seed and predictions")
        missing = labelled_ids - set(run["predictions"])
        unknown = set(run["predictions"]) - known_ids
        if missing or unknown:
            raise SystemExit(f"{file}: {len(missing)} labelled trajectories without prediction, "
                             f"{len(unknown)} predictions with unknown ids")
        bad = set(run["predictions"].values()) - set(M.CLASSES)
        if bad:
            raise SystemExit(f"{file}: unknown classes {sorted(bad)}")
        name = f"{run['model']}_n{run['size']}" if run.get("size") else run["model"]
        if any(r["seed"] == run["seed"] for r in runs.get(name, [])):
            raise SystemExit(f"{file}: {name} seed {run['seed']} appears twice")
        runs.setdefault(name, []).append(run)
    return {name: sorted(rs, key=lambda r: r["seed"]) for name, rs in sorted(runs.items())}


def prediction_matrix(runs, rows):
    return np.array([M.encode([run["predictions"][r["id"]] for r in rows]) for run in runs])


def evaluate_model(runs, rows, y, seqs, bootstrap, n_boot, sequence_level):
    preds = prediction_matrix(runs, rows)
    out = {"seeds": [run["seed"] for run in runs], "metrics": {}}
    for name, stat in M.summary_stats().items():
        values = np.array([stat(y, p) for p in preds])
        defined = values[~np.isnan(values)]
        entry = {"mean": M.seed_mean(stat, y, preds), "sd": float(defined.std()) if len(defined) else float("nan")}
        if bootstrap:
            entry["ci"] = M.cluster_bootstrap(y, preds, seqs, stat, n_boot)
        elif name in ("balanced_accuracy", "share_error"):
            entry["loso"] = M.leave_one_sequence_out(y, preds, seqs, stat)
        out["metrics"][name] = entry

    tables = [M.class_table(y, p) for p in preds]
    out["classes"] = []
    for i, cls in enumerate(M.CLASSES):
        correct = float(np.mean([t[i]["correct"] for t in tables]))
        predicted = float(np.mean([t[i]["predicted"] for t in tables]))
        n = tables[0][i]["n"]
        row = {"class": cls, "n": n, "predicted": predicted, "correct": correct, "too_few": n < M.MIN_EXAMPLES}
        if not bootstrap:
            row["recall_wilson"] = M.wilson(correct, n)
            row["precision_wilson"] = M.wilson(correct, predicted)
        out["classes"].append(row)
    out["confusion"] = np.mean([M.confusion(y, p) for p in preds], axis=0).tolist()
    out["share"] = {"true": M.orientation_share(y), "predicted": M.mean_defined([M.orientation_share(p) for p in preds])}
    if sequence_level:
        by_seed = [M.sequence_share_errors(y, p, seqs) for p in preds]
        out["sequence_mae"] = {"mae": M.mean_defined([s["mae"] for s in by_seed]), "used": by_seed[0]["used"],
                               "skipped": by_seed[0]["skipped"]}
    fragments = np.array([is_fragment(r) for r in rows])
    out["subgroups"] = {}
    for name, keep in (("vollständig", ~fragments), ("Fragment", fragments)):
        out["subgroups"][name] = {"n": int(keep.sum()),
                                  "balanced_accuracy": M.seed_mean(M.balanced_accuracy, y[keep], preds[:, keep])}
    if all("probabilities" in run for run in runs):
        out["auroc_orientierung"] = M.mean_defined([
            M.auroc_orientation(y, [run["probabilities"][r["id"]]["orientierung"] for r in rows]) for run in runs])
    return out


def evaluate_variant(rows, labels, runs, baseline, n_boot):
    y, seqs = M.encode(labels), np.array([r["seq"] for r in rows])
    n_seqs = len(set(seqs.tolist()))
    bootstrap = n_seqs >= M.MIN_SEQUENCES
    sequence_level = all((seqs == s).sum() >= M.MIN_SEQUENCE_TRACKS for s in set(seqs.tolist()))
    present = sorted(set(y.tolist()))
    out = {"n": len(rows), "sequences": n_seqs, "interval": "cluster_bootstrap" if bootstrap else "wilson_loso",
           "class_counts": {c: int((y == i).sum()) for i, c in enumerate(M.CLASSES)},
           "absent_classes": [c for i, c in enumerate(M.CLASSES) if i not in present],
           "chance_level": 1 / len(present) if present else float("nan"),
           "models": {name: evaluate_model(rs, rows, y, seqs, bootstrap, n_boot, sequence_level)
                      for name, rs in runs.items()}}
    if baseline:
        base = prediction_matrix(runs[baseline], rows)
        out["baseline"], out["comparison"] = baseline, {}
        for name, rs in runs.items():
            if name == baseline:
                continue
            preds = prediction_matrix(rs, rows)
            out["comparison"][name] = {}
            for key in ("balanced_accuracy", "recall_orientierung", "precision_orientierung", "share_error"):
                stat = M.summary_stats()[key]
                if bootstrap:
                    entry = M.paired_difference(y, preds, base, seqs, stat, n_boot)
                else:
                    entry = {"difference": M.seed_mean(stat, y, preds) - M.seed_mean(stat, y, base),
                             "loso": M.leave_one_sequence_out(y, preds, seqs, stat, baseline=base)}
                out["comparison"][name][key] = entry
    return out


def fmt(x, digits=3):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{digits}f}"


def count(x):
    return f"{x:.0f}" if float(x).is_integer() else f"{x:.1f}"


def span(low, high, digits=2, sep="–"):
    return "–" if math.isnan(low) or math.isnan(high) else f"{fmt(low, digits)}{sep}{fmt(high, digits)}"


def interval(entry):
    if "ci" in entry:
        return span(entry["ci"]["low"], entry["ci"]["high"])
    if "loso" in entry:
        return f"LOSO {span(entry['loso']['low'], entry['loso']['high'])}"
    return "–"


def class_cell(metric, row, kind):
    """Value with raw counts and interval, e.g. 0.750 (3/4, 0.30–0.95)."""
    k, n = row["correct"], row["n"] if kind == "recall" else row["predicted"]
    wil = row.get(f"{kind}_wilson")
    return f"{fmt(metric['mean'])} ({count(k)}/{count(n)}, {span(*wil) if wil else interval(metric)})"


def render_variant(name, res):
    lines = [f"## Labels: {name}", "",
             f"{res['n']} Bahnen, {res['sequences']} Sequenzen. Klassen: "
             + ", ".join(f"{c} {n}" + (" (zu wenige Beispiele)" if 0 < n < M.MIN_EXAMPLES else "")
                         for c, n in res["class_counts"].items()) + ".", ""]
    if res["absent_classes"]:
        lines += [f"**Keine Beispiele für {', '.join(res['absent_classes'])}:** Balanced Accuracy und Macro-F1 nur "
                  f"über die vorhandenen Klassen, Zufall = {res['chance_level']:.2f} statt 0.25.", ""]
    lines += ["Intervalle: 95-%-Cluster-Bootstrap über Sequenzen." if res["interval"] == "cluster_bootstrap" else
              "Intervalle: Wilson für Klassenwerte (ignoriert die Abhängigkeit innerhalb einer Sequenz, also zu eng); "
              "LOSO = Spanne beim Weglassen je einer Sequenz. Kein Bootstrap bei so wenigen Sequenzen.", "",
              "| Modell | Seeds | Balanced Acc. ± SD | Intervall | Recall Orientierung | Precision Orientierung | "
              "Accuracy | Macro-F1 |", "|---|---|---|---|---|---|---|---|"]
    for model, m in res["models"].items():
        s, orient = m["metrics"], m["classes"][M.ORIENTATION]
        ba = s["balanced_accuracy"]
        lines.append(f"| {model} | {len(m['seeds'])} | {fmt(ba['mean'])} ± {fmt(ba['sd'])} | {interval(ba)} | "
                     f"{class_cell(s['recall_orientierung'], orient, 'recall')} | "
                     f"{class_cell(s['precision_orientierung'], orient, 'precision')} | "
                     f"{fmt(s['accuracy']['mean'])} | {fmt(s['macro_f1']['mean'])} |")
    if res["interval"] == "cluster_bootstrap":
        worst = max(m["metrics"]["balanced_accuracy"]["ci"]["missing_class_share"] for m in res["models"].values())
        if worst:
            lines += ["", f"In {worst:.0%} der Bootstrap-Stichproben fehlt mindestens eine Klasse."]

    lines += ["", "### Indikator: Anteil `orientierung` an allen Bahnen außer `artefakt`", "",
              "| Modell | wahrer Anteil | vorhergesagt | Fehler (Prozentpunkte, vorzeichenbehaftet) | Intervall | "
              "MAE pro Sequenz |", "|---|---|---|---|---|---|"]
    for model, m in res["models"].items():
        err, seq = m["metrics"]["share_error"], m.get("sequence_mae")
        seq_cell = f"{100 * seq['mae']:.1f} ({seq['used']} Seq., {seq['skipped']} übersprungen)" if seq else "–"
        ci = err.get("ci") or err.get("loso")
        range_ = f"{'LOSO ' if 'loso' in err else ''}{span(100 * ci['low'], 100 * ci['high'], 1, ' bis ')}"
        lines.append(f"| {model} | {fmt(m['share']['true'])} | {fmt(m['share']['predicted'])} | "
                     f"{fmt(100 * err['mean'], 1)} | {range_} | {seq_cell} |")

    if "comparison" in res:
        lines += ["", f"### Gepaarter Vergleich gegen `{res['baseline']}` (Modell minus Baseline, beschreibend)", "",
                  "| Modell | Kennzahl | Differenz | Intervall |", "|---|---|---|---|"]
        for model, comparison in res["comparison"].items():
            for key, entry in comparison.items():
                lines.append(f"| {model} | {key} | {fmt(entry['difference'])} | {interval(entry)} |")

    lines += ["", "### Komplette Bahnen und Fragmente (Zonen, beschreibend)", "",
              "| Modell | vollständig (n) | Balanced Acc. | Fragment (n) | Balanced Acc. |", "|---|---|---|---|---|"]
    for model, m in res["models"].items():
        a, b = m["subgroups"]["vollständig"], m["subgroups"]["Fragment"]
        lines.append(f"| {model} | {a['n']} | {fmt(a['balanced_accuracy'])} | {b['n']} | {fmt(b['balanced_accuracy'])} |")

    lines += ["", "### Pro Klasse und Konfusion (Mittel über Seeds; Zeile = Label, Spalte = Vorhersage)"]
    for model, m in res["models"].items():
        lines += ["", f"**{model}**" + (f", AUROC Orientierung gegen Rest {fmt(m['auroc_orientierung'])}"
                                         if "auroc_orientierung" in m else ""), "",
                  "| Klasse | n | Recall | Precision |", "|---|---|---|---|"]
        for i, row in enumerate(m["classes"]):
            lines.append(f"| {row['class']}{' (zu wenige)' if 0 < row['n'] < M.MIN_EXAMPLES else ''} | {row['n']} | "
                         f"{class_cell(m['metrics'][f'recall_{row['class']}'], row, 'recall')} | "
                         f"{class_cell(m['metrics'][f'precision_{row['class']}'], row, 'precision')} |")
        lines += ["", "| | " + " | ".join(M.CLASSES) + " |", "|---" * 5 + "|"]
        lines += [f"| {M.CLASSES[i]} | " + " | ".join(count(v) for v in row) + " |" for i, row in enumerate(m["confusion"])]
    return lines


def render(split, source, results):
    lines = [f"# Auswertung {split} ({source})", ""]
    for name, res in results.items():
        lines += render_variant(name, res) + [""]
    lines += ["## Grenzen", "",
              "- Alle Kennzahlen gelten nur für Flüge, die der Tracker gefunden hat.",
              "- Test B ist ein einzelner anderer Stock unter anderen Bedingungen: Stock, Wetter und Kamera lassen sich "
              "nicht trennen, und der Vergleich verallgemeinert nicht auf andere Stöcke.",
              "- Vergleiche sind beschreibend, ohne p-Werte; Hauptvergleich ist das eingefrorene Modell gegen die "
              "auf Train abgestimmte Regel.",
              "- Einstimmige Bahnen sind die leichtere Teilmenge, kein Robustheitsnachweis."]
    return "\n".join(lines) + "\n"


def clean(x):
    """nan -> null, so the JSON stays valid."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return None if isinstance(x, float) and math.isnan(x) else x


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", required=True, choices=["train", "val", *TEST_SPLITS])
    ap.add_argument("--predictions", nargs="+", required=True, help="prediction files or directories of them")
    ap.add_argument("--labels", choices=["own", "final"], help="default: own for train and val, final for test")
    ap.add_argument("--baseline", help="model to compare the others against, e.g. rule")
    ap.add_argument("--owner", default="florian", help="annotator name of the owner in the votes")
    ap.add_argument("--n-bootstrap", type=int, default=M.N_BOOTSTRAP)
    ap.add_argument("--test", action="store_true", help="open the test sets; only after the model is frozen")
    ap.add_argument("--out", type=Path, help="output directory (default outputs/eval/<split>)")
    args = ap.parse_args(argv)

    is_test = args.split in TEST_SPLITS
    if is_test and not args.test:  # before any label file is opened
        raise SystemExit(f"{args.split} is a test set: pass --test, and only after the model is frozen")
    if is_test and args.labels == "own":
        raise SystemExit("test sets are only read from labels/final_<split>.jsonl")
    source = args.labels or ("final" if is_test else "own")
    rows = load_rows(args.split, source)
    if not rows:
        raise SystemExit(f"no labelled trajectories for {args.split}")
    ids = {r["id"] for r in rows}
    runs = load_runs(args.predictions, queue_ids(args.split) | ids, ids)
    if args.baseline and args.baseline not in runs:
        raise SystemExit(f"baseline {args.baseline} not among: {', '.join(runs)}")

    results = {}
    for name, (subset, labels) in label_variants(rows, args.owner.lower()).items():
        if subset:
            results[name] = evaluate_variant(subset, labels, runs, args.baseline, args.n_bootstrap)
    out = args.out or OUT / args.split
    out.mkdir(parents=True, exist_ok=True)
    text = render(args.split, source, results)
    (out / "summary.md").write_text(text)
    (out / "summary.json").write_text(json.dumps(clean(results), indent=1, ensure_ascii=False))
    print(text)
    print(f"-> {out / 'summary.md'}")


if __name__ == "__main__":
    main()
