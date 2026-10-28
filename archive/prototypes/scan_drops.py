"""Feasibility scan: count bee-sized objects that appear in the grass below the board and stay.

Corpses and expelled drones are dropped or carried off the landing board and often end up
on the ground right below it. In a per-sequence median image moving bees vanish, but a
dead bee lying still is kept. A blob that is absent in earlier medians and present in all
later ones is a 'drop' candidate. Wind-blown grass flickers and fails the persistence test.

Usage: python prototype/scan_drops.py rec2123 SEQ_FROM SEQ_TO
"""
import sys
from pathlib import Path

import av
import cv2
import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
from beeflight.splits import video_path  # noqa: E402

# ground strip directly below the landing board (full-res rows)
ZONE = {"2123": (1000, 1350), "2125": (1040, 1400)}
OUT = Path(__file__).parent / "out" / "drops"


def median_frame(seq_id, y0, y1, step=30):
    with av.open(str(video_path(seq_id))) as c:
        c.streams.video[0].thread_type = "AUTO"
        fr = [f.to_ndarray(format="bgr24")[y0:y1] for i, f in enumerate(c.decode(video=0)) if i % step == 0]
    return np.median(np.stack(fr), axis=0).astype(np.uint8)


def new_blobs(before, after, thr=40, a_min=120, a_max=2500):
    d = np.abs(after.astype(np.int16) - before.astype(np.int16)).max(axis=2)
    m = cv2.morphologyEx((d > thr).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    k, _, st, cen = cv2.connectedComponentsWithStats(m)
    return [(cen[j], st[j]) for j in range(1, k) if a_min < st[j, cv2.CC_STAT_AREA] < a_max
            and max(st[j, 2], st[j, 3]) < 90]


def main():
    rec, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    y0, y1 = ZONE[rec]
    ids = [f"rec{rec}_seq{i:03d}" for i in range(a, b + 1) if video_path(f"rec{rec}_seq{i:03d}").exists()]
    OUT.mkdir(parents=True, exist_ok=True)
    meds = []
    for s in ids:
        meds.append(median_frame(s, y0, y1))
        print("median", s, flush=True)
    np.save(OUT / f"medians_{rec}_{a}_{b}.npy", np.stack(meds))
    events = []
    for i in range(2, len(meds) - 1):
        # reference before: pixelwise median of the two previous medians; must persist in the next one
        before = np.median(np.stack(meds[i - 2:i]), axis=0).astype(np.uint8)
        for (cx, cy), st in new_blobs(before, meds[i]):
            x, y, w, h = st[:4]
            persist = np.abs(meds[i + 1][y:y + h, x:x + w].astype(np.int16)
                             - meds[i][y:y + h, x:x + w].astype(np.int16)).max(axis=2).mean()
            if persist < 18:
                events.append((ids[i], float(cx), float(cy) + y0, int(st[4])))
                r = 50
                xa, ya = int(np.clip(cx, r, meds[i].shape[1] - r)), int(np.clip(cy, r, meds[i].shape[0] - r))
                pair = np.hstack([before[ya - r:ya + r, xa - r:xa + r], meds[i][ya - r:ya + r, xa - r:xa + r]])
                cv2.imwrite(str(OUT / f"{ids[i]}_{int(cx)}_{int(cy) + y0}.jpg"), cv2.resize(pair, (400, 200)))
    print(f"{len(events)} persistent new objects across {len(ids)} sequences")
    for e in events:
        print(*e)


if __name__ == "__main__":
    main()
