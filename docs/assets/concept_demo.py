#!/usr/bin/env python3
"""CONCEPT storyboard for the venture-pilot README demo GIF.

NOT functional software. This script only prints a scripted, paced mock of the
*envisioned* product experience so VHS can record it (docs/assets/demo.tape).
The only thing that actually runs today is the Phase 0.1 eval in `eval/`.

Usage (driven by the tape):  python concept_demo.py validate "<idea>"
                             python concept_demo.py synthesize
"""
import sys, time

# ---- brand palette (truecolor ANSI) ---------------------------------------
TEAL, AMBER, RED = "32;227;162", "245;165;36", "242;84;91"
INDIGO, WHITE, MUTED, DIM = "91;141;239", "230;237;243", "123;138;165", "78;90;108"
INK = "10;14;20"

def c(s, rgb, b=False):
    return f"\033[{'1;' if b else ''}38;2;{rgb}m{s}\033[0m"

def badge(s, rgb):
    return f"\033[48;2;{rgb}m\033[38;2;{INK}m\033[1m {s} \033[0m"

BAR = c("▌", TEAL, True)
RULE = c("─" * 58, DIM)
OK = c("✓", TEAL, True)
NO = c("✗", RED, True)
SRC = c("└─", DIM)

def line(s="", d=0.05):
    sys.stdout.write(s + "\n"); sys.stdout.flush(); time.sleep(d)

def head(label, note):
    line(); line(f"  {BAR} {c(label, TEAL, True)}   {c(note, MUTED)}", 0.34)


def validate(idea):
    line()
    line(f"  {c('venture-pilot', TEAL, True)}  {c('·', DIM)}  "
         f"{c('human-in-the-loop customer discovery', MUTED)}", 0.25)
    line(f"  {RULE}", 0.1)
    line(f"  {c('idea', MUTED)}  " + c('"' + idea + '"', WHITE), 0.6)

    head("PLAN", "the agent preps — you approve anything irreversible")
    for n, task, who, col in [
        ("1", "find target customers + communities", "auto", TEAL),
        ("2", "draft outreach + interview script", "you send", AMBER),
        ("3", "build a landing-page test artifact", "you publish", AMBER),
        ("4", "synthesize your interviews -> verdict", "after calls", AMBER),
    ]:
        line(f"    {c(n, DIM)}  " + c(task.ljust(44), WHITE) + c(who, col), 0.16)
    line(f"    {c('approve plan?', MUTED)}  {c('[Y/n]', DIM)} "
         f"{c('>', TEAL)} {c('y', TEAL, True)}", 0.9)

    head("RESEARCH", "finding who actually has this pain")
    for who, tag in [
        ("ICP  eng managers · 50-200-person SaaS", "source"),
        ("community  r/engineeringmanagement · 218k", "source"),
        ("community  Rands Leadership Slack", "source"),
        ("already pay for  Fireflies · Otter · Notion", "3 srcs"),
    ]:
        line(f"    {OK}  " + c(who.ljust(44), WHITE) + f"{SRC} {c(tag, INDIGO)}", 0.22)
    line(f"    {c('·', AMBER, True)}  " + c("1 claim had no source".ljust(24), MUTED)
         + c("→ abstained, not asserted", MUTED), 0.5)

    head("ARTIFACTS", "drafted — nothing sent")
    for name, path, tag in [
        ("interview script", "out/interview-script.md", "Mom-Test"),
        ("outreach DMs", "out/outreach.md", "12 drafts"),
        ("landing page", "out/landing/index.html", "publish-gated"),
    ]:
        line(f"    {OK}  " + c(name.ljust(18), WHITE) + c(path.ljust(28), INDIGO)
             + c(tag, DIM), 0.2)

    line(); line(f"  {badge('PAUSE', AMBER)}  {c('YOUR MOVE', AMBER, True)}", 0.3)
    line(f"     {c('run the 8 interviews yourself — we never talk to', MUTED)}", 0.12)
    line(f"     {c('your customers for you.  when you are done:', MUTED)}", 0.3)
    line(f"       {c('>', TEAL)} {c('vp synthesize ./interviews/*.md', TEAL, True)}", 0.7)
    line()


def synthesize():
    line()
    line(f"  {BAR} {c('SIGNAL SYNTHESIS', TEAL, True)}   {c('intent vs. politeness', MUTED)}", 0.3)
    line(f"   {c('transcripts', MUTED)} {c('8', WHITE, True)}   {c('·', DIM)}   "
         f"{c('cited quotes', MUTED)} {c('24/24 grounded', WHITE, True)} {OK}", 0.45)
    line(f"  {RULE}", 0.1)
    line(f"   {c('VERDICT', MUTED, True)}   {badge('PIVOT', AMBER)}      "
         f"{c('confidence', MUTED)} {c('0.71', WHITE, True)} {c('· calibrated', DIM)}", 0.7)
    line()
    line("   " + c("real, paid pain is here — but not for thread summaries.", WHITE), 0.18)
    line("   " + c("6 of 8 already pay to fix post-meeting follow-ups.", WHITE), 0.6)
    line()
    line(f"   {c('evidence', MUTED)}", 0.2)
    line(f"     {NO}  " + c('"I\'d definitely use that"'.ljust(34), DIM)
         + c("politeness · no behavior", MUTED), 0.3)
    line(f"     {OK}  " + c('"we pay $40/mo for Fireflies"'.ljust(34), WHITE)
         + c("money already spent · t1", TEAL), 0.3)
    line(f"     {OK}  " + c('"dropped action items kill us"'.ljust(34), WHITE)
         + c("quantified pain · t5", TEAL), 0.45)
    line(f"     {c('→', INDIGO, True)}  "
         + c("demand points at meeting action-items, not TL;DRs", INDIGO), 0.6)
    line()
    line(f"   {c('next', TEAL, True)}   "
         + c("re-pitch the action-item tracker to those 6 buyers.", WHITE), 0.5)
    line(f"  {RULE}", 0.1)
    line("   " + c("every line links to a verbatim quote or a source.", MUTED), 0.14)
    line("   " + c("nothing is asserted — including the call to pivot.", MUTED), 0.5)
    line()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if cmd == "synthesize":
        synthesize()
    else:
        idea = sys.argv[2] if len(sys.argv) > 2 else "Slack bot that summarizes long threads for managers"
        validate(idea)
