# 05 — Tab 3: Compare

Route `#/compare`, and `#/compare?sel=<id>,<id>` for a shareable comparison.
A dedicated workspace, never a matrix embedded in the Directory.

---

## 1. The compare rail — the signature interaction

Selection happens anywhere: Directory rows, model-family pages, recipe pages,
My Hardware results. The rail is the thread connecting them.

**It does not exist at zero selections.** Not empty, not collapsed, not a
zero-state prompt — absent, with no space reserved.

At one or more selections it enters from the bottom edge (translateY 8px, 140ms,
suppressed under reduced motion):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ▣ COMPARING 3                                                               │
│ ┌───────────────────────┐┌───────────────────────┐┌───────────────────────┐ │
│ │ …NVFP4-BF16-LMHead  ✕ ││ …NVFP4-Packed       ✕ ││ …-GGUF              ✕ │ │
│ │ SGLang ⑂ · NVFP4      ││ SGLang ⑂ · NVFP4      ││ llama.cpp · Q4_K_M    │ │
│ │ DGX Spark             ││ DGX Spark             ││ 24 GB GPU             │ │
│ └───────────────────────┘└───────────────────────┘└───────────────────────┘ │
│ ▲ Mixed engines and hardware — speeds are not directly comparable           │
│                                              Clear all │ [ Compare 3 → ]    │
└─────────────────────────────────────────────────────────────────────────────┘
```

What the rail communicates, per the brief:

- **Selected recipes** — checkpoint tail, enough to tell two NVFP4 exports apart.
- **Engine and quantization differences** — each chip's second line, so the
  difference is legible before opening the workspace.
- **Whether measurements appear comparable** — a live one-line verdict:
  - `● Same engine, same hardware — speeds are directly comparable`
  - `▲ Mixed engines and hardware — speeds are not directly comparable`
  - `▲ 2 of 3 have no speed measurement`
- **Remove controls** — a `✕` per chip, plus `Clear all`.
- **A clear action to open Compare** — the primary button, with the count.

Capacity is **2 to 4**. At one selection the button reads `Select one more to
compare` and is disabled with an accessible explanation. At four, further
compare controls in the Directory go disabled with the tooltip
`Compare holds 4 — remove one first`, rather than silently ignoring the click.

State lives in `sessionStorage` and in the URL when the workspace is open, so a
comparison is shareable. On mobile the rail collapses to
`▣ 3 selected · Compare →  ✕`.

---

## 2. The workspace

A fixed identity column on the left and one column per recipe, horizontally
scrollable inside its own container if four columns exceed the viewport — the
page itself never scrolls sideways.

Seven sections, in the brief's order, each a labelled row group with a hairline
above it. Section heads are sticky within the scroll container so the reader
always knows which group a row belongs to.

### 2.1 Identity

Model family · checkpoint · publisher · quantization · quant detail · format ·
artifact size · weight license · artifact URL.

### 2.2 Runtime

Engine · **engine version** · operating system · required fork · speculative
decoding path · draft model · important flags · container image · installation
complexity (derived, labelled derived).

> Engine version and operating system are **not fields in the current schema**.
> Every cell reads `not recorded`, uniformly, for all 65 recipes. That is the
> correct rendering: it shows the reader a real gap in the dataset instead of
> hiding a row that ought to exist. Doc 07 proposes both as schema additions.

### 2.3 Hardware

Tested devices · recorded minimum memory · recorded resident memory · disk
requirement · offload strategy · power and thermal notes · whether the class is
a SKU or a range · `measured_by_us`.

### 2.4 Capabilities

Two bands, never merged:

```
                        recipe A          recipe B
MODEL CAPABILITY   text · image · video     text · image · video
RECIPE SUPPORT     text ✓                   text ✓
                   image ✕ runtime          image ✓
                   tools ✓  thinking ✓      tools ✓  thinking ✓
NATIVE CONTEXT     262,144                  262,144
TESTED CONTEXT     not recorded             32,768
RUNTIME LIMITS     no YaRN above 262144     —
```

The model band comes from `models[].modalities`; the recipe band from
`setups[].capabilities`. They are visually separated because they answer
different questions with different evidence.

### 2.5 Performance

The section with the strictest rules, because it is where a comparison tool
most easily lies.

Rows: single-stream decode · prefill · TTFT · aggregate throughput · per-stream
throughput at load · concurrency · context length · statistic type (mean /
median / peak) · measurement protocol · sample count · date · provenance tier.

- Two cells align in the same row **only** when metric, concurrency band and
  statistic type match. Otherwise each cell renders its own conditions inline
  and the row is marked `▲ not directly comparable`.
- Every value carries its unit, its condition, and its provenance label. There
  is no bare number anywhere in this section.
- Aggregate and per-stream figures always appear together where both exist.
- A missing measurement renders `no measurement`, in `--ink-4` — never `0`,
  never a blank cell, never an interpolated value.
- **No cell is highlighted as the best.** No bolding of a maximum, no green tint
  on a winner, no arrows.

### 2.6 Trust

The four confidence dimensions as four rows, plus last verification date and
source quality (count of sources by `kind`, with links).

Each cell is the level word plus its glyph plus the reason:
`◐ single community report — one builder's README, no method stated`.

