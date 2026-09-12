# Redesign integration readiness

**Date:** 2026-09-10  
**Dataset baseline:** 65 setups at `711e97f`  
**Scope:** Read-only audit of the current data against the proposed Directory,
My Hardware, Compare, and four-dimensional trust surfaces. This report does not
change Claude's in-progress frontend or Qwen's sourcing and vetting work.

## Executive verdict

| Surface | Current readiness | Safe product claim |
|---|---|---|
| Directory | High | A comprehensive, source-linked catalog of known recipes and reported results |
| Compare | Partial | Compare identity, requirements, configuration, and disclosed measurements; do not imply universal ranking |
| My Hardware | Limited | Compare recorded memory requirements with a selected budget; do not claim general compatibility yet |
| Trust model | Partial | Show source provenance now; keep recipe, compatibility, performance, and capability confidence distinct |

The strongest current product is the Directory. Identity, artifact size,
memory, disk, caveats, update dates, and source coverage are strong. The largest
gaps affect execution completeness, exact-device matching, and numeric
comparability.

## Baseline

| Item | Count |
|---|---:|
| Setups | 65 |
| Model families | 22 |
| Hardware records | 6 |
| Engines | 7 |
| Publishers and builders | 29 |
| Measurements | 144 |
| Setups with any measurement | 33 |
| Setups with decode measurements | 32 |
| Source references | 134 |
| Unique source URLs | 84 |
| Distinct checkpoints | 50 |

Evidence distribution is 4 owner-measured `box` setups, 28 community `forum`
setups, 1 `vendor` setup, and 32 unmeasured setups.

## Directory readiness

All 65 setups have the core fields required for model-family shelves and recipe
identity: title, model, checkpoint, publisher, quant, format, artifact size,
license, engine configuration, hardware class, resident-memory requirement,
disk requirement, update date, caveats, and sources.

Execution coverage is materially weaker:

| Execution field | Coverage |
|---|---:|
| Recipe repository | 65/65 |
| Ordered steps | 65/65 |
| Top-level command | 31/65 |
| Any copyable command action | 32/65 |
| `auto_bootable` stated | 25/65 |
| Clean-install verification | 0/65 |
| Pinned recipe commit | 0/65 |
| Engine version | 0/65 |

The UI should distinguish a source-linked lead, written procedure, copyable
recipe, and clean-install-tested recipe. It must not collapse these into one
"complete" state.

Three setups have no command and fewer than two actionable steps:

- `qwen38-flash-next-blazux-vllm-hybrid-spark`
- `qwen38-flash-next-azampatti-sglang-spark`
- `qwen38-27b-vllm-mtp-community`

## Compare readiness

Identity, configuration, artifact size, resident memory, disk, capabilities,
caveats, and source links can be compared now. Performance values require
strong comparability warnings.

There are 81 decode measurements:

| Protocol field | Present | Missing |
|---|---:|---:|
| Method | 72 | 9 |
| Date | 60 | 21 |
| Concurrency | 54 | 27 |
| Statistic | 23 | 58 |
| Range | 12 | 69 |
| Sample count | 11 | 70 |

Only 13 of 81 decode rows contain concurrency, statistic, method, and date
together. There are no structured prompt length, output length, sampling,
cache-state, benchmark-version, API-mode, engine-version, or timing-basis
fields. Some of this context exists only inside free-text methods.

Compare may display these measurements, but direct highlighting requires a
match on hardware, metric, workload, context, concurrency, statistic, method,
and runtime version. Missing values mean "comparability unknown," not "same."

## My Hardware readiness

Every setup has a recorded memory and disk requirement, and all six hardware
records have capacity, usable memory, type, bandwidth, architecture, chip, and
CPU/GPU descriptions. This supports qualified fixed-budget filtering.

It does not yet support broad compatibility claims:

