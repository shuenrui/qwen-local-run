# Expert causal-evidence rubric and schema proposal

Task #13 — Gwen, 2026-09-16.

**Status:** proposal only. This document does not edit `directory/data/`, `directory/SCHEMA.md`, `directory/validate.py`, `directory/site_src/`, or `directory/site/index.html`, and it does not merge or publish anything.

Inputs:

- `docs/builder-concerns-2026-09-16/corpus.md`
- `docs/builder-concerns-2026-09-16/analysis.md`
- `docs/builder-concerns-2026-09-16/pilot.md`
- `docs/builder-concerns-2026-09-16/pilot-dossiers/`
- `docs/builder-concerns-2026-09-16/builder-questions.md`
- `directory/SCHEMA.md`
- `directory/validate.py`
- current dataset audit: 79 setups and 190 measurements. The data snapshot is unchanged since `fc8d9d1`; this revision was audited at HEAD `c6cdee7`, whose only changes were CSS/generated-site typography and dark-theme contrast.

## 1. Problem

The directory already has a strong provenance law: every number carries `box`, `forum`, or `vendor` provenance and a source. But provenance answers **who reported it**, not **what the evidence can causally support**.

The pilot research shows expert builders ask sharper questions:

- Was the speed number produced by a benchmark harness, server telemetry, or wall-clock division?
- Was the comparison matched, or were context, workload, concurrency, offload, or engine build different?
- Did one builder change a bundle of kernel patches, or one variable?
- Was output correctness checked, or could the run be fast and silently corrupt?
- Is a second source an independent reproduction, a quote, a similar crowd-sourced sanity range, or the same author across X/YouTube/README?
- Which exact engine revision, fork branch, container digest, model revision, hardware variant, and offload configuration produced the number?

The current schema cannot express those distinctions except in prose. That is the gap this proposal addresses.

## 2. Design principles

1. **Provenance, causal strength, condition completeness, and output verification remain separate axes.** They must never be blended into one trust score.
2. **Recorded or absent.** A missing fact stays `null` or omitted. It is never inferred from memory arithmetic, speedup ratio, hardware class, current HEAD, or similar recipes.
3. **Lineage-based independence.** One actor/artifact/campaign is one lineage, even when it appears on X, YouTube, a README, and a model card.
4. **Negative results are first-class.** Failures, contradictions, weak methods, and unresolved ambiguities stay visible.
5. **Backward compatible.** All proposed fields are optional additive blocks. Legacy records remain valid at `schema_version` absent/1.
6. **Durable source first.** Social posts remain discovery or direct testimony; repository/card/forum artifacts remain primary where available.
7. **No quality leaderboard.** Quality canaries are recorded per setup with harness and source; they are never aggregated into a cross-setup score.
8. **Historical pins only.** A revision pin must be supported by dated evidence. Current HEAD is never substituted for an older run.

## 3. Independent evidence axes

| Axis | Existing/new | Meaning | Example |
|---|---|---|---|
| `provenance` | existing | who reported the number | `box`, `forum`, `vendor` |
| `status` | existing | recipe lifecycle | `measured`, `reported`, `claimed`, `untested`, `broken` |
| `evidence_level` | new | causal/observational strength | `c2_observation`, `c3_matched_ab` |
| `contrast_kind` | new | whether a comparison isolates one variable | `single_variable`, `bundle`, `uncontrolled`, `claimed`, `none` |
| `condition_completeness` | derived | how much benchmark context is recorded | `full`, `partial`, `insufficient` |
| `method_grade` | new | how the number was produced | `server_telemetry`, `wall_clock_division` |
| `quality_status` | new | whether output correctness/quality was checked | `unchecked`, `pass`, `fail`, `mixed`, `recorded` |
| `independent_lineages` | derived | distinct reproduction lineages | `0`, `1`, `2+` |

A fast forum number can be `c2_observation`, derived `condition_completeness: partial`, `method_grade: author_report`, `quality_status: unchecked`, `0 independent lineages`. That is honest and still useful. It must not be displayed as though it were a controlled, verified benchmark.

## 4. Causal-evidence rubric

### 4.1 Evidence levels

| Level | Name | Definition | Required support | Allowed language | Forbidden language |
|---|---|---|---|---|---|
| `c0_claim` | Assertion | A vendor/builder/headline asserts an outcome without sufficient measurement conditions. | Source and quote. | “claims”, “headline says”, “vendor states” | “demonstrates”, “proves”, “verified” |
| `c1_configuration` | Configuration fact | A durable artifact establishes what was run: command, flags, version, fork, topology, offload design, memory decomposition. | Source and locator. | “configured as”, “requires”, “documented mechanism” | “therefore achieves”, “causes speedup” |
| `c2_observation` | Observed association | One measured outcome under recorded conditions. | Measurement, source, date, provenance, method or explicit unknown. | “reported X under recorded conditions”, “observed with” | “because”, “causes”, “will reproduce” |
| `c3_matched_ab` | Matched contrast | The same lineage records two sides of a comparison with relevant conditions held constant or explicitly named. | Both sides, shared conditions, unstated conditions, source/quote, and explicit binary/runtime provenance status. | “in this author-reported matched run”, “within this source and scope” | “verified”, “proved”, universal causality across hardware/engine versions, or hiding unresolved binary provenance |
| `c4_independent_reproduction` | Independent reproduction | A distinct lineage reproduces the observation or contrast under the same relevant configuration. | ≥2 distinct lineages and reproduction evidence. | “independently reproduced by N lineages” | counting quotes/crowd ranges as reproductions |

Quality/correctness is **not** an evidence level. It is the separate `quality_status` axis and must be linked to a correctness check or quality measurement covering the same configuration/run scope. A C3 or C4 result may have `quality_status: pass`, but it is never folded into `evidence_level`.

Levels are not a single promotional ladder in every dimension. A `c3_matched_ab` with `contrast_kind: bundle` may be weaker for component attribution than a `c2_observation` of one component. UI and dossiers must show level, contrast kind, and quality status separately.

### 4.2 Contrast kinds

| Value | Meaning | Causal specificity |
|---|---|---|
| `none` | No comparison. | None. |
| `claimed` | Source asserts a comparison but does not record both sides or conditions. | Cannot support causality. |
| `uncontrolled` | Two observations exist, but a material condition differs or is unstated. | Association only. |
| `bundle` | Matched contrast where multiple changes were introduced together. | Supports “the stack changed the outcome,” not which lever caused it. |
| `single_variable` | Matched contrast where one relevant variable changed and material conditions are recorded/constant. If runtime/binary provenance is unresolved, the record must say so and may only support an author-reported scoped association, not a verified universal cause. | Supports a scoped causal statement, with explicit unresolved-provenance caveats when present. |

Examples, calibrated against Terra’s instruction that the pilot set contains only one local matched A/B candidate and Openkod’s binary-provenance nuance for pilot 02:

- **RTX 4090, DFlash2 90 vs native MTP 68.09 tok/s:** the only pilot-set example eligible for `c3_matched_ab` + `single_variable`, but it must be labelled **“author-reported matched comparison; partial condition completeness; binary provenance unresolved.”** The recorded protocol matches box/quant/KV set/prompt set/`--parallel 1`; it does not yet establish that both arms used the same llama.cpp binary or pinned baseline build. It remains single-lineage, has no `n`, has `quality_status: unchecked`, and must not use “verified” wording.
- **RTX 4090 prefill, DFlash2 1,662 vs MTP 2,324 tok/s:** same rubric and same unresolved binary-provenance caveat, with the negative result preserved: DFlash2 wins decode but loses prefill.
- **2× DGX Spark, MTP off 24.5 → MTP=3 52.1 tok/s:** `c2_observation` with `contrast_kind: uncontrolled`, not full C3. The README table is strong server telemetry, but the dossier records no raw full A/B, the repo pin is ambiguous, and the checkpoint-path discrepancy is unresolved. Pinning alone is not sufficient for C3; all four promotion facts must be established: both arms, same server/config/workload, MTP as the sole toggled variable, and resolution of the checkpoint-path discrepancy. Otherwise a clean 2× Spark rerun is the route to C3.
- **Strix Halo baseline 16.8 → full stack 47.1 tok/s:** `c2_observation`, `contrast_kind: bundle`. The source changed multiple kernel/loader/speculative levers together and lacks a full benchmark protocol, so it cannot support component-level causality or count as the pilot set’s matched A/B.
- **M3 Ultra Atomic Chat 23 → 87.6 tok/s:** `c2_observation` plus a `claimed` or `uncontrolled` comparison, not C3, because context, workload, flags, and protocol are unstated.
- **RTX PRO 6000 “100 → 170 tok/s”:** `c0_claim` or at best `c2_observation` with insufficient conditions; the chart does not restate quant, context, workload, concurrency, or offload per point.
- **Ollama RTX 3090 40.2 tok/s:** `c2_observation`, `method_grade: wall_clock_division`; the crowd range is corroboration, not `c4`.

A `c3_matched_ab` grade therefore requires an explicitly recorded matched protocol or enough constants to identify one changed variable. Table adjacency alone is not sufficient. When the stated protocol isolates a variable but engine/binary provenance is unresolved—as in pilot 02—the record may be C3 only as an **author-reported matched comparison with partial condition completeness**; it must carry the unresolved-build open question/re-review trigger and may not be rendered as “verified,” “proved,” or generally reproducible.

### 4.3 Lineage, corroboration, reproduction

A **lineage** is one actor/artifact/experiment campaign:

- same author across X, YouTube, README, and model card = one lineage;
- same vendor card and vendor social account = one lineage;
- same repository README and its announcement = one lineage;
- a fork or rehost with no new measurement = same lineage;
- a quote/repost = corroboration of the source, not independent evidence.

**Corroboration** means another source makes the claim more findable or plausible, but does not independently run it. The Ollama 3090 crowd range `38.2–45.6 tok/s` is a sanity range, not reproduction.

**Independent reproduction** requires:

1. a distinct actor/lineage;
2. an actual run or measurement, not a quote;
3. the same checkpoint/format/quant or an explicitly recorded equivalent;
4. the same engine/fork/version or recorded difference;
5. the same hardware class/count/variant or recorded difference;
6. the same relevant workload/context/concurrency/offload/speculative configuration or recorded difference.

