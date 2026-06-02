#!/usr/bin/env python3
"""sdr-plugin: first-run onboarding preflight.

Verifies that every System-Layer component the plugin needs is present on disk, and
reports the state of User-Layer prerequisites (credentials, MCP connections) that the
agent must confirm with the user.

The orchestrator skill runs this before routing the user into any "play". If
``ready`` is false, the agent must enter **onboarding mode**: tell the user exactly what
is missing and stop until it's resolved. A missing System-Layer file is a hard gate; a
missing token is only a warning (ingest falls back to dry-run); MCP connections are
account-level and cannot be inspected from disk, so they surface as ``manual_confirm``.

Resilient by design: any unexpected failure still prints valid JSON and exits 0, so a
quirk in this check never blocks the user.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

# System-Layer files that must exist for the plugin to function. Paths are relative to
# the plugin root. Keep this in sync with DATA_CONTRACT.md.
REQUIRED_FILES = [
    # Commands
    "commands/find-leads.md",
    "commands/ingest-leads.md",
    "commands/send-cold-email.md",
    "commands/sdr-pipeline.md",
    # Agents
    "agents/lead-scraper.md",
    "agents/crm-ingestor.md",
    "agents/cold-emailer.md",
    # Sub-skills
    "skills/lead-qualification/SKILL.md",
    "skills/crm-mapping/SKILL.md",
    "skills/cold-email-writing/SKILL.md",
    # Skill scripts
    "skills/lead-qualification/scripts/score_leads.py",
    "skills/crm-mapping/scripts/_config.py",
    "skills/crm-mapping/scripts/normalize_leads.py",
    "skills/crm-mapping/scripts/hubspot_upsert.py",
    "skills/crm-mapping/scripts/ensure_hubspot_setup.py",
    "skills/crm-mapping/scripts/setup_ui.py",
    "skills/cold-email-writing/scripts/validate_email.py",
    # Reference files (User Layer, but their absence breaks a play)
    "skills/lead-qualification/references/icp-definition.md",
    "skills/lead-qualification/references/scoring-rubric.md",
    "skills/lead-qualification/references/disqualifiers.md",
    "skills/crm-mapping/references/hubspot-field-map.md",
    "skills/crm-mapping/references/dedupe-policy.md",
    "skills/crm-mapping/references/custom-properties.json",
    "skills/cold-email-writing/references/email-templates.md",
    "skills/cold-email-writing/references/tone-guide.md",
    "skills/cold-email-writing/references/compliance-rules.md",
    # Hooks
    "hooks/hooks.json",
    "hooks/scripts/guard-crm-write.sh",
    "hooks/scripts/verify-qualified.py",
    "hooks/scripts/guard-email-send.sh",
    "hooks/scripts/audit-sdr.py",
    "hooks/scripts/check-version.py",
    # Manifests
    ".claude-plugin/plugin.json",
]

# Account-level MCP connections — not inspectable from disk; the agent must confirm.
MCP_SERVERS = [
    {"name": "Clay", "used_by": "/find-leads (primary lead sourcing)"},
    {"name": "Gmail", "used_by": "/send-cold-email (creates drafts, never sends)"},
]


def plugin_root() -> Path:
    """Resolve the plugin root from CLAUDE_PLUGIN_ROOT, falling back to this file's tree."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env_root:
        return Path(env_root)
    # scripts/onboarding_check.py -> skills/sdr-orchestrator -> <root>
    return Path(__file__).resolve().parents[3]


def check_token(root: Path) -> dict:
    """Report token presence/validity, reusing the crm-mapping bootstrap when available."""
    # Resolve via _config so tokens saved by setup_ui.py are visible here too.
    try:
        sys.path.insert(0, str(root / "skills" / "crm-mapping" / "scripts"))
        from _config import resolve_token  # noqa: PLC0415
        present = bool(resolve_token())
    except Exception:
        present = bool(os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN"))
    result = {"present": present, "valid": None}

    ensure = root / "skills" / "crm-mapping" / "scripts" / "ensure_hubspot_setup.py"
    if present and ensure.exists():
        try:
            proc = subprocess.run(
                [sys.executable, str(ensure), "--dry-run"],
                capture_output=True, text=True, timeout=10,
            )
            # ensure_hubspot_setup.py prints JSON with token_valid on its dry-run path.
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        if "token_valid" in data:
                            result["valid"] = bool(data["token_valid"])
                            break
                    except Exception:
                        continue
        except Exception:
            pass  # leave valid as None — couldn't determine
    return result


def main() -> None:
    try:
        root = plugin_root()

        missing = [rel for rel in REQUIRED_FILES if not (root / rel).exists()]
        token = check_token(root)

        warnings = []
        if not token["present"]:
            warnings.append(
                "No HubSpot token found — /ingest-leads will run in dry-run mode (no CRM "
                "writes). Run /setup-hubspot or set HUBSPOT_PRIVATE_APP_TOKEN to enable "
                "live upserts."
            )
        elif token["valid"] is False:
            warnings.append(
                "HubSpot token is set but appears invalid — run /setup-hubspot to re-enter it."
            )

        manual_confirm = [
            f"Confirm the {m['name']} MCP server is connected at the account level "
            f"({m['used_by']})."
            for m in MCP_SERVERS
        ]

        ready = len(missing) == 0  # token/MCP are not hard gates

        result = {
            "ready": ready,
            "plugin_root": str(root),
            "missing_system_files": missing,
            "token": token,
            "warnings": warnings,
            "manual_confirm": manual_confirm,
            "note": (
                "Version freshness is reported separately by the SessionStart hook "
                "hooks/scripts/check-version.py."
            ),
        }
        print(json.dumps(result, indent=2))
    except Exception as exc:  # never block onboarding on our own failure
        print(json.dumps({
            "ready": None,
            "error": f"onboarding_check failed: {exc}",
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
