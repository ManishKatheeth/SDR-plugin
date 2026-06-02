#!/usr/bin/env bash
# sdr-plugin: confirmation guard for Gmail draft creation.
#
# Fires (PreToolUse) before mcp__claude_ai_Gmail__create_draft is called.
# Forces Claude Code to ask the user for explicit approval before a Gmail draft
# is created, so every cold email is reviewed by a human before it even reaches
# the Drafts folder.
#
# The hook payload arrives on stdin; we consume it to avoid broken pipe.
cat >/dev/null 2>&1 || true

reason="sdr-plugin: this will create a Gmail draft for a cold outreach email. Review the subject and body above before approving."

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$reason"
exit 0
