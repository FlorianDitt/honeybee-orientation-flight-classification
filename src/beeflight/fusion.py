"""Candidates 3 and 4: late fusion of the trajectory ResNet and the frozen DINOv2 features (Wang et al. 2020).

From the paper: concatenation of the branch features, then two fully connected layers with ReLU (the first maps 2n to n,
the second n to n) and a linear classifier. Candidate 4 is Offline Gradient-Blending (Algorithms 1 and 2): one head each
on trajectory, image and fused features, loss = sum w_i L_i with w_i = G_i / O_i^2 / Z, computed once and then fixed.
G and O come from a hold-out V of the training labels and a subset T' of the rest, measured with accuracy, which the
paper calls equally effective as the loss.

Not from the paper, and our own choices:
- the image branch is frozen and only a linear layer maps it to n = 64 dimensions, whereas Wang trains all branches;
- optimizer and schedule are those of the ResNet (Fawaz 2019), so that the candidates differ only in the branches;
- V holds whole sequences (20 % of them), because trajectories of one sequence are not independent;
- T' has the size of V, since the paper only says "a subset";
- after estimating the weights the final model trains on all training labels, as candidates 1 to 3 do;
- the prediction is the fused head, which the paper's text doesn't specify;
- G <= 0 gives weight 0 and O is floored at MIN_O, since Eq. 3 is undefined there.

Only labels/train.jsonl trains and estimates; val is used by the sweep (crop and classifier) and for predictions.

Usage: beeflight-fusion --mode concat [--seeds 5] [--predict val] [--epochs 1500] [--threads 4]
       beeflight-fusion --mode gblend
"""
import argparse
import hashlib
import json
import time

import numpy as np

from . import image_features as F
from . import metrics as M
from . import resnet as R
from .splits import ROOT

OUT = ROOT / "outputs" / "models" / "fusion"
N = 64
HOLDOUT = 0.2
MIN_O = 0.01
CONCAT = (0.0, 0.0, 1.0)  # candidate 3 is the fused head alone


def blend_weights(g, o, min_o=MIN_O):
    """w_i = G_i / O_i^2 / Z (Algorithm 1)."""
    g, o = np.clip(np.asarray(g, float), 0, None), np.clip(np.asarray(o, float), min_o, None)
    w = g / o ** 2
    if w.sum() == 0:
        raise ValueError("no branch generalizes: all G <= 0")
    return w / w.sum()


def holdout(rows, share=HOLDOUT, seed=0):
    """-> (indices T, indices T', indices V): V holds whole sequences, T' is a subset of T of the size of V."""
    rng = np.random.default_rng(seed)
    seqs = sorted({r["seq"] for r in rows})
    held = set(rng.permutation(seqs)[:max(1, round(len(seqs) * share))].tolist())
    v = np.array([i for i, r in enumerate(rows) if r["seq"] in held])
    t = np.array([i for i, r in enumerate(rows) if r["seq"] not in held])
    return t, rng.permutation(t)[:len(v)], v


def build_fusion(image_dim, n_classes=len(M.CLASSES), n=N):
    from torch import nn

    class Fusion(nn.Module):
        def __init__(self):
            super().__init__()
            self.trajectory = R.build_net(n_classes)
            self.image = nn.Linear(image_dim, n)
            self.fused = nn.Sequential(nn.Linear(2 * n, n), nn.ReLU(), nn.Linear(n, n), nn.ReLU())
            self.head_trajectory = nn.Linear(n, n_classes)
            self.head_image = nn.Linear(n, n_classes)
            self.head_fused = nn.Linear(n, n_classes)

        def forward(self, traj, image):
            import torch

            a, b = self.trajectory.encode(traj), self.image(image)
            fused = self.fused(torch.cat([a, b], dim=1))
            return self.head_trajectory(a), self.head_image(b), self.head_fused(fused)

    return Fusion()


def _train(net, traj, image, y, seed, weights, epochs, batch=16, log=None, tag=""):
    """Adam and schedule of the ResNet on the blended loss; keeps the checkpoint with the lowest training loss."""
    import torch
    from torch import nn

    rng = np.random.default_rng(seed)
    dev = R.device()
    net.to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=0.001)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=50)
    loss_fn = nn.CrossEntropyLoss()
    traj, image = torch.from_numpy(traj).to(dev), torch.from_numpy(image).to(dev)
    y = torch.as_tensor(y, dtype=torch.long, device=dev)
    best, best_state = float("inf"), None
    start = time.time()
    for epoch in range(epochs):
        net.train()
        total = 0.0
        for idx in np.array_split(rng.permutation(len(y)), max(1, int(np.ceil(len(y) / batch)))):
            idx = torch.as_tensor(idx, device=dev)
            opt.zero_grad()
            loss = sum(w * loss_fn(out, y[idx]) for w, out in zip(weights, net(traj[idx], image[idx])) if w)
            loss.backward()
            opt.step()
            total += loss.item() * len(idx)
        total /= len(y)
        sched.step(total)
        if total < best:
            best, best_state = total, {k: v.detach().clone() for k, v in net.state_dict().items()}
        if log and (epoch + 1) % 50 == 0:
            log(f"  {tag} epoch {epoch + 1}/{epochs}: train loss {total:.4f}, best {best:.4f}, "
                f"lr {opt.param_groups[0]['lr']:.2g}, {time.time() - start:.0f} s")
    net.load_state_dict(best_state)
    return net.cpu()


