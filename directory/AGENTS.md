# AGENTS.md — cold-start brief for the Qwen Local-Run Directory

Read this first. It states the mission and the inviolable rules; `SCHEMA.md`
states the data model; `README.md` states current coverage and workflows.
If any of them disagree, this file wins on intent, `SCHEMA.md` wins on data
shape, and the validator (`validate.py`) wins on everything it can check.

## Mission

A public directory of every community way to run a Qwen model on hardware a
person can own. The unit of an entry is a **runnable setup**: one checkpoint ×
one engine configuration × one hardware class — because that is the thing that
actually gets run and actually gets measured. A model with 8 checkpoints across
3 engines is 24 setups, not one row. The directory scales a hand-written
dashboard into hundreds of filterable, source-linked entries, and it is
**provenance-first**: it would rather show a slow number with its source than a
fast number without one.

Success looks like: a newcomer filters by their box, sees what fits, sees how
fast it goes *according to whom*, and can run it from the copyable command.

## The laws (do not break these)

1. **Every number carries a provenance tier**: `box` (measured on the owner's
   DGX Spark, with date, n and method), `forum` (a community builder reported
   it, with a fetched, resolving source URL and the quoted sentence), `vendor`
   (the publisher's own claim, with the card URL). A number with no source is
   deleted, never downgraded and never kept.
2. **Tiers are never blended.** A card shows its own tier; the site's hint line
   counts them separately. `provenance_tier` must equal the best measurement
   tier present; the validator enforces this.
3. **Negative results stay.** "NVFP4 is slower than INT4 on SM121" and "dense
   27B does 7.8 tok/s" are among the most valuable rows in the dataset.
4. **No quality leaderboard.** Quality canaries (GPQA, GSM8K, TerminalBench,
   perplexity) come from different harnesses; ranking across them would be
   false precision. Record canaries per setup; never aggregate them into a
   score.
5. **`site/index.html` is generated.** Never edit it by hand; change `build.py`
   or the data and rebuild.
6. **Never push to `origin`.** `origin` is the public
   `MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark` repo — a third party's serving
   stack that this project measures against and credits, not an upstream.
   Pushes go to remote `mine` (`shuenrui/qwen-local-run`), branch mapping
   `qwen-directory-standalone:main`.
7. **Sizes come from the HuggingFace tree endpoint**
   (`/api/models/<id>/tree/main?recursive=true`). The siblings endpoint returns
   0 for LFS files; a size of 0 or null is invalid.
8. **`variation.license` is the weights' license** in SPDX display form;
   builder/runtime terms that differ go in `caveats`.

## Repo map

    data/setups/<id>.json     one runnable setup — the main entity
    data/models/<id>.json     family: architecture, context, modalities, license
    data/hardware/<id>.json   hardware class (bandwidth is the point, not RAM)
    data/engines/<id>.json    serving engine, its gotchas and notable flags
    data/publishers.json      attribution registry (quant shops, builders, labs)
    data/bench_map.json       experiment-model@engine -> setup id, for imports
    validate.py               schema/enum/provenance enforcement (runs in build)
    build.py                  stdlib generator -> site/index.html
    check_links.py            link-rot guard; exit 1 on any dead source URL
    import_bench.py           bench/ab.py results -> box measurements (+jsonl)
    verify_browser.py         headless-Chromium behaviour checks, any URL
    check.sh                  the gate: validate -> links -> build -> verify
    tools/vet_candidates.py   pre-merge vetting for research-pass output
    tools/install_verify_env.sh  Playwright venv at tools/.pwenv (gitignored)
    tools/history/            one-time authoring scripts + their raw inputs

## Workflows

**Add or change data:** edit `data/`, then `python3 directory/check.sh`. It must
print 0 errors and pass the browser suite before anything is published.

**Publish the site:** `ifhost publish --name local directory/site/index.html`
(Pro account; no expiry). Re-running replaces the site's entire content.

**Push:** `git push mine qwen-directory-standalone:main`.

**Research pass:** agents write candidate JSON to a file as they go (a run that
dies holding everything in memory loses everything); then
`tools/vet_candidates.py` checks enums, re-fetches every URL and flags
duplicates against the current dataset; only vetted candidates get merged.
`tools/history/inputs/` holds previous passes' raw output as examples —
including numbers that were later dropped with caveats.

**Box measurements:** run `bench/ab.py` in the serving checkout, then
`python3 directory/import_bench.py <results-dir> --engine <eng> --apply`.
Booting models costs time and power; it is gated on the owner's explicit
go-ahead. Do not boot models unprompted.

## Environment

Python 3 stdlib only for validate/build/import/check_links. Browser checks need
the Playwright venv (`tools/install_verify_env.sh`). Publishing needs the
`ifhost` CLI, already authenticated on this box. Git pushes use `gh`
(device-flow OAuth), already authenticated. No credentials live in this repo.

## Known gotchas

- Reddit hard-403s this environment; no Reddit-sourced number can be verified
  here, so none is recorded. Say so rather than importing one.
- Duplicate identity is checkpoint + engine + hardware + **config string**; two
  setups may share the first three when the config differs.
- `generation` must be numeric (3.0/3.5/3.6/3.8) or the shelf sorts wrong;
  hybrid-line families (Coder-Next, Next-80B) are 3.5.
- Forum threads on forums.developer.nvidia.com need the full slug *and* numeric
  id; truncated slugs 404. Run `check_links.py` after adding any.
- Prose style: plain, specific, no marketing voice. Caveats say what a number
  does *not* mean. Dates ISO. Sizes one decimal, GB.

## Open decisions (owner's call — do not resolve these unilaterally)

1. Repo LICENSE (public but unlicensed today).
2. Whether to vendor a copy of the serving/bench harness for self-contained
   reproducibility, or keep crediting the external checkout.
3. CI: a GitHub Action running `check.sh` on push.
4. Family-scope expansion (sub-4B edge models, cluster-scale models, VL/Omni
   beyond current entries) and the next community-research pass.
