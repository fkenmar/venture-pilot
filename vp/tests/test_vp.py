"""Deterministic, no-network tests for the vp app (mock mode only).

These cover the parts that make the product *honest*: real citation grounding,
the enforced caps/kill-switch, abstention, and that the orchestrator writes the
artifacts and reproduces the demo flow.
"""
import os

import pytest

from vp import config, orchestrator
from vp.agents import research as research_agent
from vp.agents import synthesize as synth_agent
from vp.guardrails import Budget, CapExceeded
from vp.llm import LLM
from vp.provenance import ground_quotes
from vp.trace import Trace

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INTERVIEWS = os.path.join(REPO, "interviews", "*.md")


def mkllm():
    return LLM("mock", Budget(), Trace(None))


# ---- provenance / cite-then-verify ----------------------------------------
def test_grounding_matches_verbatim_and_flags_fabricated():
    res = ground_quotes(["hello world", "never appears xyz"], ["please say hello world now"])
    assert res["grounded"] == 1 and res["total"] == 2
    assert res["offenders"] == ["never appears xyz"]


def test_grounding_normalizes_case_and_whitespace():
    assert ground_quotes(["Hello   World"], ["a hello world b"])["rate"] == 1.0


def test_grounding_empty_is_vacuously_true():
    assert ground_quotes([], ["anything"]) == {"grounded": 0, "total": 0, "rate": 1.0, "offenders": []}


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


# ---- research: cited + abstention -----------------------------------------
def test_research_returns_cited_findings_and_one_abstention():
    findings = research_agent.research(mkllm(), "any idea")
    supported = [f for f in findings if f.supported]
    abstained = [f for f in findings if not f.supported]
    assert len(supported) >= 4
    assert len(abstained) == 1
    assert all(f.sources for f in supported)          # every asserted claim has a source
    assert all(not f.sources for f in abstained)      # abstentions carry no source


# ---- synthesize: real verdict + real grounding over real files ------------
def test_synthesize_over_real_interviews_is_pivot_and_fully_grounded():
    ts = orchestrator._read_transcripts([INTERVIEWS])
    assert len(ts) == 8
    r = synth_agent.synthesize(mkllm(), ts)
    assert r.verdict == "PIVOT"
    assert r.confidence == pytest.approx(0.71)
    assert r.grounding["grounded"] == r.grounding["total"] == 8
    assert r.grounding["offenders"] == []


def test_synthesize_flags_a_fabricated_quote(monkeypatch):
    monkeypatch.setattr(synth_agent, "mock_result", lambda: {
        "verdict": "STOP", "confidence": 0.5, "summary": ["x"], "evidence": [],
        "cited_quotes": ["this quote is not in the transcript"], "demand": "", "recommendation": "",
    })
    r = synth_agent.synthesize(mkllm(), [("t1", "completely unrelated text")])
    assert r.grounding["grounded"] == 0
    assert r.grounding["offenders"] == ["this quote is not in the transcript"]


# ---- orchestrator: single-writer actually writes the artifacts ------------
def test_validate_writes_three_artifacts_and_abstains(tmp_path):
    out = str(tmp_path / "out")
    res = orchestrator.validate(mkllm(), Trace(None), Budget(), "an idea", out=out, auto_yes=True)
    assert res is not None
    for rel in ("interview-script.md", "outreach.md", "landing/index.html"):
        assert (tmp_path / "out" / rel).is_file()
    assert sum(1 for f in res["findings"] if not f.supported) == 1


# ---- CLI smoke ------------------------------------------------------------
def test_default_mode_is_mock_without_key():
    # no key configured in the test env -> deterministic offline path
    if not config.has_api_config():
        assert config.default_mode() == "mock"


def test_cli_synthesize_prints_verdict(tmp_path, capsys):
    from vp.cli import main
    rc = main(["synthesize", INTERVIEWS, "--mock", "--no-pace", "--out", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PIVOT" in out and "8/8 grounded" in out


def test_cli_validate_runs_and_writes(tmp_path, capsys):
    from vp.cli import main
    rc = main(["validate", "Slack bot that summarizes long threads", "--mock",
               "--no-pace", "--yes", "--out", str(tmp_path / "out")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PLAN" in out and "RESEARCH" in out and "YOUR MOVE" in out
    assert (tmp_path / "out" / "landing" / "index.html").is_file()
