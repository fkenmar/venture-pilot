"""vp CLI — `vp validate "<idea>"`, `vp synthesize <files>`, `vp doctor`, `vp trace`.

This app ALWAYS uses a real LLM — there is no offline/mock mode. Pick any backend:
  --api    : your Anthropic API key (what downloaded users bring) — VP_MODEL + ANTHROPIC_API_KEY
  --sdk    : a logged-in Claude Pro/Max subscription via the Claude Agent SDK (no API key)
  --openai : ANY OpenAI-compatible model — OpenAI, OpenRouter (→ Claude/GPT/Gemini/Llama),
             Groq, Together, or a LOCAL model (Ollama / LM Studio) — VP_OPENAI_* env
Run `vp doctor` to see what's available and how to turn each on.
"""
from __future__ import annotations

import argparse
import json
import os

from . import __version__, config, ui
from .guardrails import Budget, CapExceeded
from .llm import LLM
from .trace import Trace
from . import orchestrator


def _add_common(sp):
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--api", action="store_const", dest="mode", const="api",
                   help="your Anthropic API key (VP_MODEL + ANTHROPIC_API_KEY)")
    g.add_argument("--sdk", action="store_const", dest="mode", const="sdk",
                   help="a logged-in Claude Pro/Max subscription (no API key)")
    g.add_argument("--openai", action="store_const", dest="mode", const="openai",
                   help="any OpenAI-compatible LLM (OpenAI / OpenRouter / local …) via VP_OPENAI_*")
    sp.add_argument("-y", "--yes", action="store_true", help="auto-approve the plan")
    sp.add_argument("--no-pace", action="store_true", help="disable pacing (deterministic output)")
    sp.add_argument("--out", default="out", help="output dir for artifacts + trace (default: out)")


SETUP_HELP = (
    "No LLM configured. This app always uses a real model — pick one:\n"
    "  • Claude subscription : run `claude` to log in (no API key)        -> then `--sdk`\n"
    "  • Anthropic API key   : cp .env.example .env  (VP_MODEL + ANTHROPIC_API_KEY)  -> `--api`\n"
    "  • Any other LLM       : set VP_OPENAI_MODEL (+ VP_OPENAI_BASE_URL / OPENAI_API_KEY)  -> `--openai`\n"
    "See `vp doctor`."
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vp",
        description="venture-pilot — a human-in-the-loop customer-discovery co-pilot (always real AI).",
        epilog="run `vp doctor` for setup. backends: --api (your key) | --sdk (Claude subscription) | --openai (any LLM).",
    )
    p.add_argument("--version", action="version", version=f"vp {__version__}")
    sub = p.add_subparsers(dest="cmd")

    pv = sub.add_parser("validate", help="prep cited research + draft artifacts for an idea")
    pv.add_argument("idea", help="the idea, in quotes")
    _add_common(pv)

    ps = sub.add_parser("synthesize", help="turn your interviews into one honest verdict")
    ps.add_argument("paths", nargs="+", help="interview transcript files (globs ok)")
    ps.add_argument("--idea", default="", help="the idea that was pitched (optional)")
    _add_common(ps)

    sub.add_parser("doctor", help="check which LLM backends are available + how to enable them")

    pt = sub.add_parser("trace", help="pretty-print the last run (steps, sources, usage, verdict)")
    pt.add_argument("--out", default="out", help="run dir to read trace from (default: out)")
    return p


