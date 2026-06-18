"""Env-only runtime config for the vp app.

The model id is an Anthropic vendor string and the key is a secret — both live in
the environment / a gitignored .env, never in tracked source. We reuse the existing
`eval/.env` location so a single key serves the eval and the app.
"""
from __future__ import annotations

import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv() -> None:
    """Minimal .env loader (no python-dotenv dep). Looks at repo-root .env then eval/.env."""
    for rel in (".env", os.path.join("eval", ".env")):
        path = os.path.join(_REPO_ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

# Models (tiered per ARCHITECTURE §4): strong = verdict/synthesis/artifacts,
# fast = read-only research subagents. Both default to VP_MODEL when unset.
MODEL = os.environ.get("VP_MODEL", "")
FAST_MODEL = os.environ.get("VP_FAST_MODEL", "") or MODEL
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_TOKENS = int(os.environ.get("VP_MAX_TOKENS", "1500"))

# Hard per-run caps (ARCHITECTURE §5) — enforced as a kill-switch in guardrails.py.
MAX_STEPS = int(os.environ.get("VP_MAX_STEPS", "12"))
MAX_RUN_TOKENS = int(os.environ.get("VP_MAX_RUN_TOKENS", "500000"))
MAX_DOLLARS = float(os.environ.get("VP_MAX_DOLLARS", "1.50"))
MAX_WALL_S = float(os.environ.get("VP_MAX_WALL_S", "240"))

# Rough $/MTok for usage accounting (overridable; defaults to an Opus-tier estimate).
PRICE_IN_PER_MTOK = float(os.environ.get("VP_PRICE_IN", "5.0"))
PRICE_OUT_PER_MTOK = float(os.environ.get("VP_PRICE_OUT", "25.0"))


def has_api_config() -> bool:
    return bool(API_KEY and MODEL)


def default_mode() -> str:
    """Live when a key+model are configured, else the deterministic mock path."""
    return "api" if has_api_config() else "mock"


def require_api_config() -> None:
    missing = [n for n, v in (("ANTHROPIC_API_KEY", API_KEY), ("VP_MODEL", MODEL)) if not v]
    if missing:
        raise SystemExit(
            "Missing env for --api mode: " + ", ".join(missing)
            + "\nCopy eval/.env.example to eval/.env and fill it in, or run with --mock."
        )
