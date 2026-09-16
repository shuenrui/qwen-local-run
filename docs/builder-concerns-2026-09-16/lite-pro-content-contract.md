# Lite / Pro recipe content contract

Status: pilot proposal. This document changes no data or UI.

## 1. Product contract

Lite and Pro are two readings of the same recipe record. They are not separate
datasets, routes, evidence standards, or visual systems.

- Lite answers the first operational questions without hiding trust or risk.
- Pro explains the implementation, benchmark, bottleneck, and evidence chain.
- Switching modes must never change a value, provenance tier, compatibility
  result, selected recipe, or source.
- Missing evidence stays missing in both modes. Pro may explain the gap in more
  detail; it may not fill it by inference.
- The current complete recipe page is the migration baseline for Pro. Lite is a
  deliberate composition of the same facts, not a replacement summary record.

The mode controls information depth only. It does not mean beginner/expert
identity, fast/slow hardware, or safe/unsafe recipe.

## 2. Decisions each mode supports

### Lite

Lite must let a reader decide:

1. Is this the model, artifact, and runtime I intended to run?
2. What exact recorded machine and memory arrangement produced this recipe?
3. What do I copy or install to start it?
4. What performance was actually reported, under which basic conditions?
5. What important trade-off, failure, or hidden resource should stop me?
6. How strong is the evidence, and where can I inspect the source?

### Pro

Pro must additionally let an operator decide:

1. Is the runtime, kernel, and precision path transferable to my machine?
2. What is the real limiting resource: weight bandwidth, KV capacity, prefill
   compute, interconnect, host memory, storage, or scheduler behavior?
3. How does performance change with context, concurrency, cache state, and
   speculative acceptance?
4. Was a claimed optimization isolated in a matched comparison or merely
   present in the measured bundle?
5. What quality or correctness checks were performed?
6. Can I reproduce this historical result from immutable artifacts?
7. What will likely change after an engine, driver, model, or kernel update?

## 3. Global mode behavior

### Control

- Use a labelled two-option control: `Lite` and `Pro`.
- Place it in the global utility area beside theme, not among route tabs.
- Use native radio semantics or two buttons with mutually exclusive
  `aria-pressed`; do not model the control as navigation tabs.
- The accessible group name is `Information mode`.
- Changing mode announces `Lite mode selected` or `Pro mode selected` in the
  existing polite live region.

### State and URL

- Store mode as `mode=lite|pro` in the hash query.
- A valid URL value overrides saved preference.
- A saved preference overrides the product default.
- Invalid or absent values fall back safely.
- Recommended launch default: Lite for a new visitor; remember Pro after the
  visitor selects it.
- Every hash writer must preserve `mode`, including model selection, recipe
  search/filter/sort, compare selection, and canonical detail routes.
- Use one query serializer instead of adding mode handling separately to every
  route writer.

### Interaction continuity

Switching mode must preserve:

- route and entity ID;
- selected model;
- recipe filters and sort;
- expanded recipe rows;
- comparison selection;
- hardware profile and assumptions;
- theme;
- scroll position where the retained content allows it;
- keyboard focus.

If focused content is removed in Lite, return focus to the selected mode
control and announce the change. Do not call the generic route path if it
forces a scroll-to-top reset.

### Rendering rule

Render one semantic content tree for the active mode. Do not duplicate full
Lite and Pro trees and hide one with CSS. Keep one `h1`, valid heading order,
one main landmark, and the current route identity.

## 4. Lite recipe section order

Lite uses seven sections in this order. Sections 5-7 are trust-critical and
must never disappear behind Pro.

### 1. What this recipe runs

Show:

- exact model family and checkpoint;
- artifact publisher;
- quantization and format;
- artifact size;
- engine name;
- custom fork or patch requirement;
- one plain-language recipe description.

Decision supported: identity and relevance.

Current sources: `model`, `variation.*`, `engine.id`,
`engine.requires_fork`, `slug_note`.

