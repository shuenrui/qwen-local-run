# Pilot dossiers — index (task #14)

Eight source-backed expert recipe dossiers derived from the task #11 corpus and
`docs/builder-concerns-2026-09-16/pilot.md`. One file per recipe plus this
index. Every dossier uses the 13-section contract Terra specified, with pinned
revisions where the *historical* source supports them, and citations into the
raw archives (`docs/builder-concerns-2026-09-16/raw/` +
`directory/tools/history/inputs/pass4-social/raw/`). Nothing here edits `data/`,
schema, validator, UI, or candidate states.

| # | dossier | archetype | evidence grade | top-priority blocker |
|---|---|---|---|---|
| 01 | 01-qwen38-flash-next-nvidia-nvfp4-vllm-2x-spark.md | DGX Spark 2× / multi-unit, RoCE | config strong, A/B weak, reproduction 0 | repo revision not pinned; RadixArk-vs-nvidia checkpoint discrepancy |
| 02 | 02-qwen38-27b-unsloth-gguf-dflash2-llamacpp-4090.md | single consumer GPU | observed strong, A/B honest | no n; no independent repro; multi-GPU/multimodality broken |
| 03 | 03-qwen38-flash-next-strix-halo-llamacpp-mtp.md | Strix Halo / APU ROCm branch | config strong | no branch pin; byte-clean assertion not retested |
| 04 | 04-qwen38-27b-mlx-8bit-dflash2-atomic-chat-mac256.md | Apple 256GB / Atomic Chat app | weak (2 points, no protocol) | context/flags unstated; no independent run |
| 05 | 05-qwen38-27b-atomicchat-gguf-q4-2x-rtx5090.md | consumer multi-GPU, quant-table exemplar | config + quality strong; speed vendor tier | not pinned; 32k column semantics |
| 06 | 06-qwen38-flash-next-atomicchat-gguf-llamacpp-mac64.md | exceeds-RAM case | strong memory decomposition | PLE pageable sysctl/kernel version absent |
| 07 | 07-qwen38-flash-next-unsloth-gguf-llamacpp-rtx-pro-6000.md | RTX PRO 6000, precision-family gap | one operating point only | the 96 GB fit question (111 GB file on 96 GB card) |
| 08 | 08-qwen38-27b-unsloth-gguf-ollama-3090.md | simplest runtime / baseline-not-benchmark | weakest observed evidence in the set | wall-clock-vs-eval_duration non-reproduction |

## Pins recorded in the corpus (not inferred from today's HEAD)

- llama.cpp `7e4c0a96880dae4fc4268ad441f8a6446bd5460a` (build 10434, 27082 family).
- llama.cpp `ece963f41…` (build 10450, 27164).
- vLLM container `vllm/vllm-openai:qwen38-flash-next` image `sha256:d464f3b4…` (README line 405).
- DFlash2 = **PR #27342**; Flash-Next support = **PR #27742** (consolidation of #27739); MTP = **#27836**; kernel fixes = **#26592** / **#27466**; PLE quant dispatch port from vLLM **PR #53899**.
- The unsloth.ai docs page fetched 2026-09-13 (undated otherwise).

## Follow-up (task #14b): historically-resolved pinned commits

Founded on dated commit evidence only; today's HEAD is never substituted for a
historical run, and ambiguity is recorded rather than hidden. The canonical
version of this table is the one below (an earlier duplicated copy was removed).

| Artifact | Anchor (archived evidence date) | Historically appropriate pin | Status |
|---|---|---|---|
| drluoto/flash-next-strix-halo (guide repo) | 2026-08-29 (ggml discussion 27950) | `ec0ad38b4836` — "Flash-Next on Strix Halo: measured stack guide", authored exactly on 2026-08-29 | RESOLVED, unambiguous |
| drluoto/llama.cpp branch `strix-halo-flash-next` | 2026-08-29 | last branch commits on/before the anchor: `ea9f94fc7625` (qwen4exp correctness follow-ups from ggml-org/llama.cpp#27941) and `59a40b56ff79` (crusaderky detached MTP head loader), both 2026-08-29 | RESOLVED |
| z-lab/Qwen3.8-27B-DFlash2-GGUF (the drafter the 4090 DFlash2 lane pairs with) | 2026-08-19 (analogalok's 4090-thread date, the matched A/B day) | `57ab3265056d` — "DFlash 2 release", 2026-08-18 21:25 UTC. Later revisions (2d9571f8ce46 of 2026-08-24) exist but post-date the matched A/B | RESOLVED; HEAD deliberately not substituted for the 2026-08-19 run |
| MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks | 2026-08-26 (the recipe's launch post) | **earliest available commit `6e08722d1fad` (2026-08-31)** — no commit exists at or before the anchor, so no pin predating the archive can be constructed | AMBIGUITY RECORDED; the repo was bootstrapped 5 days after the post |

## Completeness audit

`09-COMPLETENESS-MATRIX.md`: per-dossier marks present / buried-in-prose /
retraceable / irrecoverable / not-stated for all 12 must-have + high-value
contract fields, column totals P 45 · B 13 · I 22 · N 11 · R 5, plus a note per
recipe on what moves each category.
