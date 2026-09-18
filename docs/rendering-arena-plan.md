# HTML Rendering Arena — expansion plan

Source: user brief, 2026-09-18 (pasted from external research/posts). The vision: a
benchmark for whether models can turn a specification into a *working visual system* —
physics, interaction, animation, spatial reasoning, design — not just a frontend
showcase. Implementation mapping for this repo is at the bottom.

## Recommended Tracks

1. 2D Physics
2. 3D Physics
3. Games
4. Mechanical Simulations
5. Scientific Visualizations
6. Procedural Worlds
7. Image-Grounded Art
8. Creative Canvas/SVG
9. Interactive Product Experiences
10. Long-Horizon Construction

## Best Challenge Ideas (abridged — full detail in chat history 2026-09-18)

1. **Earthquake Tower** — beams/joints tower, adjustable quake intensity+frequency.
   Objective: stands at 3, deforms at 5, collapses at 8; reset/replay; nothing escapes.
2. **Suspension Bridge Load Test** — cars cross, cables/decks react; hidden variants
   (span, vehicle weight, anchor position).
3. **Rube Goldberg Machine** — ball triggers dominoes→pulley→ramp→pendulum→bell;
   score each checkpoint separately, not just pass/fail.
4. **Lunar Lander** — thrust/fuel/gravity/terrain; score landing velocity, angle,
   fuel, stability.
5. **Orbital Slingshot** — moon gravity assist to reach a station; measurable objective
   (better than decorative solar system).
6. **Cargo Crane** — move containers without swing/collision; score time, collisions,
   max cable tension.
7. **Marble Sorting Factory** — gates/lifts/magnets/belts, fixed seed, score accuracy.
8. **Trebuchet Range** — parameterized; score distance over hidden configurations.
9. **Dam-Break Simulation** — particle fluid through obstacles; volume conservation.
10. **Cargo Ship Buoyancy** — load balancing, list/capsize thresholds.
11. **Soft-Body Obstacle Course** — jelly creature, deformation, controls.
12. **Cloth Wind Tunnel** — constraint cloth, adjustable wind, tearing.
13. **Chain-Reaction Demolition** — remove 3 supports, collapse into marked zone.
14. **Pinball Machine** — flippers/bumpers/ramps/multiball/scoring.
15. **Physics Mini Golf** — 3 holes, friction zones, hazards, camera.
16. **Robot Arm Warehouse** — IK, collision avoidance, pick & place.
17. **Four-Cylinder Engine** — transparent, synchronized valvetrain, speed control.
18. **Mechanical Clock** — gears/escapement/pendulum, correct ratios over time.
19. **Vehicle Suspension Lab** — spring/damper/mass sliders + graphing.
20. **Wind-Powered Machine** — turbine→pump→tank energy chain.

Scientific rendering: 21. Interactive Solar System (correct relative periods,
ellipses, camera follow, time accel, trails, moons, gravity sandbox) · 22. Three-Body
Sandbox · 23. Black Hole Lensing · 24. Magnetic Field Lab · 25. Optics Bench ·
26. Wave Interference Tank · 27. Double-Pendulum Chaos (graph divergence) ·
28. Weather Cell · 29. Plate Tectonics · 30. Ecosystem Terrarium.

Procedural 3D: 31. Voxel Fossil Excavation · 32. Voxel Creature Printer ·
33. Procedural Tree Lab · 34. Infinite Mechanical City · 35. Garden Through Four
Seasons · 36. Coral Reef Growth · 37. Crystal Growth Chamber · 38. Ant Colony ·
39. Procedural Roller Coaster (slope/curvature/G limits) · 40. 3D Factory Cutaway.

Image-grounded (need a vision lane — arena is text-only today): 41. Constellation
Creature · 42. City Photo Traffic · 43. Waterfall From a Painting · 44. Machine From
a Blueprint · 45. Museum Artifact Reconstruction · 46. Floor Plan to Living Building ·
47. Photo Relighting · 48. Cloud Weather Story.

Creative: 49. Self-Portrait in Different Media (animated process) · 50. Drawing That
Becomes Real · 51. Living Typography · 52. Musical Particle Instrument ·
53. Interactive Pop-Up Book · 54. Impossible Machine (Escher) · 55. Sand Art
Portrait · 56. Origami Simulator.

## Recommended Launch Set (12)

