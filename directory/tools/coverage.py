#!/usr/bin/env python3
"""Facet coverage report for the setup dataset.

Prints one table per facet. Every table has the same columns:

    value | setups | measured | runnable | box | forum | vendor | untested

Facets are derived from the data, never hand-typed, so the categories cannot
drift between reports:

    generation    models/<id>.generation
    line          derived from model id + architecture.kind
                  (dense | moe | coder | next-hybrid | vl | omni | flash)
    size class    derived from architecture.params_total_b
    format        variation.format
    quant         variation.quant
    engine        engine.id (+ fork marker)
    spec decode   engine.spec_decode
    hardware      each id in hardware[] (a setup can appear under several)
    evidence      provenance_tier
    schema state  legacy | legacy-with-measurement-ids | schema-v2
    v2 blocks     optional schema-v2 blocks present in a setup
    technique ids canonical technique packets referenced by setup claims
    readiness     has-command x has-decode-measurement

    python3 directory/tools/coverage.py            # human-readable tables
    python3 directory/tools/coverage.py --json     # machine-readable dict
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import validate as V  # noqa: E402  shared schema-v2 enums and field names

DATA = os.path.join(HERE, os.pardir, "data")

SPEED_PREFIXES = ("decode_", "prefill_", "ttft_")


def load():
    models = {}
    for fn in sorted(os.listdir(os.path.join(DATA, "models"))):
        if fn.endswith(".json"):
            m = json.load(open(os.path.join(DATA, "models", fn)))
            models[m["id"]] = m
    setups = []
    for fn in sorted(os.listdir(os.path.join(DATA, "setups"))):
        if fn.endswith(".json") and not fn.startswith("_"):
            setups.append(json.load(open(os.path.join(DATA, "setups", fn))))
    techniques = {}
    tech_dir = os.path.join(DATA, "techniques")
    if os.path.isdir(tech_dir):
        for fn in sorted(os.listdir(tech_dir)):
            if fn.endswith(".json") and not fn.startswith("_"):
                t = json.load(open(os.path.join(tech_dir, fn)))
                techniques[t.get("id", fn[:-5])] = t
    return models, setups, techniques


def line_of(model):
    mid = model["id"]
    kind = (model.get("architecture") or {}).get("kind", "")
    if "-vl-" in mid or mid.endswith("-vl"):
        return "vl"
    if "-omni-" in mid:
        return "omni"
    if "flash" in mid:
        return "flash"
    if "coder" in mid:
        return "coder"
    if "next" in mid:
        return "next-hybrid"
    return kind or "dense"


def size_class_of(model):
    p = (model.get("architecture") or {}).get("params_total_b")
    if p is None:
        return "unknown"
    if p <= 2:
        return "<=2B"
    if p <= 9:
        return "3-9B"
    if p <= 40:
        return "10-40B"
    if p <= 130:
        return "41-130B"
    return ">130B"


def has_command(s):
    run = s.get("run") or {}
    if run.get("command"):
        return True
    return any(st.get("kind") == "cmd" for st in run.get("steps") or [])


def has_speed(s):
    return any(
        (m.get("metric") or "").startswith(SPEED_PREFIXES)
        for m in s.get("measurements") or []
    )


def evidence_of(s):
    return s.get("provenance_tier") or "untested"


def schema_state_of(s):
    if s.get("schema_version") == 2:
        return "schema-v2"
    if has_v2_evidence_blocks(s):
        return "v2-block-without-version"
    if has_measurement_ids(s):
        return "legacy-with-measurement-ids"
    return "legacy"


def has_measurement_ids(s):
    measurements = s.get("measurements") or []
    return bool(measurements) and all(
        isinstance(m, dict) and m.get("id") for m in measurements
    )


def has_v2_evidence_blocks(s):
    setup_keys = V.V2_SETUP_KEYS - {"schema_version"}
    if any(k in s for k in setup_keys):
        return True
    for m in s.get("measurements") or []:
        if isinstance(m, dict) and any(k in m for k in ("conditions", "evidence")):
            return True
    for src in s.get("sources") or []:
        if isinstance(src, dict) and any(k in src for k in ("locator", "archive_path", "lineage_id", "retrieved")):
            return True
    return False


def v2_blocks_of(s):
    blocks = []
    if s.get("schema_version") == 2:
        blocks.append("schema_version")
    if has_measurement_ids(s):
        blocks.append("measurement-ids")
    if any(isinstance(m, dict) and m.get("conditions") for m in s.get("measurements") or []):
        blocks.append("measurement-conditions")
    if any(isinstance(m, dict) and m.get("evidence") for m in s.get("measurements") or []):
        blocks.append("measurement-evidence")
    for key in ("interconnect", "serving", "correctness", "known_failures",
                "capability_observations", "evidence"):
        if s.get(key):
            blocks.append(key)
    req = s.get("requirements") or {}
    if req.get("memory_profile"):
        blocks.append("requirements.memory_profile")
    if req.get("offload"):
        blocks.append("requirements.offload")
    engine = s.get("engine") or {}
    if engine.get("spec_decode_profile"):
        blocks.append("engine.spec_decode_profile")
    if engine.get("fork_revision") or engine.get("kernel_patches"):
        blocks.append("engine.revision-or-patches")
    run = s.get("run") or {}
    if run.get("repo_revision"):
        blocks.append("run.repo_revision")
    return blocks or ["none"]


def technique_ids_of(s):
    ids = set()
    evidence = s.get("evidence") or {}
    for claim in evidence.get("claims") or []:
        if isinstance(claim, dict) and claim.get("technique_id"):
            ids.add(claim["technique_id"])
    return sorted(ids)


def facet_values(s, models):
    model = models.get(s.get("model"), {})
    engine = s.get("engine") or {}
    eid = engine.get("id") or "?"
    if engine.get("requires_fork"):
        eid += " (fork)"
    vals = {
        "generation": model.get("generation", "?"),
        "line": line_of(model) if model else "?",
        "size class": size_class_of(model) if model else "?",
        "format": (s.get("variation") or {}).get("format", "?"),
        "quant": (s.get("variation") or {}).get("quant", "?"),
        "engine": eid,
        "spec decode": engine.get("spec_decode") or "none",
        "hardware": [(h.get("id") if isinstance(h, dict) else h) for h in (s.get("hardware") or [])] or ["?"],
        "evidence": evidence_of(s),
        "schema state": schema_state_of(s),
        "v2 blocks": v2_blocks_of(s),
        "technique ids": technique_ids_of(s) or ["none"],
        "readiness": ("runnable" if has_command(s) else "no-command")
        + ("+measured" if has_speed(s) else "+unmeasured"),
    }
    return vals


def report(models, setups):
    facets = [
        "generation", "line", "size class", "format", "quant",
        "engine", "spec decode", "hardware", "evidence", "schema state",
        "v2 blocks", "technique ids", "readiness",
    ]
    tables = {}
    for f in facets:
        rows = {}
        for s in setups:
            vals = facet_values(s, models)
            keys = vals[f] if isinstance(vals[f], list) else [vals[f]]
            for k in keys:
                r = rows.setdefault(
                    k,
                    {"setups": 0, "measured": 0, "runnable": 0,
                     "box": 0, "forum": 0, "vendor": 0, "untested": 0},
                )
                r["setups"] += 1
                if has_speed(s):
                    r["measured"] += 1
                if has_command(s):
                    r["runnable"] += 1
                tier = evidence_of(s)
                r[tier if tier in ("box", "forum", "vendor") else "untested"] += 1
        tables[f] = dict(sorted(rows.items(), key=lambda kv: -kv[1]["setups"]))
    return tables


def print_tables(tables):
    cols = ["setups", "measured", "runnable", "box", "forum", "vendor", "untested"]
    for f, rows in tables.items():
        print(f"\n## {f}")
        w = max([len(k) for k in rows] + [5])
        print(f"{'value'.ljust(w)}  " + "  ".join(c.rjust(8) for c in cols))
        for k, r in rows.items():
            print(f"{k.ljust(w)}  " + "  ".join(str(r[c]).rjust(8) for c in cols))


def main():
    models, setups, techniques = load()
    tables = report(models, setups)
    if "--json" in sys.argv:
        print(json.dumps({"techniques": len(techniques), "tables": tables}, indent=1))
    else:
        print(f"{len(setups)} setups, {len(models)} models, {len(techniques)} techniques")
        print_tables(tables)


if __name__ == "__main__":
    main()
