import numpy as np

from beeflight.detector import BOX, TILE, from_zone, tile_labels, to_zone


def test_zone_coordinates_round_trip():
    xy = np.array([[10.0, 95.0], [300.5, 400.25]])
    assert np.allclose(from_zone(to_zone(xy, "rec2123_seq050"), "rec2123_seq050"), xy)


def test_tile_label_is_centered_and_normalized():
    (line,) = tile_labels([(320, 320)], 0, 0)
    cls, cx, cy, w, h = map(float, line.split())
    assert cls == 0 and cx == cy == 0.5 and np.isclose(w, BOX / TILE) and np.isclose(h, BOX / TILE)


def test_box_mostly_outside_the_tile_is_dropped():
    assert tile_labels([(TILE + 10, 100)], 0, 0) == []
    assert len(tile_labels([(TILE - 20, 100)], 0, 0)) == 1  # 50 of 60 px inside, clipped


def test_background_blobs_fill_the_gap_where_yolo_loses_a_bee():
    import pytest

    pytest.importorskip("ultralytics")
    from beeflight.detector import BLOB_SCORE, byte_track

    def box(x, y, s):
        return [x - BOX / 2, y - BOX / 2, x + BOX / 2, y + BOX / 2, s]

    # bee B is only a low-score background blob for 20 frames
    frames = [np.array([box(100 + 12 * t, 200, 0.8), box(100 + 12 * t, 600, BLOB_SCORE if 20 <= t < 40 else 0.8)])
              for t in range(60)]
    assert sorted(len(p) for p in byte_track(frames, (1000, 1080))) == [60, 60]
    assert sorted(len(p) for p in byte_track([f[f[:, 4] > 0.5] for f in frames], (1000, 1080))) == [40, 60]
