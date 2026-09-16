# Analysis: expert-concern taxonomy, archetype stack, distrust list, and the revised per-recipe information contract

Companion to `corpus.md`. Every claim below traces to an archived payload path
(`docs/builder-concerns-2026-09-16/raw/...` or
`directory/tools/history/inputs/pass4-social/raw/...`). Frequency language is
"source-diverse" not statistical.

## C. Exact questions experts ask before choosing or trusting a recipe

Grouped by what the question actually decides:

**Will it run at all?**
1. How many bytes does one token weigh in the checkpoint, and what is THIS
   machine's bandwidth? (roofline sanity before reading any number)
2. Does the KV cache need to be quantized/offloaded, and to what tier
   (GPU → host RAM → SSD)? What exactly breaks or slows when it does?
3. Is my GPU's precision path in the same family the recipe was tested on?
   `PTuGGdDuyPI: "not all GPUs can actually run NVFP4"` — a real regional/precision trap, not a marketing line.

**How fast will it run, and believably so?**
4. Is this prefill Zeit what I actually care about?
5. Does that number survive "at concurrency 1 per stream, one agent one user"
   and still hold when my agent runs 8 concurrent tool calls?
6. What does the draft acceptance rate actually decay to at my context depth?
7. If the recipe says "90 tok/s at 30k", what's the per-stream reality and
   what's the aggregate?
8. Can I reproduce it? (commit, driver, size)

**Is it good enough for my work?**
9. Did the builder's own quality table lose numbers as the quant got smaller?
   `spiritbuun: "PPL numbers… is not really the story… at the expense of KLD"`.
10. Output survives? llamacpp-discussion-corruption case, analogalok byte-clean
    verification rule.
11. Reasoning overhead — the UNTHINKING-vs-THINKING sampler matters more than a
    small tok/s difference (`WescheNex1q: "Same model. Same prompt. Very
    different thinking budgets. Qwen3.8-27B NVFP4 on 1 DGX Spark"`).

**Sustained operation.**
12. Thermals/power/noise — real sustained behaviour, not boost peaks.
13. Offload strategy — RAM, SSD, host pinned, cold-start after reboot?
14. Multi-user/agent concurrency — when does a 24 GB card stop being enough,
    where is the next bottleneck at 8 concurrent agents.

**Cost.**
15. Tokens per dollar — `vllm AgentX: "tokens per dollar or tokens per GPU… with public configs to reproduce each point"`.

## D. Operator archetypes and their distinctive priorities

Called out per archetype, each with the specific thing they optimize for that
another archetype would find noise:

- **Single consumer GPU (RTX 3090/4090, 5090, 5060 Ti).** Wants a fast decode at
  modest context; context-vs-speed tradeoffs and 1× vs 2× quant just to fit.
  analogalok and the 16 GB operators' tests.
- **Apple Silicon unified memory (M3 Max/M4 Max/Ultra).** Decode-bound;
  MLX is the path; KV ceiling with sysctl iogpu.wired_limit_mb; nothing CUDA
  only. TriadDarren 819 GB/s.
- **Strix Halo / APU iGPU (Radeon 8060S).** ROCm + Vulkan paths; AMD GPU
  TOP_K/GTT kernel fixes; digital TDP is OEM-configurable — owners care
  whether the builder used the fix or the mainline path.
- **Multi-GPU (2×5090, 2×RX 9700, 72 GB tensor-split).** Inter-GPU split
  + how KV splits when attention is split; `_llm_d_` routing question from
  RedHat_AI: "session-sticky routing can matter more than queue balancing".
- **DGX Spark / GB10 cluster.** Unified, 128 GB per box; batch-conceptual,
  TP2+MTP, and PLE/MTP forks; requires SSH/RoCE/Interconnect documentation.
- **CPU/RAM/SSD offload.** Pageable PLE tables are the pattern; owners care
  about first-token latency and what happens after a reboot.
- **Multi-user / agent-serving.** They care about aggregate throughput, not
  single-stream speed; vLLM/llama.cpp legacy vs session-sticky vs
  prefix-caching; `MiaAI dual-Spark README: "32.02 GiB = 3,652,200 tokens"`.

**Archenote:** experts do not trust a recipe whose engine/config isn't
transferable to a similar SKU of the same class; "one builder's deck is not
another's". The recipe must say what it assumes about the box.

## E. What experts distrust (each source-backed)

1. **Peak-only claims** — `vllm Project: "Pipeline parallelism is great on cold,
   long prompts. On warm agent turns that add a few hundred tokens, the
   bubbles eat the gain."`
