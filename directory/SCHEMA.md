# Directory data model

One entry = **one runnable setup**: a specific model, a specific checkpoint
variation, a specific engine configuration, on specific hardware. That is the
unit that actually gets measured and actually gets run, so it is the unit the
directory stores.

A model with 8 checkpoints across 3 engines is 24 setups, not 1 row. They share
a `model` id and a `variation.checkpoint`, which is how the site groups them.

```
data/
├── models/<id>.json        the brain: architecture, context, modalities, license
├── hardware/<id>.json      the box: memory, bandwidth, arch + device spec
├── engines/<id>.json       the server: SGLang, vLLM, llama.cpp, ...
├── publishers.json         who made things: labs, quant shops, individuals
├── setups/<id>.json        one runnable setup  <- the main entity
├── device-schema.json      the contract for hardware[].device blocks
└── measurements.jsonl      optional: rows appended by bench/ab.py
```

Everything is validated by `validate.py`. Unknown ids and missing required
fields fail the build rather than silently rendering as blank.

## Provenance

The single most important rule in this dataset. Every number carries a
`provenance` field, and the site never mixes tiers:

| Tag      | Meaning                                    | Trust |
|----------|--------------------------------------------|-------|
| `box`    | Measured on our own hardware, method stated | high  |
| `forum`  | Reported by a community builder, linked     | mid   |
| `vendor` | Claimed by the publisher of the artifact    | low   |

`box` numbers must have `date`, `n`, and `method`. `forum` numbers must have
`source` (a URL to the thread or repo). `vendor` numbers must have `source`
(the model card or announcement). A number with no source is a validation
error — the fix is to delete it, not to downgrade the rule.

## setups/<id>.json

Required: `id`, `title`, `model`, `variation`, `engine`, `hardware`,
`requirements`, `run`, `provenance_tier`, `sources`.

```jsonc
{
  "id": "qwen38-27b-radixark-nvfp4-bf16head-sglang-dflash2-spark",
  "title": "Qwen3.8-27B NVFP4 (BF16 lm_head) — SGLang + DFlash2",
  "slug_note": "one line a human reads in a table",
  "model": "qwen3-8-27b",            // -> data/models/
  "status": "measured",              // measured | reported | claimed | untested

  "variation": {
    "checkpoint": "RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead",
    "publisher": "radixark",         // -> publishers.json
    "quant": "NVFP4",                // -> enums in validate.py
    "quant_detail": "W4A4 body, dense BF16 lm_head",
    "format": "safetensors",
    "size_gb": 24,
    "url": "https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead",
    "license": "Apache-2.0",
    "downloads": null                // HF popularity signal, null if unknown
  },

  "engine": {
    "id": "sglang",                  // -> data/engines/
    "config": "DFlash2 block-diffusion draft, EAGLE knobs N/A",
    "image": "lmsysorg/sglang:qwen38-27b-dflash2",
    "requires_fork": true,           // stock engine cannot do this
    "draft_model": "z-lab/Qwen3.8-27B-DFlash2@50307d4",
    "spec_decode": "dflash2",        // none | mtp | eagle | dspark | dflash2
    "flags": ["--mem-fraction-static 0.90", "--kv-cache-dtype fp8_e4m3"]
  },

  "hardware": ["dgx-spark"],         // -> data/hardware/, one or more
  "builder": "hasso5703",            // optional -> publishers.json; the person or
                                     // team whose recipe/numbers this setup is,
                                     // when different from the checkpoint publisher

  "requirements": {
    "memory_gb": 30,                 // resident: weights + KV + draft
    "disk_gb": 27,                   // download footprint
    "min_vram_gb": null,             // for discrete-GPU setups
    "notes": "~24GB target + ~2.6GB draft + KV pool"
  },

  "capabilities": {
    "vision": true, "video": true, "tools": true,
    "thinking": true, "long_context": 262144, "max_context": 1000000
  },

  "run": {
    "command": "./start-dflash.sh",
    "repo": "https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark",
    "repo_commit": "a1b2c3d4",             // optional: pin (sha or tag) the recipe was read from
    "profile": "profiles/qwen3.8-27b.env",   // local recipe card, if any
    "steps": [
      {"kind": "cmd", "text": "cp .env.sample .env"},
      {"kind": "cmd", "text": "./start-dflash.sh"},
      {"kind": "do", "text": "Wait for the model endpoint to become ready"}
    ],
    "auto_bootable": true                    // false = manual-only lane
  },

  "measurements": [
    {
      "metric": "decode_code",       // -> enums in validate.py
      "value": 50.9, "unit": "tok/s",
      "concurrency": 1,               // optional positive integer; simultaneous streams/clients in this measurement
      "stat": "median",               // optional: mean | median | peak
      "provenance": "box", "date": "2026-08-19", "n": 5,
      "method": "bench/ndec.py net-decode, median of 5, server completion_tokens",
      "range": [50.8, 51.1],
      "note": "ties DSpark inside the <15% noise band"
    }
  ],

  "caveats": ["Not compatible with YaRN / context >262144 — draft-config leak"],
  "provenance_tier": "box",          // best tier present in measurements
  "sources": [
    {"url": "https://github.com/MiaAI-Lab/...", "kind": "repo", "note": "recipe"},
    {"url": "https://huggingface.co/RadixArk/...", "kind": "model", "note": "weights"},
    {"url": "https://www.reddit.com/r/LocalLLaMA/comments/xyz/...", "kind": "thread",
     "mirror_url": "https://api.pullpush.io/reddit/search/submission/?ids=xyz",
     "note": "fetched via pullpush mirror 2026-09-10; quote below lifted from mirror payload"}
  ],
  "updated": "2026-09-05"
}
```

