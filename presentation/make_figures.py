"""Figures for the slides, from labels/ and outputs/. Run: .venv/bin/python presentation/make_figures.py"""
import json, collections
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "presentation" / "assets"
INK, MUTED, BG = "#16181d", "#6b7280", "#fbfaf7"
COL = {"orientierung": "#e0662a", "sammelabflug": "#3d93c9", "anflug": "#6b8f5a", "artefakt": "#a8adb5"}
NAME = {"orientierung": "Orientierungsflug", "sammelabflug": "Sammelabflug", "anflug": "Anflug", "artefakt": "Artefakt"}
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": INK, "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG})

def jl(p): return [json.loads(l) for l in open(ROOT / p)]
def clean(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color("#d1d5db")

labels = jl("labels/train.jsonl") + jl("labels/val.jsonl")  # same camera: example tracks
all_labels = labels + jl("labels/final_test_same_hive.jsonl") + jl("labels/final_test_other_hive.jsonl")

# 1. one typical track per class
allxy = np.concatenate([np.array(r["xy"]) for r in labels])
XL = (allxy[:, 0].min() - 8, allxy[:, 0].max() + 8); YL = (allxy[:, 1].min() - 8, allxy[:, 1].max() + 8)
fig, axs = plt.subplots(1, 4, figsize=(11, 3.1))
rng = np.random.default_rng(3)
for ax, c in zip(axs, COL):
    cand = [r for r in labels if r["label"] == c and len(r["xy"]) >= 30]
    picks = rng.choice(len(cand), size=min(5, len(cand)), replace=False)
    for k, i in enumerate(picks):
        xy = np.array(cand[i]["xy"]); a = 1 if k == 0 else 0.28
        ax.plot(xy[:, 0], xy[:, 1], color=COL[c], lw=3 if k == 0 else 1.4, alpha=a, solid_capstyle="round")
        if k == 0:
            ax.scatter(*xy[0], s=38, color=COL[c], zorder=3); ax.scatter(*xy[-1], s=38, facecolor=BG, edgecolor=COL[c], lw=2, zorder=3)
    ax.set_xlim(XL); ax.set_ylim(YL[::-1]); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color("#e5e7eb")
    n = sum(r["label"] == c for r in all_labels)
    ax.set_title(f"{NAME[c]}", fontsize=13, fontweight="bold", color=COL[c] if c != "artefakt" else MUTED, loc="left")
    ax.set_xlabel(f"{n} Bahnen", fontsize=10, color=MUTED)
fig.tight_layout(); fig.savefig(OUT / "klassen.png", dpi=170); plt.close(fig)

# 2. trackers, blind verdict of one rater on 30-60 random validation tracks each (labels/tracker_eval.jsonl)
ev = collections.defaultdict(collections.Counter)
for r in jl("labels/tracker_eval.jsonl"): ev[r["tracker"]][r["verdict"]] += 1
def wilson(x, n, z=1.96):
    p = x / n; d = 1 + z * z / n; m = p + z * z / (2 * n); w = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (m - w) / d, (m + w) / d
T = [("SORT\n(Bewley 2016)", "flights_chiron_sort"), ("Chiron 2013", "flights_chiron"), ("Chiron 2013\n+ Huang 2008", "flights_chiron_linked")]
T = [t for t in T if ev[t[1]]]
fig, ax = plt.subplots(figsize=(7.4, 0.8 + 0.8 * len(T)))
for i, (n, k) in enumerate(T):
    c = ev[k]; N = sum(c.values()); x = c["korrekt"]; lo, hi = wilson(x, N); final = k == "flights_chiron_linked"
    left = 0
    for v, col in (("korrekt", "#d99a1e" if final else "#8a9099"), ("bruchstueck", "#e3e5e8"), ("wechsel", "#c9cdd3"), ("keine_biene", "#c9cdd3")):
        w = 100 * c[v] / N
        if w: ax.barh(i, w, left=left, color=col, height=0.62, edgecolor=BG, lw=1.5)
        left += w
    ax.text(100 * x / N / 2, i, f"{100*x/N:.0f} %", va="center", ha="center", fontsize=13, fontweight="bold", color="white")
    ax.text(103, i, f"[{100*lo:.0f}\u2013{100*hi:.0f}]", va="center", fontsize=10.5, color=MUTED)
ax.set_yticks(range(len(T))); ax.set_yticklabels([f"{t[0]} (n={sum(ev[t[1]].values())})" for t in T], fontsize=11); ax.invert_yaxis()
ax.set_xlim(0, 118); ax.set_xticks([]); clean(ax); ax.spines["bottom"].set_visible(False)
ax.text(103, -0.62, "95 %-Intervall", fontsize=9.5, color=MUTED, va="center")
ax.set_title("Anteil korrekter Bahnen (blind bewertet)", fontsize=11, loc="left", color=MUTED)
fig.tight_layout(); fig.savefig(OUT / "tracker_vergleich.png", dpi=170); plt.close(fig)
print({k: dict(v) for k, v in ev.items()})

# 3. result: rule vs model vs model on unanimous tracks, Test A and Test B
def ev_ba(split, sec="Mehrheit (primär)", model="ensemble_kombi+B_yolo"):
    b = json.load(open(ROOT / f"outputs/eval/{split}/summary.json"))[sec]["models"][model]["metrics"]["balanced_accuracy"]
    ci = b.get("ci") or b["loso"]; return b["mean"], (ci["low"], ci["high"])
ROWS = [("Regel", "rule", "Mehrheit (primär)", "#a8adb5"), ("Modell", "ensemble_kombi+B_yolo", "Mehrheit (primär)", "#d99a1e"),
        ("Modell, nur Bahnen\nmit einstimmigen Labels", "ensemble_kombi+B_yolo", "einstimmig", "#8a5a00")]
fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.9), sharey=True)
for ax, (title, sp) in zip(axs, (("Test A · gleicher Stock", "test_same_hive"), ("Test B · neuer Stock", "test_other_hive"))):
    for i, (n, m, sec, c) in enumerate(ROWS):
        v, ci = ev_ba(sp, sec, m)
        ax.plot(ci, [i, i], color=c, lw=6, alpha=0.3, solid_capstyle="round"); ax.scatter(v, i, s=170, color=c, zorder=3)
        ax.text(v, i - 0.36, f"{v:.2f}".replace(".", ","), ha="center", fontsize=15, fontweight="bold", color=INK if i else MUTED)
    ax.set_xlim(0.5, 1.0); ax.set_ylim(2.6, -0.8); ax.set_xticks([0.5, 0.75, 1.0]); ax.set_xticklabels(["0,5", "0,75", "1"], fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold", loc="left"); clean(ax)
axs[0].set_yticks(range(3)); axs[0].set_yticklabels([r[0] for r in ROWS], fontsize=12)
fig.supxlabel("Balanced Accuracy, Balken: 95 %-Intervall", fontsize=10, color=MUTED)
fig.tight_layout(); fig.savefig(OUT / "ergebnis.png", dpi=170); plt.close(fig)

# 3b. one real frame with the hand-labelled tracks of that sequence, coloured by class
import av, cv2
from beeflight.splits import video_path
# hand-picked examples from contact sheets of train+val: compact loops in front of the board (orientierung), a straight
# departure (sammelabflug), a smooth arrival (anflug), and a leaf that jumps back and forth (artefakt, bee check: kein_tier)
from beeflight.baselines import track_features
EX = {"orientierung": "rec2123_seq083:1019", "sammelabflug": "rec2123_seq020:455", "artefakt": "rec2123_seq069:594"}
byid = {r["id"]: r for r in labels}
arr = [r for r in labels if r["label"] == "anflug" and r["seq"][:7] == "rec2123"]
arr = [(r, track_features(r)) for r in arr]
others = np.concatenate([np.array(byid[i]["xy"]) for i in EX.values()])
def free(r):  # closest approach to the other three examples: lies where nothing else is drawn
    xy = np.array(r["xy"]); return np.linalg.norm(xy[:, None] - others[None], axis=2).min(1).min()
EX["anflug"] = max((r for r, f in arr if f["end"] == "board" and 0.4 < f["straight"] < 0.85 and len(r["xy"]) >= 40
                    and f["abs_turn_deg"] < 400), key=free)["id"]
pick = [byid[EX[c]] for c in COL]
SEQ = EX["orientierung"].split(":")[0]; rows = pick
with av.open(str(video_path(SEQ))) as cont:
    img = next(f.to_ndarray(format="rgb24") for i, f in enumerate(cont.decode(video=0)) if i == 300)
img = cv2.addWeighted(img, 0.7, np.full_like(img, 25), 0.3, 0)
allp = np.concatenate([(np.array(r["xy"]) + [0, r["top"]]) * 2 for r in pick])
y0 = max(0, int(rows[0]["top"] * 2) - 120); y1 = min(img.shape[0], int(allp[:, 1].max()) + 40)
crop = img[y0:y1]; h, w = crop.shape[:2]
fig = plt.figure(figsize=(6.0 * w / h, 6.0)); ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(crop); ax.set_axis_off()
for r in pick:
    xy = (np.array(r["xy"]) + [0, r["top"]]) * 2 - [0, y0]; c = COL[r["label"]]
    ax.plot(xy[:, 0], xy[:, 1], color="white", lw=6, alpha=0.9, solid_capstyle="round")
    ax.plot(xy[:, 0], xy[:, 1], color=c, lw=3.4, solid_capstyle="round"); ax.scatter(*xy[-1], s=60, color=c, edgecolor="white", lw=1.5, zorder=3)
fig.savefig(OUT / "hero.png", dpi=170); plt.close(fig)
print("hero", EX)

# 4. label consistency (same person, a week apart)
def agree(a, b):
    A = {r["id"]: r["label"] for r in jl(a)}; B = jl(b)
    return sum(A.get(r["id"]) == r["label"] for r in B) / len(B), len(B)
(tr, n1), (va, n2) = agree("labels/train.jsonl", "labels/recheck.jsonl"), agree("labels/val.jsonl", "labels/recheck_val.jsonl")
fig, ax = plt.subplots(figsize=(3.6, 3.5))
for i, (n, v, c) in enumerate([("Train", tr, "#2f4858"), ("Val", va, "#6b8fa3")]):
    ax.bar(i, v * 100, color=c, width=0.6); ax.text(i, v * 100 + 2, f"{v*100:.0f} %", ha="center", fontsize=15, fontweight="bold")
ax.set_xticks([0, 1]); ax.set_xticklabels([f"Train\n(n={n1})", f"Val\n(n={n2})"], fontsize=11); ax.set_ylim(0, 108); ax.set_yticks([])
clean(ax); ax.spines["left"].set_visible(False)
ax.set_title("Zweites Label gleich\nwie das erste", fontsize=11, loc="left", color=MUTED)
fig.tight_layout(); fig.savefig(OUT / "label_konsistenz.png", dpi=170); plt.close(fig)
print(tr, va)

# 3c. slide 1 builds up: empty frame, then one clip per class (real frames of its own sequence, same crop as hero.png).
# Each clip shows the earlier tracks finished and draws its own track as the bee flies; the last frame stays.
H = 640; W = int(round(w * H / h / 2)) * 2; sc = H / h
to_px = lambda r: (((np.array(r["xy"]) + [0, r["top"]]) * 2 - [0, y0]) * sc).astype(np.int32)  # noqa: E731
rgb = lambda hx: tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))  # noqa: E731
dim = lambda fr: cv2.resize(cv2.addWeighted(fr, 0.7, np.full_like(fr, 25), 0.3, 0)[y0:y1], (W, H), interpolation=cv2.INTER_AREA)  # noqa: E731
def line(fr, xy, c):
    cv2.polylines(fr, [xy], False, (255, 255, 255), 6, cv2.LINE_AA); cv2.polylines(fr, [xy], False, rgb(c), 3, cv2.LINE_AA)
