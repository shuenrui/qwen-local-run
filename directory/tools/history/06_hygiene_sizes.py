#!/usr/bin/env python3
"""Hygiene fix pass 3: recompute every variation.size_gb from the HuggingFace
tree endpoint (the siblings endpoint returns 0 for LFS files, which silently
poisoned sizes). Safetensors checkpoints sum their shards; GGUF/MLX pick the
file matching the setup's quant tier."""
import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

DATA = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data"
SETUPS = os.path.join(DATA, "setups")

PATTERNS = {
    "gguf-q4": ["UD-Q4_K_XL", "Q4_K_M", "Q4_1", "Q4_0"],
    "gguf-q3": ["UD-Q3_K_XL", "Q3_K_M", "Q3_0"],
    "gguf-q2": ["UD-IQ2_XS", "UD-Q2_K_XL", "IQ2_S", "IQ2_M"],
    "gguf-q8": ["Q8_0"],
    "gguf-q5": ["Q5_K_M"],
    "mxfp4": ["MXFP4"],
    "mlx-4": ["4bit"],
    "mlx-8": ["8bit"],
}


def tree(ckpt):
    req = urllib.request.Request(
        f"https://huggingface.co/api/models/{ckpt}/tree/main?recursive=true",
        headers={"User-Agent": "directory-hygiene"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def compute(ckpt, fmt, quant):
    try:
        files = tree(ckpt)
    except Exception as e:
        return None, f"tree fetch failed: {type(e).__name__}"
    if fmt == "gguf":
        for pat in PATTERNS.get(quant, []):
            hits = [f for f in files if f["path"].endswith(".gguf")
                    and pat in f["path"].upper()]
            if hits:
                return round(sum(f.get("size") or 0 for f in hits) / 1e9, 1), pat
        return None, "no gguf file matched " + str(quant)
    if fmt == "mlx":
        for pat in PATTERNS.get(quant, ["4bit"]):
            hits = [f for f in files if pat in f["path"]
                    and (f["path"].endswith(".safetensors") or f["path"].endswith(".npz"))]
            if hits:
                return round(sum(f.get("size") or 0 for f in hits) / 1e9, 1), pat
        return None, "no mlx dir matched"
    hits = [f for f in files if f["path"].endswith(".safetensors")]
    if hits:
        return round(sum(f.get("size") or 0 for f in hits) / 1e9, 1), "safetensors sum"
    return None, "no safetensors shards"


names = [n for n in sorted(os.listdir(SETUPS)) if n.endswith(".json")]
setups = {n: json.load(open(os.path.join(SETUPS, n), encoding="utf-8")) for n in names}
jobs = []
for n, d in setups.items():
    v = d["variation"]
    if v["url"].startswith("https://huggingface.co/"):
        jobs.append((n, v["checkpoint"], v["format"], v["quant"]))

with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(lambda j: (j[0],) + compute(j[1], j[2], j[3]), jobs))

fixed = 0
for n, size, how in results:
    d = setups[n]
    old = d["variation"].get("size_gb")
    if size is None:
        print(f"  UNRESOLVED {n}: {how}")
        continue
    if old != size:
        print(f"  {n}: {old} -> {size} ({how})")
        d["variation"]["size_gb"] = size
        json.dump(d, open(os.path.join(SETUPS, n), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        open(os.path.join(SETUPS, n), "a", encoding="utf-8").write("\n")
        fixed += 1
print(f"sizes corrected on {fixed} setups")