If any material condition differs and is not accounted for, classify as `approximate_corroboration`, not reproduction.

### 4.4 Condition completeness

For speed measurements, proposed derived grades:

- **`full`**: metric, value, unit, date/source/provenance, exact context or verbatim context label, workload, concurrency, method or harness, `stat`/`n` where source distinguishes them, and the materially relevant configuration state (spec decode, offload, KV, hardware count/variant, backend/version) are recorded.
- **`partial`**: value/source/date plus some but not all required conditions.
- **`insufficient`**: value/source/date with vague or absent conditions.

`condition_completeness` should be computed by the validator/UI, not hand-stored, so it cannot drift from the actual fields.

### 4.5 Method grades

| Value | Meaning | Pilot example |
|---|---|---|
| `server_telemetry` | Read from a running server/container/engine logs or table explicitly described as server-read. | MiaAI dual-Spark README: numbers read from `docker logs` / `docker inspect`. |
| `benchmark_harness` | Named harness/command, e.g. `llama-perplexity`, `llama-bench`, vLLM benchmark client. | AtomicChat KL/top-1 protocol. |
| `vendor_published_table` | Vendor table/card without enough protocol detail to classify as a harness run. | AtomicChat 2×5090 speed table; Unsloth RTX PRO chart. |
| `author_report` | Builder states a result without a named harness or logs. | Atomic Chat M3 Ultra reply. |
| `wall_clock_division` | Tokens divided by elapsed wall-clock time. | Ollama 3090 `482 tokens / ~12s`. |
| `crowd_report` | Third-party community report or aggregator row. | llamabench.ai sanity range. |
| `unspecified` | Source does not say. | Must render as “method not stated.” |

Method grade never changes provenance tier. A `box` measurement can still be weak if wall-clock; a `vendor` measurement can be strong if it publishes a reproducible harness and quality protocol.

### 4.6 Correctness and quality

Two separate concepts:

1. **Output correctness**: did the run emit usable output? Examples: byte-clean long-prompt check, manual read, needle-in-haystack, accuracy evaluator, observed multilingual-noise failure.
2. **Quality canary**: KL divergence, perplexity, top-1 retention, GSM8K/HumanEval/benchmarks. These are recorded per setup with harness/source and never aggregated into a leaderboard.

A speed measurement may only receive `quality_status: pass` or `recorded` when the correctness/quality evidence explicitly covers the same configuration and run scope. A vendor card that publishes a quant quality table does not automatically verify every speed row on that card.

### 4.7 Causal-claim admissibility

A stored claim must have:

- explicit `statement`;
- `technique_id` when it describes a named recipe lever;
- source URL and locator;
- verbatim `quote` or linked comparison/measurement IDs for any observation/performance/quality/failure outcome; for a durable `c1_configuration` mechanism or configuration fact, an exact locator may serve as support until the verbatim quote is archived;
- `cause` and `effect` when the claim asserts a mechanism or outcome;
- `scope`: hardware, engine, checkpoint/quant, context/workload/concurrency where known;
- `evidence_level`;
- `contrast_kind` when comparative;
- `lineage_id`;
- known `contradictions` and `open_questions`;
- `binary_provenance_status` and a re-review trigger when a C3 attribution depends on unresolved engine/build provenance.

Rules:

- `c0`/`c1` may describe intended mechanism or configuration, but may not attach an outcome magnitude.
- `c2` may describe association only.
- Component-level causality requires `c3_matched_ab` + `contrast_kind: single_variable`. When binary/runtime provenance is unresolved, UI must say “author-reported matched comparison” and may not use verified/universal wording.
- Bundle causality requires `c3_matched_ab` + `contrast_kind: bundle`, and UI must say the individual lever is not isolated.
- `c4` requires distinct lineages, not URLs.
- `quality_status` is separate from `evidence_level`. A quality check may be attached to a measurement, comparison, or claim only when it explicitly covers the same configuration/run scope; it never upgrades `evidence_level` by itself.
- Contradictions do not delete the original claim; they are stored beside it.

## 5. Proposed schema additions

All fields are optional and additive. A record using them should set:

```jsonc
"schema_version": 2
```

Absent `schema_version` means legacy record.

### 5.1 Source-object extensions

Current `sources[]` entries should gain auditability fields:

```jsonc
{
  "url": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks",
  "kind": "repo",
  "note": "README server-read benchmark tables",
  "locator": "README lines 172, 179, 269, 375, 405",
  "retrieved": "2026-09-16",
  "archive_path": "docs/builder-concerns-2026-09-16/raw/repo_MiaAI-Lab_Flash-Next-Dual-DGX-Sparks_README.md",
  "lineage_id": "mia-ai-lab-dual-spark",
  "quote": null,
  "mirror_url": null
}
```

Rules:

- `locator` is required for dossier-derived evidence when the archive supports it.
- `archive_path` is required for rot-prone social/video evidence already archived by Openkod.
- `retrieved` is required for undated durable pages, such as the Unsloth docs page.
- `lineage_id` must resolve to `evidence.lineages[]`.
- Reddit mirror law remains unchanged.

### 5.2 Revision pins

Extend `run`:

```jsonc
"run": {
  "repo": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks",
  "repo_commit": null,
  "repo_revision": {
    "commit": "6e08722d1fad",
    "branch": null,
    "tag": null,
    "anchor_date": "2026-08-26",
    "resolution": "earliest_commit_after_anchor",
    "ambiguous": true,
    "source": "docs/builder-concerns-2026-09-16/pilot-dossiers/00-INDEX.md",
    "note": "Repo was bootstrapped after the recipe anchor; no historically exact commit exists."
  }
}
```

Extend `variation`:

```jsonc
"variation": {
  "revision": null,
  "revision_date": null,
  "snapshot_url": null,
  "revision_note": "HF card is a moving target; vendor re-quantizes/re-measures."
}
```

Rules:

- `resolution` enum: `exact`, `branch_on_anchor`, `earliest_commit_after_anchor`, `tag`, `page_retrieval`, `image_digest`, `unresolved`.
- `ambiguous: true` must be preserved in UI.
- Never substitute current HEAD without temporal evidence.
- If `repo_commit` and `repo_revision.commit` both exist, they must agree.

### 5.3 Hardware variant selection

Allow the existing hardware reference object to carry an exact variant:

```jsonc
"hardware": [
  {
    "id": "rtx-pro-6000",
    "count": 1,
    "variant_id": null,
    "variant_ambiguous": true,
    "variant_note": "Source says RTX PRO 6000 but does not distinguish Workstation 1792 GB/s from Server 1597 GB/s."
  }
]
```

Rules:

- `variant_id`, when present, must exist in the hardware record’s `device.variants[]`.
- `variant_ambiguous: true` is allowed only with a note/source.
- Exact variant must not be inferred from class name.

### 5.4 Engine/runtime and speculative decoding

Extend `engine`:

```jsonc
"engine": {
  "id": "llama-cpp",
  "config": "existing verbatim config string",
  "image": "existing image tag",
  "image_digest": "sha256:...",
  "version": null,
  "backend": "rocm",
  "requires_fork": true,

  "fork_revision": {
    "repo": "https://github.com/drluoto/llama.cpp",
    "branch": "strix-halo-flash-next",
    "commits": ["ea9f94fc7625", "59a40b56ff79"],
    "anchor_date": "2026-08-29",
    "resolution": "branch_on_anchor",
    "ambiguous": false,
    "source": "docs/builder-concerns-2026-09-16/pilot-dossiers/00-INDEX.md",
    "note": null
  },

  "kernel_patches": [
    {
      "id": "gpu-top-k",
      "pr": "#26592",
      "commit": null,
      "purpose": "Avoid HIP CPU fallback for TOP_K past ne=1024",
      "source": "..."
    }
  ],

  "environment": {
    "os": null,
    "driver": null,
    "cuda": null,
    "rocm": "7.1",
    "metal": null,
    "python": null,
    "packages": {"huggingface_hub": ">= recorded version"},
    "source": "...",
    "date": "...",
    "note": null
  },

  "draft_model": "existing field",
  "spec_decode": "mtp",
  "spec_decode_profile": {
    "draft_checkpoint": "drluoto/Qwen3.8-Flash-Next-MTP-GGUF",
    "draft_revision": "57ab3265056d",
    "draft_quant": "Q8_0",
    "max_draft_tokens": null,
    "acceptance_rate_pct": null,
    "acceptance_basis": null,
    "decay_curve": [
      {
        "context_tokens": 26000,
        "acceptance_rate_pct": null,
        "decode_per_stream_tok_s": 75.66,
        "source": "...",
        "note": null
      }
    ],
    "source": "...",
    "date": "...",
    "provenance": "forum"
  },

  "flags": ["--spec-type draft-mtp,ngram-mod"]
}
```

Enums:

- `backend`: `cuda`, `rocm`, `metal`, `vulkan`, `cpu`, `opencl`, `other`, `null`.
- `spec_decode` remains existing enum.
- `spec_decode_profile.method`, when present, must agree with `engine.spec_decode`.

Rules:

- `acceptance_rate_pct` must be 0–100 and source-backed.
- Acceptance must not be inferred from speedup ratio.
- A decay curve may record speed points without acceptance rates, but must not label them acceptance.
- `engine.version` may remain null; the UI already has a compare row for it and should render “not recorded.”

### 5.5 Memory decomposition and offload

Extend `requirements`:

