"""LLM client — real backends only. No mock, nothing offline.

Three transports, one interface (complete_json / research):
  - "api"    : Anthropic Messages API + server-side web_search (your own key)
  - "sdk"    : Claude Agent SDK on a logged-in Claude Pro/Max subscription (no key)
  - "openai" : ANY OpenAI-compatible /v1/chat/completions server — OpenAI, OpenRouter
               (→ Claude/GPT/Gemini/Llama/...), Groq, Together, or a LOCAL model
               (Ollama / LM Studio / vLLM). Bring whatever LLM you want.

Token usage is recorded to the budget + trace on every call.
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

    # -- transports -------------------------------------------------------
    def _anthropic(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=config.API_KEY)
        return self._client

    def _sdk_transport(self, system: str, user: str, model: str, tools):
        """Claude Agent SDK — runs on the logged-in Claude subscription (no API key)."""
        import asyncio
        try:
            from claude_agent_sdk import (query, ClaudeAgentOptions,
                                          AssistantMessage, TextBlock, ResultMessage)
        except ImportError as e:
            raise SystemExit("--sdk needs the Claude Agent SDK: `pip install claude-agent-sdk` "
                             "plus a logged-in `claude` CLI (Claude Pro/Max).") from e

        async def go():
            opts = ClaudeAgentOptions(system_prompt=system, model=model,
                                      allowed_tools=list(tools or []))
            parts, result_text, usage, cost = [], None, None, None
            async for msg in query(prompt=user, options=opts):
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock):
                            parts.append(b.text)
                elif isinstance(msg, ResultMessage):
                    usage = msg.usage or {}
                    cost = msg.total_cost_usd
                    if msg.result:
                        result_text = msg.result
            return (result_text or "".join(parts)), (usage or {}), cost

        text, usage, cost = asyncio.run(go())
        return text, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)), cost

    def _sdk_account(self, in_tok: int, out_tok: int, cost) -> None:
        self.budget.add_usage(in_tok, out_tok)
        self.trace.usage(config.SDK_MODEL, in_tok, out_tok)
        if cost is not None:
            self.trace.event("cost", usd=cost)

    def _openai_chat(self, system: str, user: str, max_tokens: int):
        """One call to any OpenAI-compatible /v1/chat/completions endpoint (stdlib only)."""
        import urllib.error
        import urllib.request
        body = {
            "model": config.OPENAI_MODEL,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json"}
        if config.OPENAI_KEY:
            headers["Authorization"] = f"Bearer {config.OPENAI_KEY}"
        req = urllib.request.Request(config.OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
                                     data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"OpenAI-compatible request failed ({e.code}) at "
                             f"{config.OPENAI_BASE_URL}: {e.read().decode()[:200]}") from e
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        return text, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))

    # -- structured completion -------------------------------------------
    def complete_json(self, system: str, user: str, *, model: str | None = None,
                      max_tokens: int | None = None, label: str = "complete") -> dict:
        self.budget.step(label)
        self.trace.step(label, mode=self.mode)
        if self.mode == "sdk":
            text, in_tok, out_tok, cost = self._sdk_transport(system, user, config.SDK_MODEL, None)
            self._sdk_account(in_tok, out_tok, cost)
            return parse_json(text)
        if self.mode == "openai":
            text, in_tok, out_tok = self._openai_chat(system, user, max_tokens or config.MAX_TOKENS)
            self.budget.add_usage(in_tok, out_tok)
            self.trace.usage(config.OPENAI_MODEL, in_tok, out_tok)
            return parse_json(text)
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

    # -- cited research --------------------------------------------------
    def research(self, query: str, *, system: str, model: str | None = None,
                 max_uses: int = 4, label: str = "research") -> list[Finding]:
        self.budget.step(label)
        self.trace.step(label, query=query, mode=self.mode)
        if self.mode == "sdk":
            text, in_tok, out_tok, cost = self._sdk_transport(system, query, config.SDK_MODEL, ["WebSearch"])
            self._sdk_account(in_tok, out_tok, cost)
            return self._record(self._parse_findings(text))
        if self.mode == "openai":
            # OpenAI-compatible endpoints have no uniform server-side web search,
            # so research draws on the model's knowledge; it must cite real URLs or abstain.
            text, in_tok, out_tok = self._openai_chat(system, query, config.MAX_TOKENS)
            self.budget.add_usage(in_tok, out_tok)
            self.trace.usage(config.OPENAI_MODEL, in_tok, out_tok)
            return self._record(self._parse_findings(text))
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
        return self._record(self._parse_findings(text))

    def _record(self, findings: list[Finding]) -> list[Finding]:
        for f in findings:
            for s in f.sources:
                self.trace.source(s.url, s.title)
        return findings

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
