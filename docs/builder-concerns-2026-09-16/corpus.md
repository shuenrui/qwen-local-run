# Builder-concerns research corpus (task #11)

Assembled 2026-09-16. Raw evidence lives under `raw/` — nothing here is merged
into `data/`. Nothing below is a claim I made up; everything traces to an
archived payload under `raw/` or a dataset file cited inline.

## A. Corpus ledger

### X (Twitter), all fetched with the authenticated CLI and archived under
`directory/tools/history/inputs/pass4-social/raw/` (pass-4 corpus, 44 payloads,
~2.3 MB) plus new sweeps re-archived on 2026-09-16 under the same dir.

| handle | role | why it qualifies | archived |
|---|---|---|---|
| @analogalok | hands-on dense-27B benchmarker on RTX 4090/5090 | repeated full-stack A/Bs with explicit KV/context/deck settings; 542 mined signal lines | xsweep_analogalok.json (200 posts), x_2088326480669667699.json (50-post thread) |
| @WescheNex1q | DGX Spark + M4 Max operator; recipes with honest negatives | 48 qwen posts captured back to Aug 6, 2026; 166 signal lines | xsweep_WescheNex1q.json |
| @spiritbuun | llama.cpp fork author (buun-llama-cpp, DFlash + TurboQuant) | ships code + numbers; 81 signal lines | xsweep_spiritbuun.json (146 posts) |
| @TriadDarren | M3 Ultra 256GB operator | Mac-side bandwidth/DFlash measurements; runs everything through an accuracy evaluator first | xsweep_TriadDarren.json (24 posts) |
| @alecqfong | DGX Station owner (BF16, large-MoE serving) | 27 signal lines | xsweep_alecqfong.json |
| @MiaAI_lab | GB10/DGX-Spark recipe lab | publishes 934-line README with gotchas and "measurements, not estimates" tables | xsweep_NVIDIAAI.json, repo_MiaAI-Lab_Flash-Next-Dual-DGX-Sparks_README.md |
| @unseenmars_ | SGLang cookbook contributor | authors the verified recipes owners read; 13 signal lines | xsweep_unseenmars_.json |
| @mr_r0b0t | r0b0tlab NVFP4+MTP-sm121 recipe author | 20 signal lines; also curates others' claims | xsweep_mr_r0b0t.json |
| @RedHat_AI | vendor with hands-on serving research | 30 signal lines, includes agentic-serving concurrency work | xsweep_RedHat_AI.json |
| @sgl_project, @vllm_project, @UnslothAI, @atomic_chat_hq, @Alibaba_Qwen, @AMD, @ollama, @NVIDIAAI | engine / vendor / lab accounts | land day-0 support, flags and gotchas | xsweep_{sgl_project,vllm_project,unslothAI,atomic_chat_hq,Alibaba_Qwen,AMD,ollama,NVIDIAAI}.json |
| r/LocalLLaMA thread 19e9xfj (Reddit, pullpush mirror) | ordinary local builders | raw UX + correctness complaints (`reddit_19e9xfj.json`) | archived |
| HF forum threads 179251/179660, NVIDIA forum, llama.cpp discussions ×10 | forum maintainers, quant shops | the "why", not just the "what" | forum-hf_*.json, gh-discussion_*.json |
| AtomicChat + MiaAI-Lab README extracts (durable artifacts) | vendor/builder | quant quality methodology + serving gotchas | hf_AtomicChat_27B-GGUF.md, repo_MiaAI-Lab_Flash-Next-Dual-DGX-Sparks_README.md |
| buun-llama TurboQuant / DFlash repository leads | runtime / fork author | 172 (TurboQuant CUDA), 169 (DFlash) | within xsweep_spiritbuun.json |

### YouTube (7 videos, full transcripts via youtube-transcript-api, archived
at `docs/builder-concerns-2026-09-16/raw/youtube/yt_<id>.json` with segment
timestamps; 7 candidates also added to the pass-4 ledger as [187]–[193]).

| URL | channel | date | transcript evidence highlights |
|---|---|---|---|
| L9QZ97y9Exg ("Your local LLM is 10x slower…") | local-inference + multi-instance serving | 2026 | 317 segments, 12k chars. Concurrency=128, 826 tok/s aggregate, "You can run four llama 70B on one 512GB machine", "limiting factor is compute, not memory" |
| 5jkAlqbk66A (LLama.cpp + TurboQuant setup) | GPU homelab step-by-step | 2026 | 554 segments, 19.7k chars. Longest transcript: full build, KV/TurboQuant branch choice, dependency conflicts |
| QMtWXu_M3dg (Qwen3.8-Flash-Next teardown) | architecture explainer | 2026 | 475 segments. Gated DeltaNet/QSA/PLE table — "mixing them up will waste your afternoon" |
| PTuGGdDuyPI (Qwen3.8-27B model-pick guide) | RTX PRO 6000 operator | 2026 | 454 segments. "not all GPUs can actually run NVFP4" — a real regional/precision caveat |
| PdFI1WN5K8c (vLLM on Colab) | beginner serving tutorial | 2026 | 279 segments, 7k chars. "3B model at FP16 in 15GB", "please use this exact version" |
| s4cTVRH2ReA (16GB box Deep-Dive) | small VRAM operator test suite | 2026 | 443 segments. Prefill pain at 16 GB + offload; "needle in haystack" 256k test at 60k took ~11 h |
| dTutfoSVMq4 ("How much can you actually trust it?") | Mac+desktop operator | 2026 | 267 segments. Trust boundary task movement; "main thing to pay attention to is having a GPU with as much memory" |

