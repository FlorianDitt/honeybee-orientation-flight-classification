"""Prototype: estimate the camera's shutter angle from motion blur of flying bees.

Idea: a bee moving d px/frame is smeared over v*T_exp = d * s px, where
s = T_exp / T_frame is the shutter fraction (shutter angle = 360 * s).
Its extent along the motion direction is therefore  E_par = body + s * d,
while the extent perpendicular to the motion, E_perp, is unaffected by blur.
Regressing E_par on d (controlling for body size via E_perp) gives s.

Usage: python prototype/shutter_calib.py VIDEO [--y-min 1080] [--thr 22] [--out DIR]
"""
import argparse
import json
from pathlib import Path

import av
import cv2
import numpy as np


def load_gray(path, y_min=0, step=1, limit=None):
    """Grayscale frames, cropped to rows >= y_min (the flight zone)."""
    frames = []
    with av.open(str(path)) as c:
        for i, fr in enumerate(c.decode(video=0)):
            if limit and i >= limit:
                break
            if i % step == 0:
                frames.append(fr.to_ndarray(format="gray")[y_min:])
    return np.stack(frames)


def blobs(diff, thr):
    mask = (diff > thr).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    k, lab, st, cen = cv2.connectedComponentsWithStats(mask)
    out = []
    for j in range(1, k):
        a = st[j, cv2.CC_STAT_AREA]
        if 150 < a < 12000:
            ys, xs = np.nonzero(lab == j)
            out.append({"c": cen[j], "pts": np.c_[xs, ys].astype(np.float32), "area": int(a)})
    return out


def extent(pts, u):
    p = pts @ u
    lo, hi = np.percentile(p, [1, 99])
    return hi - lo


def link(per_frame, max_jump):
    """Mutually unique nearest matches between consecutive frames, chained into tracks."""
    for t in range(len(per_frame) - 1):
        for b in per_frame[t]:
            fwd = [o for o in per_frame[t + 1] if np.linalg.norm(o["c"] - b["c"]) < max_jump]
            if len(fwd) == 1:
                back = [o for o in per_frame[t] if np.linalg.norm(o["c"] - fwd[0]["c"]) < max_jump]
                if len(back) == 1:
                    b["next"], fwd[0]["prev"] = fwd[0], b
    tracks = []
    for t, blobs_t in enumerate(per_frame):
        for b in blobs_t:
            if "prev" not in b:
                tr, cur, k = [], b, t
                while cur is not None:
                    tr.append((k, cur))
                    cur, k = cur.get("next"), k + 1
                tracks.append(tr)
    return tracks


def is_flight(track, min_len, min_speed, min_straight):
    """Flying bees move fast and straight; wind-blown grass jitters back and forth."""
    if len(track) < min_len:
        return False
    c = np.array([b["c"] for _, b in track])
    steps = np.linalg.norm(np.diff(c, axis=0), axis=1)
    path = steps.sum()
    return np.median(steps) >= min_speed and np.linalg.norm(c[-1] - c[0]) / (path + 1e-9) >= min_straight


def measure(gray, thr, max_jump=160, iso_radius=220, min_len=5, min_speed=4.0, min_straight=0.8):
    bg = np.median(gray[::20], axis=0).astype(np.int16)
    per_frame = [blobs(np.abs(f.astype(np.int16) - bg), thr) for f in gray]
    rows = []
    for tid, track in enumerate(link(per_frame, max_jump)):
        if not is_flight(track, min_len, min_speed, min_straight):
            continue
        for i in range(1, len(track) - 1):
            t, b = track[i]
            # isolation: no other blob nearby in this frame
            if any(o is not b and np.linalg.norm(o["c"] - b["c"]) < iso_radius for o in per_frame[t]):
                continue
            prev, nxt = [track[i - 1][1]], [track[i + 1][1]]
            v = (nxt[0]["c"] - prev[0]["c"]) / 2.0
            d = float(np.linalg.norm(v))
            if d < 1.0:
                continue
            u = v / d
            n = np.array([-u[1], u[0]])
            rows.append({
                "track": tid, "t": t, "x": float(b["c"][0]), "y": float(b["c"][1]), "d": d,  # y relative to y_min
                "e_par": float(extent(b["pts"], u)), "e_perp": float(extent(b["pts"], n)),
                "area": b["area"],
                # acceleration check: displacement consistency prev->t vs t->next
                "accel": float(np.linalg.norm((nxt[0]["c"] - b["c"]) - (b["c"] - prev[0]["c"]))),
            })
    return rows


def robust_fit(X, y, iters=20, c=1.345):
    """Huber IRLS; returns coefficients and inlier weights."""
    w = np.ones(len(y))
    for _ in range(iters):
        beta, *_ = np.linalg.lstsq(X * w[:, None] ** 0.5, y * w ** 0.5, rcond=None)
        r = y - X @ beta
        scale = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-9
        a = np.abs(r) / scale
        w = np.where(a <= c, 1.0, c / a)
    return beta, w


def bootstrap(X, y, groups, n=500, seed=0):
    """Cluster bootstrap over tracks: frames of one bee are not independent."""
    rng = np.random.default_rng(seed)
    ids = np.unique(groups)
    members = {g: np.flatnonzero(groups == g) for g in ids}
    out = []
    for _ in range(n):
        i = np.concatenate([members[g] for g in rng.choice(ids, len(ids))])
        out.append(robust_fit(X[i], y[i])[0])
    return np.percentile(np.array(out), [2.5, 97.5], axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--y-min", type=int, default=1080, help="ignore rows above (landing board)")
    ap.add_argument("--thr", type=int, nargs="+", default=[15, 22, 30, 40])
    ap.add_argument("--max-accel", type=float, default=12.0)
    ap.add_argument("--out", default="prototype/out")
    args = ap.parse_args()

    gray = load_gray(args.video, args.y_min)
    name = Path(args.video).stem
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for thr in args.thr:
        rows = [r for r in measure(gray, thr) if r["accel"] < args.max_accel]
        if len(rows) < 10:
            print(f"{name} thr={thr}: only {len(rows)} samples")
            continue
        d = np.array([r["d"] for r in rows])
        ep = np.array([r["e_par"] for r in rows])
        en = np.array([r["e_perp"] for r in rows])
        X = np.c_[np.ones_like(d), en, d]
        beta, w = robust_fit(X, ep)
        groups = np.array([r["track"] for r in rows])
        ci = bootstrap(X, ep, groups)
        s, s_lo, s_hi = beta[2], ci[0, 2], ci[1, 2]
        results[thr] = {"n": len(rows), "tracks": int(len(np.unique(groups))), "shutter_fraction": s, "ci95": [s_lo, s_hi],
                        "shutter_angle_deg": 360 * s, "exposure_ms": 1000 * s / 59.94,
                        "coef_e_perp": beta[1], "intercept": beta[0]}
        print(f"{name} thr={thr:>2}: n={len(rows):4d} tracks={len(np.unique(groups)):3d}  s={s:.3f} [{s_lo:.3f},{s_hi:.3f}]  "
              f"angle={360 * s:5.1f}°  exposure≈{1000 * s / 59.94:.2f} ms  "
              f"(E_par = {beta[0]:.1f} + {beta[1]:.2f}·E_perp + s·d)")
        with open(out / f"{name}_thr{thr}.json", "w") as f:
            json.dump(rows, f)
    with open(out / f"{name}_summary.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