def done(fr, r):
    xy = to_px(r); line(fr, xy, COL[r["label"]])
    cv2.circle(fr, tuple(int(v) for v in xy[-1]), 7, rgb(COL[r["label"]]), -1, cv2.LINE_AA)
    cv2.circle(fr, tuple(int(v) for v in xy[-1]), 7, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite(str(OUT / "leer.png"), cv2.cvtColor(cv2.resize(crop, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2BGR))
for k, r in enumerate(pick, 1):
    seq, ts, c = r["id"].split(":")[0], np.array(r["t"]), COL[r["label"]]
    f0, f1 = ts[0] - 20, ts[-1] + 20
    out = av.open(str(OUT / f"bahn{k}.mp4"), "w"); vs = out.add_stream("libx264", rate=30)  # 60 fps footage at half speed
    vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"; vs.options = {"crf": "23", "movflags": "+faststart"}
    def put(fr):
        for p in vs.encode(av.VideoFrame.from_ndarray(fr, format="rgb24")): out.mux(p)
    last = None
    with av.open(str(video_path(seq))) as cont:
        for i, f in enumerate(cont.decode(video=0)):
            if i < f0: continue
            if i > f1: break
            fr = dim(f.to_ndarray(format="rgb24"))
            for q in pick[:k - 1]: done(fr, q)
            xy = to_px(r)[ts <= i]
            if i > ts[-1]: done(fr, r)
            elif len(xy) > 1: line(fr, xy, c)
            if len(xy) and i <= ts[-1]: cv2.circle(fr, tuple(int(v) for v in xy[-1]), 16, rgb(c), 2, cv2.LINE_AA)
            put(fr); last = fr
    for _ in range(10): put(last)
    for p in vs.encode(): out.mux(p)
    out.close(); print("clip", k, r["label"], seq, f1 - f0 + 1, "frames")

# 3d. how many classes? F1 of orientierung on val for 2, 3, 4 classes (outputs/klassen/vergleich.json, post hoc)
kv = ROOT / "outputs/klassen/vergleich.json"
fig, ax = plt.subplots(figsize=(4.4, 2.5))
if kv.exists():
    V3 = json.load(open(kv))["variants"]
    for i, k in enumerate(("k2", "k3", "k4")):
        r = V3[k]; c = "#d99a1e" if k == "k4" else "#a8adb5"
        ax.plot([r["f1_o_ci"]["low"], r["f1_o_ci"]["high"]], [i, i], color=c, lw=6, alpha=0.3, solid_capstyle="round")
        ax.scatter(r["f1_o"], i, s=130, color=c, zorder=3)
        ax.text(r["f1_o_ci"]["high"] + 0.02, i, f"{r['f1_o']:.2f}".replace(".", ","), va="center", fontsize=13, fontweight="bold")
        ax.text(1.02, i, f"{r['share_error_pp']:+.0f} PP".replace("-", "−"), va="center", fontsize=11, color=MUTED, transform=ax.get_yaxis_transform())
    ax.text(1.02, -0.75, "Anteil", fontsize=9.5, color=MUTED, transform=ax.get_yaxis_transform())
    ax.set_xlim(0.3, 1.0)
else:
    ax.text(0.5, 1, "Training läuft", ha="center", va="center", fontsize=14, color=MUTED); ax.set_xlim(0, 1)
ax.set_yticks(range(3)); ax.set_yticklabels(["2 Klassen", "3 Klassen", "4 Klassen"], fontsize=12); ax.invert_yaxis()
ax.set_ylim(2.5, -0.9); ax.set_xticks([]); clean(ax); ax.spines["bottom"].set_visible(False)
ax.set_title("F1 Orientierung, Val", fontsize=11, loc="left", color=MUTED)
fig.tight_layout(); fig.savefig(OUT / "klassenzahl.png", dpi=170); plt.close(fig)
