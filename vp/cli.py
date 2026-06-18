"""vp CLI — `vp validate "<idea>"`, `vp synthesize <files>`, `vp doctor`.

Backend auto-selects the most capable thing that's configured:
  1. `--api`  : your Anthropic API key (what downloaded users bring) — VP_MODEL + ANTHROPIC_API_KEY
  2. `--sdk`  : a logged-in Claude Pro/Max subscription via the Claude Agent SDK (no API key)
  3. `--mock` : fully offline, deterministic, no AI calls
Run `vp doctor` to see what's available and how to turn each on.
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
                   help="use your Anthropic API key (VP_MODEL + ANTHROPIC_API_KEY)")
    g.add_argument("--sdk", action="store_const", dest="mode", const="sdk",
                   help="use a logged-in Claude Pro/Max subscription (no API key)")
    g.add_argument("--mock", action="store_const", dest="mode", const="mock",
                   help="offline, deterministic, no AI calls")
    sp.add_argument("-y", "--yes", action="store_true", help="auto-approve the plan")
    sp.add_argument("--no-pace", action="store_true", help="disable pacing (deterministic output)")
    sp.add_argument("--out", default="out", help="output dir for artifacts + trace (default: out)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vp",
        description="venture-pilot — a human-in-the-loop customer-discovery co-pilot.",
        epilog="run `vp doctor` to check your setup. backend: --api (your key) | --sdk (Claude subscription) | --mock (offline).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="prep cited research + draft artifacts for an idea")
    pv.add_argument("idea", help="the idea, in quotes")
    _add_common(pv)

    ps = sub.add_parser("synthesize", help="turn your interviews into one honest verdict")
    ps.add_argument("paths", nargs="+", help="interview transcript files (globs ok)")
    ps.add_argument("--idea", default="", help="the idea that was pitched (optional)")
    _add_common(ps)

    sub.add_parser("doctor", help="check what's installed and which backends are available")
    return p


def doctor() -> int:
    ui.out("")
    ui.out(f"  {ui.c('venture-pilot', ui.TEAL, True)}  {ui.c('· setup check', ui.MUTED)}")
    ui.out(f"  {ui.RULE}")
    has_key = config.has_api_config()
    sdk_ok = config.sdk_available()

    def row(ok, name, detail):
        mark = ui.OK if ok else ui.c("·", ui.DIM)
        ui.out(f"    {mark}  " + ui.c(name.ljust(26), ui.WHITE if ok else ui.MUTED) + ui.c(detail, ui.DIM))

    row(has_key, "API key + model", "VP_MODEL + ANTHROPIC_API_KEY in eval/.env" if not has_key
        else f"model set, key set")
    row(sdk_ok, "Claude subscription (SDK)", "claude CLI + claude-agent-sdk found" if sdk_ok
        else "install: pip install claude-agent-sdk; log in with `claude`")
    row(True, "offline mock", "always available — no setup")

    chosen = config.default_mode()
    ui.out("")
    ui.out(f"  {ui.c('default backend:', ui.MUTED)} {ui.c(chosen, ui.TEAL, True)} "
           f"{ui.c('(' + ui._MODE_LABEL.get(chosen, ('', ''))[0] + ')', ui.DIM)}")
    ui.out("")
    ui.out(f"  {ui.c('how to enable each:', ui.MUTED)}")
    ui.out(f"    {ui.c('--api', ui.TEAL)}   {ui.c('cp eval/.env.example eval/.env  → add VP_MODEL + ANTHROPIC_API_KEY', ui.DIM)}")
    ui.out(f"    {ui.c('--sdk', ui.INDIGO)}   {ui.c('pip install claude-agent-sdk  → log in once with `claude`', ui.DIM)}")
    ui.out(f"    {ui.c('--mock', ui.AMBER)}  {ui.c('nothing — runs the demo offline', ui.DIM)}")
    ui.out("")
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "doctor":
        return doctor()

    mode = args.mode or config.default_mode()
    if mode == "api":
        config.require_api_config()
    if mode == "sdk" and not config.sdk_available():
        raise SystemExit("--sdk needs `pip install claude-agent-sdk` and a logged-in `claude` CLI. "
                         "Run `vp doctor` for setup, or use --api / --mock.")
    ui.set_pace(not args.no_pace)

    budget = Budget()
    trace = Trace(f"{args.out}/trace.jsonl")
    trace.event("start", cmd=args.cmd, mode=mode)
    llm = LLM(mode, budget, trace)
    ui.mode_banner(mode)

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
