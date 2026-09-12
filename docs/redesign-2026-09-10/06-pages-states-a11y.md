# 06 — Trust model, supporting pages, states, accessibility, responsive

---

## 1. The trust model

One badge is replaced by four independent dimensions. They are never averaged,
never summed, and never collapsed into a single score.

### Recipe confidence — *can I install this?*

| Level | Glyph | Condition in this dataset |
|---|---|---|
| Clean-install tested | `●` | A source records a clean-install verification with a date. **Not recorded today — the field does not exist yet; see doc 07.** |
| Complete community recipe | `◑` | `run.repo` present **and** (`run.command` or ≥2 `run.steps`) **and** `requirements.memory_gb` present. 31 of 65. |
| Incomplete recipe | `◐` | A sourced lane with steps but no command, or with gaps. 34 of 65. |

### Compatibility confidence — *will it run on my hardware?*

| Level | Glyph | Condition |
|---|---|---|
| Exact-device evidence | `●` | A measurement on a hardware class that is a single SKU with `measured_by_us: true`. |
| Similar-device evidence | `◑` | Evidence on a class that is a range, or on a same-architecture sibling (DGX Spark ↔ ThinkStation PGX, same GB10 silicon). |
| Estimated | `◐` | Recorded requirement fits, no evidence on that hardware. |
| Unknown | `○` | No requirement recorded, or no hardware evidence. |
| Unsupported | `✕` | A caveat records that this path does not run on that hardware. |

### Performance confidence — *is the number real?*

| Level | Glyph | Condition |
|---|---|---|
| Controlled repeated measurement | `●` | `provenance: box` with `n > 1` and a `method`. |
| Repeated community measurement | `◑` | `provenance: forum` with `n > 1` or an explicit `stat` over a stated sample. |
| Single community report | `◐` | `provenance: forum`, single value. The commonest state — 28 setups. |
| Vendor claim | `◔` | `provenance: vendor`. 1 setup. |
| Unknown | `○` | No speed measurement. 33 setups. |

`box` with `n == 1` — which is what the four owner-measured setups actually
carry — lands at `◑`, not `●`. The dataset's own caveats say these are *"one
boot and one fixture — indicative, not a guarantee"*. The interface agrees with
the caveat rather than with the tier label.

### Capability confidence — *does this recipe actually do vision / tools?*

| Level | Glyph | Condition |
|---|---|---|
| Tested through this recipe | `●` | A capability observation with a source. Not recorded today. |
| Runtime-declared | `◑` | `setups[].capabilities` set and the engine's `features` corroborate. |
| Model-declared | `◐` | Only `models[].modalities` supports the claim. |
| Partial | `◔` | Some modalities on, some off — the 8 vision-disabled setups. |
| Unsupported | `✕` | Recipe records the capability as false where the model has it. |
| Unknown | `○` | `null` in `capabilities`. 3 setups for `tools`, 7 for `thinking`. |

### The rule the strip exists to enforce

A recipe may read `◑ ● ○ ○` — a complete recipe, exact-device compatibility
evidence, **no** performance evidence, **no** capability evidence. Under the old
single badge that setup showed one tier and read as uniformly weak or uniformly
strong depending on which number happened to exist. Four dimensions make the
actual shape legible, and it is the shape most of this dataset is in.

Individual measurements keep their own `box` / `forum` / `vendor` provenance
beside the value. The strip summarises; it never replaces a number's own source,
and the two are never blended.

---

## 2. Recipe detail page — `#/recipes/<setup-id>`

The canonical page. Stable URL, shareable, citable. Section order is fixed and
matches the in-place expansion exactly.

1. **Recipe identity and maintenance status** — title, model family link,
   checkpoint, publisher, builder, engine, the four-dimension strip, `updated`,
   freshness word, maintenance status.
2. **What the recipe runs** — `slug_note` as plain language, then artifact
   (checkpoint, quant, `quant_detail`, format, size, license, URL), then the
   model family's architecture in brief with a link to `#/models/<id>`.
3. **Complete run instructions** — `run.command` with a copy button; ordered
   steps with `cmd` in monospace and individually copyable, `do` in prose with
   no copy affordance; repo and profile links; `auto_bootable`.
4. **Tested hardware** — each class with memory, usable memory, bandwidth,
   architecture, `measured_by_us`, and the class-vs-SKU note.
5. **Measurements** — a full table: metric, value, unit, statistic, concurrency,
   sample count, method, date, provenance, source link, note. Grouped by
   provenance tier with the tiers visually separated and never interleaved.
