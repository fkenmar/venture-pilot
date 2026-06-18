"""Full run trace — every step, tool, source, and token/cost — to JSONL.

Observability from step #1 is table stakes for a trust product (ARCHITECTURE §4).
Each run gets out/<run>/trace.jsonl.
"""
from __future__ import annotations

import json
import os
import time


class Trace:
    def __init__(self, path: str | None):
        self.path = path
        self.seq = 0
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # truncate any prior trace for this run
            open(path, "w").close()

    def event(self, kind: str, **data) -> None:
        self.seq += 1
        rec = {"seq": self.seq, "t": round(time.time(), 3), "kind": kind, **data}
        if self.path:
            with open(self.path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # convenience wrappers
    def step(self, label: str, **data) -> None:
        self.event("step", label=label, **data)

    def tool(self, name: str, **data) -> None:
        self.event("tool", name=name, **data)

    def source(self, url: str, title: str = "") -> None:
        self.event("source", url=url, title=title)

    def usage(self, model: str, in_tokens: int, out_tokens: int) -> None:
        self.event("usage", model=model, in_tokens=in_tokens, out_tokens=out_tokens)
