#!/usr/bin/env bash
# sdr-plugin: confirmation guard for HubSpot writes.
#
# Fires (PreToolUse) before hubspot_upsert.py runs. Forces Claude Code to ask
# the user for explicit approval before any contact or company is written to
# HubSpot, so leads are never ingested without a human reviewing the set.

payload=$(cat 2>/dev/null || true)
cmd=$(printf '%s' "$payload" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || true)

if [[ "$cmd" != *hubspot_upsert.py* ]]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}\n'
  exit 0
fi

reason="sdr-plugin: this will write or update records in HubSpot. Confirm the qualified lead set is correct before allowing the CRM write."
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$reason"
exit 0
