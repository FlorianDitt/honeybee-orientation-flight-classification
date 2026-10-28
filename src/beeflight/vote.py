"""Merge the owner's labels with the exports of friends into one final label per track.

Votes come from labels/<split>.jsonl (the owner, local labeler) and every file in labels/votes/
(exports of the web labeler, one annotator per file, newest label per track wins). Rules:

- strict majority of the votes decides the class (2 of 3, 3 of 4, ...)
- no majority: the owner's label decides and the track gets the flag `strittig`
- no majority and no owner vote: the track stays open
- a flag (fragment, unsicher) is kept if at least half of the voters set it

Writes labels/final_<split>.jsonl with the geometry from the queue and prints agreement
(Krippendorff's alpha, nominal) plus per-annotator practice score and agreement with the majority.

Usage: beeflight-vote [--min-votes 3] [--owner florian]
"""
import argparse
import json
from collections import Counter, defaultdict

from .splits import ROOT

LABELS = ROOT / "labels"
VOTES = LABELS / "votes"
SPLITS = ["train", "val"]
FLAGS = ["fragment", "unsicher"]


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def collect(owner):
    """-> votes[split][id][annotator] = record, practice[annotator][id] = label"""
    votes = {s: defaultdict(dict) for s in SPLITS}
    practice = defaultdict(dict)
    for s in SPLITS:
        path = LABELS / f"{s}.jsonl"
        if path.exists():
            for r in read_jsonl(path):
                votes[s][r["id"]][owner] = r
    for path in sorted(VOTES.glob("*.jsonl")) if VOTES.exists() else []:
        for r in read_jsonl(path):
            who = r.get("annotator", "").strip().lower() or path.stem
            if who == owner:
                continue  # the owner's labels come from the local labeler only
            if r.get("practice"):
                practice[who][r["id"]] = r["label"]
            elif r.get("split") in votes:
                old = votes[r["split"]][r["id"]].get(who)
                if old is None or old["labeled_at"] < r["labeled_at"]:
                    votes[r["split"]][r["id"]][who] = r
    return votes, practice


def decide(by_annotator, owner):
    counts = Counter(r["label"] for r in by_annotator.values())
    n = sum(counts.values())
    (top, c), *rest = counts.most_common()
    flags = [f for f in FLAGS if 2 * sum(f in r["flags"] for r in by_annotator.values()) >= n]
    if 2 * c > n:
        return top, flags, "majority"
    if owner in by_annotator:
        return by_annotator[owner]["label"], flags + ["strittig"], "owner"
    return None, flags, "open"


def krippendorff_alpha(units):
    """Nominal alpha for units = [[label, label, ...], ...]; units with fewer than two values are ignored."""
    o = Counter()
    for values in units:
        m = len(values)
        if m < 2:
            continue
        for i, a in enumerate(values):
            for j, b in enumerate(values):
                if i != j:
                    o[a, b] += 1 / (m - 1)
    n_c = Counter()
    for (a, _), v in o.items():
        n_c[a] += v
    n = sum(n_c.values())
    if n <= 1:
        return float("nan")
    d_o = sum(v for (a, b), v in o.items() if a != b)
    d_e = sum(n_c[a] * n_c[b] for a in n_c for b in n_c if a != b) / (n - 1)
    return 1.0 if d_e == 0 else 1 - d_o / d_e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default="florian", help="annotator name of the local labels")
    ap.add_argument("--min-votes", type=int, default=3, help="tracks with fewer votes are reported, not written")
    args = ap.parse_args()
    owner = args.owner.lower()
    votes, practice = collect(owner)
    answers = {p["id"]: p["answer"] for p in json.loads((LABELS / "practice.json").read_text())["items"]} \
        if (LABELS / "practice.json").exists() else {}

    agree = defaultdict(lambda: [0, 0])
    for s in SPLITS:
        queue = {i["id"]: i for i in json.loads((LABELS / f"queue_{s}.json").read_text())["items"]}
        out, status, short = [], Counter(), 0
        for tid, by in votes[s].items():
            if tid not in queue:
                continue
            if tid in answers:  # practice tracks: only the owner labels them for real
                by = {k: v for k, v in by.items() if k == owner}
            if len(by) < args.min_votes and tid not in answers:
                short += 1
                continue
            label, flags, how = decide(by, owner)
            status[how] += 1
            if label is None:
                continue
            for who, r in by.items():
                if len(by) >= 3:
                    agree[who][0] += r["label"] == label
                    agree[who][1] += 1
            q = queue[tid]
            out.append({"id": tid, "label": label, "flags": flags, "decided_by": how,
                        "votes": {who: r["label"] for who, r in sorted(by.items())},
                        "split": s, "seq": q["seq"], "t0": q["t0"], "top": q["top"], "scale": q["scale"],
                        "t": q["t"], "xy": q["xy"]})
        (LABELS / f"final_{s}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in out))
        n_votes = Counter(len(by) for tid, by in votes[s].items() if tid in queue)
        alpha = krippendorff_alpha([[r["label"] for r in by.values()] for by in votes[s].values()])
        print(f"\n{s}: {len(queue)} tracks in queue, votes per track {dict(sorted(n_votes.items()))}")
        print(f"  final: {len(out)} -> labels/final_{s}.jsonl  ({dict(status)}; {short} with < {args.min_votes} votes)")
        print(f"  classes: {dict(Counter(r['label'] for r in out))}")
        print(f"  Krippendorff's alpha (nominal): {alpha:.3f}")

    print("\nannotator      practice   agrees with final (tracks with >= 3 votes)")
    for who in sorted(set(agree) | set(practice)):
        p = practice.get(who, {})
        right = sum(answers.get(i) == lab for i, lab in p.items())
        pr = f"{right}/{len(p)}" if p else "-"
        a, n = agree.get(who, (0, 0))
        print(f"  {who:<12} {pr:>8}   {f'{a}/{n} = {a / n:.0%}' if n else '-'}")


if __name__ == "__main__":
    main()
