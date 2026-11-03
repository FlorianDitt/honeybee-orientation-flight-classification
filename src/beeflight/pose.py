"""Pilot: can the body axis (and the head) of a flying bee be read from a single frame?

Orientation flights are described as arcs flown *facing the hive*. Whether that is measurable in our video
decides if "body points at the entrance" and the slip angle (body vs flight direction) can become features.

sample: cut full-resolution crops around tracked flying bees (Chiron + Huang tracks, train split), stratified by
        speed (slow / mid / fast, because motion blur grows with speed: exposure ≈ 1/4 frame), and store an
        automatic estimate per crop:
        - body axis from the second moments of the foreground blob (background = temporal median), axial 0..180°
        - three guesses for the head end of that axis: along the flight direction, the darker half, the
          heavier half (more foreground pixels)
        Crops go to outputs/pose/crops/ (frames t-2, t, t+2), the sample to labels/pose_queue.json.
label:  in the local labeler, page /pose: click head, then tail (blind, no estimate shown).
eval:   compare the clicks with the estimate: axis error per speed bin, accuracy of each head guess, and from the
        clicks alone how often bees fly sideways (slip angle) and face the hive.

Usage: beeflight-pose sample [--n 150 --seqs 15 --seed 0]
       beeflight-pose eval
"""
import argparse
import json
import math
import random
from collections import defaultdict

import av
import cv2
import numpy as np

from .splits import ROOT, SPLITS, video_path

FLIGHTS = ROOT / "outputs" / "flights_chiron_linked"
OUT = ROOT / "outputs" / "pose"
QUEUE = ROOT / "labels" / "pose_queue.json"
LABELS = ROOT / "labels" / "pose.jsonl"
CROP = 96  # full-res px; a bee is ~30 px long
CONTEXT = 2  # crops at t-2 and t+2 as well, so the labeler sees the motion
THR = 20  # gray-level difference to the background
MIN_AREA = 40  # full-res px; smaller blobs give no usable axis
# full-res px per frame; motion blur ≈ 0.25 × speed (exposure ≈ 4.2 ms of 16.7 ms)
BINS = {"slow": (0, 8), "mid": (8, 20), "fast": (20, 1e9)}
BOARD_BOTTOM = {"2123": 1000, "2125": 1040}  # full-res rows, flight zone starts below (as tracks.BOARD)
ZONE_MARGIN = 30
NEIGHBOUR = 60  # full-res px; skip points with another tracked bee this close (two bees in one crop)


def full_res(d, xy):
    return xy[0] / d["scale"], (xy[1] + d["top"]) / d["scale"]


def candidates(seq):
    """-> [(bin, point dict)] for every interior track point in the flight zone without a close neighbour."""
    d = json.loads((FLIGHTS / f"{seq}.json").read_text())
    rows = d["rows"]
    by_frame = defaultdict(list)
    for k, r in enumerate(rows):
        for t, xy in zip(r["t"], r["xy"]):
            by_frame[t].append((k, full_res(d, xy)))
    y_min = BOARD_BOTTOM[seq[3:7]] + ZONE_MARGIN
    out = []
    for k, r in enumerate(rows):
        pts = {t: full_res(d, xy) for t, xy in zip(r["t"], r["xy"])}
        for t in r["t"]:
            if t - 1 not in pts or t + 1 not in pts or t - CONTEXT < 0 or t + CONTEXT > 1799:
                continue
            x, y = pts[t]
            if y < y_min or not (CROP / 2 <= x <= 1080 - CROP / 2) or y > 1920 - CROP / 2:
                continue
            if any(j != k and math.dist((x, y), p) < NEIGHBOUR for j, p in by_frame[t]):
                continue
            vx = (pts[t + 1][0] - pts[t - 1][0]) / 2
            vy = (pts[t + 1][1] - pts[t - 1][1]) / 2
            speed = math.hypot(vx, vy)
            b = next(name for name, (lo, hi) in BINS.items() if lo <= speed < hi)
            out.append((b, {"seq": seq, "track": k, "t": t, "x": x, "y": y, "vx": vx, "vy": vy, "speed": speed,
                            "start": r["start"], "end": r["end"]}))
    return out


def pick(n, seqs, rng):
    """n points, the same number per speed bin, at most one per track, spread over the sequences."""
    pool = defaultdict(list)
    for seq in seqs:
        for b, p in candidates(seq):
            pool[b].append(p)
    picks = []
    for b in BINS:
        rng.shuffle(pool[b])
        used, per_seq, take = set(), defaultdict(int), []
        cap = math.ceil(n / len(BINS) / len(seqs)) + 1
        for p in pool[b]:
            key = (p["seq"], p["track"])
            if key in used or per_seq[p["seq"]] >= cap:
                continue
            used.add(key)
            per_seq[p["seq"]] += 1
            take.append({**p, "bin": b})
            if len(take) == n // len(BINS):
                break
        picks += take
    return picks


