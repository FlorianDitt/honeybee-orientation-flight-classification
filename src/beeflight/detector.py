"""Two-paper tracker: ByteTrack (Zhang et al. 2022) with a YOLO bee detector, plus HyDaT's hybrid
fallback (Ratnayake et al. 2021): background-model blobs fill in where YOLO misses a bee.

Bootstrap labels come from tracker v3: every point of a v3 flight track becomes a box. Boxes are
BOX px wide, about twice a bee, so that the Kalman-predicted box still overlaps the next detection
of a fast bee (ByteTrack matches by IoU; measured on v3 tracks: 5 % of steps below IoU 0.2 with
bee-sized boxes, 0.5 % with 60 px).

In hybrid mode the v3 blobs enter ByteTrack as low-score boxes. BYTE only uses low-score boxes in its
second association, for tracks the detector lost, and never starts a track from them. That is
HyDaT's "background subtraction where the detector fails" without touching the ByteTrack code.

The detector sees the flight zone at full resolution (below the board, minus a strip for take-offs).
Output has the same format as beeflight-tracks, in outputs/flights_bytetrack/ and outputs/flights_hybrid/,
so the v3 outputs and the hand labels on them stay untouched.

Usage: beeflight-detector bootstrap                      (YOLO dataset from v3 tracks, train split)
       beeflight-detector train [--epochs 15]
       beeflight-detector track --split val [--mode bytetrack|hybrid|both] [--match iou|center|both]
       beeflight-detector compare --split val           (share of complete tracks per tracker)
"""
import argparse
import json
from contextlib import nullcontext
from types import SimpleNamespace

import av
import cv2
import numpy as np

from .splits import ROOT, SPLITS, video_path
from .tracks import BOARD, SCALE, detect, flight_rows

BOX = 60          # full-res px, box side for training labels and background blobs
STRIP = 80        # full-res px above the board's lower edge that the detector still sees (take-offs)
TILE = 640        # training tiles at full resolution; inference runs on the whole zone at IMGSZ
IMGSZ = 1088
CENTER_SCALE = 112  # px, see center_cost
BLOB_SCORE = 0.2  # background blobs: between track_low_thresh and track_high_thresh, i.e. "low score"
# Ultralytics' bytetrack.yaml defaults (the paper uses tau = 0.6 for its pedestrian detector)
BYTE = dict(tracker_type="bytetrack", track_high_thresh=0.25, track_low_thresh=0.1, new_track_thresh=0.25,
            track_buffer=30, match_thresh=0.8, fuse_score=True)
DET = ROOT / "outputs" / "detector"
WEIGHTS = DET / "bee" / "weights" / "best.pt"


def zone(seq_id):
    """Full-res row where the detector zone starts, and the half-res top row v3 coordinates refer to."""
    top, bottom = BOARD[seq_id[3:7]]
    return bottom - STRIP, int(top * SCALE)


def to_zone(xy, seq_id):
    """v3 coordinates (half res, y relative to the board top) -> full-res coordinates in the detector zone."""
    y0, top = zone(seq_id)
    xy = np.asarray(xy, float).reshape(-1, 2)
    return np.c_[xy[:, 0] / SCALE, (xy[:, 1] + top) / SCALE - y0]


def from_zone(xy, seq_id):
    y0, top = zone(seq_id)
    xy = np.asarray(xy, float).reshape(-1, 2)
    return np.c_[xy[:, 0] * SCALE, (xy[:, 1] + y0) * SCALE - top]


def color_frames(seq_id, y0, keep=None):
    with av.open(str(video_path(seq_id))) as c:
        c.streams.video[0].thread_type = "AUTO"
        for i, f in enumerate(c.decode(video=0)):
            if keep is None or i in keep:
                yield i, f.to_ndarray(format="bgr24")[y0:]


def tile_labels(centers, x0, y0, size=TILE, box=BOX):
    """YOLO label lines for the boxes around `centers` that lie at least half inside the tile."""
    lines = []
    for cx, cy in centers:
        a = np.clip([cx - box / 2 - x0, cy - box / 2 - y0], 0, size)
        b = np.clip([cx + box / 2 - x0, cy + box / 2 - y0], 0, size)
        if np.prod(b - a) < 0.5 * box * box:
            continue
        (xa, ya), (xb, yb) = a, b
        lines.append(f"0 {(xa + xb) / 2 / size:.5f} {(ya + yb) / 2 / size:.5f} {(xb - xa) / size:.5f} {(yb - ya) / size:.5f}")
    return lines


