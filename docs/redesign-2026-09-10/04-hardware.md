# 04 — Tab 2: My Hardware

Route `#/hardware`. **Every** personalized compatibility behaviour in the
product lives here and nowhere else. Nothing on this tab narrows the Directory
unless the user explicitly asks it to.

---

## 1. Layout — desktop

Two columns, 380px profile pane on the left, results on the right. The profile
pane is sticky; changing a field re-renders the results immediately.

```
┌──────────────────────────────┬──────────────────────────────────────────────┐
│ YOUR MACHINE                 │ 65 recipes checked against "M4 Max 64 GB"    │
│ ┌──────────────────────────┐ │ assuming 8K context · 1 conversation · 6 GB  │
│ │ Detect  │ Known device   │ │ reserve                    [change assumptions]│
│ │ Custom  │ Import         │ │                                              │
│ └──────────────────────────┘ │ ● VERIFIED ON THIS EXACT MACHINE          0  │
│                              │   No recipe records a measurement on this    │
│ OS          macOS 15.3       │   exact configuration.                       │
│ CPU/CHIP    Apple M4 Max     │                                              │
│ GPU         integrated 40-c  │ ● VERIFIED ON SIMILAR HARDWARE            4  │
│ GPU COUNT   1                │   ┌────────────────────────────────────────┐ │
│ RAM         64 GB            │   │ Qwen3.8-27B MLX 4-bit — mlx-lm         │ │
│ VRAM        unified          │   │ Tested on: Apple Silicon 32–64 GB class│ │
│ MEMORY      unified          │   │ Recorded resident requirement 18 GB    │ │
│ FREE DISK   410 GB           │   │ ≈ 40 GB left of your 64 GB             │ │
│ DRIVER      —                │   │ ▸ how this was worked out              │ │
│ RUNTIME     mlx-lm 0.28      │   └────────────────────────────────────────┘ │
│ POWER LIMIT —                │                                              │
│                              │ ◐ ESTIMATED TO FIT                       11  │
│ [Save profile] [Export]      │ ○ UNCERTAIN                              38  │
│ Saved: M4 Max · RTX 4090     │ ✕ WILL NOT FIT AS RECORDED               12  │
└──────────────────────────────┴──────────────────────────────────────────────┘
```

Mobile stacks the panes: profile first, collapsed to a summary line once set
(`M4 Max · 64 GB · macOS  ✎`), results below.

---

## 2. The four ways in

### 2.1 Detect

A browser-local read. **No network request is made, and nothing is transmitted.**
The page makes no outbound requests after load at all — the dataset is inlined —
so this is verifiable rather than a promise.

What it can actually read, and what each reading is worth:

| Field | API | Honest limit |
|---|---|---|
| Platform / OS | `navigator.userAgentData` → `navigator.platform` | Family only. No version on most browsers. |
| CPU threads | `navigator.hardwareConcurrency` | Logical cores. Not the chip name. |
| RAM | `navigator.deviceMemory` | **Chromium only, rounded down to a power of two, and capped at 8.** A 64 GB Mac reports 8. Effectively unusable as a memory figure and is presented as such. |
| GPU | `navigator.gpu.requestAdapter()` → `adapter.info` | Vendor and architecture where the browser exposes them; often masked. |
| GPU (fallback) | WebGL `WEBGL_debug_renderer_info` | A renderer string such as `Apple M4 Max`. Increasingly masked for fingerprinting reasons. |
| VRAM, free disk, driver version, runtime version, power limit | — | **No browser API exposes these.** They are always manual. |

The detect panel therefore renders a per-field result, not a filled form:

```
DETECTED           Platform  macOS          from navigator.userAgentData
                   GPU       Apple M4 Max   from WebGL renderer string
                   Threads   16             from navigator.hardwareConcurrency
NOT DETECTABLE     RAM       navigator.deviceMemory caps at 8 GB and is
                             Chromium-only — enter it yourself
                   VRAM · free disk · driver · runtime · power limit
                             no browser API exposes these
```

Every detected field lands in the form marked `detected`, and every one is
editable. A field the user edits is marked `entered`. The distinction is carried
into the compatibility result, because a verdict computed from a guessed memory
figure is worth less than one computed from a stated figure.

### 2.2 Known device

