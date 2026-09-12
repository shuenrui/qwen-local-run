# 08 — Implementation and verification plan

---

## 1. Build architecture

The current `build.py` is 1,202 lines, of which ~1,100 are one raw string
holding template, stylesheet and application script. That is replaced by a
generator plus separable source assets. Still Python 3 stdlib only, still no
runtime dependency, still **one self-contained output file** that works from
`file://` and makes no network request after load.

```
directory/
  build.py                 collect data → derive index → inline assets → site/index.html
  site_src/
    shell.html             skeleton with __CSS__, __DATA__, __APP__ placeholders
    app.css                design system, all layouts, all breakpoints
    app.js                 router, state, views, filters, compare, hardware
  site/index.html          generated — never hand-edited (AGENTS.md law 5)
```

Why this split and not a framework: the deployment target accepts exactly one
HTML file, the page must run from disk, and `validate.py`/`build.py` are
committed to stdlib-only. A bundler would buy nothing and cost the file's
self-containment. Splitting the assets buys reviewable diffs, which is the
actual problem with the current file.

`build.py` keeps `collect()` and adds a derived index — model ordering, per-model
recipe grouping, facet value sets with counts, and the searchable text blob per
recipe — computed once at build time rather than on every keystroke in the
browser. All four confidence dimensions are computed **in JS**, not baked in, so
that the browser suite can assert them against the raw dataset that is inlined
alongside; a value baked at build time could agree with itself while being wrong.

### Routing

Hash-based, for the reason in doc 01 §5: `ifhost publish` serves exactly one
file at `/`, so any real sub-path 404s. Hash routes are stable, shareable,
bookmarkable, and work from `file://`.

A path shim runs before the router: if `location.pathname` matches
`/hardware`, `/compare`, `/models/:slug`, `/recipes/:slug`, `/publishers/:slug`,
`/methodology` or `/contribute`, it rewrites to the hash equivalent. The
documented paths keep working if the site ever moves to a host with directory
rewrites, and nothing breaks today.

Filter state serializes into the hash query so a filtered Directory view is a
shareable URL, and restores on load.

---

## 2. Order of work

Each step ends with `python3 directory/check.sh` at zero errors. Nothing is
published at any step.

| # | Step | Risk |
|---|---|---|
| 1 | Scaffold `site_src/`, move the existing page verbatim into it, build, verify green. **Pure refactor — no behaviour change.** | Low. Establishes that the split works before any redesign lands. |
| 2 | Design system: `app.css` tokens, type scale, both themes, focus, reduced motion. | Low |
| 3 | Router, three-tab shell, path shim, 404 view, `#/methodology`, `#/contribute`. | Low |
| 4 | Directory: shelf, row grid, in-place expansion, family rail with scroll-spy. | **High — the core.** |
| 5 | Confidence engine: the four dimensions, the evidence strip, the popover. | Medium. Asserted directly against the inlined dataset. |
| 6 | Search, common filters, Advanced panel, active-filter chips, nine sorts, the speed disclosure. | Medium |
| 7 | `#/recipes/:slug`, `#/models/:slug`, `#/publishers/:slug`, raw-JSON view. | Low |
| 8 | Compare rail + workspace + incomparability detection. | Medium |
| 9 | My Hardware: detection, manual entry, profiles, the five groups, the arithmetic panel. | **High — the honesty surface.** |
| 10 | Responsive: tablet and mobile passes at 834 and 390. | Medium |
| 11 | Accessibility pass: landmarks, table semantics, live regions, keyboard, greyscale review. | Medium |
| 12 | Rewrite `verify_browser.py` against the new interface. | Medium |
| 13 | Full gate, desktop + mobile screenshots, hand over for review. | — |

---

## 3. Data integrity during the migration

- `validate.py` is **not touched**. No rule relaxed, no enum widened, no check
  removed. The dataset that passes today passes unchanged.
