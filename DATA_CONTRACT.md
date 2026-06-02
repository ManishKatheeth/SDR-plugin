# SDR Plugin — Data Contract

This plugin separates every file and resource into two layers. The split exists so an
agent (or a new teammate) knows, at a glance, **what is safe to change and what is
human-owned data that must be left alone**.

> **The rule in one line:**
> **System Layer = the plugin's code/logic — edit it freely to improve the plugin.**
> **User Layer = credentials, tuning data, and outputs — treat as read-only; read it,
> never silently rewrite, overwrite, or delete it. Touch it only when the user explicitly
> asks you to.**

When in doubt, a file is User Layer.

---

## User Layer — human-owned (do **not** silently edit)

These belong to the user / sales team. The agent reads them (often *fresh on every run*)
but must never rewrite, reformat, or delete them on its own initiative. Edit only on an
explicit, specific request from the user.

| Path / resource | What it is | Agent may edit? |
|---|---|---|
| `HUBSPOT_PRIVATE_APP_TOKEN` (env / `.env`) | HubSpot credential. Absent → ingest runs in dry-run. | ❌ Never. Only tell the user how to set it. |
| Clay MCP, Gmail MCP (account-level connections) | External service connections. | ❌ Cannot and must not edit; ask the user to connect. |
| `skills/lead-qualification/references/icp-definition.md` | Target segment & qualification threshold. | ❌ Only when explicitly asked. Read fresh every run. |
| `skills/lead-qualification/references/scoring-rubric.md` | Point weights per signal. | ❌ Only when explicitly asked. Read fresh every run. |
| `skills/lead-qualification/references/disqualifiers.md` | Hard-stop rules. | ❌ Only when explicitly asked. Read fresh every run. |
| `skills/crm-mapping/references/hubspot-field-map.md` | Lead field → HubSpot property mapping. | ❌ Only when explicitly asked. Read fresh every run. |
| `skills/crm-mapping/references/dedupe-policy.md` | De-dupe order of operations. | ❌ Only when explicitly asked. Read fresh every run. |
| `skills/crm-mapping/references/custom-properties.json` | Canonical list of required HubSpot custom properties. | ❌ Only when explicitly asked. Read fresh every run. |
| `skills/cold-email-writing/references/email-templates.md` | Outreach templates per segment. | ❌ Only when explicitly asked. Read fresh every run. |
| `skills/cold-email-writing/references/tone-guide.md` | Voice, style, CTA rules. | ❌ Only when explicitly asked. Read fresh every run. |
| `skills/cold-email-writing/references/compliance-rules.md` | CAN-SPAM / GDPR checklist. | ❌ Only when explicitly asked. Read fresh every run. |
| `qualified-leads.json` (working dir) | Output of `/find-leads`; user-confirmed lead set. | ❌ Generated/owned data — don't hand-edit. |
| `normalized-leads.json` (working dir) | Output of `normalize_leads.py`. | ❌ Generated/owned data — don't hand-edit. |
| `~/.claude/sdr-plugin-audit.jsonl` | Append-only audit log of every CRM write & draft. | ❌ Never. Append-only by `audit-sdr.py`. |
| `~/.claude/sdr-plugin-setup.json` | Per-portal setup marker (skip re-provisioning). | ❌ Managed by `ensure_hubspot_setup.py`. |

> **Why reference files are User Layer even though they're meant to be edited:** they're
> tuned by the *humans* on the sales team to change plugin behavior, and they're re-read
> fresh on every run (the "freshness principle"). The agent's job is to *honor* them as the
> current source of truth — not to rewrite them unless the user asks for that specific edit.

---

## System Layer — plugin code/logic (safe to edit)

These implement how the plugin works. Edit them to fix bugs, add capability, or improve
behavior — the normal target of development work.

| Path | What it is |
|---|---|
| `skills/sdr-orchestrator/SKILL.md` | Control-tower entry point / router. |
| `skills/sdr-orchestrator/scripts/onboarding_check.py` | First-run preflight check. |
| `skills/lead-qualification/SKILL.md` | Lead scoring/qualification logic. |
| `skills/crm-mapping/SKILL.md` | HubSpot mapping & de-dupe logic. |
| `skills/cold-email-writing/SKILL.md` | Email drafting & compliance logic. |
| `skills/lead-qualification/scripts/score_leads.py` | Scoring script. |
| `skills/crm-mapping/scripts/{normalize_leads.py, hubspot_upsert.py, ensure_hubspot_setup.py, setup_ui.py, _config.py}` | CRM ingestion scripts. |
| `skills/cold-email-writing/scripts/validate_email.py` | Compliance validator. |
| `commands/{find-leads.md, ingest-leads.md, send-cold-email.md, sdr-pipeline.md}` | Slash-command definitions. |
| `agents/{lead-scraper.md, crm-ingestor.md, cold-emailer.md}` | Sub-agent definitions. |
| `hooks/hooks.json` | Hook wiring. |
| `hooks/scripts/{guard-crm-write.sh, verify-qualified.py, guard-email-send.sh, audit-sdr.py, check-version.py}` | Hook implementations. |
| `.claude-plugin/{plugin.json, marketplace.json}` | Plugin & marketplace manifests. |
| `.mcp.json` | MCP server wiring (project-level). |
| `README.md`, `docs/*`, `DATA_CONTRACT.md` | Documentation. |

---

## Quick test

Before editing any file, ask: *"If I overwrite this, does the user lose data, credentials,
or a tuning choice they made?"* If yes → **User Layer, leave it alone**. If it's plugin
logic you'd ship to every user → **System Layer, safe to edit**.
