#!/usr/bin/env bash
# sdr-plugin: confirmation guard for HubSpot writes.
#
# Fires (PreToolUse) before hubspot_upsert.py runs. Forces Claude Code to ask
# the user for explicit approval before any contact or company is written to
# HubSpot, so leads are never ingested without a human reviewing the set.
#
# The hook payload arrives on stdin; we consume it to avoid broken pipe.
cat >/dev/null 2>&1 || true

reason="sdr-plugin: this will write or update records in HubSpot. Confirm the qualified lead set is correct before allowing the CRM write."

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$reason"
exit 0
