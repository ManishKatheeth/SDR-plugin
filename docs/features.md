# SDR Plugin — Feature List

*What was built, and why each piece exists.*

---

## Commands

### `/find-leads <ICP or csv:path>`
**What:** Sources prospects matching an ICP description (e.g. "Series A SaaS, 50-200 employees, US") or a CSV file, scores each one, and writes `qualified-leads.json`.

**Why:** SDRs spend hours manually searching Clay, LinkedIn, and directories for leads that may not even fit the ICP. This command automates sourcing AND qualification in one step — only leads that meet the rubric survive to the next stage, cutting time-to-pipeline and reducing noise in HubSpot.

---

### `/ingest-leads <qualified-leads.json>`
**What:** Normalises the qualified lead data to the HubSpot schema, runs de-dupe checks, and upserts contacts + companies via the HubSpot REST API.

**Why:** Manual CRM entry is slow and produces duplicate records, mismatched field names, and inconsistent lifecycle stages. This command applies a single canonical field map and de-dupe policy every time, so HubSpot stays clean regardless of who runs the ingest.

---

### `/send-cold-email <email>`
**What:** Looks up the lead's profile, selects the right template, personalises the opening with a real signal, validates for CAN-SPAM/GDPR compliance, and creates a Gmail draft — never sends.

**Why:** SDRs writing individual cold emails from scratch are inconsistent in tone and frequently skip compliance basics (no opt-out link, misleading subject lines). This command enforces the team's tone guide and compliance rules on every draft while still giving the SDR full control over the final send.

---

### `/sdr-pipeline <ICP>`
**What:** Runs all three stages end-to-end (find → ingest → email) as a single orchestrated command, pausing for human confirmation at each irreversible step.

**Why:** For a full outreach campaign, running three separate commands and passing files between them is friction. This command chains the full pipeline while keeping humans in the loop — no stage is skipped or auto-approved.

---

## Agents

### `lead-scraper`
**What:** Hybrid sourcing agent that queries Clay MCP, falls back to web scraping (WebFetch), or imports from CSV depending on the input. Scores every lead using `score_leads.py` and the current ICP rubric.

**Why:** Clay doesn't cover every company and not every ingest starts from a description — sometimes it's a CSV from a conference or a website you scraped. The hybrid approach means the pipeline works regardless of the input format.

---

### `crm-ingestor`
**What:** Reads `qualified-leads.json`, runs `normalize_leads.py` to apply the HubSpot field map, then calls `hubspot_upsert.py` for each lead. Rejects leads not marked `qualified: true`.

**Why:** Separating the normalisation step from the sourcing step means the field map can be updated without touching the sourcing logic — and the agent can be tested on any JSON file, not just Clay output.

---

### `cold-emailer`
**What:** Drafts a personalised cold email using the current templates and tone guide, validates it for compliance, and creates a Gmail draft via the Gmail MCP.

**Why:** A dedicated draft-only agent makes it impossible (by design) to accidentally auto-send — the agent has no send tool in its allowed tool list, only `create_draft`.

---

## Skills

### `lead-qualification`
**What:** Scores a lead on a 0-100 scale using weighted signals (firmographics, contact title, growth signals) and disqualifies against a hard-stop list. Returns a structured JSON result with score, qualified boolean, and reason.

**Why:** Qualification criteria change as the ICP evolves — new markets, different company sizes, updated competitor lists. Because the skill re-reads its reference files on every run, a sales manager can edit `icp-definition.md` and the change takes effect on the next `/find-leads` with no code changes.

**Freshness files re-read every run:**
- `references/icp-definition.md` — target segment, qualification threshold
- `references/scoring-rubric.md` — point weights per signal
- `references/disqualifiers.md` — hard-stop rules

---

### `crm-mapping`
**What:** Maps lead fields to HubSpot contact and company properties, handles de-duplication (email match → update, domain match → associate, neither → create), and returns a per-lead status: upserted / updated / skipped / failed.

**Why:** HubSpot schemas are customised per organisation and change over time. Encoding the field map in an editable reference file means the ops team can update it without touching Python scripts.

**Freshness files re-read every run:**
- `references/hubspot-field-map.md` — source field → HubSpot property
- `references/dedupe-policy.md` — order of operations for de-duplication

---

### `cold-email-writing`
**What:** Selects the right template for the lead's segment and signal, personalises the opening line, enforces tone rules, validates for CAN-SPAM and GDPR compliance using `validate_email.py`, and produces a draft-ready email.