### 2. What it needs

Show:

- exact recorded hardware label and count;
- recorded resident memory;
- minimum VRAM where stated;
- disk requirement;
- host RAM or SSD use whenever recorded;
- context and concurrency underlying the requirement when known;
- a prominent `Offload not stated` message when fit depends on more capacity
  than the named device can provide and the source does not explain it.

Decision supported: whether the recorded resource arrangement resembles the
reader's intended environment. Lite must say `recorded on`, never unconditional
`fits`.

Current sources: `hardware`, `requirements.*`, `capabilities.long_context`.
New structured sources: `requirements.memory_profile`,
`requirements.offload`.

### 3. How to start it

Show:

- verbatim command when present, with one copy action;
- otherwise the ordered recorded steps;
- repository/profile requirement;
- a compact warning if the recipe depends on a fork, gated artifact, image
  sync, or unpinned branch.

Decision supported: reproducibility cost and first action.

Current sources: `run.command`, `run.steps`, `run.repo`, `run.profile`,
`engine.requires_fork`, `caveats`.

### 4. What was observed

Show:

- one representative decode result only when the same recipe records it;
- metric name, value, unit, statistic, concurrency, context, provenance, and
  source;
- prefill separately when recorded; never combine prefill and decode;
- `No speed measurement for this exact recipe` when absent;
- an evidence phrase, not a generic confidence badge:
  - `Author-reported operating point`
  - `Matched local comparison`
  - `Owner-measured run`
  - `Vendor-reported result`
  - `No independent reproduction recorded`

Decision supported: what was measured and how narrowly it applies.

Current sources: `measurements[]`, representative decode selection.
New structured sources: `measurements[].conditions`, `evidence.claims[]`.

### 5. How it seeks performance

Show at most three sourced techniques. Each uses a three-sentence structure:

1. `Uses`: the configuration fact.
2. `Designed to`: the documented mechanism.
3. `Evidence here`: the observed result or explicit lack of isolation.

Example:

> Uses DFlash2 speculative decoding with a four-token draft limit. DFlash2 is
> designed to verify drafted token blocks with the target model. In the cited
> single-builder comparison, decode was higher than native MTP under the
> recorded fixture; no independent reproduction is recorded.

Do not use `because`, `caused`, `made faster`, or a percentage improvement
unless the causal grade permits it.

Decision supported: the performance strategy without overstating causality.

New sources: `evidence.claims[]` linked by `technique_id` to canonical technique
packets.

### 6. Trade-offs and failures

Always show when present:

- correctness failures;
- unsupported modalities or topologies;
- prefill/decode trade-offs;
- context decay;
- hidden or ambiguous offload;
- cold-start or storage penalties;
- quality evidence and quality gaps;
- known broken version ranges.

Do not collapse these into a count such as `3 caveats`. The most consequential
item must be readable without entering Pro.

Decision supported: whether the recipe's optimization invalidates the user's
actual workload.

Current sources: `caveats`, capability conflicts, engine gotchas.
New sources: `known_failures[]`, `capability_observations[]`, quality canaries.

### 7. Evidence and freshness

Show:

- provenance tier for every displayed measurement;
- primary source links;
- last reviewed date;
- immutable runtime/artifact pin when known;
- `Historical pin unresolved` when source and repository chronology conflict;
- independent reproduction state;
- direct action: `Open Pro evidence`.

Decision supported: whether to trust, reproduce, or re-research the recipe.

Current sources: `sources`, `updated`, `run.repo_commit`, measurement sources.
New sources: structured source objects, lineage IDs, claim reviews.

## 5. Pro recipe section order

Pro retains every Lite section and expands it in place. It adds the following
detail; it does not rearrange the recipe into a separate product.

### A. Identity and immutable artifacts

- model architecture, active/total parameters, layer mix;
- checkpoint revision and exact files/hashes;
- quantization by component, calibration or imatrix source;
- conversion tool and version;
- required projectors, drafts, or sidecars;
- license and publisher lineage.

