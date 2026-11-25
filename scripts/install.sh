#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GLOBAL_CONFIG_DIR="${HOME}/.gemini/config"

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Options:
  --global-rule               Install macOS CLT git sandbox rule into ~/.gemini/config/rules/
  --project-hook <repo_dir>   Install /compact reminder hook into <repo_dir>/.agents/
  --global-hook               Install /compact reminder hook into ~/.gemini/config/
  --link-skill [skills_dir]   Symlink this skill into skills_dir (default: ~/.gemini/config/skills)
  --all                       Equivalent to --global-rule --link-skill --global-hook
  -h, --help                  Show this help
EOF
}

install_global_rule() {
  local rules_dir="${GLOBAL_CONFIG_DIR}/rules"
  mkdir -p "${rules_dir}"
  cat > "${rules_dir}/antigravity-sandbox-git-rules.md" <<'EOF'
---
trigger: always_on
description: Use macOS CommandLineTools git inside the terminal sandbox to avoid xcrun /var/db/xcode_select_link permission delays.
---

# Sandbox Git Fast Path (macOS)

On macOS, `/usr/bin/git` is an `xcrun` shim that reads `/var/db/xcode_select_link`, which fails inside the default sandbox (`Operation not permitted`) and forces slow `BypassSandbox: true` approvals.

- Before using `BypassSandbox: true` for local non-network `git` commands (`status`, `diff`, `log`, `show`, `branch`, `rev-parse`, `add`, `commit`, `restore`, `switch`), run them inside the default sandbox (`BypassSandbox: false`) using `/Library/Developer/CommandLineTools/usr/bin/git` when that binary exists (keep the `rtk` prefix: e.g. `rtk /Library/Developer/CommandLineTools/usr/bin/git status -sb`).
- Reserve `BypassSandbox: true` for network `git` operations (`push`, `fetch`, `pull`, `clone`, `ls-remote`) or when `/Library/Developer/CommandLineTools/usr/bin/git` is unavailable.
EOF
  echo "Installed global rule: ${rules_dir}/antigravity-sandbox-git-rules.md"
  echo "  - Scope: Global (all projects in Antigravity App, IDE, and agy CLI)"
  echo "  - Trigger: always_on (YAML frontmatter included)"
  echo "  - Configured: Use /Library/Developer/CommandLineTools/usr/bin/git inside sandbox for local git commands; reserve BypassSandbox for network git operations"
}

resolve_python() {
  local candidate
  for candidate in \
    "/opt/homebrew/bin/python3" \
    "/opt/homebrew/opt/python@3.12/libexec/bin/python3" \
    "/usr/local/bin/python3" \
    "/Library/Developer/CommandLineTools/usr/bin/python3"
  do
    if [ -x "${candidate}" ]; then
      echo "${candidate}"
      return 0
    fi
  done
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  echo "python3 is required to update hooks.json" >&2
  return 1
}

merge_hooks_json() {
  local hooks_json="$1"
  local python_bin
  python_bin="$(resolve_python)"
  "${python_bin}" - "$hooks_json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = {}
if path.is_file():
    raw = path.read_text(encoding="utf-8").strip()
    if raw:
        data = json.loads(raw)

data["compact-threshold-reminder"] = {
    "PreInvocation": [
        {
            "type": "command",
            "command": "./hooks/compact-reminder.sh",
            "timeout": 5,
        }
    ]
}
path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

install_hook_into() {
  local root_dir="$1"
  local scope_label="$2"
  mkdir -p "${root_dir}/hooks"
  cp "${SKILL_DIR}/scripts/compact-reminder.sh" "${root_dir}/hooks/compact-reminder.sh"
  cp "${SKILL_DIR}/scripts/compact-reminder.py" "${root_dir}/hooks/compact-reminder.py"
  chmod +x "${root_dir}/hooks/compact-reminder.sh" "${root_dir}/hooks/compact-reminder.py"
  merge_hooks_json "${root_dir}/hooks.json"
  echo "Installed compact-threshold-reminder hook into: ${root_dir}"
  echo "  - Scope: ${scope_label}"
  echo "  - Hook config: ${root_dir}/hooks.json (key: compact-threshold-reminder, event: PreInvocation)"
  echo "  - Scripts: ${root_dir}/hooks/compact-reminder.sh, ${root_dir}/hooks/compact-reminder.py"
  echo "  - Defaults: warn at 250k tokens (AGY_COMPACT_WARN_TOKENS), repeat every +100k (AGY_COMPACT_REPEAT_STEP_TOKENS)"
}

link_skill() {
  local target_dir="${1:-${GLOBAL_CONFIG_DIR}/skills}"
  mkdir -p "${target_dir}"
  ln -sfn "${SKILL_DIR}" "${target_dir}/agy_speed_up"
  echo "Linked skill: ${target_dir}/agy_speed_up -> ${SKILL_DIR}"
  echo "  - Scope: Skill directory (${target_dir}; ~/.gemini/config/skills applies to App, IDE, and agy CLI)"
  echo "  - Skill: agy-speed-up (SKILL.md, references/, scripts/)"
}

if [ $# -eq 0 ]; then
  usage
  exit 1
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --global-rule)
      install_global_rule
      shift
      ;;
    --project-hook)
      [ $# -ge 2 ] || { echo "Missing <repo_dir> for --project-hook" >&2; exit 1; }
      install_hook_into "$2/.agents" "Project ($2)"
      shift 2
      ;;
    --global-hook)
      install_hook_into "${GLOBAL_CONFIG_DIR}" "Global (all projects)"
      shift
      ;;
    --link-skill)
      if [ $# -ge 2 ] && [[ "$2" != --* ]]; then
        link_skill "$2"
        shift 2
      else
        link_skill "${GLOBAL_CONFIG_DIR}/skills"
        shift
      fi
      ;;
    --all)
      install_global_rule
      link_skill "${GLOBAL_CONFIG_DIR}/skills"
      install_hook_into "${GLOBAL_CONFIG_DIR}" "Global (all projects)"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done
