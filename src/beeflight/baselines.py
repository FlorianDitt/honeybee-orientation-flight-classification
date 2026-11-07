"""Write prediction files for the comparison ladder, in the format beeflight-evaluate reads. No learning beyond the
two thresholds of the tuned rule.

Models:
- rule_fixed:       pilot-study thresholds (straightness < 0.5 and duration > 0.4 s make a departure `orientierung`)
- rule:             the same rule, thresholds chosen by balanced accuracy on the labels of train only
- random_uniform:   random class, equally likely (one file per seed)
- random_frequency: random class, in the class shares of the train labels (one file per seed)
- always_<class>:   one constant prediction per class

Every trajectory in labels/queue_<split>.json gets a prediction. Only labels/train.jsonl is read as labels, so this
is safe for the test sets: their labels and votes are never opened.

Writes outputs/baselines/<split>/<model>_s<seed>.json.

Usage: beeflight-baselines --split val [--seeds 5] [--out DIR]
"""
import argparse
import json
from pathlib import Path

import numpy as np

from . import metrics as M
from .evaluate import flight_zone
from .splits import ROOT
from .tracks import features

LABELS = ROOT / "labels"
OUT = ROOT / "outputs" / "baselines"
FIXED = (0.5, 0.4)  # straightness, duration in seconds
GRID = [(round(float(s), 2), round(float(d), 1)) for s in np.arange(0.2, 0.95, 0.05) for d in np.arange(0.1, 1.6, 0.1)]
ORIENTATION, DEPARTURE, ARRIVAL, ARTEFACT = (M.CLASSES.index(c) for c in
                                             ("orientierung", "sammelabflug", "anflug", "artefakt"))


def track_features(row):
    shape, board_bottom = flight_zone(row["seq"][3:7])
    return features(np.column_stack([np.array(row["t"], float), np.array(row["xy"], float)]), shape, board_bottom)


def rule_predict(f, straight=FIXED[0], dur=FIXED[1]):
    """Class index from start zone, end zone, straightness and duration of one trajectory."""
    if f["start"] == "board" and f["end"] == "board":
        return ORIENTATION
    if f["start"] == "board":
        return ORIENTATION if f["straight"] < straight and f["dur_s"] > dur else DEPARTURE
    if f["end"] == "board":
        return ARRIVAL
    return ARTEFACT


def tune_rule(feats, y):
    """Thresholds with the best balanced accuracy; ties go to the larger straightness, then the longer duration."""
    score, straight, dur = max((M.balanced_accuracy(y, [rule_predict(f, s, d) for f in feats]), s, d) for s, d in GRID)
    return {"straight": straight, "dur": dur, "train_balanced_accuracy": score}


def train_labels():
    path = LABELS / "train.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} does not exist")
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r.get("label") in M.CLASSES]
    if not rows:
        raise SystemExit(f"no labelled trajectories in {path}")
    return rows


def queue_rows(split):
    path = LABELS / f"queue_{split}.json"
    if not path.exists():
        raise SystemExit(f"{path} does not exist")
    return json.loads(path.read_text())["items"]


def build_runs(rows, train, seeds):
    """-> list of run dicts for the trajectories `rows`, using only `train` as labels."""
    ids = [r["id"] for r in rows]
    y_train = M.encode([r["label"] for r in train])
    tuned = tune_rule([track_features(r) for r in train], y_train)
    shares = np.bincount(y_train, minlength=len(M.CLASSES)) / len(y_train)
    feats = [track_features(r) for r in rows]

    def run(model, seed, predicted, **config):
        return {"model": model, "seed": seed, "config": config,
                "predictions": {i: M.CLASSES[int(c)] for i, c in zip(ids, predicted)}}

    runs = [run("rule_fixed", 0, [rule_predict(f) for f in feats], straight=FIXED[0], dur=FIXED[1]),
            run("rule", 0, [rule_predict(f, tuned["straight"], tuned["dur"]) for f in feats], n_train=len(train), **tuned)]
    for c, name in enumerate(M.CLASSES):
        runs.append(run(f"always_{name}", 0, [c] * len(ids)))
    for seed in range(seeds):
        uniform = np.random.default_rng([seed, 0]).integers(0, len(M.CLASSES), len(ids))
        frequency = np.random.default_rng([seed, 1]).choice(len(M.CLASSES), len(ids), p=shares)
        runs.append(run("random_uniform", seed, uniform))
        runs.append(run("random_frequency", seed, frequency, shares=shares.tolist()))
    return runs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", required=True, choices=["train", "val", "test_same_hive", "test_other_hive"])
    ap.add_argument("--seeds", type=int, default=5, help="seeds of the random baselines")
    ap.add_argument("--out", help="output directory (default outputs/baselines/<split>)")
    args = ap.parse_args(argv)
    runs = build_runs(queue_rows(args.split), train_labels(), args.seeds)
    out = OUT / args.split if args.out is None else Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for run in runs:
        (out / f"{run['model']}_s{run['seed']}.json").write_text(json.dumps(run))
    tuned = next(r for r in runs if r["model"] == "rule")["config"]
    print(f"{len(runs)} prediction files -> {out}")
    print(f"rule tuned on {tuned['n_train']} train labels: straight < {tuned['straight']}, dur > {tuned['dur']} s "
          f"(train balanced accuracy {tuned['train_balanced_accuracy']:.3f})")


if __name__ == "__main__":
    main()