### B. Runtime and kernel path

- engine version and commit;
- fork repository and commit;
- backend and kernel implementation;
- container image digest;
- OS, driver, compute runtime, and framework versions;
- compiler/build flags and target architecture;
- full runtime flags and environment variables.

### C. Hardware topology

- exact SKU and unit count;
- host CPU/RAM;
- interconnect and tensor/expert/data split;
- power mode, power limit, and thermals when measured;
- storage device and measured read behavior when storage is active.

### D. Memory, KV, and offload accounting

- weights, draft, KV, workspace, host allocation, and reserve;
- measurement type: allocated, resident, steady-state, or peak;
- context and concurrency basis;
- KV dtype, bytes/token, and recorded pool size;
- offloaded components and tier: device, RAM, or SSD;
- mmap/pageable/pinned behavior and cold/warm state.

Never back-calculate absent KV or offload facts from throughput.

### E. Performance techniques and tuning levers

For each technique show:

- exact setting/flag/patch;
- intended mechanism source;
- architecture and version constraints;
- what outcome it is expected to affect;
- what was observed here;
- evidence grade and confounds;
- tuning range and failure boundary when sourced.

Expected technique groups include weight precision, KV precision, attention
backend, speculative decoding, prefix caching, compilation/CUDA graphs,
batching/scheduler, host affinity, expert offload, SSD streaming, and parallel
topology.

### F. Benchmark protocol and curves

- workload or prompt fixture;
- input, context, and requested/actual output tokens;
- sampling and thinking mode;
- concurrency, batching, and arrival pattern;
- cache/prefix state and warmups;
- timing basis and TTFT inclusion;
- repetitions, statistic, range, and raw result;
- separate prefill, decode, TTFT, aggregate, and per-stream views;
- context/concurrency/acceptance curves when recorded.

The UI must not plot points that have incompatible protocols on one implied
continuous curve.

### G. Quality and correctness

- byte-clean or output-verification method;
- KL, perplexity, top-1, task, or human-evaluation results;
- matched quant comparison conditions;
- silent corruption reports;
- thinking-budget or sampler effects;
- untested quality dimensions stated as gaps.

### H. Causal evidence

Show every atomic claim with:

- type: configuration, mechanism, association, matched local A/B, replicated;
- allowed wording;
- exact scope;
- source lineage;
- verbatim excerpt and locator;
- confounds and contradictions;
- reviewer decision.

The interface must visually distinguish a matched A/B from multiple points
reported by the same builder. One claim repeated across X, YouTube, and a
README remains one lineage.

### I. Operations and failure envelope

- concurrency ceiling;
- sustained power/thermal behavior;
- cold-start and restart behavior;
- multi-user scheduling/routing implications;
- unsupported modalities/topologies;
- failure signature, affected versions, workaround, and verified recovery;
- tokens per dollar only when inputs and price basis are sourced.

### J. Reproduction and maintenance

- clean-install steps;
- health check;
- gated/download prerequisites;
- immutable source and artifact pins;
- source fetch date and content hash;
- stale/superseded/contradicted status;
- re-review triggers;
- raw JSON as the final audit surface, not the primary Pro experience.

## 6. Evidence language rules

### Configuration fact

Evidence: command, config, source, or artifact explicitly contains the setting.

Allowed: `This recipe uses FP8 KV cache.`

Forbidden: `FP8 KV makes this recipe faster.`

### Intended mechanism

Evidence: authoritative implementation or design documentation.

Allowed: `FP8 KV is designed to reduce KV-cache storage.`

Required qualifier when untested: `Its realized effect in this recipe was not
isolated.`

### Observed association

Evidence: a specified setup reports an outcome without a matched control.

Allowed: `The author reported 36 tok/s with DFlash enabled.`

Forbidden: `DFlash produced 36 tok/s.`

### Matched local comparison

