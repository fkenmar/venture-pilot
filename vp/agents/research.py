"""Read-only research subagent: find the target customers + the communities where
they gather + the tools they already pay for — each with a real source URL.

Cite-then-verify: a claim with no source is returned as ABSTAINED, never asserted.
"""
from __future__ import annotations

from ..provenance import Finding, Source

SYSTEM_PROMPT = """\
You are a venture-pilot research subagent. You are READ-ONLY. For the founder's idea, \
use web_search to find: (1) the exact target customer / ICP, (2) 2-3 specific communities \
where those people gather, and (3) the tools they already pay for. Cite a REAL source URL \
for every claim. If you cannot find a credible source for a claim, do NOT assert it — put \
it under "abstained" instead. Fabricated or guessed sources are worse than none.

Return STRICT JSON only:
{"findings":[{"label":"<short display label>","claim":"<full claim>",
              "source_url":"<url>","source_title":"<title>","supported":true}],
 "abstained":[{"label":"<short>","claim":"<what could not be sourced>"}]}
Aim for 4-6 high-signal findings."""


def mock_findings(idea: str) -> list[Finding]:
    """Deterministic demo research for the Slack-thread-summarizer idea."""
    return [
        Finding("ICP  eng managers · 50-200-person SaaS",
                "Primary buyers are engineering managers at 50-200-person SaaS companies.",
                [Source("First Round Review", "https://review.firstround.com")], True),
        Finding("community  r/engineeringmanagement · 218k",
                "Active community of engineering managers discussing tooling and process.",
                [Source("r/engineeringmanagement", "https://www.reddit.com/r/engineeringmanagement/")], True),
        Finding("community  Rands Leadership Slack",
                "Large invite-based Slack community of engineering leaders.",
                [Source("Rands in Repose", "https://randsinrepose.com/welcome-to-rands-leadership-slack/")], True),
        Finding("already pay for  Fireflies · Otter · Notion",
                "Target users already pay for meeting/notes AI tools.",
                [Source("Fireflies", "https://fireflies.ai"),
                 Source("Otter", "https://otter.ai"),
                 Source("Notion AI", "https://www.notion.so/product/ai")], True),
        # abstained — no credible single source for an average willingness-to-pay number
        Finding("avg willingness-to-pay for this category",
                "No credible single source for an average price point; would be a guess.",
                [], False),
    ]


def research(llm, idea: str) -> list[Finding]:
    """Return cited findings (supported) + abstentions (unsupported)."""
    query = (f'Idea: "{idea}". Find the exact target customer/ICP, 2-3 specific communities '
             f'where they gather, and the tools they already pay for. Cite real source URLs.')
    return llm.research(query, system=SYSTEM_PROMPT, mock_findings=mock_findings(idea),
                        label="research-customers")
