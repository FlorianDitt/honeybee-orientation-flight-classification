"""Fusion network and Gradient-Blending weights of candidates 3 and 4, on small synthetic data."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from beeflight import fusion as X  # noqa: E402


def test_blend_weights_by_hand():
    # G / O^2: 0.2/0.01 = 20, 0.1/0.04 = 2.5, 0.3/0.09 = 10/3
    w = X.blend_weights([0.2, 0.1, 0.3], [0.1, 0.2, 0.3])
    total = 20 + 2.5 + 10 / 3
    assert w == pytest.approx([20 / total, 2.5 / total, (10 / 3) / total])
    assert w.sum() == pytest.approx(1)


def test_blend_weights_edge_cases():
    assert X.blend_weights([-0.1, 0.2, 0.2], [0.1, 0.1, 0.1])[0] == 0
    assert X.blend_weights([0.1, 0.1, 0.0], [-1.0, X.MIN_O, 0.5]).tolist() == pytest.approx([0.5, 0.5, 0.0])
    with pytest.raises(ValueError):
        X.blend_weights([0, -1, 0], [0.1, 0.1, 0.1])


def rows(n_seqs=10, per_seq=4):
    return [{"seq": f"s{s}", "id": f"s{s}:{k}"} for s in range(n_seqs) for k in range(per_seq)]


def test_holdout_keeps_sequences_whole_and_subset_inside_train():
    data = rows()
    t, t_sub, v = X.holdout(data)
    assert not {data[i]["seq"] for i in t} & {data[i]["seq"] for i in v}
    assert len(v) == 8 and len(t) == 32 and len(t_sub) == len(v) and set(t_sub) <= set(t)


def test_network_has_three_heads_of_the_right_shape():
    net = X.build_fusion(image_dim=12)
    outputs = net(torch.zeros(5, 6, 30), torch.zeros(5, 12))
    assert [o.shape for o in outputs] == [(5, 4)] * 3


def test_concat_trains_only_through_the_fused_head():
    traj, image = np.random.default_rng(0).normal(size=(2, 8, 6, 30)).astype(np.float32)[0], np.zeros((8, 12), np.float32)
    y = np.arange(8) % 4
    net = X._fresh(12, 0)
    before = net.head_image.weight.detach().clone()
    X._train(net, traj, image, y, 0, X.CONCAT, epochs=2, batch=4)
    assert torch.equal(net.head_image.weight, before)
    assert X.head_probabilities(net, traj, image).shape == (8, 4)


def test_weight_estimate_uses_only_the_rows_it_gets(monkeypatch):
    rng = np.random.default_rng(0)
    data = rows(5, 4)
    y = np.arange(20) % 4
    traj = rng.normal(size=(20, 6, 30)).astype(np.float32)
    image = (np.eye(4)[y] * 3 + rng.normal(0, 0.1, (20, 4))).astype(np.float32)
    calls = []
    original = X._train

    def spy(net, t, i, labels, *args, **kwargs):
        calls.append(len(labels))
        return original(net, t, i, labels, *args, **kwargs)

    monkeypatch.setattr(X, "_train", spy)
    monkeypatch.setattr(X, "blend_weights", lambda g, o: np.array([1 / 3] * 3))
    out = X.estimate_weights(traj, image, y, data, epochs=2, log=lambda _: None)
    assert calls == [16, 16, 16] and out["n_holdout"] == 4 and out["n_train"] == 16
