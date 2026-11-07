import json

import numpy as np
import pytest

import beeflight.evaluate as evaluate
import beeflight.metrics as M

O, S, A, X = range(4)  # orientierung, sammelabflug, anflug, artefakt
Y = np.array([O, O, O, O, S, S, S, A, A, X])
P = np.array([O, O, O, S, S, S, O, A, X, X])


def test_confusion_by_hand():
    c = M.confusion(Y, P)
    assert c[O].tolist() == [3, 1, 0, 0]
    assert c[S].tolist() == [1, 2, 0, 0]
    assert c[A].tolist() == [0, 0, 1, 1]
    assert c[X].tolist() == [0, 0, 0, 1]


def test_balanced_accuracy_by_hand():
    assert M.balanced_accuracy(Y, P) == pytest.approx((3 / 4 + 2 / 3 + 1 / 2 + 1) / 4)


def test_macro_f1_is_mean_of_class_f1_not_f1_of_means():
    expected = np.mean([2 * 3 / (4 + 4), 2 * 2 / (3 + 3), 2 * 1 / (2 + 1), 2 * 1 / (1 + 2)])
    assert M.macro_f1(Y, P) == pytest.approx(expected)


def test_class_table_by_hand():
    row = M.class_table(Y, P)[O]
    assert (row["n"], row["predicted"], row["correct"]) == (4, 4, 3)
    assert row["recall"] == row["precision"] == pytest.approx(0.75)
    assert row["too_few"]
    assert not M.class_table(np.zeros(5, int), np.zeros(5, int))[O]["too_few"]


def test_agrees_with_sklearn():
    metrics = pytest.importorskip("sklearn.metrics")
    rng = np.random.default_rng(0)
    for _ in range(50):
        y, p = rng.integers(0, 4, 40), rng.integers(0, 4, 40)
        assert M.balanced_accuracy(y, p) == pytest.approx(metrics.balanced_accuracy_score(y, p))
        assert M.macro_f1(y, p) == pytest.approx(metrics.f1_score(y, p, labels=range(4), average="macro", zero_division=0))
        assert M.accuracy(y, p) == pytest.approx(metrics.accuracy_score(y, p))
        scores = rng.random(40)
        assert M.auroc_orientation(y, scores) == pytest.approx(metrics.roc_auc_score(y == O, scores))


def test_chance_level_does_not_depend_on_class_shares():
    y = np.array([O] * 4 + [S] * 16 + [A] * 30 + [X] * 50)
    for constant in range(4):
        assert M.balanced_accuracy(y, np.full(100, constant)) == pytest.approx(0.25)
    rng = np.random.default_rng(1)
    y = np.repeat(y, 200)
    assert M.balanced_accuracy(y, rng.integers(0, 4, len(y))) == pytest.approx(0.25, abs=0.01)


def test_absent_class_is_left_out_not_zero():
    y, p = np.array([S, S, A, X]), np.array([S, S, A, O])
    assert M.balanced_accuracy(y, p) == pytest.approx((1 + 1 + 0) / 3)
    assert M.macro_f1(y, p) == pytest.approx((1 + 1 + 0) / 3)
    assert np.isnan(M.class_recall(O)(y, p))
    assert M.class_precision(O)(y, p) == 0


def test_undefined_precision_is_nan_not_zero():
    assert np.isnan(M.class_precision(O)(np.array([O, S]), np.array([S, S])))
    assert M.class_recall(O)(np.array([O, S]), np.array([S, S])) == 0


def test_resamples_keep_sequences_whole():
    seqs = np.array(["a"] * 3 + ["b"] * 2 + ["c"] * 4)
    sizes = {"a": 3, "b": 2, "c": 4}
    for idx in M.cluster_resamples(seqs, 200):
        for s, size in sizes.items():
            assert (seqs[idx] == s).sum() % size == 0
        for s, size in sizes.items():
            members = np.flatnonzero(seqs == s)
            counts = np.bincount(idx, minlength=len(seqs))[members]
            assert len(set(counts.tolist())) == 1


def test_bootstrap_interval_contains_point_and_reports_missing_classes():
    y = np.array([O, S, S, A, A, X, X, S, A, X, S, A])
    seqs = np.array(["a", "a", "b", "b", "c", "c", "d", "d", "e", "e", "f", "f"])
    preds = np.array([y])
    res = M.cluster_bootstrap(y, preds, seqs, M.balanced_accuracy, n=300)
    assert res["low"] == res["high"] == 1.0
    assert 0 < res["missing_class_share"] < 1  # `orientierung` only lives in sequence a


def test_undefined_replicates_are_counted():
    y, p = np.array([O, S]), np.array([[O, S]])
    res = M.cluster_bootstrap(y, p, np.array(["a", "b"]), M.class_recall(O), n=300)
    assert 0 < res["undefined_share"] < 1
    assert res["low"] == res["high"] == 1.0


