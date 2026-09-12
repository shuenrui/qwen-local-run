# Redesign — Qwen Local-Run Directory, 2026-09-10

A ground-up redesign of the product's information architecture, interaction
model, visual system, responsive behaviour and data presentation. The dataset's
integrity and provenance rules are unchanged.

**Baseline:** `711e97f` — *Improve directory UX and benchmark semantics*.
**Authority:** `directory/AGENTS.md` for product truth and provenance.

## The change in one paragraph

The product today is a single 15,800px page that opens with a machine
questionnaire, collapses trust into one badge, gives no recipe a URL, and offers
no way to compare two of the fifteen ways to run Qwen3.8-27B. It becomes a
three-tab technical index: a **Directory** homepage of model-family shelves
showing all 65 recipes with no personalization gate, a **My Hardware** tab where
every compatibility claim lives and states its own arithmetic, and a **Compare**
workspace that names every axis on which two measurements are not comparable and
never declares a winner. Trust splits into four independent dimensions. Every
recipe, model and publisher gets a permanent URL.

## Documents

| | |
|---|---|
| [01 — Audit and product map](01-audit-and-product-map.md) | What exists, what is wrong, what is preserved / migrated / replaced / removed, route map, user flows, and how this brief resolves against the 2026-09-07 UX review |
| [02 — Design system](02-design-system.md) | Colour, typography, space, the four component families, the evidence strip, motion, focus |
| [03 — Directory](03-directory.md) | Desktop and mobile layouts, the model-family shelf, the recipe row and its states, search, filters, sorting |
| [04 — My Hardware](04-hardware.md) | Detection and its real limits, profiles, assumptions, the five compatibility groups, the arithmetic panel, optional goals |
| [05 — Compare](05-compare.md) | The selection rail, the seven-section workspace, incomparability detection, states, mobile |
| [06 — Trust, pages, states, accessibility, responsive](06-pages-states-a11y.md) | The four confidence dimensions, recipe / model / publisher / methodology / contribute pages, every non-happy state, the accessibility contract, the responsive matrix |
| [07 — Data model](07-data-model.md) | Entity status today, presentation-only derivations, proposed schema additions, migration, and what is explicitly not changed |
| [08 — Implementation and verification](08-implementation-and-verification.md) | Build architecture, routing, order of work, and the check-by-check mapping from the old browser suite to the new one |

## Non-negotiables carried through

- The Directory is the homepage; every recipe is discoverable without
  personalization.
- No unconditional "Fits" verdict anywhere in the product.
- Compare never declares a winner.
- Provenance tiers never blend; quality canaries are never aggregated.
- Negative results stay visible, and are promoted rather than buried.
- Model capability, runtime support and task quality remain three separate
  claims with three separate evidence requirements.
- `site/index.html` stays generated; `validate.py` is not weakened; no data is
  invented to fill a gap.
- Nothing is published without explicit approval.