def head_probabilities(net, traj, image, head=2, batch=64):
    import torch

    dev = next(net.parameters()).device
    net.eval()
    with torch.no_grad():
        return np.concatenate([net(torch.from_numpy(traj[i:i + batch]).to(dev), torch.from_numpy(image[i:i + batch])
                                   .to(dev))[head].softmax(dim=1).cpu().numpy() for i in range(0, len(traj), batch)])


def _fresh(image_dim, seed):
    import torch

    torch.manual_seed(seed)
    return build_fusion(image_dim)


def estimate_weights(traj, image, y, rows, epochs, seed=0, log=print):
    """Algorithms 1 and 2 with N = 0: one trial per head from the same initial model, on T; G and O on V and T'."""
    t, t_sub, v = holdout(rows, seed=seed)

    def accuracies(net, head):
        return [float((head_probabilities(net, traj[s], image[s], head).argmax(axis=1) == y[s]).mean())
                for s in (t_sub, v)]

    gs, os_ = [], []
    for head in range(3):
        before = accuracies(_fresh(image.shape[1], seed), head)
        trial = tuple(float(k == head) for k in range(3))
        net = _train(_fresh(image.shape[1], seed), traj[t], image[t], y[t], seed, trial, epochs, log=log, tag=f"trial {head}")
        after = accuracies(net, head)
        gs.append(after[1] - before[1])
        os_.append((after[0] - after[1]) - (before[0] - before[1]))
        log(f"head {head}: train subset {before[0]:.3f} -> {after[0]:.3f}, hold-out {before[1]:.3f} -> {after[1]:.3f}")
    return {"weights": blend_weights(gs, os_).tolist(), "G": gs, "O": os_, "n_holdout": len(v), "n_train": len(t)}


def features_for(rows, split, config):
    """Image features in the order of `rows`."""
    ids, feats = F.load_features(split, config["crop"])
    x = F.build_x(feats, config["layers"], config["tokens"], config["frames"])
    at = {i: k for k, i in enumerate(ids)}
    return x[[at[r["id"]] for r in rows]]


def fingerprint(train_rows, config, epochs):
    text = json.dumps([R.labels_hash(train_rows), epochs, {k: config[k] for k in ("crop", "layers", "tokens", "frames")}])
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, choices=["concat", "gblend"])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=1500)
    ap.add_argument("--predict", default="val", choices=F.SPLITS)
    ap.add_argument("--threads", type=int, default=0, help="CPU threads for torch (0 = default)")
    args = ap.parse_args(argv)
    import torch

    if args.threads:
        torch.set_num_threads(args.threads)
    config = json.loads((F.OUT / "sweep.json").read_text())[0]
    rows = R.read_train()
    tag = fingerprint(rows, config, args.epochs)
    length, mean, std = R.scaling(rows)
    traj, image = R.prepare(rows, length, mean, std), features_for(rows, "train", config)
    y = M.encode([r["label"] for r in rows])
    OUT.mkdir(parents=True, exist_ok=True)

    weights = CONCAT
    if args.mode == "gblend":
        path = OUT / "gblend_weights.json"
        saved = json.loads(path.read_text()) if path.exists() else {}
        if saved.get("tag") != tag:
            saved = {**estimate_weights(traj, image, y, rows, args.epochs), "tag": tag}
            path.write_text(json.dumps(saved, indent=1))
        weights = tuple(saved["weights"])
        print("weights (trajectory, image, fused):", weights, "G", saved["G"], "O", saved["O"], flush=True)

    name = f"fusion_{args.mode}"
    target = F.rows_of(args.predict)
    traj_p, image_p = R.prepare(target, length, mean, std), features_for(target, args.predict, config)
    (OUT / args.predict).mkdir(parents=True, exist_ok=True)
    for seed in range(args.seeds):
        path = OUT / f"{name}_s{seed}.pt"
        net = _fresh(image.shape[1], seed)
        saved = torch.load(path, weights_only=False) if path.exists() else None
        if saved and saved["tag"] == tag and tuple(saved["weights"]) == tuple(weights):
            net.load_state_dict(saved["state"])
            print(f"seed {seed}: loaded {path}", flush=True)
        else:
            net = _train(net, traj, image, y, seed, weights, args.epochs, log=lambda s: print(s, flush=True), tag=f"seed {seed}")
            torch.save({"state": net.state_dict(), "tag": tag, "weights": weights, "seed": seed}, path)
        probs = head_probabilities(net, traj_p, image_p)
        run = {"model": name, "seed": seed, "config": {**config, "epochs": args.epochs, "weights": weights},
               "predictions": {r["id"]: M.CLASSES[int(k)] for r, k in zip(target, probs.argmax(axis=1))},
               "probabilities": {r["id"]: {c: float(v) for c, v in zip(M.CLASSES, p)} for r, p in zip(target, probs)}}
        (OUT / args.predict / f"{name}_s{seed}.json").write_text(json.dumps(run))
        print(f"seed {seed}: {len(target)} predictions -> {OUT / args.predict}", flush=True)


if __name__ == "__main__":
    main()
