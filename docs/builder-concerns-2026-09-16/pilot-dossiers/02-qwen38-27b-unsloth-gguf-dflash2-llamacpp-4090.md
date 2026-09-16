# Dossier 2 — qwen38-27b-unsloth-gguf-dflash2-llamacpp-4090

## 1. Exact identity / environment
- Recipe: llama.cpp **PR #27342** (DFlash2) + z-lab/Qwen3.8-27B-DFlash2 draft, single RTX 4090 24 GB (Ubuntu 22), Ud-Q4_K_XL trunk.
- Custom analogalok Q2_K 2-bit drafter replaces the stock Q4_K_M drafter (~700 MB), still 16.7 GB weights on-card.
- Builders: analogalok (X) + the llama.cpp PR-27342 patch. run.repo pinned to the archive of PR #27342; **no commit SHA in the corpus** — that is a known gap.

## 2. Source lineage
1. analogalok's X thread (the same lineage as 2089979723166200196, 2090874243185856971, 2090797011100717267, 2090400471458759145, 2090432439386874143, 2089403194157965345, 2089340439581364616) — all archived in `raw/xsweep_analogalok.json`.
2. The z-lab/unsloth HF model cards (durable checkpoint ids only — no numbers).
3. 9 posts, ONE lineage — this is the instruction Terra gave me about lineage counting, in practice.

## 3. Technique fingerprint
DFlash2 block-diffusion speculative decoding with `--parallel 1` ("force the engine to dedicate 100% of your 24GB VRAM buffer to a single user") + `--spec-draft-n-max 4`.

## 4. Atomic claim ledger
- Config: UD-Q4_K_XL, z-lab DFlash2 draft, `--max 28k` prompt, `--parallel 1`, `--spec-draft-n-max 4`, KV `q4_0/q8_0` depending on context.
- Mechanism (claimed): DFlash2 "maintains a consistent 10–15% decode speed advantage over Native MTP at every single context depth" (same lineage; one Post).
- Observed, with A/B control: 90 tok/s @30k cext vs 68.09 with Native MTP; prefill 2,324 (MTP) vs 1,662 (DFlash2) — **MTP wins prefill, DFlash2 wins decode** — matched A/B inside the same builder's series (a real A/B but single source).
- Negative result (law 3): "Multi GPU and multimodality is currently broken; Tensor splitting across multiple cards will fail on this PR" — this is the right level of honesty.

## 5. Benchmark protocol
"28k prompt baseline… tested with a 28k prompt at n-max 3" — 28k-prompt runs at each context depth; the 142k stress test is a separate operating point. Sample size `n` is not stated by the source: a **known gap** this dossier records, since no n appears anywhere in the archived posts.

## 6. Memory / offload decomposition
| layer | value |
|---|---|
| weights on-card | 16.7 GB |
| peak VRAM at 30k/n-max 4 | 22.x GB of 24 |
| drafter | 750 MB Q2_K custom |
| KV quant | f16 (100k) / q8 (170k) / q4 (250k) / 142k context ladder |

Offload is not stated by any source; the posts record 22.x GB of 24 GB VRAM resident at the measured operating points. That is consistent with the measured allocation being on-card, but does not establish that no host offload occurred.

## 7. Expert decision questions answered
Fit: only within the exact recorded configuration (one RTX 4090 24 GB, llama.cpp PR #27342, --parallel 1, KV q4/q8); the builder reported 22.x GB peak VRAM at the 30k operating point, and nothing is claimed beyond it — the dataset carries no unconditional "fits" verdict anywhere.
- Quality: not measured here; this is the recipe that was **verified byte-clean on output** in the (different) ctx 8k case but not in this one.

## 8. Trade-offs / failures / contradictions
- DFlash2 loses prefill to MTP (1,662 vs 2,324) — recorded, not smoothed.
- The 2-bit drafter's gain claim ("+13.3% more context") is one builder's statement; no KL/PPL was published except the "mean accepted = 75.89 → 75.93" A/B.

## 9. Unknowns / gaps
- No sample-size n, no reproducibility date, no independent reproduction.
- Multimodal and multi-GPU are documented **broken** on this PR branch.
- 90-tok headline attributed to "Q4_K_M" but paired with UD-Q4_K_XL — quant ambiguity, admitted-in-caveats.

## 10. Suggested Lite explanation
One RTX 4090 (24 GB), custom Q2_K drafter + --parallel 1 + a KV q4/q8 ladder: the decode curve the builder reports runs ~75.7 tok/s at 26k, 59.2 at 80k and 48.9 at 160k; the 90 tok/s headline is his DFlash2-vs-MTP A/B at ~30k context, where native MTP also wins prefill.

## 11. Full Pro explanation
This is the reference single-24GB lane: DFlash2 via PR #27342 (block-diffusion draft from z-lab), a 2-bit custom drafter, `--parallel 1` to free the batching reserve, and a K/V ladder where the KV cache decides the ceiling. Measured curve from 26k→212k prompts; a 142k real-prompt stress run at -c 170000; llama.cpp PR #27342 (not vLLM) is what carries DFlash2; with the custom Q2_K drafter the builder reports mean accepted tokens 75.89 -> 75.93 and 76 -> 76 tok/s inside his own single-source A/B.

## 12. Re-review triggers
- Upstream merge of PR #27342 into mainline, PR consolidation (as happened with #27739→#27742).
- Any change of KV quant that moves the context ceiling.
- Any Multi-GPU/multimodal backport.

## 13. Evidence completeness
- Configuration fact: strong.
- Mechanism: partial (DFlash2 as kernel-level change asserted once per PR).
- Observed association: strong (curve, with c/k detail).
- Matched A/B: `90 tok/s (DF2) vs 68.09 (MTP)` — same box/kv/quant, one source.
- Repro: 0 independent.
**Blocker:** no n, no sample count, no verifier mention, no `date/driver` pin. This is exactly the kind of row that should have a stated **`provenance_tier: forum`** and never become `box`.
