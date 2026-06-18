"""Brand terminal UI for vp — the venture-pilot palette + section renderers.

These renderers take real data and print the same layout as docs/assets/demo.gif,
so the live app's output is identical to the concept demo. Pacing is centralised
here and can be disabled (tests / --no-pace) so output is deterministic.
"""
from __future__ import annotations

import sys
import time

# ---- palette (truecolor ANSI) ---------------------------------------------
TEAL, AMBER, RED = "32;227;162", "245;165;36", "242;84;91"
INDIGO, WHITE, MUTED, DIM = "91;141;239", "230;237;243", "123;138;165", "78;90;108"
INK = "10;14;20"

VERDICT_COLOR = {"STOP": RED, "PIVOT": AMBER, "CONTINUE": TEAL}

_PACE = True


def set_pace(on: bool) -> None:
    global _PACE
    _PACE = on


def pace(seconds: float) -> None:
    if _PACE and seconds > 0:
        time.sleep(seconds)


def c(s: str, rgb: str, b: bool = False) -> str:
    return f"\033[{'1;' if b else ''}38;2;{rgb}m{s}\033[0m"


def badge(s: str, rgb: str) -> str:
    return f"\033[48;2;{rgb}m\033[38;2;{INK}m\033[1m {s} \033[0m"


BAR = c("▌", TEAL, True)
RULE = c("─" * 58, DIM)
OK = c("✓", TEAL, True)
NO = c("✗", RED, True)
SRC = c("└─", DIM)


def out(s: str = "", d: float = 0.0) -> None:
    sys.stdout.write(s + "\n")
    sys.stdout.flush()
    pace(d)


# ---- section renderers (data in, demo layout out) -------------------------
def header() -> None:
    out("")
    out(f"  {c('venture-pilot', TEAL, True)}  {c('·', DIM)}  "
        f"{c('human-in-the-loop customer discovery', MUTED)}", 0.2)
    out(f"  {RULE}", 0.05)


def idea(text: str) -> None:
    out(f"  {c('idea', MUTED)}  " + c('"' + text + '"', WHITE), 0.5)


def section(label: str, note: str) -> None:
    out("")
    out(f"  {BAR} {c(label, TEAL, True)}   {c(note, MUTED)}", 0.3)


def plan(steps) -> None:
    """steps: list of (n, task, who, who_color)."""
    for n, task, who, col in steps:
        out(f"    {c(str(n), DIM)}  " + c(task.ljust(44), WHITE) + c(who, col), 0.14)


def approve_prompt(answer: str) -> None:
    out(f"    {c('approve plan?', MUTED)}  {c('[Y/n]', DIM)} "
        f"{c('>', TEAL)} {c(answer, TEAL, True)}", 0.4)


def approve_query() -> str:
    """Styled prompt string for an interactive input() call."""
    return f"    {c('approve plan?', MUTED)}  {c('[Y/n]', DIM)} {c('>', TEAL)} "


_MODE_LABEL = {
    "api": ("your Anthropic API key", TEAL),
    "sdk": ("Claude subscription · no API key", INDIGO),
    "mock": ("offline demo · no AI calls", AMBER),
}


def mode_banner(mode: str) -> None:
    label, col = _MODE_LABEL.get(mode, (mode, MUTED))
    out(f"  {c('●', col)} {c(mode, col, True)}  {c('·', DIM)}  {c(label, MUTED)}", 0.0)


def finding(text: str, source_label: str) -> None:
    out(f"    {OK}  " + c(text.ljust(44), WHITE) + f"{SRC} {c(source_label, INDIGO)}", 0.2)


def abstain(text: str) -> None:
    out(f"    {c('·', AMBER, True)}  " + c(text.ljust(24), MUTED)
        + c("→ abstained, not asserted", MUTED), 0.4)


def artifact(name: str, path: str, tag: str) -> None:
    out(f"    {OK}  " + c(name.ljust(18), WHITE) + c(path.ljust(28), INDIGO) + c(tag, DIM), 0.18)


def pause(next_cmd: str) -> None:
    out("")
    out(f"  {badge('PAUSE', AMBER)}  {c('YOUR MOVE', AMBER, True)}", 0.3)
    out(f"     {c('run the interviews yourself — we never talk to', MUTED)}", 0.1)
    out(f"     {c('your customers for you.  when you are done:', MUTED)}", 0.25)
    out(f"       {c('>', TEAL)} {c(next_cmd, TEAL, True)}", 0.4)
    out("")


def synth_counts(n_transcripts: int, grounded: int, total: int) -> None:
    out("")
    out(f"  {BAR} {c('SIGNAL SYNTHESIS', TEAL, True)}   {c('intent vs. politeness', MUTED)}", 0.3)
    qmark = OK if grounded == total else c("✗", RED, True)
    out(f"   {c('transcripts', MUTED)} {c(str(n_transcripts), WHITE, True)}   {c('·', DIM)}   "
        f"{c('cited quotes', MUTED)} {c(f'{grounded}/{total} grounded', WHITE, True)} {qmark}", 0.4)
    out(f"  {RULE}", 0.05)


def verdict(label: str, confidence: float, summary_lines, evidence,
            demand: str, recommendation: str) -> None:
    col = VERDICT_COLOR.get(label, AMBER)
    out(f"   {c('VERDICT', MUTED, True)}   {badge(label, col)}      "
        f"{c('confidence', MUTED)} {c(f'{confidence:.2f}', WHITE, True)} {c('· calibrated', DIM)}", 0.6)
    out("")
    for ln in summary_lines:
        out("   " + c(_clip(ln, 54), WHITE), 0.16)
    out("")
    out(f"   {c('evidence', MUTED)}", 0.18)
    for kind, quote, note in evidence[:5]:
        mark = OK if kind == "signal" else NO
        note_col = TEAL if kind == "signal" else MUTED
        out(f"     {mark}  " + c(_q(_clip(quote, 30)).ljust(34), WHITE if kind == "signal" else DIM)
            + c(_clip(note, 26), note_col), 0.25)
    if demand:
        out(f"     {c('→', INDIGO, True)}  " + c(_clip(demand, 56), INDIGO), 0.5)
    out("")
    if recommendation:
        out(f"   {c('next', TEAL, True)}   " + c(recommendation, WHITE), 0.4)
    out(f"  {RULE}", 0.05)
    out("   " + c("every line links to a verbatim quote or a source.", MUTED), 0.12)
    out("   " + c("nothing is asserted — including the call to act.", MUTED), 0.4)
    out("")


def _q(s: str) -> str:
    s = s.strip().strip('"')
    return f'"{s}"'


def _clip(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"
