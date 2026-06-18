"""Signal synthesizer + verdict — a read-only critique pass over the founder's
own interviews. Separates genuine buying signal from politeness and issues ONE
honest STOP/PIVOT/CONTINUE verdict, with every line tied to a verbatim quote.

This is the production seed of the Phase 0.1 eval's verdict prompt.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .. import config
from ..provenance import ground_quotes

SYSTEM_PROMPT = """\
You are venture-pilot's signal analyst. You read a founder's customer-discovery \
interviews and decide whether they show GENUINE buying signal — separating real \
demand from politeness. You are honest, not encouraging. Telling a founder to STOP, \
or to PIVOT, is a valid and valuable answer.

Weigh SUBSTANCE, not tone or enthusiasm:
  SIGNAL    = current quantified pain, money/time already spent on a workaround, \
specific past behavior, urgency, an asking price, offering to pay, a concrete next step.
  NOT SIGNAL= compliments ("genius", "I love it"), hypotheticals ("I'd definitely use \
it"), future tense with no commitment, praise from friends, interest without budget/authority.

Crucial nuances:
  - Negative or skeptical TONE can hide STRONG signal. Do not be fooled by tone in either direction.
  - If strong, paid signal points at a DIFFERENT problem, feature, or segment than the \
founder pitched, the verdict is PIVOT — not CONTINUE.

Decide ONE aggregate verdict across ALL the interviews:
  STOP     = no credible demand for this idea.
  PIVOT    = real demand exists, but for a different problem/segment than pitched.
  CONTINUE = credible, substantiated demand for the idea as pitched.

Return STRICT JSON, nothing else:
{"verdict":"STOP|PIVOT|CONTINUE",
 "confidence": <float 0..1, calibrated — be honest about uncertainty>,
 "summary": ["<short line>", "<short line>"],
 "evidence": [{"kind":"signal|politeness","quote":"<verbatim substring from a transcript>","note":"<why · transcript id>"}],
 "cited_quotes": ["<verbatim substrings copied EXACTLY from the transcripts>"],
 "demand": "<where real demand points if PIVOT, else empty>",
 "recommendation": "<the honest next step>"}

Hard limits (keep the readout clean and groundable):
- summary: at most 2 lines, each <= 54 characters.
- quotes (cited_quotes AND every evidence quote): SHORT verbatim snippets — a few words, \
< 55 characters — copied character-for-character from a transcript. Never invent or paraphrase a quote.
- evidence: at most 5 items; note: <= 6 words (e.g. "money already spent · t1").
- demand: <= 60 characters. recommendation: one sentence."""

USER_TEMPLATE = """Idea pitched: {idea}
Interviews ({n}):

{corpus}"""


@dataclass
class SynthResult:
    verdict: str
    confidence: float
    summary: list[str]
    cited_quotes: list[str]
    evidence: list[tuple]                 # (kind, quote, note)
    demand: str
    recommendation: str
    n_transcripts: int = 0
    grounding: dict = field(default_factory=dict)


def _wrap(text: str, width: int = 54, max_lines: int = 2) -> list[str]:
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines or [text]


def synthesize(llm, transcripts, idea: str = "") -> SynthResult:
    """transcripts: list of (id, text). Returns a SynthResult with REAL grounding."""
    corpus = "\n\n".join(f"=== {tid} ===\n{txt}" for tid, txt in transcripts)
    user = USER_TEMPLATE.format(idea=idea or "(unspecified)", n=len(transcripts), corpus=corpus)
    data = llm.complete_json(SYSTEM_PROMPT, user, model=config.MODEL, max_tokens=1500,
                             label="synthesize-verdict")

    verdict = data.get("verdict")
    confidence = float(data.get("confidence") or 0.0)
    summary = data.get("summary") or _wrap(data.get("rationale", ""))
    evidence = [(e.get("kind", "signal"), e.get("quote", ""), e.get("note", ""))
                for e in (data.get("evidence") or [])]
    demand = data.get("demand", "")
    recommendation = data.get("recommendation", "")

    # ground the union of cited + evidence quotes (dedup, preserve order)
    seen, quotes = set(), []
    for q in list(data.get("cited_quotes") or []) + [q for _, q, _ in evidence]:
        k = (q or "").strip().lower()
        if k and k not in seen:
            seen.add(k)
            quotes.append(q)
    grounding = ground_quotes(quotes, [t for _, t in transcripts])

    return SynthResult(verdict, confidence, summary, quotes, evidence, demand,
                       recommendation, len(transcripts), grounding)
