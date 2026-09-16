# Expert recipe pilot — integrated admission plan

Status: decision proposal. No schema, data, UI, or publication changes are
authorized by this document.

## 1. Inputs

- Builder corpus and analysis:
  `docs/builder-concerns-2026-09-16/`
- Eight recipe dossiers and completeness matrix:
  `docs/builder-concerns-2026-09-16/pilot-dossiers/`
- Lite / Pro content contract:
  `docs/builder-concerns-2026-09-16/lite-pro-content-contract.md`
- Evidence and schema proposal:
  `docs/EVIDENCE-SCHEMA-2026-09-16.md`

## 2. Pilot conclusion

The expert layer must not be a longer recipe description. It needs to model
four different things separately:

1. what configuration was recorded;
2. what a technique is designed to change;
3. what outcome was observed with the configuration;
4. what causal or quality conclusion the evidence supports.

The current dataset often contains items 1-3 in prose, but cannot reliably
represent item 4. The pilot also shows that polished headline claims frequently
lack a pinned runtime, complete benchmark protocol, exact hardware variant,
structured offload basis, correctness check, or independent reproduction.

The schema and UI must make those absences useful rather than embarrassing:
`not stated`, `historical pin unresolved`, `author-reported`, and `no
independent reproduction` are valid expert answers.

## 3. Admission decisions

### 3.1 Evidence location

Recommendation: keep setup-specific evidence nested in each setup record.

- Measurements, comparisons, failures, contradictions, and open questions are
  part of the setup's identity and audit history.
- A sidecar would create synchronization and broken-reference risk.
- Reusable intended-mechanism knowledge belongs in separate canonical technique
  packets, not duplicated in each setup.

Proposed technique path:

```text
directory/data/techniques/<technique-id>.json
```

A technique packet may contain:

- stable ID and display name;
- category;
- intended mechanism;
- architecture/backend/version constraints;
- canonical primary sources;
- known general trade-offs;
- re-review triggers.

It must not contain a setup-specific speedup. Setup `evidence.claims[]` links to
the packet by `technique_id` and records what was actually configured and
observed in that setup.

### 3.2 Evidence axes

Recommendation: preserve independent axes.

- Provenance: `box`, `forum`, `vendor`.
- Recipe status: existing lifecycle state.
- Causal evidence: `c0_claim` through `c4_independent_reproduction`.
- Contrast kind: `none`, `claimed`, `uncontrolled`, `bundle`,
  `single_variable`.
- Method grade: server telemetry, harness, vendor table, author report,
  wall-clock division, crowd report, unspecified.
- Condition completeness: derived `full`, `partial`, `insufficient`.
- Quality/correctness: separate status and linked checks.
- Independent lineage count: derived from actual reproduction lineages.

Do not encode quality verification as a higher causal level. A matched A/B can
be quality-unchecked; a quality table can exist without a causal speed claim.

### 3.3 Labels shown to readers

Recommendation: store stable codes but show plain-language labels.

Examples:

- `c0_claim` → `Claim; protocol incomplete`
- `c1_configuration` → `Configuration verified from source`
- `c2_observation` → `Observed under recorded conditions`
- `c3_matched_ab` + `single_variable` → `Matched local comparison`
- `c3_matched_ab` + `bundle` → `Matched bundle; lever not isolated`
- `c4_independent_reproduction` → `Independently reproduced`

The exact code remains visible in Pro's audit detail, not as the primary badge.

### 3.4 Condition completeness

Recommendation: derive it; never store it.

The validator/build computes completeness from the fields required for that
metric and method. This prevents a stored `full` label from drifting after data
changes.

### 3.5 Measurement IDs

Recommendation: assign stable IDs to all 190 current measurements when the
foundation migration begins.

- IDs are mechanical identity, not inferred evidence.
- Assigning only referenced measurements creates repeated migrations and
  unstable future links.
- IDs are stored once and never regenerated from array order after admission.
- No conditions or evidence levels are auto-populated merely because an ID is
  assigned.

### 3.6 Revision enforcement

