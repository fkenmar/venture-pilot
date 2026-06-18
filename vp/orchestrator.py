"""The single-writer orchestrator: sequences steps, owns ALL writes, runs the
plan -> preview -> approve -> execute loop and the human-gate pause.

Agents return data; only this module writes files and renders the verdict.
"""
from __future__ import annotations

import glob
import os
import sys

from . import ui
from .agents import artifacts as artifacts_agent
from .agents import research as research_agent
from .agents import synthesize as synth_agent

PLAN_STEPS = [
    (1, "find target customers + communities", "auto", ui.TEAL),
    (2, "draft outreach + interview script", "you send", ui.AMBER),
    (3, "build a landing-page test artifact", "you publish", ui.AMBER),
    (4, "synthesize your interviews -> verdict", "after calls", ui.AMBER),
]


def _approve(auto_yes: bool) -> bool:
    if auto_yes or not sys.stdin.isatty():
        ui.approve_prompt("y")
        return True
    try:
        ans = input(ui.approve_query())
    except EOFError:
        ans = "y"
    return not (ans or "y").strip().lower().startswith("n")


def _read_transcripts(paths):
    """paths may include unexpanded globs. Returns [(id, text), ...] sorted."""
    files = []
    for p in paths:
        files.extend(glob.glob(p) if any(ch in p for ch in "*?[") else [p])
    out = []
    for fp in sorted(files):
        if os.path.isfile(fp):
            with open(fp) as f:
                out.append((os.path.splitext(os.path.basename(fp))[0], f.read()))
    return out


def validate(llm, trace, budget, idea, *, out="out", auto_yes=False):
    """vp validate: plan -> approve -> cited research -> drafted artifacts -> pause."""
    ui.header()
    ui.idea(idea)

    ui.section("PLAN", "the agent preps — you approve anything irreversible")
    ui.plan(PLAN_STEPS)
    if not _approve(auto_yes):
        ui.out("")
        ui.out(f"  {ui.c('plan declined — nothing was run.', ui.MUTED)}")
        trace.event("declined", phase="validate")
        return None

    ui.section("RESEARCH", "finding who actually has this pain")
    findings = research_agent.research(llm, idea)
    abstained = 0
    for f in findings:
        if f.supported:
            ui.finding(f.label, f.source_label)
        else:
            abstained += 1
    if abstained:
        noun = "claim" if abstained == 1 else "claims"
        ui.abstain(f"{abstained} {noun} had no source")

    ui.section("ARTIFACTS", "drafted — nothing sent")
    drafts = artifacts_agent.draft(llm, idea, findings)
    for a in drafts:
        path = os.path.join(out, a.relpath)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as fh:
            fh.write(a.content)
        trace.event("write", path=path, bytes=len(a.content))
        ui.artifact(a.name, f"{out}/{a.relpath}", a.tag)

    ui.pause("vp synthesize ./interviews/*.md")
    trace.event("done", phase="validate", findings=len(findings), abstained=abstained,
                artifacts=len(drafts), **budget.summary())
    return {"findings": findings, "artifacts": drafts}


def synthesize(llm, trace, budget, paths, *, idea=""):
    """vp synthesize: read the founder's interviews -> ONE honest verdict."""
    transcripts = _read_transcripts(paths)
    if not transcripts:
        raise SystemExit("no transcript files found. usage: vp synthesize ./interviews/*.md")

    result = synth_agent.synthesize(llm, transcripts, idea)
    g = result.grounding
    ui.synth_counts(result.n_transcripts, g["grounded"], g["total"])
    ui.verdict(result.verdict, result.confidence, result.summary, result.evidence,
               result.demand, result.recommendation)
    if g["offenders"]:
        ui.out(f"   {ui.c('⚠ ' + str(len(g['offenders'])) + ' ungrounded quote(s) flagged — verdict held', ui.RED)}")
    trace.event("done", phase="synthesize", verdict=result.verdict,
                confidence=result.confidence, grounded=g["grounded"], total=g["total"],
                **budget.summary())
    return result
