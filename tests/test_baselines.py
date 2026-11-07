import json

import numpy as np
import pytest

import beeflight.baselines as B
import beeflight.evaluate as evaluate
import beeflight.metrics as M

SEQ = "rec2123_seq071"
BOARD_Y, MIDDLE, EDGE_X = 100, (270, 300), 5  # board bottom + margin is at y = 120 in rec2123


def zones(start, end, straight=0.9, dur=1.0):
    return {"start": start, "end": end, "straight": straight, "dur_s": dur}


@pytest.mark.parametrize("f, expected", [
    (zones("board", "board"), "orientierung"),
    (zones("board", "edge", straight=0.3, dur=1.0), "orientierung"),
    (zones("board", "lost", straight=0.3, dur=1.0), "orientierung"),
    (zones("board", "edge", straight=0.9, dur=1.0), "sammelabflug"),
    (zones("board", "edge", straight=0.3, dur=0.2), "sammelabflug"),
    (zones("edge", "board"), "anflug"),
    (zones("lost", "board"), "anflug"),
    (zones("edge", "edge"), "artefakt"),
    (zones("lost", "edge"), "artefakt"),
])
def test_rule_by_hand(f, expected):
    assert M.CLASSES[B.rule_predict(f)] == expected


def test_tuning_finds_the_separating_thresholds():
    curvy = [zones("board", "edge", straight=0.3, dur=1.0)] * 10
    straight = [zones("board", "edge", straight=0.6, dur=1.0)] * 10
    y = np.array([B.ORIENTATION] * 10 + [B.DEPARTURE] * 10)
    tuned = B.tune_rule(curvy + straight, y)
    assert tuned["train_balanced_accuracy"] == 1
    assert 0.3 < tuned["straight"] <= 0.6 and tuned["dur"] < 1.0


def track(i, label=None, seq=SEQ, start=(270, BOARD_Y), end=(EDGE_X, 300), n=20):
    xy = np.linspace(start, end, n).tolist()
    r = {"id": f"t{i}", "seq": seq, "t": list(range(n)), "xy": xy}
    return {**r, "label": label} if label else r


def train_rows():
    return [track(i, c) for i, c in enumerate(M.CLASSES * 5)]


def test_runs_are_complete_and_reproducible():
    rows = [track(i) for i in range(30)]
    a, b = B.build_runs(rows, train_rows(), 3), B.build_runs(rows, train_rows(), 3)
    assert a == b
    assert {r["model"] for r in a} == {"rule_fixed", "rule", "random_uniform", "random_frequency",
                                       *(f"always_{c}" for c in M.CLASSES)}
    assert sum(r["model"] == "random_uniform" for r in a) == 3
    for run in a:
        assert set(run["predictions"]) == {r["id"] for r in rows}
        assert set(run["predictions"].values()) <= set(M.CLASSES)


def test_random_baselines_differ_between_seeds_and_models():
    runs = B.build_runs([track(i) for i in range(50)], train_rows(), 2)
    uniform = [r["predictions"] for r in runs if r["model"] == "random_uniform"]
    frequency = [r["predictions"] for r in runs if r["model"] == "random_frequency"]
    assert uniform[0] != uniform[1] and uniform[0] != frequency[0]


def test_frequency_baseline_follows_train_shares():
    train = [track(i, "anflug") for i in range(20)]
    runs = B.build_runs([track(i) for i in range(30)], train, 1)
    assert set(next(r for r in runs if r["model"] == "random_frequency")["predictions"].values()) == {"anflug"}


def test_both_hives_use_their_own_board():
    # y = 150 is below the rec2123 board zone (bottom 90 + margin 30) but inside the rec2125 one (135 + 30)
    assert B.track_features(track(0, start=(270, 150)))["start"] == "lost"
    assert B.track_features(track(0, seq="rec2125_seq000", start=(270, 150)))["start"] == "board"


def setup_labels(tmp_path, monkeypatch, split, queue):
    for module in (B, evaluate):
        monkeypatch.setattr(module, "LABELS", tmp_path)
    monkeypatch.setattr(B, "OUT", tmp_path / "baselines")
    monkeypatch.setattr(evaluate, "OUT", tmp_path / "eval")
    (tmp_path / "train.jsonl").write_text("".join(json.dumps(r) + "\n" for r in train_rows()))
    (tmp_path / f"queue_{split}.json").write_text(json.dumps({"items": queue}))


def test_test_split_reads_only_train_labels(tmp_path, monkeypatch):
    setup_labels(tmp_path, monkeypatch, "test_same_hive", [track(i) for i in range(10)])
    (tmp_path / "final_test_same_hive.jsonl").write_text("not json")  # would crash if it were read
    (tmp_path / "test_same_hive.jsonl").write_text("not json")
    B.main(["--split", "test_same_hive", "--seeds", "1"])
    assert (tmp_path / "baselines" / "test_same_hive" / "rule_s0.json").exists()


def test_files_work_with_evaluate(tmp_path, monkeypatch):
    queue = [track(i, seq=f"rec2123_seq{70 + i // 4:03d}") for i in range(48)]
    setup_labels(tmp_path, monkeypatch, "val", queue)
    labelled = [{**t, "label": M.CLASSES[i % 4]} for i, t in enumerate(queue[:40])]  # fewer labels than queue items
    (tmp_path / "val.jsonl").write_text("".join(json.dumps(r) + "\n" for r in labelled))
    B.main(["--split", "val", "--seeds", "2"])
    evaluate.main(["--split", "val", "--predictions", str(tmp_path / "baselines" / "val"), "--baseline", "rule",
                   "--n-bootstrap", "20"])
    res = json.loads((tmp_path / "eval" / "val" / "summary.json").read_text())["eigene Labels"]
    assert res["models"]["always_anflug"]["metrics"]["balanced_accuracy"]["mean"] == 0.25
    assert res["models"]["random_uniform"]["seeds"] == [0, 1]
    assert "rule_fixed" in res["comparison"]
