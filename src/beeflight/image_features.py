"""Candidate 2 (Nur-Bild): frozen DINOv2 features with a linear classifier (Oquab et al. 2023).

From the paper: frozen ViT-S/14 without fine-tuning; 8 evenly spaced frames, whose features are averaged (UCF, Kinetics)
or concatenated (SSv2); a linear layer trained with SGD for 12500 iterations; grid search (Appendix B.3) over the
learning rate, 1 or 4 output layers, and the class token alone or with the averaged patch tokens.

Not from the paper, and our own choices: the crop around the bee (no paper covers a 30 px object; chosen on val among
CROPS), full-batch SGD (B.3 names no batch size, and the features are cached), no random-resized-crop augmentation
(features are computed once), and ViT-S because the project runs on CPU.

The weights are pretrained elsewhere; nothing is trained on hive videos except the linear layer, on labels/train.jsonl.
Test splits read only labels/queue_<split>.json, never votes or labels.

Loading the backbone downloads code and weights through torch.hub and asks for confirmation the first time.

Usage: beeflight-dinov2 extract --split train
       beeflight-dinov2 extract --split val
       beeflight-dinov2 sweep                 # chooses crop and classifier on val, writes sweep.json
       beeflight-dinov2 fit --predict val     # 5 seeds of the chosen configuration
"""
import argparse
import itertools
import json
from collections import defaultdict

import numpy as np

from . import metrics as M
from .resnet import LABELS, read_train
from .splits import ROOT

OUT = ROOT / "outputs" / "models" / "dinov2"
CACHE = ROOT / "outputs" / "features" / "dinov2"
N_FRAMES = 8
INPUT = 224
CROPS = (64, 128, 224)  # full-resolution pixels, own choice
ITERATIONS = 12500
LEARNING_RATES = (0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)  # ImageNet, as the pretrained weights expect
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
SPLITS = ("train", "val", "test_same_hive", "test_other_hive")


def evenly_spaced(n, k=N_FRAMES):
    """k positions spread over a series of length n; short series repeat points."""
    return np.linspace(0, n - 1, k).round().astype(int)


def center_of(row, i):
    """Point i of a trajectory in full-resolution frame coordinates."""
    x, y = row["xy"][i]
    return x / row["scale"], (y + row["top"]) / row["scale"]


def crop_at(image, x, y, size):
    """Square of side `size` centred on (x, y); parts outside the frame repeat the border."""
    import cv2

    x0, y0 = int(round(x)) - size // 2, int(round(y)) - size // 2
    h, w = image.shape[:2]
    pad = [max(0, -y0), max(0, y0 + size - h), max(0, -x0), max(0, x0 + size - w)]
    if any(pad):
        image = cv2.copyMakeBorder(image, *pad, cv2.BORDER_REPLICATE)
        x0, y0 = x0 + pad[2], y0 + pad[0]
    return image[y0:y0 + size, x0:x0 + size]


def to_input(crops):
    """Crops (BGR, uint8) -> normalized array (b, 3, INPUT, INPUT)."""
    import cv2

    out = [cv2.resize(c[:, :, ::-1], (INPUT, INPUT), interpolation=cv2.INTER_CUBIC) for c in crops]
    return ((np.stack(out).astype(np.float32) / 255 - MEAN) / STD).transpose(0, 3, 1, 2)


def rows_of(split):
    """The labelled rows of train and val; for test only the queue, so no test label is opened."""
    if split == "train":
        return read_train()
    if split == "val":
        rows = [json.loads(line) for line in (LABELS / "val.jsonl").read_text().splitlines() if line.strip()]
        return [r for r in rows if r.get("label") in M.CLASSES]
    return json.loads((LABELS / f"queue_{split}.json").read_text())["items"]


def load_backbone():
    import torch

    return torch.hub.load("facebookresearch/dinov2", "dinov2_vits14", trust_repo="check").eval()


