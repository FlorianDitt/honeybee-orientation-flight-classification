"""Phase 4: classify flight tracks into the four label classes, measured on validation.

Models (docs/methode.md, section 5):
- rule:     rule baseline on straightness, duration and start/end zone. `rule_fixed` uses the thresholds of the
            pilot study (straight < 0.5, dur > 0.4 s), `rule` picks them by grid search on the training labels
- logreg:   logistic regression on the track features
- gbm:      gradient boosting on the same features
- gru:      bidirectional GRU on the point sequence (x, y, dx, dy, |v|, dtheta, gap), pretrained on the self-labels
            of all training tracks, then fine-tuned on the hand labels
- gru_scratch: the same GRU without pretraining
- gru_shape:   ablation for H2: no absolute position (only dx, dy, |v|, dtheta, gap), pretrained the same way

Coordinates: relative to the middle of the lower board edge, in board widths (the board spans the frame width in
rec2123). Every model is trained on train only, with fixed settings (no early stopping on validation), and
reported on validation; the test sets are not touched here.

Pretraining on self-labels (start/end zone: departure, arrival, board-board, other) would be trivial with the full
track, since the zones are defined by the first and last point. So every pretraining track is cropped to a random
50-100 % window: the model has to tell where the bee comes from or goes from the course of the flight.

Augmentation (training only, docs/methode.md): horizontal mirror, rotation +-10 deg, scale 0.9-1.1, random crop
of start and end (simulates fragments).

Learning curve: 25 / 50 / 100 / all hand labels, each with several seeds (stratified subsets).
Every run is written to outputs/runs/<group>/<model>_n<size>_s<seed>.json (config, seed, git hash, metrics);
the summary with 95 % cluster-bootstrap intervals over validation sequences goes to outputs/runs/<group>/summary.md.

Usage: beeflight-classify [--seeds 5] [--sizes 25 50 100 0] [--labels own|final] [--models rule gbm gru ...]
       (size 0 = all labels)
"""
import argparse
import json
import subprocess
import time
from collections import Counter
from datetime import datetime

import numpy as np

from .splits import ROOT, SPLITS
from .tracks import BOARD, SCALE, features

CLASSES = ["orientierung", "sammelabflug", "anflug", "artefakt"]
SELF = ["abflug", "anflug", "brett_brett", "sonst"]
FLIGHTS = ROOT / "outputs" / "flights_chiron_linked"
LABELS = ROOT / "labels"
RUNS = ROOT / "outputs" / "runs"
# half resolution, y relative to the board top: entrance reference point (middle of the lower board edge) and the
# board width used as unit. rec2125 (Test B) has to be set from a single frame before the test, not from results.
ENTRANCE = {"2123": dict(x=270.0, width=540.0)}
SHAPE = {"2123": (550, 540)}  # (h, w) of the flight zone below the board top
MODELS = ["rule_fixed", "rule", "logreg", "gbm", "gru", "gru_scratch", "gru_shape"]


def board_bottom(rec):
    top, bottom = BOARD[rec]
    return (bottom - top) * SCALE


# ---------------------------------------------------------------- data

def hand_labels(split, source="own"):
    """-> list of dict(id, seq, t, xy, y) from labels/<split>.jsonl (own) or labels/final_<split>.jsonl (majority)"""
    path = LABELS / (f"{split}.jsonl" if source == "own" else f"final_{split}.jsonl")
    out = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("label") not in CLASSES:
            continue
        out.append(dict(id=r["id"], seq=r["seq"], t=np.array(r["t"], float), xy=np.array(r["xy"], float),
                        y=CLASSES.index(r["label"]), flags=r.get("flags", [])))
    return out


def self_label(f):
    if f["start"] == "board" and f["end"] == "board":
        return 2
    if f["start"] == "board":
        return 0
    if f["end"] == "board":
        return 1
    return 3


def all_tracks(split):
    """Every flight track of a split with its self-label (for pretraining)."""
    out = []
    for seq in SPLITS[split]:
        path = FLIGHTS / f"{seq}.json"
        if not path.exists():
            continue
        for r in json.loads(path.read_text())["rows"]:
            out.append(dict(id=f"{seq}:{r['t0']}", seq=seq, t=np.array(r["t"], float), xy=np.array(r["xy"], float),
                            y=self_label(r)))
    return out


