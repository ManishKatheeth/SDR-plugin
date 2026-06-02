---
description: Normalize, de-duplicate, and upsert qualified leads into HubSpot via REST API.
argument-hint: "<path to qualified-leads.json> (e.g. ./qualified-leads.json)"
---

# /ingest-leads $1

Ingest the qualified leads in **$1** into HubSpot. Normalization and de-dupe checks
are automatic; **every HubSpot write is gated behind a confirmation hook** — nothing
is upserted without explicit approval.

## Steps

1. **Validate input.** If `$1` is empty or the file doesn't exist, ask for the path
   and stop. If the file exists but contains no leads marked `qualified: true`,
   abort with: "No qualified leads found in $1 — run /find-leads first."

2. **Check for HUBSPOT_PRIVATE_APP_TOKEN.** If the environment variable is unset,
   warn the user and run in `--dry-run` mode (normalizes and de-dupes but prints the
   payload without sending it to HubSpot).

3. **Delegate to `crm-ingestor`.** Pass the file path. The agent will:
   - Re-read `skills/crm-mapping/references/` fresh before mapping.
   - Normalize each lead's fields to the HubSpot schema.
   - Run de-dupe checks (email + domain) against existing HubSpot records.
   - Run `hubspot_upsert.py` for each non-duplicate lead (the hook will surface
     a confirmation prompt before each batch write).

4. **Present results.** Show:
   - N upserted (new), N updated (existing), N skipped (duplicates), N failed
     (API errors with reason).
   - Any leads that need manual review (field mapping ambiguity, company mismatch).

5. **Confirm done.** Suggest the next step:
   "Run `/send-cold-email <email>` for each new contact, or `/sdr-pipeline` to
   continue from the beginning."

## Notes

- A PreToolUse confirmation hook fires before every HubSpot write batch —
  that's expected and not an error.
- A PostToolUse audit hook logs every upsert to `~/.claude/sdr-plugin-audit.jsonl`.
- Dry-run mode is safe to run without a token and shows the exact payload.
