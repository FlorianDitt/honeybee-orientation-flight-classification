import random

from beeflight.sample import QUOTA, draw, stratum


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