```jsonc
"requirements": {
  "memory_gb": 64,
  "disk_gb": 133,
  "min_vram_gb": null,
  "notes": "existing prose note",

  "memory_profile": {
    "entries": [
      {
        "component": "weights",
        "value": 62.72,
        "unit": "GB",
        "scope": "per_unit",
        "location": "unified",
        "pageable": false,
        "context_tokens": null,
        "kv_tokens": null,
        "source": "...",
        "note": "64.3 GiB with MTP"
      },
      {
        "component": "cache_table",
        "value": 51,
        "unit": "GB",
        "scope": "total",
        "location": "gpu",
        "pageable": false,
        "source": "...",
        "note": "PLE_OFFLOAD=false for this run"
      },
      {
        "component": "kv_pool",
        "value": 32.02,
        "unit": "GiB",
        "scope": "total",
        "location": "gpu",
        "context_tokens": 262144,
        "kv_tokens": 3652200,
        "source": "...",
        "note": "README states 32.02 GiB ≈ 3,652,200 tokens"
      }
    ],
    "kv_dtype": "fp8_e4m3",
    "gpu_memory_utilization": 0.835,
    "provenance": "forum",
    "date": "2026-08-26"
  },

  "offload": {
    "strategy": "none",
    "components": [],
    "intentional": false,
    "cold_start_effect": null,
    "source": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks",
    "locator": "README measured-run configuration: PLE_OFFLOAD=false",
    "provenance": "forum",
    "date": "2026-08-26",
    "note": "Explicitly recorded no PLE offload for this run. Absence of offload prose is not evidence of `none`. rsync/NFS weight distribution is recorded under `interconnect`, not inferred as runtime offload."
  }
}
```

For the Mac64 pageable-PLE case:

```jsonc
"offload": {
  "strategy": "pageable_ple",
  "components": ["cache_table"],
  "intentional": true,
  "cold_start_effect": null,
  "source": "https://huggingface.co/AtomicChat/Qwen3.8-Flash-Next-GGUF",
  "locator": "model-card memory/PLE dependency section",
  "provenance": "vendor",
  "date": "2026-09-10",
  "note": "84.9 GB file set exceeds 64 GB physical RAM by design. The source records the intended pageable-PLE mechanism; it does not record a measured cold-start latency, so `cold_start_effect` remains null."
}
```

The intended Mac64 mechanism is represented as a C1 claim, not as an observed effect:

```jsonc
{
  "id": "pageable-ple-enables-oversize-build",
  "technique_id": "pageable-ple",
  "kind": "mechanism",
  "statement": "The 84.9 GB build can run on a 64 GB Mac because the 39.1 GB n-gram PLE table is intentionally pageable rather than fully resident.",
  "evidence_level": "c1_configuration",
  "lineage_id": "atomicchat-hf-card",
  "source": "https://huggingface.co/AtomicChat/Qwen3.8-Flash-Next-GGUF",
  "locator": "model-card memory/PLE dependency section",
  "quote": null,
  "scope": {
    "hardware": [{"id": "mac-studio-m3-ultra", "memory_gb": 64}],
    "engine": ["llama.cpp"],
    "quant": ["Q4_K_XL"]
  },
  "status": "recorded",
  "note": "Intended mechanism. No measured cold-start penalty is encoded because the source does not report one."
}
```

Enums:

- `component`: `weights`, `kv_pool`, `draft`, `cache_table`, `projector`, `activation`, `runtime_overhead`, `other`.
- `unit`: `GB`, `GiB`, `MB`, `MiB`.
- `scope`: `total`, `per_unit`.
- `location`: `gpu`, `unified`, `host_ram`, `ssd`, `mixed`, `null`.
- `offload.strategy`: `none`, `layer_offload`, `kv_offload`, `pageable_ple`, `mmap`, `nfs_weight_share`, `hybrid`, `other`.

Rules:

- Preserve source units; do not silently normalize GiB to GB.
- `requirements.memory_gb` remains the existing normalized fit/filter field.
- Offload must not be inferred from `size_gb > hardware.memory_gb`. The RTX PRO 6000 case should record an open question, not an assumed offload strategy.
- `offload.strategy: none` requires an explicit source/locator recording that offload was disabled or absent for that run. Silence, omission, or missing offload prose is not sufficient.
- `cold_start_effect` may record only an observed/measured outcome. An intended mechanism or expected penalty belongs in a C1 `evidence.claims[]` entry until a source records the actual outcome.
- `kv_pool_gb` may be recorded only when source states it or provides exact arithmetic in the cited artifact. The My Hardware estimator may still compute user-facing estimates separately, clearly labeled as estimates.

### 5.6 Interconnect and serving profile

Top-level:

```jsonc
"interconnect": {
  "kind": "roce",
  "topology": "two_node",
  "role": "tensor_parallel",
  "bandwidth_gbs": null,
  "requires_same_fabric": true,
  "source": "...",
  "date": "...",
  "note": "ConnectX RoCE/IB; passwordless SSH; weights shared via rsync or NFS"
}
```

```jsonc
"serving": {
  "workload": null,
  "batching": null,
  "scheduler": null,
  "prefix_cache": null,
  "session_affinity": null,
  "concurrency_ceiling": 64,
  "ceiling_effect": "throughput_regression",
  "ceiling_reason": "Above roughly 64 concurrent requests, draft-and-verify overhead outweighed savings.",
  "source": "...",
  "date": "...",
  "provenance": "forum"
}
```

Enums:

- `interconnect.kind`: `none`, `pcie`, `nvlink`, `roce`, `infiniband`, `thunderbolt`, `usb`, `network`, `other`, `null`.
- `interconnect.role`: `tensor_parallel`, `pipeline_parallel`, `expert_parallel`, `kv_replication`, `weight_share`, `other`, `null`.
- `serving.workload`: `chat`, `code`, `essay`, `file_rewrite`, `agent`, `needle_haystack`, `benchmark`, `mixed`, `other`, `null`.
- `serving.batching`: `static`, `continuous`, `chunked_prefill`, `other`, `null`.
- `serving.ceiling_effect`: `throughput_regression`, `latency_regression`, `oom`, `crash`, `quality_failure`, `preemption`, `other`.

Rules:

- `concurrency_ceiling` is only an explicit source-recorded ceiling/failure point.
- Do not derive it from `max(measurements[].concurrency)`.
- Aggregate vs per-stream remains encoded by metric and measurement concurrency.

### 5.7 Correctness and known failures

Top-level:

```jsonc
"correctness": {
  "output_checked": true,
  "checks": [
    {
      "kind": "byte_clean",
      "result": "pass",
      "scope": "long prompts",
      "context_tokens": null,
      "measurement_ids": [],
      "source": "...",
      "quote": "Output verified byte-clean at long prompts",
      "date": "2026-08-29",
      "lineage_id": "drluoto-strix-halo"
    }
  ],
  "quality_measurement_ids": [],
  "known_output_failure": null
}
```

```jsonc
"known_failures": [
  {
    "id": "strix-halo-rocm10-mtp-load",
    "stage": "load",
    "trigger": "ROCm 10.0",
    "effect": "Detached MTP sidecar reports n_layer_nextn=0 and missing tensor",
    "status": "open",
    "observed_date": "2026-09-03",
    "lineage_id": "community-commenter",
    "source": "...",
    "quote": "...",
    "resolution": null
  }
]
```

Enums:

- correctness `kind`: `byte_clean`, `manual_read`, `needle_haystack`, `accuracy_evaluator`, `kl_divergence`, `ppl`, `top1_retention`, `benchmark`, `other`.
- correctness `result`: `pass`, `fail`, `mixed`, `recorded`, `unknown`.
- failure `stage`: `download`, `load`, `prefill`, `decode`, `output`, `serve`, `crash`, `oom`, `other`.
- failure `status`: `open`, `fixed`, `workaround`, `intermittent`.

Rules:

- A known failure does not automatically set setup `status: broken`; use `broken` only when the exact recorded recipe fails in its stated environment.
- Output-correctness failure must remain visible in Lite.

### 5.8 Capability observations

The existing `capabilities` block records nominal model/setup capabilities. The pilots show that a capability can be broken, untested, or require an extra artifact in a specific engine/fork. Add setup-level observations without changing the nominal booleans:

```jsonc
"capability_observations": [
  {
    "capability": "video",
    "status": "broken",
    "trigger": "llama.cpp PR #27342",
    "scope": "this setup only; the model family may support video elsewhere",
    "source": "...",
    "quote": "Multi GPU and multimodality is currently broken",
    "date": "2026-08-19",
    "lineage_id": "analogalok-4090-dflash2"
  },
  {
    "capability": "vision",
    "status": "requires_extra_artifact",
    "trigger": "separate mmproj download",
    "scope": "AtomicChat Flash-Next GGUF on llama.cpp/Metal",
    "source": "...",
    "quote": null,
    "date": "2026-09-10",
    "lineage_id": "atomicchat-flash-next-card"
  }
]
```

Enums:

- `capability`: `vision`, `video`, `tools`, `thinking`, `long_context`, `structured_output`, `other`.
- `status`: `works`, `reported`, `broken`, `requires_extra_artifact`, `not_supported`, `not_tested`, `unknown`.

Rules:

- A nominal `capabilities.vision: true` must not be displayed as setup-verified when a `broken`, `not_tested`, or `requires_extra_artifact` observation exists.
- Observations are setup-scoped and source-backed; they never modify the model record.
- Long-context observations should record the tested context and workload when available, not merely the model maximum.

### 5.9 Measurement IDs, conditions, and evidence

Add stable IDs and structured conditions to each measurement:

```jsonc
{
  "id": "m2",
  "metric": "decode_per_stream",
  "value": 52.1,
  "unit": "tok/s",
  "stat": null,
  "n": null,
  "concurrency": 1,
  "context": "batch-1 greedy, MTP=3: 2.13x; draft acceptance 72.8% (823/1131)",

  "conditions": {
    "context_tokens": null,
    "context_label": "batch-1 greedy",
    "prompt_tokens": null,
    "completion_tokens": null,
    "workload": null,
    "greedy": true,
    "thinking": null,
    "temperature": null,
    "warm": null,
    "client": null,
    "hardware_count": 2,
    "hardware_variant_id": null,
    "backend": null,
    "spec_decode": "mtp",
    "max_draft_tokens": 3,
    "kv_dtype": "fp8_e4m3",
    "offload_strategy": null,
    "power_limit_pct": null,
    "clock_state": null
  },

  "evidence": {
    "level": "c2_observation",
    "contrast_id": "mtp-off-vs-mtp3",
    "contrast_kind": "uncontrolled",
    "lineage_id": "mia-ai-lab-dual-spark",
    "method_grade": "server_telemetry",
    "quality_status": "unchecked",
    "independent_reproductions": 0,
    "corroborations": [],
    "quote": null,
    "note": "README server table reports MTP off/on side by side, but no raw full A/B protocol exists and the repo pin/checkpoint-path discrepancy is unresolved. This is not a full local matched A/B."
  },

  "provenance": "forum",
  "date": "2026-08-26",
  "source": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks",
  "method": "README server-read benchmark table",
  "note": null,
  "range": null
}
```