def test_seed_mean_enters_the_interval():
    y = np.array([O, S] * 6)
    seqs = np.repeat([f"s{i}" for i in range(6)], 2)
    right, wrong = y.copy(), 1 - y
    res = M.cluster_bootstrap(y, np.array([right, wrong]), seqs, M.accuracy, n=100)
    assert res["low"] == res["high"] == 0.5


def test_paired_difference_with_itself_is_zero():
    rng = np.random.default_rng(2)
    y = rng.integers(0, 4, 60)
    preds = rng.integers(0, 4, (3, 60))
    seqs = np.repeat([f"s{i}" for i in range(12)], 5)
    res = M.paired_difference(y, preds, preds, seqs, M.balanced_accuracy, n=100)
    assert res["difference"] == res["ci"]["low"] == res["ci"]["high"] == 0


def test_paired_difference_sign():
    y = np.array([O, S, A, X] * 6)
    seqs = np.repeat([f"s{i}" for i in range(6)], 4)
    res = M.paired_difference(y, np.array([y]), np.array([np.full(24, X)]), seqs, M.balanced_accuracy, n=100)
    assert res["difference"] == pytest.approx(0.75)
    assert res["ci"]["low"] > 0


def test_leave_one_sequence_out():
    y = np.array([O, O, O, S])
    p = np.array([[O, S, S, S]])
    seqs = np.array(["a", "b", "b", "c"])
    res = M.leave_one_sequence_out(y, p, seqs, M.accuracy)
    assert res["values"]["a"] == pytest.approx(1 / 3)
    assert res["values"]["b"] == 1
    assert res["values"]["c"] == pytest.approx(1 / 3)
    assert (res["low"], res["high"]) == (pytest.approx(1 / 3), 1)
    diff = M.leave_one_sequence_out(y, p, seqs, M.accuracy, baseline=p)
    assert diff["low"] == diff["high"] == 0


def test_wilson_reference_values():
    assert M.wilson(6, 8) == (pytest.approx(0.409, abs=0.001), pytest.approx(0.929, abs=0.001))
    low, high = M.wilson(0, 10)
    assert low == 0 and high == pytest.approx(0.278, abs=0.001)
    assert all(np.isnan(M.wilson(0, 0)))


def test_share_excludes_artefacts():
    assert M.orientation_share([O, S, A, X, X]) == pytest.approx(1 / 3)
    assert np.isnan(M.orientation_share([X, X]))
    assert np.isnan(M.orientation_share([]))
    assert M.share_error([O, S, S, S], [O, O, S, S]) == pytest.approx(0.25)


def test_false_positives_inflate_the_share():
    """True share 4 %, recall 0.75, false positive rate 10 %: about 12.6 % predicted."""
    y = np.array([O] * 400 + [S] * 9600)
    p = np.concatenate([np.full(300, O), np.full(100, S), np.full(960, O), np.full(8640, S)])
    assert M.class_recall(O)(y, p) == pytest.approx(0.75)
    assert M.orientation_share(p) == pytest.approx(0.126)


def test_sequence_errors_skip_and_count_empty_sequences():
    y = np.array([O, S, X, X])
    p = np.array([O, O, X, X])
    res = M.sequence_share_errors(y, p, np.array(["a", "a", "b", "b"]))
    assert res["mae"] == pytest.approx(0.5)
    assert (res["used"], res["skipped"]) == (1, 1)
    assert np.isnan(M.share_by_sequence(y, np.array(["a", "a", "b", "b"]))["b"])


# ---------------------------------------------------------------- evaluate


def row(i, label, seq="rec2123_seq071", votes=None, xy=None):
    r = {"id": f"t{i}", "label": label, "seq": seq, "xy": xy or [[270, 100], [5, 300]], "t": [0, 1]}
    return {**r, "votes": votes} if votes else r


def write_labels(tmp_path, monkeypatch, split, rows, final=False):
    monkeypatch.setattr(evaluate, "LABELS", tmp_path)
    monkeypatch.setattr(evaluate, "OUT", tmp_path / "eval")
    name = f"final_{split}.jsonl" if final else f"{split}.jsonl"
    (tmp_path / name).write_text("".join(json.dumps(r) + "\n" for r in rows))


def write_run(path, model, seed, predictions, **extra):
    path.write_text(json.dumps({"model": model, "seed": seed, "predictions": predictions, **extra}))
    return str(path)


def val_rows():
    return [row(i, M.CLASSES[i % 4], f"rec2123_seq{70 + i // 4:03d}") for i in range(48)]


def test_test_split_refused_without_flag_before_labels_are_read(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluate, "load_rows", lambda *a: pytest.fail("labels were read"))
    with pytest.raises(SystemExit, match="--test"):
        evaluate.main(["--split", "test_same_hive", "--predictions", str(tmp_path)])


def test_test_split_cannot_use_own_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluate, "load_rows", lambda *a: pytest.fail("labels were read"))
    with pytest.raises(SystemExit, match="final"):
        evaluate.main(["--split", "test_other_hive", "--test", "--labels", "own", "--predictions", str(tmp_path)])