### 2.7 Risks

Known failures · unsupported features · disabled capabilities · quality
regressions (model-level, from `known_regressions[]`) · context limitations ·
maintenance status · full caveat list.

Caveats are shown **in full**, not truncated. In this dataset the caveat text is
frequently the most valuable content in a record — the ik_llama.cpp cross-vocab
corruption note, the YaRN/DFlash2 crash above 262144, the disputed −20–25%
decode counter-report. Truncating them would defeat the section.

---

## 3. Incomparability detection

Runs on every selection change and renders as a banner above the workspace,
before any table. It never blocks the comparison; it qualifies it.

| Check | Trigger | Banner line |
|---|---|---|
| Hardware | measured on different hardware classes | `Measured on different hardware — DGX Spark (GB10, 273 GB/s) vs 24 GB GPU (936–1008 GB/s). Memory bandwidth differs by ~3.5×.` |
| Concurrency | different `concurrency` on the compared metric | `Different concurrency — 1 stream vs 48 streams. These are different quantities.` |
| Metric | different metric families | `Different workloads — chat decode vs code decode.` |
| Statistic | `stat` differs | `Different statistics — a mean and a peak.` |
| Context | different tested context | `Different context lengths — 8K vs 32K.` |
| Provenance | tiers differ | `Different evidence tiers — owner-measured vs community-reported. These are not blended.` |
| Coverage | one or more has no measurement | `2 of 3 recipes carry no speed measurement — the performance section is mostly empty by design.` |
| Architecture | different model families | `Different model families — this compares runtimes, not the same weights.` |

**No overall winner is ever declared.** There is no score, no ranking, no
"recommended" marker, and no aggregate. The closest the workspace comes to an
opinion is a factual line such as *"Only one of these carries owner-measured
evidence"* — a statement about the evidence, not about which is better.

---

## 4. States

| State | Rendering |
|---|---|
| **Empty** (`#/compare` direct, nothing selected) | Not an error. A short explanation of what Compare does and how to select, plus a link to the Directory and the three most-populated shelves as a starting point. |
| **One selected** | The rail's disabled state with its reason; the workspace explains that comparison needs two. |
| **Two to four** | The full workspace. |
| **Fully comparable** | Banner reads `● Same engine, same hardware, same statistic — these speeds are directly comparable.` The one case where a positive statement is earned. |
| **Fully incomparable** | Every performance row marked; the banner lists every axis. Tables still render — the identity, runtime, hardware, capability and risk sections remain useful even when performance is not. |
| **Missing data** | `not recorded` per cell. A row where all cells are `not recorded` still renders, so the reader learns the field is unrecorded across the board rather than that it does not exist. |
| **Stale selection** | A recipe id in the URL that no longer exists renders a note naming the id and continues with the rest. |

---

## 5. Mobile

The desktop table is never compressed into the viewport. Comparison becomes
**category by category**:

```
┌───────────────────────────────┐
│ ← Compare 3                   │
│ ▲ Mixed engines and hardware  │
│ [Identity][Runtime][Hardware] │  ← horizontally scrollable section tabs
│ [Capabilities][Perf][Trust][Risks]
├───────────────────────────────┤
│ PERFORMANCE                   │
│ ▲ not directly comparable     │
│                               │
│ SINGLE-STREAM DECODE          │
│  A  56.6 tok/s                │
│     chat · 1 stream · box     │
│  B  28.4 tok/s                │
│     code · 1 stream · forum   │
│  C  no measurement            │
│                               │
│ AGGREGATE THROUGHPUT          │
│  A  227.6 tok/s @16 streams   │
│     28.2 tok/s each at load   │
│  B  no measurement            │
│  C  no measurement            │
└───────────────────────────────┘
```

One section at a time, recipes stacked within each field, each labelled by a
short recipe key (A/B/C) that maps to a legend pinned at the top. No horizontal
page scroll at any width.
