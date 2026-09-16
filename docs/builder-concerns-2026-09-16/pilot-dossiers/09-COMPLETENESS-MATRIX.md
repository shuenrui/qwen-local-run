| field (rank) | 01 2x Spark NVFP4 | 02 4090 DFlash2 | 03 Strix Halo | 04 M3 Ultra | 05 2x5090 | 06 Mac64 AtomicChat | 07 PRO6000 | 08 Ollama 3090 |
|---|---|---|---|---|---|---|---|---|
| run_command (verbatim) (must-have) | P | B | B | B | P | B | P | P |
| size_gb (HF-tree sourced) (must-have) | P | P | P | P | P | P | P | P |
| memory_gb / min_vram_gb / disk_gb (must-have) | P | P | P | P | B | B | P | P |
| long_context (measured) (must-have) | P | P | P | I | P | P | P | P |
| engine / driver version pin (must-have) | I | I | B | I | I | B | B | B |
| offload as structured field (must-have) | P | B | P | N | N | P | P | N |
| kv_cache_gb at recorded context (high-value) | R | R | R | I | P | P | R | N |
| spec-decode acceptance / decay curve (high-value) | P | P | P | P | N | N | P | N |
| concurrency ceiling (high-value) | R | I | I | I | N | N | I | N |
| prefill_tok_s first-class column (high-value) | P | P | P | I | P | P | P | N |
| measured power / thermals (high-value) | I | I | I | I | I | I | I | I |
| quality canary (KL / PPL / eval) (high-value) | B | I | I | I | P | P | P | B |

Legend: **P** already a first-class recorded field, **B** the fact is in the dossier corpus but only as prose, **R** the field can be recovered when the pinned artifact is pulled, **I** no honest way to recover it from the corpus as it stands, **N** not stated by any source.

**Column totals:** B=13, I=22, N=11, P=45, R=5

## Notes per recipe

- **01 2x Spark**: the engine/driver pin is *irrecoverable* only because the archive carries a container sha, not a repo sha; with the vLLM PR/commit-hashes obtained from the archived container (when resolved) this moves to **R**.
- **02 4090**: the `--parallel 1`/`--n-max 4` gotchas (the analogalok rule about on-card memory vs the agent use case) live in one prose row; the corpus does not retain the exact engine name, so kv_cache_gb stays **R** not **P**.
- **03 Strix Halo**: the byte-clean assertion is where the recipe's strongest claim lives; the branch has an immutable history pinned by `ec0ad38b4836` but pinned only via a *dossier* audit, not a stable commit on an upstream; re-pin it on a fresh ROCm. `power / thermals` is absent from this lane.
- **04 M3 Ultra**: 8 of 12 fields are **I** or **N** because the source never states context/flags/workload; length etc. cannot be recovered. This is a source-quality problem, not a contract problem.
- **05 2x5090**: the KL/top-1 table is *P* because the vendor publishes it; the same table has no `n` field or a source date to anchor a re-quant. Missing `kv_cache_gb` therefore stays **N**.
- **06 Mac64 AtomicChat**: the "84.9 > 64" case is the best case for the `offload` field; it is only *B* because PLE pageable is in a prose caveat.
- **07 PRO6000**: the 111 GB build implies host offload that the source does not state → stays **N** for the "how much memory the build actually used per tier" question. This is the single most load-bearing gap for that recipe.
- **08 Ollama 3090**: no MTP/KV/offload context at all in the corpus — that is inherent to the lane (it is the no-tricks baseline). The "verify your Ollama number" text in the record is likewise a **B** candidate: it exists, but as prose.

## Recommended next step (not yet done):
move every **B** into a field (the corpus already supports it) and reach out for the two **I**-s that block promotion (e.g. the 96 GB fit question on 07, eval_duration on 08).