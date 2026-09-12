# 01 — Audit and product map

**Audited:** `711e97f` (Improve directory UX and benchmark semantics), the built
`directory/site/index.html`, and the full dataset under `directory/data/`.
**Date:** 2026-09-10.
**Authority:** `directory/AGENTS.md` for product truth and provenance rules.

---

## 1. What exists today

One generated HTML file. One view. No routes. `build.py` is a 1,202-line Python
module whose body is a single ~1,100-line raw string containing the entire
template, stylesheet, and application script.

Measured on the current build at 1440×1000: **page height 15,831 px**, no
horizontal overflow. The first recipe appears roughly 900 px down the page.

Page order, top to bottom:

| Band | Content | Height at 1440 |
|---|---|---|
| Masthead | `<h1>`, one-sentence tagline | ~130 px |
| Machine picker | "First: what are you running this on?" — four device cards | ~190 px |
| Orientation | "New here? How local hosting works" — three-step essay, two nested `<details>` | ~280 px |
| Controls | search, sort, two rows of six selects | ~110 px |
| Body | 22 model groups, 65 expandable cards in one flat scroll | ~15,000 px |

### The dataset, as of this audit

| | |
|---|---:|
| Runnable setups | 65 |
| Model families | 22 |
| Hardware classes | 6 |
| Engines | 7 |
| Publishers and builders | 29 |

Distribution that the redesign has to survive contact with:

- **Setups per family is wildly uneven.** Qwen3.8-27B has 15; Qwen3.8-Flash-Next
  has 8; eleven families have exactly 1. A layout that assumes "a shelf holds
  six rows" breaks on both ends.
- **Evidence is thin and must look thin.** 4 `box`, 28 `forum`, 1 `vendor`,
  **32 with no measurement at all**. Half the directory is a sourced lane, not
  a measured result.
- **34 of 65 setups have no copyable command.** They carry ordered prose steps.
- **Engines cluster hard:** vLLM 23, SGLang 22, llama.cpp 11, MLX 6, and one
  each of Ollama, LM Studio, custom-fork.
- **Hardware clusters harder:** DGX Spark appears on 47 setups; the whole
  non-NVIDIA/non-Apple world is absent.
- **13 setups require an engine fork.**
- **8 setups run a vision-capable model through a runtime that does not do
  vision** — the model/recipe capability split the brief calls for is already
  in the data and is currently invisible.

### Data gaps found during the audit

These are recorded here so the design can represent absence honestly rather than
paper over it. **None of them is filled by invention.**

| Gap | Extent | Consequence for the design |
|---|---|---|
| `kv_bytes_per_token` | present on **1 of 22** models (Qwen3.8-27B only) | A KV-cache allowance can only be computed for one family. Every other compatibility result must say the KV term is not derivable. |
| `engine.version` | not in the schema at all | Compare's "Engine version" row reads *not recorded* for all 65. |
| Operating system | not a field | The OS filter can only be *implied* from the tested hardware class's `arch`, and must be labelled as implied. |
| `params_active_b` | null on 6 models, all dense | Dense active params render as "all — dense", which is definitional, not a measurement. |
| Failure reports | prose inside `caveats[]` | Known failures render from caveats and are not machine-queryable. A `failures[]` entity is proposed in doc 07. |
| `status: "broken"` | in the enum, used by 0 setups | The failure state must be designed anyway; it is reachable. |
| Setup complexity | not a field | Derived from engine class + fork requirement + step count, and labelled as derived. |

---

## 2. What is wrong with the current product

Not taste. Each item below blocks the audience this redesign is for.

**A1 — Personalization is a gate on the catalogue.** The machine picker is the
first interactive element on the page, and three separate behaviours key off it:
the fit verdict on every row, the "Start here" recommendation, and one filter.
An operator who arrives knowing exactly which checkpoint they want must scroll
past a questionnaire to reach a list.

**A2 — Onboarding owns the first viewport.** Machine picker plus the
three-step orientation consume ~470 px before a single control, and ~900 px
before a single recipe. The brief's first-viewport contract cannot coexist with
this band.

**A3 — Trust is one badge doing four jobs.** `provenance_tier` is rendered as a
single pill and read as a global quality score. It actually answers only *"how
good is the best speed number here?"* It says nothing about whether the install
was verified, whether the hardware claim was tested, or whether the capability
flags were checked. A recipe can be clean-install verified with no measurements
at all; today that reads as the weakest possible state.

**A4 — Nothing is addressable.** One page, no routes. A recipe cannot be linked,
cited in an issue, or bookmarked. There are no model-family pages, no publisher
pages, no methodology page. For a reference directory this is the most serious
structural defect on the list.

