#!/usr/bin/env python3
"""Score a lead against the ICP rubric and return a structured qualification result.

Usage:
  python3 score_leads.py --lead '{"company":"Acme","domain":"acme.com",...}' \
                         --rubric path/to/scoring-rubric.md

Exits 0 always; qualification result is printed as JSON to stdout.
"""
import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class QualificationResult:
    company: str
    domain: str
    score: int
    qualified: bool
    reason: str
    signals: list


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--lead", required=True, help="Lead JSON string")
    p.add_argument("--rubric", required=True, help="Path to scoring-rubric.md")
    p.add_argument("--threshold", type=int, default=60, help="Qualification threshold")
    return p.parse_args()


def load_rubric_weights(rubric_path: str) -> dict:
    """Parse point values from the rubric markdown table rows."""
    weights = {}
    try:
        with open(rubric_path, encoding="utf-8") as f:
            for line in f:
                # Match table rows: | Signal description | N |
                m = re.match(r"\|\s*(.+?)\s*\|\s*(-?\d+)\s*\|", line)
                if m:
                    weights[m.group(1).lower()] = int(m.group(2))
    except FileNotFoundError:
        pass
    return weights


def score_lead(lead: dict, weights: dict) -> tuple[int, list]:
    """Apply rubric weights to lead data. Returns (score, matched_signals)."""
    score = 0
    signals = []

    emp = lead.get("employee_count", 0) or 0
    if 50 <= emp <= 500:
        score += weights.get("employee count in target range (50–500)", 20)
        signals.append(f"employee count {emp} in target range")
    elif 20 <= emp <= 1000:
        score += weights.get("employee count adjacent (20–49 or 501–1000)", 10)
        signals.append(f"employee count {emp} adjacent to target range")

    stage = (lead.get("funding_stage") or "").lower()
    if any(s in stage for s in ["series a", "series b", "series c"]):
        score += weights.get("funding stage matches target (series a/b/c)", 20)
        signals.append(f"funding stage: {stage}")
    elif "seed" in stage:
        score += weights.get("seed stage (strong early signal)", 12)
        signals.append("seed-stage company")

    industry = (lead.get("industry") or "").lower()
    target_industries = ["saas", "cloud", "software", "martech", "salestech"]
    if any(i in industry for i in target_industries):
        score += weights.get("industry matches target list", 15)
        signals.append(f"industry: {industry}")
    elif any(i in industry for i in ["b2b", "enterprise"]):
        score += weights.get("adjacent industry (b2b, enterprise software)", 8)
        signals.append(f"adjacent industry: {industry}")

    country = (lead.get("country") or lead.get("hq_country") or "").lower()
    if any(c in country for c in ["united states", "us", "canada", "united kingdom", "uk"]):
        score += weights.get("hq in target geography (us/ca/uk)", 10)
        signals.append(f"HQ in {country}")
    elif any(c in country for c in ["eu", "europe", "australia"]):
        score += weights.get("hq in secondary geography (eu, au)", 5)
        signals.append(f"HQ in secondary geo: {country}")

    title = (lead.get("contact", {}).get("title") or lead.get("title") or "").lower()
    target_titles = ["vp of sales", "vp sales", "head of sales", "cro", "chief revenue"]
    close_titles = ["director of rev ops", "director of sales", "revenue operations"]
    if any(t in title for t in target_titles):
        score += weights.get("contact holds a target title (vp sales, cro, etc.)", 15)
        signals.append(f"target title: {title}")
    elif any(t in title for t in close_titles) or "founder" in title or "ceo" in title:
        score += weights.get("contact holds a close title (director of rev ops, etc.)", 8)
        signals.append(f"close title: {title}")

    email = lead.get("contact", {}).get("email") or lead.get("email") or ""
    personal_domains = ["gmail.com", "hotmail.com", "yahoo.com", "outlook.com"]
    if email and not any(pd in email for pd in personal_domains) and email:
        score += weights.get("work email available (not personal / catch-all)", 10)
        signals.append("work email available")
    elif not email:
        score += weights.get("no email found for primary contact", -10)
        signals.append("no email found")

    # Bonus signals
    if lead.get("recent_funding"):
        score += weights.get("funding round in last 6 months", 10)
        signals.append("recent funding round")

    if lead.get("open_sales_roles", 0) >= 3:
        score += weights.get("3+ open sales/sdr roles", 8)
        signals.append("3+ open sales roles")

    if lead.get("recent_launch"):
        score += weights.get("new product launch / market expansion in last 90 days", 5)
        signals.append("recent product launch")

    return max(0, score), signals


def main():
    args = parse_args()
    try:
        lead = json.loads(args.lead)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid lead JSON: {e}"}))
        sys.exit(0)

    weights = load_rubric_weights(args.rubric)
    score, signals = score_lead(lead, weights)

    qualified = score >= args.threshold
    if signals:
        reason = signals[0] if qualified else f"score {score} below threshold {args.threshold}"
    else:
        reason = "insufficient data to score"

    result = QualificationResult(
        company=lead.get("company", ""),
        domain=lead.get("domain", ""),
        score=score,
        qualified=qualified,
        reason=reason,
        signals=signals,
    )
    print(json.dumps(asdict(result), indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