def embed(net, batch):
    """(b, 3, H, W) -> (b, layers, tokens, dim): the last 4 layers, token 0 = class, token 1 = averaged patches."""
    import torch

    with torch.inference_mode():
        layers = net.get_intermediate_layers(torch.from_numpy(batch), n=4, return_class_token=True)
    return np.stack([torch.stack([cls, patches.mean(dim=1)], dim=1).numpy() for patches, cls in layers], axis=1)


def extract(split, net=None, batch=32):
    """Writes CACHE/<split>_c<crop>.npz with ids and features of shape (n, frames, layers, tokens, dim)."""
    from .detector import color_frames

    rows = rows_of(split)
    net = net or load_backbone()
    by_seq = defaultdict(list)
    for n, row in enumerate(rows):
        for f, i in enumerate(evenly_spaced(len(row["t"]))):
            by_seq[row["seq"]].append((int(row["t"][i]), n, f, int(i)))
    feats = {c: None for c in CROPS}
    for done, (seq, wanted) in enumerate(sorted(by_seq.items())):
        at_frame = defaultdict(list)
        for frame, n, f, i in wanted:
            at_frame[frame].append((n, f, i))
        pending = {c: [] for c in CROPS}
        where = []
        last = max(at_frame)
        for frame, image in color_frames(seq, 0, set(at_frame)):
            for n, f, i in at_frame.get(frame, []):
                x, y = center_of(rows[n], i)
                where.append((n, f))
                for c in CROPS:
                    pending[c].append(crop_at(image, x, y, c).copy())
            if frame >= last:
                break
        if len(where) != len(wanted):
            raise SystemExit(f"{seq}: found {len(where)} of {len(wanted)} frames")
        for c in CROPS:
            parts = [embed(net, to_input(pending[c][k:k + batch])) for k in range(0, len(where), batch)]
            out = np.concatenate(parts)
            if feats[c] is None:
                feats[c] = np.zeros((len(rows), N_FRAMES, *out.shape[1:]), dtype=np.float32)
            for (n, f), v in zip(where, out):
                feats[c][n, f] = v
        print(f"{split}: {done + 1}/{len(by_seq)} {seq}", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    for c in CROPS:
        np.savez(CACHE / f"{split}_c{c}.npz", ids=np.array([r["id"] for r in rows]), feats=feats[c])


def load_features(split, crop):
    data = np.load(CACHE / f"{split}_c{crop}.npz")
    return [str(i) for i in data["ids"]], data["feats"]


def build_x(feats, layers, tokens, frames):
    """(n, frames, layers, tokens, dim) -> (n, d). `layers` 1 or 4; `tokens` cls or cls+avg; `frames` avg or concat."""
    x = feats[:, :, -layers:, :(1 if tokens == "cls" else 2)]
    x = x.reshape(*x.shape[:2], -1)
    return x.mean(axis=1) if frames == "avg" else x.reshape(len(x), -1)


def train_linear(x, y, lrs=LEARNING_RATES, iterations=ITERATIONS, seed=0, n_classes=len(M.CLASSES)):
    """Full-batch SGD on softmax regression, one classifier per learning rate. -> (W (L, d, k), b (L, k)).

    A classifier that diverges ends up with non-finite weights and is never chosen."""
    import torch

    x = torch.as_tensor(x, dtype=torch.float32)
    one_hot = torch.eye(n_classes)[torch.as_tensor(y, dtype=torch.long)]
    gen = torch.Generator().manual_seed(seed)
    rates = torch.tensor(lrs, dtype=torch.float32)
    w = 0.01 * torch.randn(len(lrs), x.shape[1], n_classes, generator=gen)
    b = torch.zeros(len(lrs), n_classes)
    for _ in range(iterations):
        logits = torch.einsum("nd,ldk->lnk", x, w) + b[:, None]
        error = logits.softmax(dim=2) - one_hot
        w -= rates[:, None, None] * torch.einsum("nd,lnk->ldk", x, error) / len(x)
        b -= rates[:, None] * error.mean(dim=1)
    return w.numpy(), b.numpy()


def probabilities(x, w, b):
    """(n, d) with one classifier (d, k), (k) -> (n, k)."""
    logits = x @ w + b
    logits = logits - logits.max(axis=1, keepdims=True)
    p = np.exp(logits)
    return p / p.sum(axis=1, keepdims=True)


def configurations():
    return [dict(crop=c, layers=l, tokens=t, frames=f)
            for c, l, t, f in itertools.product(CROPS, (1, 4), ("cls", "cls+avg"), ("avg", "concat"))]


def labelled(split):
    return {r["id"]: r["label"] for r in rows_of(split)}


def sweep(iterations=ITERATIONS):
    """The whole grid at seed 0: fit on train, score on val by Balanced Accuracy. Writes OUT/sweep.json."""
    train_y, val_y = labelled("train"), labelled("val")
    results = []
    for config in configurations():
        ids, feats = load_features("train", config["crop"])
        vids, vfeats = load_features("val", config["crop"])
        keys = dict(layers=config["layers"], tokens=config["tokens"], frames=config["frames"])
        w, b = train_linear(build_x(feats, **keys), M.encode([train_y[i] for i in ids]), iterations=iterations)
        x_val, y_val = build_x(vfeats, **keys), M.encode([val_y[i] for i in vids])
        for k, lr in enumerate(LEARNING_RATES):
            if np.isfinite(w[k]).all():
                pred = probabilities(x_val, w[k], b[k]).argmax(axis=1)
                results.append({**config, "lr": lr, "val_balanced_accuracy": float(M.balanced_accuracy(y_val, pred))})
        print(config, "best so far", max(r["val_balanced_accuracy"] for r in results), flush=True)
    results.sort(key=lambda r: -r["val_balanced_accuracy"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sweep.json").write_text(json.dumps(results, indent=1))
    return results


def fit(split, seeds=5, iterations=ITERATIONS):
    """Trains the configuration on top of sweep.json and writes one prediction file per seed."""
    best = json.loads((OUT / "sweep.json").read_text())[0]
    keys = dict(layers=best["layers"], tokens=best["tokens"], frames=best["frames"])
    train_y = labelled("train")
    ids, feats = load_features("train", best["crop"])
    pids, pfeats = load_features(split, best["crop"])
    x, y, xp = build_x(feats, **keys), M.encode([train_y[i] for i in ids]), build_x(pfeats, **keys)
    out = OUT / split
    out.mkdir(parents=True, exist_ok=True)
    for seed in range(seeds):
        w, b = train_linear(x, y, lrs=(best["lr"],), iterations=iterations, seed=seed)
        probs = probabilities(xp, w[0], b[0])
        run = {"model": "dinov2", "seed": seed, "config": best,
               "predictions": {i: M.CLASSES[int(k)] for i, k in zip(pids, probs.argmax(axis=1))},
               "probabilities": {i: {c: float(v) for c, v in zip(M.CLASSES, p)} for i, p in zip(pids, probs)}}
        (out / f"dinov2_s{seed}.json").write_text(json.dumps(run))
        print(f"seed {seed}: {len(pids)} predictions -> {out}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["extract", "sweep", "fit"])
    ap.add_argument("--split", default="val", choices=SPLITS)
    ap.add_argument("--predict", default="val", choices=SPLITS)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--iterations", type=int, default=ITERATIONS)
    ap.add_argument("--threads", type=int, default=0, help="CPU threads for torch (0 = default)")
    args = ap.parse_args(argv)
    import torch

    if args.threads:
        torch.set_num_threads(args.threads)
    if args.action == "extract":
        extract(args.split)
    elif args.action == "sweep":
        print(json.dumps(sweep(args.iterations)[:5], indent=1))
    else:
        fit(args.predict, args.seeds, args.iterations)


if __name__ == "__main__":
    main()
