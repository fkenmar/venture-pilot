"""Deterministic, no-network tests for the vp app.

There is no mock/offline mode in the app itself — so tests inject a FakeLLM (for
orchestration/grounding) or stub a transport (for the api/sdk/openai code paths).
The honesty-critical logic — real citation grounding, enforced caps, abstention —
is exercised directly.
"""
import json
import os

import pytest

from vp import config, orchestrator
from vp.agents import research as research_agent
from vp.agents import synthesize as synth_agent
from vp.guardrails import Budget, CapExceeded
from vp.llm import LLM
from vp.provenance import Finding, Source, ground_quotes
from vp.trace import Trace

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INTERVIEWS = os.path.join(REPO, "interviews", "*.md")

# eight short snippets that appear verbatim in interviews/*.md
REAL_QUOTES = [
    "we pay $40/mo for Fireflies", "I'd definitely use that", "dropped action items kill us",
    "we already pay for Otter", "I'd switch from our current mess in a heartbeat",
    "I'd pay real money to never drop an action item again",
    "What actually costs us is dropped follow-ups", "I don't have a budget for tools",
]


class FakeLLM:
    """Duck-types the LLM interface (complete_json / research) for flow tests."""
    def __init__(self, complete=None, findings=None):
        self._complete = complete or {}
        self._findings = findings or []
        self.budget = Budget()
        self.trace = Trace(None)

    def complete_json(self, system, user, *, model=None, max_tokens=None, label=""):
        self.budget.step(label)
        return dict(self._complete)

    def research(self, query, *, system, model=None, max_uses=4, label=""):
        self.budget.step(label)
        return list(self._findings)


# ---- provenance / cite-then-verify ----------------------------------------
def test_grounding_matches_verbatim_and_flags_fabricated():
    res = ground_quotes(["hello world", "never appears xyz"], ["please say hello world now"])
    assert res["grounded"] == 1 and res["total"] == 2
    assert res["offenders"] == ["never appears xyz"]


def test_grounding_normalizes_case_and_whitespace():
    assert ground_quotes(["Hello   World"], ["a hello world b"])["rate"] == 1.0


def test_grounding_empty_is_vacuously_true():
    assert ground_quotes([], ["x"]) == {"grounded": 0, "total": 0, "rate": 1.0, "offenders": []}


# ---- guardrails: hard caps are enforced, not advisory ---------------------
def test_step_cap_raises():
    b = Budget(max_steps=2)
    b.step(); b.step()
    with pytest.raises(CapExceeded):
        b.step()


def test_cost_cap_raises():
    b = Budget(max_dollars=0.0001)
    with pytest.raises(CapExceeded):
        b.add_usage(1_000_000, 1_000_000)


def test_token_cap_raises():
    b = Budget(max_tokens=10)
    with pytest.raises(CapExceeded):
        b.add_usage(100, 0)


# ---- backend selection: real LLM only, never offline ----------------------
def test_default_mode_precedence_and_never_offline(monkeypatch):
    monkeypatch.delenv("VP_BACKEND", raising=False)
    monkeypatch.setattr(config, "openai_available", lambda: False)
    monkeypatch.setattr(config, "has_api_config", lambda: False)
    monkeypatch.setattr(config, "sdk_available", lambda: False)
    assert config.default_mode() is None                       # nothing configured -> no offline fallback
    monkeypatch.setattr(config, "sdk_available", lambda: True)
    assert config.default_mode() == "sdk"
    monkeypatch.setattr(config, "has_api_config", lambda: True)
    assert config.default_mode() == "api"
    monkeypatch.setattr(config, "openai_available", lambda: True)
    assert config.default_mode() == "openai"                   # a user-chosen LLM wins
    monkeypatch.setenv("VP_BACKEND", "sdk")
    assert config.default_mode() == "sdk"                       # explicit pin always wins


# ---- synthesize: real verdict + real grounding over real files ------------
def test_synthesize_grounds_real_quotes_over_interviews():
    ts = orchestrator._read_transcripts([INTERVIEWS])
    assert len(ts) == 8
    fake = FakeLLM(complete={
        "verdict": "PIVOT", "confidence": 0.71, "summary": ["a", "b"],
        "evidence": [{"kind": "signal", "quote": "we pay $40/mo for Fireflies", "note": "x"}],
        "cited_quotes": REAL_QUOTES, "demand": "d", "recommendation": "r",
    })
    r = synth_agent.synthesize(fake, ts)
    assert r.verdict == "PIVOT" and r.confidence == pytest.approx(0.71)
    assert r.grounding["grounded"] == r.grounding["total"] == 8
    assert r.grounding["offenders"] == []


def test_synthesize_flags_a_fabricated_quote():
    fake = FakeLLM(complete={
        "verdict": "STOP", "confidence": 0.5, "summary": ["x"], "evidence": [],
        "cited_quotes": ["this quote is not in the transcript"], "demand": "", "recommendation": "",
    })
    r = synth_agent.synthesize(fake, [("t1", "completely unrelated text")])
    assert r.grounding["grounded"] == 0
    assert r.grounding["offenders"] == ["this quote is not in the transcript"]


