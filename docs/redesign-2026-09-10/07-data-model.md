# 07 — Data-model implications

**The constraint this document works under:** no existing source-backed
information is lost, no validator rule is weakened, and nothing is invented to
fill a gap. Every proposal below is either a *presentation-layer derivation* of
data that already exists, or a *schema addition whose values would have to be
sourced before any entry could use it*.

---

## 1. Entity status today

The brief names thirteen entities the product should eventually represent
separately. Here is what actually exists.

| Entity | Status | Where it lives |
|---|---|---|
| Model family | **Exists** | `data/models/<id>.json` |
| Artifact / checkpoint | **Embedded** in `setups[].variation` | — |
| Engine | **Exists** | `data/engines/<id>.json` |
| Recipe | **Exists** — this is `setups/<id>.json` | — |
| Recipe step | **Exists** | `run.steps[] {kind, text}` |
| Hardware device | **Exists**, as a *class* | `data/hardware/<id>.json` |
| Compatibility observation | **Implicit** — `setups[].hardware[]` + `requirements` | — |
| Measurement | **Exists**, rich | `setups[].measurements[]` |
| Benchmark protocol | **Embedded** as the free-text `method` string | — |
| Capability observation | **Embedded** as booleans in `setups[].capabilities` | — |
| Failure report | **Embedded** in `caveats[]` prose | — |
| Source | **Exists** | `setups[].sources[] {url, kind, note}` |
| Contributor / publisher | **Exists** | `data/publishers.json` |

Five of the thirteen are embedded rather than first-class. That is a real
limitation, and it is worth stating plainly: **it does not block this redesign.**
The interface can render all thirteen concepts from what exists today. Promoting
them buys queryability and cross-linking, not new content.

---

## 2. Derivations — presentation only, no schema change

Computed at render time from recorded data. Each is labelled in the interface as
derived, and the formula is published on `#/methodology` so it is auditable.

| Derived value | Formula | Used by |
|---|---|---|
| `readiness` | `run.command` → `runnable`; ≥2 `run.steps` → `recipe`; else `lead` | Row column, filter, sort |
| `complexity` | engine base (ollama/lm-studio 1, llama-cpp/mlx-lm 2, vllm/sglang 3, custom-fork 4) `+1` fork `+1` >4 steps `+1` draft model | Row column, filter, sort, Compare |
| `representative_decode` | first single-stream metric by preference, non-`peak` preferred | Row, sort, Compare |
| `aggregate_pair` | `decode_agg` with its `concurrency`, paired with `decode_per_stream` at the same concurrency | Row detail, Compare |
| `recipe_confidence` | repo + (command or ≥2 steps) + requirements | Evidence strip |
| `compat_confidence` | hardware class SKU-vs-range + `measured_by_us` + measurement presence | Evidence strip, My Hardware groups |
| `perf_confidence` | provenance × `n` × `method` presence | Evidence strip |
| `cap_confidence` | recipe capabilities vs model modalities vs engine features | Evidence strip |
| `freshness` | `updated` vs today: ≤90d fresh, ≤180d aging, >180d stale | Row, filter |
| `implied_os` | from the tested hardware class's `arch`: `arm64, Metal` → macOS; `aarch64 / SM121`, `x86_64 …` → Linux | Advanced filter, **labelled "implied"** |
| `capability_conflict` | model has modality ∧ recipe records it false | Row mark, Compare, My Hardware |
| `failure_flag` | caveat matching crash / corrupt / OOM / fail / unsupported / does not work | Row mark, Risks section |

`implied_os` and `failure_flag` are the two derivations that carry
interpretation rather than arithmetic. Both are labelled as inferred in the UI,
and both are superseded the moment the corresponding schema fields exist.

---

## 3. Proposed schema additions

Ordered by value. **All are optional and default to null**, so the current 65
records stay valid and `validate.py` needs no rule relaxed. A field is only
populated from a source, per AGENTS.md law 1.

### Priority 1 — fields the interface visibly lacks

