"""Export the label queues as short cropped clips for the static labeler on GitHub Pages.

The full videos (about 100 MB each) cannot be hosted on Pages, so every track of the sample
(the first `core` items of a queue) becomes a clip of
its own: the track plus 20 frames before and after, cropped to the wide view box of the local labeler
and scaled down to at most 720 px. A still of the full frame serves as the overview. The clips go to
labeler/public-web/ (not versioned); `npm run deploy:web` in labeler/ publishes them.

Friends start with a practice round on tracks the owner labeled without flags; those tracks are
fixed once in labels/practice.json and left out of the packages, so nobody labels them twice.
The tutorial (labels/tutorial.json: example tracks per class with an explanation) replaces the practice
round on the site; its tracks get clips too and are taken out of their package afterwards, so the other
tracks keep their package.

Only the chosen splits become packages, by default the two test sets: their labels decide the reported result, so
that is where independent votes count most. Packages are just called "Paket 1", "Paket 2", ... because helpers need
not know which set they work on; the train queue is still read for the tutorial and practice tracks.

With --skip-voted, tracks that a helper already labeled (labels/votes/*.jsonl, moved to the current
tracks through the id maps) stay out of the packages, so the packages hold only tracks they have not seen.

Usage: beeflight-clips                 # test_same_hive + test_other_hive
       beeflight-clips --split train --split val --skip-voted
       beeflight-clips --force
"""
import argparse
import json
import math
import random
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction

import av
import cv2

from .splits import ROOT, video_path

LABELS = ROOT / "labels"
WEB = ROOT / "labeler" / "public-web"
FPS = Fraction(60000, 1001)
W, H = 1080, 1920
PAD = 20
CLIP_MAX = 720
# same as fitBox() in labeler/src/lib/player.ts, wide setting
MARGIN_WIDE, MIN_BOX = 260, 240
OVERVIEW = (216, 384)
PACKAGE = 50
PRACTICE = {"orientierung": 3, "sammelabflug": 3, "anflug": 2, "artefakt": 2}
TEST = ["test_same_hive", "test_other_hive"]


def full_res(item):
    return [[x / item["scale"], (y + item["top"]) / item["scale"]] for x, y in item["xy"]]


