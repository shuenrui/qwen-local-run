# arena — one prompt, every model

A zero-dependency local web app for comparing many Qwen models on one DGX
Spark. Type a prompt once, pick models, and arena runs them **serially** (one
model resident at a time — the unified-memory reality on a single Spark):

boot model → stream one reply live → record speed metrics → stop the model →
next. Answers appear side-by-side, like a mini Chatbot Arena for your box,
plus per-model TTFT / tok-s / totals and one-click export (Markdown/CSV/JSON).

## Why this exists
A 27B model with big context nearly fills the Spark's ~120 GB usable memory,
so multi-model comparison must serialize model lifecycle. Off-the-shelf chat
UIs (Open WebUI, LibreChat, …) assume all models are already reachable at
once and cannot orchestrate start→query→stop swaps — that's exactly what
`arena/server.py` does.

## Layout
- `arena/server.py` — backend. **Python stdlib only** (no pip): HTTP server,
  SSE streaming, job orchestration, model discovery, one-click downloads.
- `arena/static/` — **the front-end** (main target for UI work):
  `index.html`, `styles.css`, `app.js` (vanilla JS; markdown/code rendering
  is a small built-in renderer in `app.js`; no external libs, works offline).
- `arena/sync-launch.sh` — launcher for an NVIDIA Sync custom app; tunnels
  laptop `:8090` → Spark `:8090` and cleans up on stop.
- `profiles/*.env` — one recipe card per model (`MODEL_ID`, `CONTAINER_NAME`,
  `PORT`, `MEM_FRACTION_STATIC`, speculative settings…). Discovery is
  one-card-per-file: add a profile, it appears in the UI.
- `start-model.sh` / `start.sh` / `stop.sh` — shared SGLang launchers. The
  arena shells out to `start-model.sh <mtp|dspark>` with `PROFILE=<card>` and
  stops each model by its per-profile `CONTAINER_NAME`.
- `results/arena-<ts>/results.json` — every run is persisted on disk
  (prompt, options, full answers + reasoning, metrics). Intentionally not
  committed (personal benchmark data).

## Run
On the Spark:
```bash
python3 arena/server.py --port 8090
```
Open `http://localhost:8090`. From a laptop: `ssh -L 8090:localhost:8090
<user>@<spark-ip>` first (or the NVIDIA Sync custom app using
`arena/sync-launch.sh`).

## API contract (stable — safe to rebuild the UI on top of it)
All responses JSON. Model object (from `/api/models`):
`{id, label, name, served_model, container_name, port, model_id, engine,
cached, cached_gib, dl_status, dl_got_gib, dl_total_gib, dl_speed_mbs, dl_error}`
(`id` = profile path, e.g. `profiles/qwen3.8-27b.env`; `engine` = `sglang` or
`vllm` [manual-only lane]; `dl_status` = `""|downloading|done|error`).