@pytest.mark.parametrize("change, message", [
    (lambda p: p.pop("t0"), "without prediction"),
    (lambda p: p.update(other="anflug"), "unknown ids"),
    (lambda p: p.update(t0="biene"), "unknown classes"),
])
def test_bad_prediction_files_stop(tmp_path, monkeypatch, change, message):
    rows = val_rows()
    write_labels(tmp_path, monkeypatch, "val", rows)
    predictions = {r["id"]: r["label"] for r in rows}
    change(predictions)
    run = write_run(tmp_path / "a.json", "m", 0, predictions)
    with pytest.raises(SystemExit, match=message):
        evaluate.main(["--split", "val", "--predictions", run])


def test_duplicate_seed_stops(tmp_path, monkeypatch):
    rows = val_rows()
    write_labels(tmp_path, monkeypatch, "val", rows)
    predictions = {r["id"]: r["label"] for r in rows}
    runs = [write_run(tmp_path / f"{n}.json", "m", 0, predictions) for n in "ab"]
    with pytest.raises(SystemExit, match="twice"):
        evaluate.main(["--split", "val", "--predictions", *runs])


def test_val_report_end_to_end(tmp_path, monkeypatch):
    rows = val_rows()
    write_labels(tmp_path, monkeypatch, "val", rows)
    perfect = {r["id"]: r["label"] for r in rows}
    constant = {r["id"]: "anflug" for r in rows}
    d = tmp_path / "runs"
    d.mkdir()
    for seed in range(2):
        write_run(d / f"perfect{seed}.json", "perfect", seed, perfect,
                  probabilities={r["id"]: {"orientierung": float(r["label"] == "orientierung")} for r in rows})
    write_run(d / "rule.json", "rule", 0, constant)
    evaluate.main(["--split", "val", "--predictions", str(d), "--baseline", "rule", "--n-bootstrap", "50"])
    res = json.loads((tmp_path / "eval" / "val" / "summary.json").read_text())["eigene Labels"]
    assert res["interval"] == "cluster_bootstrap"
    assert res["models"]["perfect"]["metrics"]["balanced_accuracy"]["mean"] == 1
    assert res["models"]["rule"]["metrics"]["balanced_accuracy"]["mean"] == 0.25
    assert res["models"]["perfect"]["auroc_orientierung"] == 1
    assert res["comparison"]["perfect"]["balanced_accuracy"]["difference"] == 0.75
    assert res["comparison"]["perfect"]["balanced_accuracy"]["ci"]["low"] == 0.75
    text = (tmp_path / "eval" / "val" / "summary.md").read_text()
    assert "Cluster-Bootstrap" in text and "Grenzen" in text


def test_few_sequences_use_wilson_and_all_label_variants(tmp_path, monkeypatch):
    rows = []
    for i in range(40):
        label = M.CLASSES[i % 4]
        votes = {"florian": label, "a": label, "b": label if i % 2 else "artefakt"}
        rows.append(row(i, label, f"rec2123_seq{86 + i // 10:03d}", votes))
    write_labels(tmp_path, monkeypatch, "test_same_hive", rows, final=True)
    run = write_run(tmp_path / "m.json", "m", 0, {r["id"]: r["label"] for r in rows})
    evaluate.main(["--split", "test_same_hive", "--test", "--predictions", run])
    res = json.loads((tmp_path / "eval" / "test_same_hive" / "summary.json").read_text())
    assert set(res) == {"Mehrheit (primär)", "Autor", "einstimmig"}
    main = res["Mehrheit (primär)"]
    assert main["interval"] == "wilson_loso"
    model = main["models"]["m"]
    assert "ci" not in model["metrics"]["balanced_accuracy"]
    assert "loso" in model["metrics"]["balanced_accuracy"]
    assert model["classes"][0]["recall_wilson"][1] == 1
    assert model["sequence_mae"]["used"] == 4
    assert res["einstimmig"]["n"] < main["n"]


def test_absent_class_is_flagged_in_the_report(tmp_path, monkeypatch):
    rows = [row(i, M.CLASSES[1 + i % 3], f"rec2123_seq{70 + i // 3:03d}") for i in range(36)]
    write_labels(tmp_path, monkeypatch, "val", rows)
    run = write_run(tmp_path / "m.json", "m", 0, {r["id"]: r["label"] for r in rows})
    evaluate.main(["--split", "val", "--predictions", run, "--n-bootstrap", "20"])
    res = json.loads((tmp_path / "eval" / "val" / "summary.json").read_text())["eigene Labels"]
    assert res["absent_classes"] == ["orientierung"]
    assert res["chance_level"] == pytest.approx(1 / 3)
    assert "Keine Beispiele" in (tmp_path / "eval" / "val" / "summary.md").read_text()


def test_fragment_uses_tracker_zones_for_both_hives():
    assert not evaluate.is_fragment(row(0, "anflug", xy=[[270, 100], [5, 300]]))  # board -> edge
    assert evaluate.is_fragment(row(0, "anflug", xy=[[270, 100], [270, 300]]))  # board -> middle of the image
    assert evaluate.is_fragment(row(0, "anflug", "rec2125_seq000", xy=[[270, 300], [5, 300]]))
