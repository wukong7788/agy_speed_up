#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/compact-reminder.py"

for candidate in \
  "/opt/homebrew/bin/python3" \
  "/opt/homebrew/opt/python@3.12/libexec/bin/python3" \
  "/usr/local/bin/python3" \
  "/Library/Developer/CommandLineTools/usr/bin/python3"
do
  if [ -x "$candidate" ]; then
    exec "$candidate" "$PY_SCRIPT"
  fi
done

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$PY_SCRIPT"
fi

printf '{}\n'