def bootstrap(every=120, seq_step=2, n_val=4, empty_frac=0.15, seed=0):
    """Tiles of the flight zone with v3 track points as boxes; every other training sequence, every 2 s."""
    rng = np.random.default_rng(seed)
    seqs = [s for s in SPLITS["train"][::seq_step] if video_path(s).exists()]
    out = DET / "dataset"
    n = {"train": 0, "val": 0, "boxes": 0}
    for k, seq_id in enumerate(seqs):
        part = "val" if k >= len(seqs) - n_val else "train"
        (out / "images" / part).mkdir(parents=True, exist_ok=True)
        (out / "labels" / part).mkdir(parents=True, exist_ok=True)
        rows = json.loads((ROOT / "outputs" / "flights" / f"{seq_id}.json").read_text())["rows"]
        pts = {}
        for r in rows:
            for t, xy in zip(r["t"], to_zone(r["xy"], seq_id)):
                pts.setdefault(t, []).append(xy)
        y0, _ = zone(seq_id)
        keep = set(range(every // 2, 1800, every))
        for i, img in color_frames(seq_id, y0, keep):
            h, w = img.shape[:2]
            for x0 in (0, w - TILE):
                for ty in (0, h - TILE):
                    lines = tile_labels(pts.get(i, []), x0, ty)
                    if not lines and rng.random() > empty_frac:
                        continue
                    name = f"{seq_id}_f{i:04d}_x{x0}_y{ty}"
                    cv2.imwrite(str(out / "images" / part / f"{name}.jpg"), img[ty:ty + TILE, x0:x0 + TILE])
                    (out / "labels" / part / f"{name}.txt").write_text("\n".join(lines))
                    n[part] += 1
                    n["boxes"] += len(lines)
        print(f"{seq_id} ({part}): {n['train']} train / {n['val']} val tiles, {n['boxes']} boxes", flush=True)
    (out / "data.yaml").write_text(f"path: {out}\ntrain: images/train\nval: images/val\nnames:\n  0: bee\n")


def train(epochs=15, batch=16):
    from ultralytics import YOLO

    YOLO("yolo11n.pt").train(data=str(DET / "dataset" / "data.yaml"), imgsz=TILE, epochs=epochs, batch=batch,
                             device="cpu", workers=4, project=str(DET), name="bee", exist_ok=True,
                             flipud=0.5, mosaic=1.0, plots=True)


def yolo_detections(seq_id, model):
    """Per frame: rows (x1, y1, x2, y2, conf) in zone coordinates. Cached, both modes reuse them."""
    cache = DET / "detections" / f"{seq_id}.npz"
    if cache.exists():
        d = np.load(cache)
        return [d["boxes"][d["frame"] == i] for i in range(int(d["n"]))]
    y0, _ = zone(seq_id)
    out = []
    for _, img in color_frames(seq_id, y0):
        b = model.predict(img, imgsz=IMGSZ, conf=BYTE["track_low_thresh"], device="cpu", verbose=False)[0].boxes
        out.append(np.c_[b.xyxy.numpy(), b.conf.numpy()].reshape(-1, 5))
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, boxes=np.concatenate(out), frame=np.repeat(np.arange(len(out)), [len(o) for o in out]),
                        n=len(out))
    return out


def blob_boxes(seq_id, yolo):
    """v3 background blobs as BOX-sized low-score boxes, except where YOLO already has a box."""
    y0, top = zone(seq_id)
    dets, _, _ = detect(seq_id, top)
    out = []
    for d, yb in zip(dets, yolo):
        c = to_zone(d[:, :2], seq_id) if len(d) else np.zeros((0, 2))
        c = c[c[:, 1] >= 0]
        if len(yb):
            inside = ((c[:, None, 0] >= yb[None, :, 0]) & (c[:, None, 0] <= yb[None, :, 2])
                      & (c[:, None, 1] >= yb[None, :, 1]) & (c[:, None, 1] <= yb[None, :, 3])).any(1)
            c = c[~inside]
        out.append(np.c_[c - BOX / 2, c + BOX / 2, np.full(len(c), BLOB_SCORE)].reshape(-1, 5))
    return out


def center_cost(tracks, dets):
    """Drop-in for ByteTrack's IoU cost: distance between box centers, scaled so that the tracker's own
    thresholds (0.8 first, 0.7 unconfirmed, 0.5 second association) become 90, 78 and 56 px."""
    if not len(tracks) or not len(dets):
        return np.zeros((len(tracks), len(dets)))
    a = np.array([t.xywh[:2] for t in tracks])
    b = np.array([d.xywh[:2] for d in dets])
    return np.minimum(np.linalg.norm(a[:, None] - b[None], axis=2) / CENTER_SCALE, 1.0)


def byte_track(per_frame, shape, match="iou"):
    """Run Ultralytics' BYTETracker; returns tracks as (t, x, y) arrays in zone coordinates.

    match="center" swaps only the cost function (all three associations), the BYTE logic stays as it is.
    A new track has no velocity yet, so with IoU a fast bee has left its box before it is confirmed.
    """
    from unittest.mock import patch

    from ultralytics.engine.results import Boxes
    from ultralytics.trackers.byte_tracker import BYTETracker, matching

    tracker = BYTETracker(SimpleNamespace(**BYTE))
    pts = {}
    with patch.object(matching, "iou_distance", center_cost) if match == "center" else nullcontext():
        for t, d in enumerate(per_frame):
            boxes = Boxes(np.c_[d, np.zeros(len(d))].reshape(-1, 6), shape)
            for x1, y1, x2, y2, tid, *_ in tracker.update(boxes):
                pts.setdefault(int(tid), []).append((t, (x1 + x2) / 2, (y1 + y2) / 2))
    return [np.array(p) for p in pts.values()]


def track_seq(seq_id, model, modes, matches=("iou",)):
    y0, top = zone(seq_id)
    yolo = yolo_detections(seq_id, model)
    shape_full = (1920 - y0, 1080)
    shape_v3 = (int(1920 * SCALE) - top, int(1080 * SCALE))
    board_bottom = int(BOARD[seq_id[3:7]][1] * SCALE) - top
    blobs = blob_boxes(seq_id, yolo) if "hybrid" in modes else None
    for mode in modes:
        per_frame = yolo if mode == "bytetrack" else [np.r_[a, b] for a, b in zip(yolo, blobs)]
        for match in matches:
            name = mode + ("_center" if match == "center" else "")
            raw = [np.c_[p[:, 0], from_zone(p[:, 1:], seq_id)] for p in byte_track(per_frame, shape_full, match)]
            rows = flight_rows(raw, shape_v3, board_bottom)
            out = ROOT / "outputs" / f"flights_{name}"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{seq_id}.json").write_text(json.dumps({"seq": seq_id, "tracker": name, "top": top,
                                                            "scale": SCALE, "rows": rows}))
            done = sum("lost" not in (r["start"], r["end"]) for r in rows)
            print(f"{seq_id} {name}: {len(rows)} flight tracks, {done} complete", flush=True)


