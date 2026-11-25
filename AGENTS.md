# AGENTS.md

Instructions for AI coding agents working in the `agy_speed_up` repository.

## Repository Purpose & Layout

`agy_speed_up` is an Antigravity Skill + helper script bundle for diagnosing and reducing agent latency across Antigravity App, Antigravity IDE, and `agy` CLI.

- `SKILL.md`: Skill entrypoint (`name: agy-speed-up`); keep concise and aligned with script CLI flags and paths.
- `references/config-and-permissions.md`: Reference for `~/.gemini/config/` and `~/.gemini/antigravity-cli/` schemas, sandbox mounts, and command prefix-matching rules.
- `scripts/install.sh`: Installer for global rule (`--global-rule`), skill symlink (`--link-skill`), and `/compact` hook (`--project-hook`, `--global-hook`, `--all`).
- `scripts/compact-reminder.sh` / `scripts/compact-reminder.py`: `PreInvocation` hook reading `transcriptPath` tail (`PLANNER_RESPONSE`) and emitting `user_markdown` warnings.
- `scripts/configure-project-permissions.py`: External-terminal utility to inspect/update `~/.gemini/config/projects/<id>.json` safely.

## Antigravity Platform Constraints

- **Rules frontmatter**: Any rule file written into `~/.gemini/config/rules/*.md` or `.agents/rules/*.md` **must** start with YAML frontmatter containing a valid `trigger` (`always_on`, `model_decision`, `glob`, or `manual`); files in `rules/` without frontmatter are silently discarded by Antigravity. Standalone `AGENTS.md` / `GEMINI.md` files must **not** use frontmatter.
- **System-protected config files**: Do not attempt to edit `~/.gemini/config/config.json` or `~/.gemini/config/projects/*.json` from inside a sandboxed agent session (`Operation not permitted` / system protection boundary). Changes to those files via `configure-project-permissions.py` are intended to be run by the user in an external shell.
- **Hook context hygiene**: Keep `compact-reminder.py` zero-model-overhead (`systemMessage: ""` with `metadata.user_markdown`) and deduplicated; injected `systemMessage` steps persist in conversation history.
- **macOS sandbox `git` fast-path**: `/usr/bin/git` is an `xcrun` shim that reads `/var/db/xcode_select_link` and fails inside the macOS sandbox. If running local `git` commands inside the sandbox, invoke `/Library/Developer/CommandLineTools/usr/bin/git` directly (note: this directory may not yet be initialized as a git repository).

## Coding Conventions

- **Python scripts** (`scripts/*.py`): Use Python 3 standard library only (no third-party packages). Always preserve `python3 -B` compatibility, clean CLI `--help`, and safe defaults:
  - Hooks (`compact-reminder.py`) must always exit `0` and print `{}` on invalid input or missing files so they never block an agent turn.
  - Permission editors (`configure-project-permissions.py`) must stay **dry-run by default** and create a `.json.bak` backup before writing on `--apply`. Do not invent undocumented `permissionGrants` keys.
- **Shell scripts** (`scripts/*.sh`): `install.sh` uses `#!/usr/bin/env bash` with `set -euo pipefail`. Keep `compact-reminder.sh` POSIX/bash-safe with graceful fallback to `{}` if `python3` is missing, and preserve executable permissions (`chmod +x`) on scripts under `scripts/`.
- **Docs**: Keep `README.md`, `CHANGELOG.md`, `SKILL.md`, and `references/` in sync whenever flags, environment variables, file paths, or Antigravity version behaviors change.

## Verification Commands

Run syntax and smoke checks inside the sandbox after modifying scripts:

```bash
# Shell syntax check
bash -n scripts/install.sh scripts/compact-reminder.sh

# Python syntax / bytecode check (without writing __pycache__)
python3 -B -m py_compile scripts/compact-reminder.py scripts/configure-project-permissions.py

# CLI help smoke checks
bash scripts/install.sh --help
python3 -B scripts/configure-project-permissions.py --help

# Hook contract smoke check (must return valid JSON and exit 0)
printf '%s\n' '{"hookEventName":"PreInvocation","invocationNum":0,"lastUserInput":"hello","transcriptPath":""}' | bash scripts/compact-reminder.sh
```
