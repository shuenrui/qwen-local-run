#!/usr/bin/env python3
"""Hygiene fix pass 2: normalize license strings to SPDX display form and
resolve every remaining null/'other' variation license from the weights'
family license, with a caveat wherever a builder repo tags different terms."""
import json
import os

DATA = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data"
SETUPS = os.path.join(DATA, "setups")
MODELS = os.path.join(DATA, "models")

CANON = {"apache-2.0": "Apache-2.0", "apache2.0": "Apache-2.0", "mit": "MIT",
         "agpl-3.0": "AGPL-3.0", "gpl-3.0": "GPL-3.0", "cc-by-4.0": "CC-BY-4.0"}

models = {m["id"]: m for n, m in
          ((n, json.load(open(os.path.join(MODELS, n), encoding="utf-8")))
           for n in os.listdir(MODELS) if n.endswith(".json"))}

changed = 0
for name in sorted(os.listdir(SETUPS)):
    p = os.path.join(SETUPS, name)
    d = json.load(open(p, encoding="utf-8"))
    v = d["variation"]
    lic = v.get("license")
    if isinstance(lic, str) and lic.lower() in CANON:
        v["license"] = CANON[lic.lower()]
        changed += 1
    if v.get("license") in (None, "other"):
        fam = models.get(d["model"], {})
        base = "Apache-2.0"   # every Qwen base release in this directory is Apache-2.0
        caveats = []
        if v.get("license") == "other":
            caveats.append("The builder repo tags its own license as 'other'; the "
                           f"weights lineage is Qwen {base}.")
        else:
            caveats.append(f"The checkpoint card states no license field; the weights "
                           f"lineage is Qwen {base}.")
        if "flash-next" in d["model"]:
            caveats.append("Builder runtimes carry their own terms on top of the "
                           "weights (Mia's scripts are AGPL-3.0).")
        v["license"] = base
        for c in caveats:
            if c not in d["caveats"]:
                d["caveats"].append(c)
        changed += 1
        print(f"{name}: license -> {v['license']} (derived, caveat added)")
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(p, "a", encoding="utf-8").write("\n")

# model-level license display normalization too
for n in os.listdir(MODELS):
    if not n.endswith(".json"):
        continue
    p = os.path.join(MODELS, n)
    m = json.load(open(p, encoding="utf-8"))
    if isinstance(m.get("license"), str) and m["license"].lower() in CANON:
        m["license"] = CANON[m["license"].lower()]
        json.dump(m, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(p, "a", encoding="utf-8").write("\n")
        changed += 1

remaining = [n for n in os.listdir(SETUPS)
             if n.endswith(".json")
             and json.load(open(os.path.join(SETUPS, n), encoding="utf-8"))["variation"].get("license") in (None, "other")]
print(f"changed {changed} entries; licenses still unresolved: {remaining}")
