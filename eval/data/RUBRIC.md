# Labeling rubric — customer-discovery verdicts

Use this to label new transcripts consistently (keep the seed set and any real
transcripts you add on the same standard). Grounded in *The Mom Test* and First
Round's signal-vs-politeness framing.

## The three verdicts

| Verdict | Meaning | Look for |
|---|---|---|
| **CONTINUE** | Credible, substantiated demand **for the idea as pitched** | Current quantified pain; money/time already spent on a workaround; specific past behavior; urgency; asks price; offers to pay / pre-pay / make intros; a concrete next step |
| **PIVOT** | Real, paid demand exists — but for a **different problem, feature, or segment** than pitched | Strong signal (as above) attached to an adjacent problem; the pitched thing is dismissed or "fine"; a different buyer/use-case is named with willingness to pay |
| **STOP** | No credible demand from this person for this idea | Compliments without commitment; hypotheticals ("I'd use it"); no current pain; no budget/authority; praise from friends/family; satisfied with the status quo |

## Signal vs. politeness — the core discipline

**Signal (substance):** behavior and commitment — what they *already do*, *already pay
for*, *will pay for now*, lose money/time over, or will stake reputation on (intros).

**Not signal (politeness):** enthusiasm, compliments, "genius", "I'd definitely use
it", future-tense intentions, supportiveness from people who like you.

Two directions to resist:
- **Don't be fooled by positive tone** hiding no substance → that's STOP, not CONTINUE.
- **Don't be fooled by negative/skeptical tone** hiding real pain + willingness to pay
  → that's still CONTINUE.

## Trap taxonomy (the discriminator records)

A record's `trap_type`:
- `false_positive` — effusively positive, zero substance. A tone-follower says CONTINUE; truth is **STOP**.
- `false_negative` — skeptical/gruff, strong substance. A tone-follower says STOP; truth is **CONTINUE**.
- every **PIVOT** is implicitly a trap: the prospect is engaged/positive, so a tone-follower says CONTINUE, but the truth is **PIVOT**.

`naive_sentiment_guess` records what a pure tone-follower *would* answer — the baseline
the model must beat. On trap and pivot records it is, by construction, wrong.

## Record schema (one JSON object per line in `transcripts.jsonl`)

```
id                     short stable id (t01, t02, ...)
idea                   one-line hypothesis the founder pitched
segment                who was interviewed
transcript             multi-turn "Founder:/Prospect:" dialogue
ground_truth           STOP | PIVOT | CONTINUE   (held out from the judge)
trap_type              null | false_positive | false_negative
naive_sentiment_guess  STOP | PIVOT | CONTINUE   (the tone-follower's answer)
discriminating_signals list of the cues that decide the label
rationale              why this label is correct
```

The judge (`verdict.py`) is shown only `id`, `idea`, `segment`, `transcript`.

## Adding real transcripts

1. Anonymize / redact third-party PII **before** the transcript enters this repo
   (see `docs/ARCHITECTURE.md` §7 — data handling). Prefer paraphrased or redacted text.
2. Label `ground_truth` against this rubric; have a second person label blind and
   reconcile disagreements — that reconciled set becomes the human calibration set.
3. Add to `build_dataset.py` (keeps provenance + integrity checks) and regenerate.
4. Re-run `python run_eval.py --mode api` and watch the gate.
