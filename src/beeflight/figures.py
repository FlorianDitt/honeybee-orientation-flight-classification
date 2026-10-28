"""Slide figures from beeflight-tracks output (training/validation sequences of Stock A only).

Usage: beeflight-figures   (needs beeflight-tracks output for the sequences in SEQS)
"""
import json

import av
import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .splits import ROOT, video_path  # noqa: E402

IN = ROOT / "outputs" / "flights"
ASSETS = ROOT / "presentation" / "assets"
SEQS = ["015", "025", "035", "050", "060", "069", "078"]
CURVY, STRAIGHT = "#e0662a", "#3d93c9"  # validated pair (dataviz validator, light surface)


def categories(rows):
    dep = [r for r in rows if r["start"] == "board" and r["end"] != "board"]
    arr = [r for r in rows if r["end"] == "board" and r["start"] != "board"]
    curvy = sum(r["straight"] < 0.5 and r["dur_s"] > 0.4 for r in dep)
    return {"Abflug, kurvig": curvy, "Abflug, gerade": len(dep) - curvy,
            "Anflug": len(arr), "Fragment / Sonstige": len(rows) - len(dep) - len(arr)}


def counts_chart():
    per = [categories(json.loads((IN / f"rec2123_seq{s}.json").read_text())["rows"]) for s in SEQS]
    col = {"Abflug, kurvig": CURVY, "Abflug, gerade": STRAIGHT, "Anflug": "#8a8f98", "Fragment / Sonstige": "#dcdde0"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": "#9ca3af",
                         "axes.labelcolor": "#6b7280", "xtick.color": "#6b7280", "ytick.color": "#6b7280"})
    fig, ax = plt.subplots(figsize=(5.6, 3.3), dpi=200)
    fig.patch.set_facecolor("#fbfaf7")
    ax.set_facecolor("#fbfaf7")
    x, bottom = np.arange(len(SEQS)), np.zeros(len(SEQS))
    for k, c in col.items():
        v = np.array([p[k] for p in per])
        ax.bar(x, v, 0.62, bottom=bottom, color=c, edgecolor="#fbfaf7", linewidth=1.5, label=k)
        bottom += v
    ax.set_xticks(x, [f"Seq. {s}" for s in SEQS], fontsize=9.5)
    ax.set_ylabel("Flugbahnen pro 30 s")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.yaxis.grid(True, color="#e5e7eb", lw=0.8)
    ax.set_axisbelow(True)
    ax.set_ylim(0, bottom.max() * 1.25)
    ax.legend(frameon=False, fontsize=9.5, loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(ASSETS / "flight_counts.png", facecolor=fig.get_facecolor())
    return {k: sum(p[k] for p in per) for k in col}


def tracker_chart():
    """Share of complete tracks (both ends at the board or the frame edge) per tracker version, train + val."""
    from .splits import SPLITS
    versions = [("flights_v1", "v1 · Vorstudie"), ("flights_v2", "v2 · Zonen, Schwelle"), ("flights", "v3 · Tracker-Fixes")]
    shares, counts = [], []
    for folder, _ in versions:
        rows = [r for s in SPLITS["train"] + SPLITS["val"]
                for r in json.loads((ROOT / "outputs" / folder / f"{s}.json").read_text())["rows"]]
        done = sum("lost" not in (r["start"], r["end"]) for r in rows)
        shares.append(100 * done / len(rows))
        counts.append(done)
    fig, ax = plt.subplots(figsize=(5.4, 2.3), dpi=200)
    fig.patch.set_facecolor("#fbfaf7")
    ax.set_facecolor("#fbfaf7")
    colors = ["#c9ccd1", "#c9ccd1", "#d99a1e"]
    x = np.arange(len(versions))
    ax.bar(x, shares, 0.56, color=colors)
    for xi, sh, n in zip(x, shares, counts):
        ax.text(xi, sh + 3, f"{sh:.0f} %", ha="center", va="bottom", fontsize=13, fontweight="bold", color="#16181d")
        ax.text(xi, sh / 2, f"{n}\nBahnen", ha="center", va="center", fontsize=8.5, color="#16181d", linespacing=1.1)
    ax.set_xticks(x, [v[1] for v in versions], fontsize=9.5)
    ax.set_ylim(0, max(shares) * 1.18)
    ax.set_yticks([])
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "tracker_versions.png", facecolor=fig.get_facecolor())
    return dict(zip([v[1] for v in versions], [round(s, 1) for s in shares]))


def hero(seq="rec2123_seq050", frame=300):
    d = json.loads((IN / f"{seq}.json").read_text())
    with av.open(str(video_path(seq))) as c:
        img = next(f.to_ndarray(format="bgr24") for i, f in enumerate(c.decode(video=0)) if i == frame)
    img = cv2.addWeighted(img, 0.6, np.full_like(img, 20), 0.4, 0)
    rows = d["rows"]

    def smooth(r):  # chord length over path length: jittery tangles score low
        return np.linalg.norm(np.diff(np.array(r["xy"])[::4], axis=0), axis=1).sum() / (r["path"] + 1e-9)

    loops = sorted([r for r in rows if r["dur_s"] > 0.7 and r["straight"] < 0.5 and smooth(r) > 0.85],
                   key=lambda r: -abs(r["turn_deg"]))[:5]
    straight = sorted([r for r in rows if r["straight"] > 0.92], key=lambda r: -r["net"])[:5]
    bgr = lambda h: tuple(int(h[i:i + 2], 16) for i in (5, 3, 1))  # noqa: E731
    for group, colour in ((straight, bgr(STRAIGHT)), (loops, bgr(CURVY))):
        for r in group:
            xy = ((np.array(r["xy"]) + [0, d["top"]]) * 2).astype(np.int32)
            cv2.polylines(img, [xy], False, (250, 250, 250), 10, cv2.LINE_AA)
            cv2.polylines(img, [xy], False, colour, 6, cv2.LINE_AA)
            cv2.circle(img, tuple(int(v) for v in xy[-1]), 10, colour, -1, cv2.LINE_AA)
    crop = cv2.resize(img[760:1920], None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(ASSETS / "flights_seq050.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 88])


def main():
    print(counts_chart())
    hero()
    if (ROOT / "outputs" / "flights_v1").exists() and (ROOT / "outputs" / "flights_v2").exists():
        print(tracker_chart())


if __name__ == "__main__":
    main()
