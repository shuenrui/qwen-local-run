#!/usr/bin/env python3
"""Normalize `generation` on model entries so the shelf sorts by lineage.

build.py sorts families by float(generation); a non-numeric value sinks a
family to the bottom. Derive the numeric lineage from the model id and rewrite
only when the stored value disagrees.
"""
import json
import os
import re

MODELS = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data/models"

SPECIAL = {
    "coder-next": "3.5",   # Qwen3-Coder-Next carries the Qwen3-Next hybrid architecture
    "next-80b": "3.5",     # Qwen3-Next-80B-A3B debuted the GDN hybrid in the 3.5 line
}


def lineage(mid):
    for key, gen in SPECIAL.items():
        if key in mid:
            return gen
    m = re.match(r"^qwen3-(\d)-", mid)
    return f"3.{m.group(1)}" if m else None


changed = 0
for name in sorted(os.listdir(MODELS)):
    if not name.endswith(".json"):
        continue
    p = os.path.join(MODELS, name)
    d = json.load(open(p, encoding="utf-8"))
    want = lineage(d["id"])
    if want and str(d.get("generation")) != want:
        print(f"{d['id']}: generation {d.get('generation')!r} -> {want!r}")
        d["generation"] = want
        json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(p, "a", encoding="utf-8").write("\n")
        changed += 1
print(f"normalized {changed} model entries")
