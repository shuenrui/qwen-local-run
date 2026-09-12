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
    "decode_per_stream", "prefill_tok_s", "ttft_ms", "task_time_min",
    # quality
    "quality_index", "bench_code", "bench_toolcall", "bench_mmlu",
    "bench_gsm8k", "bench_humaneval", "bench_other",
    # footprint
    "memory_gb", "disk_gb",
}

UNITS = {"tok/s", "ms", "s", "min", "%", "GB", "score"}
STATS = {"mean", "median", "peak"}

PROVENANCE = {"box", "forum", "vendor"}
PROV_RANK = {"box": 3, "forum": 2, "vendor": 1, None: 0}

STATUS = {"measured", "reported", "claimed", "untested", "broken"}
PRACTICAL_STATUS = {"selected", "not_verified"}
PRACTICAL_QUANTS = {
    "bf16", "fp16", "fp8", "nvfp4", "mxfp4", "int8", "int4", "int4-hybrid",
    "awq", "gptq", "autoround", "gguf-q8", "gguf-q6", "gguf-q5", "gguf-q4",
    "mlx-8", "mlx-6", "mlx-4",
}

SOURCE_KINDS = {
    "repo", "model", "thread", "post", "video", "docs", "paper", "blog",
    "benchmark", "other",
}

