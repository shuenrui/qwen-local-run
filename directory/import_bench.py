#!/usr/bin/env python3
"""Regenerate `box` measurements from bench/ab.py results instead of typing them.

Reads bench/results/<exp>-<stamp>/results.json (rows: model, probe, type,
rep, tokens, seconds, toks_per_s, detail), maps each experiment model to a
setup id via directory/data/bench_map.json, and rewrites that setup's box-tier
measurements from the medians of the run. Forum/vendor measurements are never
touched. Every applied change is also appended to data/measurements.jsonl as an
audit trail.

Usage:
    python3 directory/import_bench.py bench/results/<exp>-<stamp>            # dry run
    python3 directory/import_bench.py bench/results/<exp>-<stamp> --apply    # write

The map file keys are "<experiment model name>@<engine>", e.g.
"qwen38-27b-nvfp4@dflash2". Engines: mtp, dspark, dflash2, none.
"""
import argparse
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MAP = os.path.join(DATA, "bench_map.json")
JSONL = os.path.join(DATA, "measurements.jsonl")

PROBE_METRIC = [
    (r"code", "decode_code"),
    (r"essay|prose", "decode_essay"),
    (r"chat", "decode_chat"),
]


def metric_for(probe, ptype):
    if ptype == "ttft":
        return "ttft_ms"
    for pat, met in PROBE_METRIC:
        if re.search(pat, probe):
            return met
    return "decode_chat"


def load_rows(results_dir):
    with open(os.path.join(results_dir, "results.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc.get("rows", []), doc.get("config", {})


def group(rows):
    """(model, probe, type, streams) -> list of toks_per_s (or seconds for ttft)."""
    out = {}
    for r in rows:
        streams = None
        if r["type"] == "ladder":
            m = re.search(r"streams=(\d+)", str(r.get("detail", "")))
            streams = int(m.group(1)) if m else r.get("rep")
        key = (r["model"], r["probe"], r["type"], streams)
        out.setdefault(key, []).append(r)
    return out


def run_date(results_dir):
    m = re.search(r"(\d{8})-\d{6}$", os.path.basename(results_dir.rstrip("/")))
    if not m:
        return None
    d = m.group(1)
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("--engine", default=None,
                    help="engine the run used (mtp|dspark|dflash2|none); results.json "
                         "does not record it, so pass it when a model has several lanes")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(MAP):
        sys.exit(f"missing {MAP}; create it before importing (see module docstring)")
    with open(MAP, encoding="utf-8") as fh:
        bench_map = json.load(fh)

    rows, _cfg = load_rows(args.results_dir)
    date = run_date(args.results_dir)
    groups = group(rows)

    plans = []  # (setup_id, metric, value, unit, n, method, extra_note)
    for (model, probe, ptype, streams), rs in sorted(groups.items()):
        cands = [k for k in bench_map if k.partition("@")[0] == model]
        if args.engine:
            setup_id = bench_map.get(f"{model}@{args.engine}")
        elif len(cands) == 1:
            setup_id = bench_map[cands[0]]
        else:
            setup_id = None
        if not setup_id:
            want = f"--engine {args.engine or '<engine>'}"
            print(f"UNMAPPED  {model} probe={probe} type={ptype} — "
                  f"candidates {[c.partition('@')[2] for c in cands] or 'none'}; pass {want}")
            continue
        metric = metric_for(probe, ptype)
        if ptype == "ttft":
            vals = [r["seconds"] * 1000 for r in rs]
            unit = "ms"
        else:
            vals = [r["toks_per_s"] for r in rs]
            unit = "tok/s"
        med = round(statistics.median(vals), 1)
        n = len(vals)
        method = (f"bench/ab.py {ptype} probe '{probe}', median of {n}, "
                  "tokens counted from the server's completion_tokens")
        note = probe
        if ptype == "ladder":
            metric = "decode_agg"
            per = [f"{float(r['toks_per_s']) / streams:.1f}" for r in rs]
            note = f"aggregate at {streams} concurrent streams; per-stream ~{'/'.join(per)}"
        rng = [round(min(vals), 1), round(max(vals), 1)] if n > 1 else None
        plans.append((setup_id, metric, med, unit, n, method, note, rng, streams))

    print(f"{len(plans)} measurement groups from {args.results_dir} (date {date})")
    by_setup = {}
    for p in plans:
        by_setup.setdefault(p[0], []).append(p)
    for sid, items in sorted(by_setup.items()):
        path = os.path.join(DATA, "setups", sid + ".json")
        if not os.path.exists(path):
            print(f"  MISSING setup {sid}")
            continue
        print(f"  {sid}:")
        for (_s, metric, val, unit, n, method, note, rng, streams) in items:
            print(f"     {metric:16s} {val:>8} {unit:5s} n={n}  ({note})")
        if not args.apply:
            continue
        with open(path, encoding="utf-8") as fh:
            setup = json.load(fh)
        # box rows for these metrics are regenerated, never duplicated
        keep = [m for m in setup.get("measurements", [])
                if m.get("provenance") != "box"
                or m["metric"] not in {i[1] for i in items}]
        for (_s, metric, val, unit, n, method, note, rng, streams) in items:
            entry = {"metric": metric, "value": val, "unit": unit, "provenance": "box",
                     "date": date, "n": n, "method": method, "note": note}
            if rng:
                entry["range"] = rng
            keep.append(entry)
        setup["measurements"] = keep
        setup["status"] = "measured"
        setup["provenance_tier"] = "box"
        setup["updated"] = date or setup.get("updated")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(setup, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        with open(JSONL, "a", encoding="utf-8") as fh:
            for (_s, metric, val, unit, n, method, note, rng, streams) in items:
                fh.write(json.dumps({"setup": sid, "metric": metric, "value": val,
                                     "unit": unit, "provenance": "box", "date": date,
                                     "n": n, "source": os.path.basename(
                                         args.results_dir.rstrip("/"))}) + "\n")
    if not args.apply:
        print("\ndry run: pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
