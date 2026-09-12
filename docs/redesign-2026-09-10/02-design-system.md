# 02 — Design system

The product is a **well-maintained technical index**. The nearest relatives are
a package archive, a browser compatibility table, and a lab's measurement log —
not a SaaS dashboard and not a landing page.

Three rules drive every decision below.

1. **Hierarchy comes from typography, alignment and spacing. Containers are the
   last resort.** A border is admitted only when alignment cannot do the job.
2. **Colour is a signal, not a surface.** The page is neutral. Hue appears only
   for evidence, compatibility, warning, failure and selection.
3. **Density is the point.** An operator scanning fifteen ways to run
   Qwen3.8-27B needs the fields column-aligned, not spaced apart apologetically.

Explicitly not this: gradients, glass, glow, ambient blur, decorative
illustration, nested cards, bento grids, a terminal costume, scroll animation,
or a leaderboard.

---

## 1. Colour

A neutral foundation with one accent and four signal hues. Defined as tokens on
bare `:root`, redefined under `:root:not([data-theme="light"])` in a dark media
query and again under `:root[data-theme="dark"]`, so both the system preference
and an explicit toggle resolve correctly.

### Neutrals — light

| Token | Value | Use |
|---|---|---|
| `--paper` | `#fbfaf8` | Page ground. Very slightly warm; pure white reads as a document, not an index. |
| `--surface` | `#ffffff` | Expanded panels, the compare rail, sticky bars. |
| `--surface-sunk` | `#f4f3f0` | Table zebra on hover, code blocks, the shelf spec strip. |
| `--ink` | `#15171a` | Primary text. |
| `--ink-2` | `#4a4f57` | Secondary values, prose. |
| `--ink-3` | `#767c85` | Labels, units, metadata. |
| `--ink-4` | `#9aa0a8` | Placeholder, disabled, "not recorded". |
| `--rule` | `#e6e4e0` | Hairlines between rows. |
| `--rule-2` | `#cfccc6` | Shelf separators, table heads. |
| `--rule-3` | `#a8a49d` | The heavy rule above a shelf header. |

### Neutrals — dark

`--paper #121316` · `--surface #191b1f` · `--surface-sunk #212429` ·
`--ink #eceef1` · `--ink-2 #b3b9c2` · `--ink-3 #868d97` · `--ink-4 #646b75` ·
`--rule #2a2e34` · `--rule-2 #3a3f47` · `--rule-3 #545a63`.

### Signals

Each carries a `-fg`, a `-bg` and a `-line` variant. Every one is paired with a
glyph or a word so status never depends on colour alone.

| Token | Light `fg` | Dark `fg` | Meaning | Glyph |
|---|---|---|---|---|
| `--sel` | `#1f4fd8` | `#7d9cff` | User selection: compared, focused, active filter | `▣` |
| `--ok` | `#1a6f4a` | `#5fc79a` | Verified, exact-device evidence, clean install | `●` |
| `--est` | `#7a5a12` | `#e0b45c` | Estimated, similar-device, single report | `◐` |
| `--warn` | `#8a4b12` | `#f0a068` | Caveat, incomplete, stale, quality regression | `▲` |
| `--bad` | `#a32820` | `#ff8b80` | Known failure, unsupported, disabled capability | `✕` |
| `--none` | `--ink-4` | `--ink-4` | Unknown, not recorded, no evidence | `○` |

Contrast: every `-fg` on its `-bg` and on `--paper` clears 4.5:1 for body text
and 3:1 for the ≥18.66px bold labels. `--ink-3` on `--paper` is 4.6:1;
`--ink-4` is used only for non-essential metadata and for text that is
duplicated by a glyph and a word.

### Where colour is forbidden

Model names, checkpoints, engine names, quant labels, publisher names, sizes,
context lengths, licenses, dates. All of these are ink. If everything technical
is coloured, nothing signals.

---

## 2. Typography

No web fonts. The output is one self-contained file that must work from
`file://` and make no network requests after load; a font CDN would break both.
The system stack is also the honest choice for an index — it is what every other
reference document on the reader's machine uses.

```css
--font-ui:   ui-sans-serif, -apple-system, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;
--font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo,
             "Cascadia Mono", Consolas, monospace;
```

**Monospace is reserved.** It marks commands, checkpoint ids, flags, file paths,
engine config strings, measurement values, sizes, and context lengths — the
things a reader might copy or compare digit by digit. It is never the page's
identity, never used for prose, headings, labels or navigation.

All numeric columns carry `font-variant-numeric: tabular-nums`, so decode speeds
and memory figures align on the decimal point down a shelf.

### Scale

| Role | Size / line-height | Weight | Tracking |
|---|---|---|---|
| Page title (`h1`) | 20 / 26 | 620 | -0.01em |
| Shelf title (`h2`) | 26 / 30 | 640 | -0.015em |
| Section head (`h3`) | 15 / 20 | 620 | 0 |
| Row primary | 14 / 19 | 560 | 0 |
| Body / prose | 14 / 21 | 400 | 0 |
| Row secondary | 12.5 / 17 | 400 | 0 |
| Field label | 10.5 / 14 | 620 | **0.07em, uppercase** | 
| Mono value | 12.5 / 18 | 450 | 0 |
| Big measurement | 19 / 22 | 600, tabular | -0.01em |

The uppercase 10.5px label with wide tracking is the system's connective
tissue: it names every field in a shelf header, a spec strip, a compatibility
breakdown and a compare row group. It is always `--ink-3`, never coloured, and
never larger.

### Prose measure