Evidence: both sides of the comparison, the changed variable or explicitly
named bundle, and the relevant constant and unstated conditions. Sample size,
condition completeness, and output-quality verification remain separate axes
and must be displayed rather than implied by the C3 label.

Allowed: `In this matched local comparison, enabling X changed median decode
from A to B.`

Scope remains local.

### Replicated result

Evidence: matched local comparison plus a same-scope reproduction from an
independent lineage. Repetition by the same lineage can increase condition
coverage, but it does not qualify as independent reproduction.

Allowed: `The cited independent reproductions found the same direction under
these conditions.`

Never generalize to all Qwen models or devices without corresponding coverage.

## 7. Unknown, weak, and contradictory states

Use explicit prose, not empty cells or generic confidence colors:

- `Not stated by the source`
- `Recorded only in caveat prose`
- `Source can be retraced; structured value not yet extracted`
- `Historical value cannot be recovered from the archived source`
- `Author-reported; protocol incomplete`
- `No independent reproduction recorded`
- `Artifact exceeds device memory; offload method not stated`
- `Source and repository chronology conflict`
- `Sources disagree`
- `Superseded for newer runtime versions`

When sources disagree, Lite shows the consequence and the disagreement. Pro
shows both claims, lineages, dates, and the reviewer disposition.

## 8. Content transformation rules

- Plain language may shorten terminology but may not delete its condition.
- A speed value never loses metric, concurrency, context, statistic, or
  provenance merely to fit Lite.
- `Single GPU` does not imply `no offload`.
- Artifact size below total memory does not imply runtime fit.
- Artifact size above device memory does not prove the specific offload method.
- Hardware class does not imply exact SKU.
- An engine ID does not imply stock upstream behavior.
- A current repository HEAD does not stand in for a historical run.
- A vendor quality table is valuable evidence but not independent reproduction.
- A wall-clock division is labelled as derived wall-clock throughput, not an
  engine-reported decode measurement.
- `Peak` stays labelled peak.
- Aggregate throughput never becomes per-stream speed.
- No compatibility verdict appears outside My Hardware.

## 9. Example: pilot recipe 02

Recipe: `qwen38-27b-unsloth-gguf-dflash2-llamacpp-4090`.

This example intentionally preserves gaps. Copy must be regenerated from the
approved claim ledger after schema review.

### Lite example

#### Qwen3.8-27B on one RTX 4090 with llama.cpp DFlash2

Runs the UD-Q4_K_XL target with a z-lab DFlash2 draft on one recorded 24 GB
RTX 4090-class setup. The recipe uses a llama.cpp DFlash2 patch, limits the
draft to four tokens, and sets parallelism to one. The historical DFlash2 draft
revision was resolved to `57ab3265056d`; the exact llama.cpp PR build commit is
not recorded in the archived recipe.

Recorded resources: 16.7 GB target weights, approximately 750 MB draft, and
roughly 22-23 GB VRAM at the cited 30k operating point. That allocation is
consistent with an on-card run, but the source does not establish that no host
offload occurred.

Observed performance: the builder reported 90 tok/s near 30k context in one
operating point. In the same builder's matched comparison, DFlash2 decode was
reported at 90 tok/s versus 68.09 tok/s for native MTP, while MTP prefill was
faster: 2,324 versus 1,662 tok/s. Sample count and independent reproduction are
not recorded. Treat this as an author-reported matched comparison with partial
condition completeness: binary provenance for the two arms is unresolved.

How it seeks performance: DFlash2 drafts token blocks for target-model
verification. The cited local comparison associates it with higher decode than
native MTP under the recorded fixture. The result is one builder's matched
comparison, not a general claim for other contexts or machines.

Important limits: decode declines as context grows in the recorded series;
multi-GPU and multimodal operation were reported broken on the tested PR; the
2-bit draft's quality evidence is limited; no independent reproduction is
recorded.

