#!/usr/bin/env python3
"""Merge pass 1: HF-quants + forum-research findings into the directory dataset.

Upgrades three existing setups with forum-sourced measurements and adds new
setups for genuinely new lanes. Every new checkpoint URL is re-verified against
the HuggingFace API before writing; unverifiable entries are skipped and listed.
"""
import json
import os
import urllib.request

SETUPS = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data/setups"
UPDATED = "2026-09-05"
NVIDIA_122B = ("https://forums.developer.nvidia.com/t/"
               "qwen3-5-122b-a10b-on-single-spark-up-to-51-tok-s-v2-1-pat")
NVIDIA_35B = ("https://forums.developer.nvidia.com/t/"
              "does-qwen3-5-35b-a3b-on-gb10-leave-a-lot-of-performance-o")
NVIDIA_36 = ("https://forums.developer.nvidia.com/t/"
             "whats-the-best-speed-we-can-get-with-qwen-3-6-27b-without")
HASSO_RAW = "https://raw.githubusercontent.com/hasso5703/dgx-spark-qwen38/main/README.md"
HASSO = "https://github.com/hasso5703/dgx-spark-qwen38"
HF122B = "https://huggingface.co/unsloth/Qwen3.5-122B-A10B-GGUF/discussions/3"

skipped = []


def hf_size(checkpoint):
    """Size in GB from the HF research file, else None."""
    with open("/tmp/research_hf.json", encoding="utf-8") as fh:
        for e in json.load(fh):
            if e["checkpoint"].lower() == checkpoint.lower():
                return e["size_gb"]
    return None