`run.steps` is an array of objects with exactly two fields: `kind` and `text`.
Use `kind: "cmd"` only when `text` is a shell command that can be run as shown;
use `kind: "do"` for prose instructions, UI actions, placeholders, or commands
that still need the reader to supply or interpret details. `kind` must be `cmd`
or `do`, and `text` must be a non-empty string. Legacy string entries are not
valid.

### metric enum

Speed and quality are kept in separate namespaces so the site can chart them
without mixing units.

- Speed: `decode_code`, `decode_essay`, `decode_chat`, `decode_agg`,
  `decode_per_stream`, `prefill_tok_s`, `ttft_ms`, `task_time_min`
- Quality: `quality_index`, `bench_code`, `bench_toolcall`, `bench_mmlu`
- Footprint: `memory_gb`, `disk_gb`

Anything not in the enum must be added to `validate.py` first. That friction is
deliberate: it stops the dataset from drifting into fifty one-off metric names
that cannot be compared.

`decode_agg` is reserved for throughput summed across simultaneous streams and
therefore requires `concurrency > 1`. A mean across sequential prompts or task
categories is `decode_per_stream` with `concurrency: 1` and `stat: "mean"`.
Use the optional `stat` field when a source distinguishes `mean`, `median`, or
`peak`; headline selection prefers a non-peak value when both are available.

Speed measurements may include `concurrency`, a positive integer recording the
number of simultaneous streams or clients used for that measurement. Leave it
unset when the source does not explicitly state measurement concurrency; do not
derive it from request counts, prompt counts, capacity claims, or config names.
`decode_agg` is total decode throughput across those parallel streams, while
`prefill_tok_s` is prompt-processing/read throughput and is not decode speed.

## device specs (hardware records, added 2026-09-10)

Hardware records carry an optional `device` block (contract:
`data/device-schema.json`; enforced by `validate.py`). It holds the specs that
actually determine local-inference performance — bandwidth sets the decode
roofline, capacity sets what fits — so readers can see why the same model
scores differently across classes. Provenance law applies: every published
figure in a device block traces to `device.sources[]`.