The six hardware classes in `data/hardware/`, each shown with what the dataset
actually records — memory, usable memory, bandwidth (or its range), architecture
string, and crucially **`measured_by_us`**. Two of the six are explicitly
*classes*, not SKUs (`gpu-24gb`, `mac-128gb`), and their entries say so; picking
one produces similar-hardware evidence at best, never exact-device.

### 2.3 Custom machine

The full field set the brief requires. Every field is optional; each missing
field degrades the result rather than blocking it, and the result says which
field it lacked.

OS · exact CPU or Apple chip · exact GPU · GPU count · RAM · VRAM ·
unified or separate memory · free storage · driver version · runtime version ·
optional power limit.

### 2.4 Import / export / save

Profiles are JSON, saved to `localStorage` under `qlr.profiles.v2` inside
`try/catch` (private windows and blocked site data must not break the tab).
Export writes a `.json` the user can keep or share; import accepts the same.
Several profiles can be saved and switched between, because operators have more
than one machine.

**The privacy statement is on the tab, not in a footer:** the dataset is inlined
in the page, the page makes no requests after load, detection reads only the
APIs listed above, and profiles are stored in this browser only and are never
sent anywhere.

---

## 3. Assumptions — explicit, adjustable, and part of every verdict

A compatibility result is meaningless without them, so they are stated in the
results header and editable inline:

| Assumption | Default | Why |
|---|---|---|
| Context length | 8,192 | The brief's example. Recipes are checked at the context you will actually use, not at their maximum. |
| Concurrency | 1 | One active conversation. Anything else changes the answer by an order of magnitude. |
| Safety reserve | 8 GB desktop OS / 6 GB macOS / 2 GB headless | An assumption about the *machine*, not a claim about a recipe. Adjustable, and always shown as a line item. |

Changing an assumption re-groups the results and says so:
`Context 8K → 32K moved 3 recipes from Estimated to fit into Uncertain.`

---

## 4. The five result groups

Ordered strongest evidence first. Group counts are always shown, including
zeroes — an empty "Verified on this exact machine" group is informative.

| Group | Entry condition |
|---|---|
| **● Verified on this exact machine** | A measurement exists whose hardware class matches the profile **and** that class is a single SKU with `measured_by_us: true` **and** the profile's chip matches it. In practice today: only a DGX Spark profile against the 4 `box` setups. |
| **● Verified on similar hardware** | A measurement or a recorded requirement exists on a hardware class the profile belongs to, where the class is a range rather than a SKU. |
| **◐ Estimated to fit** | No evidence on this hardware, but the recipe's *recorded* resident requirement fits within the profile's memory minus the reserve. |
| **○ Uncertain** | The recipe's memory requirement is not recorded, or the profile lacks a field the calculation needs, or the recipe's engine has no evidence of running on this architecture. |
| **✕ Will not fit as recorded** | The recorded resident requirement exceeds available memory, and the recipe records no offload strategy that would change that. |

**There is no "Fits" group and no unconditional green verdict anywhere in the
product.** The strongest thing the interface will say is *verified on this exact
machine* — a statement about evidence, not a prediction.

A recipe in a lower group is never hidden. `✕ Will not fit as recorded` is
collapsed by default with its count visible, and expands; it is often the most
useful group, because it tells an operator what their next machine buys them.

---

## 5. The compatibility result

Every result states its full arithmetic. No verdict is rendered without one.

```
Qwen3.8-27B NVFP4 (BF16 lm_head) — SGLang + DFlash2
◐ Estimated to fit

Likely to fit with approximately 26.0 GB remaining, assuming 8K context and
one active conversation. This recipe has not been tested on this exact M4 Max
configuration.

  MODEL MEMORY        23.7 GB    artifact size, from the HuggingFace tree endpoint
  RUNTIME BUFFERS     included   the recipe records a 32 GB resident requirement
                                 that already covers weights, draft and KV pool
  KV-CACHE ALLOWANCE  see above  Qwen3.8-27B records 32,768 bytes/token, so 8K
                                 single-stream is ≈ 0.27 GB inside that figure
  ASSUMED CONTEXT     8,192 tokens
  ASSUMED CONCURRENCY 1 stream
  SAFETY RESERVE      6.0 GB     macOS default, adjustable
  CPU / DISK OFFLOAD  none recorded
  ─────────────────────────────────────────────────────────────────────────
  RECORDED RESIDENT   32.0 GB    from the recipe's own requirements
  YOUR USABLE MEMORY  58.0 GB    64 GB less the 6 GB reserve
  REMAINING           26.0 GB

  EVIDENCE            Similar hardware. Measured on DGX Spark (GB10, aarch64),
                      not on Apple Silicon. This engine path is CUDA-only —
                      see caveats.
```

