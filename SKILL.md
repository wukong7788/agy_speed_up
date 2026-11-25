---
name: agy-speed-up
description: Diagnose and accelerate Google Antigravity (AGY) workflows by eliminating unnecessary BypassSandbox waits, adding token-threshold /compact reminder hooks, managing JSON permission files, and keeping context lean. Use when the user asks why AGY is slow, wants to speed up git/terminal execution in sandbox, set up compact reminders, or replicate these optimizations on another machine.
---

# AGY Speed Up

Playbook and reusable automation for making Google Antigravity (`Antigravity 2.0` / IDE / `agy` CLI) noticeably faster across machines.

## Quick Setup on a Machine

Run the bundled installer script [install.sh](./scripts/install.sh):

```bash
# 1. Install global macOS CLT git rule + symlink skill into ~/.gemini/config/skills/
bash /path/to/agy_speed_up/scripts/install.sh --global-rule --link-skill

# 2. Install the /compact threshold reminder hook into a specific project
bash /path/to/agy_speed_up/scripts/install.sh --project-hook /path/to/repo

# Optional: install the /compact hook globally (~/.gemini/config/hooks.json) instead
bash /path/to/agy_speed_up/scripts/install.sh --global-hook
```

---

## 1. Eliminate 50s+ `BypassSandbox` Waits on Local `git` (macOS)

- **Root cause**: `/usr/bin/git` is an `xcrun` shim that tries to read `/var/db/xcode_select_link`. Inside the default terminal sandbox this fails with `Operation not permitted`, causing the agent to fall back to `BypassSandbox: true` (waiting ~30–60s+ for manual approval).
- **Fix**: Invoke `/Library/Developer/CommandLineTools/usr/bin/git` directly inside the sandbox for local commands (`status`, `diff`, `log`, `show`, `branch`, `rev-parse`, `add`, `commit`, `restore`, `switch`). Keep `BypassSandbox: true` only for network commands (`push`, `fetch`, `pull`, `clone`).
- **Global rule**: Installed at `~/.gemini/config/rules/antigravity-sandbox-git-rules.md` (with required `trigger: always_on` YAML frontmatter) by `--global-rule`.

---

## 2. Token-Threshold `/compact` Reminder Hook

Long contexts (`350k–500k+` tokens) sharply increase per-turn model thinking time (often ~40–60s even for small steps).

- **Mechanism**: Uses Antigravity's `PreInvocation` hook (`invocationNum == 0`, [hooks.json schema](./scripts/compact-reminder.py)) to inspect the latest `PLANNER_RESPONSE` in `transcriptPath` (`input_tokens + cache_read_tokens`).
- **CLI companion (`v1.5.15+`)**: In `agy` CLI, you can also set `AGY_CLI_AUTO_COMPACT_OVERRIDE` (e.g., `250K`, `700000`, `80%`) and inspect the active threshold in `/context`.
- **Zero model overhead**: Returns `systemMessage: ""` with `metadata.user_markdown`, displaying an inline UI banner to the user without adding prompt tokens or triggering an extra model call.
- **Recommended thresholds**:
  - `AGY_COMPACT_WARN_TOKENS=250000` (default `250k` — sweet spot before KV-cache/reasoning latency balloons)
  - `AGY_COMPACT_REPEAT_STEP_TOKENS=100000` (escalates at `350k`, `450k`, ...)
  - `AGY_COMPACT_REMIND_EVERY_TURN=1` (optional: remind on every user prompt above threshold)
- **Files**:
  - [compact-reminder.sh](./scripts/compact-reminder.sh)
  - [compact-reminder.py](./scripts/compact-reminder.py)

---

## 3. File-Based Permissions & Command Auto-Approval

You do not have to click every setting in the UI; Antigravity persists settings and grants in JSON files (`~/.gemini/config/projects/<project-id>.json`, `~/.gemini/config/config.json`, `~/.gemini/antigravity-cli/settings.json`).

- See [config-and-permissions.md](./references/config-and-permissions.md) for exact paths, observed project JSON schemas, system-protection boundaries, and how to write prefix-matchable commands for "Always Allow".
- Use [configure-project-permissions.py](./scripts/configure-project-permissions.py) from an external shell or setup agent to locate a repo's project JSON, update `settings`, or clone verified `permissionGrants` from a golden project template (dry-run by default; creates `.json.bak` on `--apply`):

```bash
# Inspect current project config
python3 -B /path/to/agy_speed_up/scripts/configure-project-permissions.py --project-dir /path/to/repo --show

# Preview updating settings (dry-run; add --apply to write)
python3 -B /path/to/agy_speed_up/scripts/configure-project-permissions.py \
  --project-dir /path/to/repo \
  --preset auto \
  --set fileAccessPolicy=AGENT_SETTING_POLICY_ALLOW

# Clone verified v2 permissionGrants from a golden project file
python3 -B /path/to/agy_speed_up/scripts/configure-project-permissions.py \
  --project-dir /path/to/repo \
  --copy-grants-from /path/to/golden-project.json \
  --apply
```

---

## 4. Latency Diagnosis (`transcript.jsonl`)

When a step feels slow, compare timestamps (`created_at`) and token counts (`input_tokens + cache_read_tokens`) across consecutive steps in the conversation's `.system_generated/logs/transcript.jsonl`:

1. **Gap between `PLANNER_RESPONSE` (`BypassSandbox: true`) and tool completion (`GENERIC`)**: Approval + unsandboxed execution wait.
2. **Gap between `GENERIC` tool result and next `PLANNER_RESPONSE`**: Model thinking + prompt prefill time (scales strongly with `input_tokens + cache_read_tokens`).
3. **Rule of thumb**: Run `/compact` right after finishing a review/fix/commit milestone, or whenever context crosses `250k` tokens.
