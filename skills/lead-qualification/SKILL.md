---
name: lead-qualification
description: >-
  Score and qualify a prospective lead against the organisation's ICP (Ideal
  Customer Profile). Use this skill whenever you need to decide whether a
  company or contact is worth pursuing — including when sourcing leads from Clay,
  web scraping, or CSV import, or when someone asks "is this a good lead?",
  "does this company fit our ICP?", or runs /find-leads. The skill re-reads its
  ICP, rubric, and disqualifiers fresh on every run so edits to those files take
  effect immediately.
---

# Lead Qualification

Lead qualification turns a raw prospect into a binary decision — **pursue or
skip** — plus a numeric score and a one-line reason. The goal is a fast,
consistent signal the scraper can use to filter leads before any human reviews
them.

## Freshness — always use the latest rules

The files below are **edited by the sales team** as your ICP evolves. Re-read
all three fresh from disk on every qualification run — never act on a version
you remember from an earlier session:

- `references/icp-definition.md`
- `references/scoring-rubric.md`
- `references/disqualifiers.md`

If what you remember conflicts with what's in the file, **the file wins.**

## Inputs

1. **Lead data** — company name, domain, industry, employee count, funding stage,
   HQ country, primary contact name, title, email.
2. **Optional signals** — recent funding, job postings, product launches, tech
   stack, news mentions.

## Scoring process

1. Read `references/icp-definition.md` to load the current ICP (target segment,
   employee range, industries, geographies, funding stages, titles).
2. Read `references/scoring-rubric.md` to load the point weights per signal.
3. Score the lead by summing the applicable weights. Max possible score is 100.
4. Read `references/disqualifiers.md`. If any hard disqualifier matches
   (competitor, blacklisted domain, wrong geography mandate), mark the lead
   `disqualified` regardless of score.
5. Compare the score to the qualification threshold in `icp-definition.md`.
   A lead is `qualified: true` if score ≥ threshold AND no disqualifier hit.

## Output contract

Return exactly this structure for each lead:

```json
{
  "company": "<name>",
  "domain": "<domain>",
  "contact": {
    "name": "<name>",
    "title": "<title>",
    "email": "<email>"
  },
  "score": <0-100>,
  "qualified": true | false,
  "reason": "<one sentence: top positive signal or disqualifier that decided the call>",
  "signals": ["<signal 1>", "<signal 2>"]
}
```

If a required field is missing (no email, no employee count), note it in
`reason` and score the available signals only — don't fabricate missing data.

## Confidence calibration

- **High** — multiple strong ICP signals present, no missing critical fields.
- **Medium** — most signals present; 1–2 key fields missing (e.g. no headcount).
- **Low** — sparse data; score is an estimate. Flag to human for manual review.