def wide_box(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1 = min(xs) - MARGIN_WIDE, max(xs) + MARGIN_WIDE
    y0, y1 = min(ys) - MARGIN_WIDE, max(ys) + MARGIN_WIDE
    s = min(W, math.ceil(max(MIN_BOX, x1 - x0, y1 - y0)))
    s += s % 2  # even size for yuv420
    x = round(min(max(0, (x0 + x1) / 2 - s / 2), W - s))
    y = round(min(max(0, (y0 + y1) / 2 - s / 2), H - s))
    return {"x": x, "y": y, "s": s}


def clip_name(item_id):
    return item_id.replace(":", "_")


def plan(item):
    start, end = max(0, item["t0"] - PAD), min(1799, item["t1"] + PAD)
    pts = full_res(item)
    region = wide_box(pts)
    size = min(CLIP_MAX, region["s"])
    size -= size % 2
    return {
        "id": item["id"], "seq": item["seq"], "t0": item["t0"], "t1": item["t1"], "t": item["t"],
        "pts": [[round(x, 1), round(y, 1)] for x, y in pts],
        "offset": start, "last": end, "region": region, "k": size / region["s"],
        "clip": f"clips/{clip_name(item['id'])}.mp4", "still": f"clips/{clip_name(item['id'])}.jpg",
    }


def export_seq(seq, entries, force):
    """Decode one video once and write the clips of all its queued tracks."""
    todo = [e for e in entries if force or not (WEB / e["clip"]).exists()]
    if not todo:
        return seq, 0
    open_ = {}
    end = max(e["last"] for e in todo)
    with av.open(str(video_path(seq))) as src:
        src.streams.video[0].thread_type = "AUTO"
        for f, frame in enumerate(src.decode(video=0)):
            if f > end:
                break
            active = [e for e in todo if e["offset"] <= f <= e["last"]]
            if not active:
                continue
            rgb = frame.to_ndarray(format="rgb24")
            for e in active:
                if e["id"] not in open_:
                    open_[e["id"]] = writer(e)
                r, size = e["region"], round(e["k"] * e["region"]["s"])
                crop = rgb[r["y"]:r["y"] + r["s"], r["x"]:r["x"] + r["s"]]
                if size != r["s"]:
                    crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
                out, stream, n = open_[e["id"]]
                vf = av.VideoFrame.from_ndarray(crop, format="rgb24")
                vf.pts = n
                for pkt in stream.encode(vf):
                    out.mux(pkt)
                open_[e["id"]] = (out, stream, n + 1)
                if f == e["t0"]:
                    still = cv2.resize(rgb, OVERVIEW, interpolation=cv2.INTER_AREA)
                    cv2.imwrite(str(WEB / e["still"]), cv2.cvtColor(still, cv2.COLOR_RGB2BGR),
                                [cv2.IMWRITE_JPEG_QUALITY, 82])
                if f == e["last"]:
                    close(*open_.pop(e["id"])[:2])
    for out, stream, _ in open_.values():
        close(out, stream)
    return seq, len(todo)


def writer(e):
    out = av.open(str(WEB / e["clip"]), "w", options={"movflags": "+faststart"})
    size = round(e["k"] * e["region"]["s"])
    stream = out.add_stream("libx264", rate=FPS)
    stream.width = stream.height = size
    stream.pix_fmt = "yuv420p"
    stream.time_base = 1 / FPS
    stream.options = {"crf": "24", "preset": "medium", "g": "30"}
    return out, stream, 0


def close(out, stream):
    for pkt in stream.encode():
        out.mux(pkt)
    out.close()


def practice_ids(queue_train):
    """Pick the practice tracks once from the owner's confident train labels and keep them fixed."""
    path = LABELS / "practice.json"
    if path.exists():
        return json.loads(path.read_text())["items"]
    queued = {i["id"] for i in queue_train}
    labels = [json.loads(line) for line in (LABELS / "train.jsonl").read_text().splitlines() if line]
    sure = [r for r in labels if not r["flags"] and r["id"] in queued]
    rng = random.Random(0)
    picks = []
    for cls, n in PRACTICE.items():
        pool = [r for r in sure if r["label"] == cls]
        picks += rng.sample(pool, min(n, len(pool)))
    # a class with too few confident labels: fill up from the others
    rest = [r for r in sure if r not in picks]
    picks += rng.sample(rest, min(sum(PRACTICE.values()) - len(picks), len(rest)))
    rng.shuffle(picks)
    items = [{"id": r["id"], "answer": r["label"]} for r in picks]
    path.write_text(json.dumps({"source": "labels/train.jsonl", "items": items}, indent=1) + "\n")
    print(f"practice: {len(items)} tracks fixed in labels/practice.json")
    return items


def voted_ids(tracker, id_map):
    """Ids of the current tracks that some helper already labeled or saw in the practice round (labels/votes/)."""
    out = set()
    for path in sorted((LABELS / "votes").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)  # practice tracks count too: they have been seen
            made_on = r.get("tracker") or "background-v3"
            out.add(r["id"] if made_on == tracker else id_map.get(made_on, {}).get(r["id"]))
    out.discard(None)
    print(f"skip-voted: {len(out)} tracks already labeled by helpers")
    return out


def packages(split, queue, skip, first=1):
    ids = [i["id"] for i in queue if i["id"] not in skip]
    n = math.ceil(len(ids) / PACKAGE)
    bounds = [round(k * len(ids) / n) for k in range(n + 1)]
    return [{"id": f"paket-{first + k}", "split": split, "name": f"Paket {first + k}",
             "items": ids[bounds[k]:bounds[k + 1]]} for k in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", action="append", choices=["train", "val", *TEST], help="splits that become packages (default: both test sets)")
    ap.add_argument("--force", action="store_true", help="re-encode existing clips")
    ap.add_argument("--workers", type=int, default=3, help="parallel videos (about 1 GB RAM each)")
    ap.add_argument("--skip-voted", action="store_true", help="leave tracks that helpers already labeled out of the packages")
    args = ap.parse_args()
    splits = args.split or TEST
    known = list(dict.fromkeys(["train", "val", *splits]))
    (WEB / "clips").mkdir(parents=True, exist_ok=True)
    (WEB / "data").mkdir(exist_ok=True)

    queues, trackers, id_map = {}, set(), {}
    for s in known:
        if not (LABELS / f"queue_{s}.json").exists():
            raise SystemExit(f"labels/queue_{s}.json missing (beeflight-sample --split {s} ...)")
        q = json.loads((LABELS / f"queue_{s}.json").read_text())
        queues[s] = q["items"][:q.get("core", len(q["items"]))]  # online only the stratified sample
        trackers.add(q.get("tracker", "background-v3"))
        # after a tracker change the browsers of friends rename their labels with this map (webstore.ts)
        path = LABELS / f"id_map_{s}.json"
        if path.exists():
            d = json.loads(path.read_text())
            id_map.setdefault(d["from"], {}).update(d["map"])
    if len(trackers) > 1:
        raise SystemExit(f"queues come from different trackers: {sorted(trackers)}")
    tracker = trackers.pop()
    practice = practice_ids(queues["train"])
    skip = {p["id"] for p in practice}
    tutorial = json.loads((LABELS / "tutorial.json").read_text())["items"]
    voted = voted_ids(tracker, id_map) if args.skip_voted else set()
    items, pkgs = {}, []
    for s in splits:
        for i in queues[s]:
            items[i["id"]] = {**plan(i), "split": s}
        pkgs += packages(s, queues[s], skip | voted, first=len(pkgs) + 1)
    shown = {t["id"] for t in tutorial}
    for p in pkgs:  # the answer of a tutorial track is shown, so nobody labels it
        p["items"] = [i for i in p["items"] if i not in shown]
    for s in known:  # tutorial and practice tracks may lie outside the packaged splits
        full = json.loads((LABELS / f"queue_{s}.json").read_text())["items"]
        for i in full:
            if i["id"] in shown | skip and i["id"] not in items:
                items[i["id"]] = {**plan(i), "split": s}
    if missing_tut := shown - set(items):
        raise SystemExit(f"tutorial tracks not in any queue: {sorted(missing_tut)}")
    skip |= shown

    by_seq = {}
    for e in items.values():
        by_seq.setdefault(e["seq"], []).append(e)
    missing = [s for s in by_seq if not video_path(s).exists()]
    if missing:
        raise SystemExit(f"videos missing: {', '.join(missing)} (beeflight-splits --download ...)")
    with ProcessPoolExecutor(args.workers) as pool:
        jobs = [pool.submit(export_seq, seq, es, args.force) for seq, es in sorted(by_seq.items())]
        for k, job in enumerate(jobs, 1):
            seq, n = job.result()
            print(f"[{k}/{len(jobs)}] {seq}: {n} clips")

    site = {"version": 1, "tracker": tracker, "id_map": id_map, "fps": [FPS.numerator, FPS.denominator],
            "frame": [W, H], "items": items, "packages": pkgs, "practice": practice, "tutorial": tutorial}
    (WEB / "data" / "site.json").write_text(json.dumps(site, separators=(",", ":")))
    used = {e["clip"].split("/")[1] for e in items.values()} | {e["still"].split("/")[1] for e in items.values()}
    stale = [p for p in (WEB / "clips").iterdir() if p.name not in used]
    for p in stale:  # clips of an earlier queue; their names may come back for other flights
        p.unlink()
    size = sum(p.stat().st_size for p in (WEB / "clips").iterdir()) / 1e6
    print(f"{len(items)} tracks ({tracker}), {len(pkgs)} packages, {len(practice)} practice -> labeler/public-web ({size:.0f} MB)")


if __name__ == "__main__":
    main()
