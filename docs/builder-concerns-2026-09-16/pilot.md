# Recommended eight pilot recipes

Chosen from the 79 live setups for *research coverage* (every high-value expert
concern gets at least one canonical example) and *operator-archetype diversity*
(single consumer GPU, Apple Silicon, Strix Halo/APU, multi-GPU, DGX Spark/GB10
solo + 2×, CPU/RAM/SSD offload, multi-user serving). No recipe is included
twice; none of them is a claim I invented — all are already admitted in
`data/setups/` or present in the published ledger.

| # | setup id | Why this one is the canonical example |
|---|---|---|
| 1 | `qwen38-flash-next-nvidia-nvfp4-vllm-2x-spark` | The only multi-unit lane. Exercises the `{"hardware": {id, count}}` convention, interconnect prose, KV pool size (32 GiB = 3.65M tokens), MTP acceptance at 72.8%, aggregate-vs-per-stream separation. |
| 2 | `qwen38-27b-unsloth-gguf-dflash2-llamacpp-4090` | Consumer-GPU benchmarking archetype with the full KV ladder, negative row for DFlash2-vs-MTP prefill, exposed `--parallel 1`/`--spec-draft-n-max 4` knobs. |
| 3 | `qwen38-flash-next-strix-halo-llamacpp-mtp` | Only Strix Halo/AMD iGPU lane. Exercises the ROCm vs mainline question, the GPU TOP_K/GTT kernel-fix narrative, and the "output byte-clean" negative. |
| 4 | `qwen38-27b-mlx-8bit-dflash2-atomic-chat-mac256` | Apple-Silicon M3 Ultra at 256 GB, 23 → 87.6 tok/s with DFlash2 Auto — the only lane showing what a 256 GB pool actually gets you. |
| 5 | `qwen38-27b-atomicchat-gguf-q4-2x-rtx5090` | Vendor-measured with a published per-quant quality table, plus first-rate engine/fork provenance. Consumer-multi-GPU baseline. |
| 6 | `qwen38-flash-next-atomicchat-gguf-llamacpp-mac64` | The clean "hidden offload / pageable PLE" case: an 85 GB build on a 64 GB box. Exercises what the information contract's structured `offload` field would capture. |
| 7 | `qwen38-flash-next-unsloth-gguf-llamacpp-rtx-pro-6000` | The "not all GPUs can run NVFP4/FP4" mismatch trap on a workstation card; vendor-claimed tier acknowledged honestly in caveats. |
| 8 | `qwen38-27b-unsloth-gguf-ollama-3090` | The "simplest recorded runtime" lane. Exercises the "what is the baseline?" question — it is the one most builders reach for first, so its caveats about wall-clock-division measurement carry real teaching value. |

What each pilot additionally demonstrates for the *information contract*:
- `offload` as a field — setup 6 is the pure case, setup 1 the hybrid case.
- `concurrency_ceiling` and aggregate-vs-per-stream — setup 1 again.
- `acceptance_rate`/decay — setup 1 (72.8 %, by position) and setup 2 (decay
  from 90→75.66→48.93 tok/s from 26k→160k context).
- `pre-fill pain at small VRAM` — setup 8's prosey caveats plus the
  s4cTVRH2ReA YouTuber merchant case for a recorded prefill column.
- `quality artifacts` — AtomicChat's own PPL/KL table is the model for the
  `quality_canaries[]` field; setup 7 currently records none.
- `thermal/power` — recorded nowhere; the contract says "not recorded" rather
  than guessing, which is the correct move.

Rationale and the evidence for each field choice is in `analysis.md` §F/G.