def to_entrance(xy, rec):
    e = ENTRANCE[rec]
    return np.column_stack([(xy[:, 0] - e["x"]) / e["width"], (xy[:, 1] - board_bottom(rec)) / e["width"]])


def channels(pos, t):
    """(n, 7): x, y, dx, dy, |v|, dtheta, gap; velocities per frame in board widths."""
    dt = np.diff(t, prepend=t[0] - 1).clip(1, None)
    d = np.diff(pos, axis=0, prepend=pos[:1]) / dt[:, None]
    v = np.linalg.norm(d, axis=1)
    th = np.arctan2(d[:, 1], d[:, 0])
    dth = np.angle(np.exp(1j * np.diff(th, prepend=th[0])))
    dth[v < 1e-3] = 0.0
    return np.column_stack([pos, d * 50, v * 50, dth, np.log(dt)]).astype(np.float32)


def augment(pos, t, rng, crop=(0.7, 1.0)):
    if rng.random() < 0.5:
        pos = pos * [-1, 1]
    a = np.radians(rng.uniform(-10, 10))
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    pos = pos @ rot.T * rng.uniform(0.9, 1.1)
    return random_crop(pos, t, rng, *crop)


def random_crop(pos, t, rng, lo, hi):
    n = len(pos)
    k = max(8, int(round(n * rng.uniform(lo, hi))))
    if k >= n:
        return pos, t
    s = rng.integers(0, n - k + 1)
    return pos[s:s + k], t[s:s + k]


# ---------------------------------------------------------------- hand features

def feature_vector(tr):
    rec = tr["seq"][3:7]
    p = np.column_stack([tr["t"], tr["xy"]])
    f = features(p, SHAPE[rec], board_bottom(rec))
    pos = to_entrance(tr["xy"], rec)
    dist = np.linalg.norm(pos, axis=1)
    dx = np.convolve(np.diff(pos[:, 0]), np.ones(5) / 5, mode="valid") if len(pos) > 6 else np.zeros(1)
    flips = int((np.diff(np.sign(dx[np.abs(dx) > 1e-3])) != 0).sum())
    zones = ["board", "edge", "lost"]
    return [f["dur_s"], f["path"] / ENTRANCE[rec]["width"], f["net"] / ENTRANCE[rec]["width"], f["straight"],
            abs(f["turn_deg"]), f["abs_turn_deg"], f["speed"], *pos[0], *pos[-1], dist.max(), dist.mean(),
            (dist < 0.25).mean(), flips, *[f["start"] == z for z in zones], *[f["end"] == z for z in zones]]


def rule_predict(tr, straight=0.5, dur=0.4):
    rec = tr["seq"][3:7]
    f = features(np.column_stack([tr["t"], tr["xy"]]), SHAPE[rec], board_bottom(rec))
    if f["start"] == "board" and f["end"] == "board":
        return 0
    if f["start"] == "board":
        return 0 if f["straight"] < straight and f["dur_s"] > dur else 1
    if f["end"] == "board":
        return 2
    return 3


# ---------------------------------------------------------------- GRU

def gru_parts():
    import torch
    from torch import nn
    from torch.nn.utils.rnn import pack_padded_sequence, pad_sequence

    class Net(nn.Module):
        def __init__(self, n_in, n_out, hidden=64):
            super().__init__()
            self.gru = nn.GRU(n_in, hidden, num_layers=2, batch_first=True, bidirectional=True, dropout=0.2)
            self.drop = nn.Dropout(0.3)
            self.head = nn.Linear(4 * hidden, n_out)

        def encode(self, xs):
            lens = torch.tensor([len(x) for x in xs])
            pad = pad_sequence(xs, batch_first=True)
            out, h = self.gru(pack_padded_sequence(pad, lens, batch_first=True, enforce_sorted=False))
            last = torch.cat([h[-2], h[-1]], dim=1)
            mask = (torch.arange(pad.shape[1])[None] < lens[:, None]).float()[..., None]
            from torch.nn.utils.rnn import pad_packed_sequence
            seq, _ = pad_packed_sequence(out, batch_first=True)
            mean = (seq * mask[:, :seq.shape[1]]).sum(1) / lens[:, None]
            return torch.cat([last, mean], dim=1)

        def forward(self, xs):
            return self.head(self.drop(self.encode(xs)))

    return torch, nn, Net