Rules:

- `id` is required for any measurement referenced by a claim, comparison, correctness check, or quality canary. Migration should assign stable IDs to all migrated measurements and flag the subset actually cited by dossiers.
- Existing top-level `concurrency` remains canonical for backward compatibility. If `conditions.concurrency` exists, it must agree.
- Existing `context` remains a verbatim source label. New `conditions.context_tokens` is exact tokens; `context_label` preserves approximate source language such as `~30k`.
- `evidence.level` applies to that measurement, not the whole setup.
- `evidence.quality_status` is separate from `evidence.level` and must never be encoded as a causal level.
- `evidence.method_note` is optional for normal methods and required for `wall_clock_division`; UI must render it beside the number and must not use the measurement as a headline/comparability anchor.
- `independent_reproductions` counts distinct lineages, not URLs.
- `corroborations[]` may record sanity ranges and quotes; they never count as reproductions.

### 5.10 Setup evidence block

```jsonc
"evidence": {
  "rubric_version": "1.0",

  "lineages": [
    {
      "id": "mia-ai-lab-dual-spark",
      "actor": "MiaAI-Lab",
      "publisher": "mia-ai-lab",
      "kind": "builder_repo",
      "sources": ["https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks"],
      "note": "README and announcement are one lineage."
    }
  ],

  "claims": [
    {
      "id": "fp8-block-scales-required",
      "technique_id": "fp8-block-scales-routed-experts",
      "statement": "Without the FP8_BLOCK_SCALES routed-experts patch, the MoE can load unquantized and die roughly seven minutes in.",
      "kind": "failure_mode",
      "cause": {"field": "run.start_script_patch", "value": "FP8_BLOCK_SCALES routed-experts patch"},
      "effect": {"stage": "load", "outcome": "crash_or_unquantized_moe"},
      "evidence_level": "c1_configuration",
      "contrast_kind": "none",
      "lineage_id": "mia-ai-lab-dual-spark",
      "scope": {"engine": ["vllm"], "hardware": [{"id": "dgx-spark", "count": 2}]},
      "source": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks",
      "locator": "README line 89 / patch notes",
      "quote": "FP8_BLOCK_SCALES routed-experts patch (missing upstream — without it the MoE loads unquantized and dies ~7 min in)",
      "status": "recorded",
      "contradictions": [],
      "note": null
    }
  ],

  "comparisons": [
    {
      "id": "mtp-off-vs-mtp3",
      "question": "What association does the README table report between MTP off and MTP=3 at batch 1?",
      "candidate_variable": "engine.spec_decode_profile.max_draft_tokens",
      "a": {"label": "MTP off", "measurement_id": "m1"},
      "b": {"label": "MTP=3", "measurement_id": "m2"},
      "result": "b_better",
      "effect_metric": "decode_per_stream",
      "effect_direction": "increase",
      "contrast_kind": "uncontrolled",
      "conditions_constant": [
        "hardware_count=2 as stated in recipe/table",
        "batch-1 greedy label in README server-read table",
        "same MiaAI-Lab README server telemetry source"
      ],
      "conditions_unstated": [
        "raw full A/B command",
        "prompt corpus",
        "exact context tokens",
        "sample size / n",
        "same server configuration and workload across both arms",
        "MTP toggle as sole changed variable",
        "checkpoint-path discrepancy resolution",
        "repo/build pin"
      ],
      "evidence_level": "c2_observation",
      "lineage_id": "mia-ai-lab-dual-spark",
      "independent_reproductions": [],
      "quality_status": "unchecked",
      "source": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks",
      "locator": "README server-read benchmark table",
      "quote": null,
      "promotion_gate": {
        "target_level": "c3_matched_ab",
        "target_contrast_kind": "single_variable",
        "required_facts": [
          "both arms identified",
          "same server configuration and workload",
          "MTP is the sole toggled variable",
          "checkpoint-path discrepancy resolved"
        ],
        "status": "not_met",
        "note": "Pinning alone is not enough. If the four facts cannot be established from existing artifacts, a clean 2× Spark rerun is required for C3."
      },
      "note": "Not the pilot-set C3 example. Only pilot 02 is currently eligible for C3/single_variable with unresolved binary provenance."
    }
  ],

  "contradictions": [
    {
      "id": "tweet-vs-readme",
      "statement": "Announcement claims ~64 tok/s single stream and ~115 tok/s at 2–4 concurrent; repo tables record 52.1–54.4 batch-1 and 86.5–128.1 at x2–x4.",
      "resolution": "Repo numbers admitted under law 9; tweet remains discovery.",
      "status": "resolved_by_source_priority",
      "sources": ["..."],
      "lineage_ids": ["mia-ai-lab-dual-spark"]
    }
  ],

  "open_questions": [
    {
      "id": "repo-pin-ambiguous",
      "question": "No commit exists on/before the 2026-08-26 recipe anchor.",
      "blocks": ["exact_reproduction"],
      "status": "open",
      "source": "docs/builder-concerns-2026-09-16/pilot-dossiers/00-INDEX.md"
    }
  ],

  "re_review_triggers": [
    "vLLM version or container digest changes",
    "checkpoint identity changes between nvidia and RadixArk paths",
    "FP8 routed-experts patch lands upstream"
  ],

  "review": {
    "by": "gwen",
    "date": "2026-09-16",
    "rubric_version": "1.0",
    "notes": null
  }
}
```

Claim `kind` enum:

`configuration`, `mechanism`, `observation`, `performance_effect`, `quality_effect`, `fit_constraint`, `failure_mode`, `tradeoff`, `reproducibility`, `cost`, `thermal`, `interconnect`, `other`.

Comparison `result` enum:

`a_better`, `b_better`, `equivalent`, `mixed`, `inconclusive`.

Comparison evidence extensions:

- `variable`: the variable actually established as changed by the source.
- `candidate_variable`: a plausible variable for an uncontrolled/claimed contrast; it may not be rendered as isolated causality.
- `binary_provenance_status`: `resolved`, `unresolved`, or `not_applicable`; required whenever engine/build equivalence matters for a C3 attribution.
- `condition_completeness`: normally validator-derived; if persisted, it must be written by validator/build and not hand-edited.
- `method_note`: a source-backed method explanation rendered beside weak methods such as wall-clock division.
- `promotion_gate`: required for an uncontrolled contrast that could become C3 after specific facts or a clean rerun.

Contradiction `status` enum:

`open`, `resolved_by_source_priority`, `resolved_by_measurement`, `unresolved_conflict`, `superseded`.

Open-question `blocks` enum:

`fit_claim`, `speed_claim`, `quality_claim`, `causal_claim`, `exact_reproduction`, `promotion_to_box`, `technique_registry`, `builder_input`, `other`.

Open-question objects should include:

```jsonc
{
  "id": "rtx-pro-6000-fit-offload",
  "type": "needs_builder_input",
  "question": "Which memory tier/offload configuration produced the 170 tok/s RTX PRO 6000 point for a 111 GB build on a 96 GB card?",
  "blocks": ["fit_claim", "speed_claim", "causal_claim"],
  "owner": "openkod",
  "status": "open",
  "source": "docs/builder-concerns-2026-09-16/builder-questions.md",
  "locator": "Q1 — RTX PRO 6000 fit/offload",
  "related_measurement_ids": [],
  "note": "A drafted builder question is not an inferred offload/fit fact."
}
```

### 5.11 Minimal claim objects and canonical technique packets

`evidence.claims[]` is a pilot must-have, not a deferred optional field. The project goal is to explain how each recipe seeks performance, and Daily’s Lite structure needs atomic source-backed claims:

- **Uses** → `configuration` claims plus the exact `run.*`, `engine.*`, and `requirements.*` fields.
- **Designed to** → `mechanism` claims, normally `c1_configuration`.
- **Evidence here** → `observation`, `performance_effect`, `quality_effect`, `failure_mode`, or a linked `comparison`, always with its own evidence level and contrast kind.

A minimal claim object must contain:

```jsonc
{
  "id": "dflash2-draft-mechanism",
  "technique_id": "dflash2-block-diffusion-drafting",
  "kind": "mechanism",
  "statement": "DFlash2 uses a block-diffusion drafter to propose multiple tokens for the target model to verify.",
  "evidence_level": "c1_configuration",
  "lineage_id": "analogalok-4090-dflash2",
  "source": "https://github.com/...",
  "locator": "PR #27342 description / builder post",
  "quote": null,
  "status": "recorded"
}
```

Required minimal fields: `id`, `technique_id`, `kind`, `statement`, `evidence_level`, `lineage_id`, `source`, `locator`, and `status`. Observed/performance/quality/failure claims also require a verbatim `quote` or linked `measurement_ids`/`comparison_id`; durable C1 configuration/mechanism facts may rely on the exact locator until the verbatim quote is archived.

Optional/broader fields may be added later: `cause`, `effect`, `scope`, `contradictions`, `citations`, `cost`, `thermal`, `power`, `interconnect`, `re_review_triggers`, and richer claim kinds.

To prevent unsafe prose duplication, `technique_id` must resolve to a canonical technique packet. Phase 1 may introduce a small controlled registry, proposed as `directory/data/techniques.json`:

