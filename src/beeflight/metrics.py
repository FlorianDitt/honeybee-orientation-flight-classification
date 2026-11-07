"""Evaluation metrics for the four-class flight classifier (docs/methode.md, section 6). No model code in here.

Conventions, fixed before the model freeze:
- y and p are integer class indices (see CLASSES), one entry per trajectory; `preds` is one row of p per seed.
- Primary metric: balanced accuracy, the unweighted mean of the class recalls (Opitz 2024, Eq. 7).
- A class without examples is left out of the balanced accuracy and macro-F1 (chance level 1/k with k classes
  present); it never counts as recall 0. The same rule holds in every bootstrap replicate.
- Macro-F1 is the mean of the per-class F1 values (Opitz 2024, Eq. 10), not the F1 of macro precision and recall.
- Undefined values (no examples, no predictions of a class) are nan, never 0.
- Indicator: share of `orientierung` among all trajectories except `artefakt`.
"""
import numpy as np
from scipy.stats import rankdata

CLASSES = ["orientierung", "sammelabflug", "anflug", "artefakt"]
ORIENTATION, ARTEFACT = CLASSES.index("orientierung"), CLASSES.index("artefakt")
MIN_EXAMPLES = 5  # fewer examples of a class: the value stays in, but is marked as too few
MIN_SEQUENCES = 10  # fewer sequences: no cluster bootstrap (4 sequences only allow 35 distinct resamples)
MIN_SEQUENCE_TRACKS = 10  # per-sequence indicator errors only if every sequence has at least this many trajectories
N_BOOTSTRAP = 2000


def encode(labels):
    """Class names -> integer indices; raises ValueError on an unknown class."""
    return np.array([CLASSES.index(c) for c in labels], dtype=int)


def confusion(y, p):
    """4 x 4 counts; row = label, column = prediction."""
    return np.bincount(4 * np.asarray(y, dtype=int) + np.asarray(p, dtype=int), minlength=16).reshape(4, 4)


def _ratio(a, b):
    return np.divide(a, b, out=np.full(np.shape(a), np.nan), where=np.asarray(b) > 0)


def mean_defined(values):
    """Mean ignoring nan; nan without any defined value."""
    values = np.asarray(values, dtype=float)
    return float(np.nan) if np.isnan(values).all() else float(np.nanmean(values))


def balanced_accuracy(y, p):
    c = confusion(y, p)
    return mean_defined(_ratio(np.diag(c).astype(float), c.sum(axis=1).astype(float)))


def accuracy(y, p):
    c = confusion(y, p)
    return float(np.diag(c).sum() / c.sum()) if c.sum() else float("nan")


def macro_f1(y, p):
    c = confusion(y, p)
    present = c.sum(axis=1) > 0
    if not present.any():
        return float("nan")
    return float((2 * np.diag(c)[present] / (c.sum(axis=1) + c.sum(axis=0))[present]).mean())


def class_recall(cls):
    def stat(y, p):
        c = confusion(y, p)
        return float(c[cls, cls] / c[cls].sum()) if c[cls].sum() else float("nan")
    return stat


def class_precision(cls):
    def stat(y, p):
        c = confusion(y, p)
        return float(c[cls, cls] / c[:, cls].sum()) if c[:, cls].sum() else float("nan")
    return stat


def class_table(y, p):
    """One dict per class: counts, recall, precision, F1 and whether it has too few examples."""
    c = confusion(y, p)
    rows = []
    for i, name in enumerate(CLASSES):
        n, predicted, correct = int(c[i].sum()), int(c[:, i].sum()), int(c[i, i])
        rows.append({"class": name, "n": n, "predicted": predicted, "correct": correct,
                     "recall": correct / n if n else float("nan"),
                     "precision": correct / predicted if predicted else float("nan"),
                     "f1": 2 * correct / (n + predicted) if n + predicted else float("nan"),
                     "too_few": n < MIN_EXAMPLES})
    return rows


def orientation_share(labels):
    """Share of orientation flights among all trajectories except artefacts; nan without valid trajectories."""
    labels = np.asarray(labels, dtype=int)
    valid = (labels != ARTEFACT).sum()
    return float((labels == ORIENTATION).sum() / valid) if valid else float("nan")


def share_error(y, p):
    """Predicted minus true share (signed: positive = the indicator overestimates)."""
    return orientation_share(p) - orientation_share(y)


def summary_stats():
    """Name -> function(y, p) of every statistic that gets an interval."""
    stats = {"balanced_accuracy": balanced_accuracy, "accuracy": accuracy, "macro_f1": macro_f1,
             "share_error": share_error}
    for i, name in enumerate(CLASSES):
        stats[f"recall_{name}"] = class_recall(i)
        stats[f"precision_{name}"] = class_precision(i)
    return stats