Any paragraph is capped at `68ch`. Summaries, caveats and method strings are the
only long-form text in the product and they must not run the full width of a
1440px shelf.

---

## 3. Space and rhythm

A 4px base. Used values: 2, 4, 6, 8, 12, 16, 20, 24, 32, 48.

Vertical rhythm is carried by rules, not by gaps:

- `--rule` hairline between recipe rows.
- `--rule-2`, 1px, under a shelf's column header.
- `--rule-3`, 2px, **above** a shelf header — the heaviest line in the product,
  and the thing that makes the page read as a catalogue with sections rather
  than a scroll of cards.

Row height targets 44px on desktop (two text lines, 8px padding), which is also
the minimum touch target, so mobile inherits an accessible size for free.

Max content width 1440px, with the family rail at 208px outside it on very wide
viewports.

---

## 4. The four component families

### 4.1 The model-family shelf — primary motif

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ← rule-3, 2px
Qwen3.8-27B                                  15 recipes · 4 measured · upd 2026-09-05
GEN 3.8   DENSE   PARAMS 27.8B total / 27.8B active   CONTEXT 262K native → 1M max
MODALITIES text · image · video              LICENSE Apache-2.0        [model card ↗]
───────────────────────────────────────────────────────────────────── ← rule-2, 1px
  ARTIFACT              QUANT      ENGINE       TESTED ON    READY   DECODE   EVIDENCE  UPD
```

The header is a fielded spec strip, not chips. Label above value, aligned to the
same grid as the rows beneath it. It communicates all eleven fields the brief
requires; anything the data does not record renders as `not recorded` in
`--ink-4`, never blank and never guessed.

### 4.2 The recipe row — the scanning unit

A CSS grid, two text lines, aligned across the whole shelf. Never a card. Never
bordered on the sides. The only decoration is the hairline beneath it.

Full column contract, states and responsive collapse: **doc 03 §3**.

### 4.3 The detail panel

What a row expands into, and what a `#/recipes/<id>` page is built from. Full
width, `--surface`, one 3px `--sel` bar on the leading edge to tie it to the row
it belongs to. Inside it there are **no cards** — sections are separated by
labels and hairlines only.

### 4.4 The compare rail — signature interaction

Fixed to the bottom edge, `--surface`, one `--rule-2` top border, a
`0 -1px 0` line rather than a shadow. Appears only when a selection exists;
absent, not empty, at zero. Full behaviour: **doc 05 §1**.

---

## 5. Encoding evidence

The single most important visual invention in the system, because the brief
requires four independent confidence dimensions where the product has one badge.

**A four-cell strip.** Fixed order, always the same order, so position carries
meaning and the strip is readable at a glance down a column:

```
  R C P A          recipe · compatibility · performance · capability
  ● ● ◐ ○
```

- Cell glyph encodes level: `●` strongest, `◑` mid, `◐` weak, `○` unknown,
  `✕` unsupported.
- Cell colour reinforces: `--ok`, `--est`, `--none`, `--bad`.
- The strip's accessible name is the full sentence, e.g. *"Recipe: complete
  community recipe. Compatibility: exact-device evidence. Performance: single
  community report. Capability: unknown."*
- Hover or focus opens a popover naming each dimension, its level, and the
  source that sets it.

Levels per dimension are enumerated in **doc 06 §1**. The rule the strip
enforces visually: a recipe may be `● ● ○ ○` — strong install evidence, no
performance evidence at all — and the interface must make that legible rather
than averaging it into "medium".

Measurement provenance keeps its own separate mark wherever an individual number
appears: `box` / `forum` / `vendor` as a small uppercase label beside the value,
never merged into the strip and never blended with another tier.

---

## 6. Motion

Almost none, and all of it functional.

| Interaction | Treatment |
|---|---|
| Row expand / collapse | height 120ms `ease-out`; content does not fade |
| Compare rail enter | translateY 8px → 0, 140ms |
| Filter chip removal | none — immediate |
| Route change | none — immediate |
| Popover | opacity 90ms |

Under `prefers-reduced-motion: reduce`, every duration collapses to `0.01ms` and
transforms are dropped. Nothing in the product conveys information through
motion, so this removes decoration only.

---

## 7. Focus and interaction states

- Focus ring: `2px solid var(--sel)` with a `2px` offset, on a
  `:focus-visible` basis, on every interactive element including rows,
  shelf headers, filter chips and compare cells. Never suppressed.
- A selected-for-compare row: `--sel` 3px leading bar, `--sel-bg` tint, and the
  `▣` glyph in the select cell. Three signals — bar, tint, glyph — so selection
  survives greyscale.
- Hover on a row: `--surface-sunk`. Nothing moves, nothing scales.
- The expanded row keeps its `--sel`-neutral leading bar in `--rule-3` so
  expansion and selection are visually distinct.

---

## 8. What the system must keep distinguishable

The brief names six planes; each gets a fixed treatment, applied everywhere:

| Plane | Treatment |
|---|---|
| Model-level information | Shelf header and model pages only. Larger type, spec-strip labels, never inside a row. |
| Recipe-level information | Row and detail panel. 14px, mono for identifiers. |
| Measurement evidence | Tabular mono, always with unit, condition and provenance label adjacent. Never a bare number. |
| Compatibility estimate | Only inside My Hardware. Always prefixed by a hedge word and followed by its assumptions. `--est` or `--ok`, never unqualified green. |
| Warning / failure | `--warn` / `--bad`, `▲` / `✕`, and a word. Always visible in collapsed state as a count, never hidden behind expansion. |
| User-selected comparison | `--sel` bar + tint + `▣`, plus presence in the rail. |
