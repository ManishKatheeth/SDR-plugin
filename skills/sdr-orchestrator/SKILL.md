---
name: sdr-orchestrator
description: >-
  Control tower and entry point for the SDR plugin. Use this skill whenever the
  user is getting started with, setting up, or configuring the SDR plugin — adding
  API keys / credentials (HubSpot, Clay, Gmail), asking "how do I set this up",
  "what can this plugin do", "what do I need to add", or "is the plugin up to
  date" — and whenever they want to run the outbound pipeline or aren't sure which
  command, skill, or reference file applies to finding leads, qualifying them,
  ingesting to HubSpot, or writing cold emails. It routes the goal to the right
  command + sub-skill + reference files. Reach for it even when the user doesn't
  name a specific command — if they describe an SDR/outbound goal, start here.
---

# SDR Orchestrator

This is the map for the SDR plugin. The plugin automates the outbound pipeline in
three stages — **find & qualify leads → ingest into HubSpot → draft cold emails** —
and gates every irreversible action (CRM writes, Gmail drafts) behind a human
confirmation prompt, logging each to an audit trail.

Your job when this skill triggers: figure out where the user is (just installed?
mid-pipeline? stuck on a single step?) and route them to the right **play** below.
Don't reimplement what the sub-skills already do — point to them and let them load
their own fresh rules.

## First-time setup — the only manual steps

A new user only has to do two things; everything else is automatic.

1. **Add the HubSpot token** (required for live CRM writes):
   ```bash
   export HUBSPOT_PRIVATE_APP_TOKEN=pat-na1-...
   ```
   Put it in the shell profile or a `.env`. Without it, `/ingest-leads` runs in
   safe **dry-run** mode (normalizes + de-dupes, prints the payload, no API call).

2. **Connect the MCP servers** at the account level:
   - **Clay MCP** — primary lead sourcing for `/find-leads`.
   - **Gmail MCP** — used by `/send-cold-email` to create drafts (never sends).

That's it. Note what you do **not** have to do manually:

- **Custom HubSpot properties** (`lead_score`, `lead_qualification_reason`,
  `hs_funding_stage`, `recent_funding_round`) are auto-created on the first
  `/ingest-leads` run by `skills/crm-mapping/scripts/ensure_hubspot_setup.py`,
  which verifies the token and provisions anything missing (cached after first run).

**Verify setup without writing anything:**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/crm-mapping/scripts/ensure_hubspot_setup.py" --dry-run
```
This confirms the token is present and valid and lists the properties it would
ensure — making no changes. If it reports `token_present: false`, the token isn't
set; if `token_valid: false`, the token is wrong.

## Staying up to date

A `SessionStart` hook (`hooks/scripts/check-version.py`) compares the installed
version against the latest on GitHub once per session and nudges you if you're
behind. To update:

```bash
claude plugin marketplace update sdr-tools
claude plugin update sdr-plugin
```
If you're running from a clone of the source repo, `git pull` instead.

## Freshness principle — the file on disk always wins

Each sub-skill re-reads its reference files **fresh from disk on every run**, so the
sales team can tune behavior by editing markdown — no code changes, effective
immediately. When routing a task, trust the sub-skill to load the current rules; if
something you remember conflicts with a reference file, the file is correct. Each
sub-skill has its own "Freshness — always use the latest rules" section:

- `skills/lead-qualification/SKILL.md`
- `skills/crm-mapping/SKILL.md`
- `skills/cold-email-writing/SKILL.md`

## Plays — route the goal to the right place

### Play 1 — Find & qualify leads
- **When:** "find me leads", "is this company a fit", sourcing from Clay / web / CSV.
- **Command:** `/find-leads "<ICP description>"` or `/find-leads "csv:/path.csv"`
- **Handled by:** `lead-scraper` agent + `lead-qualification` skill.
- **Reads:** `skills/lead-qualification/references/{icp-definition.md, scoring-rubric.md, disqualifiers.md}`
- **Runs:** `skills/lead-qualification/scripts/score_leads.py`
- **Output:** `qualified-leads.json`. Tune targeting by editing the three references.

### Play 2 — Ingest leads into HubSpot
- **When:** "push these leads to HubSpot", "ingest", "upsert contacts".
- **Command:** `/ingest-leads ./qualified-leads.json`
- **Handled by:** `crm-ingestor` agent + `crm-mapping` skill.
- **Reads:** `skills/crm-mapping/references/{hubspot-field-map.md, dedupe-policy.md, custom-properties.json}`
- **Runs:** `skills/crm-mapping/scripts/{ensure_hubspot_setup.py, normalize_leads.py, hubspot_upsert.py}`
- **Safety:** CRM-write confirmation hook fires before each write; qualification-gate
  hook blocks ingest if no `qualified: true` leads exist. No token → dry-run.

### Play 3 — Draft a cold email
- **When:** "write a cold email to X", "draft outreach for this contact".
- **Command:** `/send-cold-email <email>`
- **Handled by:** `cold-emailer` agent + `cold-email-writing` skill.
- **Reads:** `skills/cold-email-writing/references/{email-templates.md, tone-guide.md, compliance-rules.md}`
- **Runs:** `skills/cold-email-writing/scripts/validate_email.py`
- **Safety:** validated for CAN-SPAM/GDPR before a Gmail **draft** is created; the
  Gmail-draft confirmation hook fires first. It drafts, never sends.

### Play 4 — Run the whole pipeline
- **When:** "do the full outbound run", "run the SDR pipeline end to end".
- **Command:** `/sdr-pipeline "<ICP description>"`
- **Behavior:** runs Plays 1 → 2 → 3 in order, pausing for confirmation at each
  irreversible step. Never fully unattended.

## Skill & reference map

| Sub-skill | Reference files (editable, freshness-checked) | Scripts |
|---|---|---|
| `lead-qualification` | `icp-definition.md`, `scoring-rubric.md`, `disqualifiers.md` | `score_leads.py` |
| `crm-mapping` | `hubspot-field-map.md`, `dedupe-policy.md`, `custom-properties.json` | `ensure_hubspot_setup.py`, `normalize_leads.py`, `hubspot_upsert.py` |
| `cold-email-writing` | `email-templates.md`, `tone-guide.md`, `compliance-rules.md` | `validate_email.py` |

All reference paths are under `skills/<sub-skill>/references/`; scripts under
`skills/<sub-skill>/scripts/`.

## Safety model (recap)

Every irreversible action is gated and logged — this is by design, not an error:

- **CRM-write guard** + **qualification gate** before HubSpot upserts.
- **Gmail-draft guard** before any draft is created.
- **Audit log** appends one JSON line per CRM write, email draft, and setup run to
  `~/.claude/sdr-plugin-audit.jsonl` (override with `$SDR_PLUGIN_AUDIT_LOG`).

See `README.md` for the full safety + audit details.
