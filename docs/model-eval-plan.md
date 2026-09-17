# Model Evaluation Plan — arena roadmap

> Source: evaluation brief assembled 2026-09-17 (past analysis of public X/Twitter
> model-comparison demos + standard benchmark literature). Kept verbatim as the
> product north-star for the arena app. Feasibility tiers for ONE DGX Spark
> (single GB10, ~120 GB usable, serial model swaps, offline serving) are added
> by the repo maintainers in "Implementation tiers" at the bottom.

## What Each Tweet Tests
Test | Main capability | What is measured | Main weakness
Angry Birds game (x.com/gmi_cloud/status/2093103673413132411) | One-shot frontend coding | Playability, browser physics, visuals, completion time, API cost | One prompt, subjective "same quality," no repeated runs
AI self-portrait (x.com/TypingMindApp/status/2093211668700700812) | Creative frontend generation | HTML/Canvas/SVG skill, animation, art direction, interpretation, instruction following | "Most handsome" is entirely subjective
Cloud animal (x.com/ann_nnng/status/2084188390019502360) | Multimodal image-to-code | Visual grounding, imagination, HTML drawing, animation, constraint following | No objective correctness target
Construction simulation (x.com/thehypedotnews/status/2093412212782301267) | Long-horizon agent behavior | Planning, tool use, physics constraints, recovery, cost, task completion | Models judged their own completion; one approved an empty bridge

### 1. Angry Birds Game
Same broad assignment to Qwen 3.8 Flash and Max: build a complete browser-based
physics game in one shot. Tests frontend/JS generation, physics, product
completeness, visual polish, long-task coherence, time and inference cost.
Reported: Flash 52 min / $0.70 (richer material physics); Max 99 min / $4.20
(more polished). "Same quality" not established without rubric + repeats.

### 2. Self-Portrait
Animated HTML self-portrait that develops like a hand-drawn sketch. Tests
creative interpretation, HTML/Canvas/SVG, animation sequencing, composition,
aesthetic constraint following, originality. Treat as showcase unless scored on:
renders? animated process? pencil visible? construction lines? responsive?
replay works? human preference for aesthetics.

### 3. Cloud Animal
Photo of clouds -> discover animal shape -> animated HTML illustration aligned
to the photo. Tests image understanding, spatial grounding, creative
interpretation, image-to-code, SVG/Canvas animation, constraint adherence
(supplied background, exactly one animal, stroke-by-stroke animation, cursor
shown, no UI except Replay). Score: background preserved / one animal /
spatial overlap / replay / no forbidden elements / human resemblance preference.

## Use Two Evaluation Layers
### Objective Benchmarks (verifiable -> defensible scores)
Correct multiple-choice; unit tests pass; repo issue resolved; correct function
calls; required DOM elements exist; agent reaches specified environment state.
### Showcases and Human Preference (no single right answer)
Website design, games, illustrations, writing style, creative interpretation,
UI polish -> blinded human voting + rubrics, NOT accuracy percentages.
Calling both "benchmarks" without distinguishing them will mislead users.

## Recommended Benchmark Suite
Category | Tests | Reveals
General knowledge | MMLU-Pro | broad academic knowledge/reasoning
Hard reasoning | GPQA Diamond | difficult scientific reasoning
Mathematics | AIME, MATH-500 | competition math, exact answers
Coding problems | LiveCodeBench | fresh codegen, execution, repair
Software engineering | SWE-bench Verified | resolving real GitHub issues
Instruction following | IFEval | precise verifiable constraints
Vision reasoning | MMMU-Pro | charts, diagrams, images, expert material
Long context | LongBench v2 | documents, repos, long conversations
Tool calling | BFCL | tool selection + correct arguments
Interactive agents | tau-bench | conversations, policy compliance, DB actions
Computer/terminal agents | Terminal-Bench | realistic terminal tasks
Human preference | Arena-style blind voting | subjective quality
Safety | HarmBench, StrongREJECT, XSTest | compliance, refusal quality, over-refusal

