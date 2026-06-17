# Phase 0.1 — Verdict eval

**The cheapest, highest-information test in the whole project.** Before writing any
product code, it answers one question:

> Can a model reliably tell **genuine buying signal** from **politeness** in a customer
> interview — well enough that an honest STOP / PIVOT / CONTINUE verdict beats a person
> who just follows the prospect's *tone*?

The verdict is venture-pilot's headline feature *and* its least-verifiable one (you only
learn a verdict was wrong months later). So we prove it on a labeled set first. If it
clears the bar, build it (ROADMAP Phase 2). If not, reposition: ship the verifiable
artifacts (research + landing page) and demote the verdict to an assistive summary.

## Quick start

```bash
cd eval

# 1) Offline sanity check — no API key needed. Runs the harness with a crude
#    keyword sentiment-follower as the judge. It SHOULD score badly (that proves
#    the dataset discriminates and the gate fails a tone-follower).
python run_eval.py --mode mock

# 2) The real test. Needs eval/.env (copy from .env.example): VP_MODEL + ANTHROPIC_API_KEY.
pip install -r requirements.txt
python run_eval.py --mode api

# tests (deterministic, no API)
python -m pytest tests/ -q
```

## What it measures

- **Overall accuracy** vs. three baselines: the naive sentiment-follower, random (⅓),
  and majority-class.
- **The money metric — discriminator accuracy:** accuracy on the records a tone-follower
  gets wrong (the 5 traps + 6 pivots). This is where the product must win; the naive
  baseline scores ~0% here by construction.
- **Confusion matrix**, per-class precision/recall/F1.
- **Calibration:** is the model *more* confident when it's wrong? (A trust red flag.)
- **Citation grounding:** every quote the model cites must appear verbatim in the
  transcript. Fabricated quotes are flagged — the executable form of cite-then-verify.

## The gate (ROADMAP 0.1)

`verdict_gate()` returns **PASS / WEAK / FAIL**. PASS requires all of:

| Check | Threshold |
|---|---|
| overall accuracy | ≥ 70% |
| discriminator accuracy | ≥ 60% |
| beats naive baseline by | ≥ 20 pts |
| citation grounding | ≥ 90% |

`WEAK` = some lift over naive/random but below bar (iterate prompt/model, grow the
dataset). `FAIL` = no better than a tone-follower (reposition the product).
Thresholds live in `score.py` (`GATE`) — tune as the real dataset grows. The runner
exits non-zero on `FAIL` so it can gate CI.

## Files

```
run_eval.py          CLI: run judge over the set, score, print report, write out/results_*.json
verdict.py           the judge — api mode (the seed of the production verdict prompt) + mock baseline
score.py             pure, unit-tested scoring + the gate
config.py            env-only config (model id never hardcoded; reads .env)
data/build_dataset.py  source of the dataset (dicts -> transcripts.jsonl, with integrity checks)
data/transcripts.jsonl 18 labeled transcripts (6 STOP / 6 PIVOT / 6 CONTINUE; 5 traps)
data/RUBRIC.md       labeling standard + how to add real transcripts
tests/               deterministic tests for scoring (12) and dataset integrity (7)
```

## Notes

- The 18 transcripts are *realistically simulated* seed data (per ROADMAP 0.1). Replace
  and augment them with real, redacted interview transcripts from the Phase 0.2 manual
  sessions — see `data/RUBRIC.md`. The seed set's job is to make the harness real and
  to encode the failure modes (compliment traps, gruff-but-real, wrong-problem pivots).
- The model id and API key live only in `eval/.env` (gitignored). Nothing tracked in
  this repo hardcodes them.
