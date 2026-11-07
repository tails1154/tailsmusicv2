#!/usr/bin/env bash
# TailsMusic v2 installer; safe replacement for the old dialog-based setup.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${EUID}" -ne 0 ]]; then
    echo "Run with sudo: sudo bash setup.sh [--with-kivy] [--service]" >&2
    exit 1
fi
exec python3 "$ROOT/installer.py" "$@"
