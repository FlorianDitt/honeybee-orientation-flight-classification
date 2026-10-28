"""Single source of truth for the dataset split. Everything in the project imports from here.

Train/val come from hive rec2123, split by contiguous time blocks (never random frames:
at 60 fps neighbouring frames are near-duplicates and one bee track spans many frames).
One discarded buffer sequence sits between blocks so no track crosses a split boundary.

Two test sets:
  test_same_hive   last block of rec2123  -> how good is the method?
  test_other_hive  all of rec2125         -> how well does it transfer to a new hive?
The gap between the two is the domain-shift effect.

Rules: tune only on val; run each test set once, at the end.

Usage:
  beeflight-splits                  # print summary and write splits.json
  beeflight-splits --download val   # download the videos of one split
"""
import argparse
import json
from pathlib import Path

REPO = "mrkschtr/thehiveisreal"
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "thehiveisreal"
FPS = 59.94
SEQ_SECONDS = 30.03


def _seqs(rec, start, stop):
    return [f"rec{rec}_seq{i:03d}" for i in range(start, stop + 1)]


SPLITS = {
    "train": _seqs(2123, 15, 69),
    "val": _seqs(2123, 71, 84),
    "test_same_hive": _seqs(2123, 86, 89),
    "test_other_hive": _seqs(2125, 0, 20),
}
BUFFERS = _seqs(2123, 70, 70) + _seqs(2123, 85, 85)


def video_path(seq_id):
    return DATA_DIR / "videos" / f"{seq_id}.mp4"


def get_split(name):
    """Sequence ids of a split, in temporal order."""
    return list(SPLITS[name])


def download(name):
    from huggingface_hub import hf_hub_download

    for seq_id in SPLITS[name]:
        hf_hub_download(REPO, f"videos/{seq_id}.mp4", repo_type="dataset", local_dir=DATA_DIR)


def _check():
    every = [s for ids in SPLITS.values() for s in ids] + BUFFERS
    assert len(every) == len(set(every)) == 96, "splits must be disjoint and cover all 96 sequences"


def main():
    _check()
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", choices=list(SPLITS))
    args = ap.parse_args()
    if args.download:
        download(args.download)
        return
    for name, ids in SPLITS.items():
        print(f"{name:16s} {len(ids):3d} seqs  {len(ids) * SEQ_SECONDS / 60:5.1f} min  {ids[0]} .. {ids[-1]}")
    print(f"{'buffer (unused)':16s} {len(BUFFERS):3d} seqs  {', '.join(BUFFERS)}")
    with open(ROOT / "splits.json", "w") as f:
        json.dump({"splits": SPLITS, "buffers": BUFFERS}, f, indent=2)


if __name__ == "__main__":
    main()