def doctor() -> int:
    ui.out("")
    ui.out(f"  {ui.c('venture-pilot', ui.TEAL, True)}  {ui.c('· setup check (this app always uses a real LLM)', ui.MUTED)}")
    ui.out(f"  {ui.RULE}")
    has_key, sdk_ok, oai_ok = config.has_api_config(), config.sdk_available(), config.openai_available()

    def row(ok, name, detail):
        mark = ui.OK if ok else ui.c("·", ui.DIM)
        ui.out(f"    {mark}  " + ui.c(name.ljust(28), ui.WHITE if ok else ui.MUTED) + ui.c(detail, ui.DIM))

    row(has_key, "--api  Anthropic key", "set" if has_key else "cp .env.example .env → VP_MODEL + ANTHROPIC_API_KEY")
    row(sdk_ok, "--sdk  Claude subscription", "ready (claude CLI + agent SDK)" if sdk_ok
        else "run `claude` to log in (claude-agent-sdk ships with the app)")
    row(oai_ok, "--openai  any LLM", f"{config.OPENAI_MODEL} @ {config.OPENAI_BASE_URL}" if oai_ok
        else "set VP_OPENAI_MODEL (+ VP_OPENAI_BASE_URL / OPENAI_API_KEY)")

    chosen = config.default_mode()
    ui.out("")
    if chosen:
        label = ui._MODE_LABEL.get(chosen, ("", ""))[0]
        ui.out(f"  {ui.c('default backend:', ui.MUTED)} {ui.c(chosen, ui.TEAL, True)} {ui.c('(' + label + ')', ui.DIM)}")
    else:
        ui.out(f"  {ui.c('default backend:', ui.MUTED)} {ui.c('none yet', ui.AMBER, True)}")
        ui.out(f"  {ui.c('→ run `claude` to log in (free with Claude Pro/Max), or add a key. nothing runs offline.', ui.MUTED)}")
    ui.out("")
    return 0


def trace_cmd(out_dir: str) -> int:
    path = os.path.join(out_dir, "trace.jsonl")
    if not os.path.exists(path):
        raise SystemExit(f"no trace at {path} — run `vp validate` or `vp synthesize` first.")
    recs = [json.loads(line) for line in open(path) if line.strip()]
    steps = [r for r in recs if r["kind"] == "step"]
    sources = [r for r in recs if r["kind"] == "source"]
    writes = [r for r in recs if r["kind"] == "write"]
    usage = [r for r in recs if r["kind"] == "usage"]
    done = next((r for r in recs if r["kind"] == "done"), {})

    ui.out("")
    ui.out(f"  {ui.c('venture-pilot', ui.TEAL, True)}  {ui.c('· run trace', ui.MUTED)}  {ui.c(path, ui.DIM)}")
    ui.out(f"  {ui.RULE}")
    ui.out(f"  {ui.BAR} {ui.c('steps', ui.TEAL, True)}")
    for i, s in enumerate(steps, 1):
        ui.out(f"    {ui.c(str(i), ui.DIM)}  " + ui.c(s.get("label", "").ljust(24), ui.WHITE)
               + ui.c(s.get("mode", ""), ui.DIM))
    if sources:
        ui.out(f"  {ui.BAR} {ui.c('sources', ui.TEAL, True)}")
        for s in sources:
            ui.out("    " + ui.c("└─", ui.DIM) + " " + ui.c(s.get("url", ""), ui.INDIGO))
    if writes:
        ui.out(f"  {ui.BAR} {ui.c('writes', ui.TEAL, True)}")
        for w in writes:
            ui.out(f"    {ui.OK} " + ui.c(w.get("path", ""), ui.INDIGO))
    tok = done.get("tokens", sum(u.get("in_tokens", 0) + u.get("out_tokens", 0) for u in usage))
    ui.out(f"  {ui.BAR} {ui.c('usage', ui.TEAL, True)}")
    line = f"    {ui.c(f'{tok:,} tokens', ui.WHITE)}"
    if done.get("dollars") is not None:
        line += ui.c(f"  ·  ${done['dollars']:.4f}", ui.DIM)
    line += ui.c(f"  ·  {len(steps)} step(s)", ui.DIM)
    if done.get("elapsed_s") is not None:
        line += ui.c(f"  ·  {done['elapsed_s']}s", ui.DIM)
    ui.out(line)
    if done.get("verdict"):
        col = ui.VERDICT_COLOR.get(done["verdict"], ui.AMBER)
        ui.out(f"    {ui.c('verdict', ui.MUTED)} {ui.c(done['verdict'], col, True)}  "
               + ui.c(f"{done.get('grounded')}/{done.get('total')} grounded", ui.DIM))
    ui.out("")
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    if args.cmd == "doctor":
        return doctor()
    if args.cmd == "trace":
        return trace_cmd(args.out)

    mode = args.mode or config.default_mode()
    if mode is None:
        raise SystemExit(SETUP_HELP)
    if mode == "api":
        config.require_api_config()
    if mode == "sdk" and not config.sdk_available():
        raise SystemExit("--sdk needs a logged-in `claude` CLI. Run `claude` to log in, or `vp doctor`.")
    if mode == "openai":
        config.require_openai_config()
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