6. **Capability support** — model band and recipe band, side by side, with the
   runtime reason where a capability is off.
7. **Compatibility reports** — what hardware this has been recorded on, and a
   link to check it against a saved profile in My Hardware.
8. **Known failures** — promoted out of caveats where a caveat records a crash,
   corruption, OOM or incompatibility; rendered with `✕` above the general
   caveats.
9. **Caveats** — every one, in full, under the heading *"What these numbers do
   not mean."*
10. **Sources and revision history** — every source with its `kind` and note,
    and the `updated` date. A `Raw JSON` disclosure renders the setup record
    verbatim with a copy button, for integrations and for anyone auditing what
    the page did with the data.

---

## 3. Model family page — `#/models/<model-id>`

The shelf header expanded into a page: full architecture (`layers`,
`layer_mix`, `hybrid`, `mtp_head`, thinking depths, `sglang_arch`), context and
extension method, modalities and output modalities, license, release date,
`summary`, `sampler_guidance`, `known_regressions`, `fit_note`, official
repository link — then every recipe for the family as the same row grid used in
the Directory, with the same compare controls.

## 4. Publisher page — `#/publishers/<publisher-id>`

Name, kind (lab / quant-shop / builder / individual / community-org / vendor),
role, URL — then every artifact they publish and every recipe that builds on it,
with an evidence summary across their entries. Reachable from any publisher name
anywhere in the product.

## 5. `#/methodology`

The evidence model in full: the three provenance tiers and why they are never
blended; the four confidence dimensions and their level conditions; how the
representative decode figure is chosen; why there is no quality leaderboard; the
derived-complexity formula written out; the reading-speed anchor with its
constant stated (~250 wpm, ~0.75 words/token ⇒ ~5 tok/s ≈ reading speed) so the
multiplier is auditable; the coverage table (65 / 22 / 6 / 7 / 29 and the
provenance split); and the known gaps, including the ones this audit found —
`kv_bytes_per_token` on 1 of 22 families, no engine version, no OS field, no
failure entity, Reddit unreachable from the collection environment so no
Reddit-sourced number is recorded anywhere.

## 6. `#/contribute`

The provenance contract as a submission guide: what a recipe needs to be
accepted, what a measurement needs (source, method, statistic, hardware,
context, concurrency, date), why a number with no source is deleted rather than
downgraded, why negative results are wanted, and the `check.sh` gate. Links to
`AGENTS.md`, `SCHEMA.md` and the repository.

---

## 7. Non-happy states

| State | Where | Rendering |
|---|---|---|
| **Empty — filters** | Directory | `No recipes match these 4 filters.` The active-filter chips stay visible and individually removable, plus `Clear all`. Two suggestions generated from the filter set, e.g. *"Removing `Evidence: owner-measured` would show 61."* |
| **Empty — search** | Directory | Query echoed, plus the fields searched, plus the nearest matches by checkpoint substring. |
| **Empty — hardware** | My Hardware | Never empty. All 65 are grouped; a group with zero members shows its heading and a zero, because *"nothing is verified on this exact machine"* is the answer. |
| **Empty — compare** | Compare | Explanatory, not an error. |
| **Loading** | All | The dataset is inlined; there is no fetch and therefore no loading state for data. The only async work is the WebGPU adapter query on My Hardware, which shows an inline `detecting…` on that control only and times out at 2s into `not detectable`. |
| **Error — bad route** | Any | A 404 view naming the route, with the Directory, search, and the route map. Never a blank page. |
| **Error — stale recipe id** | Recipe page, compare URL | Names the missing id, offers search, renders the rest. |
| **Error — storage blocked** | My Hardware | Every `localStorage` access is wrapped in `try/catch`; on failure the tab works fully for the session and says `Profiles cannot be saved in this browser — this one will be lost on reload.` |
| **Warning** | Everywhere | `▲` plus a word, `--warn`. Caveat counts appear on collapsed rows so a warning is never hidden behind an interaction. |
| **Failure** | Row, recipe, compare | `✕` plus `--bad`, the failure sentence visible collapsed. |
| **Incomplete data** | Everywhere | `not recorded`, `--ink-4`, italic. Never `0`, `—`, `N/A`, or blank. Where a whole field is unrecorded across the dataset (engine version, OS), the row still renders so the gap is visible. |

---

## 8. Accessibility

**Landmarks and headings.** `<header>` with `<nav>` for the tabs, `<aside>` for
the family rail, `<main>` for the view, `<footer>`. One `<h1>` per route,
`<h2>` per shelf, `<h3>` per section within a detail panel. The heading order is
never skipped.

