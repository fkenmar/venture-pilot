"""Deterministic unit tests for the scoring logic (no model calls)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import score  # noqa: E402


def test_accuracy_basic():
    assert score.accuracy(["STOP", "PIVOT"], ["STOP", "STOP"]) == 0.5
    assert score.accuracy([], []) == 0.0
    assert score.accuracy(["CONTINUE"], ["CONTINUE"]) == 1.0


def test_confusion_matrix_counts():
    cm = score.confusion_matrix(["STOP", "PIVOT", "STOP"], ["STOP", "STOP", "PIVOT"])
    assert cm["STOP"]["STOP"] == 1
    assert cm["STOP"]["PIVOT"] == 1   # truth STOP predicted PIVOT
    assert cm["PIVOT"]["STOP"] == 1   # truth PIVOT predicted STOP


def test_per_class_prf_perfect():
    preds = ["STOP", "PIVOT", "CONTINUE"]
    prf = score.per_class_prf(preds, preds)
    for lab in score.LABELS:
        assert prf[lab]["precision"] == 1.0
        assert prf[lab]["recall"] == 1.0
        assert prf[lab]["f1"] == 1.0


def test_majority_and_random_baselines():
    assert score.majority_baseline(["STOP", "STOP", "PIVOT"]) == 2 / 3
    assert abs(score.random_baseline() - 1 / 3) < 1e-9


def test_is_discriminator():
    assert score.is_discriminator({"trap_type": "false_positive", "ground_truth": "STOP"})
    assert score.is_discriminator({"trap_type": None, "ground_truth": "PIVOT"})
    assert not score.is_discriminator({"trap_type": None, "ground_truth": "CONTINUE"})


def test_naive_baseline_accuracy():
    recs = [
        {"id": "a", "naive_sentiment_guess": "CONTINUE", "ground_truth": "CONTINUE", "trap_type": None},
        {"id": "b", "naive_sentiment_guess": "CONTINUE", "ground_truth": "STOP", "trap_type": "false_positive"},
    ]
    assert score.naive_baseline_accuracy(recs) == 0.5
    # on the trap subset only, naive is 0%
    assert score.naive_baseline_accuracy(recs, score.is_discriminator) == 0.0


def test_subset_accuracy():
    recs = [
        {"id": "a", "ground_truth": "STOP", "trap_type": "false_positive"},
        {"id": "b", "ground_truth": "PIVOT", "trap_type": None},
        {"id": "c", "ground_truth": "CONTINUE", "trap_type": None},
    ]
    preds = {"a": "STOP", "b": "STOP", "c": "CONTINUE"}  # got the pivot wrong
    acc = score.subset_accuracy(recs, preds, score.is_discriminator)
    assert acc == 0.5  # a correct, b wrong; c is not a discriminator
    assert score.subset_accuracy(recs, preds, lambda r: r["id"] == "zzz") is None


def test_calibration_separation():
    preds = ["STOP", "PIVOT"]
    truths = ["STOP", "CONTINUE"]  # first correct, second wrong
    cal = score.calibration(preds, truths, [0.9, 0.8])
    assert cal["mean_conf_correct"] == 0.9
    assert cal["mean_conf_incorrect"] == 0.8
    assert abs(cal["separation"] - 0.1) < 1e-9


def test_citation_grounding_detects_fabrication():
    recs = [{"id": "a", "transcript": "Manager: we had 47 no-shows last month."}]
    results = {
        "a": {"cited_quotes": ["we had 47 no-shows", "I will pay you a million dollars"]},
    }
    g = score.citation_grounding(recs, results)
    assert g["total_quotes"] == 2
    assert g["grounded"] == 1            # only the real one is grounded
    assert g["rate"] == 0.5
    assert g["offenders"][0]["id"] == "a"


def test_citation_grounding_whitespace_normalization():
    recs = [{"id": "a", "transcript": "Owner:  send   me\nthe contract"}]
    results = {"a": {"cited_quotes": ["send me the contract"]}}
    assert score.citation_grounding(recs, results)["rate"] == 1.0


def test_build_report_and_gate_pass():
    # a perfect run on a tiny balanced set -> PASS
    records = [
        {"id": "a", "transcript": "x pay today", "ground_truth": "CONTINUE",
         "naive_sentiment_guess": "CONTINUE", "trap_type": None},
        {"id": "b", "transcript": "y love it genius", "ground_truth": "STOP",
         "naive_sentiment_guess": "CONTINUE", "trap_type": "false_positive"},
        {"id": "c", "transcript": "z different problem", "ground_truth": "PIVOT",
         "naive_sentiment_guess": "CONTINUE", "trap_type": None},
    ]
    results = [
        {"id": "a", "verdict": "CONTINUE", "confidence": 0.9, "cited_quotes": ["pay today"]},
        {"id": "b", "verdict": "STOP", "confidence": 0.8, "cited_quotes": ["love it genius"]},
        {"id": "c", "verdict": "PIVOT", "confidence": 0.7, "cited_quotes": ["different problem"]},
    ]
    rep = score.build_report(records, results)
    assert rep["model_overall_acc"] == 1.0
    assert rep["model_discriminator_acc"] == 1.0
    assert abs(rep["naive_overall_acc"] - 1 / 3) < 1e-9  # naive only gets 'a'
    gate = score.verdict_gate(rep)
    assert gate["decision"] == "PASS"


def test_gate_fail_when_no_better_than_random():
    records = [
        {"id": "a", "transcript": "t", "ground_truth": "CONTINUE",
         "naive_sentiment_guess": "CONTINUE", "trap_type": None},
        {"id": "b", "transcript": "t", "ground_truth": "STOP",
         "naive_sentiment_guess": "CONTINUE", "trap_type": "false_positive"},
        {"id": "c", "transcript": "t", "ground_truth": "PIVOT",
         "naive_sentiment_guess": "CONTINUE", "trap_type": None},
    ]
    # model just echoes the naive sentiment guess -> no lift
    results = [{"id": r["id"], "verdict": "CONTINUE", "confidence": 0.6, "cited_quotes": []}
               for r in records]
    rep = score.build_report(records, results)
    gate = score.verdict_gate(rep)
    assert gate["decision"] in ("FAIL", "WEAK")
    assert gate["beats_naive_by"] == 0.0