def box(p):
    x0 = int(round(p["x"] - CROP / 2))
    y0 = int(round(p["y"] - CROP / 2))
    return x0, y0


def estimate(gray, bg, cx, cy):
    """Body axis and head guesses of the blob at (cx, cy) in one crop; None if there is no usable blob."""
    m = (np.abs(gray.astype(np.int16) - bg.astype(np.int16)) > THR).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    k, lab, st, cen = cv2.connectedComponentsWithStats(m)
    if k < 2:
        return None
    j = 1 + int(np.argmin([math.dist((cx, cy), cen[i]) for i in range(1, k)]))
    if st[j, 4] < MIN_AREA or math.dist((cx, cy), cen[j]) > 20:
        return None
    ys, xs = np.nonzero(lab == j)
    mx, my = xs.mean(), ys.mean()
    dx, dy = xs - mx, ys - my
    mu20, mu02, mu11 = (dx * dx).mean(), (dy * dy).mean(), (dx * dy).mean()
    # long axis, image coordinates (y down), folded to 0..180°: the front/back signs below refer to this direction
    theta = math.radians(math.degrees(0.5 * math.atan2(2 * mu11, mu20 - mu02)) % 180)
    common = math.sqrt(((mu20 - mu02) / 2) ** 2 + mu11 ** 2)
    l1, l2 = (mu20 + mu02) / 2 + common, (mu20 + mu02) / 2 - common
    ax, ay = math.cos(theta), math.sin(theta)
    proj = dx * ax + dy * ay
    front, back = proj > 0, proj < 0
    vals = gray[ys, xs].astype(float)
    darker = 1 if vals[front].mean() < vals[back].mean() else -1  # +1: the +axis half is darker
    heavier = 1 if front.sum() > back.sum() else -1
    return {"cx": round(float(mx), 2), "cy": round(float(my), 2), "area": int(st[j, 4]),
            "axis_deg": round(math.degrees(theta) % 180, 1), "elong": round(math.sqrt(l1 / max(l2, 1e-6)), 2),
            "darker": darker, "heavier": heavier}


def heading(axis_deg, sign):
    return (axis_deg + (0 if sign > 0 else 180)) % 360


def sample(args):
    rng = random.Random(args.seed)
    seqs = [s for s in SPLITS["train"] if (FLIGHTS / f"{s}.json").exists() and video_path(s).exists()]
    seqs = sorted(rng.sample(seqs, min(args.seqs, len(seqs))))
    picks = pick(args.n, seqs, rng)
    crops = OUT / "crops"
    crops.mkdir(parents=True, exist_ok=True)
    by_seq = defaultdict(list)
    for p in picks:
        by_seq[p["seq"]].append(p)
    items = []
    for n_seq, (seq, ps) in enumerate(sorted(by_seq.items()), 1):
        need = {p["t"] + o for p in ps for o in range(-CONTEXT, CONTEXT + 1, CONTEXT)}
        frames, bg_frames = {}, []
        with av.open(str(video_path(seq))) as c:
            c.streams.video[0].thread_type = "AUTO"
            for i, f in enumerate(c.decode(video=0)):
                if i in need or i % 60 == 0:
                    img = f.to_ndarray(format="bgr24")
                    if i in need:
                        frames[i] = img
                    if i % 60 == 0:
                        bg_frames.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        bg = np.median(np.stack(bg_frames), axis=0).astype(np.uint8)
        for p in ps:
            x0, y0 = box(p)
            pid = f"{seq}:{p['t']}:{p['track']}"
            name = pid.replace(":", "_")
            for o in (-CONTEXT, 0, CONTEXT):
                crop = frames[p["t"] + o][y0:y0 + CROP, x0:x0 + CROP]
                cv2.imwrite(str(crops / f"{name}_{o:+d}.png"), crop)
            gray = cv2.cvtColor(frames[p["t"]][y0:y0 + CROP, x0:x0 + CROP], cv2.COLOR_BGR2GRAY)
            est = estimate(gray, bg[y0:y0 + CROP, x0:x0 + CROP], p["x"] - x0, p["y"] - y0)
            items.append({"id": pid, "name": name, **{k: p[k] for k in ("seq", "t", "bin", "start", "end")},
                          "x0": x0, "y0": y0, "px": round(p["x"] - x0, 1), "py": round(p["y"] - y0, 1),
                          "vx": round(p["vx"], 2), "vy": round(p["vy"], 2), "speed": round(p["speed"], 2),
                          "est": est})
        print(f"[{n_seq}/{len(by_seq)}] {seq}: {len(ps)} crops")
    rng.shuffle(items)  # labeling order must not follow the speed bins
    QUEUE.write_text(json.dumps({"source": FLIGHTS.name, "crop": CROP, "context": CONTEXT, "seed": args.seed,
                                 "items": items}))
    no_est = sum(i["est"] is None for i in items)
    print(f"{len(items)} crops -> {QUEUE.relative_to(ROOT)}, crops in {crops.relative_to(ROOT)}; "
          f"{no_est} without a usable blob")
    report_unlabeled(items)


