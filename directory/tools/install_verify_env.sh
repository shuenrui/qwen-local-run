#!/usr/bin/env bash
# Create the Playwright environment used by verify_browser.py, inside the repo
# at tools/.pwenv (gitignored). /tmp/pwenv works too but does not survive a
# reboot; this is the reproducible path.
set -euo pipefail
cd "$(dirname "$0")"
VENV=.pwenv
if [ -x "$VENV/bin/python" ]; then
  echo "$VENV already exists"
else
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet playwright
  "$VENV/bin/playwright" install chromium
  echo "created $VENV with Playwright + Chromium"
fi
echo "verify with: $VENV/bin/python verify_browser.py [URL]"
