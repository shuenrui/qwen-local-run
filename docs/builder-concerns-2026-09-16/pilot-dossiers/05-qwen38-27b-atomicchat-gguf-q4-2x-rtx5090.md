# Dossier 5 — qwen38-27b-atomicchat-gguf-q4-2x-rtx5090

## 1. Exact identity / environment
- Recipe: `llama-server -m Qwen3.8-27B-AD-Q4_K_M.gguf -ngl 99 -c 8192` on two RTX 5090s (full offload, `-ngl 99`, 8k context).
- Checkpoint: AtomicChat/Qwen3.8-27B-GGUF, AD-Q4_K_M = 17.1 GB; AD is the Atomic Dynamic layout of the two largest tensor groups.
- Format: GGUF. Engine: **stock** llama.cpp (the checkpoint's in-checkpoint MTP head is available but not used in the headline numbers).

## 2. Source lineage
- Vendor artifact (rung 1 in SCHEMA's social ladder): the AtomicChat HF card + "How we measured" (raw `hf_AtomicChat_27B-GGUF.md`), 305,686 downloads.
- No independent reproduction; the difficulty-curve claim ("one of the most-
  pulled 27B GGUFs anywhere") is a marketing prize, not a benchmark claim —
  recorded separately in the vendor's card language, which experts distrust less
  here because of the quality table (§6).

## 3. Technique fingerprint
A standard quantized-GGUF llama.cpp lane, no offload tricks, no speculative
decoding in the header row (MTP available as a variant command on the same
checkpoint file's MTP head).

## 4. Atomic claim ledger
- Config fact: `-ngl 99 -c 8192`, full offload, AD-Q4_K_M.
- Observed (from the card, named as a row in the card): prefill 363 → 5244, decode 77 → 72.
- Intended mechanism (from the card): "AD-" labels ffn_down / ffn_up tensors; the model gets an importance matrix from BF16 (not a quant proxy), so the quantization claims are tied to a validated quality baseline.

## 5. Benchmark protocol (honest), verbatim from the card
"Every number below is measured, not estimated... llama-perplexity -m your-quant.gguf -f eval_neutral.txt --kl-divergence-base base-neutral.kld --kl-divergence -c 4096 -ngl 99"; "Hardware: 4x RTX 5090, CUDA 13.0... I used only 2/4 cards for all the measurements though, just the servers had 4, so i write about it openly to avoid any confusion". This is the corpus's strongest self-described protocol: it states the running context and makes an ambiguity explicit in its own words.

## 6. Memory / offload decomposition
| layer | value |
|---|---|
| AD-Q4_K_M weights | 17.1 GB (card's own value) |
| on hypotheses | "full offload" implies residency across two cards |
| 8k/32k | not separated; the 5244 prefill at 32k is flagged as a likely col-semantics issue (quoted in the setup caveats). |

The card itself is the only source that tells you HOW much memory: no
`memory_gb` measurement row is attached (we carried `requirements.memory_gb: 20`,
which is the weights + KV estimate, stated as an estimate). This is honest but
thin.

## 7. Expert decision questions answered
Fit: within the recorded 2× RTX 5090 full-offload lane that the vendor used, with 17.1 GB weights and a 20 GB memory estimate (recorded as an estimate). Believably fast: vendor-tier only. Good enough: quality at the quant is the strongest thing we have (KL/top-1 table)
(team's own table); checkpoint 8-bit vs 17-bit is a KLD-vs-size fallback. Sustained: no
 data.

## 8. Trade-offs / failures / contradictions
- **Two-card setup is a choice for `n`-card cards** — the why is a *card having
  two physical cards with a 17 GB model* is the atypical case; it's not a
  "maximum op" for a home build.
- The card's 305,686 downloads are a popularity figure, not a quality figure —
  kept out of the measurement rows.
- The vendor quant table contains an honest top-1 drop at AD-IQ2_XXS
  (79.44% top-1 vs 98.92% at Q8_0), so the trade-off is measured, not hidden.

## 9. Unknowns / gaps
- run.repo_commit is not pinned; the "recipe is the card" reading has no commit.
- No `n`, no batch-size statement, no 32k scheduler statement.
- 32k/8k split threads need to be distinguished per-row once we add the
  "column semantics" to the contract.

## 10. Suggested Lite explanation
AtomicChat's 17 GB AD-Q4_K_M on two 5090s, 77 tok/s decode / 363 tok/s prefill at 8k.

## 11. Full Pro explanation
The "How we measured" section is the model example for what the pilot's information contract wants: a published quality table from the vendor, the reference perplexity (4.5219 ± 0.0238) on held-out neutral text, imatrix computed on BF16 (never on a quant proxy), and a public logig dataset so anyone can re-measure with the command verbatim.

## 12. Re-review triggers
- A re-measured quality table (new KL/top-1).
- `AD-` quant type changes; the card documents the "one-quant" conventions.
- Atomic-Chat repo adds a commit or a changelog.

## 13. Evidence completeness
- Configuration: strong (card-audited).
- Observed: strong (card tables), vendor tier only.
- Matched A/B: multiple sizes within one card.
- Reproduction: none (unusual since the card says "raw logits of the reference").
- **Strongest at:** output quality (KL/PPL) and at the "correct size" answer.
**Blocker:** no pin for the card; the card is a moving target (vendor
re-quantizes and re-measures routinely — the pass-4 note says "competitors'
files re-measured").
