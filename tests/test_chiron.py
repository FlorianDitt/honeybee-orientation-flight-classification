import numpy as np

from beeflight.chiron import MAX_MISSES, gnn_track


def test_two_crossing_bees_keep_their_identity():
    dets = [np.array([[100 + 8 * t, 200], [500 - 8 * t, 200]], float) for t in range(50)]
    tracks = gnn_track(dets)
    assert sorted(len(p) for p in tracks) == [50, 50]
    for p in tracks:
        assert np.all(np.diff(p[:, 1]) == np.diff(p[:, 1])[0])


def test_track_survives_short_gaps_but_not_max_misses():
    def gap(n):
        return [np.array([[100 + 5 * t, 200]], float) if not 20 <= t < 20 + n else np.zeros((0, 2)) for t in range(40)]
    assert len(gnn_track(gap(MAX_MISSES - 1))) == 1
    assert len(gnn_track(gap(MAX_MISSES))) == 2


def test_observation_outside_the_gate_starts_a_new_track():
    dets = [np.array([[100 + 5 * t, 200]], float) for t in range(20)] + [np.array([[400.0, 400.0]])]
    assert sorted(len(p) for p in gnn_track(dets)) == [1, 20]


def test_linking_joins_a_bee_lost_for_a_few_frames():
    from beeflight.chiron import link_tracklets
    t = np.arange(60)
    bee = np.c_[t, 100 + 5 * t, 200 + 0 * t].astype(float)
    a, b = bee[:25], bee[33:]  # 8 frames missing
    (joined,) = link_tracklets([a, b])
    assert len(joined) == len(a) + len(b)


def test_linking_keeps_a_landing_and_a_departing_bee_apart():
    from beeflight.chiron import link_tracklets
    t = np.arange(30)
    landing = np.c_[t, 300 + 0 * t, 400 - 6 * t].astype(float)            # flies up to the board
    departing = np.c_[t + 40, 305 + 0 * t, 230 + 6 * t].astype(float)     # leaves downwards near the same spot
    assert len(link_tracklets([landing, departing])) == 2