**Tabs.** The three primary tabs are links with real `href` values, marked
`aria-current="page"`. They are navigation, not an ARIA tablist — each has its
own URL and its own history entry, and forward/back work.

**Shelves.** Each shelf is a `<section>` labelled by its `<h2>`. The collapse
control on mobile is a `<button aria-expanded>` controlling the shelf body by
`aria-controls`.

**Rows.** Each row's expand control is a `<button aria-expanded aria-controls>`
whose accessible name is the recipe title, not `▸`. The whole row is not a
button — that would make the compare checkbox and the links inside it
unreachable. `Enter`/`Space` on the expand button toggles; `Escape` inside an
expanded panel collapses it and returns focus to the control.

The row grid is a real `<table>` on desktop with `<th scope="col">` per column
and `<caption>` naming the family, so screen readers announce the column when
reading a cell. The two-line cell structure sits inside the `<td>`. On mobile
the same data renders as a definition list per row, chosen by CSS and a matching
DOM swap — never a table forced into 390px.

**Filters.** Every control has a visible `<label>` or an `aria-label` naming
both the facet and its scope (`Filter by hardware class the recipe was tested
on`). The result count is an `aria-live="polite"` region announcing
`24 of 65 recipes` after each change. Active-filter chips are buttons whose
accessible name is `Remove filter: Engine SGLang`.

**Compare controls.** Each is a real `<input type="checkbox">` with an
accessible name of `Compare <recipe title>`, `aria-describedby` pointing at the
capacity note when the limit is reached. The rail is `role="region"`
`aria-label="Compare selection"` and `aria-live="polite"`, announcing
`3 of 4 selected` on change. It is placed at the end of the DOM and reached by
keyboard after the content, with a skip link to it once it exists.

**Focus.** `:focus-visible` ring, `2px --sel`, `2px` offset, never removed, on
every interactive element. Focus is never trapped — the advanced filter panel
and detail panels are inline disclosures, not modals. Expanding a row does not
move focus; collapsing from inside returns it.

**Colour independence.** Every status is glyph + word + colour. The evidence
strip's accessible name is a full sentence. The compatibility groups are named
in text. A greyscale screenshot of any view remains fully readable — this is a
review checkpoint, not an aspiration.

**Contrast.** All body text ≥ 4.5:1 against its ground; all large and bold text
≥ 3:1; focus ring ≥ 3:1 against both `--paper` and `--surface`. `--ink-4` is
restricted to text that is duplicated by a glyph and a word.

**Touch.** Minimum 44×44 for every control on mobile, including compare
checkboxes, chip removals and rail entries.

**DOM and visual order match** in every layout. The family rail precedes the
content in the DOM and is positioned by grid, not by float or absolute
placement. Nothing is reordered visually away from its reading position.

**Reflow.** No horizontal page scroll from 320px to 1920px, and at 400% zoom on
a 1280px viewport. Wide content — the compare table, measurement tables, command
blocks — scrolls inside its own `overflow-x: auto` container with a labelled
scroll region, never by moving the page.

**Reduced motion.** `prefers-reduced-motion: reduce` collapses every transition
to `0.01ms` and drops transforms. No information is conveyed by motion.

---

## 9. Responsive behaviour

| | Desktop ≥ 1180 | Tablet 720–1179 | Mobile < 720 |
|---|---|---|---|
| Global nav | Sticky, full, three tabs + utility | Sticky, three tabs | Sticky, three tabs, compact |
| Family index | Sticky 208px rail with scroll-spy | `Families ▾` selector in the filter bar | `Families ▾` drawer |
| Common filters | All seven persistent in the bar | Persistent, wrapping to two lines | Behind `Filters (n)` sheet |
| Advanced filters | Inline disclosure panel | Inline disclosure panel | Inside the sheet, below common |
| Recipe row | 10 columns, 2 lines | 6 columns, 2 lines | Structured summary, 4 stacked lines |
| Shelf header | Full spec strip | Spec strip, wrapping | Core fields + `▸ full model spec` |
| Detail | In-place panel, 2-column field grid | In-place panel, 1 column | In-place panel, 1 column |
| Compare rail | Full chips + comparability line | Full chips, comparability line wraps | Count + action + clear |
| Compare workspace | Fixed identity column + N columns | Same, container scrolls | Section-by-section, recipes stacked |
| My Hardware | Two panes, sticky profile | Two panes, profile above | Stacked, profile collapses to a summary line |

Breakpoints are chosen by where the content breaks, not by device names: 1180 is
where ten columns stop being legible, 720 is where six columns stop fitting.
