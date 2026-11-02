"""SORT (Bewley et al. 2016, arXiv 1602.00763) on the background-subtraction blobs of tracker v3.

Only the tracking step differs from v3: detection, stitching and features are the same, so the comparison
isolates the tracker. SORT as published, with one change: the association cost is the distance between the
Kalman-predicted center and the detection instead of 1 - IoU, because fast bees near the camera move more than a
box width per frame (see docs/roadmap.md, ByteTrack ablation). Blobs have no box, so the state's scale is the
blob area and the aspect ratio is fixed at 1.

Variants (VARIANTS):
- sort:     the published settings (a track is deleted after 1 missed frame, velocity noise 0.01)
- sort_bee: three changes for bees, each one measured on validation (docs/roadmap.md):
            tracks survive 5 missed frames (as v3), velocity noise 1 (a bee turns within a few frames, a
            pedestrian does not), and no new track within 20 px of a detection just assigned (a wing or shadow
            blob of the same bee, as v3)
(Chiron et al. 2013 with SORT, on Chiron's own detection, is in chiron.py.)

Usage: beeflight-sort track --split val [--board]   (writes outputs/flights_sort[_bee][_board]/)
       beeflight-sort compare --split val
"""
import argparse
import json

import numpy as np
from scipy.optimize import linear_sum_assignment

from .splits import ROOT, SPLITS, video_path
from .tracks import BOARD, SCALE, detect, flight_rows

CACHE = ROOT / "outputs" / "blobs"
GATE = 45.0  # half-res px, same gate as v3
VARIANTS = {"sort": dict(max_age=1, q_vel=0.01, birth_gap=0.0),
            "sort_bee": dict(max_age=5, q_vel=1.0, birth_gap=20.0)}

# constant-velocity model of SORT: state (u, v, s, r, u', v', s'), measurement (u, v, s, r)
F = np.eye(7) + np.eye(7, k=4)
H = np.eye(4, 7)


class KalmanTrack:
    """Noise settings as in the SORT reference implementation (KalmanBoxTracker)."""

    def __init__(self, z, q_vel=0.01):
        self.x = np.r_[z, 0, 0, 0].astype(float)
        self.P = np.eye(7) * 10.0
        self.P[4:, 4:] *= 1000.0  # unknown velocity
        self.Q = np.eye(7)
        self.Q[-1, -1] *= 0.01
        self.Q[4:, 4:] *= 0.01
        self.Q[4:6, 4:6] = np.eye(2) * q_vel  # position velocity; SORT: 0.01
        self.R = np.diag([1.0, 1.0, 10.0, 10.0])
        self.since_update = 0

    def predict(self):
        if self.x[2] + self.x[6] <= 0:
            self.x[6] = 0.0
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + self.Q
        self.since_update += 1
        return self.x[:2]

    def update(self, z):
        y = z - H @ self.x
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(7) - K @ H) @ self.P
        self.since_update = 0


def sort_track(dets, max_age=1, q_vel=0.01, birth_gap=0.0, gate=GATE):
    """Per frame: predict all tracks, Hungarian assignment on center distance, unmatched detections start tracks,
    tracks unmatched for more than `max_age` frames are deleted. With `birth_gap` > 0, no track starts that close
    to a detection just assigned. Returns per track (t, x, y) of the detections.

    SORT's min_hits only delays when a track is reported online; offline the whole history is kept and
    flight_rows drops short tracks anyway.
    """
    active, done = [], []
    for t, d in enumerate(dets):
        preds = np.array([tr.predict() for tr in active]).reshape(-1, 2)
        used = set()
        if len(active) and len(d):
            cost = np.linalg.norm(preds[:, None] - d[None, :, :2], axis=2)
            for i, j in zip(*linear_sum_assignment(cost)):
                if cost[i, j] < gate:
                    active[i].update(np.r_[d[j], 1.0])
                    active[i].pts.append((t, *d[j, :2]))
                    used.add(j)
        still = []
        for tr in active:
            (done if tr.since_update > max_age else still).append(tr)
        taken = d[sorted(used), :2] if used else np.zeros((0, 2))
        for j in range(len(d)):
            if j in used or (birth_gap and len(taken) and np.linalg.norm(taken - d[j, :2], axis=1).min() < birth_gap):
                continue
            tr = KalmanTrack(np.r_[d[j], 1.0], q_vel)
            tr.pts = [(t, *d[j, :2])]
            still.append(tr)
        active = still
    return [np.array(tr.pts) for tr in done + active]


def blobs(seq_id, top, board_rows=0):
    """v3 detections (x, y, area) per frame, cached: decoding the video twice is the slow part.

    With `board_rows` > 0 the clutter mask spares the landing board (separate cache).
    """
    cache = (CACHE.with_name("blobs_board") if board_rows else CACHE) / f"{seq_id}.npz"
    if not cache.exists():
        dets, _, bg = detect(seq_id, top, keep_rows=board_rows)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, dets=np.concatenate(dets), frame=np.repeat(np.arange(len(dets)), [len(d) for d in dets]),
                            n=len(dets), shape=bg.shape)
    c = np.load(cache)
    return [c["dets"][c["frame"] == i] for i in range(int(c["n"]))], tuple(c["shape"])


def run(seq_id, board=False):
    top, bottom = (int(v * SCALE) for v in BOARD[seq_id[3:7]])
    dets, shape = blobs(seq_id, top, board_rows=bottom - top if board else 0)
    for name, params in VARIANTS.items():
        name += "_board" if board else ""
        rows = flight_rows(sort_track(dets, **params), shape, bottom - top)
        out = ROOT / "outputs" / f"flights_{name}"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{seq_id}.json").write_text(json.dumps({"seq": seq_id, "tracker": name, "top": top, "scale": SCALE,
                                                        "rows": rows}))
        done = sum("lost" not in (r["start"], r["end"]) for r in rows)
        print(f"{seq_id} {name}: {len(rows)} flight tracks, {done} complete", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["track", "compare"])
    ap.add_argument("seqs", nargs="*")
    ap.add_argument("--split", action="append", choices=list(SPLITS), default=[])
    ap.add_argument("--board", action="store_true", help="track on the landing board too (outputs/flights_<variant>_board/)")
    args = ap.parse_args()
    seqs = args.seqs + [s for name in args.split for s in SPLITS[name]]
    if args.cmd == "compare":
        from .detector import compare
        compare(seqs, ("flights",) + tuple(f"flights_{name}{'_board' if args.board else ''}" for name in VARIANTS))
        return
    for seq_id in seqs:
        if video_path(seq_id).exists():
            run(seq_id, args.board)
        else:
            print(f"{seq_id}: video missing, skipped", flush=True)


if __name__ == "__main__":
    main()
