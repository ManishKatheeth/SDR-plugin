#!/usr/bin/env python3
"""sdr-plugin: pre-ingest qualification gate.

Fires (PreToolUse) before hubspot_upsert.py runs. Inspects the working
directory for qualified-leads.json or normalized-leads.json and denies the
write if no qualified leads are present — blocking ingest of raw or
unqualified data.

If the input file can't be found or read, the hook allows the call to proceed
(the script itself will handle the error) rather than incorrectly blocking work.
We never raise: a failing hook must not wedge the user.
"""
import json
import os
import sys
from pathlib import Path


def find_leads_file() -> Path | None:
    candidates = [
        "./normalized-leads.json",
        "./qualified-leads.json",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            return p
    return None


def main() -> None:
    # Consume stdin (hook payload) to avoid broken pipe.
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    leads_file = find_leads_file()
    if leads_file is None:
        # Can't find the file — allow and let the script error naturally.
        allow()
        return

    try:
        leads = json.loads(leads_file.read_text(encoding="utf-8"))
    except Exception:
        allow()
        return

    # Support both raw qualified-leads.json and normalized-leads.json formats.
    qualified_count = 0
    for lead in leads:
        if isinstance(lead, dict):
            src = lead.get("source_lead") or lead
            if src.get("qualified") is True:
                qualified_count += 1

    if qualified_count == 0:
        deny("sdr-plugin: no qualified leads found in the input file. Run /find-leads first to qualify leads before ingesting.")
    else:
        allow()


def allow() -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }))
    sys.exit(0)


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        allow()