```jsonc
{
  "techniques": {
    "dflash2-block-diffusion-drafting": {
      "name": "DFlash2 block-diffusion drafting",
      "category": "speculative_decode",
      "canonical_description": "Uses a block-diffusion drafter to propose multiple tokens for target-model verification.",
      "canonical_sources": ["..."],
      "status": "proposed"
    },
    "native-mtp": {
      "name": "llama.cpp native MTP",
      "category": "speculative_decode",
      "canonical_description": "Uses the target model’s multi-token-prediction path rather than a separate block-diffusion drafter.",
      "canonical_sources": ["..."],
      "status": "proposed"
    },
    "pageable-ple": {
      "name": "Pageable PLE / n-gram cache table",
      "category": "memory_strategy",
      "canonical_description": "Keeps part of the prediction/lookup table pageable or outside resident memory to run an oversize build.",
      "canonical_sources": ["..."],
      "status": "proposed"
    },
    "kv-quant-ladder": {
      "name": "KV quantization ladder",
      "category": "memory_strategy",
      "canonical_description": "Selects key/value cache precision and size to fit a context target.",
      "canonical_sources": ["..."],
      "status": "proposed"
    },
    "roce-tensor-parallel": {
      "name": "RoCE/IB tensor parallelism",
      "category": "interconnect",
      "canonical_description": "Distributes tensor-parallel work across nodes over RDMA-class networking.",
      "canonical_sources": ["..."],
      "status": "proposed"
    },
    "fp8-block-scales-routed-experts": {
      "name": "FP8 block-scales routed-experts patch",
      "category": "runtime_patch",
      "canonical_description": "Patch required to keep routed MoE expert execution on the intended FP8 block-scales path.",
      "canonical_sources": ["..."],
      "status": "proposed"
    }
  }
}
```

Rules:

- A claim may reference a technique packet for generic canonical wording, but the setup-specific `statement`, `quote`, `locator`, and evidence level remain required.
- A technique packet may not create a new causal claim by itself.
- Unregistered technique IDs are validator errors once Phase 1 is implemented.
- Existing dossier prose must not be copied into multiple setup records as free text when a canonical packet can carry the stable technique identity.

### 5.12 Pilot 02 C3 comparison example

This is the only current pilot-set C3 single-variable example. It remains author-reported and partially conditioned:

```jsonc
{
  "id": "dflash2-vs-native-mtp-decode-30k",
  "question": "What does the builder’s stated protocol report for DFlash2 versus native MTP decode at the ~30k operating point?",
  "variable": "speculative_drafter",
  "a": {"label": "native MTP", "measurement_id": "m-native-mtp-decode"},
  "b": {"label": "DFlash2", "measurement_id": "m-dflash2-decode"},
  "result": "b_better",
  "effect_metric": "decode_per_stream",
  "effect_direction": "increase",
  "contrast_kind": "single_variable",
  "conditions_constant": [
    "single RTX 4090 24 GB box",
    "same checkpoint/quant family as recorded",
    "same KV q4/q8 configuration as recorded",
    "same prompt set",
    "--parallel 1"
  ],
  "conditions_unstated": [
    "exact llama.cpp binary/build used by each arm",
    "whether native MTP ran mainline or a different fork commit",
    "sample size / n",
    "driver/runtime pins"
  ],
  "evidence_level": "c3_matched_ab",
  "binary_provenance_status": "unresolved",
  "condition_completeness": "partial",
  "lineage_id": "analogalok-4090-dflash2",
  "independent_reproductions": [],
  "quality_status": "unchecked",
  "source": "archived builder post / PR #27342 artifacts",
  "locator": "raw/xsweep_analogalok.json, 2026-08-21 18:50z post",
  "quote": null,
  "re_review_triggers": [
    "native-MTP baseline commit/build is pinned",
    "DFlash2 fork commit/build is pinned",
    "an independent lineage reruns both arms"
  ],
  "note": "Scoped author-reported matched comparison. Do not render as verified, proved, independently reproduced, or generally causal across builds."
}
```

## 6. Conditional requirements and minimal field tiers

### 6.1 By recipe status

| Status | Existing requirements | New requirements when the source supports them | Validator behavior |
|---|---|---|---|
| `measured` (owner/box) | `provenance: box`, `date`, `n`, `method` | measurement `id`; structured `conditions`; `evidence.method_grade`; exact runtime/fork/container pin; exact hardware variant; memory/KV/offload basis when relevant; correctness check when output was inspected | Missing exact pin or full speed conditions should be an error for new box records after Phase 2. |
| `reported` (community/forum) | resolvable `source`, provenance, date | source quote or locator; `lineage_id`; `method_grade`; conditions exactly as stated; `evidence.level`; open question for any load-bearing unknown | Missing quote/locator is an error for new forum numbers. Missing revision pin is a warning unless a C3+ causal claim depends on it. |
| `claimed` (vendor/publisher) | resolvable `source`, provenance, date | card/page revision or `retrieved` date; `method_grade`; `evidence.level` normally `c0_claim` or `c2_observation`; open questions for unstated fit/offload/context/concurrency; quality canaries separated from speed claims | A vendor claim may not be marked C3+ without a linked comparison and recorded protocol. |
| `untested` | runnable recipe/source, no measurements | capability observations and known constraints when stated; run revision when available | Any measurement on an `untested` setup is an error. UI must not render speed. |
| `broken` | existing caveat/source | `known_failures[]` with stage, trigger, effect, status, date, source, lineage | Prior measurements and contradictions are preserved; `broken` is not used merely because another environment failed. |

### 6.2 By evidence level

| Level | Minimum structured support |
|---|---|
| `c0_claim` | source, quote/locator, claim statement. |
| `c1_configuration` | durable source, locator, exact configuration field or canonical technique packet. |
| `c2_observation` | measurement, source, date, provenance, `method_grade`, whatever conditions the source states, explicit nulls for unstated material conditions, and separate `quality_status`. |
| `c3_matched_ab` | comparison object with both sides, asserted variable, `conditions_constant`, `conditions_unstated`, `contrast_kind`, `condition_completeness`, lineage, source/quote, and any unresolved binary/runtime provenance as an open question/re-review trigger. |
| `c4_independent_reproduction` | at least two distinct lineage IDs, actual measurement/run evidence from each, and recorded configuration equivalence or differences. |

Quality is represented only through `quality_status`, `correctness`, and linked quality measurements. It never becomes a causal level.

### 6.3 Must-have fields for the eight pilots

Keep Phase 2 minimal. These are the fields needed to stop the known pilot overstatements:

1. `schema_version: 2`
2. `measurements[].id` for every migrated measurement, with dossier-cited measurements explicitly flagged
3. `measurements[].conditions`
4. `measurements[].evidence.level`
5. `measurements[].evidence.method_grade`
6. `measurements[].evidence.lineage_id`
7. `evidence.lineages[]`
8. minimal `evidence.claims[]` for configuration, intended mechanism, and observed association, plus the minimal canonical technique registry required by `technique_id`
9. `evidence.comparisons[]` for real or claimed contrasts
10. `evidence.open_questions[]` for load-bearing unknowns
11. `requirements.offload` when offload/pageability is explicitly stated
12. `requirements.memory_profile` when the source decomposes memory
13. `engine.spec_decode_profile` when acceptance, draft revision, max-draft tokens, or decay is stated
14. `run.repo_revision` / `engine.fork_revision` / `engine.image_digest` when historically resolvable
15. hardware `variant_id` or `variant_ambiguous`
16. `correctness` and `known_failures` when stated
17. `capability_observations` when a setup-specific capability is broken, untested, or requires an extra artifact
18. `sources[].locator`, `sources[].archive_path`, `sources[].retrieved`, and `sources[].lineage_id` for dossier-backed evidence

### 6.4 Later optional fields

Defer these until the pilot contract proves out:

- `serving.scheduler`, `prefix_cache`, `session_affinity`
- `interconnect.bandwidth_gbs` and detailed topology
- power, thermal curve, noise
- tokens-per-dollar and hardware cost
- full Python/package dependency graph
- broader claim kinds beyond the minimal configuration/mechanism/observation object
- `variation.revision` for every HF card, starting with moving vendor cards
- cost/economics fields
- automated roofline/plausibility annotations

The goal is not to make every record carry every possible field. It is to make the eight pilots express the distinctions experts already ask about, while leaving unknowns visibly unknown.

## 7. Validator and tooling rules

`validate.py` should add enums and structural checks, but must not infer facts:

1. Unknown keys in new blocks error.
2. `schema_version`, when present, must be `2`.
3. Every new URL-bearing field must be checked by `check_links.py`.
4. `sources[].lineage_id`, measurement `evidence.lineage_id`, claim/comparison `lineage_id`, correctness `lineage_id`, and known-failure `lineage_id` must resolve to `evidence.lineages[]`.
5. Measurement IDs must be unique within a setup; comparison/correctness references must resolve.
6. Top-level `concurrency` and `conditions.concurrency` must agree.
7. `decode_agg` still requires `concurrency > 1`.
8. `evidence.level` must be one of `c0_claim`, `c1_configuration`, `c2_observation`, `c3_matched_ab`, or `c4_independent_reproduction`; there is no `c5` causal level.
9. `c3_matched_ab` requires a linked comparison with both sides, a recorded `variable` or explicit `candidate_variable`, source/quote, and an open question/re-review trigger when binary/runtime provenance remains unresolved.
10. `contrast_kind: single_variable` requires non-empty `conditions_constant` and a recorded `variable`. Any remaining material uncertainty must be explicit. The only current pilot exception is pilot 02: the stated protocol isolates the drafter, but `binary_provenance_status: unresolved`; it may remain `c3_matched_ab` + `single_variable` only with derived partial condition completeness, an open question/re-review trigger, and the no-“verified” UI wording.
11. `c4_independent_reproduction` requires at least two distinct lineage IDs.
12. `quality_status: pass|fail|mixed|recorded` requires linked correctness/quality evidence covering the stated scope.
13. `method_grade: benchmark_harness` requires a non-empty `method`.
14. `method_grade: wall_clock_division` must preserve `evidence.method_note` and a caveat/note explaining the weakness.
15. `acceptance_rate_pct` must be 0–100.
16. `memory_profile.entries[].value` must be positive; unit/scope/component/location enums enforced.
17. `offload.strategy: none` must not list offloaded components and requires an explicit source; absence of offload prose is not evidence for `none`.
18. `hardware[].variant_id` must exist in the hardware device variants when present.
19. `run.repo_commit` and `run.repo_revision.commit` must agree when both present.
20. `repo_revision.resolution: exact` must not have `ambiguous: true`.
21. Provenance tier rules remain unchanged: `evidence_level` never upgrades `box/forum/vendor`.
22. Quality canaries remain per-setup; validator should reject any aggregated cross-harness score field.
23. `condition_completeness` should be derived by validator/build, not stored as an editable fact.
24. `capability_observations[].capability/status` must use the enums, and each observation must have a source or explicit `unknown` status.
25. A setup with `status: untested` must not contain measurements.
26. A setup with `status: broken` should have at least one `known_failures[]` entry or an explicit caveat explaining the breakage.
27. `known_failures[].source` and `capability_observations[].source` must be link-checked.
28. `evidence.open_questions[]` is required when a load-bearing fit/offload/protocol ambiguity exists and no source-backed field can be recorded.
29. `repo_revision.resolution: earliest_commit_after_anchor` requires `ambiguous: true`.
30. New structured fields must never be auto-populated by the validator; it may derive display-only completeness, not write facts.
31. `quality_status` may be `pass`, `fail`, `mixed`, `recorded`, or `unchecked`, but it must never change `evidence_level`.
32. `cold_start_effect` may contain only an observed/measured outcome. Expected mechanisms belong in a C1 `evidence.claims[]` object.
33. Every minimal `evidence.claims[]` object must have `id`, `technique_id`, `kind`, `statement`, `evidence_level`, `lineage_id`, `source`, `locator`, and `status`; observed/performance/quality/failure claims must also have a verbatim quote or linked measurement/comparison IDs.
34. Every non-null `technique_id` must resolve in the canonical technique registry; unknown IDs error.
35. A canonical technique packet may supply generic wording, but it may not by itself create a setup-specific causal, fit, quality, or performance claim.
36. A comparison with `contrast_kind: uncontrolled` may use `candidate_variable`; it may not use a settled `variable` field or UI wording that implies the variable was isolated.
37. `method_grade: wall_clock_division` records remain admissible as C2, but `evidence.method_note` is required. UI must show the method note next to the number and may not use them as a recipe’s comparability/headline anchor.
38. Builder-input open questions may reference `docs/builder-concerns-2026-09-16/builder-questions.md` and should record `owner`, `blocks`, and `status`; they must not be converted into inferred fit/offload/method facts.

