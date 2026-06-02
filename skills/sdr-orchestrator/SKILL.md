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

## Data contract — User Layer vs System Layer

Before editing anything, know which layer a file belongs to. This protects the
user's data and tuning choices from being clobbered by well-meaning edits.

| Layer | What's in it | Your stance |
|---|---|---|
| **User Layer** (human-owned data) | Credentials (`HUBSPOT_PRIVATE_APP_TOKEN`, `.env`), MCP connections (Clay, Gmail), tunable reference files (`skills/*/references/*`), outputs (`qualified-leads.json`, `normalized-leads.json`), audit/state (`~/.claude/sdr-plugin-audit.jsonl`, `~/.claude/sdr-plugin-setup.json`) | **Read it, never silently rewrite it.** Reference files are read *fresh every run* and edited only when the user explicitly asks for that specific change. |
| **System Layer** (plugin code/logic) | `skills/*/SKILL.md`, `skills/*/scripts/*.py`, `commands/*.md`, `agents/*.md`, `hooks/hooks.json`, `hooks/scripts/*`, `.claude-plugin/*`, `.mcp.json`, docs | **Safe to edit** to fix or improve the plugin. |

The one-line test: *if overwriting a file would lose the user's data, credentials,
or a tuning choice, it's User Layer — leave it alone.* Full per-file breakdown is in
[`DATA_CONTRACT.md`](../../DATA_CONTRACT.md) at the repo root.

## First-run onboarding — verify before you route

On a first run, or whenever the user is setting up / something isn't working, **run
the preflight check before starting any play**:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/sdr-orchestrator/scripts/onboarding_check.py"
```

It prints JSON: `ready`, `missing_system_files`, `token`, `warnings`, `manual_confirm`.
Walk the result top to bottom:

1. **`ready: false` → enter onboarding mode.** One or more System-Layer files are
   missing (listed in `missing_system_files`). The plugin can't run reliably. Tell the
   user exactly which files are missing and ask them to restore/reinstall them (e.g.
   re-run `claude plugin update sdr-plugin`, or restore from source). **Do not start any
   Play until a re-run reports `ready: true`.** This is a hard gate.

2. **Token (`token.present` / `token.valid`).** A missing token is **not** a blocker —
   `/ingest-leads` falls back to safe **dry-run** (normalizes + de-dupes, prints the
   payload, no API call). If the user wants live CRM writes, have them set it:
   ```bash
   export HUBSPOT_PRIVATE_APP_TOKEN=pat-na1-...
   ```
   (shell profile or `.env`). If `token.valid` is `false`, the token is wrong — ask
   them to re-check it. You do **not** need to create the custom HubSpot properties
   (`lead_score`, `lead_qualification_reason`, `hs_funding_stage`,
   `recent_funding_round`) — they're auto-provisioned on the first `/ingest-leads` run
   by `skills/crm-mapping/scripts/ensure_hubspot_setup.py`.

3. **`manual_confirm` (MCP servers).** Clay and Gmail are connected at the *account*
   level and can't be inspected from disk. Ask the user to confirm each is connected:
   - **Clay MCP** — primary lead sourcing for `/find-leads`.
   - **Gmail MCP** — draft creation for `/send-cold-email` (never sends).
   If a server the user needs for their goal isn't connected, treat that as onboarding:
   ask them to connect it before running that play.

**Verify HubSpot without writing anything** (deeper than the preflight — validates the
token live and lists the properties it would ensure, making no changes):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/crm-mapping/scripts/ensure_hubspot_setup.py" --dry-run
```

Only once the System-Layer checks pass and the user has what their goal needs should
you move on to the Plays.

## Staying up to date

A `SessionStart` hook (`hooks/scripts/check-version.py`) compares the installed
version against the latest on GitHub once per session and nudges you if you're behind.
To check on demand at any time, run it directly:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check-version.py"
```

To update:

```bash
claude plugin marketplace update sdr-tools
claude plugin update sdr-plugin
```

If you're running from a clone of the source repo, `git pull` instead.

## Plugin inventory — your index to the repo

A concise map of every component so you can route without re-deriving the tree. Paths
are relative to the plugin root (`${CLAUDE_PLUGIN_ROOT}`).

**Commands** (`commands/`)
| Command | Does | File |
|---|---|---|
| `/find-leads <ICP or csv:path>` | Source + qualify leads → `qualified-leads.json` | `find-leads.md` |
| `/ingest-leads <file>` | Normalize, de-dupe, upsert to HubSpot (dry-run w/o token) | `ingest-leads.md` |
| `/send-cold-email <email>` | Draft a compliant cold email as a Gmail draft | `send-cold-email.md` |
| `/sdr-pipeline <ICP>` | Run all three stages end-to-end, confirming each step | `sdr-pipeline.md` |

**Agents** (`agents/`)
| Agent | Role | File |
|---|---|---|
| `lead-scraper` | Clay/web/CSV sourcing + qualification scoring | `lead-scraper.md` |
| `crm-ingestor` | Field normalization + HubSpot upsert | `crm-ingestor.md` |
| `cold-emailer` | Draft + validate email; create Gmail draft (never sends) | `cold-emailer.md` |

**Sub-skills** (`skills/`)
| Skill | Owns | References (User Layer, read fresh) | Scripts |
|---|---|---|---|
| `lead-qualification` | ICP scoring rubric | `icp-definition.md`, `scoring-rubric.md`, `disqualifiers.md` | `score_leads.py` |
| `crm-mapping` | HubSpot mapping + de-dupe | `hubspot-field-map.md`, `dedupe-policy.md`, `custom-properties.json` | `ensure_hubspot_setup.py`, `normalize_leads.py`, `hubspot_upsert.py`, `setup_ui.py`, `_config.py` |
| `cold-email-writing` | Templates + tone + compliance | `email-templates.md`, `tone-guide.md`, `compliance-rules.md` | `validate_email.py` |
| `sdr-orchestrator` | This router | — | `onboarding_check.py` |

**Hooks** (`hooks/`, wired in `hooks.json`)
| Hook | Event | Guards |
|---|---|---|
| `check-version.py` | SessionStart | Update nudge |
| `guard-crm-write.sh` | PreToolUse (`hubspot_upsert.py`) | Confirm before CRM write |
| `verify-qualified.py` | PreToolUse (`hubspot_upsert.py`) | Deny ingest if no `qualified: true` leads |
| `guard-email-send.sh` | PreToolUse (Gmail `create_draft`) | Confirm before draft |
| `audit-sdr.py` | PostToolUse (upserts, setup, drafts) | Append audit log line |

**MCP servers** (account-level connections, not in `.mcp.json`)
| Server | Used by |
|---|---|
| Clay | `/find-leads` — primary lead sourcing |
| Gmail | `/send-cold-email` — draft creation only |

**Tools used:** `Bash` (run the scripts above), `Read`/`Write`/`Edit` (files & outputs),
`WebFetch` (lead-scraper web fallback), and the Clay/Gmail MCP tools.

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

## Safety model (recap)

Every irreversible action is gated and logged — this is by design, not an error:

- **CRM-write guard** + **qualification gate** before HubSpot upserts.
- **Gmail-draft guard** before any draft is created.
- **Audit log** appends one JSON line per CRM write, email draft, and setup run to
  `~/.claude/sdr-plugin-audit.jsonl` (override with `$SDR_PLUGIN_AUDIT_LOG`).

See `README.md` for the full safety + audit details, and `DATA_CONTRACT.md` for the
full User/System layer breakdown.
