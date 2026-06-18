"""Read-only research subagent: find the target customers + the communities where
they gather + the tools they already pay for — each with a real source URL.

Cite-then-verify: a claim with no source is returned as ABSTAINED, never asserted.
On the Anthropic backends this is backed by live web search; on an OpenAI-compatible
backend it draws on the model's knowledge, so it must cite real URLs or abstain.
"""
from __future__ import annotations

SYSTEM_PROMPT = """\
You are a venture-pilot research subagent. You are READ-ONLY. For the founder's idea, \
find: (1) the exact target customer / ICP, (2) 2-3 specific communities where those \
people gather, and (3) the tools they already pay for. Use web search if it is available. \
Cite a REAL source URL for every claim. If you cannot find a credible source for a claim, \
do NOT assert it — put it under "abstained" instead. Fabricated or guessed sources are \
worse than none.

Return STRICT JSON only:
{"findings":[{"label":"<short display label>","claim":"<full claim>",
              "source_url":"<url>","source_title":"<title>","supported":true}],
 "abstained":[{"label":"<short>","claim":"<what could not be sourced>"}]}
Aim for 4-6 high-signal findings."""


def research(llm, idea: str):
    """Return cited findings (supported) + abstentions (unsupported)."""
    query = (f'Idea: "{idea}". Find the exact target customer/ICP, 2-3 specific communities '
             f'where they gather, and the tools they already pay for. Cite real source URLs.')
    return llm.research(query, system=SYSTEM_PROMPT, label="research-customers")
