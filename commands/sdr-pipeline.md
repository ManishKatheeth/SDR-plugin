---
description: Run the full SDR outbound pipeline end-to-end: find leads, ingest to HubSpot, draft cold emails — pausing for confirmation at each irreversible step.
argument-hint: "<ICP segment or 'csv:<path>'> (e.g. 'Series A SaaS, 50-500 employees, US')"
---

# /sdr-pipeline $1

Run the full outbound pipeline for **$1**: find → qualify → ingest → email.
Each stage pauses for your confirmation before moving to the next; no stage is
skipped automatically.

## Steps

1. **Validate input.** If `$1` is empty, ask for an ICP description or CSV path.

2. **Stage 1 — Find leads.** Run the `/find-leads` logic for `$1` inline (delegate
   to `lead-scraper`). Present the qualified lead summary and ask:
   "Proceed to CRM ingestion with these N leads? (yes / filter / no)"
   - **no** → stop here; file stays on disk.
   - **filter** → let the user remove leads, then re-confirm.
   - **yes** → continue to Stage 2.

3. **Stage 2 — Ingest to CRM.** Run the `/ingest-leads` logic inline (delegate to
   `crm-ingestor`). Present the ingest summary (upserted / updated / skipped).
   The HubSpot confirmation hook fires per write — that's expected.
   Ask: "Proceed to draft cold emails for the N new contacts? (yes / no)"
   - **no** → stop here.
   - **yes** → continue to Stage 3.

4. **Stage 3 — Draft cold emails.** For each newly upserted contact, run the
   `/send-cold-email` logic inline (delegate to `cold-emailer`). The Gmail
   confirmation hook fires before each draft is created — that's expected.
   Process contacts one at a time so the user can approve each email individually.

5. **Confirm done.** Summarise the full pipeline run:
   - N leads sourced, N qualified.
   - N contacts upserted to HubSpot, N updated, N skipped.
   - N Gmail drafts created (list subject lines).
   - Any items needing follow-up (borderline leads, failed upserts, compliance
     warnings).

## Notes

- The pipeline pauses for human confirmation before every irreversible action
  (CRM writes and email drafts). It is never fully automated end-to-end.
- All three confirmation / audit hooks fire as normal — they are features, not
  errors.
- To run stages independently, use `/find-leads`, `/ingest-leads`, and
  `/send-cold-email` separately.
