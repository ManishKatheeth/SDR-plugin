#!/usr/bin/env python3
"""sdr-plugin: SessionStart version nudge.

Compares the installed plugin version against the latest on GitHub and, if a newer
version exists, surfaces a one-line notice with the update command. This is the
"always-on" replacement for a plugin CLAUDE.md (which Claude Code does not auto-load
for plugins) — it runs once per session.

Resilient by design: any failure (offline, timeout, parse error, GitHub down) is
swallowed and the session starts normally. We never block the user's work.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REMOTE_URL = "https://raw.githubusercontent.com/ManishKatheeth/SDR-plugin/main/.claude-plugin/plugin.json"
TIMEOUT_SECONDS = 3


def parse_version(text: str) -> tuple[int, ...] | None:
    """Pull a version string out of a plugin.json blob and return a comparable tuple."""
    try:
        data = json.loads(text)
        raw = str(data.get("version", ""))
    except Exception:
        return None
    nums = re.findall(r"\d+", raw)
    return tuple(int(n) for n in nums) if nums else None


def local_version() -> tuple[int, ...] | None:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not root:
        return None
    path = Path(root) / ".claude-plugin" / "plugin.json"
    try:
        return parse_version(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def remote_version() -> tuple[int, ...] | None:
    try:
        req = urllib.request.Request(REMOTE_URL, headers={"User-Agent": "sdr-plugin-version-check"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return parse_version(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def main() -> None:
    local = local_version()
    remote = remote_version()

    # Only nudge when we can confidently say remote is newer than local.
    if local and remote and remote > local:
        local_str = ".".join(str(n) for n in local)
        remote_str = ".".join(str(n) for n in remote)
        notice = (
            f"📦 SDR plugin update available: v{local_str} installed, v{remote_str} on GitHub. "
            "Update with: `claude plugin marketplace update sdr-tools && claude plugin update sdr-plugin` "
            "(or `git pull` if running from source)."
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": notice,
            }
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
