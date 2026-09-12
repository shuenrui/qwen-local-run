#!/usr/bin/env python3
"""Vet research-agent candidates against the directory's rules before merging.

Reads whichever candidate files exist:
    tools/history/inputs/pass4-social/candidates.json   pass-4 social ledger
    /tmp/research_{hf,github,forum}.json                live pass output
    (--all also re-vets the merged snapshots in tools/history/inputs/)

Checks, per AGENTS laws 1 and 9-11:
    enums — imported from validate.py so they cannot drift
    URL liveness — reddit permalinks are checked via mirror_url (law 10)
    duplicates — against the current dataset (checkpoint + engine + hardware)
    Scenario B gates (law 11) — publisher whitelist, canonical publisher per
        format+quant, ladder caps (Q3/Q5 only measured or fit-boundary),
        family+quant already-covered detection
    plausibility — weight fit vs hardware memory, bandwidth roofline for
        decode speeds (spec-decode aware), NVFP4 => Blackwell-class hardware
    lineage dedupe — same artifact + engine + config + hardware collapses
        into one setup, never N rows

Nothing is written to the dataset here. Exit 0 normally; --strict exits 1
when any candidate has FIX-level problems.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import validate as V  # noqa: E402  enums: QUANTS FORMATS METRICS UNITS SPEC_DECODE

DATA = V.DATA
LEDGER = os.path.join(HERE, "history", "inputs", "pass4-social", "candidates.json")
FILES = [
    ("pass4-social", LEDGER),
    ("hf", "/tmp/research_hf.json"),
    ("github", "/tmp/research_github.json"),
    ("forum", "/tmp/research_forum.json"),
]
FILES_ALL = FILES + [
    ("hf-snapshot", os.path.join(HERE, "history", "inputs", "research_hf.json")),
    ("github-snapshot", os.path.join(HERE, "history", "inputs", "research_github.json")),
    ("forum-snapshot", os.path.join(HERE, "history", "inputs", "research_forum.json")),
]

# ---- Scenario B constants (AGENTS law 11, owner decision 2026-09-10) -------

WHITELIST = {"qwen", "unsloth", "bartowski", "ggml-org", "lmstudio-community",
             "mlx-community", "quanttrio", "mradermacher", "redhatai",
             "nvidia", "amd",
             # engine-registry lanes carry their registry as publisher
             # (Scenario B: Ollama/LM Studio only where a registry entry exists)
             "ollama"}

# (format, quant) -> publishers in canonical order; the first is the lane owner
CANON = {
    ("gguf", "gguf-q2"): ["unsloth", "bartowski", "ggml-org", "mradermacher"],
    ("gguf", "gguf-q3"): ["unsloth", "bartowski", "mradermacher"],
    ("gguf", "gguf-q4"): ["unsloth", "bartowski", "ggml-org",
                          "lmstudio-community", "mradermacher"],
    ("gguf", "gguf-q5"): ["unsloth", "bartowski", "mradermacher"],
    ("gguf", "gguf-q6"): ["unsloth", "bartowski", "ggml-org", "mradermacher"],
    ("gguf", "gguf-q8"): ["unsloth", "bartowski", "ggml-org",
                          "lmstudio-community", "mradermacher"],
    ("mlx", "mlx-4"): ["mlx-community", "lmstudio-community"],
    ("mlx", "mlx-6"): ["mlx-community"],
    ("mlx", "mlx-8"): ["mlx-community", "lmstudio-community"],
    ("awq", "awq"): ["qwen", "quanttrio"],
    ("gptq", "gptq"): ["qwen", "quanttrio"],
    ("safetensors", "fp8"): ["qwen", "nvidia", "unsloth"],
    ("safetensors", "fp16"): ["qwen"],
    ("safetensors", "bf16"): ["qwen"],
    ("safetensors", "nvfp4"): ["redhatai", "nvidia", "unsloth", "amd"],
    ("safetensors", "mxfp4"): ["amd"],
    ("safetensors", "int4-hybrid"): ["qwen"],
}

LADDER_COND = {"gguf-q3", "gguf-q5", "mlx-3", "mlx-2"}

# rough bytes-per-parameter by quant, incl. overhead — a review heuristic for
# the roofline, deliberately conservative
BPP = {"bf16": 2.0, "fp16": 2.0, "fp8": 1.06, "int8": 1.06, "nvfp4": 0.56,
       "mxfp4": 0.56, "int4": 0.56, "int4-hybrid": 0.6, "awq": 0.6,
       "gptq": 0.6, "autoround": 0.6, "gguf-q8": 1.12, "gguf-q6": 0.9,
       "gguf-q5": 0.76, "gguf-q4": 0.62, "gguf-q3": 0.5, "gguf-q2": 0.38,
       "mlx-8": 1.1, "mlx-6": 0.85, "mlx-4": 0.6, "mlx-3": 0.48, "mlx-2": 0.35}

BLACKWELL_HINTS = ("blackwell", "sm121", "sm_121", "sm120", "sm_120", "gb10",
                   "b200", "rtx 50", "rtx50", "5090", "5080", "5070", "rtx pro")
OFFLOAD_HINTS = ("offload", "mmap", "cpu", "expert", "layer", "split", "npu",
                 "unified", "swap")


def url_status(url, timeout=8):
    if not re.match(r"^https?://", url or ""):
        return "bad-scheme"
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": "Mozilla/5.0 directory-vet"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return str(r.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:
        return f"err:{type(e).__name__}"


def load(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        return {"__parse_error__": str(e)}


def norm(s):
    return re.sub(r"[^a-z0-9.-]", "", (s or "").lower())


def quant_norm(raw):
    """Map a free-text quant string onto the enum, or None."""
    if raw in V.QUANTS:
        return raw
    t = (raw or "").lower()
    m = re.search(r"\b(q|iq|ud-q|ud-iq)(\d)", t)
    if "gguf" in t or m:
        lvl = m.group(2) if m else None
        if lvl and f"gguf-q{lvl}" in V.QUANTS:
            return f"gguf-q{lvl}"
    m = re.search(r"mlx[ -]?(\d)", t)
    if m and f"mlx-{m.group(1)}" in V.QUANTS:
        return f"mlx-{m.group(1)}"
    m = re.search(r"\b(\d)[ -]?bit\b", t)
    if m:
        cand = {"4": "int4", "8": "int8"}.get(m.group(1))
        if cand:
            return cand
    for q in ("nvfp4", "mxfp4", "awq", "gptq", "fp8", "bf16", "fp16",
              "autoround", "int4-hybrid"):
        if q in t:
            return q
    return None


def fmt_from_quant(q):
    if not q:
        return None
    if q.startswith("gguf"):
        return "gguf"
    if q.startswith("mlx"):
        return "mlx"
    if q in ("awq",):
        return "awq"
    if q in ("gptq", "autoround"):
        return "gptq"
    return "safetensors"


class Index:
    """Dataset indexes: enums that live in data/, existing setups, models."""

    def __init__(self):
        self.engines = set()
        d = os.path.join(DATA, "engines")
        for n in os.listdir(d):
            if n.endswith(".json"):
                self.engines.add(n[:-5])
        self.hw = {}
        d = os.path.join(DATA, "hardware")
        for n in os.listdir(d):
            if n.endswith(".json"):
                obj = json.load(open(os.path.join(d, n), encoding="utf-8"))
                self.hw[obj["id"]] = obj
        self.setups = []
        d = os.path.join(DATA, "setups")
        for n in sorted(os.listdir(d)):
            if n.endswith(".json") and not n.startswith("_"):
                obj = json.load(open(os.path.join(d, n), encoding="utf-8"))
                self.setups.append((n[:-5], obj))
        self.models = []
        d = os.path.join(DATA, "models")
        for n in sorted(os.listdir(d)):
            if n.endswith(".json"):
                obj = json.load(open(os.path.join(d, n), encoding="utf-8"))
                self.models.append(obj)

    def hw_blackwell(self, hwval):
        if hwval in self.hw:
            h = self.hw[hwval]
            text = f"{h.get('arch','')} {h.get('gpu','')}".lower()
            return any(k in text for k in ("blackwell", "sm121", "sm_121"))
        text = (hwval or "").lower()
        return any(k in text for k in BLACKWELL_HINTS)

    def hw_bandwidth(self, hwval):
        h = self.hw.get(hwval)
        if not h:
            return None
        rng = h.get("bandwidth_range_gbs")
        return max(rng) if rng else h.get("bandwidth_gbs")

    def hw_memory(self, hwval):
        h = self.hw.get(hwval)
        if not h:
            return None
        return h.get("memory_usable_gb") or h.get("memory_gb")

    def model_match(self, text):
        t = norm(text)
        best = None
        for m in self.models:
            key = norm(m["name"])
            if key and key in t:
                if best is None or len(key) > len(norm(best["name"])):
                    best = m
        return best

    def params_read_b(self, m):
        arch = m.get("architecture") or {}
        if arch.get("kind") == "moe" and arch.get("params_active_b"):
            return arch["params_active_b"]
        return arch.get("params_total_b")

    def dataset_idents(self):
        return {(s["variation"]["checkpoint"].lower(), s["engine"]["id"],
                 tuple(sorted(s["hardware"]))) for _, s in self.setups}

    def covered_family_quants(self):
        """(model family name, quant) pairs already present in the dataset."""
        out = {}
        for sid, s in self.setups:
            m = self.model_match(s["variation"]["checkpoint"])
            if m:
                out.setdefault((norm(m["name"]), s["variation"]["quant"]), sid)
        return out


def fields(r):
    """Normalize legacy (pass 2/3) and pass-4 ledger shapes into one view."""
    f = {}
    f["raw_model"] = r.get("model") or r.get("family") or ""
    f["checkpoint"] = r.get("checkpoint") or ""
    pub = r.get("publisher")
    if not pub and re.fullmatch(r"[^/\s]+/[^/\s]+", f["checkpoint"]):
        pub = f["checkpoint"].split("/")[0]
    f["publisher"] = (pub or "").lower()
    # "" means unstated (honest null), not invalid — same convention as the dataset
    f["quant_raw"] = r.get("quant") or None
    f["format_raw"] = r.get("format") or None
    f["engine"] = r.get("engine") or None
    f["hardware"] = r.get("hardware") or None
    f["config"] = r.get("config") or r.get("config_notes") or ""
    f["spec_decode"] = r.get("spec_decode") or None
    f["size_gb"] = r.get("size_gb")
    f["measurements"] = r.get("measurements") or r.get("claimed") or []
    f["status"] = r.get("status")
    f["tier"] = r.get("tier_eligibility") or r.get("provenance_tier")
    f["quote"] = r.get("discovery_quote") or r.get("source_quote") or r.get("quote")
    f["channel"] = r.get("channel") or r.get("platform") or ""
    canon = r.get("canonical_urls") or []
    f["canonical"] = [c.get("url") if isinstance(c, dict) else c for c in canon]
    f["canonical"] = [u for u in f["canonical"] if u]
    f["url"] = (f["canonical"][0] if f["canonical"] else
                r.get("url") or r.get("repo") or r.get("thread")
                or r.get("discovery_url") or "")
    f["discovery_url"] = r.get("discovery_url") or ""
    f["mirror_url"] = r.get("mirror_url") or ""
    f["title"] = r.get("title") or r.get("thread") or ""
    return f


def vet_one(idx, f, have, covered, url_cache):
    probs, warns = [], []

    # --- enums ---------------------------------------------------------------
    q = f["quant_raw"] if f["quant_raw"] in V.QUANTS else None
    if q is None and f["quant_raw"] is not None:
        qn = quant_norm(f["quant_raw"])
        if qn:
            warns.append(f"quant={f['quant_raw']!r} -> record as {qn!r}")
            q = qn
        else:
            probs.append(f"quant={f['quant_raw']!r} not in enum")
    fmt = f["format_raw"] if f["format_raw"] in V.FORMATS else None
    if fmt is None and f["format_raw"] is not None:
        probs.append(f"format={f['format_raw']!r} not in enum")
    if fmt is None and q:
        fmt = fmt_from_quant(q)
    if f["engine"] is not None and f["engine"] not in idx.engines:
        hint = " (legacy 'other' -> use custom-fork)" if f["engine"] == "other" else ""
        probs.append(f"engine={f['engine']!r} not in data/engines{hint}")
    hw = f["hardware"]
    if hw is not None and hw not in idx.hw and not str(hw).startswith("other"):
        probs.append(f"hardware={hw!r} not a class — new classes are an owner decision")
    if f["spec_decode"] is not None and f["spec_decode"] not in V.SPEC_DECODE:
        probs.append(f"spec_decode={f['spec_decode']!r} not in enum")
    for m in f["measurements"]:
        if m.get("metric") not in V.METRICS:
            probs.append(f"metric={m.get('metric')!r}")
        if m.get("unit") not in V.UNITS:
            probs.append(f"unit={m.get('unit')!r}")

    # --- URLs (law 10: reddit permalink -> check the mirror) -----------------
    def check(label, u, mirror=""):
        if not u:
            return
        netloc = urlparse(u).netloc
        if netloc.endswith("reddit.com") and mirror:
            st = url_cache.setdefault(mirror, url_status(mirror))
            if st != "200":
                probs.append(f"{label} mirror={st}")
            else:
                warns.append(f"{label}: permalink env-blocked, mirror OK")
        else:
            st = url_cache.setdefault(u, url_status(u))
            if st != "200":
                probs.append(f"{label}={st}")

    check("url", f["url"], f["mirror_url"])
    if f["discovery_url"] and f["discovery_url"] != f["url"]:
        check("discovery", f["discovery_url"], f["mirror_url"])

    # --- duplicates against the dataset --------------------------------------
    cp = (f["checkpoint"] or f["raw_model"]).lower()
    dup = any(c == cp for c, _, _ in have)
    if dup:
        warns.append("DUP? checkpoint already in dataset (config may differ)")

    # --- Scenario B gates (law 11) --------------------------------------------
    # FIX level only for unmeasured quant-matrix lanes (the legacy hf research
    # pass); measured recipe lanes are what the directory wants — advisory WARN.
    matrix_lane = not f["measurements"] and f["channel"] in ("", "hf")
    if q and f["publisher"]:
        if f["publisher"] not in WHITELIST:
            msg = f"WHITELIST publisher={f['publisher']!r} not in law-11 list"
            (probs if matrix_lane else warns).append(msg)
        else:
            canon = CANON.get((fmt, q))
            if canon and f["publisher"] != canon[0]:
                msg = f"CANON for ({fmt},{q}) is {canon[0]!r}, not {f['publisher']!r}"
                (probs if matrix_lane else warns).append(msg)
        if q in LADDER_COND and not (f["measurements"] or f["status"] == "measured"):
            msg = f"LADDER {q} lane needs a measurement or fit-boundary justification"
            (probs if matrix_lane else warns).append(msg)
    if q is None and f["measurements"]:
        warns.append("quant unstated — resolve from the artifact before merge")
    if q and not f["measurements"]:
        m = idx.model_match(f["checkpoint"] or f["raw_model"])
        if m:
            key = (norm(m["name"]), q)
            if key in covered:
                warns.append(f"LADDER-DUP family+quant already covered by setup {covered[key]}")

    # --- plausibility ---------------------------------------------------------
    mem = idx.hw_memory(hw) if hw in idx.hw else None
    bw = idx.hw_bandwidth(hw) if hw in idx.hw else None
    blob = f"{f['config']} {f['quote'] or ''}".lower()
    if f["size_gb"] and mem and f["size_gb"] > mem \
            and not any(k in blob for k in OFFLOAD_HINTS):
        warns.append(f"FIT? size {f['size_gb']} GB > {mem} GB memory, no offload stated")
    for meas in f["measurements"]:
        if meas.get("metric") == "memory_gb" and f["size_gb"] \
                and meas.get("value", 0) < 1.05 * f["size_gb"]:
            warns.append("resident memory < 1.05x weight size — check what was measured")
    if q == "nvfp4" and hw:
        if hw in idx.hw and not idx.hw_blackwell(hw):
            probs.append("NVFP4 on non-Blackwell hardware class")
        elif hw not in idx.hw and not idx.hw_blackwell(hw):
            warns.append("NVFP4 needs Blackwell (sm_120+); 'other' hardware doesn't say so")
    m = idx.model_match(f["checkpoint"] or f["raw_model"])
    if m and q in BPP and bw:
        params = idx.params_read_b(m)
        if params:
            ceiling = bw / (params * BPP[q])
            spec_text = f"{f['config']} {f['quant_raw'] or ''} {f['title']} {f['quote'] or ''}".lower()
            spec = f["spec_decode"] not in (None, "", "none") or any(
                k in spec_text for k in
                ("mtp", "dflash", "nextn", "ngram", "eagle", "speculative", "draft"))
            warn_x, fix_x = (3.0, 8.0) if spec else (1.15, 4.0)
            for meas in f["measurements"]:
                met = str(meas.get("metric", ""))
                if meas.get("unit") != "tok/s" or not met.startswith("decode"):
                    continue
                if met == "decode_agg" or (meas.get("concurrency") or 1) > 1:
                    continue  # aggregate throughput is not bounded per-stream
                val = meas.get("value") or 0
                if val > ceiling * fix_x:
                    probs.append(f"IMPLAUSIBLE {val} tok/s > {fix_x:g}x roofline {ceiling:.1f}")
                elif val > ceiling * warn_x:
                    warns.append(f"ROOFLINE? {val} tok/s vs ceiling ~{ceiling:.1f} "
                                 f"(spec_decode={'on' if spec else 'off'})")

    # --- social ladder (laws 1, 9, 10) ----------------------------------------
    if f["channel"]:
        if f["channel"] == "reddit" and f["mirror_url"] == "":
            probs.append("reddit candidate without mirror_url (law 10)")
        if f["channel"] in ("x", "youtube") and not f["canonical"]:
            warns.append("rung 3: discovery-only — no numbers may ride on this alone")
        if f["measurements"] and f["tier"] == "forum" and not f["quote"]:
            probs.append("forum-tier numbers without a verbatim quote (law 1)")
    return probs, warns


def main():
    strict = "--strict" in sys.argv
    files = FILES_ALL if "--all" in sys.argv else FILES
    idx = Index()
    have = idx.dataset_idents()
    covered = idx.covered_family_quants()
    url_cache = {}

    all_rows = []
    for kind, path in files:
        rows = load(path)
        print(f"\n===== {kind}: {path} =====")
        if rows is None:
            print("  (file not written yet)")
            continue
        if isinstance(rows, dict):
            print("  PARSE ERROR:", rows.get("__parse_error__"))
            continue
        print(f"  {len(rows)} candidates")
        for i, r in enumerate(rows):
            if r.get("state") in ("dropped", "merged"):
                continue
            f = fields(r)
            probs, warns = vet_one(idx, f, have, covered, url_cache)
            all_rows.append((kind, i, f, probs, warns))

    # lineage dedupe across all files: same artifact+engine+config+hardware
    lineage = {}
    for n, (kind, i, f, probs, warns) in enumerate(all_rows):
        key = ((f["canonical"][0] if f["canonical"] else f["checkpoint"].lower())
               or f["raw_model"].lower(),
               f["engine"], str(f["hardware"]), norm(f["config"])[:60])
        lineage.setdefault(key, []).append(n)
    for key, members in lineage.items():
        if len(members) > 1 and key[0]:
            for n in members[1:]:
                kind, i, f, probs, warns = all_rows[n]
                warns = warns + [f"LINEAGE x{len(members)}: collapse into one "
                                 f"setup with row {members[0]}"]
                all_rows[n] = (kind, i, f, probs, warns)

    total = len(all_rows)
    n_fix = n_warn = n_ok = 0
    for kind, i, f, probs, warns in all_rows:
        verdict = "FIX" if probs else ("WARN" if warns else "OK ")
        if probs:
            n_fix += 1
        elif warns:
            n_warn += 1
        else:
            n_ok += 1
        name = f["checkpoint"] or f["title"] or f["raw_model"] or f["url"]
        print(f"  [{kind}:{i:2}] {verdict} {str(name)[:64]}")
        for p in probs:
            print(f"        FIX  {p}")
        for wline in warns:
            print(f"        warn {wline}")
        if f["quote"]:
            print(f"        quote: {f['quote'][:110]}")

    print(f"\ntotal {total}: {n_ok} OK, {n_warn} WARN, {n_fix} FIX")
    if strict and n_fix:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
