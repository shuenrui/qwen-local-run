#!/usr/bin/env bash
# One-command check for the directory: validate, link-rot, build, and (if a
# Playwright venv exists) browser verification against a local serve.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== validate =="
python3 validate.py

echo "== link rot =="
python3 check_links.py --quiet && echo "all source URLs reachable"

echo "== build =="
python3 build.py

PW=/tmp/pwenv
if [ ! -x "$PW/bin/python" ] && [ -x tools/.pwenv/bin/python ]; then
  PW=tools/.pwenv
fi
if [ -x "$PW/bin/python" ]; then
  echo "== browser verify (local serve) =="
  python3 -m http.server 8849 --bind 127.0.0.1 --directory site &
  SRV=$!
  trap 'kill $SRV 2>/dev/null || true' EXIT
  sleep 2
  "$PW/bin/python" verify_browser.py http://127.0.0.1:8849/
else
  echo "== browser verify skipped: no Playwright venv (tools/install_verify_env.sh) =="
fi

echo "== done =="
