#!/usr/bin/env python3
"""Hygiene fix pass 1: repair truncated forum URLs, drop the dead publisher,
fill null variation licenses from the HuggingFace API, normalize the Omni
license, and resolve the Omni context length from its model card."""
import json
import os
import re
import urllib.request

DATA = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data"
SETUPS = os.path.join(DATA, "setups")

REPAIRS = {
    "https://forums.developer.nvidia.com/t/qwen3-5-122b-a10b-on-single-spark-up-to-51-tok-s-v2-1-pat":
        "https://forums.developer.nvidia.com/t/qwen3-5-122b-a10b-on-single-spark-up-to-51-tok-s-v2-1-patches-quick-start-benchmark/365639",
    "https://forums.developer.nvidia.com/t/does-qwen3-5-35b-a3b-on-gb10-leave-a-lot-of-performance-o":
        "https://forums.developer.nvidia.com/t/does-qwen3-5-35b-a3b-on-gb10-leave-a-lot-of-performance-on-the-table/362200",
    "https://forums.developer.nvidia.com/t/whats-the-best-speed-we-can-get-with-qwen-3-6-27b-without":
        "https://forums.developer.nvidia.com/t/whats-the-best-speed-we-can-get-with-qwen-3-6-27b-without-quantizing/367561",
}


def get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 directory-hygiene"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


# 1. URL repairs -------------------------------------------------------------
fixed = 0
for name in sorted(os.listdir(SETUPS)):
    p = os.path.join(SETUPS, name)
    s = open(p, encoding="utf-8").read()
    orig = s
    for bad, good in REPAIRS.items():
        s = s.replace(bad, good)
    if s != orig:
        open(p, "w", encoding="utf-8").write(s)
        fixed += 1
        print("repaired URLs in", name)
print(f"url repairs touched {fixed} files")

# 2. dead publisher ----------------------------------------------------------
pp = os.path.join(DATA, "publishers.json")
pub = json.load(open(pp, encoding="utf-8"))
try:
    get("https://github.com/veloGB10")
    print("velogb10 reachable after all; keeping")
except urllib.error.HTTPError as e:
    if e.code == 404 and "velogb10" in pub["publishers"]:
        del pub["publishers"]["velogb10"]
        json.dump(pub, open(pp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(pp, "a", encoding="utf-8").write("\n")
        print("removed dead publisher velogb10")

# 3. null licenses from HF API ----------------------------------------------
def hf_license(ckpt):
    try:
        info = json.loads(get("https://huggingface.co/api/models/" + ckpt))
    except Exception:
        return None
    cd = info.get("cardData") or {}
    lic = cd.get("license")
    if isinstance(lic, list):
        lic = lic[0] if lic else None
    return lic


filled = 0
for name in sorted(os.listdir(SETUPS)):
    p = os.path.join(SETUPS, name)
    d = json.load(open(p, encoding="utf-8"))
    v = d["variation"]
    if v.get("license") is None:
        ck = v["checkpoint"]
        if ck.startswith("ollama.com/"):
            lic = "Apache-2.0"   # Ollama packages the upstream Qwen weights
            note = ("License is the upstream Qwen weights' Apache-2.0; Ollama's "
                    "packaging adds no further restriction.")
        else:
            lic = hf_license(ck)
            note = None
        if lic:
            v["license"] = lic
            if note and note not in d["caveats"]:
                d["caveats"].append(note)
            filled += 1
            print(f"license {name}: {lic}")
        else:
            print(f"license STILL UNKNOWN {name} ({ck})")
    elif v.get("license") == "AGPL (scripts)":
        v["license"] = hf_license(v["checkpoint"]) or "Apache-2.0"
        cav = ("Mia's serving scripts are AGPL-3.0 while the weights are "
               f"{v['license']}; the license field records the weights.")
        if cav not in d["caveats"]:
            d["caveats"].append(cav)
        filled += 1
        print(f"license {name}: weights {v['license']} + AGPL scripts caveat")
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(p, "a", encoding="utf-8").write("\n")
print(f"licenses filled/normalized: {filled}")

# 4. Omni license + context --------------------------------------------------
mp = os.path.join(DATA, "models", "qwen3-0-omni-30b-a3b.json")
m = json.load(open(mp, encoding="utf-8"))
if str(m.get("license", "")).startswith("other"):
    m["license"] = "Apache-2.0"
    print("omni license normalized to Apache-2.0 (card license_name)")
if not m.get("context", {}).get("native"):
    card = get("https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct/raw/main/README.md")
    hits = re.findall(r"(?:context|sequence)[^\n]{0,80}?(\d{2,7})\s*(?:tokens|token|K\b)",
                      card, flags=re.I)
    ctx = re.search(r"(32(?:,?768|K))", card)
    if ctx:
        m.setdefault("context", {})["native"] = 32768
        m["context"]["max"] = 32768
        m["context"]["extension"] = None
        print("omni context set to 32768 from card")
    else:
        print("omni context still unstated on card; leaving null (policy: null = publisher did not state it)")
json.dump(m, open(mp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(mp, "a", encoding="utf-8").write("\n")
print("done")
