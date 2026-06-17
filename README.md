# venture-pilot

**An AI co-pilot that gets a founder from a raw idea to trustworthy signal from real customers — fast, cited, and honest enough to bet on.**

venture-pilot is *not* another "type an idea, get a score" toy and *not* a fire-and-forget autonomous "AI employee." It is a human-in-the-loop workspace that does the painful connective-tissue work around real customer discovery, and tells you the truth about what it finds — including when the truth is *stop*.

> Long-term vision: an agentic co-founder that orchestrates the business functions around building a startup (research, product, GTM, ops). We get there by first nailing **one** painful, recurring, verifiable job — not by faking the whole company on day one.

## The job it does

For a pre-seed / first-time founder with an idea:

1. **Finds the exact target customers and communities** for the idea — read-only research with a real source link behind every claim.
2. **Drafts the outreach + interview script** tailored to those people.
3. **Generates the test artifact** — a focused landing page / one-page pitch you can put in front of real people.
4. **Synthesizes the signal** — you run the conversations (always you, never the agent); it ingests your notes/transcripts and separates *genuine buying intent* from *politeness*, then issues an evidence-cited **STOP / PIVOT / CONTINUE** verdict where every line links back to a real quote or source.

You make the calls. The agent preps and synthesizes. Nothing gets **sent, published, solicited, or launched** without you approving it.

## Principles (why people will actually return)

- **Honesty over cheerleading.** Every incumbent outputs a feel-good 78/100. venture-pilot will tell you to stop, and show you why.
- **Provenance over assertion.** Every market claim links to its source; every claimed outcome is a logged, verifiable event — never a number we just assert. Outcomes cannot be faked.
- **Cite-then-verify.** Facts are grounded in retrieved sources and entailment-checked. When the evidence isn't there, the agent abstains instead of hallucinating.
- **Human gates on anything irreversible.** Plan → preview → approve → execute. Read-only research runs freely; side effects ask first.
- **Bounded and observable.** Hard caps on steps/tokens/cost with a kill-switch; full traces of every step, tool, and source.

## Status

Greenfield. This repo currently contains the strategy, architecture, and roadmap — see [`docs/`](docs/). Code lands after the Phase 0 validation gates pass (see [`docs/ROADMAP.md`](docs/ROADMAP.md)).

## Repo contents

- [`eval/`](eval/) — the **Phase 0.1 verdict eval**: a harness that tests whether a model can separate genuine customer signal from politeness — 18 labeled interview transcripts (with deliberate "politeness traps"), scoring, a pass/fail gate, and a test suite. Try it offline with `python eval/run_eval.py --mode mock`.

Detailed strategy, architecture, go-to-market, and business-model planning are maintained privately while the idea is validated.