- Measurements do not carry a structured `hardware_id`.
- Hardware records do not distinguish exact SKUs from broad classes.
- Only 4 setups have owner measurements on the exact owned DGX Spark.
- Minimum VRAM is missing for 5 of 17 discrete-GPU setups.
- Operating-system constraints are absent from all 65 setups.
- Engine versions are absent from all 65 setups.
- Offload and streamed-expert behavior exists only in prose.
- Free disk, driver, runtime version, and power limit have no structured rules.
- Context and concurrency do not have a safe memory model for 21 of 22 families.

The in-progress compatibility implementation must not treat a hardware record's
global `measured_by_us` flag as proof that every setup referencing that hardware
was measured by us. That currently turns 4 exact owner-tested setups into 23
apparent exact-device matches.

Until requirement-basis fields exist, changing context or concurrency may
explain assumptions but must not visibly reclassify a setup unless the
calculation genuinely uses those values.

## Trust readiness

### Recipe confidence

Safe now:

- Source-linked lead
- Written procedure
- Copyable command available
- Auto-bootable declared

Not yet supported:

- Clean-install tested
- Version-pinned reproducibility
- Health-check verified

### Compatibility confidence

Safe now:

- Owner-measured exact evidence for the 4 `box` setups
- Community-reported hardware evidence when the source names the machine
- Requirement-only estimate
- Unknown

Not yet supported:

- General exact-SKU matching
- Context-sensitive fit
- Driver or runtime compatibility
- Reliable offload-aware classification

### Performance confidence

Current measurement provenance is strong enough to distinguish `box`, `forum`,
and `vendor`. Repetition, protocol completeness, and cross-result comparability
are not strong enough for a broad leaderboard.

### Capability confidence

All setups carry capability declarations, but there are no structured
capability observations. Current values should be labelled model-declared,
runtime-declared, partial, disabled, or unknown. "Tested through this recipe"
requires a recorded test and source.

## Minimum schema additions

These fields are prerequisites for honest My Hardware and Compare behavior:

1. `hardware.kind`: `sku` or `class`.
2. `measurements[].hardware_id` plus exact device configuration where known.
3. `engine.version` or commit.
4. Structured recipe operating-system, driver, and runtime constraints.
5. Requirement basis: context, concurrency, reserve, and whether resident
   memory already includes KV cache and runtime buffers.
6. Structured offload mode, offloaded component, host-memory use, and storage
   requirement.
7. Structured benchmark protocol with workload, lengths, timing basis, cache
   state, warmups, and raw-result reference.
8. Structured clean-install, capability, and failure observations.
9. First-class source quotation, canonical URL, mirror/archive URL, and fetch
   timestamp.
10. Artifact revision, hash, and auxiliary-file relationships.

Do not recompute resident memory by adding an estimated KV cache until each
requirement states whether its recorded resident figure already includes KV
and at what context and concurrency.

## Integration blockers

Resolve these before merging or publishing the redesign:

1. Exact-device evidence requires a matching exact-hardware observation, not a
   globally marked hardware record.
2. Context and concurrency controls must affect real calculations or be
   labelled explanatory only.
3. Known discrete-GPU profiles must populate VRAM rather than treating system
   RAM as the accelerator budget.
4. Disk, OS, driver, and runtime constraints must either affect compatibility
   or be omitted from the verdict.
5. Performance comparison must treat missing protocol values as unknown.
6. Recipe confidence must distinguish prose, commands, and tested execution.
7. Capability confidence must not claim recipe-level testing from model and
   engine declarations.
8. Failures must move from prose regexes to structured observations before the
   product offers a reliable failure filter.

## Merge acceptance checklist

- The Directory still exposes all 65 setups and all 22 model families.
- No source-backed measurements or negative results disappear.
- Model-level and recipe-level capabilities are visibly distinct.
- Only the 4 owner-measured setups can receive current exact owner-device proof.
- Missing measurement context is displayed as unknown.
- Different hardware or protocols trigger an incomparable-result warning.
- Hardware assumptions state context, concurrency, reserve, and offload basis.
- Recipe states distinguish lead, procedure, command, and verified install.
- Data validation passes before the generated site is built.
- Browser tests cover Directory, My Hardware, Compare, missing data, and mobile.
- Concurrent sourcing changes are rebased and revalidated before publication.
