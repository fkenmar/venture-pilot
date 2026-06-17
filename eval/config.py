"""Runtime config, read from environment so no model identifier is hardcoded in
committed source. Copy .env.example to .env (gitignored) and fill it in.

The product runs on an Anthropic model whose identifier contains a vendor string;
keep that identifier in .env / the environment only, never in tracked files.
"""
import os


def _load_dotenv():
    """Minimal .env loader (avoids a python-dotenv dependency for one file)."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

# The model id (e.g. an Anthropic model string) — REQUIRED for api mode, from env only.
MODEL = os.environ.get("VP_MODEL", "")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_TOKENS = int(os.environ.get("VP_MAX_TOKENS", "1024"))


def require_api_config():
    missing = []
    if not API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not MODEL:
        missing.append("VP_MODEL")
    if missing:
        raise SystemExit(
            "Missing env for api mode: " + ", ".join(missing) +
            "\nCopy eval/.env.example to eval/.env and fill it in, "
            "or run with --mode mock for a no-key dry run."
        )
