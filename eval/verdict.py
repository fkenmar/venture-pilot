"""The verdict judge: a customer-interview transcript -> STOP / PIVOT / CONTINUE,
with calibrated confidence, a short rationale, and verbatim cited quotes.

Two modes:
  - "api"  : the real product prompt, run against an Anthropic model (env-configured).
             This prompt is the SEED of the production verdict prompt.
  - "mock" : a transparent keyword sentiment-follower. Requires no API key. It exists
             to (a) run the harness end-to-end offline and (b) BE the naive baseline
             the real model must beat — running mock should score badly on the traps.

The judge only ever receives id / idea / segment / transcript.
"""
from __future__ import annotations

import json
import re

import config

LABELS = ("STOP", "PIVOT", "CONTINUE")

# --- The product verdict rubric (Mom Test / First Round signal-vs-politeness) ------
SYSTEM_PROMPT = """\
You are venture-pilot's signal analyst. You read a founder's customer-discovery \
interview and decide whether it shows GENUINE buying signal — separating real \
demand from mere politeness. You are honest, not encouraging. Telling a founder to \
stop is a valid and valuable answer.

Weigh SUBSTANCE, not tone or enthusiasm:
  STRONG signal  = current quantified pain, money/time already spent on a workaround, \
specific past behavior, urgency, asking price, offering to pay / pre-pay / make intros, \
a concrete next step.
  NOT signal     = compliments ("genius", "I love it"), hypotheticals ("I'd \
definitely use it"), future tense with no commitment, praise from friends/family, \
"I'd support you", interest without authority or budget.

Crucial nuances:
  - Negative or skeptical TONE can hide STRONG signal (real pain + willingness to pay). \
Do not be fooled by tone in either direction.
  - If there is strong, paid signal but it points at a DIFFERENT problem, feature, or \
customer segment than the founder pitched, the verdict is PIVOT — not CONTINUE.

Output exactly one of:
  STOP      = no credible demand for this idea from this person.
  PIVOT     = real demand exists, but for a different problem/segment than pitched.
  CONTINUE  = credible, substantiated demand for the idea as pitched.

Return STRICT JSON, no prose outside it:
{"verdict": "STOP|PIVOT|CONTINUE",
 "confidence": <float 0..1, calibrated — be honest about uncertainty>,
 "rationale": "<2-3 sentences citing the deciding signals>",
 "cited_quotes": ["<verbatim substring(s) copied EXACTLY from the transcript that \
drive the verdict>"]}
Quotes MUST be copied character-for-character from the transcript. Never invent a quote."""

USER_TEMPLATE = """\
Idea pitched: {idea}
Segment interviewed: {segment}

Transcript:
{transcript}"""


def _judge_visible(record):
    return {k: record[k] for k in ("id", "idea", "segment", "transcript")}


# ---------------------------------------------------------------- mock baseline ----
_POS = re.compile(r"\b(love|amazing|genius|awesome|great|wonderful|incredible|"
                  r"fantastic|cool|totally|definitely|absolutely|excited|brilliant)\b", re.I)
_NEG = re.compile(r"\b(skeptical|not sure|doubt|junk|useless|nightmare|killing|"
                  r"hate|brutal|mess|awful|terrible|tolerate)\b", re.I)


def _mock_verdict(record):
    """A pure tone-follower: more positive words -> CONTINUE, more negative -> STOP.
    Deliberately ignores substance. Never outputs PIVOT (a sentiment reader can't)."""
    text = record["transcript"]
    pos, neg = len(_POS.findall(text)), len(_NEG.findall(text))
    if pos > neg:
        verdict, conf = "CONTINUE", min(0.5 + 0.1 * (pos - neg), 0.95)
    elif neg > pos:
        verdict, conf = "STOP", min(0.5 + 0.1 * (neg - pos), 0.95)
    else:
        verdict, conf = "STOP", 0.5
    return {"id": record["id"], "verdict": verdict, "confidence": round(conf, 2),
            "rationale": f"[mock sentiment baseline] positive={pos}, negative={neg}",
            "cited_quotes": [], "mode": "mock"}


# ------------------------------------------------------------------- api judge -----
def _parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    # find the outermost JSON object if the model added stray text
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def _api_verdict(record, client):
    msg = client.messages.create(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_TEMPLATE.format(**_judge_visible(record))}],
    )
    raw = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    try:
        data = _parse_json(raw)
    except Exception as e:  # malformed output is itself a reliability signal
        return {"id": record["id"], "verdict": None, "confidence": None,
                "rationale": f"[parse error: {e}]", "cited_quotes": [],
                "raw": raw[:500], "mode": "api"}
    v = data.get("verdict")
    if v not in LABELS:
        v = None
    conf = data.get("confidence")
    try:
        conf = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    return {"id": record["id"], "verdict": v, "confidence": conf,
            "rationale": data.get("rationale", ""),
            "cited_quotes": data.get("cited_quotes") or [], "mode": "api"}


def make_judge(mode):
    """Return a callable record -> result dict for the given mode."""
    if mode == "mock":
        return _mock_verdict
    if mode == "api":
        config.require_api_config()
        import anthropic
        client = anthropic.Anthropic(api_key=config.API_KEY)
        return lambda record: _api_verdict(record, client)
    raise ValueError(f"unknown mode: {mode!r}")
