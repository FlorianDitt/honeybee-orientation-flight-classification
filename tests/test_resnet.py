import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")

import beeflight.evaluate as evaluate  # noqa: E402
import beeflight.metrics as M  # noqa: E402
import beeflight.resnet as R  # noqa: E402


def test_channels_by_hand():
    pos = np.array([[0.0, 0.0], [0.02, 0.0], [0.02, 0.02]])
    c = R.channels(pos, [10, 11, 12])
    assert c.shape == (3, 6)
    assert c[1].tolist() == pytest.approx([0.02, 0, 1, 0, 1, 0])
    assert c[2, 5] == pytest.approx(np.pi / 2)
    assert c[0, 2:].tolist() == pytest.approx([0, 0, 0, 0])


def test_velocity_is_per_frame_across_gaps():
    c = R.channels(np.array([[0.0, 0.0], [0.04, 0.0]]), [0, 2])
    assert c[1, 2] == pytest.approx(1)


def test_interpolation_keeps_ends_and_length():
    s = np.array([[0.0, 10.0], [1.0, 20.0], [2.0, 30.0]])
    out = R.interpolate(s, 5)
    assert out.shape == (5, 2)
    assert out[:, 0].tolist() == pytest.approx([0, 0.5, 1, 1.5, 2])
    assert R.interpolate(s, 2)[:, 1].tolist() == pytest.approx([10, 30])


def test_entrance_coordinates_and_missing_hive():
    assert R.to_entrance([[270, 90]], "2123")[0].tolist() == pytest.approx([0, 0])
    assert R.to_entrance([[540, 630]], "2123")[0].tolist() == pytest.approx([0.5, 1])
    with pytest.raises(ValueError, match="rec2125"):
        R.to_entrance([[270, 90]], "2125")


def test_architecture_matches_the_paper():
    net = R.build_net()
    convs = [m for m in net.modules() if isinstance(m, torch.nn.Conv1d)]
    assert [c.kernel_size[0] for c in convs if c.kernel_size[0] > 1] == [8, 5, 3] * 3
    assert {c.out_channels for c in convs} == {64}
    assert len(net.blocks) == 3
    assert net.head.in_features == 64


@pytest.mark.parametrize("length", [16, 37, 238])
def test_output_shape_for_any_length(length):
    net = R.build_net().eval()
    assert net(torch.zeros(3, R.N_CHANNELS, length)).shape == (3, len(M.CLASSES))
    assert net.encode(torch.zeros(3, R.N_CHANNELS, length)).shape == (3, 64)


def track(i, label=None, turn=False, n=20, seq="rec2123_seq071"):
    t = np.arange(n)
    xy = np.column_stack([270 + 8 * np.sin(t / 2) * 10, 100 + 8 * t]) if turn else np.column_stack([270 + 5 * t, 100 + 8 * t])
    r = {"id": f"t{i}", "seq": seq, "t": t.tolist(), "xy": xy.tolist()}
    return {**r, "label": label} if label else r


def small_rows():
    return [track(i, "orientierung" if i % 2 else "sammelabflug", turn=bool(i % 2), n=20 + i) for i in range(24)]


def test_training_learns_and_keeps_the_best_checkpoint():
    rows = small_rows()
    length, mean, std = R.scaling(rows)
    x, y = R.prepare(rows, length, mean, std), M.encode([r["label"] for r in rows])
    assert x.shape == (24, R.N_CHANNELS, length)
    net = R.train(x, y, seed=0, epochs=40)
    assert (R.predict(net, x).argmax(axis=1) == y).mean() == 1


def test_same_seed_same_result():
    rows = small_rows()
    length, mean, std = R.scaling(rows)
    x, y = R.prepare(rows, length, mean, std), M.encode([r["label"] for r in rows])
    a, b = (R.predict(R.train(x, y, seed=1, epochs=2), x) for _ in range(2))
    assert np.array_equal(a, b)


def test_end_to_end_with_evaluate_and_no_retraining(tmp_path, monkeypatch):
    rows = small_rows()
    queue = [track(100 + i, turn=bool(i % 2), seq=f"rec2123_seq{70 + i // 3:03d}") for i in range(36)]
    for module in (R, evaluate):
        monkeypatch.setattr(module, "LABELS", tmp_path)
    (tmp_path / "train.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "queue_val.json").write_text(json.dumps({"items": queue}))
    labelled = [{**q, "label": "orientierung" if i % 2 else "sammelabflug"} for i, q in enumerate(queue)]
    (tmp_path / "val.jsonl").write_text("".join(json.dumps(r) + "\n" for r in labelled))
    out = tmp_path / "models"
    R.main(["--seeds", "2", "--epochs", "3", "--out", str(out)])
    assert (out / "resnet_s1.pt").exists()
    run = json.loads((out / "val" / "resnet_s0.json").read_text())
    assert set(run["predictions"]) == {q["id"] for q in queue}
    assert sum(run["probabilities"]["t100"].values()) == pytest.approx(1)
    monkeypatch.setattr(R, "train", lambda *a, **k: pytest.fail("trained again"))
    R.main(["--seeds", "2", "--epochs", "3", "--out", str(out)])
    evaluate.main(["--split", "val", "--predictions", str(out / "val"), "--n-bootstrap", "20",
                   "--out", str(tmp_path / "eval")])
    res = json.loads((tmp_path / "eval" / "summary.json").read_text())["eigene Labels"]
    assert res["models"]["resnet"]["seeds"] == [0, 1]
    assert "auroc_orientierung" in res["models"]["resnet"]


def test_changed_labels_retrain(tmp_path, monkeypatch):
    rows = small_rows()
    R.fit_seed(rows, 0, 1, tmp_path, log=lambda s: None)
    calls = []
    real = R.train
    monkeypatch.setattr(R, "train", lambda *a, **k: calls.append(1) or real(*a, **k))
    R.fit_seed(rows, 0, 1, tmp_path, log=lambda s: None)
    assert not calls
    changed = [{**rows[0], "label": "anflug"}, *rows[1:]]
    R.fit_seed(changed, 0, 1, tmp_path, log=lambda s: None)
    assert calls
