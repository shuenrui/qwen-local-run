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
| `POST /api/run` `{prompt, models:[profile id], thinking, max_tokens, temperature, engine:"mtp"\|"dspark", auto}` | start a comparison → `202 {job_id, order}` — `order` is a **randomized blind slot list** (`A`,`B`,…); identity↔slot lives only in the job (`400` bad input; `409` one job at a time) |
| `POST /api/vote` `{job, pick:"A"…"K"\|"TIE"}` | lock in a blind preference vote after the run finishes (one per run, `409` on repeat or before completion); persisted as `votes.json` next to `results.json` |
| `GET /api/scores` | aggregate tally of every saved blind vote: `{rows:[{id,label,wins,ties,losses,votes,win_rate}]}` (ties count ½) |
| `GET /api/scores/export` | scoreboard as CSV attachment |
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
- Backend restart wipes in-memory jobs: exports work for runs of the current
  session; older runs live in `results/arena-*/results.json` (a History view
  reading them is a natural next feature).

## What the UI renders today (and what it doesn't)
- **Input:** plain text only — the prompt box. No file/document upload.
- **Output:** each response goes through the built-in markdown renderer in
  `app.js`: headings, lists, links, bold/italic, inline code, fenced code
  blocks (styled, with copy button). **No** syntax-highlight colors, and code
  is never executed — a model that generates a whole website gives you its
  HTML/CSS/JS as text, not a live page.

## Suggested front-end tasks (roughly by value)
1. **Sandboxed HTML preview**: when a response contains a full document or an
   `html`-tagged fence, add a per-card *Preview* tab that renders it in
   `<iframe sandbox="allow-scripts" srcdoc=…>` (never `allow-same-origin` —
   keeps generated code out of the app's origin). CDN-referenced assets won't
   load (offline box), so also show a “assets may not load offline” hint.
2. **Run History browser**: list `results/arena-*/results.json`, open/export
   any past run without re-running models.
3. **Syntax highlighting**: vendor highlight.js into `arena/static/vendor/`
   (offline-first) and hook it into the fenced-code renderer.
4. **Winner vote & tally**: per-prompt pick-best + running scoreboard (uses
   the existing job data; store votes alongside results.json).
5. **Diff view**: side-by-side word-diff between two cards' answers.
