#!/usr/bin/env bash
# One-time setup for the alignment spike. Run from the repo root:  bash spike/setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "creating .venv"
  python3 -m venv .venv
fi

echo "installing python dependencies"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r spike/requirements.txt

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo
  echo "ffmpeg is not installed. It is required to decode iPhone .mov/.m4a and .mp4."
  echo "  brew install ffmpeg"
fi

echo
.venv/bin/python -m spike.ingest doctor || true

echo
echo "smoke test:  .venv/bin/python -m spike.tier_a --demo"
