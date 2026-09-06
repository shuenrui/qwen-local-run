# One-time authoring scripts (provenance record)

These scripts created or repaired the dataset in `directory/data/`. They are
kept so the dataset's history is reproducible and auditable, **not** as a
pipeline to re-run: several are not idempotent and all of them hard-code the
state of the world (URLs, research files in `/tmp`) at the moment they ran.

Applied in this order:

1. `00_audit_snapshot.py` — the hygiene audit that found link rot, null
   licenses, zero sizes and dangling publishers (read-only).
2. `01_seed_setups.py` — the first 22 setups from this repo's own README,
   profile cards and dashboard.
3. `02_merge_research_pass1.py` — HuggingFace-quant and forum-thread findings.
4. `03_merge_research_pass2.py` — GitHub-recipe findings plus the blazux and
   Albond upgrades.
5. `04_hygiene_urls_licenses.py` — repaired truncated NVIDIA forum URLs,
   removed a dead publisher, filled licenses from the HuggingFace API.
6. `05_hygiene_license_normalize.py` — SPDX display form and family-derived
   licenses with caveats.
7. `06_hygiene_sizes.py` — recomputed every `size_gb` from the HuggingFace
   tree endpoint after the siblings endpoint was found to return 0 for LFS.

The maintained tools live one level up: `validate.py`, `build.py`,
`check_links.py`, `import_bench.py`, `verify_browser.py`.

8. `07_normalize_generations.py` — set hybrid-line families (Coder-Next,
   Next-80B) to generation 3.5 so shelf ordering matches lineage.
9. `08_overflow_diagnostic.py`, `09_scroll_reachability.py` — the layout
   diagnostics that found and then proved fixed the 390 px overflow and the
   measurement-table scroll containers.

`inputs/` holds the raw research-agent outputs (`research_hf.json`,
`research_github.json`, `research_forum.json`) that passes 2 and 3 consumed.
They are snapshots of what the agents returned, including numbers that were
later dropped with caveats; the dataset, not these files, is the source of
truth.

One level up, `tools/vet_candidates.py` is the maintained vetting script for
future research passes: it checks candidate enums, re-fetches URLs and flags
duplicates against the current dataset before anything is merged.
`tools/install_verify_env.sh` creates the Playwright venv at `tools/.pwenv`
(gitignored) so `verify_browser.py` stays runnable after a reboot.
