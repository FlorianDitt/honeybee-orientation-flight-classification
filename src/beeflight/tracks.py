"""Feasibility: extract whole flight paths in front of the entrance and measure how loopy they are.

Orientation flights of young bees are loops and arcs facing the hive; foragers leave and arrive
fairly straight. Per track we record where it starts and ends (board, frame edge, lost in the
grass) and its total turning angle: |turn| > 360 deg means the bee flew at least one full loop.

Usage: beeflight-tracks SEQ_ID [SEQ_ID ...]       (writes outputs/flights/<seq>.json and .jpg)
       beeflight-tracks --split train --skip-existing
"""
import argparse
import json

import av
import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

from .splits import ROOT, SPLITS, video_path

SCALE = 0.5
TRACKER = "background-v2"
# half-res px: a track ending this close to the board or the frame edge has landed or left the frame
BOARD_MARGIN, EDGE_MARGIN = 30, 30
# full-res rows: top of the board (bees sit there) and its lower edge (flight zone starts below)
BOARD = {"2123": (820, 1000), "2125": (770, 1040)}
OUT = ROOT / "outputs" / "flights"


def frames(seq_id, step=1):
    with av.open(str(video_path(seq_id))) as c:
        c.streams.video[0].thread_type = "AUTO"
        for i, f in enumerate(c.decode(video=0)):
            if i % step == 0:
                g = f.to_ndarray(format="gray")
                yield i, cv2.resize(g, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)