```jsonc
"device": {
  "identity": {"name": "NVIDIA DGX Spark", "chip": "GB10 Grace Blackwell",
               "manufacturer": "NVIDIA", "os": "DGX OS (Ubuntu)",
               "form_factor": "desktop", "sku": null},
  "memory":   {"total_gb": 128, "type": "LPDDR5X", "bandwidth_gbs": 273,
               "interface_bits": 256, "channels": null,   // only when published
               "unified": true, "usable_gb": 119, "note": null},
  "compute":  {"cpu_cores": "20-core Arm: 10x Cortex-X925 + 10x Cortex-A725",
               // every figure null unless the vendor publishes it:
               "fp32_tflops": null, "fp16_dense_tflops": null,
               "fp16_sparse_tflops": null, "fp8_dense_tflops": null,
               "fp8_sparse_tflops": null, "fp4_sparse_pflops": 1.0,
               "tensor_ai_tops": null, "neural_engine_tops": null,
               "note": "which figures are published, and what they mean"},
  "storage":  {"type": "NVMe M.2", "capacity_gb": 4096, "read_gbs": null},
  "thermal":  {"tdp_watts": 140, "psu_watts": 240, "cooling": "active fan"},
  "variants": [ // class records only: the exact SKUs, each verified
    {"id": "rtx-3090", "name": "GeForce RTX 3090", "chip": "GA102 (Ampere)",
     "memory_configs": "24 GB GDDR6X, 384-bit", "bandwidth_gbs": 936,
     "fp32_tflops": 35.6, "tdp_watts": 350}
  ],
  "sources": [{"url": "https://www.nvidia.com/...", "note": "which figures this backs"}]
}
```

Rules:

- **Placement.** The block lives in `data/hardware/<id>.json` — one spec per
  hardware class/SKU, never duplicated per setup. A setup may carry its own
  `device` key only as a measurement-specific override (same shape, no record
  cross-checks).
- **Class vs SKU.** Class records (with `bandwidth_range_gbs`) may set
  `memory.bandwidth_gbs: null` and enumerate `variants` instead; each variant
  bandwidth must fall inside the class range. Exact-SKU records must match
  their record's top-level `bandwidth_gbs` exactly.
- **null means unpublished.** A vendor figure that is not published stays
  `null` with a note — third-party estimates do not enter the dataset. Apple
  publishes Neural Engine TOPS but no GPU FLOPS; NVIDIA publishes FP4-sparse
  peaks for GB10 but no dense rates. Say what is missing, never a guess.
- **`memory.unified`** must be `true` for Apple records (CPU and GPU share one
  pool); `false` for discrete VRAM.
- **Backward compatible.** A hardware record without `device` passes with a
  warning naming the gap; setups without device specs are unaffected.

## Adding an entry

1. Copy `data/setups/_template.json`.
2. Fill every field you can verify. Use `null` for unknown — never a guess.
3. Every measurement gets a `source` unless `provenance` is `box`.
4. From the repository root, run `python3 directory/check.sh`. It validates the
   data, fetches every source URL, rebuilds `site/index.html`, and runs the
   browser suite. Every stage must pass.

## Conventions (added 2026-09-06, hygiene pass)

- **Source kinds** (`sources[].kind`): `repo`, `model`, `thread`, `post`,
  `video`, `docs`, `paper`, `blog`, `benchmark`, `other`. Forum threads and
  discussion tabs are `thread`; a builder's raw README is `docs`.
