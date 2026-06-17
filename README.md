<!-- ╔══════════════════════════════════════════════════════════════════════╗ -->
<!-- ║                          v e n t u r e - p i l o t                     ║ -->
<!-- ╚══════════════════════════════════════════════════════════════════════╝ -->

<div align="center">

<img src="docs/assets/logo.svg" alt="venture-pilot" width="640">

<h3>From a raw idea to signal you can bet on — fast, cited, and honest enough to act on.</h3>

<p>
An AI co-pilot that does the painful connective-tissue work around real customer discovery —<br>
and tells you the truth about what it finds, <strong>including when the truth is <em>stop</em>.</strong>
</p>

<p>
<img alt="status" src="https://img.shields.io/badge/status-Phase%200%20·%20validation-20E3A2?style=flat-square&labelColor=0A0E14">
<img alt="honesty" src="https://img.shields.io/badge/design-honest%20by%20default-5B8DEF?style=flat-square&labelColor=0A0E14">
<img alt="python" src="https://img.shields.io/badge/python-3.13-E6EDF3?style=flat-square&labelColor=0A0E14">
<img alt="tests" src="https://img.shields.io/badge/eval%20tests-19%20passing-20E3A2?style=flat-square&labelColor=0A0E14">
<img alt="prs" src="https://img.shields.io/badge/PRs-welcome-5B8DEF?style=flat-square&labelColor=0A0E14">
</p>

<p>
<a href="#-the-problem">Why</a> ·
<a href="#-what-it-does">What it does</a> ·
<a href="#-try-it-in-60-seconds">Quickstart</a> ·
<a href="#-the-honest-verdict">The verdict</a> ·
<a href="#-principles">Principles</a> ·
<a href="#-status-and-roadmap">Roadmap</a>
</p>

</div>

---

<div align="center">

<img src="docs/assets/demo.gif" alt="venture-pilot concept demo — the envisioned end-to-end customer-discovery flow ending in an honest, quote-grounded verdict" width="840">

<sub><strong>Concept demo — the envisioned flow.</strong> <em>Cited research → drafted artifacts (nothing sent) → <strong>you</strong> run the interviews → an honest, quote-grounded <strong>PIVOT</strong> verdict with calibrated confidence.</em></sub>

<sub>👉 This is the product we're building toward — <strong>it isn't built yet.</strong> What actually runs <strong>today</strong> is the Phase&nbsp;0.1 honesty eval: <a href="#-try-it-in-60-seconds">try it in 60 seconds ↓</a></sub>

</div>

<br>

> **What this is.** venture-pilot is a human-in-the-loop workspace for first-time and pre-seed founders. It is **not** another "type an idea, get a 78/100" toy, and **not** a fire-and-forget "AI employee." It preps and synthesizes the work around real customer discovery — *you* run the conversations and make every call.
>
> **Long-term vision:** an agentic co-founder that orchestrates the business functions around building a startup (research, product, GTM, ops). We earn that by first nailing **one** painful, recurring, verifiable job — not by faking the whole company on day one.

---

## 🎯 The problem

Every "idea validator" on the market is a flattery machine. You type your idea, it returns a confident **78/100**, a glossy SWOT, and a pat on the back. None of it touches a real customer. None of it is allowed to tell you the answer that actually saves your year:

> **Stop. Nobody is going to pay for this.**

Real founders don't die from a missing score. They die from **mistaking politeness for demand** — "I'd totally use that!" from someone who never will — and burning twelve months building it. The hard, unglamorous, genuinely valuable job is separating *genuine buying signal* from *being nice to your face*, and being honest about the result.

That's the one job venture-pilot is built to do well first.

---

## ✦ What it does

For a pre-seed / first-time founder with an idea, it runs the discovery wedge end-to-end — **research is automatic, every irreversible action waits for you:**

| # | Step | What the agent does | Who acts |
|:-:|------|---------------------|:--------:|
| **1** | 🧭 **Find the customers** | Read-only research that surfaces the exact target customers + communities, with a **real source link behind every claim**. | agent |
| **2** | ✍️ **Draft the outreach** | A tailored outreach + interview script for those specific people. | agent → *you send* |
| **3** | 📄 **Build the test artifact** | A focused landing page / one-page pitch you can put in front of real humans. | agent → *you publish* |
| **4** | ⚖️ **Synthesize the signal** | You run the conversations; it ingests your notes/transcripts, separates **buying intent from politeness**, and issues an evidence-cited **STOP / PIVOT / CONTINUE** verdict — every line linked to a real quote or source. | *you interview* → agent |

**You make the calls. The agent preps and synthesizes.** Nothing gets **sent, published, solicited, or launched** without your explicit approval.

---

## ⚖ The honest verdict

The headline feature is also the least-verifiable one — you only find out a verdict was *wrong* months later. So venture-pilot treats it like an instrument that must be calibrated, not an oracle to be trusted. It returns one of three honest answers, and **shows its work:**

| Verdict | Means | Grounded in |
|---------|-------|-------------|
| 🟥 **STOP** | No credible demand for this idea, from this person. | the quotes that *aren't* there |
| 🟧 **PIVOT** | Real, paid demand exists — but for a *different* problem or segment than you pitched. | the signal pointing elsewhere |
| 🟩 **CONTINUE** | Credible, substantiated demand for the idea **as pitched**. | behavior + money + urgency, quoted verbatim |

