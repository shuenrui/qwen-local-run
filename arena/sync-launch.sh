#!/usr/bin/env bash
# arena/sync-launch.sh — launcher for an NVIDIA Sync "Custom Application".
#
# NVIDIA Sync runs this on the DGX Spark, keeps it in the foreground while the
# app is "running", tunnels localhost:<PORT> on your laptop -> :<PORT> on the
# Spark, and sends SIGTERM when you click the ✕ (stop). We start the arena
# server, and on stop we kill it plus any in-flight one-click download
# containers so nothing is orphaned.
#
# The arena backend boots/stops the model servers itself when you click Run
# (on Spark port 8888, internal) — so this is the ONLY app you need in Sync.
set -euo pipefail

REPO="$HOME/Qwen3.8-27B-SGLang-DGX-Spark"
PORT="${ARENA_PORT:-8090}"
cd "$REPO"

SRV_PID=""
cleanup() {
  echo "[arena] stopping..."
  [ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null || true
  # stop any in-flight download containers (one-click downloads) so none orphan
  docker ps --filter "name=arena-dl-" -q 2>/dev/null | xargs -r docker stop >/dev/null 2>&1 || true
  exit 0
}
trap cleanup INT TERM HUP QUIT

echo "[arena] starting server on :$PORT  (repo: $REPO)"
python3 arena/server.py --port "$PORT" &
SRV_PID=$!
echo "[arena] PID $SRV_PID — open http://localhost:$PORT   (stop with the ✕ in NVIDIA Sync)"
wait "$SRV_PID"
