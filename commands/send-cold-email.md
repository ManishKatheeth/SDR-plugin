---
description: Write a personalised, compliance-checked cold email and create a Gmail draft for human review and sending.
argument-hint: "<lead email address or HubSpot contact ID> (e.g. jane@acme.com)"
---

# /send-cold-email $1

Draft a cold email to **$1**. Writing and compliance checks are automatic;
**a Gmail draft is created for human review — the plugin never sends email**.

## Steps

1. **Validate input.** If `$1` is empty or isn't a plausible email address or
   contact ID, ask the user and stop.

2. **Look up the lead.** Resolve `$1` to a full lead profile (company, role,
   recent signals, personalisation hooks) from `qualified-leads.json` in the
   working directory, or from HubSpot if not found locally.

3. **Delegate to `cold-emailer`.** Pass the lead profile. The agent will:
   - Re-read `skills/cold-email-writing/references/` fresh before writing.
   - Draft a subject and body using the current templates and tone guide.
   - Run `validate_email.py` to check CAN-SPAM / GDPR compliance.
   - If validation fails, revise until it passes (max 2 attempts), then report
     any remaining issues rather than drafting a non-compliant email.
   - Call `mcp__claude_ai_Gmail__create_draft` to create the draft — **the hook
     will surface a confirmation prompt before the Gmail call fires**.

4. **Present the email.** Show the full subject and body before the hook fires so
   the user can review the content.

5. **Confirm done.** Report the Gmail draft URL/ID and next step:
   "Open Gmail, review the draft, and send when ready."

## Notes

- The PreToolUse hook fires before the Gmail draft is created — confirm the
  content looks right before approving.
- The PostToolUse audit hook logs the draft (to, subject, timestamp) to
  `~/.claude/sdr-plugin-audit.jsonl`.
- Email is never auto-sent. The draft stays in Gmail until a human sends it.