class Scaler:
    def __init__(self, seqs):
        allc = np.concatenate(seqs)
        self.mu, self.sd = allc.mean(0), allc.std(0) + 1e-6

    def __call__(self, c):
        return (c - self.mu) / self.sd


def make_inputs(tracks, rng, cols, scaler, train, crop):
    out = []
    for tr in tracks:
        pos, t = to_entrance(tr["xy"], tr["seq"][3:7]), tr["t"]
        if train:
            pos, t = augment(pos, t, rng, crop)
        out.append(scaler(channels(pos, t))[:, cols])
    return out


def fit_gru(net, tracks, cols, scaler, seed, epochs, lr, crop, weighted=True, batch=32, log=None):
    torch, nn, _ = gru_parts()
    rng = np.random.default_rng(seed)
    ys = np.array([tr["y"] for tr in tracks])
    n_cls = net.head.out_features
    w = None
    if weighted:
        cnt = np.bincount(ys, minlength=n_cls).clip(1, None)
        w = torch.tensor(len(ys) / (n_cls * cnt), dtype=torch.float32)
    loss_fn = nn.CrossEntropyLoss(weight=w)
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    for ep in range(epochs):
        net.train()
        order = rng.permutation(len(tracks))
        tot = 0.0
        for i in range(0, len(order), batch):
            idx = order[i:i + batch]
            xs = [torch.from_numpy(x) for x in make_inputs([tracks[j] for j in idx], rng, cols, scaler, True, crop)]
            loss = loss_fn(net(xs), torch.from_numpy(ys[idx]))
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            tot += loss.item() * len(idx)
        sched.step()
        if log and (ep % 5 == 4 or ep == epochs - 1):
            log(f"    epoch {ep + 1}/{epochs} loss {tot / len(tracks):.3f}")
    return net


def gru_predict(net, tracks, cols, scaler):
    torch, _, _ = gru_parts()
    net.eval()
    with torch.no_grad():
        xs = [torch.from_numpy(x) for x in make_inputs(tracks, None, cols, scaler, False, None)]
        out = [net(xs[i:i + 256]).argmax(1).numpy() for i in range(0, len(xs), 256)]
    return np.concatenate(out)


# ---------------------------------------------------------------- metrics

def metrics(y, p):
    from sklearn.metrics import confusion_matrix, f1_score, recall_score
    return {"macro_f1": float(f1_score(y, p, labels=range(4), average="macro", zero_division=0)),
            "recall_orientierung": float(recall_score(y, p, labels=[0], average="macro", zero_division=0)),
            "accuracy": float((np.asarray(y) == np.asarray(p)).mean()),
            "confusion": confusion_matrix(y, p, labels=range(4)).tolist()}


def cluster_ci(y, p, seqs, key, n=2000, seed=0):
    """95 % interval of a metric by resampling whole validation sequences."""
    rng = np.random.default_rng(seed)
    y, p, seqs = np.asarray(y), np.asarray(p), np.asarray(seqs)
    groups = [np.flatnonzero(seqs == s) for s in np.unique(seqs)]
    vals = []
    for _ in range(n):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        vals.append(metrics(y[idx], p[idx])[key])
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def git_hash():
    h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "src"], cwd=ROOT, capture_output=True, text=True).stdout
    return h + ("-dirty" if dirty.strip() else "")


def subset(train, size, seed):
    """Stratified subset of `size` hand labels (all for size 0)."""
    if not size or size >= len(train):
        return list(train)
    rng = np.random.default_rng(1000 + seed)
    ys = np.array([t["y"] for t in train])
    pick = []
    for c in range(4):
        idx = np.flatnonzero(ys == c)
        k = max(1, int(round(size * len(idx) / len(ys))))
        pick += list(rng.choice(idx, min(k, len(idx)), replace=False))
    return [train[i] for i in sorted(pick)]


