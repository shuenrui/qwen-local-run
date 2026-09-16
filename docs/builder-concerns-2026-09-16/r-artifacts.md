# R-artifact resolution appendix (task #17, 2026-09-16)

Companion to `builder-questions.md` and the `pilot-dossiers/` set. Status for
each of the five `R`-matrix items flagged as *retraceable* in
`pilot-dossiers/09-COMPLETENESS-MATRIX.md`. Retrieval was done from the live
registries (GitHub + HuggingFace + Docker Hub) on 2026-09-16; nothing here
modifies `data/`. Anything whose archived evidence cannot be reconstructed is
explicitly *not* resolved.

| # | artifact | status | date-resolved | value | notes |
|---|---|---|---|---|---|
| 1 | drluoto/flash-next-strix-halo (guide repo pin) | RESOLVED | 2026-09-16 | `ec0ad38b4836` on 2026-08-29 | the anchor guidance repo commit |
| 2 | drluoto/llama.cpp branch `strix-halo-flash-next` | RESOLVED | 2026-09-16 | `ea9f94fc7625` + `59a40b56ff79`, both 2026-08-29 | two later commits (`5ad68897a6a5`, `590ac45bc19b`) post-date the anchor and are fly-by, not applied |
| 3 | z-lab/Qwen3.8-27B-DFlash2-GGUF draft model revision | RESOLVED (with a byte-level delta note) | 2026-09-16 | run-anchor revision `57ab3265056d` (2026-08-18 21:25Z). Post-anchor: `343c7b53e384` (Q4_K_M bytes change: `1a25c56858…`, BF16 also changes to `26d47ca2…`); `cb9dfae3f326` toggles BF16 only; `2d9571f8ce46` (2026-08-24) additionally rewrites the Q8_0 blob to `c18e800d…`. Local archived payload: `raw/r-artifacts/z-lab-commits-tree.json` |
| 4 | Pilot **01 dual-Spark** container (`vllm/vllm-openai:qwen38-flash-next`); pilot 07 has no container | RESOLVED-TO-CURRENT, not pinned to a historical digest | 2026-09-16 | Docker Hub tag currently resolves to multi-arch digests `sha256:0aea3024…` (amd64) and `sha256:3b0e188f…` (arm64); the dual-Spark README cites only a prefix `sha256:d464f3b4…`. Local archived payload: `raw/r-artifacts/dockerhub-qwen38-flash-next.json` | The historical digest actually used on the dual-Spark run is not recoverable from a public tag list; pilot 01's promotion gate and open_question remain; pilot 07 is untouched |
| 5 | Same z-lab revision list, pinning the Q8_0 blob specifically | RESOLVED | 2026-09-16 | Q8_0 blob is unchanged at `7f1c9a31a6…` across the 08-18 anchor and the `343c7b53e384` / `cb9dfae3f326` revisions, then is rewritten to `c18e800d…` at `2d9571f8ce46` (+64 bytes) on 2026-08-24 | the Q4_K_M change seen in row 3 belongs to revision `343c7b53e384`, not to `2d9571f8ce46`; the two revisions touch different files

## Practical consequence for the dossiers

- Pilot 03 (Strix Halo) can now legally pin `ea9f94fc7625`/`59a40b56ff79` and its
  guide repo `ec0ad38b4836`. This was previously a soft "re-anchor" blocker.
- Pilot 02 (4090 DFlash2) can pin the *draft* model to `57ab3265056d`.
  Revision `343c7b53e384` rewrote the Q4_K_M bytes (`18a380efc9…` →
  `1a25c56858…`, +64 bytes) and the BF16 file; `cb9dfae3f326` touched BF16
  only; `2d9571f8ce46` later rewrote the Q8_0 blob (`7f1c9a31a6…` →
  `c18e800d…`). Before promotion the comparison must either pin the anchor
  Q4_K_M blob or re-run on a post-anchor revision — drafter-byte drift must
  not be mixed into the recorded A/B.
- Pilot 01 stays C2/uncontrolled per Terra's gate, which is exactly the four
  facts encoded in `01 … §12`.
- No `data/` edit anywhere. This is archive-only evidence.

## What is still open

- Docker/MiaAI side: the pilot 01 dual-Spark container digest `sha256:d464f3b4…`
  is recorded only as a truncated prefix in the README (line 405). Recovering
  the full historical digest would need a complete Docker Hub tag-history walk
  or the run's own `docker inspect` logs — neither is publicly available.
  Recorded as an exhaustion log; pilot 01 keeps the open_question and its
  promotion gate. Pilot 07 has no container; its fit/offload question is
  separate (builder-questions Q1).
