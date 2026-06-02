---
name: cold-email-writing
description: >-
  Write a personalised, CAN-SPAM/GDPR-compliant cold outreach email for a
  specific qualified lead. Use this skill whenever you need to draft a cold
  email — including when running /send-cold-email or /sdr-pipeline. The skill
  re-reads its templates, tone guide, and compliance rules fresh on every run.
  It always produces a draft; it never sends. Output is validated against
  compliance rules before the Gmail draft is created.
---

# Cold Email Writing

Cold email writing turns a lead profile into a short, personalised message that
a human SDR can review, refine, and send from Gmail. The goal is a draft that
feels individually written — not a blast template — and is compliant before it
ever reaches a Gmail draft.

## Freshness — always use the latest rules

These files are edited by the team as templates and compliance requirements
evolve. Re-read all three fresh from disk on every email — never reuse a version
from memory:

- `references/email-templates.md`
- `references/tone-guide.md`
- `references/compliance-rules.md`

## Inputs

1. **Lead profile** — company, industry, contact name, title, recent signals
   (funding, job postings, launches, news).
2. **Context** (optional) — any notes from the qualification step or prior
   conversations.

## Writing process

1. **Select a template** from `references/email-templates.md` based on the lead's
   segment and primary signal (e.g. "recent funding", "scaling sales team",
   "new product").
2. **Personalise the opening line** with one specific, real signal from the lead's
   profile. Never fabricate signals. If no real signal is available, use the
   segment opener from the template.
3. **Write the body** (≤ 150 words). One clear value proposition. One CTA.
   No attachments. No pressure. Per the tone guide.
4. **Draft the subject line** (≤ 60 characters). No clickbait. No all-caps.
5. **Validate** against `references/compliance-rules.md` using `validate_email.py`.
   If validation fails, revise and re-validate (max 2 attempts). After 2 failed
   attempts, return the draft with issues listed rather than blocking.

## Output contract

Return exactly this structure before the Gmail draft is created:

```
## Draft email for <contact name> at <company>

**To:** <email>
**Subject:** <subject line>

---

<email body>

---

**Compliance:** PASS | FAIL — <brief reason if FAIL>
**Personalisation signal:** <the specific signal used in the opening>
**Template used:** <template name from email-templates.md>
```

## Tone guidelines (summary — full detail in references/tone-guide.md)

- First-person, direct, warm. Not salesy.
- No "I hope this email finds you well."
- Lead with the prospect's world, not your product.
- One ask per email. Don't pitch and schedule in the same sentence.
