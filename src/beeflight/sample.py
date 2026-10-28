"""Build the labeling queue for the web labeler (labeler/).

Draws flight tracks from outputs/flights/ for one split, stratified by self-label so that rare
curvy departures (orientation candidates) are over-represented, then shuffles them so the
labeler cannot infer the stratum from the order. Each queue item carries the full geometry,
so labels stay valid even if the tracker changes later.

Usage:
  beeflight-sample --split train --n 300
  beeflight-sample --split val --n 80
  beeflight-sample --recheck 50          # second pass on already labeled train tracks (Cohen's kappa)
"""
import argparse
import json
import random

from .splits import ROOT, SPLITS

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


def draw(items, n, rng):
    by = {k: [i for i in items if i["stratum"] == k] for k in QUOTA}
    for v in by.values():
        rng.shuffle(v)
    want = {k: round(q * n) for k, q in QUOTA.items()}
    take = {k: min(want[k], len(by[k])) for k in QUOTA}
    # hand unused quota to strata that still have tracks left
    while sum(take.values()) < min(n, len(items)):
        open_ = [k for k in QUOTA if take[k] < len(by[k])]
        take[open_[0]] += 1
        open_.append(open_.pop(0))
    queue = [i for k in QUOTA for i in by[k][:take[k]]]
    rng.shuffle(queue)
    return queue, take


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "val", "test_same_hive", "test_other_hive"])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--recheck", type=int, help="draw N labeled train tracks for a blind second pass")
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
    if target.exists():
        raise SystemExit(f"{target} exists; delete it on purpose to draw a new sample")
    items = load(args.split)
    queue, take = draw(items, args.n, rng)
    target.write_text(json.dumps({"split": args.split, "seed": args.seed, "items": queue}))
    print(f"{args.split}: {len(items)} tracks available, queue of {len(queue)} -> {target.relative_to(ROOT)}")
    print("per stratum:", take)


if __name__ == "__main__":
    main()
