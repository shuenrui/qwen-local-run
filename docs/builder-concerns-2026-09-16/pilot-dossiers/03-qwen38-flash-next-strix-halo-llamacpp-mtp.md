# Dossier 3 — qwen38-flash-next-strix-halo-llamacpp-mtp

## 1. Exact identity / environment
- Recipe: llama.cpp branch `strix-halo-flash-next` (ROCm) on an AMD Strix Halo APU (Ryzen AI Max+ 395 / Radeon 8060S, gfx1151, 128 GB unified, ROCm 7.1, HIP).
- Checkpoint: unsloth/Qwen3.8-Flash-Next-GGUF **UD-IQ4_XS** (93.7 GB) + drluoto/Qwen3.8-Flash-Next-MTP-GGUF Q8_0 sidecar (detached MTP head).
- Class: hardware/`strix-halo` — an AMD iGPU, which is the only non-NVIDIA, non-Apple unified-memory arch in the dataset. Reference: `attribution: "gfx1151"` from the candidate discussion frame.

## 2. Source lineage
1. Durable: drluoto/flash-next-strix-halo (the cookbook/guide repo) + the ggml-org/llama.cpp discussion 27950 thread (both archived).
2. Backers named upstream: rmonsurate (MTP), crusaderky (loader), Geramy (hipCUB diagnosis), jadenmach2 (radix TOP_K), Unsloth, JJJYmmm/Qwen — this chain is a genuine multi-author lineage.
3. Two related negative replies (Giulio Volpe on ROCm 10.0 breakage) — see §9.

## 3. Technique fingerprint
Three named levers, in order: (a) GPU TOP_K fix (stock HIP falls back to CPU past `ne=1024` — PR #26592 hipCUB or PR #27466 native radix), (b) native MTP (#27836) + detached-head loader fix, then (c) `--spec-type draft-mtp,ngram-mod` on top.

## 4. Atomic claim ledger
- Config: UD-IQ4_XS (greedy), separate Q8_0 MTP sidecar, the three build levers above; run without GGML_CUDA (it's ROCm).
- Mechanism: HIP falls back to CPU past ne=1024 → GPU TOP_K is the fix; MTP is a native (not IMO) decoder path on this branch, documented in PR #27836.
- Observed association: file rewrite @8k 16.8 → 47.1 tok/s; 24k 15 → 28.6.
- **Byte-clean verification**: "Output verified byte-clean at long prompts — an earlier community MTP port produced genuine-looking tok/s while emitting multilingual noise above ~1k prompt tokens ("read the output, not just the counter")". This is the strongest proof-of-output statement in the corpus.

## 5. Benchmark protocol
Two context points (8k, 24k), two task classes (file rewrite, new code). No n, no audit; the builder's own numbers. **This row should never become box** unless we re-run it.

## 6. Memory / offload decomposition
Trunk 93.7 GB plus a ~5 GB sidecar — both resident. "Approximately 105 GB of the 128 GB unified pool is allocatable to the iGPU" (AMD setting, not a formula in the corpus).

## 7. Expert decision questions answered
Fit: within the recorded Strix Halo class (Ryzen AI Max+ 395, 128 GB unified) — a class entry, not a single SKU; the builder measured at 8k and 24k context. Believably fast: for those two operating points, yes, on real coding workloads rather than synthetic tok/s. Good enough: mixed — MTP degrades above 24k context, and the guide names the pitfalls (`-ub 2048`, `GGML_CUDA_DISABLE_GRAPHS=1` on ROCm < 7.13, dio vs mmap load).
- Archetype: **AMD iGPU** — the only pilot that exercises the RDNA3.5/ROCm path with MTP plus `hipCUB/radix` backend-fix context.

## 8. Trade-offs / failures / contradictions
- **Negative (law 3):** on newer ROCm, the detached MTP sidecar reportedly loads with `n_layer_nextn` = 0 and "tensor blk.0.hc_attn_norm.weight not found" — user-verified negative result, and a §13-level trigger for re-testing a freshly merged ROCm.
- The 5.2GB-vs-360GB "shard-scalpel" trick is clever but non-standard; the repo's "Hints and pitfalls" section says why this matters.

## 9. Unknowns / gaps
- No `run.repo_commit` (the recipe lives on a branch, not a tag). PR numbers given, not SHAs.
- Builder did not record power, thermal or GPU-allocatable ceiling beyond the 112 GB value.
- The 47→31.7 → 28.6 vs 16.8 numbers are from one day; no notes on thermal drift.

## 10. Suggested Lite explanation
Strix Halo on llama.cpp-like branch with three fixes tops out at 47 tok/s on a file rewrite and 28.6 at 24k context; slower than consumer GPUs but it's the only full-MoE category this recipe covers.

## 11. Full Pro explanation
The one APU lane admitted so far. It uses normal llama.cpp quantization (UD-IQ4_XS) and a separate Q8_0 MTP sidecar; the recipe is built from a ROCm-specific branch carrying three kernel-level patches. Byte-clean was verified, which is exactly what the information contract asks for.

## 12. Re-review triggers
- New ROCm release, or merging PR #27836/#26592/#27466 into mainline.
- A Holohalo that changes HIP-`ne=1024`-falling-back; the guide explicitly names the trigger.

## 13. Evidence completeness
- Strong: configuration fact, A/B-vs-baseline on the builder's own stack.
- Weaker: no cls of n, no independent reproduction, no ngram-mode A/B (ngram-mod is a knob with no measurement).
**Blocker:** need a fresh-branch build to confirm the detached-head loader fix on current ROCm.
