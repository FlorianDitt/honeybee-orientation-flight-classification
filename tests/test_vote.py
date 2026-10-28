import math

from beeflight.vote import decide, krippendorff_alpha


def votes(*labels, flags=()):
    return {f"a{i}": {"label": lab, "flags": list(flags[i]) if flags else []} for i, lab in enumerate(labels)}


def test_majority_wins():
    assert decide(votes("anflug", "anflug", "orientierung"), "a0")[::2] == ("anflug", "majority")


def test_tie_goes_to_owner_and_is_marked():
    label, flags, how = decide(votes("anflug", "orientierung", "artefakt"), "a1")
    assert (label, how) == ("orientierung", "owner") and "strittig" in flags


def test_tie_without_owner_stays_open():
    assert decide(votes("anflug", "orientierung"), "nobody")[0] is None


def test_flag_kept_when_half_set_it():
    _, flags, _ = decide(votes("anflug", "anflug", flags=[["fragment"], []]), "a0")
    assert flags == ["fragment"]
    _, flags, _ = decide(votes("anflug", "anflug", "anflug", flags=[["fragment"], [], []]), "a0")
    assert flags == []


def test_alpha_by_hand():
    # o[a,a]=2, o[a,b]=o[b,a]=1, o[b,b]=2 -> D_o=2, D_e=2*3*3/5=3.6
    assert math.isclose(krippendorff_alpha([["a", "a"], ["a", "b"], ["b", "b"]]), 1 - 2 / 3.6)
    assert krippendorff_alpha([["a", "a", "a"], ["b", "b"], ["c"]]) == 1.0