def detect(seq_id, y_top, thr=18):
    bg = np.median(np.stack([g[y_top:] for _, g in frames(seq_id, step=15)]), axis=0).astype(np.int16)
    dets, fg_count = [], np.zeros(bg.shape, np.int32)
    for _, g in frames(seq_id):
        m = (np.abs(g[y_top:].astype(np.int16) - bg) > thr).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        fg_count += m
        k, _, st, cen = cv2.connectedComponentsWithStats(m)
        dets.append(np.array([[*cen[j], st[j, 4]] for j in range(1, k) if 25 < st[j, 4] < 3000]).reshape(-1, 3))
    # wind-blown grass and the crowded board are foreground far more often than a passing bee
    clutter = fg_count > 0.08 * len(dets)
    clutter = cv2.dilate(clutter.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    keep = []
    for d in dets:
        xi = np.clip(d[:, 0].astype(int), 0, bg.shape[1] - 1)
        yi = np.clip(d[:, 1].astype(int), 0, bg.shape[0] - 1)
        keep.append(d[~clutter[yi, xi]] if len(d) else d)
    return keep, clutter, bg


def track(dets, gate=45.0, max_gap=3):
    """Hungarian matching on constant-velocity predictions; tracks survive short gaps."""
    active, done = [], []
    for t, d in enumerate(dets):
        preds = np.array([tr["pts"][-1][1:3] + tr["v"] * (t - tr["pts"][-1][0]) for tr in active]).reshape(-1, 2)
        used = set()
        if len(active) and len(d):
            cost = np.linalg.norm(preds[:, None] - d[None, :, :2], axis=2)
            for i, j in zip(*linear_sum_assignment(cost)):
                if cost[i, j] < gate:
                    tr = active[i]
                    dt = t - tr["pts"][-1][0]
                    tr["v"] = 0.5 * tr["v"] + 0.5 * (d[j, :2] - tr["pts"][-1][1:3]) / dt
                    tr["pts"].append((t, *d[j, :2]))
                    used.add(j)
        still = []
        for tr in active:
            (done if t - tr["pts"][-1][0] > max_gap else still).append(tr)
        active = still + [{"pts": [(t, *d[j, :2])], "v": np.zeros(2)} for j in range(len(d)) if j not in used]
    return [np.array(tr["pts"]) for tr in done + active]


def zone_of(pt, shape, board_bottom):
    h, w = shape
    if pt[1] < board_bottom + BOARD_MARGIN:
        return "board"
    if pt[0] < EDGE_MARGIN or pt[0] > w - EDGE_MARGIN or pt[1] > h - EDGE_MARGIN:
        return "edge"
    return "lost"


def stitch(tracks, shape, board_bottom, max_gap=40, radius=12.0, spread=2.0, vmax=30.0):
    """Join fragments of one flight: the bee vanishes over the grass and reappears as a new track.

    A track that ends in the open ("lost") is linked to a track that starts in the open up to `max_gap`
    frames later, if the start lies near the constant-velocity extrapolation of the end and vice versa
    (tolerance grows with the gap, the bee may turn). Links are taken greedily, best first, one per end.
    Tracks leaving at the frame edge or landing on the board are never continued.
    """
    tracks = [p for p in tracks if len(p) >= 3]

    def vel(p, end):
        q = p[-5:] if end else p[:5]
        dt = q[-1, 0] - q[0, 0]
        return (q[-1, 1:] - q[0, 1:]) / dt if dt > 0 else np.zeros(2)

    ends = [(p[-1, 0], p[-1, 1:], vel(p, True), zone_of(p[-1, 1:], shape, board_bottom)) for p in tracks]
    starts = [(p[0, 0], p[0, 1:], vel(p, False), zone_of(p[0, 1:], shape, board_bottom)) for p in tracks]
    cand = []
    for i, (te, pe, ve, ze) in enumerate(ends):
        if ze != "lost":
            continue
        for j, (ts, ps, vs, zs) in enumerate(starts):
            gap = ts - te
            if i == j or zs != "lost" or not 1 <= gap <= max_gap:
                continue
            if np.linalg.norm(ps - pe) > vmax * gap:
                continue
            tol = radius + spread * gap
            err = 0.5 * (np.linalg.norm(pe + ve * gap - ps) + np.linalg.norm(ps - vs * gap - pe))
            if err < tol:
                cand.append((err / tol, i, j))
    nxt, has_prev = {}, set()
    for _, i, j in sorted(cand):
        if i in nxt or j in has_prev:
            continue
        # no cycles: j must not already lead back to i
        k = j
        while k in nxt and k != i:
            k = nxt[k]
        if k == i:
            continue
        nxt[i] = j
        has_prev.add(j)
    out = []
    for i in range(len(tracks)):
        if i in has_prev:
            continue
        parts, k = [tracks[i]], i
        while k in nxt:
            k = nxt[k]
            parts.append(tracks[k])
        out.append(np.concatenate(parts))
    return out


def flight_rows(raw, shape, board_bottom, stitched=True):
    """Raw tracker output -> flight tracks with features, as written to outputs/flights/<seq>.json."""
    tracks = stitch(raw, shape, board_bottom) if stitched else raw
    rows = []
    for p in tracks:
        if len(p) < 15:
            continue
        f = features(p, shape, board_bottom)
        # flight: mostly below the board and actually moving
        if f["frac_below_board"] < 0.6 or f["path"] < 60 or f["speed"] < 1.0:
            continue
        f["t"] = p[:, 0].astype(int).tolist()  # frame index of each point (gaps possible)
        f["xy"] = p[:, 1:].round(1).tolist()
        rows.append(f)
    return rows


def features(p, shape, board_bottom):
    t, xy = p[:, 0], p[:, 1:]
    steps = np.diff(xy, axis=0)
    seg = np.linalg.norm(steps, axis=1)
    path = seg.sum()
    # smooth heading over 3-frame chords so pixel jitter does not add up to fake turning
    ch = xy[3:] - xy[:-3]
    ok = np.linalg.norm(ch, axis=1) > 3
    ang = np.unwrap(np.arctan2(ch[ok, 1], ch[ok, 0])) if ok.sum() > 2 else np.zeros(1)

    return {
        "t0": int(t[0]), "n": len(p), "dur_s": float((t[-1] - t[0]) / 59.94),
        "path": float(path), "net": float(np.linalg.norm(xy[-1] - xy[0])),
        "straight": float(np.linalg.norm(xy[-1] - xy[0]) / (path + 1e-9)),
        "turn_deg": float(np.degrees(ang[-1] - ang[0])) if len(ang) > 1 else 0.0,
        "abs_turn_deg": float(np.degrees(np.abs(np.diff(ang)).sum())) if len(ang) > 1 else 0.0,
        "speed": float(np.median(seg)) if len(seg) else 0.0,
        "start": zone_of(xy[0], shape, board_bottom), "end": zone_of(xy[-1], shape, board_bottom),
        "frac_below_board": float((xy[:, 1] > board_bottom).mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seqs", nargs="*")
    ap.add_argument("--split", action="append", choices=list(SPLITS), default=[])
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()
    seqs = args.seqs + [s for name in args.split for s in SPLITS[name]]
    OUT.mkdir(parents=True, exist_ok=True)
    for seq_id in seqs:
        if args.skip_existing and (OUT / f"{seq_id}.json").exists():
            continue
        if not video_path(seq_id).exists():
            print(f"{seq_id}: video missing, skipped", flush=True)
            continue
        rec = seq_id[3:7]
        top, bottom = (int(v * SCALE) for v in BOARD[rec])
        dets, clutter, bg = detect(seq_id, top)
        rows = flight_rows(track(dets), bg.shape, bottom - top)
        (OUT / f"{seq_id}.json").write_text(json.dumps({"seq": seq_id, "tracker": TRACKER, "top": top, "scale": SCALE, "rows": rows}))
        # overview: loops red, straight green, rest yellow
        img = cv2.cvtColor((bg.clip(0, 255) // 2).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        img[clutter] = (img[clutter] * 0.5).astype(np.uint8)
        for f in rows:
            col = (0, 0, 255) if f["abs_turn_deg"] > 360 else (0, 220, 0) if f["straight"] > 0.8 else (0, 220, 255)
            cv2.polylines(img, [np.array(f["xy"], np.int32)], False, col, 1, cv2.LINE_AA)
        cv2.imwrite(str(OUT / f"{seq_id}.jpg"), img)
        n = len(rows)
        loops = sum(f["abs_turn_deg"] > 360 for f in rows)
        print(f"{seq_id}: {n} flight tracks, {loops} with >=360 deg turning, "
              f"start board {sum(f['start'] == 'board' for f in rows)}, end board {sum(f['end'] == 'board' for f in rows)}, "
              f"median dur {np.median([f['dur_s'] for f in rows]) if rows else 0:.2f}s", flush=True)


if __name__ == "__main__":
    main()