Evidence: forum-tier builder report with archived thread evidence. Open Pro to
inspect the context curve, flags, comparison scope, source excerpts, and gaps.

### Pro additions

Pro expands the same recipe with:

- exact target/draft file identities and revisions;
- llama.cpp PR and unresolved build-commit state;
- full command and KV precision ladder;
- memory components by operating point;
- every context/decode point without implying protocol equivalence where the
  source changes KV precision;
- the matched DFlash2/MTP comparison and its prefill reversal;
- draft acceptance evidence and its source scope;
- broken multi-GPU/multimodal failure state;
- one-lineage treatment of the nine related social posts;
- explicit gaps: sample count, driver version, correctness protocol at the
  headline operating point, and independent reproduction.

## 10. Route-specific mode contract

### Model homepage

- Lite: current practical baseline and concise evidence explanation.
- Pro: adds why that baseline was selected, alternatives, evidence gaps, and
  links to technique/recipe dossiers.
- The model index remains identical in both modes.

### Recipe directory

- Lite: current common filters; advanced filters remain available in a
  disclosure; rows prioritize identity, recorded resources, representative
  observation, trust, and risk.
- Pro: current full filter/sort surface plus new technique, protocol,
  correctness, and reproducibility facets when data supports them.
- Both modes list all recipes. Mode never filters the dataset.

### Recipe detail and row expansion

- Use the same mode-specific section composer in desktop rows, mobile rows, and
  canonical pages.
- Canonical detail may show more space, not different facts.

### Compare

- Lite initially shows Identity, Recorded Resources, Representative
  Performance, Evidence, and Risks.
- Pro shows the complete Identity, Runtime, Hardware, Memory/KV/Offload,
  Techniques, Protocol, Capabilities, Performance, Quality, Trust, and Risks.
- Both modes retain the comparability warning and never declare an overall
  winner.

### My Hardware

- Compatibility logic is unchanged by mode.
- Lite shows the verdict, main arithmetic, assumptions, and uncertainty.
- Pro exposes detailed memory components, context/concurrency assumptions,
  offload basis, and missing inputs.

### Methodology and Contribute

- Methodology documents both contracts and causal grades.
- Contribute provides Lite-minimum and Pro-complete submission checklists, but
  does not reject useful historical recipes merely because advanced fields are
  unknown.

## 11. Accessibility and responsive contract

- Toggle is keyboard-operable and visibly focused.
- Selection state is announced and not communicated by color alone.
- Lite/Pro changes preserve heading order and landmarks.
- At narrow widths, section order remains the same; Pro tables become
  structured summaries rather than horizontally compressed grids.
- Long commands scroll within their block; prose does not require horizontal
  scrolling.
- At 400% zoom, the toggle, evidence phrases, and warnings remain readable.
- Reduced motion changes no content behavior.

## 12. Test contract

Before release, browser checks must prove:

1. Deterministic default and valid/invalid URL handling.
2. Preference restoration and blocked-storage safety.
3. Mode persistence through every route writer and browser history.
4. No state, focus, or scroll reset on mode switch.
5. Lite contains commands, requirements, representative observation or explicit
   absence, provenance, failures, caveats, and sources.
6. Pro contains complete runtime, protocol, measurement, technique, quality,
   evidence, and audit sections where recorded.
7. Unknown and contradictory states render explicitly.
8. Existing provenance, speed-selection, comparability, compatibility, and
   no-leaderboard invariants remain unchanged.
9. Both modes pass accessibility, mobile, zoom, dark theme, offline, and
   no-external-request checks.

## 13. Pilot acceptance criteria

This contract is ready to implement only after:

- Gwen's schema/evidence contract provides stable field names and causal-grade
  validation;
- all eight dossiers pass sentence-to-source review;
- the pilot's known editorial defects are corrected;
- the owner approves the Lite default and section ordering;
- missing fields remain optional for historical rows and render explicitly;
- one pilot recipe can be rendered in both modes without bespoke code or
  hidden inference.
