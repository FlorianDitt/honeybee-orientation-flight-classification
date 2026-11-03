"""Appearance-based bee detector: YOLOv8 trained on the public landing-board dataset of
Sledevič & Matuzevičius (2024, Data in Brief 52, 110060; Mendeley 10.17632/8gb9r2yhfc.5), with the
training settings of Sledevič et al. (2024, Agriculture 14, 1890): YOLOv8n, input 1024 px, AdamW
lr 0.002 momentum 0.9, translate 0.1, scale 0.5, fliplr 0.5, no mosaic for the last 10 epochs.

Unlike the background model (Chiron 2013) it also sees bees that hover, walk or sit, which is where
most tracks break (at and just below the landing board).

Their camera looks down from 30 cm: a bee is about 60 x 80 px in a 1920 x 1080 frame, about 32 x 43 px
at the 1024 px input. That is close to a bee in our videos at full resolution, so inference later runs
at full resolution (no downscaling).

Deviations, because we train on a CPU: every STEP-th frame only (neighbouring frames of their videos
are near duplicates), a time budget instead of 400 epochs, and one whole hive (VAL_HIVE) held out for
validation instead of a random 80/20 split, so the score is not inflated by near-duplicate frames.
Frames without a label file contain no bee (checked by eye) and stay in as negatives.

Usage: beeflight-sledevic prepare        (file lists in outputs/sledevic/)
       beeflight-sledevic train [--hours 9]
"""
import argparse
from pathlib import Path

from .splits import ROOT

DATA = ROOT / "data" / "sledevic2024"
OUT = ROOT / "outputs" / "sledevic"
WEIGHTS = OUT / "yolov8n" / "weights" / "best.pt"
VAL_HIVE = "_bee_20230711c"
STEP, VAL_STEP = 3, 5
IMGSZ = 1024


def prepare():
    hives = sorted(p for p in DATA.glob("_bee_*") if p.is_dir())
    if not hives:
        raise SystemExit(f"no dataset in {DATA}; download Mendeley 8gb9r2yhfc v5 and unpack detection/ there")
    lists = {"train": [], "val": []}
    for hive in hives:
        part = "val" if hive.name == VAL_HIVE else "train"
        images = sorted((hive / "images").glob("*.jpg"))
        lists[part] += images[::VAL_STEP if part == "val" else STEP]
    OUT.mkdir(parents=True, exist_ok=True)
    for part, images in lists.items():
        (OUT / f"{part}.txt").write_text("".join(f"{p}\n" for p in images))
        labeled = sum((p.parent.parent / "labels" / f"{p.stem}.txt").exists() for p in images)
        print(f"{part}: {len(images)} frames, {labeled} with bees")
    (OUT / "data.yaml").write_text(f"path: {OUT}\ntrain: train.txt\nval: val.txt\nnames:\n  0: bee\n")


def train(hours=9.0, batch=8):
    from ultralytics import YOLO

    YOLO("yolov8n.pt").train(data=str(OUT / "data.yaml"), imgsz=IMGSZ, epochs=400, time=hours, batch=batch,
                             device="cpu", workers=2, project=str(OUT), name="yolov8n", exist_ok=True,
                             optimizer="AdamW", lr0=0.002, momentum=0.9, translate=0.1, scale=0.5, fliplr=0.5,
                             close_mosaic=10, plots=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "train"])
    ap.add_argument("--hours", type=float, default=9.0)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()
    if args.cmd == "prepare":
        prepare()
    else:
        train(args.hours, args.batch)


if __name__ == "__main__":
    main()