- `data/` is **not edited** by this redesign. Every schema addition in doc 07 is
  a proposal with a migration path, not a change made here.
- The site stays functional at every step: step 1 is a no-op refactor, and every
  step after it ends with a green gate.
- Rendering rules that protect the data are asserted, not assumed: no bare
  numbers, no blended tiers, no aggregate in a single-stream slot, no invented
  values for unrecorded fields.

---

## 4. Verification plan

### 4.1 The gate is unchanged

`python3 directory/check.sh` → `validate.py` → `check_links.py` → `build.py` →
browser suite against a local server. Every stage must pass. `build.py` still
runs `validate.py` itself and refuses to write on failure.

### 4.2 The browser suite is rewritten, not weakened

`verify_browser.py` drives ids belonging to the architecture being replaced.
Every existing check is either kept as-is, or mapped to a stronger equivalent.
**No check is dropped without a replacement.** The mapping:

| Existing check | Disposition |
|---|---|
| HTTP 200, page title, all links http(s), dataset counts match validator | **Kept unchanged** |
| No page errors, no console errors | **Kept unchanged** |
| No horizontal overflow at 1440 and 390 | **Kept and widened** — asserted at 390, 834, 1440, 1920, and at 400% zoom on 1280 |
| HTML entities never leak (`&rarr;`) | **Kept and widened** — scans all rendered text on every route for `&[a-z]+;` |
| Cards start collapsed / click expands / `aria-expanded` / second click collapses | → rows start collapsed, expand in place, `aria-expanded` flips, collapse restores |
| Enter key expands (keyboard) | → Enter **and** Space on the row control; Escape collapses and returns focus |
| Expand all / relabels / collapse all | → per-shelf expand-all, plus global |
| Copy button exists / `data-copy` matches visible / feedback / clipboard | **Kept**, extended to per-step copy on `cmd` steps and asserted absent on `do` steps |
| Search narrows, every hit contains the term, multi-term AND, no-match empty state | **Kept**, extended to the new searchable fields (commands, notes, methods) |
| Every filter option valid against the dataset | **Kept**, extended across all ~18 facets |
| Engine AND quant combine | → any two facets combine, sampled across the facet set |
| `tier=box` yields exactly 4 | **Kept** |
| Reset clears search / restores every control | → `Clear all` clears every chip, the search box, and the URL query |
| Four sort modes | → all nine, each asserted against a re-implementation of its key |
| `sort=evidence` puts box first | **Kept**, restated against the four-dimension strip |
| `sort=speed` starts with the fastest single-stream | **Kept**, plus: the disclosure band is present and not dismissible |
| Single-stream beats aggregate on the worst offender | **Kept** — the 489-vs-28.7 case is asserted by id |
| Aggregate states concurrency and per-stream at load | **Kept** |
| 4090 card headlines its mean, not its peak | **Kept** — asserted by id |
| Cards with measurements show numbers, others do not | **Kept** |
| Provenance pill matches the data tier | → the evidence strip's four levels recomputed from the raw dataset and compared cell by cell, for all 65 |
| Every card exposes its slug note | **Kept** |
| Four completeness states render from data | → the `Ready` column, asserted against the derivation |
| Fit is neutral before a machine is chosen | **Strengthened** — asserted that **no** fit verdict exists anywhere on `#/` regardless of a saved profile |
| SGLang not advertised for unsupported Apple Silicon | **Kept** — as a My Hardware evidence-line assertion |
| Machine profiles produce distinct recommendations | **Replaced** — the recommendation feature is removed by design; replaced by: distinct profiles produce distinct group memberships |
| Multi-GPU recommendation uses the 43.2 mean | **Replaced** by the mean-not-peak assertion above, which is the underlying rule |
| Newcomer question is the headline / orientation open / performance guide sections / device notes | **Replaced** — these assert the beginner-first structure this brief reverses. Replaced by the first-viewport contract assertions below. |
| Advanced filters visible on desktop | **Kept and inverted** — common filters must be visible **and not inside a closed disclosure** at ≥720; Advanced may be closed |
| Vanity counts in the footer | **Replaced** — counts must be absent from `#/` entirely and present on `#/methodology` |

