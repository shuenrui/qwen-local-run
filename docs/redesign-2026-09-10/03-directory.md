# 03 — Tab 1: Directory

> **Superseded on 2026-09-12 for the default route.** This advanced directory
> now lives at `#/recipes`. The model-first homepage is specified in
> [`../MODEL-FIRST-2026-09-12.md`](../MODEL-FIRST-2026-09-12.md).

Route `#/`. The homepage, the default, and the only view that is never gated by
anything. Every one of the 65 recipes is reachable here without selecting a
machine, answering a question, or dismissing an overlay.

---

## 1. Desktop layout — 1440 × 1000

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ QWEN LOCAL-RUN   [Directory] My Hardware  Compare      ⌕ …   methodology  ◐     │ 44   sticky
│ Every open-source recipe for running Qwen on hardware you own — 65 recipes,     │ 26
│ 22 families, each number carrying its source.                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [search across model, checkpoint, builder, command, engine, notes    ] ⌕        │ 40   sticky
│ Gen ▾ │ Arch ▾ │ Engine ▾ │ Quant ▾ │ Hardware ▾ │ Evidence ▾ │ Ready ▾ │       │ 36   sticky
│ ⚙ Advanced (0)  │  Sort: Recently updated ▾  │  65 of 65                        │
├──────────────┬──────────────────────────────────────────────────────────────────┤
│ FAMILIES     │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ All (22)     │ Qwen3.8-Flash-Next            8 recipes · 0 measured · 2026-09-05 │
│              │ GEN 3.8  MoE  180B total / 6B active  262K → 1M  text·image·video │
│ GENERATION   │ LICENSE varies by build; Mia's scripts are AGPL      [card ↗]     │
│  3.8 (2)     │ ──────────────────────────────────────────────────────────────── │
│  3.6 (2)     │  ARTIFACT      QUANT   ENGINE   TESTED ON  READY  DECODE  EVID UP │
│  3.5 (7)     │ ☐ azampatti…   NVFP4   SGLang   DGX Spark  ◔ rec   43.0   ●◑◐○ 09 │
│  3.0 (11)    │   azampatti     safet.  stock    needs110  moder.  chat·fo   -05  │
│              │ ☐ blazux…      MIXED   vLLM ⑂   DGX Spark  ● run   32.5   ●◑◐○ 09 │
│ ARCHITECTURE │ …                                                                │
│  Dense (10)  │                                                                  │
│  MoE (12)    │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Vision (6)  │ Qwen3.8-27B                  15 recipes · 4 measured · 2026-09-05 │
│              │ …                                                                │
│ FAMILIES     │                                                                  │
│ ▸ Qwen3.8-…  │                                                                  │
└──────────────┴──────────────────────────────────────────────────────────────────┘
```

**First-viewport contract.** At 1440×1000 the following are above the fold and
nothing else is: product identity, the three-tab navigation, one sentence, the
search field, the seven common filters, the family rail, the first shelf header
in full, and the first three to four recipe rows. Total chrome above the first
shelf is 146px. There is no hero, no questionnaire, no counts strip, and no
orientation essay.

### The rail

208px, sticky, its own scroll. Four groups, in this order:

1. **All model families** — the reset.
2. **Generation** — 3.8, 3.6, 3.5, 3.0, each with its family count.
3. **Architecture** — Dense, MoE, Vision & multimodal.
4. **Families** — all 22, ordered newest generation first then largest, each
   with its recipe count.

Generation and architecture entries are *filters* (they narrow the shelf list).
Family entries are *jump targets* (they scroll to that shelf). The two
behaviours are visually distinct: filters take a `▣` state when active, jump
targets do not. Scroll-spy marks the family currently in view.

---

## 2. The model-family shelf

One shelf per model family, in the same order as the rail. A shelf renders
whenever at least one of its recipes survives the current filters; the count in
its header then reads `4 of 15 recipes shown`.

### Header fields

All eleven fields the brief requires, laid out as a spec strip — label above
value, on the row grid:

| Field | Source | When absent |
|---|---|---|
| Model name | `models[].name` | — |
| Generation | `models[].generation` | — |
| Dense or MoE | `architecture.kind` | — |
| Total parameters | `architecture.params_total_b` | `not recorded` |
| Active parameters | `architecture.params_active_b` | Dense → `all — dense`; MoE → `not recorded` |
| Native context | `context.native` | `unstated by the publisher` |
| Max advertised context | `context.max` | `not stated` |
| Modalities | `modalities[]` | — |
| Weight license | `models[].license` | — |
| Recipe count | derived | — |
| Measured-recipe count | count of `provenance_tier == box\|forum\|vendor` with ≥1 speed measurement | `0 measured` |
| Most recent update | max `setups[].updated` in the family | — |

Two additions the data supports and the header earns:

- **Known regressions** — `models[].known_regressions[]`. Qwen3.8-27B carries
  three. Rendered as a `▲ 3 known regressions` disclosure in the header, because
  a family-level quality regression belongs to the family, not to any recipe.
- **Model card link** — `models[].url`, plus a link to `#/models/<id>`.

