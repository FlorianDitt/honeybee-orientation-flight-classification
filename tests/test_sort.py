import numpy as np

from beeflight.sort import sort_track


def test_two_crossing_bees_keep_their_identity():
    # A flies right, B flies left at the same height: the constant-velocity prediction keeps them apart
    dets = [np.array([[100 + 8 * t, 200, 80], [500 - 8 * t, 200, 80]], float) for t in range(50)]
    tracks = sort_track(dets, max_age=1)
    assert sorted(len(p) for p in tracks) == [50, 50]
    for p in tracks:
        assert np.all(np.diff(p[:, 1]) == np.diff(p[:, 1])[0])  # each track moves one way only


def test_gap_longer_than_max_age_splits_the_track():
    dets = [np.array([[100 + 5 * t, 200, 80]], float) if not 20 <= t < 23 else np.zeros((0, 3)) for t in range(40)]
    assert sorted(len(p) for p in sort_track(dets, max_age=1)) == [17, 20]
    assert [len(p) for p in sort_track(dets, max_age=5)] == [37]


def test_birth_gap_stops_a_wing_blob_from_starting_a_second_track():
    # from frame 5 on, the tracked bee also shows a small blob 8 px beside it
    dets = [np.array([[100 + 5 * t, 200, 80], [108 + 5 * t, 200, 30]][: 1 + (t >= 5)], float) for t in range(30)]
    assert len(sort_track(dets, birth_gap=0.0)) == 2
    assert [len(p) for p in sort_track(dets, birth_gap=20.0)] == [30]
