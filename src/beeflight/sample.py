"""Build the labeling queue for the web labeler (labeler/).

Draws flight tracks from outputs/flights/ for one split, stratified by self-label so that rare
curvy departures (orientation candidates) are over-represented, then shuffles them so the
labeler cannot infer the stratum from the order. Each queue item carries the full geometry,
so labels stay valid even if the tracker changes later.

With --all the remaining tracks of the split follow the sample in random order, so the local labeler
can go through everything; the first `core` items are the stratified sample (online packages, models).
With --carry, labels made on an earlier tracker version are moved to the matching new tracks; those
tracks are part of the sample.

Usage:
  beeflight-sample --split train --n 300 --all --carry labels/archive/background-v1/train.jsonl
  beeflight-sample --split val --n 80 --all
  beeflight-sample --recheck 50          # second pass on already labeled train tracks (Cohen's kappa)
"""
import argparse
import json
import random
from pathlib import Path

import numpy as np

from .splits import ROOT, SPLITS
from .tracks import TRACKER

FLIGHTS = ROOT / "outputs" / "flights"
LABELS = ROOT / "labels"
# share of the queue per stratum; leftovers of small strata are redistributed
QUOTA = {"dep_curvy": 0.30, "dep_straight": 0.15, "arrival": 0.20, "board_board": 0.15, "other": 0.20}


def stratum(r):
    if r["start"] == "board" and r["end"] == "board":
        return "board_board"
    if r["start"] == "board":
        return "dep_curvy" if r["straight"] < 0.5 and r["dur_s"] > 0.4 else "dep_straight"
    if r["end"] == "board":
        return "arrival"
    return "other"


def track_id(seq, t0, seen):
    """seq:t0, with a letter suffix when two tracks of one sequence start in the same frame."""
    base = f"{seq}:{t0}"
    n = seen.get(base, 0)
    seen[base] = n + 1
    return base if n == 0 else base + "abcdefghijklmnopqrstuvwxyz"[n]


def load(split):
    items, seen = [], {}
    for seq in SPLITS[split]:
        path = FLIGHTS / f"{seq}.json"
        if not path.exists():
            continue
        d = json.loads(path.read_text())
        for r in d["rows"]:
            items.append({
                "id": track_id(seq, r["t0"], seen), "seq": seq, "t0": r["t0"], "t1": r["t"][-1],
                "top": d["top"], "scale": d["scale"], "t": r["t"], "xy": r["xy"],
                "stratum": stratum(r),
            })
    return items


def draw(items, n, rng, forced=frozenset()):
    """Stratified sample of n items; items whose id is in `forced` are always in and count toward their stratum."""
    fixed = [i for i in items if i["id"] in forced]
    by = {k: [i for i in items if i["stratum"] == k and i["id"] not in forced] for k in QUOTA}
    for v in by.values():
        rng.shuffle(v)
    have = {k: sum(i["stratum"] == k for i in fixed) for k in QUOTA}
    take = {k: min(max(0, round(q * n) - have[k]), len(by[k])) for k, q in QUOTA.items()}
    # hand unused quota to strata that still have tracks left
    while sum(take.values()) + len(fixed) < min(n, len(items)):
        k = next(k for k in QUOTA if take[k] < len(by[k]))
        take[k] += 1
    queue = fixed + [i for k in QUOTA for i in by[k][:take[k]]]
    rng.shuffle(queue)
    return queue, {k: take[k] + have[k] for k in QUOTA}


def match(old, items, min_overlap=0.6, max_dist=6.0, max_growth=1.3):
    """New track that is the same flight as an old labeled one: shares most of its frames at the same place.

    A track that grew a lot (stitched fragments) is not matched: it may deserve another class.
    """
    best, best_overlap = None, 0.0
    old_pts = dict(zip(old["t"], map(tuple, old["xy"])))
    for it in items:
        if it["seq"] != old["seq"] or it["t1"] < old["t"][0] or it["t0"] > old["t"][-1]:
            continue
        common = [(old_pts[t], xy) for t, xy in zip(it["t"], it["xy"]) if t in old_pts]
        overlap = len(common) / len(old["t"])
        if overlap < min_overlap or len(it["t"]) > max_growth * len(old["t"]):
            continue
        dist = np.mean([np.hypot(a[0] - b[0], a[1] - b[1]) for a, b in common])
        if dist <= max_dist and overlap > best_overlap:
            best, best_overlap = it, overlap
    return best


def carry(old_path, items):
    """-> {new id: label record with the new geometry} for every old label with a matching new track."""
    out, used = {}, set()
    for old in (json.loads(line) for line in old_path.read_text().splitlines() if line.strip()):
        it = match(old, [i for i in items if i["id"] not in used])
        if it is None:
            continue
        used.add(it["id"])
        out[it["id"]] = {
            "id": it["id"], "label": old["label"], "flags": old["flags"], "note": old["note"],
            "labeled_at": old["labeled_at"], "split": old["split"], "seq": it["seq"], "t0": it["t0"],
            "tracker": TRACKER, "top": it["top"], "scale": it["scale"], "t": it["t"], "xy": it["xy"],
            "carried_from": {"id": old["id"], "tracker": old["tracker"]},
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "val", "test_same_hive", "test_other_hive"])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--recheck", type=int, help="draw N labeled train tracks for a blind second pass")
    ap.add_argument("--all", action="store_true", help="append all remaining tracks after the sample")
    ap.add_argument("--carry", type=Path, help="labels of an earlier tracker version to move to the new tracks")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    LABELS.mkdir(exist_ok=True)

    if args.recheck:
        done = [json.loads(line)["id"] for line in (LABELS / "train.jsonl").read_text().splitlines() if line]
        queue_train = {i["id"]: i for i in json.loads((LABELS / "queue_train.json").read_text())["items"]}
        ids = rng.sample(done, min(args.recheck, len(done)))
        out = {"split": "recheck", "seed": args.seed, "items": [queue_train[i] for i in ids]}
        (LABELS / "queue_recheck.json").write_text(json.dumps(out))
        print(f"recheck queue: {len(ids)} tracks -> labels/queue_recheck.json")
        return

    target = LABELS / f"queue_{args.split}.json"
    labels_path = LABELS / f"{args.split}.jsonl"
    if target.exists():
        raise SystemExit(f"{target} exists; delete it on purpose to draw a new sample")
    if args.carry and labels_path.exists():
        raise SystemExit(f"{labels_path} exists; archive it before carrying labels over")
    items = load(args.split)
    carried = carry(args.carry, items) if args.carry else {}
    queue, take = draw(items, args.n, rng, forced=set(carried))
    core = len(queue)
    if args.all:
        chosen = {i["id"] for i in queue}
        rest = [i for i in items if i["id"] not in chosen]
        rng.shuffle(rest)
        queue += rest
    target.write_text(json.dumps({"split": args.split, "seed": args.seed, "tracker": TRACKER, "core": core, "items": queue}))
    print(f"{args.split}: {len(items)} tracks available, sample of {core} first, queue of {len(queue)} -> {target.relative_to(ROOT)}")
    print("sample per stratum:", take)
    if args.carry:
        labels_path.write_text("".join(json.dumps(r) + "\n" for r in carried.values()))
        n_old = sum(1 for line in args.carry.read_text().splitlines() if line.strip())
        print(f"carried {len(carried)} of {n_old} labels -> {labels_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
