# Dossier 8 — qwen38-27b-unsloth-gguf-ollama-3090

## 1. Exact identity / environment
- Recipe: `ollama pull hf.co/unsloth/Qwen3.8-27B-GGUF:Q4_K_M`, context capped at
  131072 via a local `qwen-capped-128k` tag; blobs 16.5GB + 928 MB projector on a secondary drive; load ~19.5 s; one RTX 3090.
- Engine: Ollama's HF-bridge (registry lane per law 11), checkpoint from unsloth.

## 2. Source lineage
- Primary: HF forum thread 179251 (`raw/forum-hf_179251.json`) — the
  wall-clock division happens here, with concomitant corrections.
- Corroboration: llamabench.ai community RTX 3090 non-speculative runs (38.2 /
  40.0 / 41.1 / 45.6 tok/s — sanity range, **not a reproduction** per the cited
  thread).
- Weight: unsloth GGUF card. `run.repo` is the HF card, not a repo (the recipe is
  a pull, a pinned command, a context ceiling, a location for blobs).

## 3. Technique fingerprint
The "simplest recorded runtime in this hardware tier": no speculative
decoding, no KV quant, no offload tricks. This is the lane the directory uses
for the honest **baseline-not-a-benchmark** comparison.

## 4. Atomic claim ledger
- Config fact: ollama pull + a cap tag + a secondary drive for blobs.
- Observed: 40.2 tok/s recorded as `decode_per_stream`, forum tier, {"source":
  discuss.huggingface.co/t/179251}, "$12s wall-clock on the Q4_K_M pull";
  corroborated by an untested llamabench.ai crowd range 38.2-45.6.
- Intended mechanism: "context capped at 131072 via a local tag" — memory driven
  not by engine memory but by a *named capping tag* the builder created.

## 5. Benchmark protocol, verbatim from the forum
Q4_K_M pull: 482 tokens in ~12 s wall-clock on a 4090 (the "40.2"); John6666's
whole reply is a **decision tree for verifying Ollama numbers**
(`ollama ps`, `ollama run --verbose`, `--tokenize`, eval_duration
straight) = the strongest "how to VERIFY an Ollama number" text in the corpus;
crowd-sourced llamabench.ai rows carried with "not a reproduction".

## 6. Memory / offload decomposition
| layer | value |
|---|---|
| Q4_K_M weights | 17.4 GB (`size_gb`) |
| blobs on a secondary drive | 16.5 GB + 928 MB projector |
| load time | ~19.5 s |
| context cap mechanism | local `qwen-capped-128k` tag |

## 7. Expert decision questions answered
Fit: within this exact recorded run (one RTX 3090, Q4_K_M pull, 131072 local cap). It is also the lane the context cap effectively makes reproducible for a 24 GB card — but the corpus does not record a second operator and so remains single-source.
own admission. Good enough: for first-time users of the class, yes.
Sustained: not tested.
- Expert-quirk: in r/LocalLLaMA the wall-clock-division reasoning is the
  *unnquee* thing to convince a recruit of; this row in the schema gives the
  `provenance: forum` vs "untested" tension.

## 8. Trade-offs / failures / contradictions
- The "one of the fastest lanes" intuition is what vendors would put in the
  headline = **trying to call a simplistic run a reference**, which is exactly
  what the corpus blames; the pilot set includes it so the UI can *compare*
  rather than recommend.
- Per @John6666, Ollama's own numbers (wall-clock) can be misleading — the
  "verify your own builder's data" text from the thread is the model for a
  first-class "how to verify" note (Dossier's §5/hard).

## 9. Unknowns / gaps
- The 40.2 tok/s figure is a **wall-clock division, not Ollama's eval_duration**;
  the pass-4 note adds this caveat in prose; nothing in the schema carries it.
- No `n` and no context ceiling measured; the "131072 cap" is a local tag, not a
  ceiling a user can reproduce in Ollama server APIs.
-发动机 `ollama` engine record's gotchas field is the one place this recipe's
  "which runtime version" question lives — currently only noted there, not
  measurable.

## 10. Suggested Lite explanation
Q4_K_M on a 3090 via Ollama: 40.2 tok/s, ~19.5 s load, 16.5 GB of blobs — the simplest route, and the value shows up when you compare it against a one-lane-break two-card recipe or a speculative one.

## 11. Full Pro explanation
This lane's value is the opposite of the Flash-Next recipes: no thinking knobs,
no PR branches, no host offload. The Ollama pull through the HF bridge takes a
Q4_K_M at 17.4 GB and a named cap tag; the "40.2" is a wall-clock remainder in the
verification chain John6666 warned about — so the row should state method: the
way it is done here. The dataset's `requirements.memory_gb` and the "capped at
131072 by a local tag" are the succinct answer to "can I trust this engine's
context number?"

## 12. Re-review triggers
- Ollama changes HF-bridge blob handling / context cap behavior.
- unsloth re-quantizes with a different tag.
- An independent builder records a real (non-wall-clock) number.

## 13. Evidence completeness
- Configuration: strong (pull + tag + blob sizes).
- Observed: weak (a wall-clock figure plus crowd corroboration that is not a reproduction).
- Matched A/B: no.
- Reproduction: none; the corroboration is explicitly "sanity range, not a reproduction".
- **Blocker:** the 40.2 number cannot be promoted above `forum` without an
  eval_duration or a fresh run; the `local tag` cap is unique to this builder —
  a second user would need their own command.
