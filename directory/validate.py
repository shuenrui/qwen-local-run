#!/usr/bin/env python3
"""Validate the directory dataset. Stdlib only.

Usage: python3 directory/validate.py [--strict]

Fails on: missing required fields, unknown cross-reference ids, measurements
without a source, values outside the enums, and duplicate ids. --strict also
fails on warnings (null fields that a complete entry would fill in).
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

QUANTS = {
    "bf16", "fp16", "fp8", "nvfp4", "mxfp4", "int8", "int4", "int4-hybrid",
    "awq", "gptq", "autoround", "gguf-q8", "gguf-q6", "gguf-q5", "gguf-q4",
    "gguf-q3", "gguf-q2", "mlx-8", "mlx-6", "mlx-4", "mlx-3", "mlx-2",
    "mixed", "other",
}

FORMATS = {
    "safetensors", "gguf", "mlx", "onnx", "gptq", "awq", "unknown",
}

SPEC_DECODE = {"none", "mtp", "eagle", "dspark", "dflash2", "ngram", "other"}

METRICS = {
    # speed
    "decode_code", "decode_essay", "decode_chat", "decode_agg",
    "decode_per_stream", "ttft_ms", "task_time_min",
    # quality
    "quality_index", "bench_code", "bench_toolcall", "bench_mmlu",
    "bench_gsm8k", "bench_humaneval", "bench_other",
    # footprint
    "memory_gb", "disk_gb",
}

UNITS = {"tok/s", "ms", "s", "min", "%", "GB", "score"}

PROVENANCE = {"box", "forum", "vendor"}
PROV_RANK = {"box": 3, "forum": 2, "vendor": 1, None: 0}

STATUS = {"measured", "reported", "claimed", "untested", "broken"}

SOURCE_KINDS = {
    "repo", "model", "thread", "post", "video", "docs", "paper", "blog",
    "benchmark", "other",
}

URL_RE = re.compile(r"^https?://\S+$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

REQUIRED_SETUP = [
    "id", "title", "model", "variation", "engine", "hardware",
    "requirements", "run", "status", "sources",
]
REQUIRED_VARIATION = ["checkpoint", "publisher", "quant", "format", "url"]
REQUIRED_ENGINE = ["id", "config"]
REQUIRED_RUN = ["repo"]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def load(rel: str):
    path = os.path.join(DATA, rel)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_dir(rel: str) -> dict:
    out = {}
    d = os.path.join(DATA, rel)
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        try:
            obj = load(os.path.join(rel, name))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{rel}/{name}: invalid JSON — {exc}") from exc
        out[name[:-5]] = obj
    return out


def check_id(rep: Report, where: str, value: str) -> None:
    if not isinstance(value, str) or not ID_RE.match(value):
        rep.err(where, f"id {value!r} must match {ID_RE.pattern}")


def check_url(rep: Report, where: str, field: str, value) -> None:
    if value is None:
        rep.warn(where, f"{field} is null")
        return
    if not isinstance(value, str) or not URL_RE.match(value):
        rep.err(where, f"{field} {value!r} is not an http(s) URL")


def main() -> int:
    strict = "--strict" in sys.argv

    models = load_dir("models")
    hardware = load_dir("hardware")
    engines = load_dir("engines")
    setups = load_dir("setups")
    publishers = load("publishers.json")
    pub_ids = set(publishers.get("publishers", {}))

    rep = Report()

    for mid, m in models.items():
        w = f"models/{mid}"
        if m.get("id", mid) != mid:
            rep.err(w, f"filename {mid} != id {m.get('id')!r}")
        check_id(rep, w, mid)
        for f in ("name", "family", "publisher"):
            if f not in m:
                rep.err(w, f"missing {f}")
        if m.get("publisher") not in pub_ids:
            rep.err(w, f"unknown publisher {m.get('publisher')!r}")
        check_url(rep, w, "url", m.get("url"))
        arch = m.get("architecture", {})
        # params_total_b may sit at top level or inside architecture; accept either.
        params = m.get("params_total_b", arch.get("params_total_b"))
        if not isinstance(params, (int, float)):
            rep.err(w, f"missing or non-numeric params_total_b (top level or architecture), got {params!r}")
        if arch.get("kind") not in ("dense", "moe", None):
            rep.err(w, f"architecture.kind {arch.get('kind')!r} not dense|moe")
        if arch.get("kind") == "moe" and not arch.get("params_active_b"):
            rep.warn(w, "MoE model without params_active_b")

    for hid, h in hardware.items():
        w = f"hardware/{hid}"
        if h.get("id", hid) != hid:
            rep.err(w, f"filename {hid} != id {h.get('id')!r}")
        check_id(rep, w, hid)
        for f in ("name", "memory_gb", "bandwidth_gbs"):
            if f not in h:
                rep.err(w, f"missing {f}")
        if not isinstance(h.get("memory_gb"), (int, float)):
            rep.err(w, f"memory_gb must be a number, got {h.get('memory_gb')!r}")

    for eid, e in engines.items():
        w = f"engines/{eid}"
        if e.get("id", eid) != eid:
            rep.err(w, f"filename {eid} != id {e.get('id')!r}")
        check_id(rep, w, eid)
        for f in ("name", "kind", "url"):
            if f not in e:
                rep.err(w, f"missing {f}")
        # A fork-category engine has no single canonical upstream, so a null url
        # is honest there; everywhere else it means a missing link.
        if e.get("kind") == "fork" and e.get("url") is None:
            pass
        else:
            check_url(rep, w, "url", e.get("url"))

    seen_titles: dict[str, str] = {}
    for sid, s in setups.items():
        w = f"setups/{sid}"
        if s.get("id", sid) != sid:
            rep.err(w, f"filename {sid} != id {s.get('id')!r}")
        check_id(rep, w, sid)

        for f in REQUIRED_SETUP:
            if f not in s:
                rep.err(w, f"missing required field {f!r}")

        if s.get("model") not in models:
            rep.err(w, f"unknown model id {s.get('model')!r}")

        if s.get("status") not in STATUS:
            rep.err(w, f"status {s.get('status')!r} not in {sorted(STATUS)}")

        # A near-duplicate setup is almost always a copy/paste mistake.
        key = json.dumps(
            [s.get("model"), s.get("variation", {}).get("checkpoint"),
             s.get("engine", {}).get("id"), s.get("engine", {}).get("config"),
             sorted(s.get("hardware", []))],
            sort_keys=True,
        )
        if key in seen_titles:
            rep.err(w, f"duplicate of setups/{seen_titles[key]} (same model+checkpoint+engine+config+hardware)")
        seen_titles[key] = sid

        v = s.get("variation", {})
        for f in REQUIRED_VARIATION:
            if f not in v or v[f] is None:
                rep.err(w, f"variation.{f} missing or null")
        if v.get("quant", "").lower() not in QUANTS:
            rep.err(w, f"variation.quant {v.get('quant')!r} not in enum")
        if v.get("format") not in FORMATS:
            rep.err(w, f"variation.format {v.get('format')!r} not in enum")
        if v.get("publisher") not in pub_ids:
            rep.err(w, f"variation.publisher {v.get('publisher')!r} unknown")
        if s.get("builder") and s["builder"] not in pub_ids:
            rep.err(w, f"builder {s.get('builder')!r} unknown publisher")
        check_url(rep, w, "variation.url", v.get("url"))
        if not isinstance(v.get("size_gb"), (int, float)):
            rep.err(w, f"variation.size_gb must be a number or null, got {v.get('size_gb')!r}")

        e = s.get("engine", {})
        for f in REQUIRED_ENGINE:
            if f not in e or e[f] is None:
                rep.err(w, f"engine.{f} missing or null")
        if e.get("id") not in engines:
            rep.err(w, f"engine.id {e.get('id')!r} unknown")
        if e.get("spec_decode", "none") not in SPEC_DECODE:
            rep.err(w, f"engine.spec_decode {e.get('spec_decode')!r} not in enum")

        hw = s.get("hardware")
        if not isinstance(hw, list) or not hw:
            rep.err(w, "hardware must be a non-empty list")
        else:
            for h in hw:
                if h not in hardware:
                    rep.err(w, f"unknown hardware id {h!r}")

        req = s.get("requirements", {})
        for f in ("memory_gb", "disk_gb"):
            val = req.get(f)
            if val is not None and not isinstance(val, (int, float)):
                rep.err(w, f"requirements.{f} must be a number or null, got {val!r}")
        if req.get("memory_gb") is None:
            rep.warn(w, "requirements.memory_gb is null — cannot answer 'will it fit'")

        run = s.get("run", {})
        for f in REQUIRED_RUN:
            if f not in run or run[f] is None:
                rep.err(w, f"run.{f} missing or null")
        check_url(rep, w, "run.repo", run.get("repo"))
        if not run.get("command") and not run.get("steps"):
            rep.err(w, "run needs a command or steps — this is the 'how to run' directory")

        caps = s.get("capabilities", {})
        if caps.get("long_context") is not None and not isinstance(caps["long_context"], int):
            rep.err(w, "capabilities.long_context must be an int token count or null")

        best = None
        for i, m in enumerate(s.get("measurements", [])):
            mw = f"{w} measurements[{i}]"
            if m.get("metric") not in METRICS:
                rep.err(mw, f"metric {m.get('metric')!r} not in enum")
            if not isinstance(m.get("value"), (int, float)):
                rep.err(mw, f"value must be a number, got {m.get('value')!r}")
            if m.get("unit") not in UNITS:
                rep.err(mw, f"unit {m.get('unit')!r} not in enum")
            prov = m.get("provenance")
            if prov not in PROVENANCE:
                rep.err(mw, f"provenance {prov!r} not in {sorted(PROVENANCE)}")
                continue
            best = prov if PROV_RANK[prov] > PROV_RANK[best] else best
            if prov == "box":
                for f in ("date", "n", "method"):
                    if not m.get(f):
                        rep.err(mw, f"box measurement requires {f}")
            else:
                if not m.get("source"):
                    rep.err(mw, f"{prov} measurement requires a source URL")
            if m.get("source"):
                check_url(rep, mw, "source", m["source"])
            if m.get("date") and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(m["date"])):
                rep.err(mw, f"date {m['date']!r} must be YYYY-MM-DD")

        declared = s.get("provenance_tier")
        if declared and PROV_RANK.get(declared, 0) > PROV_RANK[best]:
            rep.err(w, f"provenance_tier {declared!r} overstates the best measurement tier {best!r}")
        if declared and declared != best and best is not None:
            rep.warn(w, f"provenance_tier {declared!r} != best measurement tier {best!r}")
        if s.get("measurements") and declared != best:
            rep.err(w, f"provenance_tier must equal best measurement tier ({best!r})")
        if not s.get("measurements") and declared not in (None, "vendor"):
            rep.err(w, "no measurements but provenance_tier claims evidence")

        srcs = s.get("sources", [])
        if not isinstance(srcs, list) or not srcs:
            rep.err(w, "sources must be a non-empty list")
        for i, src in enumerate(srcs):
            sw = f"{w} sources[{i}]"
            check_url(rep, sw, "url", src.get("url"))
            if src.get("kind") not in SOURCE_KINDS:
                rep.err(sw, f"kind {src.get('kind')!r} not in enum")

        if not s.get("updated"):
            rep.warn(w, "no updated date")

    for m in models.values():
        used = any(s.get("model") == m["id"] for s in setups.values())
        if not used:
            rep.warn("models", f"{m['id']} has no setups — it will not appear in the directory")

    for line in rep.warnings:
        print(f"WARN  {line}")
    for line in rep.errors:
        print(f"ERROR {line}")

    print(
        f"\n{len(setups)} setups · {len(models)} models · {len(hardware)} hardware · "
        f"{len(engines)} engines · {len(pub_ids)} publishers"
    )
    print(f"{len(rep.errors)} errors, {len(rep.warnings)} warnings")

    if rep.errors or (strict and rep.warnings):
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
