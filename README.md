# sdr-plugin

A Claude Code plugin that automates the SDR outbound pipeline in three stages:
**find and qualify leads → ingest into HubSpot → draft personalised cold emails**.
Each irreversible step is gated behind a human confirmation prompt and logged to
an audit trail.

## What's in the box

| Component | What it does |
|---|---|
| `/find-leads <ICP or csv:path>` | Sources leads from Clay MCP, web scraping, or CSV; scores them against the ICP; writes `qualified-leads.json`. |
| `/ingest-leads <file>` | Normalises, de-dupes, and upserts qualified leads into HubSpot via REST API. Dry-runs if no token is set. |
| `/send-cold-email <email>` | Drafts a personalised, compliance-checked cold email and creates a Gmail draft for human review. |
| `/sdr-pipeline <ICP>` | Runs all three stages end-to-end, pausing for confirmation at each step. |
| `lead-scraper` agent | Hybrid sourcing: Clay MCP (primary), web scraping (fallback), CSV import. Applies `lead-qualification` skill. |
| `crm-ingestor` agent | Normalises fields and runs HubSpot upsert. Applies `crm-mapping` skill. |
| `cold-emailer` agent | Writes and validates email drafts. Creates Gmail drafts. Never sends. |
| `lead-qualification` skill | ICP scoring rubric (freshness-checked). Editable references: ICP definition, scoring rubric, disqualifiers. |
| `crm-mapping` skill | HubSpot field mapping + de-dupe policy (freshness-checked). Scripts: normalize_leads.py, hubspot_upsert.py. |
| `cold-email-writing` skill | Template + tone guide + CAN-SPAM/GDPR rules (freshness-checked). Script: validate_email.py. |
| CRM confirmation hook | `PreToolUse` — asks for approval before every HubSpot write. |
| Qualification gate hook | `PreToolUse` — denies ingest if no qualified leads are present. |
| Email confirmation hook | `PreToolUse` — asks for approval before every Gmail draft. |
| Audit hook | `PostToolUse` — appends every CRM write and email draft to an audit log. |

## Prerequisites

- **Claude Code** with plugin support.
- **Python 3** — used by the hook scripts and pipeline scripts.
- **Clay MCP** connected at the account level (for lead sourcing).
- **Gmail MCP** connected at the account level (for email drafts).
- **HubSpot private app token** (for CRM writes — optional; without it, ingest runs in dry-run mode).

## Setup

### 1. Set the HubSpot token (required for live ingest)

```bash
export HUBSPOT_PRIVATE_APP_TOKEN=pat-na1-...
```

Add it to your shell profile or a `.env` file. Without it, `/ingest-leads`
runs in dry-run mode and prints the payload without calling HubSpot.

### 2. Install the plugin

```
claude plugin marketplace add /path/to/SDR-plugin
claude plugin install sdr-plugin@sdr-tools
```

That's it. The plugin auto-creates all required custom HubSpot properties the
first time `/ingest-leads` runs — no manual portal configuration needed.

The required properties (created once, idempotent) are:
- **Contact:** `lead_score` (number), `lead_qualification_reason` (single-line text)
- **Company:** `hs_funding_stage` (single-line text), `recent_funding_round` (checkbox)

After the first successful provision, a marker file
(`~/.claude/sdr-plugin-setup.json`) caches the result so no extra API calls are
made on subsequent runs. Pass `--force` to re-provision manually:

```bash
python3 skills/crm-mapping/scripts/ensure_hubspot_setup.py --force
```

To add more custom properties, edit
`skills/crm-mapping/references/custom-properties.json` and run with `--force`.

## Usage

```
/find-leads "Series A SaaS companies, 50-200 employees, US"
/ingest-leads ./qualified-leads.json
/send-cold-email sarah.chen@acmesales.com
```

Or run the full pipeline:

```
/sdr-pipeline "Series A SaaS companies, 50-200 employees, US"
```

Or import from a CSV:

```
/find-leads "csv:/path/to/prospects.csv"
```

## Tuning lead qualification

Edit the reference files in `skills/lead-qualification/references/` — no code
changes needed. Changes take effect on the next run:

- `icp-definition.md` — target segment, employee range, funding stages, qualification threshold.
- `scoring-rubric.md` — point weights per signal.
- `disqualifiers.md` — hard-stop rules (competitors, geographies, opt-outs).

## Tuning email templates

Edit `skills/cold-email-writing/references/`:

- `email-templates.md` — add/edit outreach templates per segment.
- `tone-guide.md` — adjust the voice and CTA style.
- `compliance-rules.md` — update for new legal requirements.

## Safety: confirmation gates + audit log

- **CRM write guard** (`hooks/scripts/guard-crm-write.sh`): `PreToolUse` hook
  that intercepts `hubspot_upsert.py` and forces an approval prompt.
- **Qualification gate** (`hooks/scripts/verify-qualified.py`): `PreToolUse` hook
  that denies ingest if the input file contains no qualified leads.
- **Email draft guard** (`hooks/scripts/guard-email-send.sh`): `PreToolUse` hook
  that intercepts `mcp__claude_ai_Gmail__create_draft` and forces approval.
- **Audit log** (`hooks/scripts/audit-sdr.py`): `PostToolUse` hook that appends
  one JSON line per action to `~/.claude/sdr-plugin-audit.jsonl`.
  Override the path with `$SDR_PLUGIN_AUDIT_LOG`.

## Audit log

The audit log is append-only and never deleted by the plugin. Each line is a
JSON object:

```json
{
  "ts": "2026-06-02T10:30:00Z",
  "user": "manishkatheeth",
  "action": "hubspot_upsert",
  "tool": "Bash",
  "target": "sarah.chen@acmesales.com",
  "subject": "",
  "tool_input": { ... }
}
```

Default location: `~/.claude/sdr-plugin-audit.jsonl`

## Version

Plugin version is in `.claude-plugin/plugin.json`. Tag releases with:

```
claude plugin tag .
```
