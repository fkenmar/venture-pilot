"""vp CLI — `vp validate "<idea>"` and `vp synthesize <files>`.

Mode defaults to live (--api) when VP_MODEL + ANTHROPIC_API_KEY are configured,
else the deterministic mock path. Either way the orchestration is identical.
"""
from __future__ import annotations

import argparse

from . import config, ui
from .guardrails import Budget, CapExceeded
from .llm import LLM
from .trace import Trace
from . import orchestrator


def _add_common(sp):
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--api", action="store_const", dest="mode", const="api",
                   help="use the live Anthropic model + web search (needs eval/.env)")
    g.add_argument("--mock", action="store_const", dest="mode", const="mock",
                   help="deterministic offline path (no API key)")
    sp.add_argument("-y", "--yes", action="store_true", help="auto-approve the plan")
    sp.add_argument("--no-pace", action="store_true", help="disable pacing (deterministic output)")
    sp.add_argument("--out", default="out", help="output dir for artifacts + trace (default: out)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vp", description="human-in-the-loop customer discovery")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="prep cited research + draft artifacts for an idea")
    pv.add_argument("idea", help="the idea, in quotes")
    _add_common(pv)

    ps = sub.add_parser("synthesize", help="separate genuine signal from politeness across interviews")
    ps.add_argument("paths", nargs="+", help="interview transcript files (globs ok)")
    ps.add_argument("--idea", default="", help="the idea that was pitched (optional)")
    _add_common(ps)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    mode = args.mode or config.default_mode()
    if mode == "api":
        config.require_api_config()
    ui.set_pace(not args.no_pace)

    budget = Budget()
    trace = Trace(f"{args.out}/trace.jsonl")
    trace.event("start", cmd=args.cmd, mode=mode)
    llm = LLM(mode, budget, trace)

    try:
        if args.cmd == "validate":
            orchestrator.validate(llm, trace, budget, args.idea, out=args.out, auto_yes=args.yes)
        else:
            orchestrator.synthesize(llm, trace, budget, args.paths, idea=args.idea)
    except CapExceeded as e:
        ui.out("")
        ui.out(f"  {ui.badge('KILL-SWITCH', ui.RED)}  {ui.c(str(e), ui.RED)}")
        ui.out(f"  {ui.c('run halted at a hard cap — partial trace: ' + (trace.path or ''), ui.MUTED)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
