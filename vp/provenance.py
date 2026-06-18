"""Provenance: source-linked facts + cite-then-verify grounding.

The grounding check is the executable form of the honesty wedge — a cited quote
must appear *verbatim* in the source text, or it is flagged as fabricated. The
substring/normalisation logic is the same one the Phase 0.1 eval gates on.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Source:
    title: str
    url: str


@dataclass
class Finding:
    """A read-only research finding. `supported=False` means we abstained:
    a claim with no source is surfaced as abstained, never asserted."""
    label: str               # short display label, e.g. "ICP  eng managers · 50-200-person SaaS"
    claim: str               # the full claim text
    sources: list[Source] = field(default_factory=list)
    supported: bool = True

    @property
    def source_label(self) -> str:
        n = len(self.sources)
        return "source" if n == 1 else f"{n} srcs"


def _norm(s: str) -> str:
    return " ".join((s or "").split()).lower()


def ground_quotes(quotes, transcripts) -> dict:
    """Fraction of cited quotes that appear verbatim in ANY transcript.

    quotes: iterable of strings. transcripts: iterable of transcript texts.
    Returns {grounded, total, rate, offenders}. No citations -> vacuously grounded.
    """
    corpus = [_norm(t) for t in transcripts]
    total = grounded = 0
    offenders = []
    for q in quotes:
        if not q or not q.strip():
            continue
        total += 1
        nq = _norm(q)
        if any(nq in t for t in corpus):
            grounded += 1
        else:
            offenders.append(q)
    rate = grounded / total if total else 1.0
    return {"grounded": grounded, "total": total, "rate": rate, "offenders": offenders}