**Why:** Compliance violations (missing opt-out, spam trigger words, deceptive subject lines) expose the company to legal risk. Encoding the rules in a reference file and running automated validation on every draft catches issues before they become problems.

**Freshness files re-read every run:**
- `references/email-templates.md` — outreach templates per segment
- `references/tone-guide.md` — voice, CTA formats, what to avoid
- `references/compliance-rules.md` — CAN-SPAM / GDPR requirements

---

## Hooks

### `guard-crm-write.sh` (PreToolUse)
**What:** Fires before `hubspot_upsert.py` runs and emits `permissionDecision: "ask"`, forcing Claude Code to surface an approval prompt before any HubSpot write.

**Why:** A CRM write is hard to reverse — duplicates, wrong lifecycle stages, and overwritten fields cause downstream problems. A mandatory confirmation step ensures no leads reach HubSpot without explicit human approval.

---

### `verify-qualified.py` (PreToolUse)
**What:** Fires before `hubspot_upsert.py` runs and inspects the input file. If no leads are marked `qualified: true`, it emits `permissionDecision: "deny"` with a clear reason — blocking the ingest entirely.

**Why:** Without this gate, it's possible to accidentally ingest raw, unscored leads (e.g. a file passed incorrectly) and pollute HubSpot with off-ICP contacts. This hook is the hard enforcement of the rule "only qualified leads reach the CRM."

---

### `guard-email-send.sh` (PreToolUse)
**What:** Fires before `mcp__claude_ai_Gmail__create_draft` and emits `permissionDecision: "ask"`, prompting the user to review the subject and body before the draft is created.

**Why:** Cold emails are one-way communications with real prospects. A confirmation step forces the SDR to read the draft before it lands in their Drafts folder, catching tone issues or wrong recipients before they become awkward.

---

### `audit-sdr.py` (PostToolUse)
**What:** Fires after every HubSpot upsert and every Gmail draft creation. Appends one JSON line per action (timestamp, user, action type, target email/contact, tool input) to `~/.claude/sdr-plugin-audit.jsonl`.

**Why:** When a prospect says "I never opted into this" or a manager asks "who added this contact to HubSpot?", the audit log provides the answer. It's append-only so it can't be quietly edited, and it never blocks the user even if it fails to write.

---

## Scripts

### `score_leads.py`
Standalone scoring script. Parses the rubric markdown, applies weighted signals to a lead JSON, and returns a structured qualification result. Runnable independently for testing the ICP rules.

### `normalize_leads.py`
Applies the HubSpot field map to `qualified-leads.json` and produces `normalized-leads.json`. Handles all transforms (title-case names, strip domain prefixes, industry enum mapping). Skips unqualified leads silently.

### `hubspot_upsert.py`
Calls the HubSpot v3 Contacts and Companies API to upsert a single normalized lead. Searches by email and domain before creating to enforce de-dupe. Runs in dry-run mode automatically if `HUBSPOT_PRIVATE_APP_TOKEN` is not set — safe to call without credentials.

### `validate_email.py`
Checks a cold email subject and body against a compliance checklist: subject length, spam trigger words, all-caps detection, opt-out presence, and CTA presence. Returns a PASS/FAIL JSON with a list of specific issues. Called by `cold-emailer` before any Gmail draft is created.

---

## Reference files (editable by the team)

All reference files are Markdown and live in `skills/*/references/`. They are
**never cached** — every agent re-reads them from disk at the start of each run.
To update a rule, edit the file. No code changes, no restarts.

| File | What it controls |
|---|---|
| `lead-qualification/references/icp-definition.md` | Target segment, employee range, funding stages, qualification threshold |
| `lead-qualification/references/scoring-rubric.md` | Point weights for each lead signal |
| `lead-qualification/references/disqualifiers.md` | Hard-stop rules (competitors, geo bans, opt-outs) |
| `crm-mapping/references/hubspot-field-map.md` | Lead field → HubSpot property mapping and transforms |
| `crm-mapping/references/dedupe-policy.md` | De-dupe order of operations and edge cases |
| `cold-email-writing/references/email-templates.md` | Outreach templates per segment/signal |
| `cold-email-writing/references/tone-guide.md` | Voice, style, and CTA format rules |
| `cold-email-writing/references/compliance-rules.md` | CAN-SPAM / GDPR requirements and validation checklist |
