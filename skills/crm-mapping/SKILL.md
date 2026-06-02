---
name: crm-mapping
description: >-
  Map qualified lead data to the HubSpot contact/company schema, de-duplicate
  against existing CRM records, and upsert via the HubSpot REST API. Use this
  skill whenever you need to push leads into HubSpot — including when running
  /ingest-leads or /sdr-pipeline. The skill re-reads its field map and de-dupe
  policy fresh on every run so schema changes take effect immediately without
  code changes.
---

# CRM Mapping

CRM mapping turns a qualified lead (from `qualified-leads.json`) into a clean
HubSpot record — correctly mapped, de-duplicated, and upserted with the right
lifecycle stage and owner assignment.

## Freshness — always use the latest rules

The files below are edited when the HubSpot schema or de-dupe policy changes.
Re-read both fresh from disk on every ingest run — never act on a remembered
version:

- `references/hubspot-field-map.md`
- `references/dedupe-policy.md`

## First-run environment setup

Before normalization, run the bootstrap check once per HubSpot portal:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/crm-mapping/scripts/ensure_hubspot_setup.py"
```

This script:
1. Checks that `HUBSPOT_PRIVATE_APP_TOKEN` is set — if not, reports `token_present: false`
   and the ingest continues in dry-run mode.
2. Validates the token with a lightweight `GET /account-info/v3/details` call.
3. Reads `references/custom-properties.json` (the canonical list of required custom
   properties) and creates any that don't yet exist in the portal.
4. Writes a marker file (`~/.claude/sdr-plugin-setup.json`, keyed by `portalId`)
   so subsequent runs skip all provisioning API calls — pass `--force` to re-check.

If the token is absent the ingest still proceeds in dry-run mode (no HubSpot writes),
consistent with existing behavior.

The required custom properties are defined in `references/custom-properties.json`.
Edit that file to add or change properties — no code changes required.

## Normalization

1. Load `references/hubspot-field-map.md` to understand which lead fields map to
   which HubSpot contact and company properties.
2. For each qualified lead, apply the mapping:
   - Lead `company` → HubSpot company `name`
   - Lead `domain` → HubSpot company `domain` and contact `company` association
   - Lead `contact.email` → HubSpot contact `email` (primary identifier for de-dupe)
   - Lead `contact.name` → split to `firstname` + `lastname`
   - Lead `contact.title` → HubSpot contact `jobtitle`
   - Lead `employee_count` → HubSpot company `numberofemployees`
   - Lead `funding_stage` → HubSpot company `hs_funding_stage` (custom property)
   - Lead `score` → HubSpot contact `lead_score` (custom property)
   - Lead `reason` → HubSpot contact `lead_qualification_reason` (custom property)
3. Set default values for required fields not present in the lead:
   - `lifecyclestage` → `lead`
   - `hs_lead_status` → `new`
   - `lead_source` → `sdr-plugin`

## De-duplication

Before upserting, check `references/dedupe-policy.md` for the current rules.
The default de-dupe approach:

1. Search HubSpot for an existing contact with the same email. If found → `update`.
2. If no email match, search by domain for an existing company. If the company
   exists and there is a contact with the same name → `update`.
3. If neither match → `upsert` (create new contact + company association).
4. If the contact or domain is on the opt-out list → `skip`.

## Output contract (per lead)

```json
{
  "status": "upserted" | "updated" | "skipped" | "failed",
  "hubspot_contact_id": "<id or null>",
  "hubspot_company_id": "<id or null>",
  "reason": "<one-line: why this status>",
  "payload": { "<hubspot fields mapped>" }
}
```

## Reference files

- `references/hubspot-field-map.md` — source field → HubSpot property name, type,
  and any required transformation (e.g. title-case, domain strip).
- `references/dedupe-policy.md` — the de-dupe order of operations and edge cases
  (duplicate emails, company merges, opt-out handling).