URL_RE = re.compile(r"^https?://\S+$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# device spec (data/device-schema.json): field shape per section. Numbers accept
# null ("vendor does not publish") but never strings; strings must be non-empty.
DEVICE_SECTIONS = {
    "identity": {
        "required": ("name", "chip", "manufacturer"),
        "strings": ("name", "chip", "manufacturer", "os", "form_factor", "sku"),
        "numbers": (),
    },
    "memory": {
        "required": ("total_gb", "type"),
        "strings": ("type", "note"),
        "numbers": ("total_gb", "usable_gb", "bandwidth_gbs", "interface_bits", "channels"),
        "bools": ("unified",),
    },
    "compute": {
        "required": (),
        "strings": ("cpu_cores", "note"),
        "numbers": ("fp32_tflops", "fp16_dense_tflops", "fp16_sparse_tflops",
                    "fp8_dense_tflops", "fp8_sparse_tflops", "fp4_sparse_pflops",
                    "tensor_ai_tops", "neural_engine_tops"),
    },
    "storage": {
        "required": (),
        "strings": ("type", "note"),
        "numbers": ("read_gbs", "capacity_gb"),
    },
    "thermal": {
        "required": (),
        "strings": ("cooling", "note"),
        "numbers": ("tdp_watts", "psu_watts"),
    },
}
DEVICE_TOP_KEYS = set(DEVICE_SECTIONS) | {"variants", "sources"}
DEVICE_VARIANT_KEYS = {"id", "name", "chip", "memory_configs", "bandwidth_gbs",
                       "fp32_tflops", "tensor_ai_tops", "neural_engine_tops",
                       "tdp_watts", "note"}

REQUIRED_SETUP = [
    "id", "title", "model", "variation", "engine", "hardware",
    "requirements", "run", "status", "sources",
]
REQUIRED_VARIATION = ["checkpoint", "publisher", "quant", "format", "url"]
REQUIRED_ENGINE = ["id", "config"]
REQUIRED_RUN = ["repo"]
RUN_STEP_KINDS = {"cmd", "do"}
RUN_STEP_FIELDS = {"kind", "text"}


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


def check_device(rep: Report, where: str, dev, hw=None) -> None:
    """Validate a device spec block (data/device-schema.json).

    `hw` is the enclosing hardware record, when the block sits in one; it
    enables the cross-checks that keep the block and the record's top-level
    numbers from drifting apart. `hw=None` for per-setup override blocks.
    """
    if not isinstance(dev, dict):
        rep.err(where, f"device must be an object, got {type(dev).__name__}")
        return
    unknown = set(dev) - DEVICE_TOP_KEYS
    if unknown:
        rep.err(where, f"device has unknown keys {sorted(unknown)}; allowed: {sorted(DEVICE_TOP_KEYS)}")

    for section, spec in DEVICE_SECTIONS.items():
        if section not in dev:
            if spec["required"]:
                rep.err(where, f"device.{section} missing (requires {list(spec['required'])})")
            continue
        sec = dev[section]
        if sec is None:
            continue
        if not isinstance(sec, dict):
            rep.err(where, f"device.{section} must be an object")
            continue
        sw = f"{where}.device.{section}"
        unknown = set(sec) - set(spec["strings"]) - set(spec["numbers"]) - set(spec.get("bools", ()))
        if unknown:
            rep.err(sw, f"unknown keys {sorted(unknown)}")
        num_fields, str_fields = set(spec["numbers"]), set(spec["strings"])
        bool_fields = set(spec.get("bools", ()))
        for f in spec["required"]:
            val = sec.get(f)
            if f in num_fields:
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    rep.err(sw, f"{f} must be a number, got {val!r}")
            elif not isinstance(val, str) or not val.strip():
                rep.err(sw, f"{f} must be a non-empty string, got {val!r}")
        for f in spec["strings"]:
            if f in sec and sec[f] is not None and (not isinstance(sec[f], str) or not sec[f].strip()):
                rep.err(sw, f"{f} must be a non-empty string or null, got {sec[f]!r}")
        for f in spec["numbers"]:
            val = sec.get(f)
            if val is None:
                continue
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                rep.err(sw, f"{f} must be a number or null, got {val!r}")
            elif val < 0:
                rep.err(sw, f"{f} must be >= 0, got {val!r}")
        for f in bool_fields:
            val = sec.get(f)
            if val is not None and not isinstance(val, bool):
                rep.err(sw, f"{f} must be a boolean or null, got {val!r}")

    mem = dev.get("memory") or {}
    if isinstance(mem.get("total_gb"), (int, float)) and not isinstance(mem["total_gb"], bool) \
            and mem["total_gb"] <= 0:
        rep.err(f"{where}.device.memory", f"total_gb must be positive, got {mem['total_gb']!r}")
    bw = mem.get("bandwidth_gbs")
    if isinstance(bw, (int, float)) and not isinstance(bw, bool) and bw <= 0:
        rep.err(f"{where}.device.memory", f"bandwidth_gbs must be positive, got {bw!r}")

    variants = dev.get("variants")
    if variants is not None:
        if not isinstance(variants, list):
            rep.err(f"{where}.device.variants", "must be a list")
        else:
            seen = set()
            for i, var in enumerate(variants):
                vw = f"{where}.device.variants[{i}]"
                if not isinstance(var, dict):
                    rep.err(vw, "must be an object")
                    continue
                unknown = set(var) - DEVICE_VARIANT_KEYS
                if unknown:
                    rep.err(vw, f"unknown keys {sorted(unknown)}")
                for f in ("id", "name", "chip"):
                    if not isinstance(var.get(f), str) or not var[f].strip():
                        rep.err(vw, f"{f} must be a non-empty string, got {var.get(f)!r}")
                if isinstance(var.get("id"), str) and var["id"] in seen:
                    rep.err(vw, f"duplicate variant id {var['id']!r}")
                seen.add(var.get("id"))
                vbw = var.get("bandwidth_gbs")
                if isinstance(vbw, bool) or not isinstance(vbw, (int, float)) or vbw <= 0:
                    rep.err(vw, f"bandwidth_gbs must be a positive number, got {vbw!r}")
                elif hw and isinstance(hw.get("bandwidth_range_gbs"), list) and len(hw["bandwidth_range_gbs"]) == 2:
                    lo, hi = hw["bandwidth_range_gbs"]
                    if not (lo <= vbw <= hi):
                        rep.err(vw, f"bandwidth {vbw} outside the class range [{lo}, {hi}]; "
                                    f"widen the range or move the SKU to another class")

    srcs = dev.get("sources")
    if not isinstance(srcs, list) or not srcs:
        rep.err(f"{where}.device.sources", "must be a non-empty list of {url, note}")
    else:
        for i, src in enumerate(srcs):
            if not isinstance(src, dict):
                rep.err(f"{where}.device.sources[{i}]", "must be an object with url and note")
                continue
            u = src.get("url")
            if not isinstance(u, str) or not URL_RE.match(u):
                rep.err(f"{where}.device.sources[{i}]", f"url {u!r} is not an http(s) URL")
            if not isinstance(src.get("note"), str) or not src["note"].strip():
                rep.err(f"{where}.device.sources[{i}]", "note must state which figures this source backs")

    if hw:
        if hw.get("vendor") == "Apple" and mem.get("unified") is not True:
            rep.warn(f"{where}.device.memory",
                     "Apple hardware should state memory.unified: true (CPU and GPU share one pool)")
        if not hw.get("bandwidth_range_gbs") and hw.get("bandwidth_gbs") is not None \
                and bw is not None and bw != hw["bandwidth_gbs"]:
            rep.err(f"{where}.device.memory",
                    f"bandwidth_gbs {bw} != hardware record's bandwidth_gbs {hw['bandwidth_gbs']} — "
                    f"an exact-SKU device block must match its record")


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
        baseline = m.get("practical_baseline")
        if not isinstance(baseline, dict):
            rep.err(w, "practical_baseline must be an object")
        else:
            bstatus = baseline.get("status")
            if bstatus not in PRACTICAL_STATUS:
                rep.err(w, f"practical_baseline.status {bstatus!r} not in {sorted(PRACTICAL_STATUS)}")
            reviewed = baseline.get("reviewed")
            if not isinstance(reviewed, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", reviewed):
                rep.err(w, "practical_baseline.reviewed must be YYYY-MM-DD")
            target = baseline.get("setup")
            if bstatus == "not_verified":
                if target is not None:
                    rep.err(w, "not_verified practical baseline must set setup to null")
                if not isinstance(baseline.get("reason"), str) or not baseline["reason"].strip():
                    rep.err(w, "not_verified practical baseline requires a reason")
            elif bstatus == "selected":
                if not isinstance(baseline.get("rationale"), str) or not baseline["rationale"].strip():
                    rep.err(w, "selected practical baseline requires a rationale")
                setup = setups.get(target)
                if setup is None:
                    rep.err(w, f"practical_baseline.setup {target!r} is not a setup id")
                else:
                    if setup.get("model") != mid:
                        rep.err(w, f"practical baseline setup belongs to {setup.get('model')!r}, not {mid!r}")
                    quant = setup.get("variation", {}).get("quant")
                    if quant not in PRACTICAL_QUANTS:
                        rep.err(w, f"practical baseline quant {quant!r} is below the stable 4-bit-or-better policy")
                    if setup.get("status") not in {"measured", "reported"}:
                        rep.err(w, "practical baseline setup must be measured or reported")
                    run = setup.get("run", {})
                    if not run.get("command") and len(run.get("steps") or []) < 2:
                        rep.err(w, "practical baseline setup needs a command or at least two run steps")

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
        if "device" in h:
            check_device(rep, w, h["device"], hw=h)
        else:
            rep.warn(w, "no device spec — readers cannot see the bandwidth/compute behind "
                        "this hardware's numbers (see data/device-schema.json)")

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
        # Optional per-setup device override: a measurement-specific hardware
        # delta (e.g. an overclocked card). Same shape as the hardware block's
        # device spec, without the record cross-checks.
        if s.get("device") is not None:
            check_device(rep, f"{w} device", s["device"])

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
        rc = run.get("repo_commit")
        if rc is not None and (not isinstance(rc, str) or not rc.strip()):
            rep.err(w, "run.repo_commit must be a non-empty string (commit sha or tag)")
        if not run.get("command") and not run.get("steps"):
            rep.err(w, "run needs a command or steps — this is the 'how to run' directory")
        steps = run.get("steps")
        if steps is not None:
            if not isinstance(steps, list):
                rep.err(w, "run.steps must be a list")
            else:
                for i, step in enumerate(steps):
                    sw = f"{w} run.steps[{i}]"
                    if not isinstance(step, dict):
                        rep.err(sw, "must be an object with exactly 'kind' and 'text'")
                        continue
                    if set(step) != RUN_STEP_FIELDS:
                        rep.err(sw, "must contain exactly 'kind' and 'text'")
                    if step.get("kind") not in RUN_STEP_KINDS:
                        rep.err(sw, f"kind {step.get('kind')!r} not in {sorted(RUN_STEP_KINDS)}")
                    if not isinstance(step.get("text"), str) or not step["text"].strip():
                        rep.err(sw, "text must be a non-empty string")

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
            concurrency = m.get("concurrency")
            if concurrency is not None and (
                isinstance(concurrency, bool)
                or not isinstance(concurrency, int)
                or concurrency <= 0
            ):
                rep.err(mw, f"concurrency must be a positive integer, got {concurrency!r}")
            if m.get("metric") == "decode_agg" and (
                not isinstance(concurrency, int)
                or isinstance(concurrency, bool)
                or concurrency <= 1
            ):
                rep.err(mw, "decode_agg requires concurrency > 1; use decode_per_stream for single-stream or cross-prompt summaries")
            if m.get("stat") is not None and m["stat"] not in STATS:
                rep.err(mw, f"stat {m.get('stat')!r} not in {sorted(STATS)}")
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
            if src.get("mirror_url") is not None:
                check_url(rep, sw, "mirror_url", src.get("mirror_url"))
            if isinstance(src.get("url"), str) and "reddit.com" in src["url"] \
                    and not src.get("mirror_url"):
                rep.err(sw, "reddit.com source requires mirror_url (AGENTS law 10)")
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