### 4.3 New checks

**Structure**
- All ten routes resolve; an unknown route renders the 404 view, not a blank page.
- Back and forward restore the previous route and its filter state.
- `#/` is the default for a bare URL and for an empty hash.
- The path shim rewrites `/hardware` to `#/hardware`.

**First-viewport contract at 1440×1000** — identity, three tabs, one sentence,
search, the seven common filters, the family rail, the first shelf header, and
≥3 recipe rows are all within the first 1000px; and no hero, questionnaire,
counts strip or orientation essay is.

**Directory**
- All 22 shelves render; every one of the 65 recipes is reachable with no
  filters and no profile.
- Shelf headers carry all eleven required fields, with `not recorded` where the
  data is null — asserted specifically for the six models with null
  `params_active_b` and the one with a null context.
- Row column count and alignment at each breakpoint.
- The 8 capability-conflict setups show the conflict **collapsed**.
- The 32 measurement-free setups render `— no speed data`, are not dimmed, and
  are not sorted out of existence.

**Trust**
- Each of the four dimensions recomputed independently in the test and compared
  against the rendered strip for all 65 recipes.
- The strip's accessible name is a full sentence naming all four.
- No route renders a blended tier.

**Compare**
- The rail is **absent** at zero selections (not hidden — no node).
- Appears at one, with a disabled action and a stated reason.
- Caps at four with an explained refusal.
- Selection persists across all three tabs.
- The workspace renders all seven sections.
- Incomparability banner fires for a deliberately mismatched pair and is
  suppressed for a matched pair.
- **No winner marker exists anywhere** — asserted by scanning for best/winner
  highlighting classes and for a highlighted maximum in the performance section.

**My Hardware**
- No unconditional "Fits" string exists on the route, under any profile.
- Every result states model memory, runtime buffers, KV allowance, assumed
  context, assumed concurrency, safety reserve, offload, remaining, and evidence
  provenance.
- The 21 families without `kv_bytes_per_token` render the KV line as
  not-derivable, never as a number.
- All five groups render including empty ones.
- Detection degrades: with WebGPU and WebGL stubbed out, the panel reports what
  it could not detect and the tab stays usable.
- `localStorage` throwing does not break the tab.
- **No network request is made after load** — asserted by route interception
  across every tab.

**Accessibility**
- Exactly one `<h1>` per route; no skipped heading levels.
- Landmarks present and unique.
- Full keyboard traversal of a shelf: rail → filters → row → compare → expand →
  panel links → next row, with a visible focus ring at every stop.
- `aria-live` result count updates after filtering.
- Every interactive element has a non-empty accessible name.
- Reduced motion honoured (asserted with the media feature emulated).
- Contrast sampled programmatically on every token pair in both themes.

**Both themes** — every structural check runs under `prefers-color-scheme:
light` and `dark`.

### 4.4 Definition of done

```bash
bash directory/tools/install_verify_env.sh   # once
python3 directory/check.sh                   # validate → links → build → browser
```

Zero validation errors, every source URL resolving, the browser suite green at
390 / 834 / 1440 / 1920 in both themes, then screenshots for review.

**Acceptance test, in plain English.** Hand the page to an operator with one
sentence: *"Find every way to run Qwen3.8-27B, and tell me which of them you'd
trust."* They should reach the shelf, read fifteen column-aligned rows, compare
three of them, and be able to say which evidence is owner-measured and which is
one person's README — **without selecting a machine, dismissing anything, or
being shown a ranking.**

**No publish without explicit go-ahead.** `ifhost publish` replaces the live
site's entire content; that is the owner's call.