def compare(seqs, folders=("flights", "flights_bytetrack", "flights_hybrid", "flights_bytetrack_center",
                           "flights_hybrid_center")):
    """Share of complete tracks (no end in the grass), overall and for loopy vs other flights."""
    print(f"{'tracker':26s} {'tracks':>7s} {'complete':>9s} {'share':>6s} {'loopy':>6s} {'other':>6s}")
    for folder in folders:
        files = [ROOT / "outputs" / folder / f"{s}.json" for s in seqs]
        if not all(f.exists() for f in files):
            print(f"{folder:26s} missing for some sequences")
            continue
        rows = [r for f in files for r in json.loads(f.read_text())["rows"]]
        ok = np.array(["lost" not in (r["start"], r["end"]) for r in rows])
        loopy = np.array([r["abs_turn_deg"] > 360 for r in rows])
        print(f"{folder:26s} {len(rows):7d} {ok.sum():9d} {100 * ok.mean():5.1f}% "
              f"{100 * ok[loopy].mean():5.1f}% {100 * ok[~loopy].mean():5.1f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bootstrap", "train", "track", "compare"])
    ap.add_argument("seqs", nargs="*")
    ap.add_argument("--split", action="append", choices=list(SPLITS), default=[])
    ap.add_argument("--mode", choices=["bytetrack", "hybrid", "both"], default="both")
    ap.add_argument("--match", choices=["iou", "center", "both"], default="iou")
    ap.add_argument("--epochs", type=int, default=15)
    args = ap.parse_args()
    seqs = args.seqs + [s for name in args.split for s in SPLITS[name]]
    if args.cmd == "bootstrap":
        bootstrap()
    elif args.cmd == "train":
        train(args.epochs)
    elif args.cmd == "track":
        from ultralytics import YOLO

        model = YOLO(str(WEIGHTS))
        modes = ["bytetrack", "hybrid"] if args.mode == "both" else [args.mode]
        for seq_id in seqs:
            track_seq(seq_id, model, modes, ["iou", "center"] if args.match == "both" else [args.match])
    else:
        compare(seqs)


if __name__ == "__main__":
    main()
