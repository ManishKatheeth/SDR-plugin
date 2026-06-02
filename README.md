# sdr-plugin

A Claude Code plugin that automates the SDR outbound pipeline in three stages:
**find and qualify leads → ingest into HubSpot → draft personalised cold emails**.
Each irreversible step is gated behind a human confirmation prompt and logged to
an audit trail.

## What's in the box

| Component | What it does |
|---|---|
| `sdr-orchestrator` skill | Central entry point: data contract, first-run onboarding preflight, a plugin inventory/index, version-update guidance, and "plays" that route any SDR goal to the right command, sub-skill, and reference files. Start here. |
| [`DATA_CONTRACT.md`](DATA_CONTRACT.md) | Splits every file into **User Layer** (credentials, tunable references, outputs — read-only to the agent) and **System Layer** (plugin code — safe to edit). Read before changing files. |
| `/find-leads <ICP or csv:path>` | Sources leads from Clay MCP, web scraping, or CSV; scores them against the ICP; writes `qualified-leads.json`. |
| `/ingest-leads <file>` | Normalises, de-dupes, and upserts qualified leads into HubSpot via REST API. Dry-runs if no token is set. |
| `/send-cold-email <email>` | Drafts a personalised, compliance-checked cold email and creates a Gmail draft for human review. |
| `/sdr-pipeline <ICP>` | Runs all three stages end-to-end, pausing for confirmation at each step. |
| `lead-scraper` agent | Hybrid sourcing: Clay MCP (primary), web scraping (fallback), CSV import. Applies `lead-qualification` skill. |
| `crm-ingestor` agent | Normalises fields and runs HubSpot upsert. Applies `crm-mapping` skill. |
| `cold-emailer` agent | Writes and validates email drafts. Creates Gmail drafts. Never sends. |
| `lead-qualification` skill | ICP scoring rubric (freshness-checked). Editable references: ICP definition, scoring rubric, disqualifiers. |
| `crm-mapping` skill | HubSpot field mapping + de-dupe policy (freshness-checked). Scripts: normalize_leads.py, hubspot_upsert.py. |
| HubSpot setup UI | `skills/crm-mapping/scripts/setup_ui.py` — secure local web form for pasting your token (served on 127.0.0.1, token never logged). Alternative to `export`. |
| Onboarding preflight | `skills/sdr-orchestrator/scripts/onboarding_check.py` — verifies all System-Layer files are present and surfaces missing credentials/MCP connections as JSON. Runs automatically on first use. |
| `cold-email-writing` skill | Template + tone guide + CAN-SPAM/GDPR rules (freshness-checked). Script: validate_email.py. |
| CRM confirmation hook | `PreToolUse` — asks for approval before every HubSpot write. |
| Qualification gate hook | `PreToolUse` — denies ingest if no qualified leads are present. |
| Email confirmation hook | `PreToolUse` — asks for approval before every Gmail draft. |
| Audit hook | `PostToolUse` — appends every CRM write, email draft, and setup run to an audit log. |
| Version-check hook | `SessionStart` — compares the installed version against GitHub once per session and nudges you if a newer version is available. |

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

**Prefer a guided form?** The setup UI serves a masked input on localhost — the
token is never exposed as a shell argument or written to any log:

```bash
python3 skills/crm-mapping/scripts/setup_ui.py
```

It opens a browser tab on `http://127.0.0.1:<port>`, saves the token to
`~/.claude/sdr-plugin-config.json` (mode 600), and immediately verifies and
provisions the required HubSpot properties.

### 2. Install the plugin

Install straight from GitHub — no need to clone the repo first:

```
claude plugin marketplace add ManishKatheeth/SDR-plugin
claude plugin install sdr-plugin@sdr-tools
```

> Prefer the in-app flow? Run `/plugin marketplace add ManishKatheeth/SDR-plugin`
> inside Claude Code, then `/plugin` → **Discover** → install **sdr-plugin**.

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

## Getting started

Not sure where to begin? Just ask Claude **"how do I set up the SDR plugin"** or
**"what can this plugin do"** — the `sdr-orchestrator` skill walks you through keys,
setup, and which command to use for each goal.

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

## Troubleshooting

Run the onboarding preflight at any time to check plugin health:

```bash
python3 skills/sdr-orchestrator/scripts/onboarding_check.py
```

It prints a JSON object with four keys:

| Key | Meaning |
|---|---|
| `ready` | `true` if all System-Layer files are present. `false` = plugin can't run; restore missing files first. |
| `missing_system_files` | List of absent required files (empty when `ready: true`). |
| `token` | `{ "present": bool, "valid": bool }` — missing token is a warning only; ingest falls back to dry-run. |
| `manual_confirm` | MCP servers (Clay, Gmail) that need to be manually verified as connected. |

The `sdr-orchestrator` skill runs this automatically on first use.

## Version

Plugin version is in `.claude-plugin/plugin.json`. Tag releases with:

```
claude plugin tag .
```
