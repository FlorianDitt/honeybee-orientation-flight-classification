"""Feasibility scan: find flight tracks that look like a bee carrying something (corpse, drone).

A bee carrying a corpse is roughly twice as wide as a lone bee. Width across the flight
direction (e_perp) is not inflated by motion blur, so it is the size feature we threshold.
Drones are bigger too, so candidates must be reviewed by eye; this only shortlists them.

Usage: python prototype/scan_carry.py SEQ_ID [SEQ_ID ...]
"""
import csv
import sys
from pathlib import Path

import av
import cv2
import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from beeflight.splits import video_path  # noqa: E402
from shutter_calib import blobs, extent, link  # noqa: E402

Y_MIN = {"2123": 1020, "2125": 1080}  # flight zone starts below the landing board
OUT = Path(__file__).parent / "out" / "carry"


def scan(seq_id, thr=22, min_len=4):
    rec = seq_id[3:7]
    y_min = Y_MIN[rec]
    with av.open(str(video_path(seq_id))) as c:
        c.streams.video[0].thread_type = "AUTO"
        gray = np.stack([f.to_ndarray(format="gray")[y_min:] for f in c.decode(video=0)])
    bg = np.median(gray[::20], axis=0).astype(np.int16)
    per_frame = [blobs(np.abs(f.astype(np.int16) - bg), thr) for f in gray]
    del gray
    rows = []
    for tid, track in enumerate(link(per_frame, max_jump=160)):
        if len(track) < min_len:
            continue
        c = np.array([b["c"] for _, b in track])
        steps = np.linalg.norm(np.diff(c, axis=0), axis=1)
        if np.median(steps) < 2:  # static clutter
            continue
        widths, areas = [], []
        for i in range(1, len(track) - 1):
            v = track[i + 1][1]["c"] - track[i - 1][1]["c"]
            if np.linalg.norm(v) < 1:
                continue
            u = v / np.linalg.norm(v)
            widths.append(extent(track[i][1]["pts"], np.array([-u[1], u[0]])))
            areas.append(track[i][1]["area"])
        if not widths:
            continue
        k = int(np.argmax(widths))
        t_mid, b_mid = track[k + 1]
        rows.append({
            "seq": seq_id, "track": tid, "t_start": track[0][0], "len": len(track),
            "speed": float(np.median(steps)), "width": float(np.median(widths)),
            "area": float(np.median(areas)), "t_peak": t_mid,
            "x": float(b_mid["c"][0]), "y": float(b_mid["c"][1] + y_min),
            "dy": float(c[-1, 1] - c[0, 1]),  # >0: moving away from the hive (downwards)
        })
    return rows


def crops(seq_id, cand, out_dir, r=70):
    """Save a 3-frame colour strip around each candidate's widest moment."""
    want = {}
    for row in cand:
        for k in (-2, 0, 2):
            want.setdefault(row["t_peak"] + k, []).append((row, k))
    strips = {id(row): [None] * 3 for row in cand}
    with av.open(str(video_path(seq_id))) as c:
        for i, fr in enumerate(c.decode(video=0)):
            if i in want:
                img = fr.to_ndarray(format="bgr24")
                for row, k in want[i]:
                    x = int(np.clip(row["x"], r, img.shape[1] - r))
                    y = int(np.clip(row["y"], r, img.shape[0] - r))
                    strips[id(row)][(k + 2) // 2] = cv2.resize(img[y - r:y + r, x - r:x + r], (240, 240))
            if i > max(want):
                break
    for row in cand:
        tiles = [t if t is not None else np.zeros((240, 240, 3), np.uint8) for t in strips[id(row)]]
        strip = np.hstack(tiles)
        cv2.putText(strip, f"{seq_id} f{row['t_peak']} w={row['width']:.0f}", (4, 18), 0, .55, (0, 0, 255), 2)
        cv2.imwrite(str(out_dir / f"{seq_id}_f{row['t_peak']:04d}.jpg"), strip)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for seq_id in sys.argv[1:]:
        rows = scan(seq_id)
        w = np.array([r["width"] for r in rows])
        med = np.median(w) if len(w) else 0
        for r in rows:
            r["width_ratio"] = r["width"] / med if med else 0
        cand = [r for r in rows if r["width_ratio"] >= 1.8]
        if cand:
            crops(seq_id, cand, OUT)
        print(f"{seq_id}: {len(rows)} flight tracks, median width {med:.1f}px, {len(cand)} wide candidates", flush=True)
        all_rows += rows
    path = OUT / "tracks.csv"
    new = not path.exists()
    with open(path, "a", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        if new:
            wr.writeheader()
        wr.writerows(all_rows)


if __name__ == "__main__":
    main()
