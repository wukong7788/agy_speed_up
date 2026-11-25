#!/usr/bin/env python3
"""Inspect or update Antigravity per-project settings/permissionGrants JSON safely."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

PROJECTS_DIR = Path.home() / ".gemini" / "config" / "projects"

ALLOWED_SETTINGS: dict[str, set[str] | type] = {
    "sandboxMode": bool,
    "fileAccessPolicy": {
        "AGENT_SETTING_POLICY_ASK",
        "AGENT_SETTING_POLICY_ALLOW",
        "AGENT_SETTING_POLICY_DENY",
    },
    "internetPolicy": {
        "AGENT_SETTING_POLICY_ASK",
        "AGENT_SETTING_POLICY_ALLOW",
        "AGENT_SETTING_POLICY_DENY",
    },
    "autoExecutionPolicy": {
        "CASCADE_COMMANDS_AUTO_EXECUTION_AUTO",
        "CASCADE_COMMANDS_AUTO_EXECUTION_PROCEED_IN_SANDBOX",
        "CASCADE_COMMANDS_AUTO_EXECUTION_REQUEST_REVIEW",
    },
    "permissionPreset": {
        "AGENT_PERMISSION_PRESET_AUTO",
        "AGENT_PERMISSION_PRESET_DEFAULT",
        "AGENT_PERMISSION_PRESET_REQUEST_REVIEW",
        "AGENT_PERMISSION_PRESET_TURBO",
    },
    "artifactReviewMode": {
        "ARTIFACT_REVIEW_MODE_TURBO",
        "ARTIFACT_REVIEW_MODE_PLAN",
    },
}

PRESETS: dict[str, dict[str, object]] = {
    "auto": {
        "sandboxMode": True,
        "autoExecutionPolicy": "CASCADE_COMMANDS_AUTO_EXECUTION_AUTO",
        "permissionPreset": "AGENT_PERMISSION_PRESET_AUTO",
    },
    "sandbox-auto": {
        "sandboxMode": True,
        "fileAccessPolicy": "AGENT_SETTING_POLICY_ALLOW",
        "autoExecutionPolicy": "CASCADE_COMMANDS_AUTO_EXECUTION_PROCEED_IN_SANDBOX",
        "artifactReviewMode": "ARTIFACT_REVIEW_MODE_TURBO",
    },
}


def find_project_file(repo_path: Path) -> Path | None:
    if not PROJECTS_DIR.is_dir():
        return None
    resolved = repo_path.expanduser().resolve()
    target_uri = f"file://{quote(str(resolved))}"
    raw_uri = f"file://{resolved}"

    for candidate in sorted(PROJECTS_DIR.glob("*.json")):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        resources = data.get("projectResources", {}).get("resources", [])
        for item in resources:
            folder_uri = item.get("gitFolder", {}).get("folderUri", "")
            if folder_uri in {target_uri, raw_uri}:
                return candidate
    return None


def parse_kv(raw: str, force: bool) -> tuple[str, object]:
    if "=" not in raw:
        raise ValueError(f"Expected KEY=VALUE, got: {raw}")
    key, value = raw.split("=", 1)
    key = key.strip()
    value = value.strip()

    spec = ALLOWED_SETTINGS.get(key)
    if spec is None and not force:
        raise ValueError(f"Unsupported setting key '{key}'. Allowed: {sorted(ALLOWED_SETTINGS)} (use --force to override)")

    if spec is bool:
        lowered = value.lower()
        if lowered not in {"true", "false"}:
            raise ValueError(f"Setting '{key}' requires true or false, got: {value}")
        return key, lowered == "true"

    if isinstance(spec, set) and value not in spec and not force:
        raise ValueError(f"Unexpected value '{value}' for '{key}'. Expected one of: {sorted(spec)} (use --force to override)")

    return key, value


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or update Antigravity project config JSON.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--project-dir", help="Repository directory to match in ~/.gemini/config/projects/*.json")
    target.add_argument("--project-file", help="Explicit path to ~/.gemini/config/projects/<id>.json")

    parser.add_argument("--show", action="store_true", help="Print matched file and current config")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Apply a named settings preset")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="Set a settings key")
    parser.add_argument("--copy-grants-from", help="Copy permissionGrants object from a verified sample project JSON")
    parser.add_argument("--force", action="store_true", help="Allow unrecognized keys/enum values")
    parser.add_argument("--apply", action="store_true", help="Write changes to disk (default is dry-run)")
    args = parser.parse_args()

    if args.project_file:
        project_file = Path(args.project_file).expanduser().resolve()
    else:
        matched = find_project_file(Path(args.project_dir))
        if matched is None:
            print(f"No project JSON found under {PROJECTS_DIR} matching {args.project_dir}", file=sys.stderr)
            return 1
        project_file = matched

    if not project_file.is_file():
        print(f"Project file not found: {project_file}", file=sys.stderr)
        return 1

    original = json.loads(project_file.read_text(encoding="utf-8"))
    updated = copy.deepcopy(original)
    settings = updated.setdefault("settings", {})

    changed = False
    if args.preset:
        for k, v in PRESETS[args.preset].items():
            if settings.get(k) != v:
                settings[k] = v
                changed = True

    for item in args.set:
        k, v = parse_kv(item, args.force)
        if settings.get(k) != v:
            settings[k] = v
            changed = True

    if args.copy_grants_from:
        sample_path = Path(args.copy_grants_from).expanduser().resolve()
        sample_data = json.loads(sample_path.read_text(encoding="utf-8"))
        sample_grants = sample_data.get("permissionGrants")
        if not isinstance(sample_grants, dict):
            print(f"Source file has no object 'permissionGrants': {sample_path}", file=sys.stderr)
            return 1
        if updated.get("permissionGrants") != sample_grants:
            updated["permissionGrants"] = copy.deepcopy(sample_grants)
            changed = True

    print(f"Project file: {project_file}")
    if args.show or not changed:
        print(json.dumps(updated, indent=2, ensure_ascii=False))
        return 0

    if not args.apply:
        print("--- DRY RUN (pass --apply to write; .bak backup will be created) ---")
        print(json.dumps(updated, indent=2, ensure_ascii=False))
        return 0

    backup = project_file.with_suffix(".json.bak")
    shutil.copy2(project_file, backup)
    project_file.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Backed up original to: {backup}")
    print(f"Updated: {project_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
