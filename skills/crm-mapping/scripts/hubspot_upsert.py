#!/usr/bin/env python3
"""Upsert a single normalized lead into HubSpot via the REST API.

Usage:
  python3 hubspot_upsert.py --contact '{"email":"...","firstname":"..."}' \
                             --company '{"name":"...","domain":"..."}' \
                             [--dry-run]

Requires HUBSPOT_PRIVATE_APP_TOKEN environment variable unless --dry-run is set.
Exits 0 always; result is printed as JSON to stdout.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import resolve_token  # noqa: E402

HUBSPOT_API = "https://api.hubapi.com"


def make_request(method: str, path: str, payload: dict, token: str) -> dict:
    url = f"{HUBSPOT_API}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}", "detail": body}


def search_contact(email: str, token: str) -> str | None:
    resp = make_request("POST", "/crm/v3/objects/contacts/search", {
        "filterGroups": [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}],
        "properties": ["email", "firstname", "lastname"],
    }, token)
    results = resp.get("results", [])
    return results[0]["id"] if results else None


def search_company(domain: str, token: str) -> str | None:
    resp = make_request("POST", "/crm/v3/objects/companies/search", {
        "filterGroups": [{"filters": [{"propertyName": "domain", "operator": "EQ", "value": domain}]}],
        "properties": ["domain", "name"],
    }, token)
    results = resp.get("results", [])
    return results[0]["id"] if results else None


def upsert_contact(contact: dict, company_id: str | None, token: str, dry_run: bool) -> dict:
    email = contact.get("email", "")
    if dry_run:
        return {"status": "dry-run", "payload": contact, "company_id": company_id}

    existing_id = search_contact(email, token)
    if existing_id:
        resp = make_request("PATCH", f"/crm/v3/objects/contacts/{existing_id}", {"properties": contact}, token)
        return {"status": "updated", "hubspot_contact_id": existing_id, "response": resp}
    else:
        resp = make_request("POST", "/crm/v3/objects/contacts", {"properties": contact}, token)
        new_id = resp.get("id")
        if new_id and company_id:
            make_request("PUT", f"/crm/v3/objects/contacts/{new_id}/associations/companies/{company_id}/contact_to_company", {}, token)
        return {"status": "upserted", "hubspot_contact_id": new_id, "response": resp}


def upsert_company(company: dict, token: str, dry_run: bool) -> dict:
    domain = company.get("domain", "")
    if dry_run:
        return {"status": "dry-run", "payload": company}

    existing_id = search_company(domain, token)
    if existing_id:
        make_request("PATCH", f"/crm/v3/objects/companies/{existing_id}", {"properties": company}, token)
        return {"status": "updated", "hubspot_company_id": existing_id}
    else:
        resp = make_request("POST", "/crm/v3/objects/companies", {"properties": company}, token)
        return {"status": "upserted", "hubspot_company_id": resp.get("id"), "response": resp}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--contact", required=True, help="Contact JSON")
    p.add_argument("--company", default="{}", help="Company JSON")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    token = resolve_token()
    dry_run = args.dry_run or not token

    if not token and not args.dry_run:
        print(json.dumps({"warning": "No HubSpot token found — run /setup-hubspot. Running in dry-run mode."}))

    try:
        contact = json.loads(args.contact)
        company = json.loads(args.company)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(0)

    company_result = upsert_company(company, token, dry_run)
    company_id = company_result.get("hubspot_company_id")

    contact_result = upsert_contact(contact, company_id, token, dry_run)

    output = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": dry_run,
        "contact": contact_result,
        "company": company_result,
    }
    print(json.dumps(output, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
