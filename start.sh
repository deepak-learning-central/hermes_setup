#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh'
  echo 'Then reopen your shell and run: bash start.sh'
  exit 1
fi
uv sync --frozen --no-dev
printf '\nHermes setup: http://localhost:8765\nFrom your laptop, open an SSH tunnel (see README.md).\nKeep this terminal open during setup. Ctrl+C stops the setup page; Hermes keeps running.\n\n'
exec uv run --no-sync hermes-setup web --host 127.0.0.1 --port 8765
