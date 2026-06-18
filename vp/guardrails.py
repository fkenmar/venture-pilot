"""Hard per-run caps with enforcement + a kill-switch (ARCHITECTURE §5).

Not alerts — a `CapExceeded` is raised and the orchestrator halts. This is the
structural antidote to the runaway-loop / margin-blowout failure class.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from . import config


class CapExceeded(RuntimeError):
    """Raised when a run exceeds a hard cap. The orchestrator stops on this."""


@dataclass
class Budget:
    max_steps: int = config.MAX_STEPS
    max_tokens: int = config.MAX_RUN_TOKENS
    max_dollars: float = config.MAX_DOLLARS
    max_wall_s: float = config.MAX_WALL_S
    steps: int = 0
    in_tokens: int = 0
    out_tokens: int = 0
    dollars: float = 0.0
    _start: float = 0.0

    def __post_init__(self):
        self._start = time.time()

    @property
    def tokens(self) -> int:
        return self.in_tokens + self.out_tokens

    @property
    def elapsed(self) -> float:
        return time.time() - self._start

    def step(self, label: str = "") -> None:
        self.steps += 1
        self._check(f"step '{label}'")

    def add_usage(self, in_tokens: int, out_tokens: int) -> None:
        self.in_tokens += int(in_tokens or 0)
        self.out_tokens += int(out_tokens or 0)
        self.dollars += (in_tokens or 0) / 1e6 * config.PRICE_IN_PER_MTOK
        self.dollars += (out_tokens or 0) / 1e6 * config.PRICE_OUT_PER_MTOK
        self._check("token usage")

    def _check(self, where: str) -> None:
        if self.steps > self.max_steps:
            raise CapExceeded(f"step cap {self.max_steps} exceeded at {where}")
        if self.tokens > self.max_tokens:
            raise CapExceeded(f"token cap {self.max_tokens} exceeded at {where}")
        if self.dollars > self.max_dollars:
            raise CapExceeded(f"cost cap ${self.max_dollars:.2f} exceeded at {where}")
        if self.elapsed > self.max_wall_s:
            raise CapExceeded(f"wall-clock cap {self.max_wall_s:.0f}s exceeded at {where}")

    def summary(self) -> dict:
        return {"steps": self.steps, "in_tokens": self.in_tokens, "out_tokens": self.out_tokens,
                "tokens": self.tokens, "dollars": round(self.dollars, 4),
                "elapsed_s": round(self.elapsed, 2)}