2. **Numbers that don't survive an independent reproduction** — the llama.cpp
   27B silent-corruption discussion is the canonical corpus case: plausible
   tok/s with garbage output.
3. **Aggregate vs per-stream confusion** — `MiaAI-lab README under "How to read
   these tables"`; analogalok's "the complete VRAM physics… bounded by
   bandwidth or physical VRAM" — in r/LocalLLaMA noiserr's thread, owners call
   themselves out for mixing these.
4. **Vendor claims that never mention trade-offs** — analogalok names the
   exact trade ("– parallel 1 is what buys you 250k context"), while vendor
   posts say "up to 4× faster" without it. AtomicChat is the *positive* case
   (publishes PPL, KL, own everything), so the distrust is of *what's
   omitted*, not of the vendor being untrustworthy.
5. **Wrong quant for the architecture** — precision family mismatches are
   distrusted on sight (`PTuGGdDuyPI`: "not all GPUs can actually run NVFP4").
6. **Hidden offload** — s4cTVRH2ReA's 16 GB box prefill pain is the classic
   "the benchmark was fine but why is my real prompt slow" story.
7. **Benchmarking-out-of-context** — `TriadDarren` runs everything through an
   Accuracy Evaluator first, and calls out "this article is… largely a
   marketing piece".
8. **Reproducibility friction ignored** — `MiaAI dual-Spark README:` a run
   needs `--restart` unset (die-on-crash), `huggingface_hub >= x` offline
   mode, gated-repo, image-sync, verified-complete snapshot. A recipe that
   skips these is untrustworthy even when its numbers are real.
9. **One source louder than three** — Terra's rule about one builder
   repeating a claim across X/YouTube/README counting as one lineage is
   confirmed by the corpus: analogalok's 4090 series plus Atom's HF card plus
   a YouTube video repeating the DFlash2 claim are the *same* lineage, not
   three independent corroborations.

## F. Revised per-recipe information contract

New field-level contract, ordered by must-have first. (Nothing here is
mandatory to add today; this is the research recommendation.)

**Must-have — without it the row is not trustworthy:**
- `run.repo_commit` + `run.command` verbatim (already required).
- `requirements.memory_gb` + `min_vram_gb` + `disk_gb` (already required-ish).
- `capabilities.long_context` — the measured token ceiling, not the ambit.
- `variation.size_gb` — from the HF tree endpoint, not a guess. (already law)
- `engine.version` / kernel commit — *new*: answers "does this still work
  after the next driver/PR merge?" (source: MiaAI-Lab gotchas, RedHat_AI,
  PTuGGdDuyPI).
- `offload` as a structured field (none | ram | ssd | host-ple | hybrid) —
  *new*: today it's prose in `requirements.notes` on 9 of 79 setups.

**High-value — decides whether the recipe fits your actual workload:**
- `kv_cache_gb` at the recorded context — one number answers "will 200k of
  conversation fit" without arithmetic.
- `spec_decode.acceptance_rate` + a decay curve whenever available.
- `concurrency_ceiling` — the tested number of parallel streams, distinct
  from the `concurrency` of one measurement.
- `prefill_tok_s` — already in the enum and should be a first-class column,
  not buried.
- `thermals.power_watts` when measured; at minimum say "not recorded".
- `engine.batching` / `batching.lookup` — the group that the vLLM agentic
  blog treats as a first-class dimension.
- Correctness artifact: a `quality_canaries[]` list (human-eval / KLD / the
  sampler `thinking` effort) rather than prose.

**Niche — include only when the source states it:**
- tokens-per-dollar;
- thermal curve sustained vs peak;
- interconnect specifics (RoCE/RDMA role) — currently only in the 2× Spark
  lane's `engine.config` prose.

Every field must remain "recorded or absent", never inferred — the whole
trust model of the directory depends on that.

## G. What the 79-setup dataset already covers vs gaps

Present: bandwidth / memory class, quant ladder, single-stream vs aggregate
separation, provenance tiers, caveats.

Buried in prose (measured): offload (9), KV/offload/kv details (16),
acceptance/decay curves, engines' `requires_fork` context, driver-version
friction.

Absent as fields: engine/runtime/driver version, concurrency ceiling,
kernel/backend selector, cost, power, KV-offload strategy, verified-output.

What must never be inferred (the schema must keep it honest):
- `provenance_tier` never "upgraded" to box without the owner's own run.
- Acceptance rate / KV pool size must not be back-derived from aggregate
  throughput.
- No `decode_tok_s` without a metric, a context, and a concurrency.
- No "fits" verdict anywhere except My Hardware.

## H. Recommended pilot recipes (next doc)