| Field | Shape | Why |
|---|---|---|
| `engine.version` | `string \| null` | Compare has an "Engine version" row that reads `not recorded` for all 65. A vLLM number from 0.6 and one from 0.11 are not the same claim. |
| `run.os` | `["linux","macos","windows"] \| null` | The brief requires an OS filter. Today it can only be implied from hardware. |
| `run.verified_clean_install` | `{date, by, source} \| null` | The top level of recipe confidence — *clean-install tested* — is currently unreachable. Without this field the strongest recipe evidence cannot exist. |
| `models[].kv_bytes_per_token` | already in schema, **1 of 22 populated** | Not an addition — a backfill. It is the only input that makes a KV-cache allowance computable, and 21 families cannot produce one. Highest-value backfill in the dataset. |

### Priority 2 — promote embedded entities

| Entity | Proposal |
|---|---|
| **Failure report** | `setups[].failures[]` — `{stage, error_signature, symptom, root_cause, recovery, recovery_verified, engine_version, driver_version, date, source}`. Migrate the caveats that already describe failures (ik_llama.cpp cross-vocab corruption, the YaRN/DFlash2 crash above 262144, the draft-capture crash). Caveats stay for everything that is a qualification rather than a failure. |
| **Capability observation** | `setups[].capability_observations[]` — `{capability, supported, evidence: tested\|runtime-declared\|model-declared, source, date}`. Turns four booleans into sourced claims and makes *tested through this recipe* reachable. |
| **Benchmark protocol** | `benchmarks/<id>.json` — `{name, harness, version, prompt_set, input_len, output_len, url}`, referenced by `measurements[].protocol`. The `method` string already carries this prose; a referencable protocol is what makes two numbers legitimately comparable rather than merely adjacent. |
| **Artifact** | `data/artifacts/<id>.json` lifted out of `variation`, adding `revision`, `sha256`, `auxiliary_files` (the mmproj files llama.cpp vision needs), `draft_compatibility`, `corruption_reports`. Several setups already share a checkpoint; today its metadata is duplicated per setup. |

### Priority 3 — completeness

`hardware[].compute_tflops_by_precision`, `hardware[].cpu_topology`,
`hardware[].power_limit_w`, `hardware[].thermal_notes`;
`setups[].requirements.offload` as a structured value rather than prose;
`measurements[].warmup_n`, `.cache_state`, `.power_mode`, `.tool`,
`.timing` (`engine-reported` | `wall-clock`), `.raw_result_file`;
`setups[].estimated_setup_minutes`; `setups[].maintenance_status`.

`measurements[].timing` deserves a note: the dataset already contains three
different clocks (net-decode, synthetic fixture, wall-time), and the caveats say
so in prose. Making it a field would let Compare detect a clock mismatch
automatically instead of relying on a reader noticing a sentence.

---

## 4. Migration

Additive and reversible.

1. **Nothing changes first.** The redesign ships against the current schema.
   Every proposed field renders as `not recorded` until it exists. This is
   deliberate: the interface makes the gaps visible, which is the argument for
   filling them.
2. **Add optional fields to `validate.py`** — type-checked when present, never
   required. No existing record becomes invalid.
3. **Backfill only from sources.** `kv_bytes_per_token` first (21 families,
   from published model cards and config files). `engine.version` next, from
   each recipe's own repo or thread — where a source does not state it, it stays
   null, and the interface keeps saying `not recorded`.
4. **Promote entities behind a compatibility read.** Introduce `failures[]` and
   read `caveats[]` as a fallback so both shapes render during the transition.
5. **Re-run the gate at every step** — `validate.py` → `check_links.py` →
   `build.py` → browser suite. Zero errors is the entry condition for each stage,
   not the exit criterion.

## 5. What this redesign does *not* change

- Provenance tiers, their meanings, and the rule that they never blend.
- The requirement that a number without a source is deleted, not downgraded.
- `provenance_tier` never overstating the best measurement present.
- The prohibition on aggregating quality canaries into a score.
- The retention of negative results.
- The duplicate-identity rule (checkpoint + engine + hardware + config string).
- Sizes coming from the HuggingFace tree endpoint.
- `variation.license` meaning the weights' license.
- Any enum in `validate.py`.

The four confidence dimensions are computed **from** the provenance data; they
do not replace it, override it, or blend it. Every individual measurement keeps
its own provenance, source, method, statistic, hardware, context and concurrency
exactly as recorded.
