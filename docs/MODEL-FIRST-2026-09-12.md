# Model-first homepage

**Shipped:** 2026-09-12. This document supersedes the 2026-09-10 Directory
brief only for the default route. The advanced recipe index remains intact at
`#/recipes`.

## Job

A visitor who already knows the model they care about should first see the
available model families, the most accessible defensible hardware baseline,
and any single-stream speed recorded on that exact baseline. They should not
have to scan every checkpoint and engine recipe before choosing a model.

## Information architecture

| Destination | Route | Job |
|---|---|---|
| Models | `#/` | Choose a model and inspect its practical baseline |
| Recipes | `#/recipes` | Search and filter the complete advanced recipe index |
| My Hardware | `#/hardware` | Evaluate recipes against one declared machine |
| Compare | `#/compare` | Compare two to four exact recipes |

The homepage is a model list controlling a persistent evidence preview on
desktop. Mobile rows navigate to the existing model-family route, where the
same baseline appears before architecture and recipes.

## Practical baseline

The baseline is editorial, explicit, and review-dated. It references one setup
instead of copying its values. A selected setup must be `reported` or
`measured`, stable 4-bit-or-better, and reproducible. Selection prioritizes a
single consumer GPU or common Mac, consumer hardware with clearly labelled
offload, a 128 GB workstation/appliance, then custom multi-GPU rigs.

RAM and SSD streaming are valid only when resident memory, VRAM, disk, context,
and offload notes remain visible. A model without a qualifying setup says
`Not verified yet`; the homepage never derives a recommendation from weight
size alone.

Speed is rendered only from the referenced setup's representative
single-stream decode measurement. The value always retains metric, statistic,
concurrency state, provenance, note, and source. A faster number from another
recipe is never combined with the baseline requirement.

## First viewport

At desktop width the first viewport contains product navigation, one sentence,
model search, generation/architecture/baseline filters, the first model rows,
and the selected model's practical-baseline preview. No recipe table,
personalization gate, compatibility verdict, or unsourced estimate appears.

## Responsive behavior

- Desktop: model list and sticky preview side by side.
- Tablet: preview first, then the model list.
- Mobile: structured model rows; selecting one opens its model-family page.
- All widths preserve keyboard focus, URL-addressable selection, dark mode,
  reduced motion, and reflow at 320 px.
