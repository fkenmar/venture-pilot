"""Anthropic client wrapper with a mock backend.

In `api` mode this makes real Messages API calls (including the server-side
web_search tool for cited research) and records token usage to the budget + trace.
In `mock` mode it returns caller-supplied canned data but STILL exercises the
budget (synthetic usage) and trace, so the orchestration is identical in both modes.
"""
from __future__ import annotations

import json
import re

from . import config
from .guardrails import Budget
from .trace import Trace
from .provenance import Finding, Source


def parse_json(text: str) -> dict:
    """Tolerant JSON extraction from a model response (handles fences / stray prose)."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


class LLM:
    def __init__(self, mode: str, budget: Budget, trace: Trace):
        self.mode = mode
        self.budget = budget
        self.trace = trace
        self._client = None

    # -- internal ---------------------------------------------------------
    def _anthropic(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=config.API_KEY)
        return self._client

    def _mock_usage(self, system: str, user: str, label: str) -> None:
        est_in = (len(system) + len(user)) // 4
        est_out = 220
        self.budget.add_usage(est_in, est_out)
        self.trace.usage("mock", est_in, est_out)

    # -- structured completion -------------------------------------------
    def complete_json(self, system: str, user: str, *, model: str | None = None,
                      max_tokens: int | None = None, mock_result=None, label: str = "complete") -> dict:
        self.budget.step(label)
        self.trace.step(label, mode=self.mode)
        if self.mode == "mock":
            self._mock_usage(system, user, label)
            return dict(mock_result or {})
        msg = self._anthropic().messages.create(
            model=model or config.MODEL,
            max_tokens=max_tokens or config.MAX_TOKENS,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", None) == "text")
        self.budget.add_usage(msg.usage.input_tokens, msg.usage.output_tokens)
        self.trace.usage(model or config.MODEL, msg.usage.input_tokens, msg.usage.output_tokens)
        return parse_json(text)

    # -- cited research (web_search) -------------------------------------
    def research(self, query: str, *, system: str, model: str | None = None,
                 max_uses: int = 4, mock_findings=None, label: str = "research") -> list[Finding]:
        self.budget.step(label)
        self.trace.step(label, query=query, mode=self.mode)
        if self.mode == "mock":
            self._mock_usage(system, query, label)
            findings = mock_findings or []
            for f in findings:
                for s in f.sources:
                    self.trace.source(s.url, s.title)
            return findings
        client = self._anthropic()
        msg = client.messages.create(
            model=model or config.FAST_MODEL,
            max_tokens=config.MAX_TOKENS,
            temperature=0,
            system=system,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}],
            messages=[{"role": "user", "content": query}],
        )
        self.budget.add_usage(msg.usage.input_tokens, msg.usage.output_tokens)
        self.trace.usage(model or config.FAST_MODEL, msg.usage.input_tokens, msg.usage.output_tokens)
        text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", None) == "text")
        return self._parse_findings(text)

    def _parse_findings(self, text: str) -> list[Finding]:
        try:
            data = parse_json(text)
        except Exception:
            return []
        findings = []
        for item in data.get("findings", []):
            sources = []
            url = item.get("source_url")
            if url:
                sources.append(Source(item.get("source_title", url), url))
            for s in item.get("sources", []) or []:
                sources.append(Source(s.get("title", s.get("url", "")), s.get("url", "")))
            supported = bool(sources) and item.get("supported", True)
            findings.append(Finding(
                label=item.get("label", item.get("claim", ""))[:60],
                claim=item.get("claim", ""),
                sources=sources,
                supported=supported,
            ))
        for item in data.get("abstained", []) or []:
            findings.append(Finding(label=item.get("label", str(item))[:60],
                                    claim=item.get("claim", str(item)), sources=[], supported=False))
        return findings
