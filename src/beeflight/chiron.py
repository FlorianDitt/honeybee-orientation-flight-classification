"""Tracker after Chiron, Gomez-Krämer & Ménard 2013 (EURASIP JIVP 2013:59), reduced to 2D.

The paper tracks bees at the hive entrance with a stereo camera. Without depth, what remains is:

Detection (Sect. 3.1, intensity part of HIDS):
- background IBG = temporal median of frames (Eq. 8), then selective adaptation: only pixels outside the
  foreground move towards the current frame with learning rate DELTA (Eq. 12)
- absolute motion mask IAMM: |IBG - I| dilated with S1, eroded with S2 (S1 > S2), mean filtered, > DM (Eq. 6)
- relative motion mask IRMM: |I_t - I_t-1| opened with S3, > DRM (Eq. 9)
- foreground: regions of IAMM without any relative motion are dropped ("all potential targets except areas
  that exhibited no motion", Eq. 10 with every depth undetermined)
- one observation per region: its centroid (Sect. 3.2)

Tracking (Sect. 4, 3D-GNN in the image plane):
- one Kalman filter per bee, state (x, y, x', y'), constant velocity
- Global Nearest Neighbor: Hungarian assignment on the negative log-likelihood of the innovation,
  ln sqrt|S| + (N ln 2 pi + d^2) / 2 with Mahalanobis distance d (Eq. 16-19), only pairs inside the gate
- observations without a track start a new one; a track is deleted after MAX_MISSES missed frames in a row

Not in the paper, so set here: the thresholds, structuring elements and noise levels (the paper gives no
values), a minimum region area against pixel noise, and a chi-square gate. Nothing from v3 is used: no clutter
mask, no blob merging, no birth gap, no stitching. Same half resolution and flight zone as v3, so the tracks
are comparable.

The landing board lies inside the tracked area (as in the paper, which tracks bees on the board too).
--no-board drops observations on the board, for comparison with v3, which masks it.

Tracklet linking (Huang, Wu & Nevatia, ECCV 2008, second level of the hierarchical association):
the tracker above gives reliable but broken tracklets (a bee lost for a few frames over the grass comes back as a
new track). Afterwards every tracklet end may link to one tracklet start 1..LINK_GAP frames later, chosen globally
with the Hungarian algorithm. A link needs both motion predictions to agree: the end of A extrapolated forward
and the start of B extrapolated backward must each land near the other, within LINK_R0 + LINK_R1 * gap; the
"no link" option costs as much as the gate, so a link is only taken if it is better than none. Also on the board.

Variants (VARIANTS), all on the same observations per threshold pair:
- chiron:        first version, DM 15 / DRM 8 (hand-evaluated, kept unchanged)
- chiron_sort:   SORT (Bewley et al. 2016, sort.py) instead of the GNN, DM 15 / DRM 8
- chiron_strict: DM 25 / DRM 10 (stricter: less grass and shadow, chosen on validation)
- chiron_linked: DM 25 / DRM 10 plus tracklet linking (final)

Usage: beeflight-chiron SEQ_ID ... | --split val [--variants chiron_linked ...] [--no-board]
       (writes outputs/flights_<variant>[_noboard]/)
"""
import argparse
import json

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from .splits import ROOT, SPLITS, video_path
from .tracks import BOARD, SCALE, flight_rows, frames

OUT = ROOT / "outputs" / "flights_chiron"
TRACKER = "chiron2013-2d"

# detection
DELTA = 0.05                 # background learning rate (Eq. 12)
DM, DRM = 25, 10             # grey-level thresholds of IAMM and IRMM (15 / 8 in the first version)
S1, S2, S3 = 5, 3, 3         # structuring elements (square, px)
MEAN = 3                     # mean filter size
MIN_AREA = 20                # half-res px, below that it is pixel noise
# tracking
MAX_MISSES = 3               # "destroyed if it is not associated to an observation three times in succession"
SIGMA_M = 2.0                # measurement noise of a centroid (px)
SIGMA_A = 4.0                # process noise: acceleration (px / frame^2), bees turn sharply
SIGMA_V0 = 20.0              # velocity uncertainty of a new track (px / frame)
GATE = 13.8                  # chi-square, 2 dof, 99.9 %
# tracklet linking (half-res px, frames)
LINK_GAP = 60                # up to 1 s without observation
LINK_R0, LINK_R1 = 10.0, 1.5 # allowed prediction error: grows with the gap, the bee may turn
LINK_VMAX = 30.0             # no faster than this across the gap (px / frame)

