# Open questions to put to the source builders (task #14 blockers → task #13 open_question fields)

Drafted 2026-09-16 as the sourcing side of Terra's open decision #8. Two
load-bearing answer gaps from my dossiers. Until a builder replies, the schema
keeps these as `open_question` fields; nothing is inferred into `data/`.

## Q1 — RTX PRO 6000 fit/offload (dossier 07, the 111 GB UD-Q4_K_XL on a 96 GB card)

Unsloth (@UnslothAI), about their qwen3.8-next guide + the 170 tok/s claim:

> The MTP chart says 170 tokens/s on 1x RTX 6000 PRO with UD-Q4_K_XL — but that file is 111.3 GB while
> the card has 96 GB. Which tier carried the PLE table on that run (host-pinned page-locked? pageable?
> CPU-RAM offload flag? `--parallel 1` vs default batching)? Did the 100 tok/s baseline use the same
> KV / context / quant and driver/runtime versions, and was the number a single-stream run? Finally, does the
> shared-Q8_0 MTP module force a larger resident footprint than the one your 96-114 GB table assumes
> for the 4-bit lane?

Reproduce path: post to the same thread as the chart and to the docs page's comments
section; archive both payloads under
`directory/tools/history/inputs/pass4-social/raw/` so the corpus can cite them.

## Q2 — Ollama wall-clock vs eval_duration (dossier 08, the 40.2 tok/s)

@MiaAI_lab's thread with @John6666 correction tree and the caller.

> Your 27B lane records 40.2 tok/s as `decode_per_stream`; the thread treats that as wall-clock division
> (output tokens over measured wall seconds) rather than Ollama's own eval_duration. To make the record
> usable as a benchmark-grade number for other builders, could you re-run it on the same box with
> `ollama run --verbose` (or share the equivalent verbose output) and report the exact eval_duration /
> eval_count pair? If a re-run is not possible, is the 131072 context cap the Q4_K_M pull's actual
> ceiling, or a transient limitation of that specific bridge tag?

## Where this belongs in the schema

- `evidence.open_questions[]` on each of these two setups (not on hardware records);
  type: "needs_builder_input"; each references `attempt_id`s already linked in the
  dossier's sources so a future answer has a stable home.
- Validator rule: a `c2_wall_clock_division` measurement is admissible, but the UI must
  render the `method_note` beside the headline number and may not use it as the
  recipe's comparability anchor (same verdict so far).

## Re-review triggers (same as the dossier)

- A builder response to either question triggers re-review. It may fill
  conditions, leave the level unchanged, upgrade it if admissibility rules are
  met, or downgrade it if the reply contradicts the recorded values.
- If rate limits prevent a reply before the integrated pilot review, the open_question
  entries remain explicitly unanswered and pilots 07/08 keep the current R/I
  marks in the matrix.

## Send status (2026-09-16)

Attempts to push both questions over the authenticated `twitter` CLI
(`reply`, then a neutral `post`, and a shortened variant that even passed the
280-byte length check) all fail at the Twitter API layer with
"Failed to create tweet" even for a trivial standalone post, while reads
(`tweet`, `user-posts`, `status`, `whoami`) still succeed. The authenticated
write path on this box is not accepting tweets — i.e., a tooling/
authorization limit, not a wording problem. Both questions therefore remain
**drafted and pinned but unsent**; retrying requires either a write-capable
session or the owner's preferred alternate channel.