def hf_api_size(checkpoint, pattern=None):
    """Bytes of the repo's weights from the HF API, in GB.

    For GGUF repos a pattern selects the one file (a GGUF repo holds every quant);
    otherwise all .safetensors shards are summed.
    """
    req = urllib.request.Request(
        "https://huggingface.co/api/models/" + checkpoint,
        headers={"User-Agent": "directory-merge"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            info = json.load(r)
    except Exception:
        return None
    files = [(s.get("rfilename") or "", s.get("size") or 0)
             for s in info.get("siblings", [])]
    if pattern:
        pick = [sz for name, sz in files
                if pattern in name.lower() and name.lower().endswith(".gguf")]
        if pick:
            return round(sum(pick) / 1e9, 1)
        return None
    shards = [sz for name, sz in files if name.lower().endswith(".safetensors")]
    if shards:
        return round(sum(shards) / 1e9, 1)
    gg = [sz for name, sz in files if name.lower().endswith(".gguf")]
    return round(max(gg) / 1e9, 1) if gg else None


def url_ok(url):
    req = urllib.request.Request(
        "https://huggingface.co/api/models/" + url.split("huggingface.co/")[-1],
        headers={"User-Agent": "directory-merge"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False


def fm(metric, value, unit, source, date, method, note=None, rng=None, n=None):
    d = {"metric": metric, "value": value, "unit": unit, "provenance": "forum",
         "source": source, "date": date, "method": method}
    if note:
        d["note"] = note
    if rng:
        d["range"] = rng
    if n:
        d["n"] = n
    return d


def setup(sid, title, slug, model, variation, engine, hardware, req, run,
          measurements, caveats, sources, caps=None, status="reported"):
    v = {"license": "Apache-2.0", "downloads": None}
    v.update(variation)
    if v.get("size_gb") is None:
        v["size_gb"] = hf_size(v["checkpoint"])
    if v.get("size_gb") is None:
        v["size_gb"] = hf_api_size(v["checkpoint"], v.pop("file_match", None))
    else:
        v.pop("file_match", None)
    if v.get("size_gb") is None:
        skipped.append((sid, "no size available"))
        return None
    if v["url"].startswith("https://huggingface.co/") and not url_ok(v["url"]):
        skipped.append((sid, "HF url not resolvable: " + v["url"]))
        return None
    e = {"image": None, "requires_fork": False, "draft_model": None,
         "spec_decode": "none", "flags": []}
    e.update(engine)
    s = {
        "id": sid, "title": title, "slug_note": slug, "model": model,
        "status": status, "variation": v, "engine": e, "hardware": hardware,
        "requirements": req,
        "capabilities": caps or {"vision": False, "video": False, "tools": True,
                                 "thinking": True, "long_context": 262144,
                                 "max_context": 262144},
        "run": run, "measurements": measurements, "caveats": caveats,
        "provenance_tier": "forum" if measurements else None,
        "sources": sources, "updated": UPDATED,
    }
    if not measurements:
        s["status"] = "untested"
    return s


def write(s):
    if s is None:
        return
    with open(os.path.join(SETUPS, s["id"] + ".json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wrote", s["id"])


# ---------------------------------------------------------------- upgrades ---
def add_unique(d, new_ms):
    have = {(m["metric"], m["value"], m.get("source")) for m in d["measurements"]}
    for m in new_ms:
        if (m["metric"], m["value"], m.get("source")) not in have:
            d["measurements"].append(m)


def add_src(d, url, kind, note):
    if not any(s["url"] == url for s in d["sources"]):
        d["sources"].append({"url": url, "kind": kind, "note": note})


p = os.path.join(SETUPS, "qwen38-27b-fp8-official.json")
d = json.load(open(p, encoding="utf-8"))
add_unique(d, [
    fm("decode_agg", 108, "tok/s", HASSO_RAW, "2026-08-30",
       "builder's ./bench.sh at 8 concurrent streams on a single DGX Spark",
       "Against 135-148 tok/s for the NVFP4 export at the same concurrency: "
       "FP8 weights cost KV pool, not just disk."),
    fm("memory_gb", 30.9, "GB", HASSO_RAW, "2026-08-30",
       "checkpoint size on disk; SGLang KV pool held 771,139 tokens at fp8_e4m3",
       "The trade this lane makes: 30.9 GB of weights versus 21 GB for NVFP4, "
       "taken straight out of the KV pool on a 128 GB box."),
])
add_src(d, HASSO, "repo", "independent builder's FP8 lane with numbers")
add_src(d, HASSO_RAW, "docs", "README carrying the quoted measurements")
cav = ("The forum numbers above come from a builder lane using "
       "--kv-cache-dtype fp8_e4m3; our own card for these weights is still unbenched, "
       "so treat 108 tok/s at 8 streams as his configuration, not ours.")
if cav not in d["caveats"]:
    d["caveats"].append(cav)
d["status"] = "reported"
d["provenance_tier"] = "forum"
d["updated"] = UPDATED
json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(p, "a", encoding="utf-8").write("\n")
print("upgraded qwen38-27b-fp8-official")

p = os.path.join(SETUPS, "qwen35-122b-a10b-albond-int4-vllm-spark.json")
d = json.load(open(p, encoding="utf-8"))
add_unique(d, [
    fm("decode_chat", 28.3, "tok/s", NVIDIA_122B, "2026-04-05",
       "vLLM 0.19 + Intel AutoRound INT4 + FlashInfer, single stream, single Spark",
       "Baseline before speculative decoding."),
    fm("decode_chat", 38.4, "tok/s", NVIDIA_122B, "2026-04-05",
       "same stack with hybrid INT4+FP8 shared experts and MTP-1, 95% acceptance",
       "'managed to get from 28.3 to 38.4 tok/s with no quality loss'."),
    fm("decode_code", 39.1, "tok/s", NVIDIA_122B, "2026-04-05",
       "512-token code generation, hybrid+MTP, warm cache, run 2"),
])
for cav in (
    "The thread's v2 recipe (post #71) claims 51 tok/s; the details were not "
    "fetched, so that claim is not recorded as a measurement here.",
    "A comment in the same thread reports 56 tok/s aggregate via Open WebUI on a "
    "multi-Spark Ray cluster with eugr/spark-vllm-docker; node count unstated, so "
    "it is not comparable to the single-box rows.",
):
    if cav not in d["caveats"]:
        d["caveats"].append(cav)
d["updated"] = UPDATED
json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(p, "a", encoding="utf-8").write("\n")
print("upgraded qwen35-122b-a10b-albond-int4-vllm-spark")

# ------------------------------------------------------------ new setups ----
M_BENCH = "builder's ./bench.sh streaming decode net of TTFT, greedy median; frozen battery ./bench-matrix.sh"

write(setup(
    "qwen38-27b-hasso-nvfp4-dflash2-sglang-spark",
    "Qwen3.8-27B NVFP4 — hasso5703 one-command SGLang + DFlash2 block-8",
    "An independent builder's boot-persistent DFlash2 lane at half memory fraction: "
    "50 tok/s chat, 135-258 aggregate, with quality canaries attached.",
    "qwen3-8-27b",
    {"checkpoint": "RadixArk/Qwen3.8-27B-NVFP4", "publisher": "radixark",
     "quant": "nvfp4", "quant_detail": "W4A4 body; builder pairs it with the z-lab DFlash2 draft",
     "format": "safetensors", "size_gb": 22,
     "url": "https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4"},
    {"id": "sglang", "spec_decode": "dflash2",
     "config": "DFlash2 draft block 8, --mem-fraction-static 0.50, boot-persistent one-command install",
     "flags": ["--mem-fraction-static 0.50"]},
    ["dgx-spark"],
    {"memory_gb": 30, "disk_gb": 84, "min_vram_gb": None,
     "notes": "Builder states ~39 GB under $HOME plus ~45 GB Docker image for the 27B target."},
    {"repo": HASSO, "command": None,
     "steps": ["Follow the repo's one-command boot-persistent SGLang install",
               "Select the 27B NVFP4 + DFlash2 target",
               "./bench.sh to reproduce the decode numbers"]},
    [fm("decode_chat", 50, "tok/s", HASSO_RAW, "2026-08-30", M_BENCH,
        "Thinking on, single stream; code 41-47, reasoning 52-57, math peak 60."),
     fm("decode_code", 40, "tok/s", HASSO_RAW, "2026-08-30", M_BENCH,
        "Agentic coding battery (code, diffs, tool calls); range 32-40.", rng=[32, 40]),
     fm("decode_essay", 22, "tok/s", HASSO_RAW, "2026-08-30", M_BENCH,
        "Free-form prose EN; FR 20, DE 17 in the same battery.", rng=[17, 23]),
     fm("decode_agg", 135, "tok/s", HASSO_RAW, "2026-08-30", M_BENCH,
        "8 concurrent streams aggregate; stated range 135-148.", rng=[135, 148]),
     fm("decode_agg", 258, "tok/s", HASSO_RAW, "2026-08-30", M_BENCH,
        "32 concurrent streams aggregate."),
     fm("bench_gsm8k", 94.0, "%", HASSO_RAW, "2026-08-30",
        "GSM8K, 200 problems (188/200), same box, thinking on",
        "Quality canary, not a speed number."),
     fm("bench_toolcall", 91, "score", HASSO_RAW, "2026-08-30",
        "tool-eval-bench, 69 scenarios, 91/100 'Excellent'; IFEval 200 prompts",
        "Quality canary, not a speed number.")],
    ["Single-builder numbers on a configuration we have not run: mem-fraction 0.50 "
     "versus our 0.90/16 profile, so his aggregates are not directly comparable to "
     "our box rows.",
     "The quality canaries (GSM8K 94%, tool-eval 91) are his harness, not a "
     "shared benchmark; compare them only against his other targets."],
    [{"url": HASSO, "kind": "repo", "note": "the recipe and scripts"},
     {"url": HASSO_RAW, "kind": "docs", "note": "README carrying the quoted numbers"}]))

write(setup(
    "qwen38-flash-next-hasso-nvfp4-mtp-sglang-spark",
    "Qwen3.8-Flash-Next NVFP4 — hasso5703 SGLang lane with prefix caching",
    "The Flash-Next lane that actually makes prefix caching work on Spark: a 30K "
    "conversation re-served in 0.5 s warm versus 18.4 s cold.",
    "qwen3-8-flash-next",
    {"checkpoint": "RadixArk/Qwen3.8-Flash-Next-NVFP4", "publisher": "radixark",
     "quant": "nvfp4",
     "quant_detail": "NVFP4 main weights, bf16 KV cache, 51B N-gram (PLE) table mmap-served from NVMe",
     "format": "safetensors", "size_gb": 136,
     "url": "https://huggingface.co/RadixArk/Qwen3.8-Flash-Next-NVFP4"},
    {"id": "sglang", "spec_decode": "mtp",
     "config": "NEXTN/MTP speculative head, bf16 KV, PLE table mmap from NVMe, prefix caching on"},
    ["dgx-spark"],
    {"memory_gb": 110, "disk_gb": 230, "min_vram_gb": None,
     "notes": "~195 GB under $HOME (~136 GB checkpoint plus PLE table) plus Docker; host MemAvailable 16.6 GiB during a 120K prompt."},
    {"repo": HASSO, "command": None,
     "steps": ["Follow the repo's one-command install",
               "Select the flash-next NVFP4 + MTP target",
               "Keep the PLE table on NVMe; it is mmap-served, not loaded"]},
    [fm("decode_chat", 34.2, "tok/s", HASSO_RAW, "2026-09-03",
        "two-call wall-clock decode, reasoning, single Spark", "README headline number."),
     fm("decode_essay", 20.3, "tok/s", HASSO_RAW, "2026-09-03",
        "two-call wall-clock decode, free prose, single Spark"),
     fm("decode_chat", 28, "tok/s", HASSO_RAW, "2026-09-03",
        "field report at ~100K context depth (user hashd1ve)",
        "Stated as 'near 28-31' at depth; a depth point, not a fresh-context number."),
     fm("task_time_min", 18.4, "s", HASSO_RAW, "2026-09-03",
        "30K-token conversation re-served cold versus 0.5 s warm with prefix caching",
        "The differentiator of this lane: prefix caching works here."),
     fm("bench_other", 1500, "tok/s", HASSO_RAW, "2026-09-03",
        "cold prefill with real QSA sparse kernels, stated ~1500-2000 tok/s"),
     fm("quality_index", 9, "score", HASSO_RAW, "2026-09-03",
        "exact needle retrieval 9/9 at 120K prompt tokens; quality canaries 4/4",
        "Retrieval canary at depth, not an intelligence index.")],
    ["Overlaps the Mia, azampatti and blazux lanes on the same weights; the prefix-"
     "caching and 120K-retrieval numbers are what this lane adds.",
     "Disk footprint is the real price: ~230 GB free, most of it the mmap-served PLE table."],
    [{"url": HASSO, "kind": "repo", "note": "the recipe and scripts"},
     {"url": HASSO_RAW, "kind": "docs", "note": "README carrying the quoted numbers"}]))

write(setup(
    "qwen35-122b-a10b-redhatai-nvfp4-vllm-spark",
    "Qwen3.5-122B-A10B RedHatAI NVFP4 on vLLM — the SM121 kernel trap",
    "A documented negative result: NVFP4 of the 122B decodes at 16.6 tok/s on "
    "Spark, slower than INT4, because FP4 CUTLASS kernels do not run on SM121 yet.",
    "qwen3-5-122b-a10b",
    {"checkpoint": "RedHatAI/Qwen3.5-122B-A10B-NVFP4", "publisher": "redhatai",
     "quant": "nvfp4", "quant_detail": "NVFP4 export of the 122B MoE",
     "format": "safetensors", "size_gb": None,
     "url": "https://huggingface.co/RedHatAI/Qwen3.5-122B-A10B-NVFP4"},
    {"id": "vllm", "config": "stock vLLM on a single DGX Spark"},
    ["dgx-spark"],
    {"memory_gb": 70, "disk_gb": 68, "min_vram_gb": None,
     "notes": "Fits a single Spark; the problem is kernel support, not capacity."},
    {"repo": NVIDIA_122B, "command": None,
     "steps": ["Serve the RedHatAI NVFP4 checkpoint with stock vLLM on one Spark",
               "Expect FP4 kernels to fall back; measure before trusting the quant label"]},
    [fm("decode_chat", 16.6, "tok/s", NVIDIA_122B, "2026-04-05",
        "single DGX Spark, vLLM, single stream",
        "'slower than INT4 because FP4 CUTLASS kernels don't work on SM121 yet'.")],
    ["Keep this entry precisely because it is slow: it is the counter-example to "
     "'NVFP4 is always faster' on Blackwell-mini silicon.",
     "Kernel support moves; re-check vLLM/FlashInfer SM121 FP4 status before deleting this row."],
    [{"url": NVIDIA_122B, "kind": "thread", "note": "NVIDIA developer forum thread with the measurement"},
     {"url": "https://huggingface.co/RedHatAI/Qwen3.5-122B-A10B-NVFP4", "kind": "model",
      "note": "weights"}]))

write(setup(
    "qwen35-35b-a3b-intel-int4-vllm-spark-concurrency",
    "Qwen3.5-35B-A3B Intel INT4 AutoRound on vLLM — concurrency sweep on Spark",
    "The controlled concurrency sweep for the 35B MoE on one Spark: 60.9 aggregate "
    "at 5x, 66.3 at 10x, with a 990-call GPQA quality check attached.",
    "qwen3-5-35b-a3b",
    {"checkpoint": "Intel/Qwen3.5-35B-A3B-int4-AutoRound", "publisher": "intel",
     "quant": "int4-hybrid", "quant_detail": "AutoRound INT4 with FP8 KV cache",
     "format": "safetensors", "size_gb": None,
     "url": "https://huggingface.co/Intel/Qwen3.5-35B-A3B-int4-AutoRound"},
    {"id": "vllm",
     "config": "prefix caching on, --gpu-memory-utilization 0.8, --max-num-seqs 10, FP8 KV",
     "flags": ["--gpu-memory-utilization 0.8", "--max-num-seqs 10"]},
    ["dgx-spark"],
    {"memory_gb": 26, "disk_gb": 24, "min_vram_gb": None,
     "notes": "INT4 MoE plus FP8 KV leaves headroom for 10 concurrent sequences."},
    {"repo": NVIDIA_35B, "command": None,
     "steps": ["Serve the Intel INT4 checkpoint with vLLM on one Spark",
               "Enable prefix caching and FP8 KV as in the thread",
               "Run vllm bench serve at 5x and 10x concurrency"]},
    [fm("decode_agg", 60.87, "tok/s", NVIDIA_35B, "2026-03-02",
        "vllm bench serve, 5x concurrency, 100 prompts, 42K input tokens total"),
     fm("ttft_ms", 15715.12, "ms", NVIDIA_35B, "2026-03-02",
        "mean TTFT at 5x concurrency with prefix caching (median 12491 ms)"),
     fm("decode_agg", 66.27, "tok/s", NVIDIA_35B, "2026-03-02",
        "same prompt set at 10x concurrency"),
     fm("bench_other", 82.32, "%", NVIDIA_35B, "2026-03-02",
        "GPQA Diamond, 198 questions x 5 repeats = 990 eval calls, 9.1M tokens",
        "Quality check on the served quant, not a speed number.")],
    ["TTFT at these concurrencies is dominated by the 42K-token prompt set; do not "
     "read 15.7 s as single-request latency."],
    [{"url": NVIDIA_35B, "kind": "thread", "note": "thread with the full bench tables"},
     {"url": "https://huggingface.co/Intel/Qwen3.5-35B-A3B-int4-AutoRound", "kind": "model",
      "note": "weights"}]))

write(setup(
    "qwen35-35b-a3b-bf16-mxfp4-marlin-vllm-spark",
    "Qwen3.5-35B-A3B BF16 weights with runtime MXFP4 Marlin experts on Spark",
    "BF16 checkpoint, MXFP4 quantised at load for the MoE experts: 69.5 tok/s per "
    "stream and 339.5 aggregate at 100 concurrent on one Spark.",
    "qwen3-5-35b-a3b",
    {"checkpoint": "Qwen/Qwen3.5-35B-A3B", "publisher": "qwen",
     "quant": "mixed", "quant_detail": "BF16 weights on disk, vLLM runtime MXFP4 (Marlin) for MoE experts, FP8 KV",
     "format": "safetensors", "size_gb": None,
     "url": "https://huggingface.co/Qwen/Qwen3.5-35B-A3B"},
    {"id": "vllm", "requires_fork": True,
     "config": "custom vLLM build (nightly-based) applying runtime MXFP4 Marlin to experts + FP8 KV"},
    ["dgx-spark"],
    {"memory_gb": 40, "disk_gb": 70, "min_vram_gb": None,
     "notes": "BF16 on disk (~70 GB) but experts compressed in memory; needs the builder's vLLM build."},
    {"repo": NVIDIA_35B, "command": None,
     "steps": ["Build or obtain the thread author's vLLM nightly-based fork",
               "Serve Qwen/Qwen3.5-35B-A3B with runtime MXFP4 experts and FP8 KV",
               "Bench at 1, 10 and 100 concurrency"]},
    [fm("decode_per_stream", 69.45, "tok/s", NVIDIA_35B, "2026-03-06",
        "1 concurrent request, 1024 input / 128 output tokens, DGX Spark"),
     fm("ttft_ms", 167.71, "ms", NVIDIA_35B, "2026-03-06", "mean TTFT at 1 concurrent request"),
     fm("decode_agg", 253.53, "tok/s", NVIDIA_35B, "2026-03-06",
        "10 concurrent requests (mean TTFT 935.12 ms)"),
     fm("decode_agg", 339.5, "tok/s", NVIDIA_35B, "2026-03-06",
        "100 concurrent requests (mean TTFT 17137.53 ms)")],
    ["Requires the thread author's custom vLLM build; stock vLLM will not reproduce "
     "the runtime-MXFP4 path, so reproducibility is weaker than the stock-engine rows."],
    [{"url": NVIDIA_35B, "kind": "thread", "note": "thread with the serving benchmark tables"},
     {"url": "https://huggingface.co/Qwen/Qwen3.5-35B-A3B", "kind": "model", "note": "weights"}]))

write(setup(
    "qwen35-35b-a3b-vllm-nightly-mtp2-spark-c100",
    "Qwen3.5-35B-A3B on vLLM nightly with MTP=2 at concurrency 100 on Spark",
    "The throughput ceiling reported for the 35B MoE on one Spark: 431 aggregate "
    "tok/s at concurrency 100 with the in-checkpoint MTP head.",
    "qwen3-5-35b-a3b",
    {"checkpoint": "Qwen/Qwen3.5-35B-A3B", "publisher": "qwen",
     "quant": "bf16", "quant_detail": "BF16 weights, --gpu-memory-utilization 0.8, qwen3_next_mtp num_speculative_tokens=2",
     "format": "safetensors", "size_gb": None,
     "url": "https://huggingface.co/Qwen/Qwen3.5-35B-A3B"},
    {"id": "vllm", "spec_decode": "mtp",
     "config": "vLLM nightly, MTP num_speculative_tokens=2, gpu-memory-utilization 0.8"},
    ["dgx-spark"],
    {"memory_gb": 75, "disk_gb": 70, "min_vram_gb": None,
     "notes": "BF16 MoE plus KV for 100 concurrent sequences at 128K unit context."},
    {"repo": NVIDIA_35B, "command": None,
     "steps": ["Serve with vLLM nightly and the MTP speculative config from the thread",
               "vllm bench serve, 1000 requests, max concurrency 100"]},
    [fm("decode_agg", 431.42, "tok/s", NVIDIA_35B, "2026-03-02",
        "vllm bench serve, 1000 requests, max concurrency 100, 128K-context unit"),
     fm("ttft_ms", 2242.31, "ms", NVIDIA_35B, "2026-03-02",
        "mean TTFT at concurrency 100; median 1550.75 ms, P99 above 10 s")],
    ["Aggregate throughput at concurrency 100 says nothing about single-stream "
     "latency; pair this row with the per-stream rows before choosing a config.",
     "The same bench on 2x RTX PRO 6000 Blackwell reached 3341.89 tok/s — a "
     "datacenter comparison the thread includes, not a local target."],
    [{"url": NVIDIA_35B, "kind": "thread", "note": "thread with the bench output"},
     {"url": "https://huggingface.co/Qwen/Qwen3.5-35B-A3B", "kind": "model", "note": "weights"}]))

write(setup(
    "qwen36-27b-fp8-vllm-mtp3-spark",
    "Qwen3.6-27B FP8 on vLLM: 7.8 tok/s bare, ~2x with MTP=3 on Spark",
    "The dense-27B reality check on Spark: 7.8 tok/s without speculative decoding, "
    "14.5-15.8 with MTP=3 — and the reason the directory pushes MoE on this box.",
    "qwen3-6-27b",
    {"checkpoint": "Qwen/Qwen3.6-27B-FP8", "publisher": "qwen",
     "quant": "fp8", "quant_detail": "FP8 weights, unquantized KV cache",
     "format": "safetensors", "size_gb": None,
     "url": "https://huggingface.co/Qwen/Qwen3.6-27B-FP8"},
    {"id": "vllm", "spec_decode": "mtp",
     "config": "--speculative-config method=mtp num_speculative_tokens=3 for the doubled rows"},
    ["dgx-spark"],
    {"memory_gb": 32, "disk_gb": 30, "min_vram_gb": None,
     "notes": "Fits easily; bandwidth, not capacity, is the wall for dense 27B."},
    {"repo": NVIDIA_36, "command": None,
     "steps": ["Serve Qwen3.6-27B-FP8 with stock vLLM on one Spark",
               "Bench the two prompts below with and without the MTP speculative config"]},
    [fm("decode_code", 7.8, "tok/s", NVIDIA_36, "2026-04-23",
        "'write me a commented quicksort function in Python', baseline without MTP"),
     fm("decode_essay", 7.8, "tok/s", NVIDIA_36, "2026-04-23",
        "'2-page essay on phone addiction', baseline without MTP"),
     fm("decode_code", 14.5, "tok/s", NVIDIA_36, "2026-04-23",
        "same quicksort prompt with MTP num_speculative_tokens=3"),
     fm("decode_essay", 15.8, "tok/s", NVIDIA_36, "2026-04-23",
        "same essay prompt with MTP=3; 15.2 tok/s average across prompts")],
    ["A deliberate negative result: keep it visible so 'just run the dense 27B' "
     "comes with its number attached.",
     "The thread's qualitative AgentBench note — dense BF16 Qwen3.6 beating MoE "
     "quants on agent tasks — is a quality signal, not recorded as a metric here."],
    [{"url": NVIDIA_36, "kind": "thread", "note": "thread with the MTP comparison table"},
     {"url": "https://huggingface.co/Qwen/Qwen3.6-27B-FP8", "kind": "model", "note": "weights"}]))

write(setup(
    "qwen35-122b-a10b-unsloth-gguf-q4-llamacpp-multigpu",
    "Qwen3.5-122B-A10B UD-Q4_K_XL on llama.cpp across 72 GB of mixed GPUs",
    "The 122B MoE at Q4 on a 4090D+3090 rig: 66.2 tok/s at 131K context with two "
    "parallel slots, and 1.3K tok/s prefill.",
    "qwen3-5-122b-a10b",
    {"checkpoint": "unsloth/Qwen3.5-122B-A10B-GGUF", "publisher": "unsloth",
     "quant": "gguf-q4", "quant_detail": "UD-Q4_K_XL, 63.65 GiB, 4.48 BPW",
     "format": "gguf", "size_gb": None,
     "url": "https://huggingface.co/unsloth/Qwen3.5-122B-A10B-GGUF"},
    {"id": "llama-cpp", "config": "llama.cpp server cuda12 b8124, --ctx-size 131072, --parallel 2, tensor-split across both cards"},
    ["gpu-multigpu-72gb"],
    {"memory_gb": 68, "disk_gb": 68, "min_vram_gb": 68,
     "notes": "63.65 GiB of weights split across 48+24 GB; host RAM 256 GB DDR5-4800."},
    {"repo": HF122B, "command": None,
     "steps": ["Download the UD-Q4_K_XL GGUF",
               "llama.cpp server with CUDA, ctx 131072, parallel 2, tensor-split over both GPUs"]},
    [fm("decode_chat", 66.2, "tok/s", HF122B, "2026-02-25",
        "llama.cpp server cuda12 b8124, ctx 131072, parallel 2 slots"),
     fm("ttft_ms", 1322.38, "ms", HF122B, "2026-02-25",
        "prompt eval of 1734 tokens = 1311.27 tok/s prefill")],
    ["Mixed-card rig: the 3090's slower kernels and the PCIe lanes cap this; do not "
     "compare it to single-GPU or unified-memory rows."],
    [{"url": HF122B, "kind": "thread", "note": "HF discussion with the server log"},
     {"url": "https://huggingface.co/unsloth/Qwen3.5-122B-A10B-GGUF", "kind": "model",
      "note": "GGUF repo"}]))

write(setup(
    "qwen35-122b-a10b-unsloth-gguf-q3-llamacpp-multigpu-256k",
    "Qwen3.5-122B-A10B UD-Q3_K_XL on llama.cpp at 256K context, 72 GB VRAM",
    "The long-context 122B report: 50 tok/s generation on a 256K-token prompt, with "
    "prefill collapsing from 1800 tok/s at 4K to 800 tok/s at 256K.",
    "qwen3-5-122b-a10b",
    {"checkpoint": "unsloth/Qwen3.5-122B-A10B-GGUF", "publisher": "unsloth",
     "quant": "gguf-q3", "quant_detail": "UD-Q3_K_XL (author also runs IQ4_XS at ~240K context)",
     "format": "gguf", "size_gb": None,
     "url": "https://huggingface.co/unsloth/Qwen3.5-122B-A10B-GGUF"},
    {"id": "llama-cpp", "config": "llama.cpp b8157, 256K-token prompt, tensor-split across 4090 + 2x 3090"},
    ["gpu-multigpu-72gb"],
    {"memory_gb": 60, "disk_gb": 60, "min_vram_gb": 60,
     "notes": "Q3 fits with KV room for 256K; author notes the rig is PCIe-lane limited."},
    {"repo": HF122B, "command": None,
     "steps": ["Download the UD-Q3_K_XL GGUF",
               "llama.cpp b8157 or newer with tensor-split over three cards",
               "Load a 256K-token prompt and measure generation and prefill"]},
    [fm("decode_chat", 50, "tok/s", HF122B, "2026-02-26",
        "llama.cpp b8157 with a 256K-token prompt loaded"),
     fm("bench_other", 800, "tok/s", HF122B, "2026-02-26",
        "prefill on a single 256K-token prompt (worst case)"),
     fm("bench_other", 1800, "tok/s", HF122B, "2026-02-26",
        "prefill on a 4K-token prompt")],
    ["Prefill at 256K is the number to watch: it is 2.25x worse than at 4K on the "
     "same rig, which is the PCIe-lane tax made visible."],
    [{"url": HF122B, "kind": "thread", "note": "HF discussion with the numbers"},
     {"url": "https://huggingface.co/unsloth/Qwen3.5-122B-A10B-GGUF", "kind": "model",
      "note": "GGUF repo"}]))

write(setup(
    "qwen35-35b-a3b-mxfp4-llamacpp-spark-implied",
    "Qwen3.5-35B-A3B MXFP4 on plain llama.cpp, ~57 tok/s at 256K (hardware implied)",
    "The 'no rituals required' datapoint: plain llama.cpp at ~57 TPS on 256K "
    "context, posted in the Spark forum but without the box named.",
    "qwen3-5-35b-a3b",
    {"checkpoint": "unsloth/Qwen3.5-35B-A3B-GGUF", "publisher": "unsloth",
     "quant": "mxfp4", "quant_detail": "MXFP4 GGUF (post mentions Q4 as the alternative)",
     "format": "gguf", "size_gb": None, "file_match": "mxfp4",
     "url": "https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF"},
    {"id": "llama-cpp", "config": "plain mainline llama.cpp, 256K context, no speculative decoding"},
    ["dgx-spark"],
    {"memory_gb": 22, "disk_gb": 22, "min_vram_gb": None,
     "notes": "MoE at 4-bit fits with room; hardware is implied by the thread, not stated."},
    {"repo": NVIDIA_35B, "command": None,
     "steps": ["Load the MXFP4 GGUF in mainline llama.cpp",
               "Run at 256K context and measure tokens per second"]},
    [fm("decode_chat", 57, "tok/s", NVIDIA_35B, "2026-03-04",
        "'~57 TPS (256k)'; concurrency and fixture not stated in the post")],
    ["Hardware is NOT stated in the post: it sits in the NVIDIA DGX Spark / GB10 "
     "forum, so GB10 is implied but unconfirmed. Treat 57 tok/s as directional.",
     "Concurrency and fixture unstated; this is a single anecdotal number, kept "
     "because it is the plainest possible stack."],
    [{"url": NVIDIA_35B, "kind": "thread", "note": "the post (hardware implied, not stated)"},
     {"url": "https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF", "kind": "model",
      "note": "GGUF repo"}]))

# ------------------------------------------------- untested HF quant lanes ---
UNTESTED = [
    ("qwen38-27b-mlx-community-4bit-mac",
     "Qwen3.8-27B MLX 4-bit on Apple Silicon",
     "The Mac lane for the 27B: mlx-community's 4-bit MLX export for mlx-lm.",
     "qwen3-8-27b", "mlx-community/Qwen3.8-27B-4bit", "mlx-community", "mlx-4",
     "4-bit MLX export", "mlx", "https://huggingface.co/mlx-community/Qwen3.8-27B-4bit",
     "mlx-lm", "mlx-lm serve on an M-series Mac with 64 GB+ unified memory",
     ["mac-128gb"], 18, 17,
     ["No numbers yet: validates as a lane, not as a measured setup.",
      "Needs a 64 GB+ Mac for comfort; a 32 GB Mac will swap."],
     262144),
    ("qwen38-27b-unsloth-gguf-llamacpp",
     "Qwen3.8-27B unsloth GGUF on llama.cpp (24 GB card or Mac)",
     "Dynamic UD quants from IQ1_S to BF16 put the 27B on a 24 GB card or a Mac.",
     "qwen3-8-27b", "unsloth/Qwen3.8-27B-GGUF", "unsloth", "gguf-q4",
     "Dynamic UD quants; size shown is the Q4-class representative", "gguf",
     "https://huggingface.co/unsloth/Qwen3.8-27B-GGUF",
     "llama-cpp", "llama.cpp with CUDA or Metal, Q4_K_M or smaller to stay on-card",
     ["gpu-24gb", "mac-128gb"], 18, 18,
     ["No numbers yet; pick the quant by your VRAM, not by the benchmark tables.",
      "At IQ1_S the 27B fits almost anywhere but quality cost is real."],
     262144),
    ("qwen35-35b-a3b-bartowski-gguf-llamacpp",
     "Qwen3.5-35B-A3B bartowski GGUF on llama.cpp",
     "bartowski's per-quant cards for the 35B MoE, the classic llama.cpp lane.",
     "qwen3-5-35b-a3b", "bartowski/Qwen_Qwen3.5-35B-A3B-GGUF", "bartowski",
     "gguf-q4", "Per-quant GGUF splits with llama.cpp test notes", "gguf",
     "https://huggingface.co/bartowski/Qwen_Qwen3.5-35B-A3B-GGUF",
     "llama-cpp", "llama.cpp CUDA or Metal; Q4_K_M fits 24 GB with KV room",
     ["gpu-24gb", "mac-128gb"], 21, 21,
     ["No numbers yet; bartowski cards list per-quant quality samples, use them."],
     262144),
    ("qwen36-35b-a3b-quanttrio-awq-vllm",
     "Qwen3.6-35B-A3B QuantTrio AWQ on vLLM (24 GB card)",
     "The AWQ lane for the 3.6 MoE: small enough for a single 24 GB card in vLLM.",
     "qwen3-6-35b-a3b", "QuantTrio/Qwen3.6-35B-A3B-AWQ", "quanttrio", "awq",
     "AWQ quant aimed at vLLM serving", "awq",
     "https://huggingface.co/QuantTrio/Qwen3.6-35B-A3B-AWQ",
     "vllm", "vLLM with the AWQ checkpoint on a 24 GB card",
     ["gpu-24gb"], 19, 19,
     ["No numbers yet; AWQ on SM89 is well supported, SM121 less proven."],
     262144),
    ("qwen36-27b-nvidia-nvfp4-sglang",
     "Qwen3.6-27B nvidia NVFP4 on SGLang (Spark)",
     "NVIDIA's own NVFP4 export of the dense 3.6 27B, the SM121-native quant.",
     "qwen3-6-27b", "nvidia/Qwen3.6-27B-NVFP4", "nvidia", "nvfp4",
     "NVIDIA NVFP4 export", "safetensors",
     "https://huggingface.co/nvidia/Qwen3.6-27B-NVFP4",
     "sglang", "SGLang with the NVFP4 checkpoint on a DGX Spark",
     ["dgx-spark"], 17, 16,
     ["No numbers yet; note the 122B NVFP4 row elsewhere in this directory: FP4 "
      "kernels on SM121 have been the slow path before, measure before trusting."],
     262144),
    ("qwen35-122b-a10b-qwen-gptq-int4-vllm",
     "Qwen3.5-122B-A10B official GPTQ-Int4 on vLLM (Spark)",
     "Qwen's own GPTQ-Int4 export of the 122B MoE: fits one Spark, no third-party quant.",
     "qwen3-5-122b-a10b", "Qwen/Qwen3.5-122B-A10B-GPTQ-Int4", "qwen", "gptq",
     "Official GPTQ Int4 export", "gptq",
     "https://huggingface.co/Qwen/Qwen3.5-122B-A10B-GPTQ-Int4",
     "vllm", "vLLM with the GPTQ checkpoint on a DGX Spark",
     ["dgx-spark"], 66, 64,
     ["No numbers yet; compare against the Intel AutoRound and Albond lanes before choosing."],
     262144),
    ("qwen36-27b-unsloth-mtp-gguf-llamacpp",
     "Qwen3.6-27B unsloth GGUF with the MTP head intact (llama.cpp)",
     "A GGUF that keeps the MTP draft head, so llama.cpp can spec-decode the dense 27B.",
     "qwen3-6-27b", "unsloth/Qwen3.6-27B-MTP-GGUF", "unsloth", "gguf-q4",
     "GGUF retaining the MTP head for llama.cpp speculative decoding", "gguf",
     "https://huggingface.co/unsloth/Qwen3.6-27B-MTP-GGUF",
     "llama-cpp", "llama.cpp with --speculative-type or draft from the MTP head, per repo notes",
     ["mac-128gb", "gpu-24gb"], 18, 18,
     ["No numbers yet; the forum's vLLM MTP=3 rows for this model show ~2x, llama.cpp's gain is unmeasured here."],
     262144),
]

for (sid, title, slug, model, ckpt, pub, quant, qd, fmt, url, eng, cfg,
     hw, mem, disk, caveats, ctx) in UNTESTED:
    var = {"checkpoint": ckpt, "publisher": pub, "quant": quant,
           "quant_detail": qd, "format": fmt, "size_gb": None, "url": url}
    if fmt == "gguf" and quant == "mxfp4":
        var["file_match"] = "mxfp4"
    write(setup(
        sid, title, slug, model,
        var,
        {"id": eng, "config": cfg},
        hw,
        {"memory_gb": mem, "disk_gb": disk, "min_vram_gb": None,
         "notes": "Resident estimate from the quant size plus KV headroom."},
        {"repo": url, "command": None,
         "steps": [f"Download {ckpt}", cfg]},
        [], caveats,
        [{"url": url, "kind": "model", "note": "weights / quant card"}],
        caps={"vision": False, "video": False, "tools": True, "thinking": True,
              "long_context": ctx, "max_context": ctx}))

print("\nskipped:")
for s in skipped:
    print("  ", s)
