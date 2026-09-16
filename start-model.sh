#!/usr/bin/env bash
# start-model.sh — generic launcher for the A/B harness.
# Usage: PROFILE=profiles/qwen3.6-35b-a3b.env ./start-model.sh [mtp|dspark]
#   mtp    -> ./start.sh (EAGLE/MTP, works for both models)
#   dspark -> ./start-dspark.sh (Qwen3.8-27B only; draft is model-specific)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="${PROFILE:-profiles/qwen3.8-27b.env}"
MODE="${1:-mtp}"

if [[ ! -f "${SCRIPT_DIR}/${PROFILE}" && ! -f "${PROFILE}" ]]; then
  echo "profile not found: ${PROFILE}"; exit 1
fi
# Resolve relative to repo root.
[[ -f "${SCRIPT_DIR}/${PROFILE}" ]] && PROFILE="${SCRIPT_DIR}/${PROFILE}"

# Load profile: shell env wins, profile fills gaps (same rule as start.sh/.env).
while IFS='=' read -r key value || [[ -n "${key}" ]]; do
  key="${key%$'\r'}"; value="${value%$'\r'}"
  key="${key#"${key%%[![:space:]]*}"}"; key="${key%"${key##*[![:space:]]}"}"
  [[ -z "${key}" || "${key}" == \#* ]] && continue
  if [[ -z "${!key:-}" ]]; then export "${key}=${value}"; fi
done < "${PROFILE}"

echo "profile: ${PROFILE}"
echo "model: ${MODEL_ID:-?} served=${SERVED_MODEL_NAME:-?} img=${IMAGE:-?} mem=${MEM_FRACTION_STATIC:-?}"

# vLLM lanes (Flash-Next, Albond 122B) need their own repos' launchers —
# this starter only speaks SGLang. Boot them manually, then benchmark with
# bench/ab.py --only <name> (manual mode) or the UI with auto OFF.
if [[ "${ENGINE:-sglang}" == "vllm" ]]; then
  echo "MANUAL-ONLY profile (ENGINE=vllm). This starter cannot boot vLLM."
  echo "See the notes at the top of: ${PROFILE}"
  exit 1
fi

case "${MODE}" in
  mtp) exec "${SCRIPT_DIR}/start.sh" ;;
  dspark)
    if [[ "${MODEL_ID:-}" == *"35B"* || "${MODEL_ID:-}" == *"35b"* ]]; then
      echo "ERROR: dspark draft RadixArk/Qwen3.8-27B-DSpark is 3.8-only. Use mtp for 35B-A3B."; exit 1
    fi
    exec "${SCRIPT_DIR}/start-dspark.sh" ;;
  *) echo "unknown mode '${MODE}' (use mtp|dspark)"; exit 1 ;;
esac
