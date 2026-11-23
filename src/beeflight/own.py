"""Write the owner's own labels from the online labeler into labels/<split>.jsonl.

The packages "Eigene Train …" / "Eigene Validierung …" (beeflight-clips --own) let the owner label train and val
tracks on GitHub Pages when the local labeler is too slow (remote connection). Their export is a file like the
helpers' exports, but it must not land in labels/votes/ as an extra vote: these are the owner's labels. This
script adds the geometry from the queue and writes every train / val label like the local labeler does; an
existing label of the same track is replaced only by a newer one.

Usage: beeflight-own beeflight_florian_2026-11-10.jsonl [--dry-run]
       beeflight-own <export> --test   # after the freeze: only the test sets -> labels/test_*.jsonl (for beeflight-vote --test)
"""
import argparse
import json
import os
from pathlib import Path

from .splits import ROOT

LABELS = ROOT / "labels"
SPLITS = ["train", "val", "recheck", "recheck_val"]  # recheck*: blind second pass, own result files
TEST_SPLITS = ["test_same_hive", "test_other_hive"]  # only with --test, after the model is frozen
CLASSES = {"orientierung", "sammelabflug", "anflug", "artefakt"}


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export", type=Path, help="export file of the online labeler")
    ap.add_argument("--dry-run", action="store_true", help="only count, write nothing")
    ap.add_argument("--test", action="store_true", help="only the test sets (and nothing else); after the freeze")
    args = ap.parse_args()
    splits = TEST_SPLITS if args.test else SPLITS
    recs = [r for r in read_jsonl(args.export) if not r.get("practice") and r.get("split") in splits]
    if not recs:
        raise SystemExit(f"no labels of {', '.join(splits)} in the file")
    for s in splits:
        mine = [r for r in recs if r["split"] == s]
        if not mine:
            continue
        queue = json.loads((LABELS / f"queue_{s}.json").read_text())
        tracker, items = queue["tracker"], {i["id"]: i for i in queue["items"]}
        path = LABELS / f"{s}.jsonl"
        all_ = {r["id"]: r for r in read_jsonl(path)}
        added = replaced = kept = 0
        for r in mine:
            if r.get("tracker") != tracker:
                raise SystemExit(f"{r['id']}: labeled on tracker {r.get('tracker')}, queue is {tracker}")
            if r["id"] not in items or r["label"] not in CLASSES:
                raise SystemExit(f"{r['id']}: not in labels/queue_{s}.json or unknown class {r['label']}")
            old = all_.get(r["id"])
            if old and old["labeled_at"] >= r["labeled_at"]:
                kept += 1
                continue
            i = items[r["id"]]
            rec = {"id": r["id"], "label": r["label"], "flags": r.get("flags", []), "note": r.get("note", "")}
            if r.get("reason"):
                rec["reason"] = r["reason"]
            rec |= {"labeled_at": r["labeled_at"], "split": s, "seq": i["seq"], "t0": i["t0"], "tracker": tracker,
                    "top": i["top"], "scale": i["scale"], "t": i["t"], "xy": i["xy"], "source": "online"}
            all_[r["id"]] = rec
            replaced += old is not None
            added += old is None
        print(f"{s}: {added} new, {replaced} replaced, {kept} kept (local label is newer) -> {len(all_)} labels")
        if not args.dry_run:
            tmp = path.with_suffix(".jsonl.tmp")
            tmp.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in all_.values()))
            os.replace(tmp, path)


if __name__ == "__main__":
    main()
