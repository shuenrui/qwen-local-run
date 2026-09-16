# Dossier 1 — qwen38-flash-next-nvidia-nvfp4-vllm-2x-spark

## 1. Exact identity / environment
- Recipe: vLLM TP2+EP+MTP3 across two DGX Sparks (GB10, sm_121, 128 GB each) over ConnectX RoCE/IB.
- Checkpoint: nvidia/Qwen3.8-Flash-Next-NVFP4 (publisher nvidia), FP8 KV.
- Environment: Docker on both nodes, ~126 GiB free per node, weights shared via rsync or NFS; container `vllm/vllm-openai:qwen38-flash-next` **image sha256:d464f3b4…** (~20.6 GB NVIDIA dev build) — README line 405 (`raw/repo_MiaAI-Lab_Flash-Next-Dual-DGX-Sparks_README.md`).
- `MAX_MODEL_LEN=262144`, `GPU_MEMORY_UTILIZATION=0.835`, `MAX_NUM_SEQS=8` (README line 172).
- Hardware class: `dgx-spark` × 2 (the only admitted multi-unit lane).

## 2. Source lineage (durable artifact first)
1. Primary: MiaAI-Lab dual-Spark README, 935 lines archived; "These numbers were read from the running server (`docker logs vllm-fn`, `docker inspect vllm-fn`) — they are measurements, not estimates."
2. Corpus: featured in the MiaAI post + README (one evidence lineage; not independent).
3. Corroboration: candidate 56 (@WescheNex1q 2× Spark NVFP4) and 128 (2× Spark 176B) mention the same shape; no second A/B.

## 3. Technique fingerprint
TP2+EP + MTP3, bf16-KV-by-default option, PLE table for qwen4_exp, host-side PLE offload optional, checkpoint loader patches — this is a **kernel-level MoE-parallel serving recipe**, not a plain quant lane.

## 4. Atomic claim ledger (configuration facts vs mechanisms vs associations)
- **Configuration fact:** TP2+EP+MTP3, fp8 KV, GMU 0.835, MAX_MODEL_LEN=262144.
- **Intended mechanism (documented, e.g. from the vLLM patch notes):** PLE-table dtype re-injection, MTP layer-index alias fix, MXFP8 `mm_mxfp8` dispatch (README line 89) — plus "FP8_BLOCK_SCALES routed-experts patch (missing upstream — without it the MoE loads unquantized and dies ~7 min in)".
- **Observed association (README tables):** batch-1 greedy with MTP=3 → 52.1 tok/s per stream; x8 aggregate → 207.0 tok/s.
- **Matched A/B:** no raw full-A/B; within-table comparison only (MTP off 24.5 → MTP 3: 52.1).

## 5. Benchmark protocol (as stated by the source)
Server-side reads: bench tables in the repo README; README §"1 GiB of KV pool ≈ 71–74K tokens ≈ +0.07× at 1M ctx"; "3,652,200 tokens = 32 GiB fp8 pool"; load ~6:15 weights + 122 s engine init.

## 6. Memory / offload decomposition (README lines 179, 269, 375)
| layer | value | note |
|---|---|---|
| weights resident/node | 62.72 GB | 64.3 GiB with MTP |
| PLE table | 51 GB fp8 | `PLE_OFFLOAD=false` (pageable path disabled for this run) |
| KV pool | 31.7 / 32.02 GiB | ~3.65 M tokens fp8 |
| headroom constraint | ~2 concurrent 1M requests resident | "3rd+ gets preempted" |

## 7. Expert decision questions answered
Fit: no (needs exactly 2 boxes on one fabric). believably fast: yes with per-node tables. Good enough: yes. Sustained ops: not measured.
- Interconnect: RoCE/IB, passwordless SSH required — interconnect is a **configuration fact** here, not an estimate.

## 8. Trade-offs / failures / contradictions
- The tweet-vs-README gap is not blended: the admitted row uses the README numbers, and the tweet's "~64 tok/s single stream, ~115 for 2-4 concurrent" stays recorded in the ledger as the source it contradicts.
- **Discrepancy (unresolved):** README's RadixArk/Qwen3.8-Flash-Next-NVFP4 recipe/verify path is a different repo than the admitted nvidia/Qwen3.8-Flash-Next-NVFP4 checkpoint — the README uses both (line 10 vs 162 vs 384), and the "checkpoint fixes" are checkpoint-specific. Not yet resolved which HALF the fixes are needed for.

## 9. Unknowns / gaps
- run.repo_commit is not pinned. The container image sha is the only durable revision in the corpus.
- This is a **two-occupation** lane: no data for the same checkpoint on one box.

## 10. Suggested Lite explanation
Lite: one 2× DGX Spark lane; 52 tok/s per stream; ~207 at 8 concurrent; needs RoCE/IB and a developer vLLM image.

## 11. Full Pro explanation
Two 128 GB GB10 boxes joined over ConnectX. A 20.6 GB dev build with three upstream-missing patches. KV pool 32 GiB (~3.65 M tokens). Aggregate scales 3.8× from x1; per-stream falls to 49%. Load is ~6:15.

## 12. Re-review triggers
- Any change to vLLM version or to the checkpoint (RadixArk vs nvidia) that changes the PLE dtype/al-index patch.
- New upstream block for the FP8 routed-experts patch.
- PROMOTION-GATE (from Terra, 2026-09-16): pinning alone is **not** enough to move pilot 01 from C2/uncontrolled to C3. A rerun is not categorically required if the cited telemetry table plus the archived source can establish: (1) both arms, (2) same server/config/workload, (3) the sole MTP toggle, and (4) resolution of the checkpoint-path discrepancy. If those facts remain unavailable, pilot 01 stays C2/uncontrolled; a clean rerun is the route to C3.

## 13. Evidence completeness
- Configuration fact: strong (README-verified).
- Intended mechanism: strong from README §"portnotes".
- Observed association: strong, server-read tables.
- Matched A/B: weak — only within-row (MTP ON vs OFF).
- Reproduction: 0 independent (1 lineage).
**Blockers:** no repo commit pin; A/B vs RadixArk not run; alpha of 1× box missing.
