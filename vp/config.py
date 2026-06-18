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

# Model alias for the Claude Agent SDK backend (--sdk), which runs on the
# logged-in Claude subscription instead of a metered API key.
SDK_MODEL = os.environ.get("VP_SDK_MODEL", "sonnet")

# OpenAI-compatible backend (--openai) — works with ANY /v1/chat/completions server:
# OpenAI, OpenRouter (→ Claude/GPT/Gemini/Llama/...), Groq, Together, Gemini's OpenAI
# endpoint, or a LOCAL model (Ollama / LM Studio / vLLM). Bring whatever LLM you want.
OPENAI_BASE_URL = os.environ.get("VP_OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("VP_OPENAI_MODEL", "")
OPENAI_KEY = os.environ.get("VP_OPENAI_KEY", "") or os.environ.get("OPENAI_API_KEY", "")

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


def sdk_available() -> bool:
    """True when the Claude Agent SDK + a `claude` CLI are present (subscription path)."""
    import importlib.util
    import shutil
    return shutil.which("claude") is not None and importlib.util.find_spec("claude_agent_sdk") is not None


def openai_available() -> bool:
    """True when an OpenAI-compatible LLM is configured (a model + a key, or a local URL)."""
    local = any(h in OPENAI_BASE_URL for h in ("localhost", "127.0.0.1", "0.0.0.0"))
    return bool(OPENAI_MODEL and (OPENAI_KEY or local))


def require_openai_config() -> None:
    if not OPENAI_MODEL:
        raise SystemExit("--openai needs VP_OPENAI_MODEL (+ VP_OPENAI_KEY / OPENAI_API_KEY "
                         "unless the endpoint is local). Run `vp doctor`.")


def default_mode():
    """The LLM the user wants. `VP_BACKEND` pins it explicitly; otherwise pick the best
    that's configured: a custom LLM you set up (openai) -> your Anthropic key (api) ->
    a logged-in Claude subscription (sdk). Returns None when nothing is set up — the CLI
    then prints setup help. There is no offline/mock mode; this app always uses a real LLM."""
    pinned = os.environ.get("VP_BACKEND", "").strip().lower()
    if pinned in ("api", "sdk", "openai"):
        return pinned
    if openai_available():
        return "openai"
    if has_api_config():
        return "api"
    if sdk_available():
        return "sdk"
    return None


def require_api_config() -> None:
    missing = [n for n, v in (("ANTHROPIC_API_KEY", API_KEY), ("VP_MODEL", MODEL)) if not v]
    if missing:
        raise SystemExit(
            "Missing env for --api: " + ", ".join(missing)
            + "\nAdd them to .env (cp .env.example .env), or use --sdk / --openai. See `vp doctor`."
        )