Recommendation: conditional severity.

- New `box` measurements: exact runtime/artifact pin is an error unless the
  platform cannot provide one and an explicit immutable equivalent exists.
- New C3/C4 comparisons: missing load-bearing revision is an error.
- New forum/vendor C0-C2 records: missing revision is a warning plus an open
  question when the source genuinely does not state one.
- Legacy records: warning only until individually migrated.
- Fork-required recipes: missing fork revision is an error for migrated pilots;
  warning for unmigrated legacy records.

### 3.7 Wall-clock-derived speed

Recommendation: exclude `wall_clock_division` from representative headline and
practical-baseline speed selection.

- Keep it visible in Lite as `rough wall-clock observation` when it is the only
  speed evidence.
- Show full derivation and weakness in Pro.
- Never compare it directly with engine-reported decode without an explicit
  incompatibility warning.
- It remains useful evidence; it is not benchmark-grade evidence.

### 3.8 Recoverable artifacts

Recommendation: close the five `R` completeness items before migrating the
eight pilots. Three historical pins were resolved during the dossier audit;
record those results and resolve or explicitly exhaust the remaining two. A
source-backed recoverable value should not be knowingly left in prose or marked
unknown during a deliberate pilot migration.

### 3.9 Builder questions

Recommendation: contact builders for the two load-bearing irrecoverable gaps:

1. RTX PRO 6000: how the 111 GB artifact ran on the named 96 GB device, including
   host/offload behavior and measured memory basis.
2. Ollama RTX 3090: engine-reported `eval_duration`/token accounting, sample
   count, and exact runtime version for the wall-clock-derived result.

No response is also a valid outcome. The setup retains an open question and the
UI remains constrained.

### 3.10 Initial product mode

Recommendation: Lite is the default for a visitor with no saved preference;
Pro persists after selection. Shared URLs explicitly carrying `mode=pro`
override local preference.

This requires owner approval before implementation.

## 4. Minimal pilot schema

The pilot should add only fields required to express existing research without
overstatement:

1. `schema_version: 2`
2. stable `measurements[].id`
3. `measurements[].conditions`
4. per-measurement `evidence.level`, `method_grade`, and `lineage_id`
5. setup `evidence.lineages[]`
6. minimal `evidence.claims[]` with `technique_id`, statement, kind, scope,
   source/locator, level, lineage, contradictions, and open questions
7. `evidence.comparisons[]`
8. `evidence.contradictions[]`
9. `evidence.open_questions[]`
10. historical `run.repo_revision`, `engine.fork_revision`, image digest, and
    explicit ambiguity
11. exact or ambiguous hardware variant
12. `engine.backend`, environment, kernel patches, and
    `spec_decode_profile` when sourced
13. `requirements.memory_profile`
14. `requirements.offload`
15. `correctness`
16. `known_failures[]`
17. `capability_observations[]`
18. source locators, archive paths, retrieval dates, and lineage IDs

Interconnect and serving fields enter the pilot only where the source already
states them and they answer a pilot question. Power, thermal curves, noise,
cost, and package graphs remain later optional fields.

## 5. Eight-pilot admission rules

### Pilot 01 — dual DGX Spark

- C2 observation, uncontrolled contrast for MTP off/on.
- Not a C3 example.
- Preserve the repository-after-announcement pin ambiguity.
- Expose checkpoint-path discrepancy and RoCE/setup prerequisites.

### Pilot 02 — RTX 4090 DFlash2

- The only pilot eligible for C3 + single-variable, scoped to the cited
  builder comparison and stated protocol.
- Treat this as an author-reported matched comparison with partial condition
  completeness: binary provenance for the native-MTP and DFlash2 arms is
  unresolved. Do not label it verified.
- If revision recovery shows other load-bearing build differences, downgrade
  the contrast to bundle or uncontrolled.
- Quality status remains unchecked at the headline operating point.
- Sample count and independent reproduction remain absent.
- Prefill reversal and broken multi-GPU/multimodal behavior remain visible in
  Lite.

