# Dossier 6 — qwen38-flash-next-atomicchat-gguf-llamacpp-mac64

## 1. Exact identity / environment
- Recipe: AtomicChat AD-3.84bpw-IQ4_XS-M64 build on llama.cpp/Metal, M5 Max MacBook 64GB.
- `AD-3.84bpw-IQ4_XS-M64`: 45.8 GB file + a **39.1 GB pageable n-gram PLE table** = 84.9 GB total — the file set exceeds the 64 GB machine by design, not by accident.
- Vision requires the separate mmproj (projector) file, per the card.

## 2. Source lineage
- Rung 1 durable vendor artifact: the AtomicChat Flash-Next HF card (`raw/hf_AtomicChat_Flash-Next-GGUF.md`), with the "How we measured" section and the **"Three traps"** section (below).
- One evidence lineage.

## 3. Technique fingerprint
The only pilot whose headline value is **a memory-shape trick**, not speed: keep the n-gram (PLE) table pageable so an 85 GB build runs on a 64 GB box.

## 4. Atomic claim ledger
- Config: AD-3.84bpw-IQ4_XS-M64, "with vision, at 36 tok/s".
- Observed (card): decode 36 tok/s (tg128), prefill 517.9 (pp512), model-self 44,125 MiB (wired limit 57,344 MiB) + host 37,279 MiB.
- Intended mechanism: the card names the architecture's trap — "`moe_intermediate_size` is 640. k-quants and i-quants need rows divisible by 256, and 640 is not, so `ffn_down_exps` (23% of the model) falls back silently: ask for IQ2_XXS and you get IQ4_NL... Only block-32 types work there and 4.25 bits is the floor." And "`mxfp4` discards the importance matrix outright."

## 5. Benchmark protocol (stated by the vendor, verbatim fragments)
"pp512 on M5 Max 64GB"; "tg128, with vision, on the 85GB AD build that exceeds machine RAM via the pageable PLE table"; MTL0 wired-limit figures; the card also gives its own **KL-divergence and top-1** table: 3.84bpw 0.2277 / 82.68%, 4.27bpw 0.0842 / 89.49% ("the one to take"), 5.00bpw 0.0837 / 89.55%.

## 6. Memory / offload decomposition
| layer | value |
|---|---|
| AD-3.84bpw build | 45.8 GB |
| n-gram PLE table | 51.2B parameters, 39.1 GB, **pageable** |
| MMA-model | 44,125 MiB model-self (57,344 MiB wired limit) |
| host pageable | 37,279 MiB |
| readable | 84.9 > 64 by design |

One built-in trade worth naming: the n-gram (PLE) tensor stays coarsely
quantized, so at ~39 GB it is far lighter for the pageable path than a GPU-
faulted table would be. The MTL0 model-self figure (44,125 MiB) therefore lands
*below* the wired limit while the host still carries the pageable remainder —
not "higher than physical RAM", which was a misread.

## 7. Expert decision questions answered
Fit: not unconditional — per the vendor, the 84.9 GB build runs *only because* the PLE table pages from disk (44,125 MiB model-self vs a 57,344 MiB wired limit plus 37,279 MiB host, all vendor-attributed figures). Believable: vendor tier only.
Good enough: only in the benchmark space; no quality canary aside from the vendor's own `top-1` 82.68% and KL 0.2277, which are honest signals.

## 8. Trade-offs / failures / contradictions
- An 85 GB build on 64 GB of hardware cannot be a "fits" verdict — this is
  exactly why the directory needs a **no-unconditional-fits** rule and why this
  lane is useful as a gotcha example.
- The 3.84 bpw file that the recipe ships below the quality table's overall
  recommended pick ("the one to take"); the measured cost of that cheaper file
  is the top-1 drop, not a hidden quality loss.
- Vision is a separate download (the card lists a separate mmproj, and the
  vendor's card says vision needs the projector, same as pass-5baby note).

## 9. Unknowns / gaps
- run.repo_commit not pinned (the HF card, not the repo, is the recipe).
- No MTP/PRF `--spec-type` given for speculative decoding on this build.
- Whether the pageable table ever crossed a memory-pressure ceiling is not recorded by the vendor card; that limit is simply absent from the source rather than whitewashed.

## 10. Suggested Lite explanation
AtomicChat's 84.9 GB build: 45.8 GB weights plus a 39 GB n-gram table, kept pageable so it runs on 64 GB of Apple unified memory at 36 tok/s.

## 11. Full Pro explanation
The three "this architecture" traps are the kind of detail no generic check would give you: (1) `moe_intermediate_size` = 640 breaks block-8/16 quant types, so only block-32 quant types work for `ffn_down_exps`; (2) the n-gram GET_ROWS tensor receives **no importance matrix** in llama.cpp, so its 51.2B parameters are quantized blind, with 6-bit-vs-8.5-bit = 0.0005 mean KLD (below the error bar); (3) `mxfp4` **discards the importance matrix** altogether, so it cannot be used for `ffn_down_exps` without a quality loss the card tests and publishes. This is also the recipe that makes the "structured offload" contract field load-bearing.

## 12. Re-review triggers
- AtomicChat re-quantizes or re-measures (they do this routinely — their card says so).
- llama.cpp changes the GET_ROWS/PLE handling (upstream ngram-module).
- A second independent builder runs the same build — currently the card is the only source.

## 13. Evidence completeness
- Configuration fact: strong (the card publishes a specific file and size).
- Observed: 3 (prefill 517.9 pp512, decode 36 tg128, memory numbers in MiB).
- Matched A/B: no; single build.
- Reproduction: none.
- **Strongest at:** memory-shape honesty — 84.9 > 64 GB is a *credible* build only because the source said so.
**Blockers:** `run.repo_commit` is unset; nothing records the MTL0 `sysctl` value or kernel version; the "pageable" mechanism itself is only stated in the vendor's card (no independent reproduction exists so far), so the dataset carries it in caveats prose — the contract's `offload` field would make this a first-class value.
