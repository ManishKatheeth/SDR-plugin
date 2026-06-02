#!/usr/bin/env python3
"""sdr-plugin: append-only audit logger for CRM writes and Gmail drafts.

Fires (PostToolUse) after hubspot_upsert.py completes or after
mcp__claude_ai_Gmail__create_draft succeeds. Records who did what, when.

Because this plugin writes to live HubSpot and real Gmail drafts, the audit
trail lets the team review every ingest and draft and reconstruct decisions.

Log location (one JSON object per line):
  $SDR_PLUGIN_AUDIT_LOG  (if set), else  ~/.claude/sdr-plugin-audit.jsonl

The hook payload is read from stdin. We never raise: a failing audit logger
must not block the user's work, so all errors are swallowed.
"""
import json
import os
import sys
from datetime import datetime, timezone


def main() -> None:
    log_path = os.environ.get(
        "SDR_PLUGIN_AUDIT_LOG",
        os.path.join(os.path.expanduser("~"), ".claude", "sdr-plugin-audit.jsonl"),
    )

    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    # Extract the relevant target from whichever tool fired.
    cmd = tool_input.get("command", "")

    is_hubspot_cmd = "hubspot_upsert.py" in cmd or "ensure_hubspot_setup.py" in cmd
    is_gmail = "gmail" in tool_name.lower()
    if not is_hubspot_cmd and not is_gmail:
        sys.exit(0)
    if "gmail" in tool_name.lower():
        target = tool_input.get("to", "") or tool_input.get("recipient", "")
        subject = tool_input.get("subject", "")
        action_type = "gmail_draft"
    elif "ensure_hubspot_setup" in cmd:
        target = ""
        subject = ""
        action_type = "hubspot_setup"
    else:
        # HubSpot upsert — extract contact email from the --contact arg.
        import re
        m = re.search(r'"email"\s*:\s*"([^"]+)"', cmd)
        target = m.group(1) if m else ""
        subject = ""
        action_type = "hubspot_upsert"

    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user": os.environ.get("USER", "unknown"),
        "action": action_type,
        "tool": tool_name,
        "target": target,
        "subject": subject,
        "tool_input": tool_input,
    }

    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