`architecture.params_active_b` is null on six dense models. For a dense model
every parameter is active per token by definition, so the header says
`all — dense` rather than inventing a figure; for a MoE with a null it says
`not recorded`.

---

## 3. The recipe row

A ten-column CSS grid, two text lines, column-aligned across the entire shelf.

```
grid-template-columns:
  26px            /* select   */
  minmax(0,2.2fr) /* artifact */
  0.9fr           /* quant    */
  1.1fr           /* engine   */
  1fr             /* tested on*/
  0.85fr          /* ready    */
  0.9fr           /* decode   */
  0.8fr           /* evidence */
  0.6fr           /* updated  */
  26px;           /* expand   */
```

| Col | Line 1 | Line 2 (`--ink-3`, 12.5px) |
|---|---|---|
| **select** | `☐` / `▣` compare control | — |
| **Artifact** | checkpoint tail, mono, 14px | publisher · `quant_detail` truncated to one line |
| **Quant** | quant label | format · artifact size |
| **Engine** | engine name + `⑂` if `requires_fork` | spec-decode path, or `stock` |
| **Tested on** | first hardware class | `+n more`, or the second class |
| **Ready** | `● runnable` / `◔ recipe` / `○ lead` | derived setup complexity |
| **Decode** | value + unit, tabular, 19px | metric + condition + provenance |
| **Evidence** | the four-cell strip | — |
| **Updated** | `YYYY-MM` | freshness word |
| **expand** | `▸` / `▾` | — |

Setup complexity is derived and labelled as derived — the dataset has no
complexity field. The derivation, stated on `#/methodology`:

```
base   ollama 1 · lm-studio 1 · llama-cpp 2 · mlx-lm 2 · vllm 3 · sglang 3 · custom-fork 4
  +1   engine.requires_fork
  +1   run.steps has more than 4 entries
  +1   engine.draft_model is set
  →    1–2 one command · 3–4 moderate setup · 5+ involved build
```

### The Decode column contract

This is where the previous review's P0-1 lives, and it is now a column rule
rather than a card rule.

1. Pick the representative value from **single-stream metrics only**:
   `decode_chat` → `decode_code` → `decode_essay` → `decode_per_stream`, each
   required to have `concurrency == null || concurrency <= 1`.
2. Prefer a non-`peak` `stat` when both exist.
3. **Never render a bare number.** Line 2 always carries the metric, the
   concurrency condition and the provenance tier:
   `chat · 1 stream · forum`.
4. If the only speed evidence is aggregate, the cell shows the aggregate with
   `▲ agg only` and states its concurrency: `266.8 · agg @48 · forum`. It is
   never promoted into the single-stream slot.
5. Where both exist, the aggregate and the per-stream-at-load figure appear in
   the expanded panel, together:
   `266.8 tok/s across 48 streams — 5.6 tok/s each at that load.`
6. No measurements at all → `— no speed data`, `--ink-4`.

### Row states

| State | Rendering |
|---|---|
| **Typical** | All ten columns populated. |
| **Minimum data** (`untested`, 32 of 65) | Decode `— no speed data`; Ready `○ lead`; Evidence `◑ ○ ○ ○`; row is not dimmed — it is a legitimate sourced lane, and dimming it would hide a third of the directory. |
| **Maximum data** (`box`, 4 of 65) | Decode carries a `box` label; Evidence `● ● ● ◑`; a `+3 more measurements` affordance in the expanded panel. |
| **Missing field** | `not recorded`, `--ink-4`, italic. Never blank, never `0`, never `—` alone. |
| **Warning** | `▲` before the affected cell; caveat count in the expand cell: `▸ 5 caveats`. |
| **Failure** | `✕` mark, `--bad` leading bar, and the failure sentence promoted into line 2 of the Artifact column so it is visible **collapsed**. `status: "broken"` renders here. |
| **Capability disabled by runtime** | Artifact line 2 gains `✕ vision off (runtime)`. The 8 setups where a vision-capable model runs through a non-vision runtime are visible without expanding. |
| **Selected** | `▣`, `--sel` leading bar, `--sel-bg` tint, present in the rail. |
| **Expanded** | `▾`, detail panel below spanning all columns. |

### Expanded detail

Opens in place, 120ms, keeps the row visible above it. Content order matches the
recipe page exactly so nothing is learned twice:

plain-language summary (`slug_note`) · complete commands (`run.command`, copy
button) · ordered steps (`cmd` monospace + copy, `do` prose, never mixed) ·
requirements · runtime configuration (`engine.config`, flags, image,
draft model, spec-decode) · measurements table · compatibility observations
(which hardware classes, with `measured_by_us`) · enabled and disabled
capabilities · known failures · caveats · sources · revision history.

Footer of the panel: `Open recipe page →` (`#/recipes/<id>`), `Raw JSON`,
`Add to compare`.

---

## 4. Search and filtering