# ---- research + orchestrator (single-writer writes the artifacts) ---------
def test_research_agent_preserves_supported_and_abstained():
    fake = FakeLLM(findings=[Finding("ICP", "c", [Source("X", "https://x.com")], True),
                             Finding("price", "no source", [], False)])
    fs = research_agent.research(fake, "idea")
    assert sum(f.supported for f in fs) == 1
    assert sum(not f.supported for f in fs) == 1


def test_validate_writes_three_artifacts_and_abstains(tmp_path):
    fake = FakeLLM(findings=[Finding("ICP", "c", [Source("X", "https://x.com")], True),
                             Finding("p", "x", [], False)])
    res = orchestrator.validate(fake, Trace(None), Budget(), "an idea",
                                out=str(tmp_path / "out"), auto_yes=True)
    assert res is not None
    for rel in ("interview-script.md", "outreach.md", "landing/index.html"):
        assert (tmp_path / "out" / rel).is_file()
    assert sum(1 for f in res["findings"] if not f.supported) == 1


# ---- transport code paths, each stubbed (no network, no key) --------------
class _Blk:
    def __init__(self, text):
        self.type, self.text = "text", text


class _Msg:
    def __init__(self, text, i=100, o=40):
        self.content = [_Blk(text)]
        self.usage = type("U", (), {"input_tokens": i, "output_tokens": o})()


class _FakeAnthropic:
    def __init__(self, reply):
        self.calls = []
        outer = self

        class _Messages:
            def create(self, **kw):
                outer.calls.append(kw)
                return reply
        self.messages = _Messages()


def test_api_path_parses_and_accounts(monkeypatch):
    llm = LLM("api", Budget(), Trace(None))
    llm._client = _FakeAnthropic(_Msg('{"verdict":"STOP","confidence":0.4}', i=120, o=30))
    out = llm.complete_json("s", "u")
    assert out == {"verdict": "STOP", "confidence": 0.4}
    assert llm.budget.in_tokens == 120 and llm.budget.out_tokens == 30


def test_api_research_uses_web_search_tool(monkeypatch):
    reply = _Msg('{"findings":[{"label":"L","claim":"c","source_url":"https://x.com","supported":true}],"abstained":[]}')
    llm = LLM("api", Budget(), Trace(None))
    llm._client = _FakeAnthropic(reply)
    findings = llm.research("q", system="s")
    assert findings and findings[0].sources[0].url == "https://x.com"
    assert llm._client.calls[0]["tools"][0]["type"].startswith("web_search")


def test_sdk_path_routes_and_accounts(monkeypatch):
    llm = LLM("sdk", Budget(), Trace(None))
    monkeypatch.setattr(llm, "_sdk_transport",
                        lambda system, user, model, tools: ('{"verdict":"CONTINUE","confidence":0.8}', 50, 20, 0.0))
    assert llm.complete_json("s", "u") == {"verdict": "CONTINUE", "confidence": 0.8}
    assert llm.budget.in_tokens == 50 and llm.budget.out_tokens == 20


def test_openai_path_routes_and_accounts(monkeypatch):
    llm = LLM("openai", Budget(), Trace(None))
    monkeypatch.setattr(llm, "_openai_chat",
                        lambda system, user, max_tokens: ('{"verdict":"STOP","confidence":0.3}', 40, 12))
    assert llm.complete_json("s", "u") == {"verdict": "STOP", "confidence": 0.3}
    assert llm.budget.in_tokens == 40 and llm.budget.out_tokens == 12


def test_openai_research_routes(monkeypatch):
    llm = LLM("openai", Budget(), Trace(None))
    reply = '{"findings":[{"label":"L","claim":"c","source_url":"https://x.com","supported":true}],"abstained":[]}'
    monkeypatch.setattr(llm, "_openai_chat", lambda system, q, max_tokens: (reply, 5, 5))
    findings = llm.research("q", system="s")
    assert findings and findings[0].supported


# ---- CLI: never offline, helpful when unconfigured ------------------------
def test_cli_doctor_runs(capsys):
    from vp.cli import main
    assert main(["doctor"]) == 0
    assert "setup check" in capsys.readouterr().out


def test_cli_errors_when_no_backend(monkeypatch):
    from vp.cli import main
    monkeypatch.setattr("vp.cli.config.default_mode", lambda: None)
    with pytest.raises(SystemExit):
        main(["synthesize", INTERVIEWS, "--no-pace"])


def test_cli_trace_reads_a_run(tmp_path, capsys):
    from vp.cli import trace_cmd
    recs = [
        {"seq": 1, "kind": "start", "cmd": "synthesize", "mode": "sdk"},
        {"seq": 2, "kind": "step", "label": "synthesize-verdict", "mode": "sdk"},
        {"seq": 3, "kind": "usage", "model": "sonnet", "in_tokens": 3, "out_tokens": 600},
        {"seq": 4, "kind": "done", "phase": "synthesize", "verdict": "PIVOT",
         "grounded": 5, "total": 5, "tokens": 603, "dollars": 0.012, "elapsed_s": 50.2},
    ]
    (tmp_path / "trace.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
    assert trace_cmd(str(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "run trace" in out and "PIVOT" in out and "grounded" in out
