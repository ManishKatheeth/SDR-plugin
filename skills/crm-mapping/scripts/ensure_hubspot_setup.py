#!/usr/bin/env python3
"""Verify the HubSpot token and auto-provision required custom properties.

Run this once before the first ingest. On success it writes a marker file
(~/.claude/sdr-plugin-setup.json keyed by portalId) so subsequent runs skip
all API calls — pass --force to re-check regardless.

Usage:
  python3 ensure_hubspot_setup.py [--force] [--marker <path>] [--dry-run]

Exits 0 always; result is printed as JSON to stdout.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import resolve_token  # noqa: E402

HUBSPOT_API = "https://api.hubapi.com"
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "references" / "custom-properties.json"
DEFAULT_MARKER = Path.home() / ".claude" / "sdr-plugin-setup.json"


def make_request(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    url = f"{HUBSPOT_API}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
        except Exception:
            detail = {"raw": body}
        return e.code, {"error": f"HTTP {e.code}", "detail": detail}


def verify_token(token: str) -> tuple[bool, dict]:
    status, body = make_request("GET", "/account-info/v3/details", token)
    if status == 200:
        return True, body
    return False, body


def get_existing_properties(object_type: str, token: str) -> set[str]:
    status, body = make_request("GET", f"/crm/v3/properties/{object_type}", token)
    if status != 200:
        return set()
    return {p["name"] for p in body.get("results", [])}


def create_property(object_type: str, prop: dict, token: str) -> dict:
    payload = {
        "name": prop["name"],
        "label": prop["label"],
        "type": prop["type"],
        "fieldType": prop["fieldType"],
        "groupName": prop["groupName"],
    }
    status, body = make_request("POST", f"/crm/v3/properties/{object_type}", token, payload)
    if status in (200, 201):
        return {"status": "created"}
    return {"status": "failed", "error": body}


def load_config() -> list[dict]:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return []


def read_marker(marker_path: Path) -> dict | None:
    try:
        return json.loads(marker_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_marker(marker_path: Path, portal_id: str, property_results: dict) -> None:
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "portalId": portal_id,
        "provisioned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "properties": property_results,
    }
    marker_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="Re-check even if marker exists")
    p.add_argument("--dry-run", action="store_true", help="Verify token only; do not create properties")
    default_marker = os.environ.get("SDR_PLUGIN_SETUP_MARKER", str(DEFAULT_MARKER))
    p.add_argument("--marker", default=default_marker, help="Path to the marker file")
    return p.parse_args()


def main():
    args = parse_args()
    marker_path = Path(args.marker)

    token = resolve_token()
    if not token:
        print(json.dumps({
            "token_present": False,
            "mode": "dry-run",
            "message": "No HubSpot token found — run /setup-hubspot to add one. "
                       "Ingest will run in dry-run mode until then.",
        }))
        sys.exit(0)

    token_valid, account_info = verify_token(token)
    if not token_valid:
        print(json.dumps({
            "token_present": True,
            "token_valid": False,
            "error": account_info,
            "message": "HubSpot rejected the token — run /setup-hubspot to re-enter it.",
        }))
        sys.exit(0)

    portal_id = str(account_info.get("portalId", ""))

    if not args.force:
        marker = read_marker(marker_path)
        if marker and marker.get("portalId") == portal_id:
            print(json.dumps({
                "token_present": True,
                "token_valid": True,
                "portalId": portal_id,
                "status": "already-provisioned",
                "provisioned_at": marker.get("provisioned_at"),
                "message": "Custom properties already provisioned. Pass --force to re-check.",
            }))
            sys.exit(0)

    required_props = load_config()
    if not required_props:
        print(json.dumps({
            "token_present": True,
            "token_valid": True,
            "portalId": portal_id,
            "status": "error",
            "message": f"Could not load custom-properties.json from {CONFIG_PATH}",
        }))
        sys.exit(0)

    if args.dry_run:
        print(json.dumps({
            "token_present": True,
            "token_valid": True,
            "portalId": portal_id,
            "mode": "dry-run",
            "properties_to_provision": [p["name"] for p in required_props],
            "message": "Dry-run: token verified. Remove --dry-run to create properties.",
        }))
        sys.exit(0)

    # Group required properties by objectType and check which already exist.
    by_type: dict[str, list[dict]] = {}
    for prop in required_props:
        by_type.setdefault(prop["objectType"], []).append(prop)

    property_results: dict[str, dict] = {}
    for object_type, props in by_type.items():
        existing = get_existing_properties(object_type, token)
        for prop in props:
            name = prop["name"]
            if name in existing:
                property_results[name] = {"status": "existing", "objectType": object_type}
            else:
                result = create_property(object_type, prop, token)
                result["objectType"] = object_type
                property_results[name] = result

    all_ok = all(r["status"] in ("existing", "created") for r in property_results.values())
    if all_ok:
        write_marker(marker_path, portal_id, property_results)

    print(json.dumps({
        "token_present": True,
        "token_valid": True,
        "portalId": portal_id,
        "status": "provisioned" if all_ok else "partial",
        "properties": property_results,
        "marker_written": all_ok,
        "message": "Custom properties provisioned." if all_ok
                   else "Some properties could not be created — see 'properties' for details.",
    }, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
