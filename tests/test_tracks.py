import numpy as np

from beeflight.tracks import BOARD_MARGIN, EDGE_MARGIN, features, merge_close, stitch, track, zone_of

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


def line(t0, t1, x0, vx, y=250.0):
    t = np.arange(t0, t1)
    return np.c_[t, x0 + vx * (t - t0), np.full(len(t), y)]


def test_stitch_joins_a_bee_lost_over_the_grass():
    a = line(0, 30, 100, 4)  # ends at x=216, in the open
    b = line(42, 70, 100 + 4 * 42, 4)  # reappears where it should be 12 frames later
    out = stitch([a, b], SHAPE, board_bottom=50)
    assert len(out) == 1 and len(out[0]) == 58


def test_stitch_ignores_far_or_departed_tracks():
    a = line(0, 30, 100, 4)
    far = line(42, 70, 100 + 4 * 42, 4, y=420)  # same time, wrong place
    assert len(stitch([a, far], SHAPE, board_bottom=50)) == 2
    gone = line(0, 30, 360, 4.5)  # leaves at the right edge
    back = line(40, 60, 480, -4)
    assert len(stitch([gone, back], SHAPE, board_bottom=50)) == 2


def test_zone_margins():
    assert zone_of((250, 50 + BOARD_MARGIN - 1), SHAPE, 50) == "board"
    assert zone_of((EDGE_MARGIN - 1, 250), SHAPE, 50) == "edge"
    assert zone_of((250, 250), SHAPE, 50) == "lost"


def test_split_blob_of_one_bee_does_not_steal_the_track():
    t = np.arange(40)
    bee = np.c_[10 + 8 * t, 200 + 0 * t]
    dets = []
    for i in t:
        d = [[*bee[i], 120]]
        if 18 <= i <= 20:  # wing or shadow shows up as a second blob next to the bee
            d.append([bee[i][0] - 6, bee[i][1] + 9, 40])
        dets.append(merge_close(np.array(d, float)))
    tracks = [p for p in track(dets) if len(p) > 5]
    assert len(tracks) == 1 and len(tracks[0]) == 40


def test_tracker_follows_a_sharp_turn():
    # 25 px/frame to the right, then a hairpin back: the prediction lands 50 px off, the last position 25 px
    xy = [(50 + 25 * i, 200) for i in range(12)] + [(325 - 25 * i, 215) for i in range(1, 12)]
    dets = [np.array([[x, y, 100]], float) for x, y in xy]
    assert len([p for p in track(dets) if len(p) > 5]) == 1
