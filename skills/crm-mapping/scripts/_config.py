"""Shared HubSpot token storage for the SDR plugin.

The token is resolved in priority order:
  1. HUBSPOT_PRIVATE_APP_TOKEN environment variable (advanced / CI use)
  2. ~/.claude/sdr-plugin-config.json  ->  {"hubspot_private_app_token": "..."}

The config file is written with mode 600 (owner read/write only). It lives in
the user's home directory, never in the repo, so it is never committed.

Both standalone scripts in this directory import this module; because Python
puts a script's own directory on sys.path[0], `from _config import ...` works
when the scripts are run directly (python3 /abs/path/script.py).
"""
import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "sdr-plugin-config.json"
TOKEN_KEY = "hubspot_private_app_token"
ENV_VAR = "HUBSPOT_PRIVATE_APP_TOKEN"


def _read_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def resolve_token() -> str:
    """Return the HubSpot token from the env var, then the config file, else ''."""
    env = os.environ.get(ENV_VAR, "").strip()
    if env:
        return env
    return str(_read_config().get(TOKEN_KEY, "")).strip()


def token_source() -> str:
    """Where the active token came from: 'env', 'config', or 'none'."""
    if os.environ.get(ENV_VAR, "").strip():
        return "env"
    if _read_config().get(TOKEN_KEY):
        return "config"
    return "none"


def save_token(token: str) -> Path:
    """Persist the token to the config file (merging existing keys), mode 600."""
    token = (token or "").strip()
    if not token:
        raise ValueError("Refusing to save an empty token.")
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = _read_config()
    config[TOKEN_KEY] = token
    # Write with restrictive perms even on first creation.
    fd = os.open(CONFIG_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")
    os.chmod(CONFIG_PATH, 0o600)
    return CONFIG_PATH


def redact(token: str) -> str:
    """Mask a token for display: keep a short prefix and the last 4 chars."""
    token = (token or "").strip()
    if not token:
        return ""
    last4 = token[-4:] if len(token) >= 4 else token
    # Preserve a recognizable HubSpot prefix (e.g. "pat-na1-") when present.
    prefix = ""
    for sep_count, ch in enumerate(token):
        prefix += ch
        if ch == "-" and prefix.count("-") >= 2:
            break
        if len(prefix) >= 8:
            break
    return f"{prefix}••••{last4}"