VARIANTS = {"chiron": dict(dm=15, drm=8), "chiron_sort": dict(dm=15, drm=8, sort=True),
            "chiron_strict": dict(dm=25, drm=10), "chiron_linked": dict(dm=25, drm=10, link=True)}

F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], float)
H = np.eye(2, 4)
Q = SIGMA_A ** 2 * np.array([[.25, 0, .5, 0], [0, .25, 0, .5], [.5, 0, 1, 0], [0, .5, 0, 1]])
R = SIGMA_M ** 2 * np.eye(2)


def kernel(n):
    return np.ones((n, n), np.uint8)


def detect(seq_id, y_top, skip_rows=0, dm=DM, drm=DRM):
    """Observations (x, y, area) per frame, half resolution, y relative to y_top; none in the first `skip_rows` rows."""
    bg = np.median(np.stack([g[y_top:] for _, g in frames(seq_id, step=15)]), axis=0).astype(np.float32)
    dets, prev = [], None
    for _, g in frames(seq_id):
        img = g[y_top:].astype(np.float32)
        diff = cv2.erode(cv2.dilate(np.abs(bg - img), kernel(S1)), kernel(S2))
        iamm = (cv2.blur(diff, (MEAN, MEAN)) > dm).astype(np.uint8)
        if prev is None:
            irmm = np.ones_like(iamm)
        else:
            irmm = (cv2.morphologyEx(np.abs(img - prev), cv2.MORPH_OPEN, kernel(S3)) > drm).astype(np.uint8)
        k, lab, st, cen = cv2.connectedComponentsWithStats(iamm)
        moving = np.zeros(k, bool)
        moving[np.unique(lab[irmm > 0])] = True
        keep = [j for j in range(1, k) if moving[j] and st[j, 4] >= MIN_AREA]
        c = np.c_[cen[keep], st[keep, 4]].reshape(-1, 3)
        dets.append(c[c[:, 1] >= skip_rows])
        fg = np.isin(lab, keep)
        bg = np.where(fg, bg, DELTA * img + (1 - DELTA) * bg)
        prev = img
    return dets, bg.shape


class Track:
    def __init__(self, t, z):
        self.x = np.r_[z, 0.0, 0.0]
        self.P = np.diag([SIGMA_M ** 2, SIGMA_M ** 2, SIGMA_V0 ** 2, SIGMA_V0 ** 2])
        self.misses = 0
        self.pts = [(t, *z)]

    def predict(self):
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def innovation(self):
        S = H @ self.P @ H.T + R
        return self.x[:2], S

    def update(self, t, z):
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ (z - H @ self.x)
        self.P = (np.eye(4) - K @ H) @ self.P
        self.misses = 0
        self.pts.append((t, *z))


def gnn_track(dets, max_misses=MAX_MISSES, gate=GATE):
    """Kalman filter per track, Hungarian assignment on the negative log-likelihood inside the gate."""
    active, done = [], []
    for t, d in enumerate(dets):
        d = d[:, :2]
        for tr in active:
            tr.predict()
        used = set()
        if active and len(d):
            cost = np.full((len(active), len(d)), np.inf)
            for i, tr in enumerate(active):
                mu, S = tr.innovation()
                Si = np.linalg.inv(S)
                e = d - mu
                d2 = np.einsum("nj,jk,nk->n", e, Si, e)
                ok = d2 < gate
                cost[i, ok] = 0.5 * np.log(np.linalg.det(S)) + 0.5 * (2 * np.log(2 * np.pi) + d2[ok])
            big = 1e9
            rows, cols = linear_sum_assignment(np.where(np.isfinite(cost), cost, big))
            for i, j in zip(rows, cols):
                if np.isfinite(cost[i, j]):
                    active[i].update(t, d[j])
                    used.add(j)
        still = []
        for tr in active:
            if tr.pts[-1][0] != t:
                tr.misses += 1
            (done if tr.misses >= max_misses else still).append(tr)
        still += [Track(t, d[j]) for j in range(len(d)) if j not in used]
        active = still
    return [np.array(tr.pts) for tr in done + active]


