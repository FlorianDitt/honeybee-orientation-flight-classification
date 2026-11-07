"""Crops, feature layout and the linear classifier of candidate 2, without videos or downloaded weights."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from beeflight import image_features as F  # noqa: E402


def test_evenly_spaced_covers_both_ends_and_repeats_short_series():
    assert F.evenly_spaced(100).tolist()[0] == 0 and F.evenly_spaced(100).tolist()[-1] == 99
    assert len(F.evenly_spaced(3)) == F.N_FRAMES and F.evenly_spaced(1).tolist() == [0] * F.N_FRAMES


def test_center_undoes_scale_and_top():
    assert F.center_of({"xy": [[10, 20]], "scale": 0.5, "top": 410}, 0) == (20, 860)


def test_crop_is_centred_and_keeps_size_at_the_border():
    image = np.zeros((100, 80, 3), np.uint8)
    image[50, 40] = 255
    assert F.crop_at(image, 40, 50, 10)[5, 5, 0] == 255
    for x, y in ((0, 0), (79, 99), (-5, 200)):
        assert F.crop_at(image, x, y, 64).shape == (64, 64, 3)


def test_to_input_shape_and_rgb_order():
    crop = np.zeros((64, 64, 3), np.uint8)
    crop[..., 0] = 255  # blue in BGR
    out = F.to_input([crop])
    assert out.shape == (1, 3, F.INPUT, F.INPUT)
    assert out[0, 2].mean() > 0 > out[0, 0].mean()


@pytest.mark.parametrize("layers, tokens, frames, d", [(1, "cls", "avg", 5), (4, "cls", "avg", 20),
                                                       (1, "cls+avg", "avg", 10), (4, "cls+avg", "avg", 40),
                                                       (1, "cls", "concat", 40), (4, "cls+avg", "concat", 320)])
def test_build_x_dimensions(layers, tokens, frames, d):
    assert F.build_x(np.zeros((3, 8, 4, 2, 5), np.float32), layers, tokens, frames).shape == (3, d)


def test_one_layer_means_the_last_and_cls_means_token_zero():
    feats = np.zeros((1, 8, 4, 2, 1), np.float32)
    feats[0, :, 3, 0] = 7
    assert F.build_x(feats, 1, "cls", "avg").tolist() == [[7]]


def test_linear_classifier_learns_separable_classes():
    rng = np.random.default_rng(0)
    y = np.repeat(np.arange(4), 20)
    x = (np.eye(4)[y] * 3 + rng.normal(0, 0.1, (80, 4))).astype(np.float32)
    w, b = F.train_linear(x, y, lrs=(0.5, 0.0001), iterations=300)
    probs = F.probabilities(x, w[0], b[0])
    assert (probs.argmax(axis=1) == y).all()
    assert np.isclose(probs.sum(axis=1), 1).all()


def test_grid_is_the_papers_plus_crop_and_frames():
    assert len(F.LEARNING_RATES) == 13
    assert len(F.configurations()) == 2 * 2 * 2 * len(F.CROPS)


def test_test_split_reads_only_the_queue(monkeypatch, tmp_path):
    (tmp_path / "queue_test_same_hive.json").write_text('{"items": [{"id": "a"}]}')
    monkeypatch.setattr(F, "LABELS", tmp_path)
    assert F.rows_of("test_same_hive") == [{"id": "a"}]
