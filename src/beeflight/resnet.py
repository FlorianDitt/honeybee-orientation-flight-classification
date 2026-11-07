"""Candidate 1 (Nur-Bahn): ResNet on the trajectory, as in Fawaz et al. 2019, section "Residual Network".

Three residual blocks, each with three convolutions of 64 filters and lengths 8, 5, 3 with batch normalization
before ReLU, then global average pooling and a linear classifier. Adam with learning rate 0.001, batch size 16, 1500
epochs; the learning rate halves after 50 epochs without a better training loss; the checkpoint with the best training
loss is kept. Each channel is linearly interpolated to the longest series of the training labels.

From the project instead of the paper: the channels x, y, dx, dy, |v|, dtheta relative to the entrance
(docs/methode.md) and standardizing them with the means of the training labels.

Trained on labels/train.jsonl only. Every trajectory of labels/queue_<split>.json gets a prediction, so no test label
is read. Writes outputs/models/resnet/resnet_s<seed>.pt and outputs/models/resnet/<split>/resnet_s<seed>.json.

Usage: beeflight-resnet [--seeds 5] [--predict val] [--epochs 1500] [--threads 4]
       beeflight-resnet --predict test_same_hive   # uses saved models, trains only what is missing
"""
import argparse
import hashlib
import json
import time

import numpy as np

from . import metrics as M
from .evaluate import flight_zone
from .splits import ROOT

LABELS = ROOT / "labels"
OUT = ROOT / "outputs" / "models" / "resnet"
N_CHANNELS = 6
# entrance reference point (middle of the lower board edge) and board width at half resolution.
# rec2125 is still missing: docs/roadmap.md sets it from a single frame at the freeze, not from results.
ENTRANCE = {"2123": dict(x=270.0, width=540.0)}


def to_entrance(xy, rec):
    if rec not in ENTRANCE:
        raise ValueError(f"no entrance position for rec{rec}: set it from a single frame (docs/roadmap.md, phase 5)")
    _, bottom = flight_zone(rec)
    e = ENTRANCE[rec]
    xy = np.asarray(xy, dtype=float)
    return np.column_stack([(xy[:, 0] - e["x"]) / e["width"], (xy[:, 1] - bottom) / e["width"]])


def channels(pos, t):
    """(n, 6): x, y, dx, dy, |v|, dtheta; velocities per frame, in board widths times 50."""
    t = np.asarray(t, dtype=float)
    dt = np.diff(t, prepend=t[0] - 1).clip(1, None)
    d = np.diff(pos, axis=0, prepend=pos[:1]) / dt[:, None]
    v = np.linalg.norm(d, axis=1)
    theta = np.arctan2(d[:, 1], d[:, 0])
    dtheta = np.angle(np.exp(1j * np.diff(theta, prepend=theta[0])))
    dtheta[v < 1e-3] = 0.0
    return np.column_stack([pos, d * 50, v * 50, dtheta]).astype(np.float32)


def interpolate(series, length):
    """(n, c) -> (length, c), each channel linearly interpolated."""
    old, new = np.linspace(0, 1, len(series)), np.linspace(0, 1, length)
    return np.column_stack([np.interp(new, old, series[:, c]) for c in range(series.shape[1])]).astype(np.float32)


def series_of(row):
    return channels(to_entrance(row["xy"], row["seq"][3:7]), row["t"])


def prepare(rows, length, mean, std):
    """-> (n, channels, length) array for torch."""
    data = np.stack([interpolate(series_of(r), length) for r in rows])
    return np.transpose((data - mean) / std, (0, 2, 1)).astype(np.float32)


def build_net(n_classes=len(M.CLASSES), n_channels=N_CHANNELS):
    from torch import nn

    class Block(nn.Module):
        def __init__(self, c_in, c_out):
            super().__init__()
            layers = []
            for i, kernel in enumerate((8, 5, 3)):
                layers += [nn.Conv1d(c_in if i == 0 else c_out, c_out, kernel, padding="same"), nn.BatchNorm1d(c_out)]
                if i < 2:
                    layers.append(nn.ReLU())
            self.path = nn.Sequential(*layers)
            self.short = nn.BatchNorm1d(c_out) if c_in == c_out else nn.Sequential(nn.Conv1d(c_in, c_out, 1),
                                                                                  nn.BatchNorm1d(c_out))
            self.relu = nn.ReLU()

        def forward(self, x):
            return self.relu(self.path(x) + self.short(x))

    class ResNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.blocks = nn.Sequential(Block(n_channels, 64), Block(64, 64), Block(64, 64))
            self.head = nn.Linear(64, n_classes)

        def encode(self, x):
            return self.blocks(x).mean(dim=2)  # global average pooling

        def forward(self, x):
            return self.head(self.encode(x))

    return ResNet()


