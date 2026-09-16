# Dossier 4 — qwen38-27b-mlx-8bit-dflash2-atomic-chat-mac256

## 1. Exact identity / environment
- Recipe: Atomic Chat app on Apple Silicon (MLX-VLM backend), DFlash2 on Auto; checkpoint: mlx-community/Qwen3.8-27B-8bit; hardware: **mac-256gb** (M3 Ultra).
- No flags, no context, no command - this is the barest recipe in the pilot set.

## 2. Source lineage
- One vendor post (x.com/atomic_chat_hq/status/2090436652363665614), reply by @TriadDarren, archived in `raw/xsweep_atomic_chat_hq.json`.
- Also referenced by @JoelDeTeves (also one post, same lineage).
- The atomic-chat engine record; the mlx-community 8-bit HF card (29.5 GB).

## 3. Technique fingerprint
Hardware-side: everything resident in a 256 GB unified pool. Engine architecture is new (a **TypeScript Jan-fork** that vendors its own MLX-VLM path) — a fork-category engine, entirely the reason it was admitted as `atomic-chat` and not `mlx-lm`.

## 4. Atomic claim ledger
- Baseline 23 tok/s → 87.6 with DFlash2 on Auto = 3.79×.
- Vendor headline "Up to 4× faster" — retained because the reply corroborates it as 3.79×,
  bilibili argument exactly.
- "${Sample}" is the *only* driver in this dossier: a single reply from a builder
  who answered "How'd you get there?" only.

## 5. Benchmark protocol — **not stated**
No n, no context, no workload. This is a recipe where the "Lite" explanation
must be careful not to imply more than the source.

## 6. Memory / offload decomposition
8-bit MLX (29.5 GB) in 245 GB usable pool; no offload. This is a
**memory-abundance** archetype (Point 7 in my memory-headed pilot set: you don't
run a 24 GB card in the M3 Ultra; you run 30 GB).

## 7. Expert decision questions answered
Fit: only as a claim of the recorded machine (an M3 Ultra 256 GB Mac); because the builder stated no context and no workload, no broader fit is implied. Believably fast: single-stream samples only.
Good enough: unknown, no quality gate (unnchecked). Sustained: unknown.
- The only other data point for this archetype: a 3.79× lift from DFlash2 on
  Auto at 23 → 87.6 tok/s (the builder’s own reply; no curve, no repetitions).

## 8. Trade-offs / failures / contradictions
- **"Atomic Chat" is a UI, not a kernel**: while the README states it
  "vendor benchmarks DFlash2 on RTX 6000" as fact, the OpenSource engine
  registry's `README says DFlash Apple-only` contradicts it. It is recorded
  as an unresolved contradiction in the engine's gotchas (from a pass-4
  note) — not settled here.
- The accepted 4× headline number is the vendor's own; the observed 3.79×
  is in this pilot's data, so the honest description is "3.79×".

## 9. Unknowns / gaps
- Context length, sampler settings, MTP/DFlash block size, and KV quantized or not — all unanswered.
- Nothing states the MLX stack version (`mlx-community 8-bit` requires re-
  solving the actual snapshot). Reference `mlx_community/8bit` card snapshot was not pinned.
- The vendor routinely raises this class (Flash-Next, 27B) on X and the same
  builders repeat their claims; one lineage.

## 10. Suggested Lite explanation
MLX 8-bit on a 256 GB M3 Ultra, 23 tok/s stock and 87.6 with DFlash2, in the Atomic Chat app.

## 11. Full Pro explanation
Apple unified memory 256 GB tier; the only lane to cover the "M3 Ultra"
archetype beyond a 128 GB Mac. The clamp on this row is *client framing*: the
`sizes` are the model's own numbers on a box Apple configured differently per
tier.

## 12. Re-review triggers
- AtomicChat renames or re-benchmarks; `Atomic-Chat` repo adds a commit pin.
- An MLX quant of the same checkpoint gets published (e.g. a 6-bit).

## 13. Evidence completeness
- Configuration fact: weak (no context, no flags).
- Observed: two points (23, 87.6) — no curve.
- Matched A/B: yes, reported by the same vendor (same lineage).
- Reproduction: none.
**Blocker:** no per-run protocol; cannot become `box` or a "reference" lane
without a re-run. It should stay `reported`/`low-confidence` in any UI.