| Endpoint | Meaning |
|---|---|
| `GET /api/models` | discovered models + live cache/download state |
| `POST /api/run` `{prompt, models:[profile id], thinking, max_tokens, temperature, engine:"mtp"\|"dspark", auto, challenge?, runs?}` | start a comparison → `202 {job_id, order}` — `order` is a **randomized blind key list** (`A`, or `A1,A2…` when `runs>1`); identity↔slot lives only in the job (`400` bad input; `409` one job at a time). With `challenge`, the file supplies prompt (unless overridden), options defaults, and the `checks` rubric |
| `POST /api/vote` `{job, pick:"A"…"K"\|"TIE"}` | lock in a blind preference vote after the run finishes (one per run, `409` on repeat or before completion); persisted as `votes.json` next to `results.json` |
| `GET /api/scores` | aggregate tally of every saved blind vote: `{rows:[{id,label,wins,ties,losses,votes,win_rate}]}` (ties count ½) |
| `GET /api/scores/export` | scoreboard as CSV attachment |
| `GET /api/challenges` | saved challenges from `arena/challenges/*.json`: `{challenges:[{id,name,category,prompt,thinking,max_tokens,temperature,engine,runs,checks,server_checks,dom_checks}]}` |
| `GET /api/runs` | summaries of every saved run: `{runs:[{name,prompt,models,challenge,vote,reconstructed,graded}]}` |
| `GET /api/runs/<name>` | a full saved job (read-only; powers the History view) |
| `GET /api/runs/<name>/export?fmt=md\|csv\|json` | re-export a past run without re-running models |
| `GET /api/runs/<name>/artifact/<key>` | serve a generated HTML artifact standalone (CSP-sandboxed, `inline`) |
| `POST /api/grade` `{job, key, checks:[{type,pass,…}]}` | the browser posts back DOM-check verdicts collected inside the sandboxed iframe; server stores them under `grades`, recomputes `passed`/`rates` and re-persists the run |
| `GET /api/jobs/<id>` | job snapshot: `{status, prompt, options…, results:[{id,label,status,ttft_s,total_s,tokens,estimated,toks_per_s,text,reasoning,error}]}` |
| `GET /api/jobs/<id>/stream` | SSE events, **keyed by blind slot only** (never the model id, so live streaming can't leak identity): `{type:"status",slot,status}`, `{type:"delta",slot,kind:"content"\|"reasoning",text}`, `{type:"done",slot,ttft_s,total_s,tokens,estimated,toks_per_s,text,reasoning}`, `{type:"error",slot,error}`, `{type:"job-done",saved_dir}`, `{type:"end"}` |
| `GET /api/jobs/<id>/export?fmt=md\|csv\|json` | download the run as attachment (all include full responses) |
| `POST /api/download` `{id}` | start a **resumable** model download → `202`; `409` if one is active. Runs as root inside a throwaway container (`huggingface_hub.snapshot_download`) because the shared HF cache is root-owned |
| `POST /api/cancel` `{id}` | stop the active download container |

## Front-end notes (for contributors)
- Keep `arena/static/` dependency-free: vanilla JS/CSS, no npm/CDN — the app
  must run offline on the Spark. If you add markdown/highlighting libs,
  vendor them under `arena/static/vendor/`.
- `app.js` state: `SELECTED` (Set of profile ids) drives checkbox restore
  across re-renders; `renderModels()` re-polls every 2 s only while a
  download is active; `openStream()` consumes SSE and drives per-model cards
  (`BUF` accumulates streamed text; `renderMarkdown` output is throttled
  ~80 ms; a cursor span marks streaming state).
- The picker intentionally **locks uncached models** (Download button, no
  checkbox) — a run can never boot a model that isn't fully on disk.
- Big models boot in ~1–2 min (weights + Triton cache are warm on this box);
  UI status badges (`starting → waiting-ready → running → done → stopped`)
  exist so the serial wait never looks frozen. Preserve that feedback.
- Backend restart wipes in-memory jobs, but every run persists to
  `results/arena-*/results.json` and the **History** panel can open/export
  those saved runs without re-running any model.

## Challenges & auto-grading
`arena/challenges/<id>.json`: `{id, name, category, prompt, thinking, max_tokens,
temperature, engine, runs (1–5), checks:[…]}`. The UI dropdown prefills from a
challenge; `runs: k` repeats each model (blind keys `A1..Ak`) and reports
**pass@1 / pass@k** (first attempt / any attempt). Check types:
- server-side: `contains`, `not_contains` (`ci` optional), `regex` (`flags:"i"`),
  `regex_count` (`equals`), `json_valid` (`keys`), `word_count` (`min`/`max`),
  `exec` (`lang:"python"` — runs the first fenced block inside a throwaway
  `docker run --network none --read-only --tmpfs /tmp` container)
- client-side (graded in a hidden sandbox iframe, posted to `POST /api/grade`):
  `dom_selectors` (`selectors:[…]`, each must match ≥1), `dom_no_errors`
A model that emits no runnable/parsable content simply fails those checks —
that is the point (see `docs/model-eval-plan.md`: keep failures visible).

## Testing without a GPU
`arena/tests/mock_model.py` is an OpenAI-compatible stand-in on `127.0.0.1:8899`.
Run the server with **`ARENA_RESULTS=results/_e2e`** (isolation guard — never
point it at real results), create throwaway profiles with `PORT=8899`, and
`POST /api/run` with `"auto": false` to exercise slots/SSE/checks/vote/grade/
history at full speed. E2E cleanup must delete only its own scratch dirs.

## What the UI renders today (and what it doesn't)
- **Input:** plain text only — the prompt box. No file/document upload.
- **Output:** built-in markdown renderer plus a tiny offline syntax highlighter
  (`hl()` in app.js: python/js keywords, strings, comments, numbers — no
  external libs). Generated websites run live in the per-card **Preview** tab
  (sandboxed iframe with runtime-error capture), and challenge DOM checks are
  graded there automatically; verdicts flow back via `POST /api/grade`.

## Remaining ideas (good next tasks)
1. **Diff view** between two cards' answers.
2. **GPU cost column** (power.draw sampling during runs) in results + history.
3. **Export bundle** (zip of md+csv+json per run) and shareable links.
4. A bigger vendored highlighter if the mini one falls short (vendor under
   `arena/static/vendor/`, stay offline).
