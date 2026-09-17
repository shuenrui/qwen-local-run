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
import random
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # repo root
PROFILES_DIR = os.path.join(ROOT, "profiles")
STATIC_DIR = os.path.join(HERE, "static")
# Tests MUST point ARENA_RESULTS at a scratch dir so e2e cleanup can never
# touch real saved runs (see arena/tests/mock_model.py usage in README).
RESULTS_DIR = os.path.abspath(os.environ.get("ARENA_RESULTS", os.path.join(ROOT, "results")))
CH_DIR = os.path.join(HERE, "challenges")
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
                    add_event(job, {"type": "delta", "slot": item["key"],
                                    "kind": "reasoning", "text": rc})
                if ct:
                    if first is None:
                        first = time.time()
                    parts.append(ct)
                    add_event(job, {"type": "delta", "slot": item["key"],
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


# --------------------- challenges, checks, grading --------------------------

def list_challenges():
    out = []
    for path in sorted(glob.glob(os.path.join(CH_DIR, "*.json"))):
        try:
            with open(path) as f:
                c = json.load(f)
        except (OSError, ValueError):
            continue
        checks = c.get("checks") or []
        c["server_checks"] = sum(1 for ch in checks if not str(ch.get("type", "")).startswith("dom_"))
        c["dom_checks"] = sum(1 for ch in checks if str(ch.get("type", "")).startswith("dom_"))
        out.append(c)
    return out


def load_challenge(cid):
    cid = str(cid or "")
    if not re.fullmatch(r"[\w.-]+", cid):
        return None
    path = os.path.join(CH_DIR, cid + ".json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def first_code(text, lang="python"):
    m = re.search(r"```" + re.escape(lang) + r"\s*\n([\s\S]*?)```", text or "", re.I)
    if not m:
        m = re.search(r"```(?:[\w+-]*)\s*\n([\s\S]*?)```", text or "")
    return m.group(1) if m else None


def _exec_python(code, timeout=45):
    """Run model code in a throwaway container (no net, read-only fs)."""
    try:
        p = subprocess.run(
            ["docker", "run", "-i", "--rm", "--network", "none", "--read-only",
             "--tmpfs", "/tmp", DOWNLOAD_IMAGE, "python3", "-I", "-"],
            input=code.encode(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout)
        return p.returncode == 0, p.stdout.decode("utf-8", "replace")[-300:]
    except Exception as e:
        return False, str(e)[:300]


def _recompute_pass(item):
    sigs = []
    if item.get("server_ok") is not None:
        sigs.append(bool(item["server_ok"]))
    dom = any(str(c.get("type", "")).startswith("dom_") for c in item.get("checks", []))
    if dom:
        if item.get("dom_pass") is None:
            item["passed"] = None               # waiting for client-side grade
            return
        sigs.append(bool(item["dom_pass"]))
    item["passed"] = all(sigs) if sigs else None


def run_server_checks(item, prompt, max_tokens):
    """Evaluate every non-dom check against item['text']; update passed state."""
    details, dom_any = [], False
    text = item.get("text", "") or ""
    for ch in item.get("checks", []):
        t = str(ch.get("type", ""))
        ok, extra = False, {}
        if t.startswith("dom_"):
            dom_any = True
            continue
        try:
            if t == "contains":
                ok = (ch.get("value", "") in text) if not ch.get("ci") else \
                     (ch.get("value", "").lower() in text.lower())
            elif t == "not_contains":
                ok = (ch.get("value", "") not in text) if not ch.get("ci") else \
                     (ch.get("value", "").lower() not in text.lower())
            elif t == "regex":
                ok = re.search(ch.get("value", ""), text,
                               re.I if "i" in str(ch.get("flags", "")) else 0) is not None
            elif t == "regex_count":
                ok = len(re.findall(ch.get("value", ""), text, re.M)) == int(ch.get("equals"))
            elif t == "json_valid":
                mt = re.search(r"\{[\s\S]*\}", text)
                try:
                    obj = json.loads(mt.group(0)) if mt else None
                    ok = isinstance(obj, dict) and all(k in obj for k in ch.get("keys", []))
                except ValueError:
                    ok = False
            elif t == "word_count":
                n = len(text.split())
                ok = int(ch.get("min", 0)) <= n <= int(ch.get("max", 10 ** 9))
                extra = {"n": n}
            elif t == "exec":
                code = first_code(text, ch.get("lang", "python"))
                if not code:
                    ok, extra["out"] = False, "no fenced code found"
                else:
                    ok, out = _exec_python(code)
                    extra["out"] = out
            else:
                ok = False
        except (re.error, ValueError):
            ok = False
        d = {"type": t, "pass": bool(ok)}
        d.update(extra)
        details.append(d)
    item["checks_detail"] = details
    item["server_ok"] = (all(d["pass"] for d in details) if details else None)
    item["dom_pending"] = dom_any and item.get("dom_pass") is None
    _recompute_pass(item)


def compute_rates(job):
    rates = {}
    for r in job["results"]:
        e = rates.setdefault(r["slot"], {"k": 0, "pass1": False, "any": False,
                                         "n_pass": 0, "pending": 0})
        e["k"] += 1
        if r.get("rep", 1) == 1:
            e["pass1"] = bool(r.get("passed"))
        if r.get("passed") is True:
            e["any"] = True
            e["n_pass"] += 1
        elif r.get("passed") is None and (r.get("checks") or []):
            e["pending"] += 1
    return rates


def merge_dom_grades(job):
    for item in job["results"]:
        g = (job.get("grades") or {}).get(item["key"])
        if g:
            item["dom_checks"] = g.get("checks", [])
            item["dom_pass"] = bool(g.get("pass"))
        _recompute_pass(item)


def _persist_job(job, saved=None):
    saved = saved or os.path.join(ROOT, job.get("saved_dir", RESULTS_DIR))
    try:
        os.makedirs(saved, exist_ok=True)
        with open(os.path.join(saved, "results.json"), "w") as f:
            json.dump({k: v for k, v in job.items() if k != "events"}, f, indent=2)
    except Exception:
        traceback.print_exc()
        sys.stderr.write("[arena] FAILED to persist run to %s\n" % saved)


def list_runs():
    out = []
    for d in sorted(glob.glob(os.path.join(RESULTS_DIR, "arena-*")), reverse=True):
        try:
            with open(os.path.join(d, "results.json")) as f:
                j = json.load(f)
        except (OSError, ValueError):
            continue
        rs = j.get("results", [])
        vote = None
        try:
            with open(os.path.join(d, "votes.json")) as f:
                pick = (json.load(f) or {}).get("pick")
            if pick:
                vote = "tie" if pick == "TIE" else next(
                    (r.get("label") for r in rs if r.get("slot") == pick), pick)
        except (OSError, ValueError):
            pass
        out.append({"name": os.path.basename(d),
                    "prompt": (j.get("prompt") or "")[:110],
                    "models": sorted({(r.get("label") or r.get("name") or "") for r in rs}),
                    "challenge": j.get("challenge"), "vote": vote,
                    "reconstructed": bool(j.get("reconstructed")),
                    "graded": any(r.get("passed") is not None for r in rs)})
    return out


def run_job(job):
    try:
        groups = []
        for it in job["results"]:
            if not groups or groups[-1][0] != it["slot"]:
                groups.append((it["slot"], []))
            groups[-1][1].append(it)
        for slot, items in groups:
            first = items[0]
            port, cname = first["port"], first["container_name"]
            try:
                if job.get("cancel"):
                    raise RuntimeError("cancelled before this model")
                if job["auto"]:
                    if first.get("engine", "sglang") != "sglang":
                        raise RuntimeError("manual-only lane (ENGINE=%s): boot it yourself, "
                                           "then rerun with auto OFF" % first.get("engine"))
                    for it in items:
                        it["status"] = "starting"
                        add_event(job, {"type": "status", "slot": it["key"], "status": "starting"})
                    prof = os.path.join(ROOT, first["id"])
                    env = dict(os.environ, PROFILE=prof)
                    eng = job["engine"]
                    if "35b" in (first.get("model_id", "").lower()) and eng == "dspark":
                        eng = "mtp"
                    subprocess.run(["bash", os.path.join(ROOT, "start-model.sh"), eng],
                                   cwd=ROOT, env=env, check=True)
                    for it in items:
                        it["status"] = "waiting-ready"
                    add_event(job, {"type": "status", "slot": items[-1]["key"], "status": "waiting-ready"})
                    if not wait_ready(port):
                        raise RuntimeError("server never became ready")
                for it in items:
                    it["status"] = "running"
                    add_event(job, {"type": "status", "slot": it["key"], "status": "running"})
                    try:
                        m = stream_chat(job, it, port, it["served_model"], job["prompt"],
                                        job["thinking"], job["max_tokens"], job["temperature"])
                        it.update(m, status="done")
                        it["toks_per_s"] = round(m["tokens"] / max(m["total_s"], 1e-6), 1)
                        run_server_checks(it, job["prompt"], job["max_tokens"])
                        add_event(job, {"type": "done", "slot": it["key"],
                                        "ttft_s": m["ttft_s"], "total_s": m["total_s"],
                                        "tokens": m["tokens"], "estimated": m["estimated"],
                                        "toks_per_s": it["toks_per_s"],
                                        "text": m["text"], "reasoning": m.get("reasoning", ""),
                                        "checks": it.get("checks_detail", []),
                                        "dom": [c for c in it.get("checks", [])
                                                if str(c.get("type", "")).startswith("dom_")],
                                        "passed": it.get("passed")})
                    except Exception as e:          # one rep can fail; others continue
                        it["status"] = "error"
                        it["error"] = str(e)[:500]
                        add_event(job, {"type": "error", "slot": it["key"], "error": it["error"]})
            except Exception as e:                   # boot failure fails the whole group
                for it in items:
                    if it["status"] not in ("done", "error"):
                        it["status"] = "error"
                        it["error"] = str(e)[:500]
                        add_event(job, {"type": "error", "slot": it["key"], "error": it["error"]})
            finally:
                if job["auto"]:
                    stop_container(cname)
                    for it in items:
                        add_event(job, {"type": "status", "slot": it["key"], "status": "stopped"})
        merge_dom_grades(job)
        job["rates"] = compute_rates(job)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        saved = os.path.join(RESULTS_DIR, "arena-%s-%s" % (stamp, job["id"]))
        dup = 0
        while os.path.exists(os.path.join(saved, "results.json")):
            dup += 1
            saved = os.path.join(RESULTS_DIR, "arena-%s-%s-%d" % (stamp, job["id"], dup))
        _persist_job(job, saved)
        job["saved_dir"] = os.path.relpath(saved, ROOT)
        job["status"] = "done"
        add_event(job, {"type": "job-done", "saved_dir": job["saved_dir"], "rates": job["rates"]})
    finally:
        run_lock.release()


def tally_scores():
    """Aggregate persisted blind votes across all saved runs -> per-model tally."""
    agg = {}
    for rj in glob.glob(os.path.join(RESULTS_DIR, "arena-*", "results.json")):
        try:
            with open(rj) as f:
                j = json.load(f)
            with open(os.path.join(os.path.dirname(rj), "votes.json")) as f:
                pick = (json.load(f) or {}).get("pick")
        except (OSError, ValueError):
            continue
        rs = j.get("results", [])
        if not pick or not rs:
            continue
        winner = None
        if pick != "TIE":
            winner = next((r["id"] for r in rs if r.get("slot") == pick), None)
            if winner is None:
                continue
        for r in rs:
            e = agg.setdefault(r["id"], {"label": r.get("label") or r.get("name"),
                                         "wins": 0, "ties": 0, "losses": 0, "votes": 0})
            e["votes"] += 1
            if pick == "TIE":
                e["ties"] += 1
            elif r["id"] == winner:
                e["wins"] += 1
            else:
                e["losses"] += 1
    return agg


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
        w.writerow(["slot", "model", "rep", "status", "ttft_s", "total_s",
                    "toks_per_s", "tokens", "estimated", "passed", "error", "response"])
        for r in res:
            p = r.get("passed")
            w.writerow([r.get("slot", ""), r.get("label") or r.get("name"),
                        r.get("rep", 1), r.get("status"),
                        r.get("ttft_s", ""), r.get("total_s", ""),
                        r.get("toks_per_s", ""), r.get("tokens", ""),
                        "yes" if r.get("estimated") else "",
                        "" if p is None else ("pass" if p else "fail"),
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
    if job.get("vote"):
        v = job["vote"]
        slot = v.get("pick")
        who = "Tie 🤝" if slot == "TIE" else next(
            (r.get("label") for r in res if r.get("slot") == slot), slot)
        L.append("- **Blind vote:** %s (locked %s)" % (who, v.get("at", "")))
    L += ["", "## Summary", "",
          "| model | status | TTFT (s) | total (s) | tok/s | tokens |",
          "|---|---|---|---|---|---|"]
    for r in res:
        L.append("| %s | %s | %s | %s | %s | %s |" % (
            r.get("label") or r.get("name"), r.get("status"),
            r.get("ttft_s", "—"), r.get("total_s", "—"),
            r.get("toks_per_s", "—"), r.get("tokens", "—")))
    if job.get("rates"):
        parts = []
        for s in sorted(job["rates"]):
            e = job["rates"][s]
            parts.append("%s: pass@1 %s · pass@k %s (%d/%d)" % (
                s, "✓" if e["pass1"] else "✗", "✓" if e["any"] else "✗",
                e["n_pass"], e["k"]))
        L += ["", "**Grading:** " + "; ".join(parts)]
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
        if r.get("checks_detail"):
            L += ["", "**Checks:** " + " · ".join(
                "%s %s" % (d["type"], "✓" if d["pass"] else "✗")
                for d in r["checks_detail"])]
        if r.get("dom_checks"):
            L += ["", "**DOM:** " + " · ".join(
                "%s %s" % (d.get("type"), "✓" if d.get("pass") else "✗")
                for d in r["dom_checks"])]
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
        if path == "/api/challenges":
            return self._json(200, {"challenges": list_challenges()})
        if path == "/api/runs":
            return self._json(200, {"runs": list_runs()})
        if path.startswith("/api/runs/"):
            name = path[len("/api/runs/"):].strip("/")
            fmt = (parse_qs(urlparse(self.path).query).get("fmt") or ["md"])[0]
            if name.endswith("/export"):
                return self._saved_export(name[:-len("/export")], fmt)
            return self._saved_view(name)
        if path == "/api/scores":
            return self._scores()
        if path == "/api/scores/export":
            return self._scores_csv()
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
        if path == "/api/vote":
            return self._vote()
        if path == "/api/grade":
            return self._grade()
        if path != "/api/run":
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "invalid JSON"})
        prompt = (body.get("prompt") or "").strip()
        models = body.get("models") or []
        if not models:
            return self._json(400, {"error": "no models selected"})
        ch = None
        if body.get("challenge"):
            ch = load_challenge(body["challenge"])
            if ch is None:
                return self._json(400, {"error": "unknown challenge"})
            prompt = prompt or (ch.get("prompt") or "").strip()
        if not prompt:
            return self._json(400, {"error": "prompt is empty"})
        try:
            max_tokens = max(1, min(int(body.get("max_tokens", 2000)), MAX_TOKEN_LIMIT))
        except (TypeError, ValueError):
            max_tokens = 2000
        try:
            reps = int(body.get("runs") or (ch or {}).get("runs") or 1)
        except (TypeError, ValueError):
            reps = 1
        reps = max(1, min(reps, 5))
        known = {m["id"]: m for m in discover_models()}
        for mid in models:
            if mid not in known:
                return self._json(400, {"error": f"unknown model '{mid}'"})
        if not run_lock.acquire(blocking=False):
            return self._json(409, {"error": "a run is already active"})
        slots = list("ABCDEFGHIJK"[:len(models)])
        random.shuffle(slots)                    # blind display order (protocol #8)
        checks = (ch or {}).get("checks") or []
        results = []
        for mid, slot in zip(models, slots):
            base = {"slot": slot, "id": mid, "name": known[mid]["name"],
                    "label": known[mid]["label"], "served_model": known[mid]["served_model"],
                    "container_name": known[mid]["container_name"], "port": known[mid]["port"],
                    "model_id": known[mid]["model_id"],
                    "engine": known[mid].get("engine", "sglang"),
                    "checks": checks, "status": "queued"}
            for rep in range(1, reps + 1):
                it = dict(base, rep=rep)
                it["key"] = slot if reps == 1 else "%s%d" % (slot, rep)
                results.append(it)
        with jobs_lock:
            job_seq[0] += 1
            jid = f"job-{job_seq[0]}"
            job = {"id": jid, "status": "running", "prompt": prompt,
                   "challenge": (body.get("challenge") or None),
                   "thinking": bool(body.get("thinking", False)),
                   "max_tokens": max_tokens,
                   "temperature": body.get("temperature"),
                   "auto": bool(body.get("auto", True)),
                   "engine": (body.get("engine") or "mtp"),
                   "order": [it["key"] for it in results],
                   "events": [], "grades": {}, "results": results}
            jobs[jid] = job
        threading.Thread(target=run_job, args=(job,), daemon=True).start()
        return self._json(202, {"job_id": jid, "order": job["order"]})

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

    def _vote(self):
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "invalid JSON"})
        jid = body.get("job")
        pick = (body.get("pick") or "").strip().upper()
        with jobs_lock:
            job = jobs.get(jid)
        if job is None:
            return self._json(404, {"error": "unknown job"})
        slots = {r.get("slot") for r in job.get("results", [])}
        if pick not in slots | {"TIE"}:
            return self._json(400, {"error": "pick must be a run slot or TIE"})
        if job.get("status") != "done":
            return self._json(409, {"error": "run not finished yet"})
        if job.get("vote"):
            return self._json(409, {"error": "already voted: " + str(job["vote"].get("pick"))})
        job["vote"] = {"pick": pick,
                       "at": datetime.now().isoformat(timespec="seconds")}
        saved = job.get("saved_dir")
        if saved:
            try:
                with open(os.path.join(ROOT, saved, "votes.json"), "w") as f:
                    json.dump(job["vote"], f, indent=2)
            except OSError:
                pass
        return self._json(200, dict(job["vote"]))

    def _grade(self):
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "invalid JSON"})
        jid, key = body.get("job"), body.get("key")
        checks = body.get("checks")
        with jobs_lock:
            job = jobs.get(jid)
        if job is None:
            return self._json(404, {"error": "unknown job"})
        item = next((r for r in job["results"] if r.get("key") == key), None)
        if item is None or not isinstance(checks, list) or not checks:
            return self._json(400, {"error": "bad key or checks"})
        ok = all(bool(c.get("pass")) for c in checks)
        job.setdefault("grades", {})[key] = {
            "checks": checks, "pass": ok,
            "at": datetime.now().isoformat(timespec="seconds")}
        item["dom_checks"] = checks
        item["dom_pass"] = ok
        item["dom_pending"] = False
        _recompute_pass(item)
        job["rates"] = compute_rates(job)
        if job.get("saved_dir"):
            _persist_job(job)
        return self._json(200, {"key": key, "passed": item.get("passed"),
                                "rates": job["rates"]})

    def _load_saved(self, name):
        if not re.fullmatch(r"arena-[\w.-]+", str(name or "")):
            return None
        rj = os.path.join(RESULTS_DIR, name, "results.json")
        if not os.path.isfile(rj):
            return None
        try:
            with open(rj) as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _saved_view(self, name):
        j = self._load_saved(name)
        if j is None:
            return self._json(404, {"error": "unknown run"})
        return self._json(200, j)

    def _saved_export(self, name, fmt):
        j = self._load_saved(name)
        if j is None:
            return self._json(404, {"error": "unknown run"})
        try:
            fname, mime, content = build_export(j, fmt)
        except Exception as e:
            return self._json(500, {"error": f"export failed: {e}"})
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="%s"' % fname)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _scores(self):
        agg = tally_scores()
        rows = []
        for mid, e in agg.items():
            wr = (e["wins"] + 0.5 * e["ties"]) / e["votes"] * 100 if e["votes"] else 0
            rows.append({"id": mid, **e, "win_rate": round(wr, 1)})
        rows.sort(key=lambda r: (-r["win_rate"], r["label"]))
        return self._json(200, {"rows": rows})

    def _scores_csv(self):
        import io as _io
        import csv as _csv
        agg = tally_scores()
        buf = _io.StringIO()
        w = _csv.writer(buf)
        w.writerow(["model", "votes", "wins", "ties", "losses", "win_rate_pct"])
        def rate(e):
            return (e["wins"] + 0.5 * e["ties"]) / e["votes"] * 100 if e["votes"] else 0
        for mid, e in sorted(agg.items(), key=lambda kv: -rate(kv[1])):
            w.writerow([e["label"], e["votes"], e["wins"], e["ties"],
                        e["losses"], round(rate(e), 1)])
        data = buf.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="arena-scoreboard.csv"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
