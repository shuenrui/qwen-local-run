# Qwen Local-Run Directory

A data-driven directory of every community way to run a Qwen model on hardware
you own. It scales the hand-written dashboard at `local.host.impossibuild.ai`
from a single shelf to hundreds of filterable entries without hand-editing HTML.

The unit of an entry is a **runnable setup**: one specific checkpoint, one
specific engine configuration, on specific hardware. That is the thing that
actually gets run and actually gets measured, so it is the thing the directory
stores. A model with 8 checkpoints across 3 engines is 24 setups, not one row.

## Layout

```
directory/
├── SCHEMA.md            the data-model contract (read this before adding data)
├── validate.py          stdlib validator; fails the build on bad data
├── build.py             stdlib generator -> site/index.html (self-contained)
├── verify_browser.py    headless-Chromium checks against the built site
├── data/
│   ├── models/<id>.json      architecture, context, modalities, license
│   ├── hardware/<id>.json    the box: memory, bandwidth, arch
│   ├── engines/<id>.json     the server: SGLang, vLLM, llama.cpp, ...
│   ├── publishers.json       who made things: labs, quant shops, individuals
│   └── setups/<id>.json      one runnable setup  <- the main entity
└── site/index.html      generated; commit or serve it, do not edit it
```

## Workflow

```
# 1. edit or add data/setups/<id>.json (see SCHEMA.md for required fields)
python3 directory/validate.py     # must print 0 errors
python3 directory/build.py        # regenerates site/index.html
```

`build.py` runs `validate.py` first and refuses to write on failure. The
generated page is a single self-contained HTML file: the dataset is inlined as
JSON, so it can be served statically or opened from disk with no build step.

## Provenance is the load-bearing rule

Every number carries a `provenance` field and the site never mixes tiers:

| Tag      | Meaning                                    | Trust |
|----------|--------------------------------------------|-------|
| `box`    | measured on our own hardware, method stated | high  |
| `forum`  | reported by a community builder, linked     | mid   |
| `vendor` | claimed by the publisher of the artifact    | low   |

`box` numbers must have `date`, `n`, and `method`. `forum` and `vendor` numbers
must have a `source` URL. A number with no source is a validation error, and the
fix is to delete the number, not to downgrade the rule. A setup's
`provenance_tier` may never overstate its best measurement, and the validator
enforces that.

## Current coverage

65 setups, 22 models, 6 hardware classes, 7 engines, 29 publishers. Provenance
splits 4 `box` (measured on our DGX Spark), 28 `forum` (builder- or
thread-reported, each with its URL and the quoted sentence), 1 `vendor`
(unsloth's own claim), and 32 `untested` lanes that validate and name a run
command but carry no numbers yet.

Hardware lanes: DGX Spark / GB10 (47 setups, plus 6 that also list the
ThinkStation PGX as the same-silicon alternative), 24 GB consumer GPUs (13),
128 GB Macs (11), 32-64 GB Macs (4), mixed multi-GPU ~72 GB rigs (4), and the
Lenovo ThinkStation PGX. Engines: SGLang, vLLM, llama.cpp, MLX, Ollama,
LM Studio, plus one custom-fork category. Model families span the 3.0, 3.5,
3.6 and 3.8 lines including the VL and Omni branches; see the scope note below
for what is deliberately absent.

Community entries came from three research passes (HuggingFace quant cards,
GitHub run recipes, forum threads); every candidate was re-checked against the
validator's enums and every URL re-fetched before merging. Reddit is
unreachable from this environment (hard 403), so no Reddit-sourced number is
recorded anywhere in the dataset.

Scope of the family list, from an audit of the Qwen org on HuggingFace:
there is **no Qwen 4 series** — 3.8 is the newest line. Deliberately excluded
from setups: `Qwen3.8-2.4T-A95B` and `Qwen3-Coder-480B-A35B` (cluster-scale, no
single-box local lane), sub-4B edge models (no hardware class below a 24 GB GPU
or 32 GB Mac exists yet), and the Embedding/Reranker/ASR/TTS families (not
text-generation serving). Vision and Omni families are included where a local
lane exists.

## Known gaps, deliberately

- `hardware/gpu-24gb.json` and `hardware/mac-128gb.json` are **class** entries
  (RTX 3090/4090 class; M3/M4 Max class), not single SKUs, and are not measured
  by us. They carry a bandwidth range and a note saying so.
- `engines/custom-fork.json` has a null `url` on purpose: it is a category for
  builder-specific forks with no single canonical upstream. The validator
  accepts a null URL only for `kind: "fork"`.
- Community research (HuggingFace quants, GitHub recipes, forum-reported
  numbers) is merged as of 2026-09-05. What remains uncovered: Reddit-sourced
  numbers (platform blocks this environment), Mac lanes for the 27B dense
  model beyond MLX/llama.cpp defaults, and any true fine-tunes — everything
  here so far is a quant, a build, or a weight-edited derivative.
- `bench/` results are not wired in yet. Once they are, `box` rows should be
  regenerated from `measurements.jsonl` rather than typed by hand.

## Bench wiring

`box` rows are not typed by hand once the harness has run them. `bench/ab.py`
writes `results/<exp>-<stamp>/results.json`; `import_bench.py` turns those rows
into measurements on the matching setup:

    python3 directory/import_bench.py bench/results/<exp>-<stamp> --engine mtp          # dry run
    python3 directory/import_bench.py bench/results/<exp>-<stamp> --engine mtp --apply  # write

`directory/data/bench_map.json` maps `<experiment model name>@<engine>` to a
setup id; `--engine` is required when a model has several lanes because
`results.json` does not record which engine the run used. Applying replaces
only the `box` measurements for the touched metrics (forum/vendor rows are
never touched), flips the setup to `measured`, and appends an audit line per
measurement to `data/measurements.jsonl`. Running the benchmarks themselves
still needs a booted model, which is a separate decision.

## Verification

`verify_browser.py` drives the built page in headless Chromium (real clicks,
typing, and selection) and checks: rendering counts, every filter option
against the inlined dataset, multi-term search, all four sort modes,
expand/collapse (mouse and keyboard), expand-all, reset, the copy button and
clipboard contents, provenance pills versus data, and horizontal overflow at
1440px and 390px. It exits non-zero on any failure. See its docstring for the
Playwright setup. Pass a URL as the first argument to verify a deployed copy:

    /tmp/pwenv/bin/python directory/verify_browser.py https://local.host.impossibuild.ai/

## Live

Published as a static site on ifhost from the Pro account
(`shuenrui0003@gmail.com`):

    ifhost publish --name local directory/site/index.html

Live at **https://local.host.impossibuild.ai** — the directory's original
address, now served from the Pro plan (no expiry window). A second name,
`qwen-local-run`, points at the same build as a spare alias; delete it with
`ifhost sites rm qwen-local-run` if one URL is preferred. Re-running `publish`
with the same name replaces the site's entire content, so this one command is
the whole deployment step after any data change.

History: the site first went out on the free account
(`shuen.rui@impossible.finance`), whose 24-hour window paused it on
2026-09-06. That paused site still held the name `local`, so it was deleted
(its content was already superseded and lives in this repo, including the old
hand-written dashboard at `dashboard/index.html`) to free the name, which was
then re-claimed from the Pro account. Site names are global across ifhost
accounts and first-claim-wins, which is why the reclaim had to happen in the
same breath as the delete.
