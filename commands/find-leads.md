---
description: Source and qualify leads from Clay MCP, web scraping, or a CSV file, filtered against the current ICP.
argument-hint: "<ICP segment or 'csv:<path>'> (e.g. 'B2B SaaS companies 50-200 employees' or 'csv:/path/to/leads.csv')"
---

# /find-leads $1

Find and qualify leads matching **$1**. Sourcing is automatic; **no data is
written anywhere during this stage** — the output is a local `qualified-leads.json`
file you confirm before the next step.

## Steps

1. **Validate input.** If `$1` is empty, ask for an ICP description or CSV path and
   stop. A CSV path must start with `csv:` followed by a readable file path.

2. **Delegate to `lead-scraper`.** Pass `$1` as the sourcing target. The agent will:
   - Re-read `skills/lead-qualification/references/` fresh before scoring.
   - Source leads from Clay MCP (primary), web scraping (fallback), or CSV import,
     depending on the input type and what Clay returns.
   - Score and qualify each lead against the current ICP rubric.
   - Write results to `./qualified-leads.json` in the working directory.

3. **Present a summary.** Show:
   - Total candidates sourced vs. leads that passed qualification.
   - Top 5 qualified leads (company, contact, score, reason).
   - Any leads that were borderline (score within 5 pts of the threshold).

4. **Ask for confirmation.** Prompt: "Proceed to CRM ingestion with these
   N leads? (yes / filter / no)"
   - **no** → stop; the file stays on disk for review.
   - **filter** → let the user remove specific leads by name or index, then
     re-present the summary.
   - **yes** → report the file path and suggest running `/ingest-leads ./qualified-leads.json`.

## Notes

- Clay is the preferred source; web scraping is a fallback for companies Clay
  doesn't cover. Respect robots.txt.
- The ICP and scoring rubric live in editable reference files — edit them to tune
  what counts as a qualified lead without touching this command.
- Never auto-proceed to ingest; the human confirms the qualified set first.