- **Licenses**: `variation.license` records the *weights'* license in SPDX
  display form (e.g. `Apache-2.0`). Where a builder repo or runtime carries
  different terms (Mia's AGPL scripts, a card tagged `other`), the weights
  license still goes in the field and the difference goes in `caveats`.
  A null license is a validation-era mistake: derive it from the base family
  and say so in a caveat.
- **Sizes**: `variation.size_gb` comes from the HuggingFace *tree* endpoint
  (`/api/models/<id>/tree/main?recursive=true`), summing safetensors shards or
  picking the GGUF/MLX file that matches the quant tier. The siblings endpoint
  returns 0 for LFS files and must not be used. A size of 0 or null is invalid.
- **Checkpoint ids** stay clean (`org/repo`); quant flavour parentheticals
  belong in `quant_detail`, never in `checkpoint`.
- **Context**: `models[].context.native` null means "the publisher did not
  state it", which is honest and allowed; the site renders it as unstated
  rather than blank-zero.
- **Identity**: two setups may share checkpoint + engine + hardware when their
  engine `config` differs (different spec-decode, runtime, or memory profile).
  The config string is part of a setup's identity; the validator's duplicate
  check includes it.
- **Family scope**: the model list covers Qwen 3.0/3.5/3.6/3.8 text, vision and
  omni branches that have a plausible local lane. Excluded on purpose:
  cluster-scale models (Qwen3.8-2.4T-A95B, Qwen3-Coder-480B-A35B), sub-4B edge
  models (no hardware class below a 24 GB GPU / 32 GB Mac), and
  Embedding/Reranker/ASR/TTS (not text-generation serving). There is no Qwen 4
  series as of the 2026-09-05 audit of the Qwen org.

## Social & archive conventions (added 2026-09-10, pass 4)

Social channels (X, YouTube, Reddit, GitHub discussions, vendor forums) are a
**discovery layer** (AGENTS law 9). A social find becomes a dataset entry only
through this ladder — the higher the rung, the more of the number survives:

1. **Names a durable artifact.** The post/video points at a GitHub repo or HF
   model card. The recipe is read from the repo (pinned via `run.repo_commit`,
   sha or tag, at fetch time) — never from the caption. Numbers stated in the
   post enter as `forum` with quote, date, method note and the post URL as an
   extra source; the artifact stays the primary source.
2. **No artifact, but fully stated.** The post gives hardware + engine config
   + command + measurement method explicitly. A `forum` number is allowed with
   the post as primary source (kind `post`/`video`/`thread`), rot-prone URLs
   archived (see below).
3. **Vaguer than that.** No number is recorded. The setup may still enter as
   `reported`/`untested` with the post as a discovery source, or not at all.

- **`sources[].mirror_url`** — required for any `reddit.com` URL (law 10):
  reddit hard-403s this environment, so the pullpush/arctic-shift mirror JSON
  is the verifiable evidence. `check_links.py` fetches the mirror and reports
  the permalink alongside it. The quote must match the mirror payload
  verbatim; the note records the fetch date.
- **Archive convention** — other rot-prone links (X posts, YouTube
  descriptions, forum posts likely to be deleted) carry an archive.today or
  web.archive.org URL in the source `note` when one exists.
- **Lineage dedupe** — N social posts about the same repo + engine + config +
  hardware collapse into one setup. The earliest or most complete post is the
  primary source; the rest are listed in `sources` as corroboration, never as
  separate rows.
- **New hardware classes** implied by social leads (Strix Halo, RDNA3 desktop,
  sub-24 GB GPUs) are an owner decision (AGENTS open decision 4); collect the
  candidate, do not create the class unilaterally.

## Maintenance tools

- `validate.py` — schema and enum enforcement; runs inside `build.py`.
- `check_links.py` — re-fetches every cited URL; exit 1 on any dead link.
  Run it before publishing: a dead source URL is a provenance failure.
- `import_bench.py` — regenerates `box` measurements from `bench/ab.py`
  results via `data/bench_map.json`; appends to `data/measurements.jsonl`.
- `verify_browser.py` — headless-Chromium behaviour checks against a served
  or live URL; dataset-size agnostic.
- `tools/vet_candidates.py` — pre-merge vetting for research-pass candidates:
  enums (imported from `validate.py`, no drift), URL liveness, duplicates,
  Scenario B prune gates (law 11), plausibility (fit + bandwidth roofline),
  lineage dedupe.
- `tools/social_candidates.py` — pass-4 collector: fetches X (fxtwitter),
  YouTube, Reddit (pullpush mirror), GitHub discussions/issues (`gh`), and
  Discourse forums (HF, NVIDIA) into
  `tools/history/inputs/pass4-social/` (raw payloads + ledger).
- `tools/coverage.py` — facet coverage tables (generation, format, quant,
  engine, hardware, provenance, status) from the current dataset.
