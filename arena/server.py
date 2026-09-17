#!/usr/bin/env python3
"""arena/server.py — local one-shot multi-model comparison server.

Stdlib only (no pip, no npm; ARM-safe). Runs on the DGX Spark; the browser
talks to it over 127.0.0.1. For each selected model it runs the model
SERIALLY (one resident at a time, the RAM reality on one Spark):

    start-model.sh -> wait ready -> stream one reply (live SSE to browser)
    -> record metrics -> docker stop/rm THAT model's container -> next

It stops each model by its per-profile CONTAINER_NAME, so it never depends on
the hardcoded-name stop.sh and always frees the GPU between models.

Endpoints:
  GET  /                      -> static/index.html
  GET  /static/<file>         -> assets
  GET  /api/models            -> discovered models + live cache status
  POST /api/run               -> {job_id} (202) | 409 busy | 400 bad input
  GET  /api/jobs/<id>         -> job snapshot (poll fallback)
  GET  /api/jobs/<id>/stream  -> SSE: status + token deltas + final metrics

Run body: {prompt, models:[profile ids], thinking, max_tokens, temperature,
           engine:"mtp"|"dspark", auto:true}

Usage:  python3 arena/server.py [--port 8090]
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # repo root
PROFILES_DIR = os.path.join(ROOT, "profiles")
STATIC_DIR = os.path.join(HERE, "static")
RESULTS_DIR = os.path.join(ROOT, "results")
HF_HUB = os.path.join(ROOT, ".cache", "huggingface", "hub")
# Downloads run as root inside a throwaway container: the HF cache is root-owned
# (the SGLang containers created it), so a host-side `hf download` cannot write
# its .locks. This image is already present locally and ships huggingface_hub.
DOWNLOAD_IMAGE = os.environ.get("ARENA_DL_IMAGE", "lmsysorg/sglang:qwen38-27b")

MAX_TOKEN_LIMIT = 5000
READY_TIMEOUT_S = 1200                            # model boot can be slow

jobs = {}
jobs_lock = threading.Lock()
run_lock = threading.Lock()                       # one active run at a time
job_seq = [0]

downloads = {}                                    # model_id -> {status, got, total, speed, error, pid}
dl_lock = threading.Lock()
_total_cache = {}                                 # model_id -> total bytes (memoized HF lookup)


# ----------------------------- model discovery -----------------------------

def load_profile(path):
    """Parse a profiles/*.env card into a dict (ignores comments/blanks)."""
    env = {}
    with open(path) as f:
        for ln in f:
            ln = ln.strip().rstrip("\r")
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            k = k.strip()
            if not k or " " in k:
                continue
            env[k] = v.strip().strip("'\"")
    return env


def hub_cache(model_id):
    """(has_weights, gib) for an HF repo id, measured from the local hub cache."""
    if "/" not in (model_id or ""):
        return False, 0.0
    org, name = model_id.split("/", 1)
    d = os.path.join(HF_HUB, f"models--{org}--{name}")
    if not os.path.isdir(d):
        return False, 0.0
    total, has = 0, False
    for dp, _, fns in os.walk(d):
        for fn in fns:
            if fn.endswith((".safetensors", ".bin", ".gguf", ".pt")):
                has = True
            try:
                total += os.path.getsize(os.path.join(dp, fn))
            except OSError:
                pass
    return has, round(total / 1024 ** 3, 1)


def discover_models():
    """One entry per profiles/*.env, with live cache state from disk."""
    out = []
    for path in sorted(glob.glob(os.path.join(PROFILES_DIR, "*.env"))):
        env = load_profile(path)
        rel = os.path.relpath(path, ROOT)
        stem = os.path.splitext(os.path.basename(path))[0]
        try:
            port = int(env.get("PORT", "8888"))
        except ValueError:
            port = 8888
        model_id = env.get("MODEL_ID", "")
        served = env.get("SERVED_MODEL_NAME", stem)
        cached, gib = hub_cache(model_id)
        with dl_lock:
            dl = dict(downloads.get(model_id, {}))
        out.append({
            "id": rel,
            "label": stem,
            "name": served,
            "served_model": served,
            "container_name": env.get("CONTAINER_NAME", served),
            "port": port,
            "model_id": model_id,
            "engine": env.get("ENGINE", "sglang"),
            "cached": cached,
            "cached_gib": gib,
            "dl_status": dl.get("status", ""),
            "dl_got_gib": round(dl.get("got", 0) / 1024 ** 3, 2),
            "dl_total_gib": round(dl.get("total", 0) / 1024 ** 3, 2),
            "dl_speed_mbs": round(dl.get("speed", 0) / 1024 ** 2, 1),
            "dl_error": dl.get("error", ""),
        })
    return out


# ----------------------------- model downloads -----------------------------

def _hf_token():
    """Resolve an HF token from env or ~/.bashrc (same rule as start.sh)."""
    tok = os.environ.get("HF_TOKEN")
    if tok:
        return tok
    import re
    try:
        with open(os.path.join(os.path.expanduser("~"), ".bashrc")) as f:
            for ln in f:
                m = re.match(r'\s*(?:export\s+)?HF_TOKEN=["\']?([A-Za-z0-9_-]+)', ln)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return ""


def model_total_bytes(model_id):
    """Total repo size (bytes) from the HF API, memoized. 0 if unknown."""
    if model_id in _total_cache:
        return _total_cache[model_id]
    total = 0
    try:
        tok = _hf_token()
        hdr = {"Authorization": f"Bearer {tok}"} if tok else {}
        req = urllib.request.Request(
            f"https://huggingface.co/api/models/{model_id}?blobs=true", headers=hdr)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        total = sum((s.get("size") or 0) for s in data.get("siblings", []))
    except Exception:
        total = 0
    _total_cache[model_id] = total
    return total


def cache_dir_bytes(model_id):
    """Bytes present locally for a repo (real files only; snapshots are symlinks)."""
    if "/" not in (model_id or ""):
        return 0
    org, name = model_id.split("/", 1)
    d = os.path.join(HF_HUB, f"models--{org}--{name}")
    total = 0
    for dp, _, fns in os.walk(d):
        for fn in fns:
            p = os.path.join(dp, fn)
            if os.path.islink(p):
                continue
            try:
                total += os.path.getsize(p)
            except OSError:
                pass
    return total


def free_bytes(path=ROOT):
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize
    except OSError:
        return 0


def _dl_log_path(model_id):
    return os.path.join(HERE, ".download-" + model_id.replace("/", "_") + ".log")


def _poll_download(model_id, proc):
    """Update progress every 2s; flip to done/error when the fetch exits."""
    last_got, last_t = cache_dir_bytes(model_id), time.time()
    while True:
        time.sleep(2)
        got = cache_dir_bytes(model_id)
        now = time.time()
        speed = max(0.0, (got - last_got) / max(now - last_t, 1e-6))
        last_got, last_t = got, now
        with dl_lock:
            st = downloads.get(model_id)
            if not st:
                return
            st["got"], st["speed"] = got, speed
        rc = proc.poll()
        if rc is not None:
            cached, _ = hub_cache(model_id)
            tail = ""
            try:
                with open(_dl_log_path(model_id), "rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(max(0, size - 600))
                    tail = f.read().decode("utf-8", "replace").strip()[-400:]
            except OSError:
                pass
            with dl_lock:
                st = downloads.get(model_id)
                if not st:
                    return
                if st.get("cancelled"):
                    downloads.pop(model_id, None)
                    return
                if rc == 0 and cached:
                    st["status"] = "done"
                    st["got"] = st.get("total") or got
                    st["speed"] = 0.0
                else:
                    st["status"] = "error"
                    st["error"] = tail or f"hf download exited with code {rc}"
            return


def _dl_container_name(model_id):
    return ("arena-dl-" + model_id.replace("/", "_").replace(".", "-"))[:62]


def start_download(model_id):
    """Fetch a repo as root in a throwaway container (the cache is root-owned).
    Resumable; one download at a time. Returns (ok, info_dict)."""
    with dl_lock:
        cur = downloads.get(model_id)
        if cur and cur["status"] in ("downloading", "done"):
            return True, dict(cur)
        busy = [m for m, s in downloads.items() if s["status"] == "downloading"]
    if busy:
        return False, {"error": f"a download is already active: {busy[0]}"}
    cached, _ = hub_cache(model_id)
    if cached:
        with dl_lock:
            downloads[model_id] = {"status": "done", "got": 0, "total": 0, "speed": 0.0, "error": ""}
        return True, dict(downloads[model_id])
    total = model_total_bytes(model_id)
    if total and free_bytes() < total * 1.15:
        return False, {"error": f"not enough disk free for ~{total / 1024 ** 3:.1f} GB"}
    hf_home_host = os.path.join(ROOT, ".cache", "huggingface")
    cname = _dl_container_name(model_id)
    subprocess.run(["docker", "rm", "-f", cname], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cmd = ["docker", "run", "--rm", "--name", cname, "--network", "host",
           "-v", hf_home_host + ":/root/.cache/huggingface",
           "-e", "HF_HOME=/root/.cache/huggingface",
           "-e", "ARENA_REPO=" + model_id]
    tok = _hf_token()
    if tok:
        cmd += ["-e", "HF_TOKEN=" + tok]
    cmd += ["--entrypoint", "python3", DOWNLOAD_IMAGE, "-c",
            "import os;from huggingface_hub import snapshot_download;"
            "snapshot_download(os.environ['ARENA_REPO'])"]
    logf = open(_dl_log_path(model_id), "wb")
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=logf, stderr=subprocess.STDOUT,
                                start_new_session=True)
    except Exception as e:
        logf.close()
        return False, {"error": f"failed to launch download container: {e}"}
    with dl_lock:
        downloads[model_id] = {"status": "downloading", "got": cache_dir_bytes(model_id),
                               "total": total, "speed": 0.0, "error": "",
                               "pid": proc.pid, "container": cname}
    threading.Thread(target=_poll_download, args=(model_id, proc), daemon=True).start()
    return True, dict(downloads[model_id])


def cancel_download(model_id):
    """Stop an in-flight download container (resumable later)."""
    with dl_lock:
        st = downloads.get(model_id)
        pid = (st or {}).get("pid")
        cname = (st or {}).get("container")
        if st:
            st["cancelled"] = True
            st["speed"] = 0.0
    if cname:
        try:
            subprocess.run(["docker", "stop", cname], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        except Exception:
            pass
    if pid:
        try:
            os.killpg(os.getpgid(pid), 15)
        except Exception:
            try:
                os.kill(pid, 15)
            except Exception:
                pass
    return True


# ------------------------------- job runner --------------------------------

def add_event(job, ev):
    """Append an event to the job's SSE log (consumed by /stream tails)."""
    ev["seq"] = len(job["events"])
    job["events"].append(ev)


def wait_ready(port, timeout_s=READY_TIMEOUT_S):
    url = f"http://127.0.0.1:{port}/v1/models"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


def stop_container(name):
    """Stop + remove this model's container so the GPU frees for the next."""
    for action in ("stop", "rm"):
        try:
            subprocess.run(["docker", action, name], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=180)
        except Exception:
            pass


def stream_chat(job, item, port, served_model, prompt, thinking, max_tokens, temperature):
    """Stream one reply, pushing token deltas as SSE events. Returns metrics."""
    body = {
        "model": served_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": thinking},
    }
    if temperature is not None:
        body["temperature"] = temperature
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    first = None
    parts, reasoning = [], []
    usage_tokens = None
    with urllib.request.urlopen(req, timeout=900) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except Exception:
                continue
            if obj.get("usage"):
                usage_tokens = obj["usage"].get("completion_tokens", usage_tokens)
            for ch in obj.get("choices", []):
                delta = ch.get("delta") or {}
                rc, ct = delta.get("reasoning_content"), delta.get("content")
                if rc:
                    if first is None:
                        first = time.time()
                    reasoning.append(rc)
                    add_event(job, {"type": "delta", "model": item["id"],
                                    "kind": "reasoning", "text": rc})
                if ct:
                    if first is None:
                        first = time.time()
                    parts.append(ct)
                    add_event(job, {"type": "delta", "model": item["id"],
                                    "kind": "content", "text": ct})
    total = time.time() - t0
    text = "".join(parts)
    estimated = False
    if usage_tokens is None:                        # fallback, flagged
        usage_tokens = len(text.split())
        estimated = True
    return {"text": text, "reasoning": "".join(reasoning),
            "ttft_s": round((first or time.time()) - t0, 2),
            "total_s": round(total, 2), "tokens": usage_tokens,
            "estimated": estimated}


def run_job(job):
    try:
        for item in job["results"]:
            if job.get("cancel"):
                item["status"] = "skipped"
                add_event(job, {"type": "status", "model": item["id"], "status": "skipped"})
                continue
            cname, port = item["container_name"], item["port"]
            item["status"] = "starting"
            add_event(job, {"type": "status", "model": item["id"], "status": "starting"})
            try:
                if job["auto"]:
                    if item.get("engine", "sglang") != "sglang":
                        raise RuntimeError(
                            "manual-only lane (ENGINE=%s): boot it yourself, "
                            "then rerun with auto OFF" % item.get("engine"))
                    prof = os.path.join(ROOT, item["id"])
                    env = dict(os.environ, PROFILE=prof)
                    eng = job["engine"]
                    if "35b" in (item.get("model_id", "").lower()) and eng == "dspark":
                        eng = "mtp"                 # dspark draft is 3.8-only
                    subprocess.run(["bash", os.path.join(ROOT, "start-model.sh"), eng],
                                   cwd=ROOT, env=env, check=True)
                    item["status"] = "waiting-ready"
                    add_event(job, {"type": "status", "model": item["id"], "status": "waiting-ready"})
                    if not wait_ready(port):
                        raise RuntimeError("server never became ready")
                item["status"] = "running"
                add_event(job, {"type": "status", "model": item["id"], "status": "running"})
                m = stream_chat(job, item, port, item["served_model"], job["prompt"],
                                job["thinking"], job["max_tokens"], job["temperature"])
                item.update(m, status="done")
                item["toks_per_s"] = round(m["tokens"] / max(m["total_s"], 1e-6), 1)
                add_event(job, {"type": "done", "model": item["id"],
                                "ttft_s": m["ttft_s"], "total_s": m["total_s"],
                                "tokens": m["tokens"], "estimated": m["estimated"],
                                "toks_per_s": item["toks_per_s"],
                                "text": m["text"], "reasoning": m.get("reasoning", "")})
            except Exception as e:                  # surface to the model's card
                item["status"] = "error"
                item["error"] = str(e)[:500]
                add_event(job, {"type": "error", "model": item["id"], "error": item["error"]})
            finally:
                if job["auto"]:
                    stop_container(cname)
                    add_event(job, {"type": "status", "model": item["id"], "status": "stopped"})
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        saved = os.path.join(RESULTS_DIR, f"arena-{stamp}")
        os.makedirs(saved, exist_ok=True)
        with open(os.path.join(saved, "results.json"), "w") as f:
            json.dump({k: v for k, v in job.items() if k != "events"}, f, indent=2)
        job["saved_dir"] = os.path.relpath(saved, ROOT)
        job["status"] = "done"
        add_event(job, {"type": "job-done", "saved_dir": job["saved_dir"]})
    finally:
        run_lock.release()


# ------------------------------- export ------------------------------------

def build_export(job, fmt):
    """Render a finished job as md | csv | json. Returns (filename, mime, text).
    All three include the full per-model response text."""
    import io
    import csv as _csv
    res = job.get("results", [])
    stamp = (job.get("saved_dir") or job.get("id", "run")).split("/")[-1]
    base = stamp if stamp.startswith("arena-") else "arena-" + stamp

    if fmt == "json":
        return base + ".json", "application/json", json.dumps(job, indent=2)

    if fmt == "csv":
        buf = io.StringIO()
        w = _csv.writer(buf)
        w.writerow(["model", "status", "ttft_s", "total_s", "toks_per_s",
                    "tokens", "estimated", "error", "response"])
        for r in res:
            w.writerow([r.get("label") or r.get("name"), r.get("status"),
                        r.get("ttft_s", ""), r.get("total_s", ""),
                        r.get("toks_per_s", ""), r.get("tokens", ""),
                        "yes" if r.get("estimated") else "",
                        r.get("error", ""), r.get("text", "")])
        return base + ".csv", "text/csv", buf.getvalue()

    # markdown report (default): summary + full side-by-side responses
    L = ["# Arena comparison", ""]
    L.append("- **Prompt:** " + (job.get("prompt", "").replace("\n", " ") or "_none_"))
    temp = job.get("temperature")
    L.append("- **Options:** thinking=%s · max_tokens=%s · engine=%s · temperature=%s"
             % (bool(job.get("thinking")), job.get("max_tokens"), job.get("engine"),
                "default" if temp is None else temp))
    if job.get("saved_dir"):
        L.append("- **Saved:** " + job["saved_dir"])
    L += ["", "## Summary", "",
          "| model | status | TTFT (s) | total (s) | tok/s | tokens |",
          "|---|---|---|---|---|---|"]
    for r in res:
        L.append("| %s | %s | %s | %s | %s | %s |" % (
            r.get("label") or r.get("name"), r.get("status"),
            r.get("ttft_s", "—"), r.get("total_s", "—"),
            r.get("toks_per_s", "—"), r.get("tokens", "—")))
    L += ["", "## Responses"]
    for r in res:
        meta = r.get("status", "")
        extras = []
        if r.get("toks_per_s"):
            extras.append("%s tok/s" % r["toks_per_s"])
        if r.get("ttft_s") is not None:
            extras.append("TTFT %ss" % r["ttft_s"])
        if r.get("tokens") is not None:
            extras.append("%s tokens" % r["tokens"])
        if extras:
            meta += " · " + " · ".join(extras)
        L += ["", "### %s" % (r.get("label") or r.get("name")), "_%s_" % meta, ""]
        if r.get("error"):
            L.append("> ⚠ " + r["error"].replace("\n", " "))
            continue
        if r.get("reasoning"):
            L += ["<details><summary>thinking</summary>", "", r["reasoning"],
                  "", "</details>", ""]
        L.append(r.get("text", ""))
    return base + ".md", "text/markdown", "\n".join(L)


# ------------------------------- http server -------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "Arena/1.0"
    protocol_version = "HTTP/1.1"                   # keep-alive + SSE

    def _send(self, code, ctype, data):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, "application/json", json.dumps(obj).encode())

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._static("index.html", "text/html")
        if path.startswith("/static/"):
            return self._static(path[len("/static/"):], None)
        if path == "/api/models":
            return self._json(200, {"models": discover_models()})
        if path.startswith("/api/jobs/"):
            rest = path[len("/api/jobs/"):]
            fmt = (parse_qs(urlparse(self.path).query).get("fmt") or ["md"])[0]
            if rest.endswith("/export"):
                return self._export(rest[:-len("/export")], fmt)
            if rest.endswith("/stream"):
                return self._sse(rest[:-len("/stream")])
            return self._snapshot(rest)
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/download":
            return self._download()
        if path == "/api/cancel":
            return self._cancel()
        if path != "/api/run":
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "invalid JSON"})
        prompt = (body.get("prompt") or "").strip()
        models = body.get("models") or []
        if not prompt:
            return self._json(400, {"error": "prompt is empty"})
        if not models:
            return self._json(400, {"error": "no models selected"})
        try:
            max_tokens = max(1, min(int(body.get("max_tokens", 2000)), MAX_TOKEN_LIMIT))
        except (TypeError, ValueError):
            max_tokens = 2000
        known = {m["id"]: m for m in discover_models()}
        for mid in models:
            if mid not in known:
                return self._json(400, {"error": f"unknown model '{mid}'"})
        if not run_lock.acquire(blocking=False):
            return self._json(409, {"error": "a run is already active"})
        with jobs_lock:
            job_seq[0] += 1
            jid = f"job-{job_seq[0]}"
            job = {"id": jid, "status": "running", "prompt": prompt,
                   "thinking": bool(body.get("thinking", False)),
                   "max_tokens": max_tokens,
                   "temperature": body.get("temperature"),
                   "auto": bool(body.get("auto", True)),
                   "engine": (body.get("engine") or "mtp"),
                   "events": [],
                   "results": [{"id": mid, "name": known[mid]["name"],
                                "label": known[mid]["label"],
                                "served_model": known[mid]["served_model"],
                                "container_name": known[mid]["container_name"],
                                "port": known[mid]["port"],
                                "model_id": known[mid]["model_id"],
                                "engine": known[mid].get("engine", "sglang"),
                                "status": "queued"} for mid in models]}
            jobs[jid] = job
        threading.Thread(target=run_job, args=(job,), daemon=True).start()
        return self._json(202, {"job_id": jid})

    def _download(self):
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "invalid JSON"})
        mid = (body.get("id") or "").strip()
        models = discover_models()
        by_mid = {m["model_id"]: m for m in models}
        by_id = {m["id"]: m for m in models}
        if mid in by_id and mid not in by_mid:
            mid = by_id[mid]["model_id"]
        if mid not in by_mid:
            return self._json(400, {"error": f"unknown model '{mid}'"})
        if by_mid[mid]["engine"] != "sglang":
            return self._json(400, {"error": "manual-only lane: fetch/boot it from its own repo"})
        ok, info = start_download(mid)
        if not ok:
            return self._json(409, info)
        return self._json(202, {"model_id": mid, "status": info.get("status", "downloading")})

    def _cancel(self):
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "invalid JSON"})
        mid = (body.get("id") or "").strip()
        models = discover_models()
        by_mid = {m["model_id"]: m for m in models}
        by_id = {m["id"]: m for m in models}
        if mid in by_id and mid not in by_mid:
            mid = by_id[mid]["model_id"]
        if mid not in by_mid:
            return self._json(400, {"error": f"unknown model '{mid}'"})
        cancel_download(mid)
        return self._json(200, {"cancelled": mid})

    def _snapshot(self, jid):
        with jobs_lock:
            job = jobs.get(jid)
        if job is None:
            return self._json(404, {"error": "unknown job"})
        return self._json(200, {k: v for k, v in job.items() if k != "events"})

    def _export(self, jid, fmt):
        with jobs_lock:
            job = jobs.get(jid)
        if job is None:
            return self._json(404, {"error": "unknown job"})
        try:
            fname, mime, content = build_export(job, fmt)
        except Exception as e:
            return self._json(500, {"error": f"export failed: {e}"})
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="%s"' % fname)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _sse(self, jid):
        with jobs_lock:
            job = jobs.get(jid)
        if job is None:
            return self._json(404, {"error": "unknown job"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        idx = 0
        try:
            while True:
                with jobs_lock:
                    evs = job["events"][idx:]
                    done = (job["status"] == "done")
                if evs:
                    idx += len(evs)
                    blob = "".join("data: " + json.dumps(e) + "\n\n" for e in evs)
                    self.wfile.write(blob.encode())
                    self.wfile.flush()
                elif done:
                    self.wfile.write(b'data: {"type":"end"}\n\n')
                    self.wfile.flush()
                    break
                else:
                    time.sleep(0.15)
        except Exception:
            pass                                    # client disconnected

    def _static(self, name, ctype):
        if ".." in name or name.startswith("/"):
            return self._json(400, {"error": "bad path"})
        path = os.path.join(STATIC_DIR, name)
        if not os.path.isfile(path):
            return self._json(404, {"error": "not found"})
        if ctype is None:
            ctype = ("text/html" if name.endswith(".html") else
                     "application/javascript" if name.endswith(".js") else
                     "text/css" if name.endswith(".css") else
                     "application/octet-stream")
        with open(path, "rb") as f:
            data = f.read()
        self._send(200, ctype + "; charset=utf-8", data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(line_buffering=True)   # live logs when piped/redirected
    except Exception:
        pass
    found = discover_models()
    print(f"profiles: {PROFILES_DIR}")
    for m in found:
        flag = "cached" if m["cached"] else "NEEDS DOWNLOAD"
        print(f"  - {m['label']:28s} {m['container_name']:30s} {flag}")
    print(f"open http://localhost:{args.port}/")
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
