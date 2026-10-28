from beeflight.splits import BUFFERS, SPLITS, _check


def test_splits_disjoint_and_complete():
    _check()


def test_test_sets_untouched_by_train_and_val():
    seen = set(SPLITS["train"]) | set(SPLITS["val"])
    assert not seen & set(SPLITS["test_same_hive"])
    assert not seen & set(SPLITS["test_other_hive"])


def test_buffers_separate_blocks():
    # one discarded sequence between train/val and between val/test A
    assert BUFFERS == ["rec2123_seq070", "rec2123_seq085"]
    assert SPLITS["train"][-1] == "rec2123_seq069" and SPLITS["val"][0] == "rec2123_seq071"
    assert SPLITS["val"][-1] == "rec2123_seq084" and SPLITS["test_same_hive"][0] == "rec2123_seq086"