**A5 — There is no comparison.** The dataset's whole point is that Qwen3.8-27B
has fifteen ways to run it that differ in engine, quant, spec-decode path and
context ceiling. The product offers no way to put two of them side by side.

**A6 — Filtering is far below the data's resolution.** Six selects — engine,
hardware, quant, tier, fit, readiness. Absent: generation, family, parameter
range, dense/MoE, modality and capability, artifact format, OS, complexity,
stock-vs-fork, publisher, freshness, known-failure. The dataset supports all of
them.

**A7 — The card is the wrong unit.** 65 full-width cards in one scroll, each
with a chip strip, is a 15,800 px page. Cards resist scanning: you cannot
compare quant across four rows when each row is 240 px tall and its fields are
not column-aligned.

**A8 — The generator is not a codebase.** One string literal holding template,
CSS and JS. It cannot be diffed usefully, linted, or reviewed section by
section, and it forces every change through one file.

---

## 3. Relationship to `docs/UX-REVIEW-2026-09-07.md`

That review was written to a different brief — *"a newcomer to local hosting
could not use the page to learn anything."* This brief inverts the audience:
advanced users and operators are primary, and beginner onboarding must not
dominate. The two documents disagree, and the disagreement is deliberate. This
is how it resolves.

### Kept in full — every truth-telling correction survives

| From the review | Status |
|---|---|
| P0-1 single-stream tok/s wins the headline; never a bare number; aggregate shown with its concurrency | **Kept and extended.** Becomes the `Decode` column contract and the Performance section rules in Compare. |
| P0-2 no fit verdict without a declared machine | **Kept and hardened.** Verdicts now exist only inside My Hardware, and even there the unconditional "Fits" is banned outright. |
| P0-3 `cmd` vs `do` step kinds, prose never in a copy affordance | **Kept.** Already in the schema and validator; the new run block honours it. |
| P0-4 completeness is stated before the click | **Kept.** Becomes the `Ready` column, a first-class filter, and a sort mode. |
| P0-5 never pass an HTML entity through `esc()` | **Kept as a standing rule.** |
| P2-3 reading-speed anchor | **Kept, demoted.** Moves from the row into the expanded detail and the glossary; it is orientation, not a scanning field. |
| P2-4 empty-state copy with a one-click clear | **Kept.** |

### Replaced — the structural recommendations, because the audience changed

| From the review | Replaced by |
|---|---|
| P1-1 machine picker as the page header | The **My Hardware tab** at `#/hardware`. The picker is a destination, not a gate. |
| P1-2 a single "Start here" recommendation above the list | Removed from the Directory. Ranked, grouped compatibility results live in My Hardware. The Directory has no opinion; it has an index. |
| P1-3 two-tier filters with common filters hidden behind "More filters" | Inverted. Common filters are **always visible**; the tier boundary moves so that *specialist* filters go into Advanced Filters and everything an operator uses daily stays on the surface. |
| P1-6 the three-step "how local hosting works" band above the list | Moves to `#/methodology`, with contextual definitions in place. |
| P2-2 stats to the footer | Kept out of the first viewport, but they become the coverage table on `#/methodology` rather than footer decoration. |

### Superseded constraint

The review's constraint list pins `#f-engine`, `#f-hw`, `#f-quant`, `#f-tier`,
`#f-fit`, `#sort`, `#expand-all`, `#reset`, `.card`, `#out`, `#counts`, `#gen`,
`#hint` because `verify_browser.py` drives them. Those ids belong to an
architecture this redesign deliberately replaces. **The browser suite is
rewritten to drive the new interface at equal or greater coverage** — see doc 08
for the old-check → new-check mapping. This is an architecture replacement, not
a weakening: no check is dropped without a stronger replacement, and none of
`validate.py`'s data rules is touched.

---

## 4. Product map

### The three tabs

| Tab | Route | Question it answers | Personalization |
|---|---|---|---|
| **Directory** | `#/` | *What ways exist to run Qwen locally?* | None. Never gated. |
| **My Hardware** | `#/hardware` | *What can **this** machine run, and how confident is that?* | All of it, here only. |
| **Compare** | `#/compare` | *How do these 2–4 recipes actually differ?* | None. Selection only. |

The Directory is the homepage and the default. Neither of the other tabs can
restrict it, and no state from them narrows it without the user asking.

### Preserve / migrate / replace / remove