`check_links.py` must fetch:

- existing `sources[].url` and `mirror_url`;
- `measurements[].source`;
- new nested URLs in `run.repo_revision`, `variation`, `engine`, `requirements`, `interconnect`, `serving`, `correctness`, `known_failures`, `capability_observations`, `evidence.claims`, `evidence.comparisons`, `evidence.contradictions`, and `evidence.open_questions`;
- proposed canonical technique-registry URLs in `data/techniques.json` when Phase 1 is implemented.

`tools/vet_candidates.py` should learn the same optional shapes before candidates use them.

`verify_browser.py` should eventually assert:

- recorded-or-absent rendering;
- no inferred offload/KV/acceptance/version/fit;
- no `c5` or quality-verified causal badge; quality status is rendered separately from evidence level;
- wall-clock and vendor-table method notes remain visible;
- `method_grade: wall_clock_division` is not used as a homepage/headline or comparability anchor;
- matched vs bundle vs uncontrolled vs claimed comparisons are labeled distinctly;
- only pilot 02 may receive a matched single-variable badge, and that badge must say “author-reported matched comparison; partial conditions; binary provenance unresolved” rather than “verified”;
- pilot 01 MTP off/on must render as uncontrolled C2 with its promotion gate visible in Pro;
- independent reproduction count is not conflated with corroboration;
- capability observations override nominal capabilities in setup views;
- known failures and contradictions remain visible where they affect safety or fit;
- minimal claims/technique packets are exposed in the Lite “Uses / Designed to / Evidence here” structure without duplicating unsafe prose;
- Lite never hides mandatory safety/trust information;
- Pro exposes the structured evidence without requiring raw JSON literacy.

## 8. QA and test matrix

Future implementation must be gated by both `validate.py` and `verify_browser.py`.

| Scenario | Data shape | Validator expectation | UI/browser expectation |
|---|---|---|---|
| Legacy compatibility | 79 current records, no `schema_version` | pass unchanged | current 220-check suite remains green |
| Unknown evidence field | typo in `evidence`, `conditions`, or `memory_profile` | error | build fails |
| C3 without comparison | measurement `evidence.level: c3_matched_ab` but no linked comparison/source sides | error | not rendered |
| C3 with unresolved binary provenance | pilot 02 author-reported matched comparison; protocol constants recorded but both-arm binary/build not pinned | pass only with `condition_completeness: partial`, `binary_provenance_status: unresolved`, and an open question/re-review trigger | may show scoped matched evidence as “author-reported matched comparison; partial conditions; binary provenance unresolved”; never “verified” |
| Single-variable causality | `contrast_kind: single_variable` with recorded variable/constants | pass only when material conditions are recorded or explicitly unresolved with an open question | may show scoped matched evidence; cannot imply universal causality |
| Bundle contrast | Strix-style stack-vs-baseline | pass as C2/bundle | must say individual lever not isolated |
| Uncontrolled contrast | 2× Spark table adjacency without full A/B protocol | pass as C2/uncontrolled with promotion gate | must not show matched-A/B badge; must preserve missing conditions |
| Claimed vendor contrast | RTX PRO 100→170 without protocol | pass as C0/C2 | must not imply causal proof |
| C5/quality level | any `c5_quality_verified` or quality value inside `evidence_level` | error | quality status is shown separately from causal level |
| Quality linkage | `quality_status: pass|recorded|mixed` without same-scope correctness/quality evidence | error | no speed row may appear quality-verified |
| Minimal claim object | `evidence.claims[]` missing `technique_id`, source/locator, lineage, support, or status | error | Lite cannot render the claim as an authoritative “Uses”/“Designed to”/“Evidence here” item |
| Technique registry | claim `technique_id` absent from canonical registry | error once registry exists | UI renders canonical packet wording plus setup-specific source, not duplicated unsafe prose |
| False reproduction | `c4_independent_reproduction` with one lineage | error | not rendered |
| Corroboration vs reproduction | Ollama crowd range in `corroborations[]` | pass | must label sanity range, not reproduction |
| Weak wall-clock speed | `method_grade: wall_clock_division` | pass only with `evidence.method_note` and preserved caveat | Lite/Pro shows a method-note line next to the number; it is not a headline/comparability anchor |
| Hidden offload inferred | 111 GB file on 96 GB card, no offload source | no offload field may be inferred | show unresolved fit/offload question; no “fits” verdict |
| Unsourced no-offload | `offload.strategy: none` with only absent offload prose | error | cannot render “no offload” |
| Intentional pageable offload | Mac64 84.9 GB build on 64 GB | `offload.strategy: pageable_ple` valid; `cold_start_effect` null unless measured | Lite must disclose intentional pageability and expected mechanism only as a C1 claim |
| Expected cold-start encoded as fact | `cold_start_effect: disk-bound first-token latency expected` without measured source | error | intended mechanism is rendered as C1, not as an observed effect |
| KV inferred from speedup | acceptance rate absent but speedup present | error if acceptance inferred | render “acceptance not recorded” |
| Acceptance/decay recorded | structured profile with source | pass | Pro shows curve/table; Lite may summarize only if conditions present |
| 32k column ambiguity | AtomicChat 32k prefill semantics unresolved | open question required for direct comparison | compare page must not call 8k and 32k prefill directly comparable |
| Revision ambiguity | MiaAI repo earliest commit after anchor | `repo_revision.ambiguous: true` required | UI must not claim exact historical pin |
| Hardware variant ambiguity | RTX PRO 6000 edition unstated | `variant_ambiguous: true` allowed with note | UI must show variant unstated |
| Builder-input open question | RTX PRO fit/offload or Ollama `eval_duration` awaiting reply | stored as `open_questions[]`, not inferred fit/method | UI shows unresolved question and owner/source path |
| Capability contradiction | nominal vision true, setup observation broken | pass | setup view must prioritize observation over nominal capability |
| Known failure | ROCm 10 load failure | `known_failures[]` valid | failure remains visible; original success evidence preserved |
| Quality canary aggregation | attempt to create cross-harness score | error/reject | no quality leaderboard |
| Provenance upgrade | dossier analysis tries forum→box | error | provenance tier unchanged |
| Nested source rot | URL only in `evidence.open_questions`, `known_failures`, or technique registry | `check_links.py` fetches it | dead link fails gate |

The full gate remains `python3 directory/check.sh`. New browser checks should be dataset-derived and must not weaken existing route, provenance, accessibility, responsive, dark-theme, compare, or count-aware hardware assertions.

## 9. Dossier-to-schema mapping

| Dossier section | Proposed schema destination |
|---|---|
| 1. Exact identity/environment | existing identity fields + `run.repo_revision`, `variation.revision`, `engine.version/backend/fork_revision/environment`, hardware `variant_id` |
| 2. Source lineage | `evidence.lineages`, `sources[].lineage_id/locator/archive_path` |
| 3. Technique fingerprint | `engine.config/flags/spec_decode_profile`, `requirements.offload`, `interconnect` |
| 4. Atomic claim ledger | `evidence.claims`, `evidence.comparisons`, `known_failures` |
| 5. Benchmark protocol | `measurements[].conditions`, `method`, `method_grade`, `stat`, `n` |
| 6. Memory/offload decomposition | `requirements.memory_profile`, `requirements.offload` |
| 7. Expert decision questions | derived UI contract; not stored as new editorial copy |
| 8. Trade-offs/failures/contradictions | `caveats`, `known_failures`, `evidence.contradictions` |
| 9. Unknowns/gaps | null fields + `evidence.open_questions`; the two current builder-input blockers are archived in `docs/builder-concerns-2026-09-16/builder-questions.md` and should be linked from there rather than restated as inferred data |
| 10. Suggested Lite explanation | presentation layer, task #12; not a data field |
| 11. Full Pro explanation | presentation layer, task #12; not a data field |
| 12. Re-review triggers | `evidence.re_review_triggers`; pilot 02 includes binary/runtime-provenance pinning, pilot 01 includes the four-fact C3 promotion gate |
| 13. Evidence completeness | derived from fields + `evidence.review` |

### 9.1 Legacy/prose-name crosswalk

Use these canonical stable names in data and task #12. Do not introduce a separate `protocol` field.

