# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

People evaluating or operating Qwen models on hardware they can own. They may
arrive knowing the model they want and need a fast, source-backed answer to
what hardware can run it before inspecting implementation recipes.

## Product Purpose

Qwen Local-Run is a provenance-first directory of community ways to run Qwen
models locally. The homepage helps visitors choose a model and understand its
practical hardware floor; the recipe directory then exposes every recorded
checkpoint, engine configuration, measurement, command, caveat, and source.

## Positioning

The directory keeps model claims, runnable recipes, hardware requirements, and
measurements separate. A speed is shown only with the exact recipe and source
that produced it; missing evidence remains visible instead of being estimated.

## Operating Context

Visitors browse models, inspect a curated practical baseline, open all recipes
for one model, check compatibility against their own machine, and compare two
to four exact recipes. The output is one self-contained, hash-routed HTML file
that also works from `file://` and makes no network requests after loading.

## Capabilities and Constraints

- The default homepage lists model families, not every recipe.
- The full advanced recipe index remains available at `#/recipes`.
- A practical baseline is a curated reference to a reported or measured,
  reproducible, stable 4-bit-or-better setup on the most accessible recorded
  hardware. RAM or SSD offload is allowed only when shown prominently.
- Baseline speed is shown only when the referenced setup has a single-stream
  decode measurement. It is never borrowed from another recipe.
- Models without a defensible baseline remain listed as `Not verified yet`.
- Compatibility verdicts remain exclusive to My Hardware and are always
  hedged; the catalogue never says an unconditional `fits`.
- Provenance tiers and confidence dimensions remain independent and are never
  blended.
- The generated `directory/site/index.html` is never edited manually.
- Publication requires explicit approval.

## Evidence on Hand

The source dataset lives under `directory/data/`. Models, hardware classes,
engines, publishers, runnable setups, measurements, caveats, and source URLs
are validated by `directory/validate.py`. Coverage is incomplete by design;
the interface must not fabricate missing minimums or performance.

## Product Principles

- Start from the model a visitor wants, then reveal implementation detail.
- Prefer a sourced gap over an unsupported estimate.
- Keep practical guidance attached to the exact runnable setup behind it.
- Make advanced recipe detail available without making it the entry barrier.
- Explain hardware trade-offs, especially offload, context, and bandwidth.

## Accessibility & Inclusion

The web interface must remain keyboard operable, visibly focused, semantic,
usable at 400% zoom, responsive from 320px upward, compatible with reduced
motion, and understandable without relying on colour alone.