| Current behaviour | Verdict | Notes |
|---|---|---|
| Provenance tiers, never blended | **Preserve** | Non-negotiable. Extended into four confidence dimensions; tiers still never mix. |
| Negative results and caveats kept visible | **Preserve** | Promoted: caveats become a top-level recipe section and a Compare "Risks" row group. |
| `cmd`/`do` step rendering | **Preserve** | |
| Single-stream headline speed | **Preserve** | Now with mandatory condition text in every position it appears. |
| Model grouping | **Migrate** | Group → **model-family shelf** with a full spec header and a column-aligned row grid. |
| Search + sort | **Migrate** | Search widened to commands and notes; six sort modes become nine. |
| Six filter selects | **Migrate** | Split into always-visible common filters and an Advanced Filters panel; ~18 facets total. |
| Expandable card body | **Migrate** | Expands in place as a row detail panel **and** gets a permanent page at `#/recipes/<id>`. |
| Machine picker | **Migrate** | Whole feature moves to `#/hardware`, gains manual entry, import/export and saved profiles. |
| Fit badge on every row | **Replace** | Directory rows show the neutral recorded requirement. Verdicts exist only in My Hardware, as five graded states. |
| One `provenance_tier` pill | **Replace** | Four independent confidence dimensions. |
| "Start here" recommendation on the homepage | **Remove** | Directory holds no opinion. |
| Orientation essay band | **Remove from `#/`** | Relocated to `#/methodology`. |
| Vanity counts strip | **Remove from `#/`** | Becomes the coverage table on `#/methodology`. |
| Single-file 1,200-line generator | **Replace** | `site_src/{shell.html,app.css,app.js}` inlined by `build.py`. Still stdlib-only, still one self-contained output file. |

### Entities the interface now exposes

Model family · Artifact (checkpoint) · Engine · Recipe · Recipe step · Hardware
class · Compatibility observation · Measurement · Capability observation ·
Failure/caveat · Source · Publisher/contributor.

Doc 07 states which of these exist in the data today, which are derived for
presentation, and which are proposed schema additions.

---

## 5. Route map

Routing is **hash-based**, and that is a hosting constraint, not a preference.
`ifhost publish` accepts *exactly one HTML file* served at `/`; any real
sub-path would 404. Hash routes are stable, shareable, bookmarkable, work from
`file://`, and survive the existing one-file deployment unchanged.

| Route | View |
|---|---|
| `#/` | Directory (default; bare `/` resolves here) |
| `#/?q=…&engine=…&gen=…&…` | Directory with filter state — the shareable filtered view |
| `#/hardware` | My Hardware |
| `#/compare` | Compare workspace |
| `#/compare?sel=id,id,id` | Compare with an explicit selection |
| `#/models/<model-id>` | Model family page |
| `#/recipes/<setup-id>` | Recipe detail page |
| `#/publishers/<publisher-id>` | Publisher / contributor page |
| `#/methodology` | Evidence model, coverage, what the numbers mean |
| `#/contribute` | How to add a recipe; the provenance contract |

A path shim rewrites `/hardware`, `/compare`, `/models/x`, `/recipes/x` to their
hash equivalents on load, so the documented paths keep working if the site ever
moves to a host with directory rewrites. Unknown routes render a 404 view that
offers the Directory and search rather than dead-ending.

---

## 6. Primary user flows

**F1 — Browse the catalogue (default, no personalization).**
Land on `#/` → all 22 shelves render → jump via the family rail or scroll →
expand a row in place → read commands, measurements, caveats → open
`#/recipes/<id>` for the permanent page or copy the command. *No machine
required at any step.*

**F2 — Find every way to run one family.**
`#/` → rail → *Qwen3.8-27B* → shelf header states architecture, context,
license, recipe and measured counts → 15 rows compare across quant, engine,
spec-decode → select 3 → Compare.

**F3 — Constrain by an engine the operator already runs.**
`#/` → `Engine: SGLang` + `Stock engine only` → 22 → 12 rows across 6 shelves →
sort *Strongest evidence* → expand the top row.

**F4 — Check a specific machine.**
`#/hardware` → Detect (or pick a known device, or enter a custom machine) →
set context and concurrency assumptions → results grouped into five confidence
bands → each states its memory arithmetic and whether the evidence is exact-device
or similar-device → send two to Compare.

**F5 — Decide between two recipes.**
Select rows anywhere → the compare rail appears → open `#/compare` → seven
sections → the comparability banner names every axis on which the measurements
are *not* comparable → no winner is declared.

**F6 — Cite a recipe.**
`#/recipes/<id>` → stable URL, sources with kinds and fetch dates, revision
history, and a raw-JSON view for integrations.

---

## 7. Boundaries this redesign holds

1. The Directory is the homepage and shows every recipe with no personalization.
2. No hardware state ever narrows the Directory unless explicitly asked for.
3. No unconditional "Fits" verdict, anywhere, ever.
4. Compare never declares an overall winner.
5. Model capability, runtime support, and task quality stay three separate
   claims with three separate evidence requirements.
6. Provenance tiers are never blended; quality canaries are never aggregated.
7. Negative results stay visible and get promoted, not buried.
8. `site/index.html` stays generated. `validate.py` is not weakened.
9. Nothing is published without explicit approval.
