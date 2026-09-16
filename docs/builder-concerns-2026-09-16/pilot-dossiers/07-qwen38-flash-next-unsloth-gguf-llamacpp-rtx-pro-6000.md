# Dossier 7 — qwen38-flash-next-unsloth-gguf-llamacpp-rtx-pro-6000

## 1. Exact identity / environment
- Recipe: llama.cpp / Unsloth Desktop, `UD-Q4_K_XL` GGUF (111.3 GB) on one **RTX PRO 6000 Blackwell** (96 GB card).
- Command verbatim from the docs (archived raw): `llama-server -hf unsloth/Qwen3.8-Flash-Next-GGUF:UD-Q4_K_XL -md unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 5`

## 2. Source lineage (durable, dated)
- Primary: the unsloth.ai docs page for qwen3.8-next, **retrieved 2026-09-13** and archived verbatim. The revision of that page at fetch time is pinned to its own URL content, not a commit.
- The vendor post (2095157074112164072) is discovery; the doc is the artifact.
- Untracked in history: which page revision the chart "170 tok/s" came from; the docs page does not version itself.

## 3. Technique fingerprint
DDraft-hook MTP via the "shared" Q8_0 MTP module (2.79 GB in Q8) — "shared" because it reuses the main model's embed layer so the module costs 5.23 GB rather than 7.77 GB at BF16.

## 4. Atomic claim ledger
- Config: UD-Q4_K_XL (111.3GB), shared Q8_0 MTP module, `--spec-draft-n-max 5`.
- MTP-off baseline: ~100 tok/s → MTP on 170 tok/s on one RTX 6000 PRO.
- The chart's exact quant per point is NOT re-stated in the docs; my
  gguf-q4 mapping is the inference from the documented command, and the admitted
  record says that in the caveats — this is a "the source supports it but not the
  chart" case.

## 5. Benchmark protocol (stated by the vendor)
"GGUFs can reach 170 tokens/s on a RTX PRO 6000"; "MTP enables Qwen3.8-Flash ~1.3-1.7x faster inference with no accuracy change". No n, no workload class, no quant stated per bar on the chart.

## 6. Memory / offload decomposition (vendor data in the same docs)
| quant | disk size | total memory need (weights+overhead) |
|---|---|---|
| 1-bit UD-IQ1_S | 72.5 GB | 76 GB (MTP) |
| 4-bit UD-Q4_K_XL | 111.3 GB | 115 GB (MTP), 96-114 GB |
| 5-bit UD-Q5_K_XL | 158.3 GB | 164 GB |
| 8-bit Q8_0 | 188.2 GB | 200 GB |
The docs also say, for the 3-bit MTP quant, "works on 91GB RAM so it's best to
have a 96GB RAM/unified memory device"; for this recipe the card that matters is
how the model + MTP module decomposes the 96 GB card. **The 111 GB file does not
fit in one 96 GB card without host offload of the PLE table** — the docs don't
explicitly say on this page — an unknown we should flag.
- `kld_top-1` table for the Flash-Next (top-1% accuracy for 1-bit at 77% of the
  BF16 figure); KL/t PPL table is in the docs' quantization-analysis section.

## 7. Expert decision questions answered
Fit: fitting is exactly what the docs don't answer cleanly for a 96 GB card; the 96-114 GB "4-bit" range spans it. Believable: yes if the PLE is offloaded, unclear otherwise. Good enough: yes (`top-1%` 92.255 for UD-Q4_K_XL vs 77-94% at lower bits).
- Precision-family: the docs correctly note **UD-quants** used by Unsloth on Blackwell.

## 8. Trade-offs / failures / contradictions
- **A 111 GB build on a 96 GB card:** the whole build is only possible in the 111 GB file because some tier can be host-pageable. The docs and the X post do **not say** which of the two options produced the 170 tok/s; a real knowledge gap the owner should ask Unsloth to answer (mirrors hsu_byron's "which trial / which offload" gap).
- "MTP shared module" saves disk but changes memory accounting — the chart does not state whether the baseline and the 170 number share a KV configuration.

## 9. Unknowns / gaps
- The vendor doc is undated and the card is not pinned to a snapshot. Retrievable: re-fetch and diff.
- Unclear whether the 170 number was a `len(token)` frontend, a single stream, or another context; docs Sah description only.
- Blackwell `sm_120` requirement. Not stated on this page (stated on the general docs).
- The "1.79 TB/s" RTX PRO 6000 variant is hardware only. `fp4_sparse_pflops`
  is null on the device record; the docs never state whether MTP on Blackwell
  uses FP4 path (provenance gap).

## 10. Suggested Lite explanation
Unsloth's own 111 GB 4-bit build + shared MTP head, 170 tok/s on one RTX PRO 6000 — but the build only fits the card with a host RAM offload, which the X post does not state.

## 11. Full Pro explanation
This is a vendor-claimed recipe with a published "how we got here" table: Unsloth
sizes their 4-bit lane at "96-114 GB (total memory)", and the MTP module has an
extra 1-2GB headroom. `shared MTP` instead of a separate draft saves ~1-2GB. The
info contract should note the vendor claim is tied to a model card, not a
tracked repo commit — because the docs page is undated, this row should be
stated with the fetch date and this dossier's URL, not a fake-versioned commit.

## 12. Re-review triggers
- A change in the docs page (we can re-fetch and diff); a v2 of the MTP
  (gguf) module; an independent reproduction on a NB-vendor board.

## 13. Evidence completeness
- Configuration: strong (exact command).
- Observed: one number (170), one operating point.
- Matched A/B: no.
- Reproduction: none.
- **Blocker:** the 96 GB fit question is unresolved; we cannot set
  `requirements.memory_gb` to 111 without explaining the discrepancy —
  currently the admitted row records 114 GB with a note. Also no driver / SM
  /quant mapping. This recipe stays `claimed` and is **excluded from the
  directory's "spans >1 class" argument** until the fit question is answered.