| Legacy/prose or dossier name | Canonical schema destination | Notes |
|---|---|---|
| “benchmark protocol” | `measurements[].conditions` + `method` + `method_grade` + `stat`/`n` | The protocol is the structured measurement conditions and method metadata, not a standalone `protocol` key. |
| “atomic claim ledger” | `evidence.claims[]`, with comparative claims linked through `evidence.comparisons[]` | A claim is setup-specific; generic technique wording comes from the canonical technique registry. |
| “failure modes” / “known issues” | `known_failures[]` | Not `evidence.failures`; setup-level safety/breakage facts live here. |
| “memory basis” / “memory decomposition” | `requirements.memory_profile` | Preserves component, value, unit, scope, location, pageability, context/KV basis, and source. |
| “offload basis” / “pageable PLE” | `requirements.offload` | `strategy: none` requires explicit source; intended mechanisms without observed effects are C1 claims. |
| “technique fingerprint” | `engine.*`, `requirements.offload`, `interconnect`, and `evidence.claims[].technique_id` | `technique_id` points to a canonical packet so prose is not duplicated unsafely. |
| “source lineage” | `evidence.lineages[]` plus `sources[].lineage_id` | One actor/artifact/campaign is one lineage. |
| “evidence completeness” | derived from fields; review metadata in `evidence.review` | `condition_completeness` is validator/UI-derived unless Terra later approves storing a computed value. |
| “quality canary” | existing quality `measurements[]` and `correctness.checks[]` references, summarized by `quality_status` | Separate from causal `evidence_level`. |
| “builder question” | `evidence.open_questions[]` with `owner`, `blocks`, `status`, and a path to `docs/builder-concerns-2026-09-16/builder-questions.md` | A question never becomes an inferred fit/offload/method fact. |

## 10. Pilot mapping and current grades

| Pilot | Existing evidence | Proposed grade under rubric | Key new fields | Load-bearing blocker |
|---|---|---|---|---|
| 01 2× Spark NVFP4 vLLM | README server-read tables; MTP off/on; KV pool; RoCE; image digest | MTP off/on `c2_observation` with `contrast_kind: uncontrolled`; concurrency rows `c2_observation`; reproduction 0. C3 promotion gate: both arms, same server/config/workload, MTP as sole toggled variable, and checkpoint-path discrepancy resolved. Pinning alone is not enough; otherwise a clean rerun is required. | `repo_revision.ambiguous`, `engine.image_digest`, `memory_profile`, `interconnect`, measurement conditions, comparison/open question, `promotion_gate` | No historically exact repo commit; checkpoint-path discrepancy; no raw full A/B |
| 02 4090 DFlash2 | Builder curve; DFlash vs MTP decode/prefill; flags; broken multi-GPU/multimodal | The pilot set’s only author-reported local matched A/B: decode and prefill contrasts `c3_matched_ab`, `single_variable`, derived partial conditions, `binary_provenance_status: unresolved`; decay observations `c2_observation`; reproduction 0; `quality_status: unchecked`; no “verified” wording | `fork_revision`, `spec_decode_profile.decay_curve`, measurement context conditions, capability observation, known failure, open question/re-review trigger for same-binary baseline | No `n`, no independent repro, no driver/version pin; binary equivalence unresolved |
| 03 Strix Halo MTP | Branch/PR levers; baseline vs stack; byte-clean output; ROCm 10 failure | Stack contrast `c2_observation`, `contrast_kind: bundle`; correctness setup-level pass; independent failure observation, not success reproduction | `engine.backend=rocm`, `fork_revision`, `kernel_patches`, `correctness`, `known_failures` | Multiple levers changed together; branch/loader state on newer ROCm; byte-clean check not retested |
| 04 M3 Ultra Atomic Chat | Baseline 23 → DFlash2 87.6; no protocol | `c2_observation`; comparison `claimed` or `uncontrolled`, not C3; vendor headline C0 | explicit null conditions, `method_grade=author_report`, open questions | Context/workload/flags/version unstated |
| 05 2× RTX 5090 AtomicChat | Vendor command; speed table; KL/top-1 protocol | Speed rows `c2_observation`, `vendor_published_table`; quality canaries recorded; 32k prefill column semantics open | `variation.revision`, quality measurements, `method_grade`, `serving`/conditions, open question | Card not pinned; 32k column semantics and batch behavior unclear |
| 06 Mac64 AtomicChat PLE | Strong memory decomposition; intentional pageable PLE; vendor speed/quality | Memory/offload `c1_configuration`; speed `c2_observation`; no matched A/B. Intended pageability and any expected cold-start behavior are C1 claims; `cold_start_effect` remains null unless measured. | `memory_profile`, `offload.strategy=pageable_ple`, `evidence.claims[]`, correctness/quality canaries, `method_grade` | PLE sysctl/kernel version and measured cold-start behavior absent |
| 07 RTX PRO 6000 Unsloth | Exact command; one vendor operating point; 96–114 GB fit ambiguity | `c0_claim` or `c2_observation` with insufficient conditions; contrast `claimed`; fit blocked | `page_retrieval` revision, `variant_ambiguous`, `open_questions` linked to `docs/builder-concerns-2026-09-16/builder-questions.md`, offload null | Which offload/configuration produced 170 tok/s on a 96 GB card is unstated |
| 08 Ollama 3090 | Pull/tag/blob facts; wall-clock 40.2; crowd sanity range | `c2_observation`; `method_grade=wall_clock_division`; corroboration not reproduction; not headline/comparability-eligible | `conditions.power_limit_pct`, `clock_state`, `corroborations`, `method_note`, open question linked to `docs/builder-concerns-2026-09-16/builder-questions.md` | Weak method and no independent harness/`eval_duration` run |

The completeness matrix totals remain the migration priority:

- **P 45**: already first-class; keep.
- **B 13**: source supports the fact but current schema only has prose; migrate first.
- **R 5**: recoverable from a pinned artifact; retrieve before recording.
- **I 22**: irrecoverable from the current corpus; leave null and record an open question where load-bearing.
- **N 11**: not stated; leave null.

### Pilot claims that fail the proposed standard

These are the specific claims the future schema/UI must block or qualify:

1. **All eight:** “independently reproduced” fails. No pilot has `c4_independent_reproduction`.
2. **01 2× Spark:** “MTP off/on is a full matched A/B” fails. It is a strong within-table observation, but no raw full A/B protocol, exact repo pin, or resolved checkpoint path exists. Promotion to C3 requires all four gate facts or a clean rerun; pinning alone is not enough.
3. **01 2× Spark:** “exactly reproducible from the recorded repo commit” fails because the earliest commit postdates the anchor and the ambiguity must remain visible.
4. **02 4090:** “verified” or “quality-checked” fails. It is the only author-reported local matched A/B, but condition completeness is partial, binary provenance is unresolved, and it has no `n`, independent reproduction, or linked quality/correctness check.
5. **03 Strix Halo:** “MTP caused 16.8→47.1 tok/s” fails. The gain is a bundle of branch/kernel/loader/speculative changes.
6. **03 Strix Halo:** an unqualified current-workflow claim fails while the ROCm 10 detached-MTP load failure remains open.
7. **04 M3 Ultra:** “DFlash2 verified 3.79× faster” fails. Context, workload, flags, and protocol are unstated; this is an author-reported contrast, not C3.
8. **05 2×5090:** “32k prefill is 14.4× faster than 8k prefill” fails. The 5,244 tok/s column semantics are unresolved and may not be directly comparable.
9. **05/07 vendor quality tables:** “this speed row is quality-verified because the vendor publishes a KL/top-1 table” fails unless the quality evidence explicitly covers the same run/configuration.
10. **06 Mac64:** “fits a 64 GB Mac” fails without disclosing that the 84.9 GB build depends on intentional pageable PLE behavior. “Measured disk-bound cold-start penalty” also fails unless a source records the outcome; the intended mechanism is C1 only.
11. **07 RTX PRO 6000:** “fits a 96 GB card” or “uses host offload” fails. The 111 GB build’s actual tier/offload configuration is unstated; the correct state is an open fit question linked to `docs/builder-concerns-2026-09-16/builder-questions.md`.
12. **07 RTX PRO 6000:** “MTP causally produces 170 tok/s under these conditions” fails because quant/context/workload/concurrency/offload per chart point are not restated.
13. **08 Ollama 3090:** “benchmark-grade 40.2 tok/s” or “headline 40.2 tok/s” fails. The source method is wall-clock division, not `eval_duration`; it may remain visible as C2 with a method-note line beside the number, but it may not anchor the recipe’s comparability or headline speed.
14. **08 Ollama 3090:** “community-reproduced” fails. The llamabench range is corroboration, not reproduction.
15. **Any pilot:** dossier analysis may not upgrade `forum` or `vendor` provenance to `box`.

## 11. Current structured-gap audit

At current HEAD `c6cdee7`; the data snapshot is unchanged from `fc8d9d1`:

- 79 setups, 190 measurements.
- Measurement provenance: 168 `forum`, 13 `box`, 9 `vendor`.
- Setup provenance tiers: 38 `forum`, 33 none/untested, 4 `vendor`, 4 `box`.
- Setup statuses: 38 reported, 33 untested, 4 claimed, 4 measured.
- 143 speed measurements: 25 have a `context` annotation, 85 have `concurrency`, 95 have `method`, 23 have `stat`, 12 have `range`.
- 21 quality measurements exist.
- No setup currently has structured `run.repo_commit`, `engine.version`, `engine.commit`, `requirements.offload`, `requirements.memory_profile`, `interconnect`, `serving`, `correctness`, `known_failures`, or `evidence`.
- Measurements currently have no `id`, `conditions`, or `evidence` block.
- `directory/site_src/app.js` already contains a compare row for `engine.version`, but no dataset record supplies that field yet.

This confirms the research conclusion: much expert-relevant information exists, but it is prose-bound or absent. The schema should make the prose-bound facts structured without converting unknowns into guesses.

## 12. UI implications and overstatement guards for task #12

Daily’s Lite/Pro contract should be able to rely on these distinctions. The schema’s purpose is not merely to store more fields; it is to prevent specific UI overstatements.

### 12.1 Claims the UI must never overstate

