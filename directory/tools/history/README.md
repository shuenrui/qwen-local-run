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
