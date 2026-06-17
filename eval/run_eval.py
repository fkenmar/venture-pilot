#!/usr/bin/env python3
"""Phase 0.1 eval runner.

Runs the verdict judge over the labeled transcript set and reports whether the
model's STOP/PIVOT/CONTINUE verdict beats a naive sentiment-follower — the test
that validates (or kills) the honesty wedge before any product code is written.

Usage:
  python run_eval.py --mode mock          # no API key; runs the naive baseline as judge
  python run_eval.py --mode api           # real model (needs eval/.env: VP_MODEL + key)
  python run_eval.py --mode api --limit 4 # quick smoke test on 4 transcripts
"""
from __future__ import annotations

import argparse
import json
import os

import score
from verdict import make_judge

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "data", "transcripts.jsonl")
OUT_DIR = os.path.join(HERE, "out")


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def pct(x):
    return "  n/a" if x is None else f"{x * 100:5.1f}%"


def print_report(rep, gate, mode):
    R = rep
    print("\n" + "=" * 64)
    print(f"  venture-pilot — Phase 0.1 verdict eval   (judge mode: {mode})")
    print("=" * 64)
    print(f"  transcripts scored: {R['n']}")
    print("\n  ACCURACY")
    print(f"    model overall .............. {pct(R['model_overall_acc'])}")
    print(f"    naive sentiment baseline ... {pct(R['naive_overall_acc'])}")
    print(f"    random (1/3) ............... {pct(R['random_baseline'])}")
    print(f"    majority class ............. {pct(R['majority_baseline'])}")
    print("\n  THE MONEY METRIC — discriminator records (traps + pivots)")
    print(f"    model ...................... {pct(R['model_discriminator_acc'])}")
    print(f"    naive on same records ...... {pct(R['naive_discriminator_acc'])}")
    print(f"    model on traps only ........ {pct(R['model_trap_acc'])}")
    print(f"    model on pivots only ....... {pct(R['model_pivot_acc'])}")
    print("\n  CONFUSION MATRIX  (rows = truth, cols = predicted)")
    labs = score.LABELS
    print("    " + " " * 10 + "".join(f"{l[:4]:>8}" for l in labs))
    for t in labs:
        row = R["confusion_matrix"][t]
        print(f"    {t:>10}" + "".join(f"{row[p]:>8}" for p in labs))
    cal = R["calibration"]
    print("\n  CALIBRATION")
    print(f"    mean confidence when correct ..... {pct(cal['mean_conf_correct'])}")
    print(f"    mean confidence when WRONG ....... {pct(cal['mean_conf_incorrect'])}"
          + ("   <- overconfident" if (cal['mean_conf_incorrect'] or 0) >= 0.7 else ""))
    cg = R["citation_grounding"]
    print("\n  CITATION GROUNDING (quotes that really appear in the transcript)")
    print(f"    rate ....................... {pct(cg['rate'])}  ({cg['grounded']}/{cg['total_quotes']})")
    if cg["offenders"]:
        print(f"    FABRICATED QUOTES: {len(cg['offenders'])} (see results file) <- trust risk")
    print("\n" + "-" * 64)
    print(f"  GATE DECISION: {gate['decision']}    (model beats naive by "
          f"{gate['beats_naive_by'] * 100:+.1f} pts)")
    for name, ok in gate["checks"].items():
        print(f"    [{'PASS' if ok else 'FAIL'}] {name}")
    if gate["decision"] == "PASS":
        print("  -> Headline feature validated. Proceed to build it (ROADMAP Phase 2).")
    elif gate["decision"] == "WEAK":
        print("  -> Some lift over naive, below bar. Iterate the prompt/model, expand data,")
        print("     and lead the product with the verifiable artifacts (Phase 1) meanwhile.")
    else:
        print("  -> Headline feature NOT validated. Reposition: ship the verifiable-artifact")
        print("     wedge; demote the verdict to an assistive summary (ROADMAP 0.1 gate).")
    print("=" * 64 + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["mock", "api"], default="mock")
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--limit", type=int, default=0, help="score only the first N (0 = all)")
    args = ap.parse_args()

    records = load(args.data)
    if args.limit:
        records = records[: args.limit]
    judge = make_judge(args.mode)

    results = []
    for i, rec in enumerate(records, 1):
        res = judge(rec)
        results.append(res)
        print(f"  [{i}/{len(records)}] {rec['id']}: {res.get('verdict')} "
              f"(truth {rec['ground_truth']})"
              + ("" if res.get("verdict") == rec["ground_truth"] else "   X"))

    rep = score.build_report(records, results)
    gate = score.verdict_gate(rep)
    print_report(rep, gate, args.mode)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, f"results_{args.mode}.json"), "w") as f:
        json.dump({"mode": args.mode, "results": results, "report": rep, "gate": gate},
                  f, indent=2, ensure_ascii=False)
    print(f"  full results -> {os.path.join(args.out, f'results_{args.mode}.json')}\n")
    return 0 if gate["decision"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