### Where each line actually comes from

This is the part that must not drift into invention.

- **Recorded resident requirement** — `requirements.memory_gb`. Source-backed,
  present on all 65 setups, and it is the *primary* input. The estimate is built
  on the dataset's own figure, not on a reconstruction of it.
- **Model memory** — `variation.size_gb`, from the HuggingFace tree endpoint per
  AGENTS.md law 7.
- **KV-cache allowance** — computable only where `kv_bytes_per_token` is
  recorded. **That is 1 of 22 model families today (Qwen3.8-27B).** For the other
  21 the line reads:
  `KV-CACHE ALLOWANCE — not derivable: this family does not record bytes per token.`
  It is never estimated from parameter count.
- **Runtime buffers** — not a field in the dataset. Where
  `requirements.memory_gb` exceeds `variation.size_gb`, the difference is the
  recipe's own recorded allowance and is described as such. Where it does not,
  the line reads `not recorded separately`. No engine overhead constant is
  invented.
- **Safety reserve** — a user-facing assumption about the machine, labelled
  adjustable. The only number on the panel that is not from the dataset, and it
  is marked.
- **CPU / disk offload** — from `requirements.notes` and `caveats` where a recipe
  records one, e.g. the mlx-flash SSD expert-streaming lane whose 224 GB
  artifact runs on a 64 GB Mac. Otherwise `none recorded`.
- **Exact vs similar** — from the hardware class's `measured_by_us` flag and
  whether the class is a SKU or a range.

### Language rules

- Hedge first, number second: *"Likely to fit with approximately 26.0 GB
  remaining, assuming …"*
- Every verdict names its assumptions in the same sentence.
- Every verdict that is not exact-device evidence says so explicitly, naming the
  hardware the evidence actually came from.
- The words `fits`, `compatible`, `supported` never appear unqualified.
- A cross-architecture mismatch (a CUDA engine path against an Apple profile) is
  called out in the evidence line even when the memory arithmetic passes,
  because memory is not the binding constraint there.

---

## 6. Optional goals

A single optional row, collapsed by default, above the results:
`▸ Narrow by what you want to do (optional)`.

General chat · Coding · Vision · Tool use · Long documents · Single-user API ·
Multi-user serving · Lowest setup complexity · Highest measured throughput.

**What a goal may and may not do:**

| Goal | Legitimate effect | Forbidden |
|---|---|---|
| Vision | Filter to recipes whose **recipe-level** capability records vision enabled. | Implying the model is good at vision. |
| Tool use | Filter to `capabilities.tools == true`. | Ranking by tool-calling quality. |
| Long documents | Filter by tested context ceiling. | Claiming long-context quality. |
| Multi-user serving | Surface recipes with a `decode_agg` measurement, showing concurrency **and** the per-stream figure at that load. | Ranking by aggregate throughput. |
| Lowest setup complexity | Sort by the derived complexity score. | — |
| Highest measured throughput | Sort by measured value, **with the speed disclosure band**. | Presenting it as a ranking of models. |
| Coding | **Filters nothing by default.** | Labelling any recipe "best for coding". |

Selecting *Coding* renders, in place of a filtered list:

> Only 3 of 65 recipes carry a coding measurement, from three different
> harnesses. AGENTS.md law 4 forbids ranking across harnesses, so this goal does
> not reorder anything. Here are the recipes that carry coding evidence, each
> with its harness named — judge them yourself.

The three concepts stay separate on screen at all times:

| Concept | Belongs to | Answered by |
|---|---|---|
| Model capability | the model family | `models[].modalities` |
| Runtime support | the recipe | `setups[].capabilities` |
| Task quality | neither, without comparable benchmark evidence | a measurement with a named harness |

A vision-capable model whose recipe disables vision renders as
`Model: vision ✓ · This recipe: vision ✕ (runtime does not implement it)` —
eight setups in the current dataset do exactly this, and it is visible on the
collapsed row, not just in the detail.

---

## 7. Sending results onward

Each result carries `☐ compare` and `open recipe →`. Selections made here feed
the same compare rail as the Directory, and the rail persists across tabs. Two
recipes selected in My Hardware and one in the Directory make one comparison.