### Pilot 03 — Strix Halo

- C2 observation + bundle, not component-level causality.
- Preserve branch/history pins and byte-clean check scope.
- Kernel/loader constraints are configuration/failure claims.

### Pilot 04 — M3 Ultra

- C2 author/vendor observation with incomplete conditions.
- No C3 language for 23 → 87.6.
- Missing context, flags, and protocol remain visible.

### Pilot 05 — dual RTX 5090

- Vendor speed and quality evidence remain separate.
- Ambiguous 8k/32k prefill semantics cannot be plotted or directly compared.
- Vendor quality table does not independently reproduce speed.

### Pilot 06 — Mac 64 GB pageable PLE

- Pageable PLE is a load-bearing structured offload fact, vendor-attributed.
- The 84.9 GB total must not become an unconditional fit statement.
- Cold-start effect remains absent unless explicitly sourced.

### Pilot 07 — RTX PRO 6000

- Do not infer offload from 111 GB artifact versus 96 GB device.
- Block practical-fit language until method is resolved.
- Preserve one operating point and vendor-tier conditions.

### Pilot 08 — Ollama RTX 3090

- C2 wall-clock-derived observation.
- Excluded from representative headline/baseline speed.
- Crowd range is corroboration only, not reproduction.

No pilot is C4 independently reproduced.

## 6. Implementation phases

### Phase A — Foundation, no UI

1. Add schema-version-2 optional shapes to `SCHEMA.md` and validator.
2. Add canonical technique registry schema and initial technique packets needed
   by the eight pilots.
3. Add nested link traversal and lineage/reference checks.
4. Teach candidate vetting and coverage tools the optional shapes.
5. Assign stable IDs to all current measurements without inventing conditions.
6. Keep all 79 legacy records valid.

Exit gate: current full check remains green; negative fixture tests prove false
C3/C4, hidden offload, wall-clock, and ambiguity cases fail or warn correctly.

### Phase B — Pilot data migration

1. Record the three resolved historical pins and resolve or explicitly exhaust
   the two remaining recoverable artifacts.
2. Migrate the eight setup records only.
3. Move every completeness-matrix `B` item into a structured field when its
   source supports it.
4. Preserve `I` and `N` as explicit open questions or absent values.
5. Run sentence-to-source review on every Lite/Pro claim.

Exit gate: dossiers and setup JSON agree; only pilot 02 receives C3;
no pilot receives C4; no fit/offload/quality inference is introduced.

### Phase C — Lite / Pro presentation

1. Add global mode state, URL preservation, saved preference, and accessible
   control.
2. Refactor the shared detail renderer into one mode-aware semantic composer.
3. Implement the seven Lite sections and Pro expansions from the content
   contract.
4. Extend Compare, My Hardware, Methodology, and Contribute without changing
   compatibility arithmetic or provenance laws.
5. Render plain-language evidence labels with codes available in Pro audit.

Exit gate: both modes pass browser, accessibility, offline, mobile, dark/light,
zoom, route-state, and evidence-invariant tests.

### Phase D — Pilot release and observation

1. Publish the eight enriched recipes.
2. Collect owner and expert feedback on usefulness, not visual novelty.
3. Audit whether readers understand matched, observed, vendor, wall-clock,
   quality, and reproduction distinctions.
4. Adjust the contract before migrating the remaining 71.

### Phase E — Remaining 71

Migrate in engine/technique batches only after pilot acceptance. Do not bulk
generate causal prose from existing caveats.

## 7. Required approvals

Before Phase A begins, approve or change:

1. nested setup evidence plus separate canonical technique packets;
2. causal levels C0-C4 with quality separate;
3. plain-language UI labels with codes in Pro audit;
4. derived condition completeness;
5. stable IDs for all 190 measurements;
6. conditional revision-pin severity;
7. exclusion of wall-clock-derived rates from representative headlines;
8. closure of five recoverable-artifact rows and outreach for two blockers;
9. Lite as the new-visitor default.

No live migration should start with any of these unresolved.