# ---------------------------------------------------------------- experiment

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--sizes", type=int, nargs="+", default=[25, 50, 100, 0])
    ap.add_argument("--labels", choices=["own", "final"], default="own")
    ap.add_argument("--models", nargs="+", choices=MODELS, default=MODELS)
    ap.add_argument("--pre-epochs", type=int, default=30)
    ap.add_argument("--fine-epochs", type=int, default=60)
    ap.add_argument("--threads", type=int, default=0, help="torch threads (0 = default)")
    ap.add_argument("--group", default=None, help="output folder under outputs/runs/ (default: timestamp)")
    args = ap.parse_args()

    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    group = RUNS / (args.group or datetime.now().strftime("%Y-%m-%d_%H%M"))
    group.mkdir(parents=True, exist_ok=True)
    logf = open(group / "log.txt", "a")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n")
        logf.flush()

    train, val = hand_labels("train", args.labels), hand_labels("val", args.labels)
    yv, sv = [t["y"] for t in val], [t["seq"] for t in val]
    githash = git_hash()
    log(f"git {githash}, labels {args.labels}: train {len(train)} {dict(Counter(CLASSES[t['y']] for t in train))}, "
        f"val {len(val)} {dict(Counter(CLASSES[t['y']] for t in val))}")
    results = []

    def record(model, size, seed, pred, extra=None):
        m = metrics(yv, pred)
        res = {"model": model, "size": size, "seed": seed, "n_train": n_train, "labels": args.labels, "git": githash,
               "config": {**vars(args), **(extra or {})}, "val": m,
               "predictions": {t["id"]: CLASSES[int(q)] for t, q in zip(val, pred)}}
        (group / f"{model}_n{size}_s{seed}.json").write_text(json.dumps(res, indent=1))
        results.append(res)
        log(f"  {model:12s} n={n_train:3d} seed {seed}: macro-F1 {m['macro_f1']:.3f}, "
            f"recall orient. {m['recall_orientierung']:.3f}, acc {m['accuracy']:.3f}")
        return m

    # rule baseline: no learning curve for the fixed one, the tuned one is fitted on each training subset
    n_train = len(train)
    if "rule_fixed" in args.models:
        record("rule_fixed", 0, 0, np.array([rule_predict(t) for t in val]), {"straight": 0.5, "dur": 0.4})
    grid = [(s, d) for s in np.arange(0.2, 0.95, 0.05) for d in np.arange(0.1, 1.6, 0.1)]

    gru_models = [m for m in args.models if m.startswith("gru")]
    pre = {}
    if gru_models:
        torch, nn, Net = gru_parts()
        if args.threads:
            torch.set_num_threads(args.threads)
        unlabeled = all_tracks("train")
        log(f"pretraining set: {len(unlabeled)} train tracks, self-labels {dict(Counter(SELF[t['y']] for t in unlabeled))}")
        scaler = Scaler([channels(to_entrance(t["xy"], t["seq"][3:7]), t["t"]) for t in unlabeled])
        cols_of = {"gru": list(range(7)), "gru_scratch": list(range(7)), "gru_shape": list(range(2, 7))}
        for seed in range(args.seeds):
            for kind, cols in (("full", cols_of["gru"]), ("shape", cols_of["gru_shape"])):
                if (kind == "full" and "gru" not in gru_models) or (kind == "shape" and "gru_shape" not in gru_models):
                    continue
                path = group / f"pretrained_{kind}_s{seed}.pt"
                torch.manual_seed(seed)
                net = Net(len(cols), len(SELF))
                if path.exists():
                    net.load_state_dict(torch.load(path))
                else:
                    t0 = time.time()
                    log(f"pretrain {kind} seed {seed}")
                    fit_gru(net, unlabeled, cols, scaler, seed, args.pre_epochs, 2e-3, (0.5, 1.0), batch=64, log=log)
                    torch.save(net.state_dict(), path)
                    log(f"  done in {time.time() - t0:.0f} s")
                pre[kind, seed] = net.state_dict()

    for size in args.sizes:
        for seed in range(args.seeds):
            tr = subset(train, size, seed)
            n_train = len(tr)
            ys = np.array([t["y"] for t in tr])
            log(f"size {size or 'all'} (n={n_train}) seed {seed}")
            if "rule" in args.models:
                acc = [(metrics(ys, [rule_predict(t, s, d) for t in tr])["macro_f1"], s, d) for s, d in grid]
                _, s, d = max(acc)
                record("rule", size, seed, np.array([rule_predict(t, s, d) for t in val]),
                       {"straight": float(s), "dur": float(d)})
            if {"logreg", "gbm"} & set(args.models):
                X = np.array([feature_vector(t) for t in tr], float)
                Xv = np.array([feature_vector(t) for t in val], float)
                cnt = np.bincount(ys, minlength=4).clip(1, None)
                sw = (len(ys) / (4 * cnt))[ys]
                if "logreg" in args.models:
                    lr = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"))
                    record("logreg", size, seed, lr.fit(X, ys).predict(Xv))
                if "gbm" in args.models:
                    gb = GradientBoostingClassifier(n_estimators=200, max_depth=2, learning_rate=0.05, subsample=0.8,
                                                    random_state=seed)
                    record("gbm", size, seed, gb.fit(X, ys, sample_weight=sw).predict(Xv))
            for model in gru_models:
                cols = cols_of[model]
                torch.manual_seed(seed)
                net = Net(len(cols), len(SELF))
                if model != "gru_scratch":
                    net.load_state_dict(pre["shape" if model == "gru_shape" else "full", seed])
                net.head = nn.Linear(net.head.in_features, len(CLASSES))
                fit_gru(net, tr, cols, scaler, seed, args.fine_epochs, 1e-3, (0.7, 1.0), batch=16)
                record(model, size, seed, gru_predict(net, val, cols, scaler))

    summary(results, val, group, log)


