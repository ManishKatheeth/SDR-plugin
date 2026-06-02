# SDR Plugin — Build Plan

*Saved for future reference. Generated 2026-06-02.*

## Context

This plugin automates the SDR outbound pipeline in three stages:
**find leads → ingest into HubSpot → draft cold emails**. It addresses the
problem that SDR outbound is manual, inconsistent, and risky (un-reviewed emails,
duplicate CRM records, no audit trail).

**Key decisions:**
- **Lead source:** Hybrid — Clay MCP (primary) + web scraping (fallback) + CSV import.
- **Cold email:** Draft + confirm — Gmail draft only, never auto-sends.
- **HubSpot:** REST API via `HUBSPOT_PRIVATE_APP_TOKEN` env var; no HubSpot MCP needed.

---

## Plugin structure

```
SDR-plugin/
├── .claude-plugin/
│   ├── plugin.json              ← manifest (name, version, author, hooks pointer)
│   └── marketplace.json         ← distribution manifest
├── .mcp.json                    ← { "mcpServers": {} }
├── README.md
├── docs/
│   ├── sdr-plugin-plan.md       ← this file
│   └── features.md              ← what was built and why
├── commands/
│   ├── find-leads.md            ← /find-leads <ICP or csv:path>
│   ├── ingest-leads.md          ← /ingest-leads <file>
│   ├── send-cold-email.md       ← /send-cold-email <email>
│   └── sdr-pipeline.md          ← /sdr-pipeline <ICP>
├── agents/
│   ├── lead-scraper.md          ← Clay + WebFetch + CSV; applies lead-qualification
│   ├── crm-ingestor.md          ← normalise + upsert; applies crm-mapping
│   └── cold-emailer.md          ← draft + validate; applies cold-email-writing
├── skills/
│   ├── lead-qualification/
│   │   ├── SKILL.md
│   │   ├── references/{icp-definition.md, scoring-rubric.md, disqualifiers.md}
│   │   ├── scripts/score_leads.py
│   │   └── evals/evals.json
│   ├── crm-mapping/
│   │   ├── SKILL.md
│   │   ├── references/{hubspot-field-map.md, dedupe-policy.md}
│   │   ├── scripts/{normalize_leads.py, hubspot_upsert.py}
│   │   └── evals/evals.json
│   └── cold-email-writing/
│       ├── SKILL.md
│       ├── references/{email-templates.md, tone-guide.md, compliance-rules.md}
│       ├── scripts/validate_email.py
│       └── evals/evals.json
└── hooks/
    ├── hooks.json
    └── scripts/
        ├── guard-crm-write.sh    ← PreToolUse "ask" before HubSpot upsert
        ├── guard-email-send.sh   ← PreToolUse "ask" before Gmail draft
        ├── verify-qualified.py   ← PreToolUse "deny" if no qualified leads
        └── audit-sdr.py          ← PostToolUse append-only JSONL audit
```

---

## Hook design

All hooks follow the `support-plugin` convention:
- `hooks/hooks.json` with `PreToolUse` / `PostToolUse` entries.
- `${CLAUDE_PLUGIN_ROOT}` env var resolves to the plugin root at runtime.
- Scripts exit 0 on all errors (never wedge the user).

| Hook | Event | Matcher | Action |
|---|---|---|---|
| `guard-crm-write.sh` | PreToolUse | Bash + `*hubspot_upsert.py*` | `permissionDecision: "ask"` |
| `verify-qualified.py` | PreToolUse | Bash + `*hubspot_upsert.py*` | `"deny"` if no qualified leads, else `"allow"` |
| `guard-email-send.sh` | PreToolUse | `mcp__claude_ai_Gmail__create_draft` | `"ask"` |
| `audit-sdr.py` | PostToolUse | Bash upsert + Gmail draft | Append to `~/.claude/sdr-plugin-audit.jsonl` |

---

## Skills design (created via skill-creator)

Each skill ships three required elements:

1. **Freshness checks** — SKILL.md instructs agents to re-read all `references/`
   files fresh on every run (pattern from `support-plugin` ticket-triage skill).
2. **Executable scripts** in `scripts/` — deterministic operations (scoring,
   normalisation, HubSpot upsert, compliance validation).
3. **Reference docs** in `references/` — editable by the sales team; changes
   take effect on the next run without code changes.

---

## Verification checklist

1. `ls -R SDR-plugin` — all files present per the tree above.
2. `python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('**/*.json',recursive=True)]"` — all JSON parses cleanly.
3. `python3 score_leads.py --lead '{"company":"Test","employee_count":100,"industry":"SaaS"}' --rubric ...` — returns score JSON.
4. `python3 hubspot_upsert.py --contact '{"email":"test@test.com"}' --dry-run` — prints payload, no API call.
5. `python3 validate_email.py --subject "Test" --body "..."` — returns compliance JSON.
6. `echo '{}' | bash guard-crm-write.sh` — outputs `permissionDecision:"ask"` JSON.
7. `echo '{}' | python3 verify-qualified.py` — outputs `"allow"` (no file) or `"deny"` (empty qualified list).
8. `echo '{}' | python3 audit-sdr.py` — appends one line to `~/.claude/sdr-plugin-audit.jsonl`.