1. Angry Birds-style destruction game
2. Suspension bridge load test
3. Rube Goldberg machine
4. Lunar lander
5. Cargo crane
6. Four-cylinder engine
7. Solar-system orbital challenge
8. Cloth wind tunnel
9. Voxel creature printer
10. Animated garden
11. Image-to-animal drawing
12. Self-portrait drawing process

Mix: 2D+3D, objective+subjective, physics+aesthetics, short+long generation,
Canvas/SVG/WebGL, games+simulation+creative.

## Benchmarkability contract (from the brief)

Every submission exposes:

```js
window.BENCH = {
  reset(seed) {},
  step(milliseconds) {},
  perform(action, payload) {},
  getState() {},
  getMetrics() {}
};
```

Evaluator can: use deterministic seeds, trigger controls automatically, advance the
simulation, inspect positions/velocities/task state, verify completion, replay
identical scenarios across models. Stable selectors required:
`data-testid="reset"`, `data-testid="score"`, `data-testid="simulation"`.

Scoring dimensions: functional requirements · physics/simulation correctness ·
interaction/playability · visual quality · performance/stability ·
accessibility/responsiveness. Keep cost/tokens/completion time OUT of the quality
score; display together as a quality–efficiency frontier.

Design choice — capability vs framework:
- Model capability → preload the same libraries for everyone (Three.js + Rapier 3D,
  Matter.js 2D).
- End-to-end ability → any library, less numerically comparable physics.
- Creative tasks → Canvas/SVG/WebGL free, blind human voting.
- Strict physics → test invariants and final states, not screenshot similarity.
- Strongest version: 6 deterministic physics + 3 playable games + 3 open showcases.

---

## Implementation mapping (arena, 2026-09-18)

Already in place (no work needed):
- Blind A/B slots, one-shot voting, scoreboard → covers "blind human voting" for
  creative/subjective tasks.
- Speed/token metrics displayed separately from pass verdicts → quality–efficiency
  frontier already separated by design.
- Sandboxed artifact rendering (Preview tab, history side-by-side, CSP-sandboxed
  artifact route) → the "working visual system" viewing layer.
- DOM grading iframe with `dom_selectors`, `dom_no_errors`, `canvas_motion` →
  functional + stability dimensions.
- Challenge JSON library with per-task checks → tracks/categories map to the
  `category` field.

Built with this plan (v1):
- **`bench` check type** — the BENCH harness. A check is
  `{"type":"bench","steps":[{op:"reset",seed}|{op:"step",ms}|{op:"perform",action,payload}|{op:"wait",ms}],
  "assert":[{metric|state:"path", equals|min|max|near±tol}]}`. Runs inside the
  existing grading iframe; multiple bench checks run sequentially and may build on
  each other's state (intentional for staged scenarios like quake 3→8). Missing
  `window.BENCH` or timed-out scenarios fail explicitly (no silent passes).
- **Client-check routing fix** — `canvas_motion` was silently auto-failed server-side
  (unknown-type fallback) and never reached the browser grader. Routing now uses
  `is_client_check()` (`dom_*`, `canvas_motion`, `bench`) consistently in
  `run_server_checks`, `_recompute_pass`, the SSE `done` event and challenge counts.
- **First bench-scored challenges**: `double-pendulum` (chaos divergence + energy
  drift), `lunar-lander` (free-fall physics + thrust fuel burn), `earthquake-tower`
  (survive 3 / collapse 8 staged scenario). All pin the BENCH contract +
  `data-testid` selectors in the prompt.

Deferred / roadmap:
- **Library preloading** (pin Three.js/Rapier/Matter.js for everyone): v1 pins exact
  CDN URLs in prompts instead of harness injection (grading runs in the viewer's
  browser, which has internet; injected UMD + model-imported ESM can double-load).
  Revisit with a `preload` challenge field injecting scripts before page code.
- **Checkpoint scoring** (Rube Goldberg): needs per-check weighted scores, not just
  pass/fail — extend rates to a 0..1 score per check.
- **Image-grounded track (41–48)**: needs the vision lane (multimodal inputs); arena
  is text-only today.
- **Long-Horizon Construction**: needs multi-turn runs; arena is single-shot.
- **Hidden variants** (bridge/trebuchet): parameterize prompts per rep with seeds
  only revealed after voting.
- Perf/stability dimension: add frame-interval sampling to the grading shim
  (raf count already reported in canvas_motion results).