def seed_mean(stat, y, preds):
    """Mean of a statistic over seeds, ignoring seeds where it is undefined."""
    return mean_defined([stat(y, p) for p in preds])


def cluster_resamples(seqs, n=N_BOOTSTRAP, seed=0):
    """Index arrays that resample whole sequences with replacement."""
    seqs = np.asarray(seqs)
    groups = [np.flatnonzero(seqs == s) for s in np.unique(seqs)]
    rng = np.random.default_rng(seed)
    for _ in range(n):
        yield np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])


def _interval(values, y, resamples):
    values = np.asarray(values, dtype=float)
    defined = values[~np.isnan(values)]
    present = set(np.asarray(y).tolist())
    missing = np.mean([not present <= set(np.asarray(y)[idx].tolist()) for idx in resamples])
    return {"low": float(np.percentile(defined, 2.5)) if len(defined) else float("nan"),
            "high": float(np.percentile(defined, 97.5)) if len(defined) else float("nan"),
            "undefined_share": float(np.isnan(values).mean()), "missing_class_share": float(missing)}


def cluster_bootstrap(y, preds, seqs, stat, n=N_BOOTSTRAP, seed=0):
    """95 % percentile interval of the seed mean, resampling whole sequences."""
    y, preds = np.asarray(y), np.asarray(preds)
    resamples = list(cluster_resamples(seqs, n, seed))
    return _interval([seed_mean(stat, y[idx], preds[:, idx]) for idx in resamples], y, resamples)


def paired_difference(y, preds_a, preds_b, seqs, stat, n=N_BOOTSTRAP, seed=0):
    """Difference a - b of the seed means, with its interval on the same resampled trajectories."""
    y, preds_a, preds_b = np.asarray(y), np.asarray(preds_a), np.asarray(preds_b)
    resamples = list(cluster_resamples(seqs, n, seed))
    values = [seed_mean(stat, y[idx], preds_a[:, idx]) - seed_mean(stat, y[idx], preds_b[:, idx]) for idx in resamples]
    return {"difference": seed_mean(stat, y, preds_a) - seed_mean(stat, y, preds_b), "ci": _interval(values, y, resamples)}


def leave_one_sequence_out(y, preds, seqs, stat, baseline=None):
    """Range of a statistic (or of its difference to `baseline`) when one sequence at a time is left out."""
    y, preds, seqs = np.asarray(y), np.asarray(preds), np.asarray(seqs)
    values = {}
    for s in np.unique(seqs):
        keep = seqs != s
        value = seed_mean(stat, y[keep], preds[:, keep])
        if baseline is not None:
            value -= seed_mean(stat, y[keep], np.asarray(baseline)[:, keep])
        values[str(s)] = value
    defined = [v for v in values.values() if not np.isnan(v)]
    return {"low": min(defined, default=float("nan")), "high": max(defined, default=float("nan")), "values": values}


def wilson(k, n, z=1.96):
    """Wilson score interval; ignores dependence between trajectories. k may be a mean count over seeds."""
    if n <= 0:
        return float("nan"), float("nan")
    r = k / n
    denominator = 1 + z ** 2 / n
    centre = (r + z ** 2 / (2 * n)) / denominator
    half = z * np.sqrt(r * (1 - r) / n + z ** 2 / (4 * n ** 2)) / denominator
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


def share_by_sequence(labels, seqs):
    """Sequence -> orientation share (nan without valid trajectories), for the indicator over time."""
    labels, seqs = np.asarray(labels, dtype=int), np.asarray(seqs)
    return {str(s): orientation_share(labels[seqs == s]) for s in np.unique(seqs)}


def sequence_share_errors(y, p, seqs):
    """Mean absolute share error per sequence; sequences where a share is undefined are skipped and counted."""
    y, p, seqs = np.asarray(y, dtype=int), np.asarray(p, dtype=int), np.asarray(seqs)
    errors = {str(s): abs(share_error(y[seqs == s], p[seqs == s])) for s in np.unique(seqs)}
    defined = [v for v in errors.values() if not np.isnan(v)]
    return {"mae": float(np.mean(defined)) if defined else float("nan"), "used": len(defined),
            "skipped": len(errors) - len(defined), "errors": errors}


def auroc_orientation(y, scores):
    """AUROC of `orientierung` against the rest (rank formula); nan unless both groups exist."""
    positive = np.asarray(y, dtype=int) == ORIENTATION
    n_pos, n_neg = int(positive.sum()), int((~positive).sum())
    if not n_pos or not n_neg:
        return float("nan")
    ranks = rankdata(scores)
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
