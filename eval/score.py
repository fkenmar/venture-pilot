"""Pure, deterministic scoring for the Phase 0.1 verdict eval.

No I/O, no model calls — every function here is unit-tested in tests/test_score.py.
The headline question: does the model's STOP/PIVOT/CONTINUE verdict beat a naive
sentiment-follower, especially on the trap/pivot 'discriminator' records?
"""
from __future__ import annotations

LABELS = ("STOP", "PIVOT", "CONTINUE")

# Gate thresholds (v0 — tune as the real dataset grows). See README "The gate".
GATE = {
    "overall_acc": 0.70,        # model must classify >=70% correctly
    "discriminator_acc": 0.60,  # >=60% on the records sentiment-following fails
    "beats_naive_by": 0.20,     # model - naive baseline, absolute
    "citation_grounding": 0.90, # >=90% of cited quotes must really appear in transcript
}


def accuracy(preds, truths):
    if not preds:
        return 0.0
    return sum(p == t for p, t in zip(preds, truths)) / len(preds)


def confusion_matrix(preds, truths, labels=LABELS):
    """Return {truth_label: {pred_label: count}}."""
    m = {t: {p: 0 for p in labels} for t in labels}
    for p, t in zip(preds, truths):
        if t in m and p in m[t]:
            m[t][p] += 1
    return m


def per_class_prf(preds, truths, labels=LABELS):
    """Precision / recall / f1 per label."""
    out = {}
    for lab in labels:
        tp = sum(p == lab and t == lab for p, t in zip(preds, truths))
        fp = sum(p == lab and t != lab for p, t in zip(preds, truths))
        fn = sum(p != lab and t == lab for p, t in zip(preds, truths))
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out[lab] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
    return out


def majority_baseline(truths):
    """Accuracy of always guessing the most common true label."""
    if not truths:
        return 0.0
    counts = {l: truths.count(l) for l in set(truths)}
    top = max(counts.values())
    return top / len(truths)


def random_baseline(labels=LABELS):
    return 1.0 / len(labels)


def is_discriminator(record):
    """A record where a tone-follower gets it wrong: any trap, or any PIVOT
    (a sentiment-follower never outputs PIVOT)."""
    return bool(record.get("trap_type")) or record.get("ground_truth") == "PIVOT"


def subset_accuracy(records, preds_by_id, predicate):
    """Accuracy over records matching predicate(record)."""
    ids = [r["id"] for r in records if predicate(r)]
    if not ids:
        return None
    truth = {r["id"]: r["ground_truth"] for r in records}
    correct = sum(preds_by_id.get(i) == truth[i] for i in ids)
    return correct / len(ids)


def naive_baseline_accuracy(records, predicate=None):
    """Accuracy of the held-in naive_sentiment_guess vs ground truth."""
    rs = [r for r in records if (predicate is None or predicate(r))]
    if not rs:
        return None
    return sum(r["naive_sentiment_guess"] == r["ground_truth"] for r in rs) / len(rs)


def calibration(preds, truths, confidences):
    """Mean stated confidence when correct vs incorrect, and the overconfidence gap
    (mean confidence on wrong answers — high is bad)."""
    cor = [c for p, t, c in zip(preds, truths, confidences) if p == t and c is not None]
    wrong = [c for p, t, c in zip(preds, truths, confidences) if p != t and c is not None]
    mc = sum(cor) / len(cor) if cor else None
    mw = sum(wrong) / len(wrong) if wrong else None
    return {
        "mean_conf_correct": mc,
        "mean_conf_incorrect": mw,
        "overconfidence_on_wrong": mw,  # alias: how confident it was while wrong
        "separation": (mc - mw) if (mc is not None and mw is not None) else None,
    }


def citation_grounding(records, results_by_id):
    """Fraction of all cited quotes that actually appear (substring) in the transcript.
    Catches fabricated quotes — the cite-then-verify guardrail. Quotes are normalized
    on whitespace before the substring check."""
    def norm(s):
        return " ".join(s.split()).lower()

    transcripts = {r["id"]: norm(r["transcript"]) for r in records}
    total = grounded = 0
    offenders = []
    for rid, res in results_by_id.items():
        t = transcripts.get(rid, "")
        for q in (res.get("cited_quotes") or []):
            total += 1
            if q and norm(q) in t:
                grounded += 1
            else:
                offenders.append({"id": rid, "quote": q})
    rate = grounded / total if total else 1.0  # no citations -> vacuously grounded
    return {"rate": rate, "total_quotes": total, "grounded": grounded, "offenders": offenders}


def build_report(records, results):
    """records: list of full dataset dicts (with ground truth).
    results: list of {id, verdict, confidence, cited_quotes, ...} from the judge.
    Returns a structured report dict; verdict_gate() turns it into a decision."""
    by_id = {r["id"]: r for r in records}
    res_by_id = {x["id"]: x for x in results}
    pred_by_id = {x["id"]: x.get("verdict") for x in results}

    ordered = [r for r in records if r["id"] in res_by_id]
    preds = [res_by_id[r["id"]].get("verdict") for r in ordered]
    truths = [r["ground_truth"] for r in ordered]
    confs = [res_by_id[r["id"]].get("confidence") for r in ordered]

    disc_pred = subset_accuracy(ordered, pred_by_id, is_discriminator)
    trap_pred = subset_accuracy(ordered, pred_by_id, lambda r: bool(r.get("trap_type")))
    pivot_pred = subset_accuracy(ordered, pred_by_id, lambda r: r["ground_truth"] == "PIVOT")

    return {
        "n": len(ordered),
        "model_overall_acc": accuracy(preds, truths),
        "naive_overall_acc": naive_baseline_accuracy(ordered),
        "random_baseline": random_baseline(),
        "majority_baseline": majority_baseline(truths),
        "model_discriminator_acc": disc_pred,
        "naive_discriminator_acc": naive_baseline_accuracy(ordered, is_discriminator),
        "model_trap_acc": trap_pred,
        "model_pivot_acc": pivot_pred,
        "confusion_matrix": confusion_matrix(preds, truths),
        "per_class": per_class_prf(preds, truths),
        "calibration": calibration(preds, truths, confs),
        "citation_grounding": citation_grounding(ordered, res_by_id),
    }


def verdict_gate(report):
    """Turn a report into the ROADMAP 0.1 decision: PASS / WEAK / FAIL, with reasons."""
    reasons = []
    overall = report["model_overall_acc"]
    disc = report["model_discriminator_acc"] or 0.0
    naive = report["naive_overall_acc"] or 0.0
    beats_naive = overall - naive
    cite = report["citation_grounding"]["rate"]

    checks = {
        "overall_acc>=%.2f" % GATE["overall_acc"]: overall >= GATE["overall_acc"],
        "discriminator_acc>=%.2f" % GATE["discriminator_acc"]: disc >= GATE["discriminator_acc"],
        "beats_naive_by>=%.2f" % GATE["beats_naive_by"]: beats_naive >= GATE["beats_naive_by"],
        "citation_grounding>=%.2f" % GATE["citation_grounding"]: cite >= GATE["citation_grounding"],
    }
    for name, ok in checks.items():
        if not ok:
            reasons.append(name)

    if all(checks.values()):
        decision = "PASS"
    elif overall > report["random_baseline"] and beats_naive > 0:
        decision = "WEAK"
    else:
        decision = "FAIL"
    return {"decision": decision, "checks": checks, "failed": reasons,
            "beats_naive_by": beats_naive}
