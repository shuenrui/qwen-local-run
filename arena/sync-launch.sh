#!/usr/bin/env bash
# arena/sync-launch.sh — launcher for an NVIDIA Sync "Custom Application".
#
# NVIDIA Sync runs this on the DGX Spark, keeps it in the foreground while the
# app is "running", tunnels localhost:<PORT> on your laptop -> :<PORT> on the
# Spark, and sends SIGTERM when you click the ✕ (stop).
#
# Reuse-first: if an arena server is ALREADY listening on <PORT> (e.g. started
# manually or left detached), this script does not start a second one and does
# not kill the external one on stop — it just rides the tunnel until that
# server goes away. Otherwise it starts the server itself and stops it (plus
# any in-flight download containers) on exit.
set -euo pipefail

REPO="$HOME/Qwen3.8-27B-SGLang-DGX-Spark"
PORT="${ARENA_PORT:-8090}"
cd "$REPO"

SRV_PID=""
cleanup() {
  if [ -n "$SRV_PID" ]; then
    echo "[arena] stopping our server..."
    kill "$SRV_PID" 2>/dev/null || true
    docker ps --filter "name=arena-dl-" -q 2>/dev/null | xargs -r docker stop >/dev/null 2>&1 || true
  fi
  exit 0
}
trap cleanup INT TERM HUP QUIT

healthy() { curl -sf -m 3 "http://127.0.0.1:$PORT/api/models" >/dev/null 2>&1; }

if healthy; then
  echo "[arena] reusing server already listening on :$PORT (tunnel only)"
  while healthy; do sleep 5; done
  echo "[arena] external server went away; exiting"
  exit 0
fi

echo "[arena] starting server on :$PORT  (repo: $REPO)"
python3 arena/server.py --port "$PORT" &
SRV_PID=$!
echo "[arena] PID $SRV_PID — open http://localhost:$PORT   (stop with the ✕ in NVIDIA Sync)"
wait "$SRV_PID"
