#!/usr/bin/env python3
"""Vet research-agent candidates against the directory's rules before merging.

Reads /tmp/research_hf.json, /tmp/research_github.json, /tmp/research_forum.json,
checks enums and URL resolvability, flags duplicates against existing setups,
and prints a review table. Nothing is written to the dataset here.
"""
import json
import os
import re
import sys
import urllib.request

DATA = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data"
FILES = {
    "hf": "/tmp/research_hf.json",
    "github": "/tmp/research_github.json",
    "forum": "/tmp/research_forum.json",
}

QUANTS = {"bf16", "fp16", "fp8", "nvfp4", "mxfp4", "int8", "int4", "int4-hybrid",
          "awq", "gptq", "autoround", "gguf-q8", "gguf-q6", "gguf-q5", "gguf-q4",
          "gguf-q3", "gguf-q2", "mlx-8", "mlx-6", "mlx-4", "mlx-3", "mlx-2",
          "mixed", "other"}
FORMATS = {"safetensors", "gguf", "mlx", "onnx", "gptq", "awq", "unknown"}
METRICS = {"decode_code", "decode_essay", "decode_chat", "decode_agg",
           "decode_per_stream", "ttft_ms", "task_time_min", "quality_index",
           "bench_code", "bench_toolcall", "bench_mmlu", "bench_gsm8k",
           "bench_humaneval", "bench_other", "memory_gb", "disk_gb"}
UNITS = {"tok/s", "ms", "s", "min", "%", "GB", "score"}
ENGINES = {"sglang", "vllm", "llama-cpp", "ollama", "lm-studio", "mlx-lm",
           "custom-fork"}
HW = {"dgx-spark", "gpu-24gb", "mac-128gb"}


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


def existing_checkpoints():
    out = set()
    d = os.path.join(DATA, "setups")
    for f in os.listdir(d):
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            s = json.load(fh)
        out.add((s["variation"]["checkpoint"].lower(),
                 s["engine"]["id"], tuple(sorted(s["hardware"]))))
    return out


def main():
    have = existing_checkpoints()
    total = 0
    for kind, path in FILES.items():
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
            total += 1
            probs = []
            url = r.get("url") or r.get("repo") or r.get("thread") or ""
            if kind == "hf":
                if r.get("quant") not in QUANTS:
                    probs.append(f"quant={r.get('quant')!r}")
                if r.get("format") not in FORMATS:
                    probs.append(f"format={r.get('format')!r}")
            else:
                eng = r.get("engine")
                if eng not in ENGINES and eng is not None:
                    probs.append(f"engine={eng!r}")
                hw = r.get("hardware")
                if hw not in HW and hw is not None and not str(hw).startswith("other"):
                    probs.append(f"hardware={hw!r}")
                for m in r.get("claimed") or r.get("measurements") or []:
                    if m.get("metric") not in METRICS:
                        probs.append(f"metric={m.get('metric')!r}")
                    if m.get("unit") not in UNITS:
                        probs.append(f"unit={m.get('unit')!r}")
            st = url_status(url)
            if st != "200":
                probs.append(f"url={st}")
            cp = (r.get("checkpoint") or r.get("model") or "").lower()
            dup = any(c == cp for c, _, _ in have)
            name = r.get("checkpoint") or r.get("title") or r.get("thread")
            print(f"  [{i:2}] {'OK ' if not probs else 'FIX'} "
                  f"{'DUP?' if dup else '    '} {str(name)[:60]}")
            if probs:
                print(f"        problems: {', '.join(probs)}")
            quote = r.get("source_quote") or r.get("quote")
            if quote:
                print(f"        quote: {quote[:110]}")
    print(f"\ntotal candidates: {total}")


if __name__ == "__main__":
    sys.exit(main())
