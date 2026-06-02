#!/usr/bin/env python3
"""Normalize qualified-leads.json to the HubSpot contact/company schema.

Usage:
  python3 normalize_leads.py --input ./qualified-leads.json \
                              --field-map path/to/hubspot-field-map.md \
                              --output ./normalized-leads.json

Reads qualified leads (qualified: true only), applies field transforms, and
writes normalized-leads.json. Exits 0 always; errors are included in output.
"""
import argparse
import json
import re
import sys
from pathlib import Path


INDUSTRY_MAP = {
    "saas": "COMPUTER_SOFTWARE",
    "cloud": "COMPUTER_SOFTWARE",
    "software": "COMPUTER_SOFTWARE",
    "martech": "MARKETING_AND_ADVERTISING",
    "salestech": "COMPUTER_SOFTWARE",
    "fintech": "FINANCIAL_SERVICES",
    "b2b": "INFORMATION_TECHNOLOGY_AND_SERVICES",
    "enterprise": "INFORMATION_TECHNOLOGY_AND_SERVICES",
}


def title_case(s: str) -> str:
    return s.strip().title() if s else ""


def normalize_domain(domain: str) -> str:
    return re.sub(r"^www\.", "", domain.lower().strip()) if domain else ""


def split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "").strip().split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def map_industry(industry: str) -> str:
    lower = (industry or "").lower()
    for key, val in INDUSTRY_MAP.items():
        if key in lower:
            return val
    return "OTHER"


def normalize_contact(lead: dict) -> dict:
    contact = lead.get("contact") or {}
    email = (contact.get("email") or lead.get("email") or "").lower().strip()
    full_name = contact.get("name") or lead.get("contact_name") or ""
    firstname, lastname = split_name(full_name)

    return {
        "email": email,
        "firstname": title_case(firstname),
        "lastname": title_case(lastname),
        "jobtitle": (contact.get("title") or lead.get("title") or "").strip(),
        "hs_linkedin_bio": contact.get("linkedin_url") or "",
        "lead_score": lead.get("score", 0),
        "lead_qualification_reason": lead.get("reason", ""),
        "lifecyclestage": "lead",
        "hs_lead_status": "new",
        "lead_source": "sdr-plugin",
    }


def normalize_company(lead: dict) -> dict:
    industry_raw = lead.get("industry") or ""
    return {
        "name": title_case(lead.get("company") or ""),
        "domain": normalize_domain(lead.get("domain") or ""),
        "industry": map_industry(industry_raw),
        "numberofemployees": lead.get("employee_count") or None,
        "hs_funding_stage": title_case(lead.get("funding_stage") or ""),
        "country": (lead.get("country") or lead.get("hq_country") or "").upper()[:2] or None,
        "recent_funding_round": bool(lead.get("recent_funding")),
    }


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--field-map", required=True)
    p.add_argument("--output", default="./normalized-leads.json")
    return p.parse_args()


def main():
    args = parse_args()
    try:
        leads = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"error": f"Could not read input: {e}"}))
        sys.exit(0)

    qualified = [l for l in leads if l.get("qualified") is True]
    normalized = []
    for lead in qualified:
        try:
            normalized.append({
                "source_lead": lead,
                "contact": normalize_contact(lead),
                "company": normalize_company(lead),
            })
        except Exception as e:
            normalized.append({
                "source_lead": lead,
                "error": str(e),
            })

    Path(args.output).write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    print(f"Normalized {len(normalized)} qualified leads → {args.output}")
    sys.exit(0)


if __name__ == "__main__":
    main()
