import random

from beeflight.sample import QUOTA, draw, match, stratum, track_id


def row(start, end, straight=0.9, dur=1.0):
    return {"start": start, "end": end, "straight": straight, "dur_s": dur}


def test_stratum_rules():
    assert stratum(row("board", "edge", straight=0.3)) == "dep_curvy"
    assert stratum(row("board", "edge", straight=0.3, dur=0.2)) == "dep_straight"
    assert stratum(row("board", "lost")) == "dep_straight"
    assert stratum(row("edge", "board")) == "arrival"
    assert stratum(row("board", "board")) == "board_board"
    assert stratum(row("lost", "edge")) == "other"


def test_draw_fills_quota_and_redistributes_small_strata():
    items = [{"id": f"{k}{i}", "stratum": k} for k in QUOTA for i in range(200 if k != "dep_curvy" else 20)]
    queue, take = draw(items, 300, random.Random(0))
    assert len(queue) == 300 and len({i["id"] for i in queue}) == 300
    assert take["dep_curvy"] == 20  # all curvy departures, the rest of their quota goes elsewhere
    assert sum(take.values()) == 300


def test_draw_is_shuffled_and_reproducible():
    items = [{"id": f"{k}{i}", "stratum": k} for k in QUOTA for i in range(50)]
    a, _ = draw(items, 100, random.Random(1))
    b, _ = draw(items, 100, random.Random(1))
    assert [i["id"] for i in a] == [i["id"] for i in b]
    assert len({i["stratum"] for i in a[:10]}) > 1


def test_track_ids_are_unique_when_tracks_start_together():
    seen = {}
    assert [track_id("s", 5, seen) for _ in range(3)] == ["s:5", "s:5b", "s:5c"]
    assert track_id("s", 6, seen) == "s:6"


def test_draw_keeps_forced_items_and_counts_them():
    items = [{"id": f"{k}{i}", "stratum": k} for k in QUOTA for i in range(100)]
    queue, take = draw(items, 100, random.Random(0), forced={"dep_curvy0", "other5"})
    ids = {i["id"] for i in queue}
    assert len(queue) == 100 and {"dep_curvy0", "other5"} <= ids
    assert take["dep_curvy"] == 30 and sum(take.values()) == 100


def track(seq, t0, n, x0=100.0, dx=3.0, y=50.0):
    t = list(range(t0, t0 + n))
    return {"id": f"{seq}:{t0}", "seq": seq, "t0": t0, "t1": t[-1], "t": t, "xy": [[x0 + dx * k, y] for k in range(n)]}


def test_match_finds_same_flight_but_not_grown_or_other():
    old = track("s", 10, 30)
    same = track("s", 8, 33, x0=94.0)  # starts 2 frames earlier, same line
    elsewhere = track("s", 10, 30, y=120.0)
    grown = track("s", 10, 60)  # stitched to twice the length
    assert match(old, [elsewhere, same, grown]) is same
    assert match(old, [elsewhere, grown]) is None
    assert match(old, [track("other", 10, 30)]) is None
