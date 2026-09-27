#!/usr/bin/env bash
set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Run this script from inside the TailsMusic repository." >&2
    exit 1
fi

if [[ "${1:-}" == "--push" ]]; then
    PUSH_AFTER_COMMIT=1
    shift
else
    PUSH_AFTER_COMMIT=0
fi

if [[ $# -gt 0 ]]; then
    COMMIT_MESSAGE="$*"
else
    read -r -p "Commit message: " COMMIT_MESSAGE
fi

if [[ -z "$COMMIT_MESSAGE" ]]; then
    echo "A commit message is required." >&2
    exit 1
fi

echo "Running Ruff..."
uvx ruff check --output-format=github

echo "Compiling Python modules..."
python3 -m compileall -q player.py tools.py wifi.py hotspot.py portal apps

echo "Checking whitespace..."
git diff --check

git add -A
if git diff --cached --quiet; then
    echo "No changes to commit."
    exit 0
fi

git commit -m "$COMMIT_MESSAGE"

if [[ "$PUSH_AFTER_COMMIT" == "1" ]]; then
    git push
else
    echo "Committed locally. Use '$0 --push' to publish it."
fi
