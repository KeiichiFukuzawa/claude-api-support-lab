#!/usr/bin/env bash
# One-step setup for macOS and Linux.
#
#   bash scripts/setup.sh
#
# It finds Python 3.11 or newer, makes .venv, installs the project,
# runs the mock tests, and sends one free request with a fake key (401).
# It never asks for your API key.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

step() { printf '\n== %s ==\n' "$1"; }

is_new_enough() {
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

find_python() {
  local cmd
  for cmd in python3.14 python3.13 python3.12 python3.11 python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    if command -v "$cmd" >/dev/null 2>&1 && is_new_enough "$cmd"; then
      command -v "$cmd"
      return 0
    fi
  done
  return 1
}

step "1/4 Find Python 3.11 or newer"
if ! PY="$(find_python)"; then
  echo "Python 3.11 or newer was not found."
  echo "The Python that comes with macOS (3.9) is too old for this project. Keep it; do not remove it."
  echo "Install the latest Python from https://www.python.org/downloads/ , then run this script again."
  if command -v open >/dev/null 2>&1; then
    open "https://www.python.org/downloads/"
  fi
  exit 1
fi
echo "Using $PY ($("$PY" --version))"

step "2/4 Make .venv and install"
if [ -x .venv/bin/python ] && ! is_new_enough .venv/bin/python; then
  echo "The old .venv uses an old Python. Making a new one."
  rm -rf .venv
fi
if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -e ".[dev]"
echo "Installed."

step "3/4 Run the mock tests (no API calls, free)"
.venv/bin/python -m pytest -q

step "4/4 Send one request with a fake key (expect 401, free)"
# Exit code 1 is the expected result here (an API error), so do not stop on it.
set +e
.venv/bin/python -m src.diagnose --scenario bad-key --no-log
code=$?
set -e
if [ "$code" -ne 1 ]; then
  echo "Unexpected result (exit code $code). Check your network and try again."
  exit 1
fi

cat <<EOF

Setup finished.
Next time, you do not need to activate anything. Use the lab command:

  $ROOT/scripts/lab test
  $ROOT/scripts/lab practice
  $ROOT/scripts/lab diagnose --scenario bad-model
  $ROOT/scripts/lab escalate

Requests that use your own key need ANTHROPIC_API_KEY in the same terminal:

  export ANTHROPIC_API_KEY="your key here"
EOF