### Search

One field, matching across model name, family, checkpoint, publisher and builder
name, engine name and config string, quant and `quant_detail`, run command and
step text, `slug_note`, caveats, and measurement method and note strings.
Multi-term: every whitespace-separated term must match somewhere (AND).
Debounced 120ms. Serialized to the URL as `?q=`.

### Common filters — always visible, never collapsed

Generation · Architecture · Engine · Quant · Hardware class · Evidence · Ready.

### Advanced Filters — a panel, opened by `⚙ Advanced (n)`

Parameter range (dual slider over `params_total_b`) · Modality and capability
(text, vision, audio, tools, thinking — each as a tri-state: any / recipe
supports / recipe disables) · Artifact format · Operating system *(implied by
tested hardware class — labelled as implied, because the dataset has no OS
field)* · Stock engine vs custom fork · Speculative-decoding path · Runnable
recipe completeness · Performance measurement availability · Measurement
provenance tier · Maintainer or publisher · Maintenance freshness · Known
success / known failure · Context ceiling.

The panel opens inline beneath the filter bar. It is a disclosure, not a modal,
not a drawer, and not an overlay — the shelves stay visible and re-filter live
beneath it.

**Hardware filtering here means "tested on this hardware class"** and says so in
the control's own label: `Tested on ▾`. It is not a fit calculation and never
produces a verdict. The panel carries one line to that effect with a link to
`#/hardware`.

### Active filters

Every active filter renders as a removable chip in a strip beneath the filter
bar: `Engine: SGLang ✕`. A range filter shows its bounds. `Clear all` appears
once two or more are active. State is serialized to the URL, so a filtered view
is shareable, and restored on load.

### Sorting

| Mode | Key |
|---|---|
| Recently updated *(default)* | `updated` desc |
| Model generation | generation desc, then params desc |
| Model size | `params_total_b` desc |
| Easiest to run | derived complexity asc, then has-command |
| Most complete | steps + command + requirements + capability completeness |
| Strongest evidence | the four-dimension strip, lexicographic R→C→P→A |
| Most measured | count of measurements desc |
| Decode speed | representative single-stream value desc |
| Smallest footprint | `requirements.memory_gb` asc |

**The speed-sort disclosure is mandatory and not dismissible.** Selecting
*Decode speed* pins a band above the first shelf:

> ▲ These numbers were produced on different hardware, at different context
> lengths, with different workloads and concurrency, by different people, using
> different clocks. 4 are owner-measured, 28 are community-reported, 33 have no
> measurement and are sorted last. This ordering is a discovery aid. It is not a
> leaderboard.

Sorting never reorders shelves relative to each other — it orders rows *within*
each shelf. The catalogue's structure is the model family; sorting does not
dissolve it. A `Flatten to one ranked list` toggle exists for the operator who
genuinely wants a cross-family ordering, and it carries the same disclosure.

---

## 5. Mobile — 390 × 844

```
┌───────────────────────────────┐
│ QWEN LOCAL-RUN          ⌕  ◐  │  sticky
│ Directory │ Hardware │ Compare│  sticky, 3-up
├───────────────────────────────┤
│ [search                    ⌕] │
│ [ Families ▾ ] [ Filters (2) ]│
├───────────────────────────────┤
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Qwen3.8-27B                   │
│ 15 recipes · 4 measured       │
│ Dense · 27.8B · 262K → 1M     │
│ ▸ full model spec             │
│ ───────────────────────────── │
│ ☐ RadixArk/…-NVFP4-BF16-LMHead│
│   SGLang ⑂ · NVFP4 · 23.7 GB  │
│   DGX Spark · needs 32 GB     │
│   56.6 tok/s  chat·1 stream·box│
│   ● runnable   ●●●◑         ▸ │
│ ───────────────────────────── │
│ ☐ …                           │
├───────────────────────────────┤
│ ▣ 2 selected · Compare      ✕ │  fixed rail
└───────────────────────────────┘
```

- Shelves stay vertically browsable; the family rail becomes a `Families ▾`
  drawer listing the same four groups.
- The shelf header keeps name, counts, architecture, params and context; the
  remaining spec fields go behind `▸ full model spec`.
- **The row becomes a structured summary, not a squeezed table.** Four stacked
  lines — identity, runtime, hardware and requirement, measurement — each
  keeping its label. No horizontal scroll, no compressed desktop grid.
- Technical fields (flags, config string, sources, revision history) live only
  in the expanded panel.
- The compare rail collapses to count + action + clear.
- Filters open as a full-height sheet with the common filters first and Advanced
  below, and an explicit `Apply` that closes it.

## 6. Tablet — 834 × 1112

- Rail → `Families ▾` selector in the filter bar.
- Advanced Filters becomes an expandable panel (same disclosure, wider).
- Row drops to six columns: select, artifact, engine, ready, decode, expand.
  Quant, tested-on, evidence and updated fold into the artifact and decode
  cells' second lines. Nothing is lost — everything remains in the expanded
  panel.
