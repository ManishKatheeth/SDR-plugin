# Compliance Rules (CAN-SPAM / GDPR)

Hard requirements for every outbound email. The validate_email.py script checks
these automatically. The cold-email-writing skill re-reads this file fresh on
every run. Update this file when legal or compliance requirements change.

## CAN-SPAM requirements (US)

All outbound commercial email must:

1. **Identify as an advertisement** — if it's a first cold contact, the email
   is commercial by nature; do not misrepresent the relationship.
2. **Include a physical address** — the sender's physical mailing address must
   be present in the email or in a footer. Add it to every template.
3. **Include a clear opt-out mechanism** — every email must contain an
   unsubscribe link or a clear instruction ("Reply 'unsubscribe' to be removed").
4. **Honor opt-out requests promptly** — any contact who unsubscribes must be
   added to the suppression list before the next send.
5. **No deceptive subject lines** — the subject must reflect the content of
   the email. Do not use "Re:" or "Fwd:" to fake a prior thread.
6. **No misleading headers** — the From name and domain must correctly identify
   the sender.

## GDPR requirements (EU/UK contacts)

For any contact with an EU or UK email or company address:

1. **Legitimate interest basis** — B2B cold email to corporate contacts is
   generally permitted under legitimate interest. Personal email addresses
   (gmail, yahoo, etc.) are not covered by legitimate interest.
2. **No sensitive personal data** — do not reference health, religion, political
   views, or other special-category data in the email.
3. **Right to erasure** — include an opt-out / unsubscribe mechanism. Honor
   requests within 72 hours.
4. **Data minimisation** — don't include more personal data in the email than
   necessary to make the ask.

## Validation checklist (checked by validate_email.py)

- [ ] Subject line ≤ 60 characters
- [ ] Body ≤ 300 words
- [ ] Contains a CTA (question mark or call-to-action phrase)
- [ ] Contains opt-out text ("unsubscribe", "opt out", "remove", or "reply STOP")
- [ ] No spam trigger words: "free", "guaranteed", "no risk", "act now",
      "limited time", "winner", "prize", "click here", "buy now"
- [ ] No ALL-CAPS words (beyond acronyms like CRM, SaaS, CEO)
- [ ] No deceptive "Re:" or "Fwd:" in subject if it's a cold email
- [ ] Subject line does not contain exclamation marks

## Physical address placeholder

Add your company's registered address to every email template footer:

```
[Your Company Name] · [Street Address] · [City, State, ZIP] · Unsubscribe
```

Update this in `email-templates.md` before sending.
