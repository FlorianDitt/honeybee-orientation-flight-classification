import numpy as np

from beeflight.tracks import features, track

SHAPE = (500, 500)


def path(xy):
    return np.c_[np.arange(len(xy)), xy]


def test_full_loop_turns_360_degrees():
    a = np.linspace(0, 2 * np.pi, 80)
    f = features(path(np.c_[250 + 60 * np.cos(a), 250 + 60 * np.sin(a)]), SHAPE, board_bottom=50)
    assert 320 < abs(f["turn_deg"]) < 400
    assert f["straight"] < 0.1


def test_straight_departure_from_board_to_edge():
    xy = np.c_[np.full(60, 200.0), np.linspace(55, 495, 60)]
    f = features(path(xy), SHAPE, board_bottom=50)
    assert f["start"] == "board" and f["end"] == "edge"
    assert f["straight"] > 0.99 and abs(f["turn_deg"]) < 5


def test_tracker_follows_two_crossing_bees():
    t = np.arange(40)
    a = np.c_[10 + 8 * t, 100 + 0 * t]
    b = np.c_[10 + 8 * t, 300 - 0 * t]
    dets = [np.array([[*a[i], 100], [*b[i], 100]], float) for i in t]
    tracks = [p for p in track(dets) if len(p) > 5]
    assert len(tracks) == 2 and all(len(p) == 40 for p in tracks)
