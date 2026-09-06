#!/usr/bin/env python3
"""Dataset hygiene audit: link rot, license/field consistency, dup lanes,
unused publishers. Read-only; prints a report."""
import json
import os
import re
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

DATA = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data"


def load_dir(rel):
    out = {}
    d = os.path.join(DATA, rel)
    for n in sorted(os.listdir(d)):
        if n.endswith(".json"):
            out[n[:-5]] = json.load(open(os.path.join(d, n), encoding="utf-8"))
    return out


def status(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 directory-audit"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"err:{type(e).__name__}"


setups = load_dir("setups")
models = load_dir("models")
hardware = load_dir("hardware")
publishers = json.load(open(os.path.join(DATA, "publishers.json"), encoding="utf-8"))["publishers"]

urls = {}
for sid, s in setups.items():
    for src in s.get("sources", []):
        urls.setdefault(src["url"], []).append(f"setups/{sid}")
    for m in s.get("measurements", []):
        if m.get("source"):
            urls.setdefault(m["source"], []).append(f"setups/{sid}:m")
    urls.setdefault(s["variation"]["url"], []).append(f"setups/{sid}:var")
    if s["run"].get("repo"):
        urls.setdefault(s["run"]["repo"], []).append(f"setups/{sid}:run")
for mid, m in models.items():
    urls.setdefault(m["url"], []).append(f"models/{mid}")
for hid, h in hardware.items():
    if h.get("url"):
        urls.setdefault(h["url"], []).append(f"hardware/{hid}")
for pid, p in publishers.items():
    if p.get("url"):
        urls.setdefault(p["url"], []).append(f"publishers/{pid}")

print(f"checking {len(urls)} distinct URLs with 8 workers...")
with ThreadPoolExecutor(max_workers=8) as ex:
    codes = list(ex.map(status, urls))
bad = [(u, c, urls[u]) for u, c in zip(urls, codes) if c != 200]
print(f"\n=== LINK ROT: {len(bad)} of {len(urls)} not HTTP 200 ===")
for u, c, where in bad:
    print(f"  {c}  {u}\n        used by: {', '.join(where[:3])}")

print("\n=== LICENSE VALUES ===")
lic = Counter()
for mid, m in models.items():
    lic[(m.get("license"), mid)] += 1
for sid, s in setups.items():
    lic[(s["variation"].get("license"), sid)] += 1
for (val, who), _ in sorted(lic.items(), key=lambda kv: str(kv[0][0])):
    if val is None or not re.match(r"^[A-Za-z0-9.\-+ ]+$", str(val)) or "other" in str(val).lower():
        print(f"  {who}: {val!r}")

print("\n=== NULL / SUSPECT FIELDS ===")
for mid, m in models.items():
    c = m.get("context", {})
    if not c.get("native"):
        print(f"  models/{mid}: context.native missing")
    a = m.get("architecture", {})
    if a.get("kind") == "moe" and not a.get("params_active_b"):
        print(f"  models/{mid}: moe without params_active_b")
    if not m.get("released"):
        print(f"  models/{mid}: released missing")
for sid, s in setups.items():
    r = s.get("requirements", {})
    if r.get("memory_gb") is None:
        print(f"  setups/{sid}: requirements.memory_gb null")
    if not s.get("slug_note"):
        print(f"  setups/{sid}: no slug_note")
    if s.get("status") == "measured" and not any(
            m.get("provenance") == "box" for m in s.get("measurements", [])):
        print(f"  setups/{sid}: status measured but no box measurement")
    for m in s.get("measurements", []):
        if m.get("provenance") in ("forum", "vendor") and not m.get("source"):
            print(f"  setups/{sid}: {m['provenance']} measurement without source")
        if m.get("provenance") == "box" and not (m.get("date") and m.get("n") and m.get("method")):
            print(f"  setups/{sid}: box measurement missing date/n/method")

print("\n=== DUPLICATE LANES (checkpoint+engine+hardware) ===")
seen = defaultdict(list)
for sid, s in setups.items():
    key = (s["variation"]["checkpoint"].lower(), s["engine"]["id"],
           tuple(sorted(s["hardware"])))
    seen[key].append(sid)
for key, sids in seen.items():
    if len(sids) > 1:
        cfgs = [setups[s]["engine"]["config"][:60] for s in sids]
        print(f"  {key[0]} | {key[1]} | {','.join(key[2])}\n      {sids}\n      configs: {cfgs}")

print("\n=== UNUSED PUBLISHERS ===")
used = set()
for sid, s in setups.items():
    used.add(s["variation"]["publisher"])
for mid, m in models.items():
    used.add(m.get("publisher"))
for pid in sorted(set(publishers) - used):
    print(f"  {pid}: {publishers[pid].get('name')}")

print("\n=== HARDWARE CLASSES NEVER USED ===")
hused = set()
for sid, s in setups.items():
    hused.update(s["hardware"])
for hid in sorted(set(hardware) - hused):
    print(f"  {hid}")

print("\n=== ENGINES NEVER USED ===")
engines = load_dir("engines")
eused = {s["engine"]["id"] for s in setups.values()}
for eid in sorted(set(engines) - eused):
    print(f"  {eid}")