def link_tracklets(tracks, max_gap=LINK_GAP, r0=LINK_R0, r1=LINK_R1, vmax=LINK_VMAX):
    """Join tracklets (arrays of t, x, y) end-to-start, globally optimal, both motion predictions must agree."""
    tracks = [p for p in tracks if len(p) >= 2]
    n = len(tracks)
    if n < 2:
        return tracks

    def vel(p, end):
        q = p[-5:] if end else p[:5]
        dt = q[-1, 0] - q[0, 0]
        return (q[-1, 1:] - q[0, 1:]) / dt if dt > 0 else np.zeros(2)

    t_end = np.array([p[-1, 0] for p in tracks]); t_start = np.array([p[0, 0] for p in tracks])
    p_end = np.array([p[-1, 1:] for p in tracks]); p_start = np.array([p[0, 1:] for p in tracks])
    v_end = np.array([vel(p, True) for p in tracks]); v_start = np.array([vel(p, False) for p in tracks])
    big = 1e6
    cost = np.full((n, n), big)
    for i in range(n):
        gap = t_start - t_end[i]
        for j in np.flatnonzero((gap >= 1) & (gap <= max_gap)):
            g = gap[j]
            if np.linalg.norm(p_start[j] - p_end[i]) > vmax * g:
                continue
            tol = r0 + r1 * g
            fwd = np.linalg.norm(p_end[i] + v_end[i] * g - p_start[j])
            bwd = np.linalg.norm(p_start[j] - v_start[j] * g - p_end[i])
            if max(fwd, bwd) < tol:
                cost[i, j] = (fwd + bwd) / (2 * tol)
    # augmented assignment: ends x starts, plus a "no link" option of cost 1 for every end and every start
    none = np.full((n, n), big)
    np.fill_diagonal(none, 1.0)
    full = np.block([[cost, none], [none, np.zeros((n, n))]])
    rows, cols = linear_sum_assignment(full)
    nxt = {i: j for i, j in zip(rows, cols) if i < n and j < n and cost[i, j] < 1.0}
    has_prev = set(nxt.values())
    out = []
    for i in range(n):
        if i in has_prev:
            continue
        parts, k = [tracks[i]], i
        while k in nxt:
            k = nxt[k]
            parts.append(tracks[k])
        out.append(np.concatenate(parts))
    return out


def observations(seq_id, top, skip_rows=0, dm=DM, drm=DRM):
    """detect(), cached per threshold pair: decoding the video is the slow part, all variants reuse it."""
    name = f"blobs_chiron_{dm}_{drm}" + ("_noboard" if skip_rows else "")
    cache = ROOT / "outputs" / name / f"{seq_id}.npz"
    if not cache.exists():
        dets, shape = detect(seq_id, top, skip_rows, dm, drm)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, dets=np.concatenate(dets), frame=np.repeat(np.arange(len(dets)), [len(d) for d in dets]),
                            n=len(dets), shape=shape)
    c = np.load(cache)
    return [c["dets"][c["frame"] == i] for i in range(int(c["n"]))], tuple(c["shape"])


def run(seq_id, variants=("chiron_linked",), board=True):
    from .sort import sort_track

    top, bottom = (int(v * SCALE) for v in BOARD[seq_id[3:7]])
    suffix = "" if board else "_noboard"
    for name in variants:
        v = VARIANTS[name]
        dets, shape = observations(seq_id, top, 0 if board else bottom - top, v["dm"], v["drm"])
        raw = sort_track(dets, max_age=MAX_MISSES, q_vel=1.0) if v.get("sort") else gnn_track(dets)
        if v.get("link"):
            raw = link_tracklets(raw)
        rows = flight_rows(raw, shape, bottom - top, stitched=False)
        out = ROOT / "outputs" / f"flights_{name}{suffix}"
        out.mkdir(parents=True, exist_ok=True)
        tracker = TRACKER + "-" + name.replace("_", "-") + suffix.replace("_", "-")
        (out / f"{seq_id}.json").write_text(json.dumps({"seq": seq_id, "tracker": tracker, "top": top, "scale": SCALE,
                                                         "rows": rows}))
        done = sum("lost" not in (r["start"], r["end"]) for r in rows)
        print(f"{seq_id} {out.name}: {len(rows)} flight tracks, {done} complete", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seqs", nargs="*")
    ap.add_argument("--split", action="append", choices=list(SPLITS), default=[])
    ap.add_argument("--variants", nargs="+", choices=list(VARIANTS), default=["chiron_strict", "chiron_linked"])
    ap.add_argument("--no-board", action="store_true", help="drop observations on the landing board")
    args = ap.parse_args()
    for seq_id in args.seqs + [s for name in args.split for s in SPLITS[name]]:
        if video_path(seq_id).exists():
            run(seq_id, args.variants, board=not args.no_board)
        else:
            print(f"{seq_id}: video missing, skipped", flush=True)


if __name__ == "__main__":
    main()
