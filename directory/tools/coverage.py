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
    readiness     has-command x has-decode-measurement

    python3 directory/tools/coverage.py            # human-readable tables
    python3 directory/tools/coverage.py --json     # machine-readable dict
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
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
    return models, setups


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
        "hardware": s.get("hardware") or ["?"],
        "evidence": evidence_of(s),
        "readiness": ("runnable" if has_command(s) else "no-command")
        + ("+measured" if has_speed(s) else "+unmeasured"),
    }
    return vals


def report(models, setups):
    facets = [
        "generation", "line", "size class", "format", "quant",
        "engine", "spec decode", "hardware", "evidence", "readiness",
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
    models, setups = load()
    tables = report(models, setups)
    if "--json" in sys.argv:
        print(json.dumps(tables, indent=1))
    else:
        print(f"{len(setups)} setups, {len(models)} models")
        print_tables(tables)


if __name__ == "__main__":
    main()