### Durable artifacts cited (via `raw/artifacts/` and the existing pass-4 raw/)
- MiaAI-Lab dual-Spark README: 934 lines, "measurements, not estimates" tables.
- AtomicChat 27B and Flash-Next HF cards: own KL/PPL tables; "three traps".
- llama.cpp discussions 27080/27164/27950/28287/28512/28588 (incl. one that
  produced garbage output while showing a plausible tok/s).
- Unsloth Qwen3.8-Next docs page (durable 170 tok/s RTX PRO 6000 claim).
- RadixArk DSpark/SpecForge thread (arxiv-quality methodology reference).

## B. What experts actually care about (ranked by source diversity)

Frequently recurring (independent voices):

1. **The decode number is memory-bandwidth-bound; capacity not speed decides
   what runs at all.** Recurs in analogalok ("25 GB/s…"), WescheNex1q
   ("Limiting factor is compute, not memory"), TriadDarren (819 GB/s vs M5 Max),
   RedHat_AI/sgl_project ("GPU memory is the one tier in the stack you can't
   expand"), MiaAI dual-Spark README. Experts infer whether a recipe is
   interesting from bandwidth × bytes-per-token before reading a tok/s number.
2. **Context window is bought with KV-cache quantization and offloading, not
   with more VRAM.** analogalok's entire KV ladder series (f16 → q8 → q4 →
   PLE→RAM→n-gram→2-bit drafter); AtomicChat "why this table is different";
   MiaAI "1 GiB of KV pool ≈ 71–74K tokens"; spiritbuun TurboQuant; bartowski
   KLD-vs-size tests.
3. **Speculative decoding is a knob, not a constant.** Experts ask acceptance
   rate, per-position decay and the no-victory point; hsu_byron's post "above
   roughly 64 concurrent requests, draft-and-verify overhead outweighed the
   savings" is the rare high-concurrency EOT the directory currently doesn't
   capture; analogalok's decay curves, spiritbuun's medium-vs-xhigh shift,
   WescheNex1q's 97.55% MTP acceptance.
4. **Prefill and decode are two separate measurements.** analogalok and
   WescheNex1q both publish prefill separately, hsu_byron's 1M-ctx prefill
   stress, s4cTVRH2ReA's prefill pain in 16 GB, PTuGGdDuyPI's 2.4T prefill.
5. **Correctness of the output is measured, not assumed.** analogalok "read
   the output, not just the counter"; the llama.cpp 27B silent-corruption case;
   TriadDarren runs everything through an Accuracy Evaluator first; AtomicChat
   publishes its own KL/PPL table; spiritbuun's "PPL numbers… is not really the
   story… at the expense of KLD".
6. **Reproducibility is a running cost, not a footnote.** MiaAI-Lab notes the
   `huggingface_hub >= x` offline failure and gated-repo failure;
   Analogalok "this won't work because you forgot X"; every recipe names
   driver/kernel commit; RedHat_AI cites measured GPU versions.
7. **Offload is a decision, not automatic.** PLE-into-host-RAM warning on the
   dual-Spark; lmstudio/r0b0tlab/DGX-offload lanes; analogalok: "the 85GB build
   relies on pageable PLE by design".

High-impact but source-limited so far: interconnect (RoCE/RDMA hints in the
MiaAI dual-Spark and RedHat v0.30 _llm_d_ posts), thermal/noise (only anecdotal
—"graph capture OOM-wedges until you power-cycle", "thermal, no more than"),
and "tokens per dollar" (vllm AgentX blog, OpenRouter economics).

## C–F. Expert canonical questions / archetypes / distrust / fields

Ranked at `docs/builder-concerns-2026-09-16/analysis.md`.

## G. Gap analysis

Ran against `directory/data/setups/*` (79 setups):
- Scores/concurrency present for many; **concurrency ceiling** only implicit.
- **Acceptance/decay curves** (draft acceptance %, decay to 250k) appear in
  prose of 9 setups, absent as fields anywhere.
- **KV pool size / KV quantization / KV offload** mostly in `caveats` prose
  (16 setups) rather than a field; only qwen3-8-27b has `kv_bytes_per_token`.
- **Offload** appears in `requirements.notes` for 9 setups; absent as a lane.
- **Thermals / power** — only hardware device blocks; no per-setup power.
- **Driver / runtime version** — only as pass 4 ledger notes; absent as a
  structured `run.version` or `engine.version`.
- **Correctness/quality** as independent evidence (canaries) exists only
  sparsely; there is no "did the output survive" field.
- **Speed/quality trade-off** (KV tople) too — you cannot tell from a setup row
  whether the fastest lane also produced the cleanest output.
- **Interconnect** (2× DGX Spark) is only in `engine.config` prose today.
- Deterministic **"does this satisfy my archetype"** verdicts come only from
  the My Hardware page, not from the recipe list.

## H. Suggested pilot recipes (8) — best coverage across expert concerns

Rationale at `docs/builder-concerns-2026-09-16/pilot.md`.