| Pilot issue | Forbidden UI interpretation | Required UI behavior |
|---|---|---|
| Only pilot 02 contains an author-reported local matched single-variable A/B | Labeling pilots 01, 03, 04, 05, 07, or 08 as “matched A/B”, “controlled”, or “causally proven” | Only pilot 02’s DFlash2-vs-MTP decode/prefill contrast may carry a matched single-variable badge, qualified as partial conditions with binary provenance unresolved; all others use observation, bundle, uncontrolled, or claimed wording. |
| Pilot 01 MTP off/on table | “MTP caused 2.13× in a controlled A/B” | “README table reports MTP off vs MTP=3; no raw full A/B; repo pin and checkpoint path ambiguous.” |
| Pilot 03 stack-vs-baseline | “MTP caused 16.8→47.1 tok/s” | “The full branch/kernel/MTP stack is associated with the gain; individual levers are not isolated.” |
| Pilot 04 23→87.6 tok/s | “DFlash2 verified 3.79× faster” | “Vendor/builder reports 23→87.6 tok/s; context, workload, flags, and protocol are unstated.” |
| No independent reproduction across all eight | “verified”, “reproduced”, “community-confirmed” | Show `0 independent reproductions`; distinguish quotes and crowd ranges from reproductions. |
| Pilot 08 crowd sanity range | “independently reproduced” | “Similar crowd-reported 3090 range exists; it is corroboration, not reproduction.” |
| Pilot 07 111 GB build on 96 GB card | “fits”, “offloads to host RAM”, or any inferred memory strategy | “Fit/offload configuration unresolved; source does not state how the 111 GB build produced 170 tok/s on a 96 GB card.” |
| Pilot 06 84.9 GB build on 64 GB | Normal fit, hidden pageability, or an “expected disk-bound/cold-start risk” | Lite must disclose vendor-stated intentional pageable PLE and say cold-start behavior is not recorded; it may not present an expectation as an observed risk or effect. |
| Pilot 01 acceptance 72.8% and pilot 02 decay prose | Inferring acceptance from speedup or presenting prose decay as a structured measured curve without source | Render acceptance/decay only where source states it; otherwise “not recorded.” |
| Pilot 05 8k vs 32k prefill | Directly comparing 363 and 5,244 tok/s as a context scaling result | Show vendor-table column-semantics ambiguity; block direct comparability until source clarifies batch/prefill semantics. |
| Pilot 08 wall-clock 40.2 tok/s | Benchmark-grade or headline speed | Show a method-note line beside the number: wall-clock division, not `eval_duration`; no `n`; not promotable or usable as the recipe’s comparability anchor. |
| Vendor quality tables | Ranking models/quantizations or treating quality table as verification of unrelated speed rows | Show canary, harness, source, and scope; no cross-harness leaderboard and no speed-quality blending. |
| Dossier analysis | Upgrading `forum`/`vendor` to `box` | Provenance tier remains source-based; analysis never changes tier. |
| Nominal capabilities | Showing setup-supported video/vision/tools when a setup-specific observation says broken/untested/extra artifact | Prioritize `capability_observations` over nominal capabilities. |
| Historical pins | Presenting an ambiguous post-anchor commit as exact | Show revision ambiguity and anchor date. |

### 12.2 Lite requirements

Lite may simplify language but must never hide:

- hardware count and ambiguous variant;
- intentional/pageable/hidden offload, with unmeasured cold-start behavior shown as not recorded rather than expected;
- unresolved fit questions;
- wall-clock or unclear vendor-table method, with the method note beside the number;
- claimed vs uncontrolled vs bundle vs single-variable comparison;
- author-reported matched comparisons with partial conditions/unresolved binary provenance;
- zero independent reproductions;
- output-correctness failure or unchecked correctness when a speed claim is prominent;
- separate causal evidence and quality status—no blended “verified” badge;
- revision ambiguity when exact reproduction matters;
- setup-specific capability breakage;
- the minimal Uses / Designed to / Evidence here claims needed to explain how the recipe seeks performance.

### 12.3 Pro requirements

Pro should expose:

- full runtime/environment/fork/image/model revision pins;
- canonical technique packets and setup-specific claims;
- memory decomposition with units/scope/location;
- offload components and strategy;
- speculative acceptance/decay;
- measurement IDs, conditions, method grade, and dossier citation flags;
- comparisons with contrast kind, constants, unstated conditions, lineage, binary/runtime provenance, and C3 promotion gates;
- contradictions/open questions/re-review triggers, including builder-input questions and their archived question file;
- correctness and quality canaries with harness/source;
- capability observations and known failures;
- interconnect, power, thermal, and cost when recorded.

The UI should not show one blended “trust score.” Show separate badges or rows for provenance, evidence level, contrast kind, conditions, method, reproduction, and quality.

## 13. Migration plan

### Phase 0 — proposal

This document. No implementation.

### Phase 1 — validator acceptance

Authorized implementation task:

- add optional enums/structures to `validate.py`;
- add the minimal canonical technique registry required by `technique_id`;
- update `SCHEMA.md`;
- update `check_links.py` to traverse nested sources and technique-registry sources;
- add validator/QA tests for C0–C4 only, separate `quality_status`, minimal claims, unsourced `offload.strategy: none`, expected-vs-observed `cold_start_effect`, wall-clock method notes, pilot 01 promotion gates, and pilot 02 unresolved binary provenance;
- run full gate with no data changes to prove backward compatibility.

Success criterion: current 79 records still pass unchanged.

### Phase 2 — eight-pilot migration

Authorized data task:

- add `schema_version: 2` and IDs to all migrated measurements, flagging the measurements actually cited by dossiers;
- add minimal `evidence.claims[]` and `technique_id` links for Uses / Designed to / Evidence here;
- migrate only **B** and already-**P** facts into fields;
- add **R** facts only after retrieving the pinned artifact;
- leave **I/N** null;
- record load-bearing unknowns as `open_questions`, linking `docs/builder-concerns-2026-09-16/builder-questions.md` for the two builder-input blockers;
- preserve all caveats and negatives.

Success criterion: each pilot dossier maps to structured fields without changing any existing numeric value or provenance tier.

### Phase 3 — UI contract

Daily’s task #12 defines Lite/Pro sections. Implementation later:

- render new fields recorded-or-absent;
- add stable data hooks;
- extend `verify_browser.py`;
- run full gate.

### Phase 4 — opportunistic migration of the remaining 71 setups

No bulk migration. For the other 71 records:

- leave legacy records without `schema_version` until they are revisited;
- when a record is touched for source rot, re-review, new evidence, or UI migration, add only source-backed fields;
- any record that gains one new evidence field must set `schema_version: 2` and pass the full new validator rules;
- existing caveats must remain until the structured fields and UI render at least the same safety information;
- prose-only offload/KV/acceptance/version facts should be migrated using Openkod’s **B** priority, but **I/N** facts stay null/open;
- never infer a field across the dataset from hardware arithmetic, current engine HEAD, similar recipes, or speed ratios.

Success criterion: the gate remains green after each individually touched record, and no record gains a structured fact that is not present in its cited source.

## 14. Open decisions for Terra/owner

1. Approve evidence-level names and whether UI should expose codes (`C0–C4`) or plain labels. Quality is not `C5`; it is a separate `quality_status` axis. Recommended UI: plain labels with code tooltips for Pro.
2. Approve placement: nested blocks inside setups versus a sidecar evidence file. Recommended and supported by Openkod: nested blocks, because raw evidence is per-post and setup lineages should not fragment.
3. Approve whether `condition_completeness` should be derived only, or also stored after validator computation. Recommended: derive only in validator/UI unless a computed value is explicitly written by the build.
4. Approve whether measurement IDs should be assigned to all 190 measurements in Phase 2 or only referenced measurements. Openkod’s sourcing recommendation: assign IDs to all migrated measurements and flag the dossier-cited subset, especially the 4090 A/B pairs, 2× Spark tables, and AtomicChat 517.9/36.0 pair.
5. Approve strictness: warnings versus errors for missing `repo_revision` on `requires_fork: true` lanes. Recommended: warning for historical forum records, error for new box/measured records after Phase 2.
6. Decide whether `method_grade: wall_clock_division` should be excluded from homepage headline speed selection, or retained with a visible weak-method warning. Openkod’s sourcing recommendation: retain visibly with a method-note line, but do not make it a headline/comparability anchor.
7. Decide whether Openkod should fetch the remaining **R** artifacts before any data migration. Openkod owns this as a sourcing task: three of five are already resolved in task #14 (`ec0ad38b4836`, `ea9f94fc7625` + `59a40b56ff79`, `57ab3265056d`); the remaining RTX PRO 6000 container info and post-anchor z-lab revisions stay retrieval work, not schema work.
8. Decide whether the two load-bearing pilot blockers—RTX PRO 6000 fit/offload and Ollama `eval_duration`—should be owner questions to the builders before promotion. Openkod has drafted them in `docs/builder-concerns-2026-09-16/builder-questions.md` and owns sending/archiving once rate limits recover; until replies exist, they remain `open_questions[]`.
9. Approve the canonical technique registry and initial `technique_id` set required by minimal `evidence.claims[]`.
10. Approve pilot 02’s final wording: C3 author-reported matched comparison, partial condition completeness, binary/runtime provenance unresolved, no “verified”/“proved” language, with a dated-pin re-review trigger.

## 15. Recommendation

Adopt the rubric now as the review standard for task #14 dossiers and task #12 Lite/Pro contracts, but implement schema/validator changes only after Terra authorizes Phase 1.

The first data migration should be limited to the eight pilots and should move only facts already supported by the archived corpus. The most valuable immediate fields are:

1. revision pins and ambiguity;
2. measurement IDs/conditions/method grade;
3. minimal claims and canonical technique packets;
4. memory decomposition;
5. structured offload;
6. comparisons with contrast kind and promotion gates;
7. lineage/corroboration/reproduction separation;
8. separate quality status, correctness, capability observations, known failures, and open questions.

The immediate UI contract should be built around the fact that pilot 02 is the only author-reported local matched single-variable A/B—with partial conditions and unresolved binary provenance—no pilot has independent reproduction, quality is never a causal level, and the risky 96 GB/64 GB offload cases must remain explicit rather than inferred.

That gives experts the causal context they actually ask for while preserving the directory’s core law: recorded or absent, never inferred.