def summary(results, val, group, log):
    yv, sv = [t["y"] for t in val], [t["seq"] for t in val]
    lines = [f"# Klassifikation auf Validierung ({len(val)} Bahnen, {len(set(sv))} Sequenzen)", "",
             "Mittel über Seeds; 95-%-KI per Cluster-Bootstrap über Sequenzen, für den ersten Seed.", "",
             "| Modell | n Train | Seeds | Macro-F1 | KI | Recall Orientierung | KI | Accuracy |",
             "|---|---|---|---|---|---|---|---|"]
    keys = sorted({(r["model"], r["n_train"]) for r in results}, key=lambda k: (MODELS.index(k[0]), k[1]))
    for model, n in keys:
        rs = [r for r in results if r["model"] == model and r["n_train"] == n]
        if not rs:
            continue
        p0 = [CLASSES.index(rs[0]["predictions"][t["id"]]) for t in val]
        ci_f = cluster_ci(yv, p0, sv, "macro_f1")
        ci_r = cluster_ci(yv, p0, sv, "recall_orientierung")
        f = np.mean([r["val"]["macro_f1"] for r in rs]), np.std([r["val"]["macro_f1"] for r in rs])
        rc = np.mean([r["val"]["recall_orientierung"] for r in rs])
        acc = np.mean([r["val"]["accuracy"] for r in rs])
        lines.append(f"| {model} | {n} | {len(rs)} | {f[0]:.3f} ± {f[1]:.3f} | {ci_f[0]:.2f}–{ci_f[1]:.2f} | "
                     f"{rc:.3f} | {ci_r[0]:.2f}–{ci_r[1]:.2f} | {acc:.3f} |")
    # confusion of the best model with all labels, summed over seeds
    full = [r for r in results if r["size"] == 0 or r["model"] == "rule_fixed"]
    if full:
        best = max({r["model"] for r in full},
                   key=lambda m: np.mean([r["val"]["macro_f1"] for r in full if r["model"] == m]))
        conf = np.sum([r["val"]["confusion"] for r in full if r["model"] == best], axis=0)
        lines += ["", f"Konfusionsmatrix `{best}` (alle Labels, Summe über Seeds; Zeile = Label, Spalte = Vorhersage):", "",
                  "| | " + " | ".join(CLASSES) + " |", "|---" * 5 + "|"]
        lines += [f"| {CLASSES[i]} | " + " | ".join(str(v) for v in row) + " |" for i, row in enumerate(conf)]
    (group / "summary.md").write_text("\n".join(lines) + "\n")
    log("\n".join(lines))


if __name__ == "__main__":
    main()
