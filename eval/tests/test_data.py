"""Integrity tests for the seed transcript dataset."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import score  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "transcripts.jsonl")


def load():
    with open(DATA) as f:
        return [json.loads(line) for line in f if line.strip()]


def test_dataset_loads_and_is_nonempty():
    recs = load()
    assert len(recs) >= 15  # ROADMAP 0.1 calls for 15-20


def test_unique_ids():
    recs = load()
    ids = [r["id"] for r in recs]
    assert len(ids) == len(set(ids))


def test_labels_valid_and_balanced():
    recs = load()
    counts = {l: sum(r["ground_truth"] == l for r in recs) for l in score.LABELS}
    for l in score.LABELS:
        assert r_ok(recs, l), f"label {l} invalid somewhere"
        assert counts[l] >= 4, f"class {l} underrepresented: {counts}"


def r_ok(recs, label):
    return all(r["ground_truth"] in score.LABELS for r in recs)


def test_required_fields_present():
    for r in load():
        for k in ("id", "idea", "segment", "transcript", "ground_truth",
                  "trap_type", "naive_sentiment_guess"):
            assert k in r, f"{r.get('id')} missing {k}"
        assert r["trap_type"] in (None, "false_positive", "false_negative")
        assert r["naive_sentiment_guess"] in score.LABELS


def test_has_both_trap_directions():
    recs = load()
    types = {r["trap_type"] for r in recs}
    assert "false_positive" in types  # polite-but-empty
    assert "false_negative" in types  # gruff-but-real


def test_naive_baseline_is_beatable_but_not_trivial():
    """The dataset must be discriminating: a tone-follower should do POORLY on the
    discriminator subset (so a substance-reading model can demonstrate lift)."""
    recs = load()
    naive_disc = score.naive_baseline_accuracy(recs, score.is_discriminator)
    assert naive_disc is not None
    assert naive_disc <= 0.20, f"naive baseline too strong on discriminators: {naive_disc}"


def test_naive_guess_differs_from_truth_on_traps():
    for r in load():
        if r["trap_type"]:
            assert r["naive_sentiment_guess"] != r["ground_truth"], \
                f"{r['id']} trap should fool the sentiment-follower"
