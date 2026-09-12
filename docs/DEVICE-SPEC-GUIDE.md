# Device spec integration guide

**Date:** 2026-09-10 · **Contract:** `directory/data/device-schema.json` ·
**Enforcement:** `directory/validate.py` (`check_device`) · **Docs:**
`directory/SCHEMA.md` § "device specs"

## Why

The directory records what a setup *achieved*; the device block records the
hardware physics that explain *why the same model scores differently across
boxes*. Memory bandwidth sets the low-concurrency decode roofline; capacity
sets what fits; vendor-published compute peaks set prefill ceilings. Without
these, "27B does 43.2 tok/s here but 11.5 there" is unexplainable noise.

## Placement rule

One spec per hardware record, never per setup:

```text
directory/data/hardware/<id>.json   ← "device": { ... } lives here
```

Setups reference hardware ids (`hardware: ["dgx-spark"]`) and inherit the spec.
A setup may carry its own `device` key **only** as a measurement-specific
override — e.g. a benchmark ran on an overclocked or partially-offloaded card
that differs from the class. Same shape, no record cross-checks.

## Field semantics that matter

| Field | Meaning | Rules |
|---|---|---|
| `memory.bandwidth_gbs` | The strongest hardware predictor of low-concurrency decode speed | Must equal the record's `bandwidth_gbs` on exact-SKU records; `null` + variants allowed on class records |
| `memory.unified` | CPU/GPU share one pool (Apple Silicon, GB10) | `true` required for Apple records (validator warns) |
| `compute.*_tflops` | Vendor-published compute peaks | `null` when unpublished — never a third-party estimate |
| `compute.neural_engine_tops` | Apple Neural Engine, TOPS | Apple publishes it, but current MLX/llama.cpp paths mostly drive the GPU — not an inference promise |
| `variants[]` | Exact SKUs inside a class | Unique ids; bandwidth must fall inside the class `bandwidth_range_gbs` |
| `sources[]` | Provenance for specs | Every published figure traces to the cited vendor page |

## Verified example entries (shipped in the dataset)

Full blocks live in the records; these are the verified headline values:

### DGX Spark (GB10) — `dgx-spark.json`, exact SKU

