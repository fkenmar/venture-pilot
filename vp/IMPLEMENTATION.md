# venture-pilot — Implementation workflow & agentic structure

*How the `vp` app is built so it behaves exactly like [`docs/assets/demo.gif`](../docs/assets/demo.gif) — and stays honest while doing it. This is the build contract; the design rationale lives in `docs/ARCHITECTURE.md` (private).*

## 0. What "done" means

`vp` reproduces the demo end-to-end, for real:

```
vp validate "<idea>"          # PLAN → approve gate → cited RESEARCH → drafted ARTIFACTS → human-gate PAUSE
vp synthesize ./interviews/*  # SIGNAL SYNTHESIS → grounded STOP/PIVOT/CONTINUE verdict + calibrated confidence
```

Three real backends, one code path around them — pick any LLM you want:

| Backend | Model calls | For |
|------|-------------|-----|
| **`--api`** | Anthropic Messages API + server-side `web_search` | downloaded users — their own `ANTHROPIC_API_KEY` + `VP_MODEL` |
| **`--sdk`** | Claude Agent SDK on a logged-in Claude Pro/Max subscription | running on a subscription, no API key (our dev path) |
| **`--openai`** | any OpenAI-compatible `/v1/chat/completions` (OpenAI / OpenRouter / Groq / local …) | bring any LLM you want |

There is **no offline/mock mode** — the app always uses a real LLM. `vp` auto-selects the configured backend (`VP_BACKEND` pins it): a custom LLM → `--openai`, your key → `--api`, else a logged-in subscription → `--sdk`; if nothing's set up it prints setup help. Tests inject a FakeLLM or stub a transport, so the orchestration, grounding, caps, and tracing run with no network and no model.

## 1. Agentic structure (single-writer orchestrator + read-only subagents)

Per `docs/ARCHITECTURE.md §1`, this is a **read/write split**, enforced in code — not by prompt convention:

```
        vp validate "<idea>"
                │
                ▼
   ┌──────────────────────────────┐     owns ALL writes (out/, trace, ledger)
   │   ORCHESTRATOR (single writer)│     sequences steps · the plan→approve→execute loop
   └───┬───────────────────┬───────┘
       │ read fan-out      │ writes
       ▼                   ▼
  RESEARCH subagents   ARTIFACT drafter ──► out/interview-script.md, out/outreach.md, out/landing/index.html
  (read-only, cited,   (single-writer,        (labeled DRAFT — publish/send gated)
   abstain on no src)   draft-only)

        vp synthesize <transcripts>
                │
                ▼
   SIGNAL SYNTHESIZER + VERDICT (read-only critique pass) ──► STOP/PIVOT/CONTINUE + grounded quotes
```

- **Research subagents are read-only** and may run in parallel; each returns *cited findings with source URLs* and **abstains** when a claim has no source.
- **The orchestrator owns every write.** Two agents never write the same artifact. The verdict runs as a clean-context read-only critique pass, never a parallel writer.
- **Chain-length discipline:** 1–3 high-reliability steps, then a human checkpoint (the approve gate and the YOUR-MOVE pause are exactly those checkpoints).

## 2. Module map (`vp/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Entry: `validate` / `synthesize` / `doctor` / `trace`, backend flags `--api/--sdk/--openai`, `--yes`, `--out`. Renders the brand UI. |
| `orchestrator.py` | Single-writer loop: plan → preview → **approve** → execute; owns all writes; sequences agents; enforces the pause. |
| `agents/research.py` | Read-only cited research (web_search), returns `Finding`s with sources; abstains on unsupported claims. |
| `agents/artifacts.py` | Draft-only artifact writer: interview script, outreach DMs, landing page → files (labeled DRAFT). |
| `agents/synthesize.py` | Verdict judge (reuses the `eval/` `SYSTEM_PROMPT` seed): transcripts → verdict + confidence + cited quotes. |
| `llm.py` | One interface (`complete_json` / `research`) over three real backends — Anthropic Messages (+`web_search`), the Claude Agent SDK, and any OpenAI-compatible endpoint — with **usage/cost accounting**. |
| `provenance.py` | Source-linked `Fact`/`Finding` types + **citation grounding** (verbatim substring check, reused from `eval/score.py`). |
| `guardrails.py` | Hard per-run caps (steps / tokens / dollars / wall-clock) **with enforcement** + pause-for-resume kill-switch. |
| `trace.py` | Full JSONL run trace (every step, tool, source, token/cost) → `out/<run>/trace.jsonl`. |
| `ui.py` | Brand terminal UI (the venture-pilot ANSI palette + section renderers), so the live output is identical to the demo GIF. |
| `config.py` | Env-only config (model id, key, caps, mode); never hardcodes the model string. |

## 3. Reliability practices wired in (ARCHITECTURE §5, non-negotiable)

- **Cite-then-verify** — every research claim carries a source URL and passes the grounding check; unsupported → **abstain**, never assert.
- **Hard caps with enforcement** — `guardrails.py` raises a `CapExceeded` kill-switch; not just logging.
- **Single-writer in code** — only the orchestrator writes; agents return data.
- **Calibrated uncertainty** — the verdict reports confidence and the grounding rate; fabricated quotes are flagged (a trust red flag), never silently kept.
- **Validate all tool outputs** — malformed model JSON is caught and surfaced, never silently continued.
- **Full trace from step 1** — `trace.jsonl` records steps, tools, sources, tokens, cost.

## 4. Build sequence (TDD, real-LLM only)

1. **Foundations** — config, ui, llm (api/sdk/openai), trace, guardrails, provenance.
2. **`synthesize`** first (smallest; grounding is deterministic) + sample `interviews/`.
3. **`validate`** — research (cited/abstain) → artifacts (file writes) → plan/approve gate → pause.
4. **Orchestrator + CLI** — `doctor` (setup), `trace` (observability), backend auto-detect.
5. **Tests** — inject a FakeLLM / stub each transport; grounding, caps, abstention, and the flow run with **no network and no model**.
6. **Live** — exercised against a real backend (the SDK on a Claude subscription).

**Dev rules:** there is **no offline/mock mode** — the app always uses a real LLM; tests never call the network; the model id never enters tracked source; **commits are authored solely by the repo owner — no Claude author/co-author trailer.**