It weighs **substance over tone** — money already spent on a workaround, specific past behavior, urgency, an asking price — and is explicitly *not* fooled by enthusiasm ("genius!", "I'd definitely use it") or by a gruff tone that hides real pain. When the evidence isn't there, it **abstains** instead of inventing a number.

---

## 🚀 Try it in 60 seconds

You can run the project's first real artifact — the **Phase 0.1 verdict eval** — right now, offline, no API key. It's the test that validates (or kills) the entire honesty thesis *before* any product is built.

```bash
git clone <this-repo> && cd venture-pilot/eval

# Offline sanity check — no API key. Runs a naive keyword sentiment-follower
# as the judge. It SHOULD score badly: that proves the dataset has teeth and
# the gate correctly fails a tone-follower.
python run_eval.py --mode mock

# The real test (needs eval/.env: VP_MODEL + ANTHROPIC_API_KEY)
pip install -r requirements.txt
python run_eval.py --mode api

# Deterministic test suite (19 tests, no API)
python -m pytest tests/ -q
```

**What you'll see:** each of 18 labeled transcripts judged, accuracy vs. three baselines, the **"money metric"** (accuracy on the records a tone-follower gets wrong), a confusion matrix, calibration, citation-grounding, and a single **PASS / WEAK / FAIL** gate decision.

> In `--mode mock` the naive tone-follower scores **~11% and fails the gate on purpose** — it's the dumb baseline the real model has to beat by ≥20 points. That failure is the proof the eval actually discriminates.

---

## 🛡 Principles

*Why people will actually come back — the opposite of every flattery machine:*

<table>
<tr>
<td width="50%" valign="top">

#### 🫀 Honesty over cheerleading
Every incumbent outputs a feel-good 78/100. venture-pilot will tell you to **stop**, and show you exactly why.

</td>
<td width="50%" valign="top">

#### 🔗 Provenance over assertion
Every market claim links to its source. Every claimed outcome is a logged, verifiable event — never a number we just assert. **Outcomes can't be faked.**

</td>
</tr>
<tr>
<td width="50%" valign="top">

#### 🔬 Cite-then-verify
Facts are grounded in retrieved sources and entailment-checked. When the evidence isn't there, the agent **abstains** instead of hallucinating.

</td>
<td width="50%" valign="top">

#### 🚦 Human gates on anything irreversible
**Plan → preview → approve → execute.** Read-only research runs freely; anything with a side effect asks first.

</td>
</tr>
<tr>
<td colspan="2" valign="top">

#### 📊 Bounded & observable
Hard caps on steps / tokens / cost with a kill-switch, and full traces of every step, tool, and source. No runaway agents, no black boxes.

</td>
</tr>
</table>

---

## 📦 What's in this repo

This is a **greenfield** project being de-risked in public. Code lands only after the Phase 0 validation gates pass. What's public today:

| Path | What it is |
|------|-----------|
| [**`eval/`**](eval/) | The **Phase 0.1 verdict eval** — a real, runnable harness testing whether a model can separate genuine signal from politeness. 18 labeled transcripts (with deliberate *politeness traps*), scoring, a pass/fail gate, and 19 deterministic tests. |
| [`eval/data/`](eval/data/) | The labeled transcript set + the [`RUBRIC.md`](eval/data/RUBRIC.md) labeling standard for adding real interviews. |
| [`docs/assets/`](docs/assets/) | Brand assets, plus the concept-demo storyboard (`concept_demo.py` + `demo.tape`) that generates the GIF above. |

> The full **strategy, architecture, roadmap, GTM, and business-model** docs are kept **private while the idea is validated.** The [`eval/`](eval/) harness is public on purpose — it's the part that proves or kills the thesis.

---

## 🗺 Status and roadmap

**Greenfield — Phase 0 (validation before code).** The honesty thesis is being proven on a labeled eval set before any product is built. The wedge ships *verifiable artifacts first* (cited research + landing page), and the headline verdict feature ships **only if the Phase 0.1 eval clears its gate.**

```
Phase 0  ░ De-risk before code      → kill/redesign gates  ·  ← we are here
Phase 1  ░ Verifiable-artifact MVP  → cited research + landing page
Phase 2  ░ The honest verdict       → STOP/PIVOT/CONTINUE + first paying users
Phase 3  ░ Escape one-shot churn    → recurring weekly signal digest
Phase 4  ░ Expand toward the vision → only after a retention floor
```

Each phase is a **kill/redesign gate** — validation before code. The detailed roadmap, gates, and milestones are kept private during validation.

---

## 🤝 Follow the build

There are no fake users here and there won't be — but if the honesty wedge resonates, you can help prove it out:

- ⭐ **Star / watch** the repo to follow the validation in public.
- 🧪 **Run the eval** (`python run_eval.py --mode mock`) and open an issue with what you find.
- 🗣️ **Bring real transcripts.** The eval gets sharper with real, redacted interview data — see [`eval/data/RUBRIC.md`](eval/data/RUBRIC.md) for the labeling standard.
- 💡 **Disagree well.** The fastest way to improve an honesty tool is an adversarial counter-example. PRs and issues welcome.

---

<div align="center">
<sub>Built in the open · validation before code · honesty over cheerleading.</sub>
<br>
<sub>Permanent guardrail: <strong>send / publish / solicit / launch stays human-gated, always.</strong></sub>
</div>