128 GB LPDDR5X unified, **273 GB/s** (256-bit), 20-core Arm
(10× Cortex-X925 + 10× Cortex-A725), up to **1 PFLOP FP4 (sparse)**,
140 W chip TDP / 240 W PSU, 4 TB self-encrypting NVMe.
Source: [NVIDIA DGX Spark specifications](https://www.nvidia.com/en-us/products/workstations/dgx-spark/).

### Apple M4 family — `mac-64gb.json` / `mac-128gb.json`, class + variants

| Chip | Bandwidth | RAM configs | In class |
|---|---:|---|---|
| M4 (base) | 120 GB/s | 16–32 GB | mac-64gb |
| M4 Pro | 273 GB/s | 24–64 GB | mac-64gb |
| M4 Max (low) | 410 GB/s | 36–48 GB | mac-128gb |
| M4 Max (high) | 546 GB/s | 48–128 GB | mac-128gb |
| M1 Pro / M2 Pro | 200 / 204.8 GB/s | 16–32 GB | mac-64gb |
| M3 Pro | 153.6 GB/s | 18–36 GB | mac-64gb |
| M1 Max / M2 Max / M3 Max | 400 / 409.6 / 409.6 GB/s | 64–128 GB | mac-128gb |
| M2 Ultra | 800 GB/s | 64–192 GB | *not yet a class* |
| M3 Ultra | 819 GB/s | 96–512 GB | *not yet a class* |

Sources: [Apple newsroom (M4 Pro/Max)](https://www.apple.com/newsroom/2024/10/apple-introduces-m4-pro-and-m4-max/),
[MacBook Pro tech specs](https://support.apple.com/en-us/121553),
[Ars Technica comparison table](https://arstechnica.com/apple/2024/10/apples-m4-m4-pro-and-m4-max-compared-to-past-generations-and-to-each-other/),
[Mac Studio 2025 (M3 Ultra)](https://support.apple.com/en-us/122211).

### Consumer GPU — `gpu-24gb.json`, class + variants

| Card | Bandwidth | FP32 | Tensor | TGP |
|---|---:|---:|---|---:|
| RTX 3090 (GA102, Ampere) | 936 GB/s | 35.6 TFLOPS | no native FP8 | 350 W |
| RTX 4090 (AD102, Ada) | 1008 GB/s | 83 TFLOPS | 1321 AI TOPS (FP8 sparse) | 450 W |

Sources: [NVIDIA RTX 4090 page](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4090/),
[videocardz RTX 3090](https://videocardz.net/nvidia-geforce-rtx-3090).

## Corrections applied to the original request

The task's example values contradicted vendor-published specs. In this
dataset, a number with no source is deleted (AGENTS law 1), so the examples
carry sourced values instead:

| Claimed in task | Verified reality | Why it matters |
|---|---|---|
| DGX Spark bandwidth **800 GB/s** | **273 GB/s** (NVIDIA spec sheet, 256-bit LPDDR5X) | The decode roofline is ~3× lower than claimed |
| DGX Spark **72 ARM cores** | **20-core Arm** (10× X925 + 10× A725) | 72 cores is Grace *CPU* territory, not GB10 |
| DGX Spark TDP **500 W** | **140 W** chip TDP, 240 W PSU | Determines sustained-load behaviour |
| DGX Spark FP32 1.5 / FP16 3.0 / FP8 6.0 TFLOPS | **Not published**; only FP4-sparse 1 PFLOP | Inventing a 2× scaling ladder is fabrication |
| DGX Spark **8 memory channels** | Channel count **not published**; 256-bit interface is | Only published facts enter |
| M4 **~200 GB/s** | **120 GB/s** (200 is M1 Pro; M4 Pro is 273) | A 2× error in the headline hardware predictor |
| **M4 Ultra 800 GB/s** | **No M4 Ultra exists**; 800 GB/s is M2 Ultra, 819 GB/s is M3 Ultra | The variant does not exist |
| M4 `neural_engine_tflops` for MLX | Apple publishes **TOPS (38)**, not TFLOPS; MLX mostly drives the **GPU** | ANE TOPS is not an MLX throughput figure |
| RTX 3090 (any) | 936 GB/s, 350 W, 35.6 TFLOPS FP32, **no native FP8** | Ampere FP8 paths are emulated and slower |

## How to add a device block

1. Verify every figure on the vendor's own page (datasheet, product page,
   support article). Anything unpublished → `null` + note.
2. Edit the hardware record — add `device` between `notes` and
   `measured_by_us` (see any of the five updated records for shape).
3. For a class record: set `memory.bandwidth_gbs: null`, enumerate
   `variants[]` with per-SKU bandwidths inside `bandwidth_range_gbs`.
4. Cite every figure in `device.sources[]` with a note naming what it backs.
5. Bump the record's `updated` date.
6. Run `python3 directory/validate.py` — then `python3 directory/check.sh`
   before publishing.

### Per-setup override (rare)

```jsonc
// setups/<id>.json — only when THIS measurement's hardware differs
"device": {
  "identity": {"name": "RTX 4090 (OC, 2000 MHz power-capped)", "chip": "AD102 (Ada Lovelace)",
               "manufacturer": "NVIDIA", "os": "Ubuntu 24.04"},
  "memory": {"total_gb": 24, "type": "GDDR6X", "bandwidth_gbs": 1008, "unified": false},
  "thermal": {"tdp_watts": 300, "note": "owner power-capped the card"},
  "sources": [{"url": "https://...", "note": "builder's own description of the card"}]
}
```

## Validator behaviour

- Hardware record **without** `device`: passes with a warning naming the gap
  (`--strict` fails on it). Currently exactly one record lacks a block
  (`gpu-multigpu-72gb`) — intentional, its numbers always name the exact card
  mix in measurement context.
- Unknown keys, string-in-number-field, missing identity, empty sources,
  variant bandwidth outside the class range, and exact-SKU bandwidth drift
  are **errors**.
- Apple records without `memory.unified: true` get a warning.

The site reads the block from the inlined dataset; rendering it in Compare and
My Hardware is a presentation follow-up, not a data change.