def axial_diff(a, b):
    d = abs(a - b) % 180
    return min(d, 180 - d)


def circ_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def report_unlabeled(items):
    """What the estimate alone shows: how elongated the blobs are and how often the axis follows the motion."""
    print("\nwithout labels (estimate only):")
    print("bin    n   blob  elong(median)  axis within 20° of flight direction")
    for b in BINS:
        its = [i for i in items if i["bin"] == b]
        est = [i for i in its if i["est"]]
        el = np.median([i["est"]["elong"] for i in est]) if est else float("nan")
        along = [axial_diff(i["est"]["axis_deg"], math.degrees(math.atan2(i["vy"], i["vx"])) % 180) < 20 for i in est]
        print(f"{b:6} {len(its):3} {len(est):5}  {el:13.2f}  {sum(along)}/{len(along)}")


def evaluate(args):
    items = {i["id"]: i for i in json.loads(QUEUE.read_text())["items"]}
    labels = [json.loads(line) for line in LABELS.read_text().splitlines() if line.strip()] if LABELS.exists() else []
    labels = [r for r in labels if r["id"] in items]
    print(f"{len(labels)} of {len(items)} crops labeled")
    rows = []
    for r in labels:
        it = items[r["id"]]
        axis = None
        if r.get("head") and r.get("tail"):
            hx, hy = r["head"]
            tx, ty = r["tail"]
            axis = math.degrees(math.atan2(hy - ty, hx - tx)) % 360  # tail -> head, image coordinates
        rows.append((it, r, axis))

    print("\n1. Body axis: estimate vs. clicks (axial error, 0..90°)")
    print("bin    labeled  unclear  no blob  median  <20°        <30°")
    for b in BINS:
        rb = [(it, r, a) for it, r, a in rows if it["bin"] == b]
        clicked = [(it, a) for it, r, a in rb if a is not None]
        both = [(it, a) for it, a in clicked if it["est"]]
        err = [axial_diff(it["est"]["axis_deg"], a % 180) for it, a in both]
        n = len(err)
        k20, k30 = sum(e < 20 for e in err), sum(e < 30 for e in err)
        med = np.median(err) if err else float("nan")
        print(f"{b:6} {len(rb):7}  {len(rb) - len(clicked):7}  {len(clicked) - n:7}  {med:5.1f}°  "
              f"{k20:3}/{n:<3} {pct(k20, n)}  {k30:3}/{n:<3} {pct(k30, n)}")

    print("\n2. Which end is the head (only crops with a sure direction and an axis error < 30°)")
    print("bin    n    flight direction    darker half        heavier half")
    for b in [*BINS, "all"]:
        sure = [(it, a) for it, r, a in rows if a is not None and it["est"] and "richtung_unsicher" not in r["flags"]
                and (b == "all" or it["bin"] == b) and axial_diff(it["est"]["axis_deg"], a % 180) < 30]
        n = len(sure)
        cells = []
        for guess in ("flight", "darker", "heavier"):
            k = 0
            for it, a in sure:
                est = it["est"]
                if guess == "flight":
                    sign = 1 if math.cos(math.radians(est["axis_deg"])) * it["vx"] + \
                        math.sin(math.radians(est["axis_deg"])) * it["vy"] >= 0 else -1
                else:
                    sign = est[guess]
                k += circ_diff(heading(est["axis_deg"], sign), a) < 90
            cells.append(f"{k:3}/{n:<3} {pct(k, n)}")
        print(f"{b:6} {n:3}  " + "   ".join(cells))
    print("   (an accuracy far below 50 % means the opposite rule works: e.g. the lighter half is the head)")

    print("\n3. From the clicks alone (crops with a sure direction)")
    print("bin    n   slip > 45° (sideways/backwards)   head points up towards the board (< 45°)")
    for b in BINS:
        sure = [(it, a) for it, r, a in rows if a is not None and "richtung_unsicher" not in r["flags"] and it["bin"] == b]
        n = len(sure)
        slip = sum(circ_diff(a, math.degrees(math.atan2(it["vy"], it["vx"])) % 360) > 45 for it, a in sure)
        up = sum(circ_diff(a, 270) < 45 for it, a in sure)  # 270° = -y = towards the board
        print(f"{b:6} {n:3}   {slip:3}/{n:<3} {pct(slip, n):30}  {up:3}/{n:<3} {pct(up, n)}")


def pct(k, n):
    if n == 0:
        return "   –"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:3.0f} % [{100 * lo:.0f}–{100 * hi:.0f}]"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--n", type=int, default=150)
    s.add_argument("--seqs", type=int, default=15)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--force", action="store_true", help="overwrite an existing sample (and orphan its labels)")
    sub.add_parser("eval")
    args = ap.parse_args()
    if args.cmd == "sample":
        if QUEUE.exists() and not args.force:
            raise SystemExit(f"{QUEUE.relative_to(ROOT)} exists; --force draws a new sample")
        sample(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