First version suggestion (9): MMLU-Pro or GPQA; AIME; LiveCodeBench; IFEval;
MMMU-Pro; BFCL; five custom real-world challenges; blind user voting;
cost + latency telemetry.

## Custom Challenges (tweet-style)
1 responsive dashboard from brief; 2 playable browser game w/ specified
mechanics; 3 reproduce supplied screenshot; 4 image->animation interpretation;
5 multi-PDF document QA; 6 product research -> structured results; 7 repair
deliberately broken app; 8 CSV -> correct charts; 9 multi-step sandbox agent
task; 10 content under 10-20 simultaneous testable rules.

### Auto-scored for frontend output
build success; runtime errors; functional interactions; DOM requirements;
mobile responsiveness; accessibility checks; screenshot similarity (when
reference exists); task completion time; input/output tokens; total cost.
### Plus blinded human judgments
visual quality; usability; originality; overall preference.

## Testing Protocol
1 identical system prompt/tools/environment; 2 publish prompt + rubric;
3 record exact model version/provider/date; 4 comparable reasoning budget,
temperature, token limits; 5 creative tasks >= 3 runs; 6 agent tasks 5-10
runs; 7 report pass@1 not best attempt; 8 blind + randomize names in voting;
9 swap positions for LLM judges; 10 track latency/speed/tokens/cost separately
from quality; 11 keep failures visible; 12 private rotating test set vs
contamination.

## Avoid One Overall Score
Show category scores; users apply their own weights. At most named profiles:
best for coding / visual creation / agents / reasoning / best value / fastest /
most reliable.

The strongest differentiator for the arena app: combining standard benchmark
data, reproducible real-world challenges, side-by-side artifacts, blind
preference voting, and transparent cost/latency telemetry.

Sources checked through 2026-09-17: original tweets + disclosed prompts,
SWE-bench, LiveCodeBench, IFEval, MMMU, LongBench v2, BFCL, tau-bench,
Terminal-Bench, Stanford HELM.

---

## Implementation tiers (repo maintainers' feasibility notes — ONE Spark)
Hardware reality: one ~27B model resident at a time (boot ~1-2 min serial),
offline serving, 262K ctx, NVFP4 quantization. Scores are *local-model* scores,
not cloud-equivalent.

**Tier A — build in arena now (no GPU conflict, pure app work)**
- Blind voting + scoreboard + randomized positions (protocol #8/#9).
- Sandboxed iframe artifact runner: build-success, runtime-error capture,
  DOM-requirement assertions, responsive reflow check, replay checks.
- Challenge library: prompt + rubric + machine-checkable assertions as YAML;
  runs=k -> pass@1; failures preserved; telemetry panel (tokens/TTFT/tok-s/
  wall time/GPU power via nvidia-smi as local "cost" proxy).
- Category scorecards + named profiles (no aggregate score).

**Tier B — via API harnesses pointed at our own endpoint (offline-capable
once datasets are downloaded; run outside the UI; token budget may exceed the
UI's 5000 cap)**
- IFEval (strict, verifiable, small) — best first objective suite.
- GPQA-Diamond / MMLU-Pro subsets via lm-evaluation-harness (openai-compat).
- AIME/MATH-500 with sympy/math_verify checker (thinking mode ON; long budgets).
- BFCL-style tool-call grading against the served `qwen3_coder` parser.
- LiveCodeBench subset: needs sandboxed `docker run python` executor (we
  already run docker) + fresh-problem downloads.

**Tier C — defer (too heavy or mismatched for one Spark / current models)**
- SWE-bench Verified, tau-bench, Terminal-Bench (long agent loops x many
  instances x serial boot = days; revisit with 2-clustered Sparks).
- MMMU-Pro / cloud-animal image-to-code (served Qwen3.8-27B is text-only;
  needs a vision lane, e.g. the vLLM manual profiles).
- LongBench v2 at full length (later; KV budget collides with 5000-token outs).
- Safety suites (HarmBench/StrongREJECT/XSTest) — valuable, but a project of
  their own; XSTest (over-refusal) could be an early cheap subset.
