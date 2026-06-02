#!/usr/bin/env python3
"""Validate a cold email draft against CAN-SPAM / GDPR compliance rules.

Usage:
  python3 validate_email.py --subject "Your subject" \
                             --body "Email body text" \
                             --compliance path/to/compliance-rules.md

Prints a JSON result with passed/failed status and a list of issues.
Exits 0 always.
"""
import argparse
import json
import re
import sys


SPAM_TRIGGER_WORDS = [
    "free", "guaranteed", "no risk", "act now", "limited time",
    "winner", "prize", "click here", "buy now", "urgent", "congratulations!",
    "100% free", "make money",
]

OPT_OUT_PHRASES = [
    "unsubscribe", "opt out", "opt-out", "reply stop", "remove me",
    "to be removed", "no longer receive",
]

CTA_PHRASES = [
    "?", "worth a call", "15 minutes", "20 minutes", "happy to", "let me know",
    "open to", "can i", "would you", "schedule",
]


def check_subject(subject: str) -> list[str]:
    issues = []
    if len(subject) > 60:
        issues.append(f"Subject too long: {len(subject)} chars (max 60)")
    if "!" in subject:
        issues.append("Subject contains exclamation mark")
    if re.search(r"\b(Re:|Fwd:)", subject, re.I):
        issues.append("Subject uses deceptive Re: or Fwd: prefix")
    if subject == subject.upper() and len(subject) > 5:
        issues.append("Subject is all-caps")
    return issues


def check_body(body: str) -> list[str]:
    issues = []
    word_count = len(body.split())
    if word_count > 300:
        issues.append(f"Body too long: {word_count} words (max 300)")

    body_lower = body.lower()

    for word in SPAM_TRIGGER_WORDS:
        if word in body_lower:
            issues.append(f"Spam trigger word found: '{word}'")

    # Check all-caps words (allow acronyms ≤ 4 chars like CRM, SaaS)
    all_caps_words = re.findall(r"\b[A-Z]{5,}\b", body)
    if all_caps_words:
        issues.append(f"ALL-CAPS words found: {', '.join(set(all_caps_words))}")

    has_opt_out = any(phrase in body_lower for phrase in OPT_OUT_PHRASES)
    if not has_opt_out:
        issues.append("Missing opt-out / unsubscribe mechanism")

    has_cta = any(phrase in body_lower for phrase in CTA_PHRASES)
    if not has_cta:
        issues.append("No clear CTA found")

    return issues


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--compliance", required=False, help="Path to compliance-rules.md (unused by script; checked by agent)")
    return p.parse_args()


def main():
    args = parse_args()
    issues = []
    issues.extend(check_subject(args.subject))
    issues.extend(check_body(args.body))

    result = {
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "subject_length": len(args.subject),
        "body_word_count": len(args.body.split()),
    }
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
