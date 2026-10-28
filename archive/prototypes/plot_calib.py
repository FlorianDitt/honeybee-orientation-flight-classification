"""Plot blur extent vs. per-frame displacement for calibration outputs."""
import json
import sys

import matplotlib.pyplot as plt
import numpy as np

thr = sys.argv[1] if len(sys.argv) > 1 else "22"
fig, ax = plt.subplots(figsize=(7, 4.5))
for name, color in [("rec2123_seq050", "#d08a2c"), ("rec2125_seq010", "#3a6ea5")]:
    rows = json.load(open(f"prototype/out/{name}_thr{thr}.json"))
    fit = json.load(open(f"prototype/out/{name}_summary.json"))[thr]
    d = np.array([r["d"] for r in rows])
    # partial residual: remove the body-size term so only the blur term remains
    y = np.array([r["e_par"] - fit["coef_e_perp"] * r["e_perp"] for r in rows])
    ax.scatter(d, y, s=8, alpha=0.4, color=color)
    xs = np.linspace(0, d.max(), 50)
    lo, hi = fit["ci95"]
    ax.plot(xs, fit["intercept"] + fit["shutter_fraction"] * xs, color=color, lw=2,
            label=f"{name}: s={fit['shutter_fraction']:.2f} [{lo:.2f}, {hi:.2f}] "
                  f"≈ {fit['exposure_ms']:.1f} ms")
ax.plot(xs, 25 + xs, "k--", lw=1, label="360° shutter (s = 1), for reference")
ax.set_xlabel("displacement between frames d [px/frame]")
ax.set_ylabel("extent along motion, body-size corrected [px]")
ax.set_title(f"Blur grows with speed: slope = shutter fraction (thr={thr})")
ax.legend(fontsize=8)
ax.set_ylim(0, 160)
fig.tight_layout()
fig.savefig(f"prototype/out/calibration_thr{thr}.png", dpi=150)
