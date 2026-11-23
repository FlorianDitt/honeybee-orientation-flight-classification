"""Is there a honey bee on the track? Labels for a pre-classifier in front of the track classifier.

Idea (Florian, 19.11.2026): many artefakt tracks show no bee at all (grass, shadow) or another insect; a detector
in front of the classifier could send those straight to artefakt. YOLO (Darian) and BioCLIP zero-shot were tested on
val first (BioCLIP fails at ~30 px). This module prepares the labels for an own pre-classifier.

sample: every artefakt track of labels/train.jsonl and labels/val.jsonl (test is never read). Per track a strip of
        K full-resolution crops at evenly spaced track points, as one PNG in outputs/biene/crops/, the order
        shuffled; queue in labels/biene_queue.json.
label:  local labeler, page /biene: honigbiene / anderes_insekt / kein_tier / unklar, stored in labels/biene.jsonl.
count:  how many of each answer, per split.

Usage: python -m beeflight.biene sample [--k 8 --seed 0] | count
"""
import argparse
import json
import random
from collections import Counter, defaultdict

import av
import cv2
import numpy as np

from .splits import ROOT, video_path

OUT = ROOT / "outputs" / "biene" / "crops"
QUEUE = ROOT / "labels" / "biene_queue.json"
LABELS = ROOT / "labels" / "biene.jsonl"
SPLITS = ("train", "val")
CROP = 96  # full-res px around the track point; a bee is ~30 px long
ANSWERS = ("honigbiene", "anderes_insekt", "kein_tier", "unklar")


def artefakte():
    out = []
    for s in SPLITS:
        for line in (ROOT / "labels" / f"{s}.jsonl").read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("label") == "artefakt":
                    out.append({**r, "split": s})
    return out


def sample(args):
    rows = artefakte()
    OUT.mkdir(parents=True, exist_ok=True)
    by_seq = defaultdict(list)
    for r in rows:
        by_seq[r["seq"]].append(r)
    items = []
    for n, (seq, rs) in enumerate(sorted(by_seq.items()), 1):
        want = defaultdict(list)  # frame -> [(row id, slot, x, y)]
        for r in rs:
            for slot, j in enumerate(np.linspace(0, len(r["t"]) - 1, args.k).round().astype(int)):
                x, y = r["xy"][j]
                want[r["t"][j]].append((r["id"], slot, x / r["scale"], (y + r["top"]) / r["scale"]))
        strips = {r["id"]: np.zeros((CROP, CROP * args.k, 3), np.uint8) for r in rs}
        with av.open(str(video_path(seq))) as c:
            c.streams.video[0].thread_type = "AUTO"
            for k, f in enumerate(c.decode(video=0)):
                if k not in want:
                    continue
                img = f.to_ndarray(format="bgr24")
                h, w = img.shape[:2]
                for rid, slot, x, y in want[k]:
                    x0 = min(max(int(round(x - CROP / 2)), 0), w - CROP)
                    y0 = min(max(int(round(y - CROP / 2)), 0), h - CROP)
                    strips[rid][:, slot * CROP:(slot + 1) * CROP] = img[y0:y0 + CROP, x0:x0 + CROP]
        for r in rs:
            name = r["id"].replace(":", "_")
            cv2.imwrite(str(OUT / f"{name}.png"), strips[r["id"]])
            items.append({"id": r["id"], "name": name, "split": r["split"], "seq": seq,
                          "frames": len(r["t"])})
        print(f"[{n}/{len(by_seq)}] {seq}: {len(rs)} tracks", flush=True)
    random.Random(args.seed).shuffle(items)
    QUEUE.write_text(json.dumps({"crop": CROP, "k": args.k, "answers": ANSWERS, "items": items}))
    print(f"{len(items)} tracks -> {QUEUE.relative_to(ROOT)}, strips in {OUT.relative_to(ROOT)}")


def count(_args):
    q = {i["id"]: i for i in json.loads(QUEUE.read_text())["items"]}
    labels = [json.loads(line) for line in LABELS.read_text().splitlines() if line.strip()] if LABELS.exists() else []
    c = Counter((q[r["id"]]["split"], r["answer"]) for r in labels if r["id"] in q)
    print(f"{len(labels)} of {len(q)} labeled")
    for s in SPLITS:
        print(s, {a: c[(s, a)] for a in ANSWERS})


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--k", type=int, default=8)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--force", action="store_true")
    sub.add_parser("count")
    a = ap.parse_args()
    if a.cmd == "sample":
        if QUEUE.exists() and not a.force:
            raise SystemExit(f"{QUEUE.relative_to(ROOT)} exists; --force draws a new sample")
        sample(a)
    else:
        count(a)


if __name__ == "__main__":
    main()