def train(x, y, seed, epochs=1500, batch=16, log=None):
    """-> network with the checkpoint of the lowest training loss."""
    import torch
    from torch import nn

    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    net = build_net()
    opt = torch.optim.Adam(net.parameters(), lr=0.001)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=50)
    loss_fn = nn.CrossEntropyLoss()
    x, y = torch.from_numpy(x), torch.as_tensor(y, dtype=torch.long)
    best, best_state = float("inf"), None
    start = time.time()
    for epoch in range(epochs):
        net.train()
        total = 0.0
        for idx in np.array_split(rng.permutation(len(x)), max(1, int(np.ceil(len(x) / batch)))):
            idx = torch.as_tensor(idx)
            opt.zero_grad()
            loss = loss_fn(net(x[idx]), y[idx])
            loss.backward()
            opt.step()
            total += loss.item() * len(idx)
        total /= len(x)
        sched.step(total)
        if total < best:
            best, best_state = total, {k: v.detach().clone() for k, v in net.state_dict().items()}
        if log and (epoch + 1) % 50 == 0:
            log(f"  seed {seed} epoch {epoch + 1}/{epochs}: train loss {total:.4f}, best {best:.4f}, "
                f"lr {opt.param_groups[0]['lr']:.2g}, {time.time() - start:.0f} s")
    net.load_state_dict(best_state)
    return net


def predict(net, x, batch=64):
    import torch

    net.eval()
    with torch.no_grad():
        return np.concatenate([net(torch.from_numpy(x[i:i + batch])).softmax(dim=1).numpy()
                               for i in range(0, len(x), batch)])


def read_train():
    rows = [json.loads(line) for line in (LABELS / "train.jsonl").read_text().splitlines() if line.strip()]
    return [r for r in rows if r.get("label") in M.CLASSES]


def labels_hash(rows):
    text = json.dumps(sorted((r["id"], r["label"]) for r in rows))
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def scaling(rows):
    """Longest series, and channel means and standard deviations of the training labels."""
    series = [series_of(r) for r in rows]
    points = np.concatenate(series)
    return max(len(s) for s in series), points.mean(axis=0), points.std(axis=0) + 1e-6


def fit_seed(train_rows, seed, epochs, out, log=print):
    """Train one seed, or load it if it exists for the same labels and epochs. -> (net, length, mean, std)"""
    import torch

    path = out / f"resnet_s{seed}.pt"
    tag = labels_hash(train_rows)
    if path.exists():
        saved = torch.load(path, weights_only=False)
        if saved["labels_hash"] == tag and saved["epochs"] == epochs:
            net = build_net()
            net.load_state_dict(saved["state"])
            log(f"seed {seed}: loaded {path}")
            return net, saved["length"], saved["mean"], saved["std"]
    length, mean, std = scaling(train_rows)
    x = prepare(train_rows, length, mean, std)
    y = M.encode([r["label"] for r in train_rows])
    log(f"seed {seed}: training on {len(y)} labels, length {length}, {epochs} epochs")
    net = train(x, y, seed, epochs, log=log)
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"state": net.state_dict(), "length": length, "mean": mean, "std": std, "labels_hash": tag,
                "epochs": epochs, "seed": seed}, path)
    return net, length, mean, std


def run_file(net, rows, length, mean, std, seed, epochs, tag):
    probs = predict(net, prepare(rows, length, mean, std))
    return {"model": "resnet", "seed": seed, "config": {"epochs": epochs, "length": length, "labels_hash": tag},
            "predictions": {r["id"]: M.CLASSES[int(i)] for r, i in zip(rows, probs.argmax(axis=1))},
            "probabilities": {r["id"]: {c: float(v) for c, v in zip(M.CLASSES, p)} for r, p in zip(rows, probs)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=1500)
    ap.add_argument("--predict", default="val", choices=["train", "val", "test_same_hive", "test_other_hive"])
    ap.add_argument("--threads", type=int, default=0, help="CPU threads for torch (0 = default)")
    ap.add_argument("--out", help="output directory (default outputs/models/resnet)")
    args = ap.parse_args(argv)
    import torch
    from pathlib import Path

    if args.threads:
        torch.set_num_threads(args.threads)
    out = Path(args.out) if args.out else OUT
    train_rows = read_train()
    rows = json.loads((LABELS / f"queue_{args.predict}.json").read_text())["items"]
    tag = labels_hash(train_rows)
    (out / args.predict).mkdir(parents=True, exist_ok=True)
    for seed in range(args.seeds):
        net, length, mean, std = fit_seed(train_rows, seed, args.epochs, out, log=lambda s: print(s, flush=True))
        run = run_file(net, rows, length, mean, std, seed, args.epochs, tag)
        (out / args.predict / f"resnet_s{seed}.json").write_text(json.dumps(run))
        print(f"seed {seed}: {len(rows)} predictions -> {out / args.predict}", flush=True)


if __name__ == "__main__":
    main()
