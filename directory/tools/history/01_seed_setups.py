#!/usr/bin/env python3
"""One-time seed: write setups verifiable from this repo's own sources
(README.md canonical tables, profiles/*.env, PLANS.md, dashboard)."""
import json, os

OUT = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data/setups"
REPO = "https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark"
COOKBOOK = "https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B"
CARD27 = "https://huggingface.co/Qwen/Qwen3.8-27B"
HF_PACKED = "https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4"
HF_BF16HEAD = "https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead"
HF_DSPARK = "https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark"
HF_DFLASH = "https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2"
DFLASH_BLOG = "https://inco.ai/blog/dflash2/"
DFLASH_COMMIT = "https://github.com/sgl-project/sglang/commit/c14312a66"
HASSO = "https://github.com/hasso5703/dgx-spark-qwen38"
SGLANG = "https://github.com/sgl-project/sglang"

NDEC = ("bench/ndec.py two-call net-decode, median of 5, tokens counted from the "
        "server's completion_tokens via stream_options.include_usage")

SPARK = ["dgx-spark"]

setups = []


def add(**kw):
    kw.setdefault("updated", "2026-09-05")
    setups.append(kw)


# --------------------------------------------------------------------------
# Qwen3.8-27B on the packed-FP4-head NVFP4 export.
# README: "DSpark/MTP measured 2026-08-18, DFlash2 2026-08-19, all on the
# packed-FP4-head export; the default is now the BF16-head twin."
# --------------------------------------------------------------------------
PACKED_VAR = {
    "checkpoint": "RadixArk/Qwen3.8-27B-NVFP4",
    "publisher": "radixark",
    "quant": "nvfp4",
    "quant_detail": "W4A4 body with lm_head packed to FP4. ~1.7GB smaller on disk than the BF16-head twin.",
    "format": "safetensors",
    "size_gb": 22,
    "url": HF_PACKED,
    "license": "Apache-2.0",
    "downloads": None,
}

add(
    id="qwen38-27b-nvfp4-packed-sglang-dflash2",
    title="Qwen3.8-27B NVFP4 (packed FP4 head) — SGLang + DFlash2",
    slug_note="Fastest all-round configuration measured on our box: ties DSpark on code inside the noise band, beats MTP on the long essay, and wins every short-chat condition once tokens are counted correctly.",
    model="qwen3-8-27b",
    status="measured",
    variation=dict(PACKED_VAR),
    engine={
        "id": "sglang",
        "config": "DFlash2 block-diffusion draft. speculative_num_steps forced to 1; EAGLE knobs (topk, num_steps) do not apply to a diffusion drafter. --enable-dp-attention and the overlap scheduler off. Radix cache strategy forced to extra_buffer because DFLASH rejects extra_buffer_lazy.",
        "image": "lmsysorg/sglang:qwen38-27b-dflash2",
        "requires_fork": True,
        "draft_model": "z-lab/Qwen3.8-27B-DFlash2@50307d4 (mirror of incoai/...)",
        "spec_decode": "dflash2",
        "flags": ["--mem-fraction-static 0.90", "--kv-cache-dtype fp8_e4m3",
                  "--max-running-requests 16", "--chunked-prefill-size 8192",
                  "--reasoning-parser qwen3", "--tool-call-parser qwen3_coder"],
    },
    hardware=SPARK,
    requirements={"memory_gb": 30, "disk_gb": 25, "min_vram_gb": None,
                  "notes": "~22GB packed-head target + ~2.6GB block-diffusion draft + KV pool at mem-fraction 0.90."},
    capabilities={"vision": True, "video": True, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": 262144},
    run={"command": "./start-dflash.sh",
         "repo": REPO,
         "profile": "profiles/qwen3.8-27b.env",
         "steps": ["cp .env.sample .env", "./start-dflash.sh",
                   "curl http://127.0.0.1:8888/v1/models", "./stop.sh"],
         "auto_bootable": True},
    measurements=[
        {"metric": "decode_code", "value": 50.9, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-19", "n": 5, "method": NDEC, "range": [50.8, 51.1],
         "note": "LRUCache + small test probe. Ties DSpark's 51.5 inside the <15% noise band."},
        {"metric": "decode_essay", "value": 25.4, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-19", "n": 5, "method": NDEC, "range": [25.3, 25.4],
         "note": "Babbage-to-GPUs long essay. Beats both DSpark (18.3) and MTP (24.1)."},
        {"metric": "decode_chat", "value": 66.6, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-19", "n": 5, "method": NDEC + "; streamed, temperature 1.0, thinking on",
         "range": [45.6, 80.2],
         "note": "Short chat with thinking on. This image batches ~3.75 tokens per SSE event at a fixed ~8 events/s, so a client that counts events as tokens reads ~9 tok/s. Always count completion_tokens."},
        {"metric": "ttft_ms", "value": 8200, "unit": "ms", "provenance": "box",
         "date": "2026-08-19", "n": 1,
         "method": "bench/bench.sh wall-time probe on a fresh ~16K prompt, warm",
         "note": "Cold boot is ~13s (Triton kernel warmup); the .cache/triton volume persists it."},
    ],
    caveats=[
        "Not compatible with YaRN or context >262144. The rope override leaks into the draft config and crashes with AttributeError: 'PreTrainedConfig' object has no attribute 'max_position_embeddings'. Keep YARN=0 and CONTEXT_LENGTH=262144.",
        "No released SGLang image has DFlash2 — it merged upstream 2026-08-19, after every published tag. start-dflash.sh builds the image from patch/ on first run, which needs git and network once.",
        "Crash history, now fixed: the original head handling dequantized the whole NVFP4 lm_head (~2.5-5GB) during draft-graph capture and hard-rebooted the box at mem-fraction 0.95, and at 0.80 with concurrency >= 8-10. The image now runs the quantized head in place via lm_head.quant_method.apply. If you still see that reboot signature it is not the memory fraction.",
        "Measured 2026-08-19 on a single boot, one day after the DSpark/MTP figures. Cross-engine deltas are indicative, not a race. The recommendation in the repo is one replication boot before switching a production default.",
        "A minimal 5-file overlay build measured 61.1 code / 28.4 essay versus 50.9 / 25.4 for the whole-tree build at the same base digest — but that A/B is confounded (fresh boot, concurrency 10 vs 4), so it is recorded and not believed.",
    ],
    provenance_tier="box",
    sources=[
        {"url": REPO, "kind": "repo", "note": "recipe + start-dflash.sh"},
        {"url": HF_PACKED, "kind": "model", "note": "weights"},
        {"url": HF_DFLASH, "kind": "model", "note": "block-diffusion draft"},
        {"url": DFLASH_BLOG, "kind": "blog", "note": "DFlash2 write-up, serving recipe"},
        {"url": DFLASH_COMMIT, "kind": "repo", "note": "upstream DFlash2 support"},
    ],
)

add(
    id="qwen38-27b-nvfp4-packed-sglang-dspark",
    title="Qwen3.8-27B NVFP4 (packed FP4 head) — SGLang + DSpark block-7",
    slug_note="The code peak: 51.5 tok/s on the LRUCache probe, about 1.5x MTP. Gives the long essay back — 18.3 versus MTP's 24.1.",
    model="qwen3-8-27b",
    status="measured",
    variation=dict(PACKED_VAR),
    engine={
        "id": "sglang",
        "config": "DSpark block-7 with 8 draft tokens, unquantized draft. torch.compile plus decode-graph caps, --num-continuous-decode-steps 2, prefill CUDA graphs off, flashinfer.",
        "image": "lmsysorg/sglang:qwen38-27b",
        "requires_fork": False,
        "draft_model": "RadixArk/Qwen3.8-27B-DSpark (~2.7GB, fetched once)",
        "spec_decode": "dspark",
        "flags": ["--speculative-dspark-block-size 7", "--speculative-num-draft-tokens 8",
                  "--cuda-graph-max-bs-decode 4", "--mem-fraction-static 0.90",
                  "--kv-cache-dtype fp8_e4m3", "--cpuset-cpus 5-9,15-19"],
    },
    hardware=SPARK,
    requirements={"memory_gb": 30, "disk_gb": 25, "min_vram_gb": None,
                  "notes": "~22GB target + ~2.7GB DSpark draft + KV pool at mem-fraction 0.90."},
    capabilities={"vision": True, "video": True, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": 262144},
    run={"command": "./start-dspark.sh",
         "repo": REPO,
         "profile": "profiles/qwen3.8-27b.env",
         "steps": ["cp .env.sample .env", "./start-dspark.sh"],
         "auto_bootable": True},
    measurements=[
        {"metric": "decode_code", "value": 51.5, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-18", "n": 5, "method": NDEC, "range": [51.4, 51.7],
         "note": "Block-7 is the measured code peak. Block-5 trades -16% code for +8% prose."},
        {"metric": "decode_essay", "value": 18.3, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-18", "n": 5, "method": NDEC, "range": [18.2, 18.3],
         "note": "The essay is what DSpark gives back versus MTP."},
        {"metric": "decode_chat", "value": 23.2, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-18", "n": 5, "method": NDEC + "; streamed, temperature 1.0, thinking on",
         "note": "Slightly beat MTP (21.0) on default chat with thinking on and no degrade. Thinking-off chat was a small MTP edge (22.0 / 21.3 here vs 24.6 / 23.4)."},
    ],
    caveats=[
        "Not compatible with YaRN or context >262144 — same draft-config leak as DFlash2. Keep YARN=0 and CONTEXT_LENGTH=262144.",
        "--cuda-graph-max-bs is a deprecated alias in this build; the DSpark stack uses --cuda-graph-max-bs-decode 4.",
        "--speculative-accept-threshold-acc below 1.0 measured worse. Leave it at 1.0.",
        "The DSpark draft was trained on FP8, but switching the target to QUANT=fp8 did not lift acceptance.",
        "Recorded on the older stock image with an event-counting script for the short-chat cell, where events did approximate single tokens. That is not true of the DFlash2 image.",
    ],
    provenance_tier="box",
    sources=[
        {"url": REPO, "kind": "repo", "note": "recipe + start-dspark.sh"},
        {"url": HF_DSPARK, "kind": "model", "note": "DSpark draft"},
        {"url": HASSO, "kind": "repo", "note": "published DSpark-on-GB10 config this stack builds on"},
        {"url": COOKBOOK, "kind": "docs", "note": "SGLang DGX Spark serving recipe"},
    ],
)

add(
    id="qwen38-27b-nvfp4-packed-sglang-mtp",
    title="Qwen3.8-27B NVFP4 (packed FP4 head) — SGLang + EAGLE/MTP 3/1/4",
    slug_note="The long-form writing choice, and the only path that supports YaRN out to 1M context. Slower on code: 34.5 versus DSpark's 51.5.",
    model="qwen3-8-27b",
    status="measured",
    variation=dict(PACKED_VAR),
    engine={
        "id": "sglang",
        "config": "EAGLE speculative decoding against the checkpoint's in-checkpoint MTP head, steps/topk/draft = 3/1/4 (the measured peak; the sweep gave 2->12.8, 3->17.2, 4->16.8, 5->16.3, 6->15.8). topk=1 requires draft = steps+1, validated at launch.",
        "image": "lmsysorg/sglang:qwen38-27b",
        "requires_fork": False,
        "draft_model": None,
        "spec_decode": "mtp",
        "flags": ["--speculative-algorithm EAGLE", "--speculative-num-steps 3",
                  "--speculative-eagle-topk 1", "--speculative-num-draft-tokens 4",
                  "--mem-fraction-static 0.95", "--kv-cache-dtype fp8_e4m3",
                  "--enable-metrics", "--enable-cache-report"],
    },
    hardware=SPARK,
    requirements={"memory_gb": 30, "disk_gb": 22, "min_vram_gb": None,
                  "notes": "~22GB target, no separate draft download (MTP head is in the checkpoint). mem-fraction 0.95."},
    capabilities={"vision": True, "video": True, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": 1000000},
    run={"command": "./start.sh",
         "repo": REPO,
         "profile": "profiles/qwen3.8-27b.env",
         "steps": ["cp .env.sample .env", "./start.sh"],
         "auto_bootable": True},
    measurements=[
        {"metric": "decode_code", "value": 34.5, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-18", "n": 5, "method": NDEC, "range": [34.5, 34.6]},
        {"metric": "decode_essay", "value": 24.1, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-18", "n": 5, "method": NDEC, "range": [24.1, 24.1],
         "note": "The MTP prose win is specifically the long essay."},
        {"metric": "decode_chat", "value": 21.0, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-18", "n": 5, "method": NDEC + "; streamed, temperature 1.0, thinking on",
         "note": "Thinking-off: 24.6 at T=0, 23.4 at T=1."},
    ],
    caveats=[
        "Wall-time figures from bench/bench.sh are a different clock and are not comparable to the net-decode table: thinking 17.2-20.5 tok/s, non-thinking 21.6-22.7, tool-call 26-28, TTFT on a fresh ~16K prompt ~8.3s warm / ~13s first boot.",
        "NGRAM speculative decoding measured ~30% under MTP and was rejected. Prefill CUDA graphs were also rejected — this build auto-disables them on this model anyway because GDN layers are not standard GQA.",
        "Every Tier A (kernel-path) and Tier B (config/host) tuning experiment measured zero net gain. These flags are the local optimum on this box, not a starting point.",
        "This is the only engine path here that supports YaRN. DSpark and DFlash2 both crash above 262144.",
    ],
    provenance_tier="box",
    sources=[
        {"url": REPO, "kind": "repo", "note": "recipe + start.sh"},
        {"url": COOKBOOK, "kind": "docs", "note": "SGLang DGX Spark serving recipe"},
        {"url": CARD27, "kind": "model", "note": "YaRN 1M recipe and sampling recommendations"},
    ],
)

# --------------------------------------------------------------------------
# Qwen3.8-27B on the BF16-lm_head export — the current repo default.
# --------------------------------------------------------------------------
BF16HEAD_VAR = {
    "checkpoint": "RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead",
    "publisher": "radixark",
    "quant": "nvfp4",
    "quant_detail": "W4A4 body with a dense BF16 lm_head. The export the SGLang cookbook recipes were measured against. +~1.7GB on disk / +~3.2GB at runtime versus the packed-FP4 head.",
    "format": "safetensors",
    "size_gb": 24,
    "url": HF_BF16HEAD,
    "license": "Apache-2.0",
    "downloads": None,
}

add(
    id="qwen38-27b-nvfp4-bf16head-sglang-dflash2",
    title="Qwen3.8-27B NVFP4 (BF16 lm_head) — SGLang + DFlash2, 0.90/16 profile",
    slug_note="The current default in our repo. Same NVFP4 body as the measured packed-head twin, with a denser lm_head. One community builder reports steadier tool-calls; that is unproven.",
    model="qwen3-8-27b",
    status="measured",
    variation=dict(BF16HEAD_VAR),
    engine={
        "id": "sglang",
        "config": "DFlash2 block-diffusion draft on the dense-head export, so the DFLASH selector uses the native dense path and needs no quantized-head patch. mem-fraction 0.90 with 16 concurrent requests.",
        "image": "lmsysorg/sglang:qwen38-27b-dflash2",
        "requires_fork": True,
        "draft_model": "z-lab/Qwen3.8-27B-DFlash2@50307d4",
        "spec_decode": "dflash2",
        "flags": ["--mem-fraction-static 0.90", "--max-running-requests 16",
                  "--max-mamba-cache-size 64", "--kv-cache-dtype fp8_e4m3"],
    },
    hardware=SPARK,
    requirements={"memory_gb": 32, "disk_gb": 27, "min_vram_gb": None,
                  "notes": "~24GB target + ~2.6GB draft + KV pool. GDN state pool = concurrency x 4 slots = 64 slots (~3.1GB at BF16, 78.4MB/slot)."},
    capabilities={"vision": True, "video": True, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": 262144},
    run={"command": "PROFILE=profiles/qwen3.8-27b.env ./start-model.sh",
         "repo": REPO,
         "profile": "profiles/qwen3.8-27b.env",
         "steps": ["cp .env.sample .env", "./start-dflash.sh"],
         "auto_bootable": True},
    measurements=[
        {"metric": "decode_per_stream", "value": 56.6, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-19", "n": 1, "method": "synthetic structural-decode fixture, single stream, first post-fix boot at the 0.90/16 profile"},
        {"metric": "decode_agg", "value": 227.6, "unit": "tok/s", "provenance": "box",
         "date": "2026-08-19", "n": 1, "method": "same fixture at 16 concurrent streams; aggregate across all streams",
         "note": "Per-stream degrades gracefully 56.6 -> 28.2 tok/s as concurrency rises 1 -> 16."},
        {"metric": "ttft_ms", "value": 127, "unit": "ms", "provenance": "box",
         "date": "2026-08-19", "n": 1, "method": "same fixture, single stream",
         "note": "TTFT holds 0.13-0.28s through 8 streams, then jumps to 4.18s at 16 (16-way admission on this box)."},
    ],
    caveats=[
        "The canonical probe table (code 50.9 / essay 25.4 / chat 66.6) was recorded on the packed-FP4-head twin, not on this checkpoint. Same NVFP4 body, denser lm_head. The public dashboard attributes those numbers to this export; the README's canonical table does not. Treat them as indicative until re-measured here.",
        "The concurrency ladder is one boot and one fixture — indicative, not a guarantee. Replicate before relying on it. It is also a third clock: not comparable to the net-decode table or to wall-time figures.",
        "This boot completed all 16 streams without a reboot, which is what proved the draft-capture crash was gone.",
        "Still not measured on this checkpoint: the BF16 full-precision target, and any long-context configuration.",
        "One community builder reports steadier tool-calls on the BF16 head versus the packed head. Unproven — there is a disputed counter-report claiming -20-25% decode, which needs a controlled retest.",
    ],
    provenance_tier="box",
    sources=[
        {"url": REPO, "kind": "repo", "note": "recipe, profile card, concurrency ladder"},
        {"url": HF_BF16HEAD, "kind": "model", "note": "weights"},
        {"url": COOKBOOK, "kind": "docs", "note": "measured against this export"},
    ],
)

# --------------------------------------------------------------------------
# Qwen3.8-27B official checkpoints
# --------------------------------------------------------------------------
add(
    id="qwen38-27b-bf16-official",
    title="Qwen3.8-27B BF16 — official reference weights",
    slug_note="The ceiling. Nothing quantized, nothing to argue about. Proves what the other checkpoints are losing, and it still fits in 128GB.",
    model="qwen3-8-27b",
    status="untested",
    variation={
        "checkpoint": "Qwen/Qwen3.8-27B", "publisher": "qwen", "quant": "bf16",
        "quant_detail": "Full-precision reference. The DFlash2 drafts were trained against this export.",
        "format": "safetensors", "size_gb": 52, "url": CARD27,
        "license": "Apache-2.0", "downloads": None,
    },
    engine={"id": "sglang", "config": "QUANT=bf16 or DF_TARGET=bf16. Any engine that loads the arch.",
            "image": "lmsysorg/sglang:qwen38-27b", "requires_fork": False,
            "draft_model": None, "spec_decode": "mtp", "flags": []},
    hardware=SPARK,
    requirements={"memory_gb": 60, "disk_gb": 52, "min_vram_gb": None,
                  "notes": "52GB of weights leaves room for KV on a 128GB box, but not for much concurrency."},
    capabilities={"vision": True, "video": True, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": 1000000},
    run={"command": "QUANT=bf16 ./start.sh",
         "repo": REPO, "profile": None,
         "steps": ["QUANT=bf16 ./start.sh"], "auto_bootable": True},
    measurements=[],
    caveats=["Entirely unbenched on our box. It exists in the directory as the reference the quantized rows are compared against, not as a recommendation."],
    provenance_tier=None,
    sources=[{"url": CARD27, "kind": "model", "note": "official model card"},
             {"url": REPO, "kind": "repo", "note": "QUANT=bf16 path"}],
)

add(
    id="qwen38-27b-fp8-official",
    title="Qwen3.8-27B FP8 — official near-lossless daily driver",
    slug_note="The vendor's own FP8 export. Roughly half the BF16 footprint with no community quantizer in the chain.",
    model="qwen3-8-27b",
    status="untested",
    variation={
        "checkpoint": "Qwen/Qwen3.8-27B-FP8", "publisher": "qwen", "quant": "fp8",
        "quant_detail": "Official FP8 export. Near-lossless per the vendor.",
        "format": "safetensors", "size_gb": 29,
        "url": "https://huggingface.co/Qwen/Qwen3.8-27B-FP8",
        "license": "Apache-2.0", "downloads": None,
    },
    engine={"id": "sglang", "config": "QUANT=fp8. Loads on both SGLang and vLLM without a fork.",
            "image": "lmsysorg/sglang:qwen38-27b", "requires_fork": False,
            "draft_model": None, "spec_decode": "mtp", "flags": ["--kv-cache-dtype fp8_e4m3"]},
    hardware=SPARK,
    requirements={"memory_gb": 38, "disk_gb": 29, "min_vram_gb": None, "notes": None},
    capabilities={"vision": True, "video": True, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": 1000000},
    run={"command": "QUANT=fp8 ./start.sh", "repo": REPO, "profile": None,
         "steps": ["QUANT=fp8 ./start.sh"], "auto_bootable": True},
    measurements=[],
    caveats=[
        "Unbenched on our box.",
        "GDN in float32 measured -3% versus bf16, and the FP8 KV path measured ~30% slower on the cookbook's own config — the repo pins bf16 GDN for that reason. That is about the GDN state dtype, not this checkpoint, but the two get confused.",
        "The DSpark draft was trained on FP8, yet QUANT=fp8 did not lift draft acceptance.",
    ],
    provenance_tier=None,
    sources=[{"url": "https://huggingface.co/Qwen/Qwen3.8-27B-FP8", "kind": "model", "note": "official FP8"},
             {"url": REPO, "kind": "repo", "note": "QUANT=fp8 path"}],
)

add(
    id="qwen38-27b-vllm-mtp-community",
    title="Qwen3.8-27B — vLLM + MTP (community configuration)",
    slug_note="What the same weights do on vLLM instead of SGLang. Reported 19.8-32.6 tok/s on code and ~13 on the essay across community threads — well under every SGLang path.",
    model="qwen3-8-27b",
    status="reported",
    variation=dict(BF16HEAD_VAR),
    engine={"id": "vllm", "config": "vLLM with MTP speculative decoding. Community-reported configuration, no single canonical recipe.",
            "image": None, "requires_fork": False, "draft_model": None,
            "spec_decode": "mtp", "flags": ["--enable-auto-tool-choice", "--tool-call-parser"]},
    hardware=SPARK,
    requirements={"memory_gb": 32, "disk_gb": 24, "min_vram_gb": None,
                  "notes": "No DSpark or DFlash2 support in vLLM, so the speed ceiling is MTP alone."},
    capabilities={"vision": True, "video": True, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": None},
    run={"command": None, "repo": REPO, "profile": None,
         "steps": ["Not a single recipe — see the linked community threads for the flags each builder used."],
         "auto_bootable": False},
    measurements=[
        {"metric": "decode_code", "value": 32.6, "unit": "tok/s", "provenance": "forum",
         "date": None, "n": None, "method": None, "range": [19.8, 32.6],
         "note": "Spread across community reports, not a single controlled run.",
         "source": REPO},
        {"metric": "decode_essay", "value": 13, "unit": "tok/s", "provenance": "forum",
         "date": None, "n": None, "method": None,
         "note": "Approximate. Single-sample community reports.", "source": REPO},
    ],
    caveats=[
        "The spread (19.8-32.6) is wide enough that these are not comparable to each other, let alone to our SGLang numbers. Different builders, different flags, different concurrency.",
        "Recorded here because the SGLang-versus-vLLM gap on this model is the single most consequential engine choice on this hardware, and because the gap is large.",
    ],
    provenance_tier="forum",
    sources=[{"url": REPO, "kind": "repo", "note": "PLANS.md forum-signal summary"},
             {"url": "https://github.com/vllm-project/vllm", "kind": "repo", "note": "engine"}],
)

# --------------------------------------------------------------------------
# Qwen3.8-Flash-Next single-box builds
# --------------------------------------------------------------------------
FN = "qwen3-8-flash-next"

add(
    id="qwen38-flash-next-mia-vllm-spark",
    title="Qwen3.8-Flash-Next 180B — Mia's single-Spark vLLM build",
    slug_note="The reference single-box 180B recipe. 99GB resident plus a 27GB embedding lookup table memory-mapped from disk, vision verified on, and a 400K-context stress test passed.",
    model=FN,
    status="reported",
    variation={
        "checkpoint": "Mia-AiLab/Qwen3.8-Flash-Next-NVFP4", "publisher": "mia-ai-lab",
        "quant": "nvfp4",
        "quant_detail": "99GB re-zip of the model with the 51GB PLE lookup table split out to a 27GB disk-resident file, mmap'd with MADV_RANDOM and fetched line by line. FP8 KV cache notes on by default.",
        "format": "safetensors", "size_gb": 126,
        "url": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark",
        "license": "AGPL (scripts)", "downloads": None,
    },
    engine={"id": "vllm", "config": "vLLM tensor-parallel 1, FP8 KV notes default, MTP-3 speculative decoding, 262144 native context with YARN=1 reaching 524288. Host-side memory budget: 26GB reserve plus a watchdog.",
            "image": "vllm/vllm-openai:qwen38-flash-next", "requires_fork": True,
            "draft_model": "in-checkpoint MTP head (4B)", "spec_decode": "mtp",
            "flags": ["--tensor-parallel-size 1", "--max-model-len 262144"]},
    hardware=SPARK,
    requirements={"memory_gb": 99, "disk_gb": 126, "min_vram_gb": None,
                  "notes": "99GB resident + 27GB table on disk + 26GB host reserve. About 15GB of headroom left on a 128GB box — mem-fraction pinned to 0.78 and concurrency capped at 4."},
    capabilities={"vision": True, "video": True, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": 524288},
    run={"command": "cp .env.sample .env && ./download.sh && ./start.sh",
         "repo": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark",
         "profile": "profiles/qwen3.8-flash-next-mia.env",
         "steps": ["git clone the repo", "cp .env.sample .env", "./download.sh", "./start.sh"],
         "auto_bootable": False},
    measurements=[
        {"metric": "decode_per_stream", "value": 37, "unit": "tok/s", "provenance": "forum",
         "date": "2026-09-04", "n": None, "method": None,
         "note": "Single stream. Builder-reported.",
         "source": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark"},
        {"metric": "decode_agg", "value": 86, "unit": "tok/s", "provenance": "forum",
         "date": "2026-09-04", "n": None, "method": None,
         "note": "Aggregate at 4 concurrent streams.",
         "source": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark"},
    ],
    caveats=[
        "Manual-only lane: our start-model.sh refuses to auto-boot ENGINE=vllm cards. Bring the server up from the builder's repo, then point the profile's PORT at it with auto=false to benchmark it.",
        "Prefill reads 1500-2000 tok/s per the builder. Reading is cheap here; writing is the bottleneck.",
        "The repo scripts are AGPL, which is a different license from the Apache-2.0 weights. Check both before shipping anything.",
        "At 99GB resident with a 26GB host reserve, this build has roughly 15GB of slack. Context length and concurrency both have to stay tuned down.",
    ],
    provenance_tier="forum",
    sources=[
        {"url": "https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark", "kind": "repo", "note": "the build"},
        {"url": REPO, "kind": "repo", "note": "our profile card + teardown notes"},
    ],
)

add(
    id="qwen38-flash-next-azampatti-sglang-spark",
    title="Qwen3.8-Flash-Next 180B — azampatti SGLang build",
    slug_note="The easiest install of the five known single-Spark builds, and the fastest reported coding throughput at ~43 tok/s. The catch: vision is off, so it is language-only.",
    model=FN,
    status="reported",
    variation={
        "checkpoint": "Qwen3.8-Flash-Next (base, ~135GB)", "publisher": "azampatti",
        "quant": "mixed",
        "quant_detail": "~135GB base footprint served through SGLang at 200K context.",
        "format": "safetensors", "size_gb": 135,
        "url": "https://github.com/azampatti", "license": None, "downloads": None,
    },
    engine={"id": "sglang", "config": "SGLang at 200K context. Builder describes it as the easiest install path.",
            "image": None, "requires_fork": False, "draft_model": None,
            "spec_decode": "none", "flags": []},
    hardware=SPARK,
    requirements={"memory_gb": 110, "disk_gb": 135, "min_vram_gb": None,
                  "notes": "Largest disk footprint of the five builds. Tightest fit on a 128GB box."},
    capabilities={"vision": False, "video": False, "tools": True, "thinking": True,
                  "long_context": 200000, "max_context": 200000},
    run={"command": None, "repo": "https://github.com/azampatti", "profile": None,
         "steps": ["See the builder's repo for the one-command install."], "auto_bootable": False},
    measurements=[
        {"metric": "decode_code", "value": 43, "unit": "tok/s", "provenance": "forum",
         "date": None, "n": None, "method": None, "note": "Coding workload, builder-reported.",
         "source": "https://github.com/azampatti"},
    ],
    caveats=[
        "Vision is OFF — this is a language-only build. If you need image or video input, this is not the lane.",
        "The builder states a 60 tok/s upgrade is 'days away'. Treat the current number as a floor, and treat the promise as marketing until it ships.",
        "Exact repo URL could not be pinned from our sources beyond the GitHub account; verify before following the install steps.",
    ],
    provenance_tier="forum",
    sources=[{"url": "https://github.com/azampatti", "kind": "repo", "note": "builder account"},
             {"url": REPO, "kind": "repo", "note": "our builder sweep"}],
)

add(
    id="qwen38-flash-next-blazux-vllm-hybrid-spark",
    title="Qwen3.8-Flash-Next 180B — blazux vLLM hybrid mmap build",
    slug_note="The memory-efficiency specialist: ~122GB on disk but only ~76GB resident, thanks to hybrid FP8 sides and mmap. Vision stays on. Reported ~26-31 tok/s.",
    model=FN,
    status="reported",
    variation={
        "checkpoint": "Qwen3.8-Flash-Next hybrid FP8", "publisher": "blazux",
        "quant": "mixed",
        "quant_detail": "Hybrid quantization: FP8 on the sides, lower precision elsewhere. Roughly +20% throughput from the hybrid FP8 sides alone.",
        "format": "safetensors", "size_gb": 122,
        "url": "https://github.com/blazux", "license": None, "downloads": None,
    },
    engine={"id": "vllm", "config": "vLLM with mmap-backed weight loading. ~122GB on disk compresses to ~76GB resident.",
            "image": None, "requires_fork": True, "draft_model": None,
            "spec_decode": "none", "flags": []},
    hardware=SPARK,
    requirements={"memory_gb": 76, "disk_gb": 122, "min_vram_gb": None,
                  "notes": "Lowest resident footprint of the full-featured 180B builds — about 43GB of headroom left on a 128GB box, versus ~15GB for Mia's."},
    capabilities={"vision": True, "video": None, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": None},
    run={"command": None, "repo": "https://github.com/blazux", "profile": None,
         "steps": ["See the builder's repo."], "auto_bootable": False},
    measurements=[
        {"metric": "decode_per_stream", "value": 31, "unit": "tok/s", "provenance": "forum",
         "date": None, "n": None, "method": None, "range": [26, 31],
         "note": "Builder-reported range. The Saren fork of this build reports 47.5 on code and 60 on JSON extraction.",
         "source": "https://github.com/blazux"},
    ],
    caveats=[
        "Slower than azampatti and Mia on throughput; the trade is resident memory and working vision.",
        "The Saren fork reports substantially better numbers (47.5 code / 60 JSON) on the same approach. Fork-versus-upstream deltas this large are usually a configuration difference, not a code difference — verify which one you are actually installing.",
        "Exact repo URL could not be pinned from our sources beyond the GitHub account.",
    ],
    provenance_tier="forum",
    sources=[{"url": "https://github.com/blazux", "kind": "repo", "note": "builder account"},
             {"url": REPO, "kind": "repo", "note": "our builder sweep"}],
)

add(
    id="qwen38-flash-next-orcarouter-gguf-uncensored",
    title="Qwen3.8-Flash-Next 180B — OrcaRouter uncensored GGUF (SSD sidecar)",
    slug_note="The uncensored lane, and the fastest reading throughput anywhere in the directory: 489 tok/s prefill, 28.7 tok/s decode, vision on, 256K context. It needs a custom Rust engine fork.",
    model=FN,
    status="reported",
    variation={
        "checkpoint": "Baekpica/Qwen3.8-Flash-Next-Uncensored-Mixed-Quant-SSD-PLE-GGUF",
        "publisher": "orcarouter", "quant": "gguf-q4",
        "quant_detail": "Mixed-quant GGUF with the PLE embedding table split to an SSD sidecar. ~110GB plus the sidecar. Gated download.",
        "format": "gguf", "size_gb": 110,
        "url": "https://huggingface.co/Baekpica", "license": None, "downloads": None,
    },
    engine={"id": "custom-fork", "config": "ds4-dfm-rs, the builder's own Rust engine fork. Not SGLang or vLLM compatible — these weights will not load in a stock engine.",
            "image": None, "requires_fork": True, "draft_model": None,
            "spec_decode": "other", "flags": []},
    hardware=SPARK,
    requirements={"memory_gb": 100, "disk_gb": 140, "min_vram_gb": None,
                  "notes": "Needs fast NVMe for the SSD sidecar; the embedding table is read from disk during generation."},
    capabilities={"vision": True, "video": None, "tools": None, "thinking": None,
                  "long_context": 262144, "max_context": 262144},
    run={"command": None, "repo": "https://huggingface.co/Baekpica", "profile": None,
         "steps": ["Request access — the download is gated.",
                   "Install the builder's ds4-dfm-rs Rust engine fork.",
                   "A stock engine will not load these weights."],
         "auto_bootable": False},
    measurements=[
        {"metric": "decode_per_stream", "value": 28.7, "unit": "tok/s", "provenance": "forum",
         "date": None, "n": None, "method": None, "note": "Write/decode throughput, builder-reported.",
         "source": "https://huggingface.co/Baekpica"},
        {"metric": "decode_agg", "value": 489, "unit": "tok/s", "provenance": "forum",
         "date": None, "n": None, "method": None,
         "note": "Read/prefill throughput. Comparable to Mia's 1500-2000 prefill claim on a different fixture, so these two numbers are not comparable to each other.",
         "source": "https://huggingface.co/Baekpica"},
    ],
    caveats=[
        "Gated download plus a mandatory custom engine fork. This is the least portable entry in the directory: the weights are useless without their engine.",
        "Reproducibility is the weakest tier here. No independent replication of the 489 / 28.7 figures.",
        "Uncensored means the alignment safety behavior is removed. That is a deliberate product choice by the builder, not a bug — know what you are deploying.",
        "OrcaRouter itself is a router, not a benchmark harness. It does not publish comparative measurements against other builds.",
    ],
    provenance_tier="forum",
    sources=[{"url": "https://huggingface.co/Baekpica", "kind": "model", "note": "gated GGUF"},
             {"url": REPO, "kind": "repo", "note": "our verification of the engine requirement"}],
)

add(
    id="qwen38-flash-next-unsloth-gguf-iq1s",
    title="Qwen3.8-Flash-Next 180B — unsloth GGUF UD-IQ1_S (smallest usable)",
    slug_note="The 24GB-card lane for a 180B model: ~67GB in IQ1_S, runnable through llama.cpp. Vision arrives via a separate projector file. Vendor-claimed ~34.5 tok/s.",
    model=FN,
    status="claimed",
    variation={
        "checkpoint": "unsloth/Qwen3.8-Flash-Next-GGUF (UD-IQ1_S)", "publisher": "unsloth",
        "quant": "gguf-q2",
        "quant_detail": "UD-IQ1_S, unsloth's dynamic ~1-bit-per-weight scheme. Smallest usable Flash-Next build known.",
        "format": "gguf", "size_gb": 67,
        "url": "https://huggingface.co/unsloth", "license": "Apache-2.0", "downloads": None,
    },
    engine={"id": "llama-cpp", "config": "llama.cpp with CPU/GPU layer split. Vision requires the separate mmproj projector file, which is not inside the main GGUF.",
            "image": None, "requires_fork": False, "draft_model": None,
            "spec_decode": "none", "flags": ["-ngl (layers on GPU)", "--mmproj (vision projector)"]},
    hardware=["dgx-spark", "gpu-24gb", "mac-128gb"],
    requirements={"memory_gb": 72, "disk_gb": 67, "min_vram_gb": 24,
                  "notes": "Runs with partial GPU offload on a 24GB card — the rest spills to system RAM, which is where the throughput goes. Comfortable on 128GB unified memory."},
    capabilities={"vision": True, "video": None, "tools": None, "thinking": True,
                  "long_context": 262144, "max_context": None},
    run={"command": "llama-server -hf unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ1_S",
         "repo": "https://huggingface.co/unsloth", "profile": None,
         "steps": ["Download the GGUF plus its mmproj file",
                   "llama-server -hf unsloth/Qwen3.8-Flash-Next-GGUF:UD-IQ1_S -ngl 99"],
         "auto_bootable": True},
    measurements=[
        {"metric": "decode_per_stream", "value": 34.5, "unit": "tok/s", "provenance": "vendor",
         "date": None, "n": None, "method": None,
         "note": "Vendor-claimed. No hardware or configuration stated in our source, so it is not comparable to any other row.",
         "source": "https://huggingface.co/unsloth"},
    ],
    caveats=[
        "At ~1 bit per weight, quality degradation on a 180B MoE is not characterized anywhere in our sources. The vendor number is a throughput claim, not a quality claim.",
        "The 34.5 tok/s figure has no stated hardware. Do not compare it to the Spark builds.",
        "Exact repo id and quant filename should be re-verified against the publisher before download; our source records the org and quant name but not a confirmed repo path.",
    ],
    provenance_tier="vendor",
    sources=[{"url": "https://huggingface.co/unsloth", "kind": "model", "note": "GGUF publisher"},
             {"url": REPO, "kind": "repo", "note": "our quant shortlist"}],
)

# --------------------------------------------------------------------------
# Qwen3.5-122B-A10B — Albond INT4-hybrid
# --------------------------------------------------------------------------
add(
    id="qwen35-122b-a10b-albond-int4-vllm-spark",
    title="Qwen3.5-122B-A10B — Albond INT4+FP8 hybrid on vLLM",
    slug_note="The best-documented 100B-class single-Spark recipe: ~67GB resident, MTP-2, 256K context, and the builder publishes both throughput and a quality peak rather than only one of them.",
    model="qwen3-5-122b-a10b",
    status="reported",
    variation={
        "checkpoint": "Intel/Qwen3.5-122B-A10B-int4-AutoRound", "publisher": "intel",
        "quant": "int4-hybrid",
        "quant_detail": "AutoRound INT4 body with FP8 on selected layers. ~67GB resident for a 122B-total / 10B-active MoE.",
        "format": "safetensors", "size_gb": 67,
        "url": "https://huggingface.co/Intel/Qwen3.5-122B-A10B-int4-AutoRound",
        "license": "Apache-2.0", "downloads": None,
    },
    engine={"id": "vllm", "config": "vLLM from the builder's repo with MTP-2 speculative decoding, mem-fraction 0.80, concurrency 4, chunked prefill 8192, 262144 context.",
            "image": "vllm-vllm-openai-albond", "requires_fork": True,
            "draft_model": "in-checkpoint MTP head, 2 steps", "spec_decode": "mtp",
            "flags": ["--gpu-memory-utilization 0.80", "--max-model-len 262144"]},
    hardware=SPARK,
    requirements={"memory_gb": 67, "disk_gb": 70, "min_vram_gb": None,
                  "notes": "~67GB resident leaves about 52GB of headroom on a 128GB box — far more comfortable than the 180B builds."},
    capabilities={"vision": False, "video": False, "tools": True, "thinking": True,
                  "long_context": 262144, "max_context": 262144},
    run={"command": "See the builder's repo — manual vLLM boot",
         "repo": "https://github.com/albond/DGX_Spark_Qwen3.5-122B-A10B-AR-INT4",
         "profile": "profiles/qwen3.5-122b-albond.env",
         "steps": ["Clone the builder's repo", "Boot vLLM per his instructions",
                   "Point profiles/qwen3.5-122b-albond.env at the running PORT with auto=false to benchmark it"],
         "auto_bootable": False},
    measurements=[
        {"metric": "decode_per_stream", "value": 52, "unit": "tok/s", "provenance": "forum",
         "date": None, "n": None, "method": None, "note": "Builder-reported.",
         "source": "https://github.com/albond/DGX_Spark_Qwen3.5-122B-A10B-AR-INT4"},
        {"metric": "bench_code", "value": 54.9, "unit": "score", "provenance": "forum",
         "date": None, "n": None, "method": None,
         "note": "LongCode peak, builder-reported. Different fixture from our code probe — not comparable to the 27B tok/s rows.",
         "source": "https://github.com/albond/DGX_Spark_Qwen3.5-122B-A10B-AR-INT4"},
    ],
    caveats=[
        "Manual-only lane: our start-model.sh refuses to auto-boot ENGINE=vllm cards.",
        "52 tok/s for a 10B-active MoE is faster than any 180B build in this directory, and it is the concrete demonstration of the bandwidth argument: on a 273 GB/s box, active parameters decide speed, not total parameters.",
        "Not measured on our box. The profile card exists so the harness can record numbers once the server is up.",
    ],
    provenance_tier="forum",
    sources=[
        {"url": "https://github.com/albond/DGX_Spark_Qwen3.5-122B-A10B-AR-INT4", "kind": "repo", "note": "the recipe"},
        {"url": "https://huggingface.co/Intel/Qwen3.5-122B-A10B-int4-AutoRound", "kind": "model", "note": "weights"},
    ],
)

# --------------------------------------------------------------------------
# Profile-card lanes: recipe cards that validate but have no measurements yet.
# --------------------------------------------------------------------------
def profile_lane(pid, model, title, checkpoint, publisher, quant, quant_detail,
                 size_gb, url, ctx, mem_frac, conc, spec, spec_decode, slug,
                 extra_caveats=(), hardware=None, engine_id="sglang", mem_gb=None):
    return dict(
        id=pid, title=title, slug_note=slug, model=model, status="untested",
        variation={"checkpoint": checkpoint, "publisher": publisher, "quant": quant,
                   "quant_detail": quant_detail, "format": "safetensors",
                   "size_gb": size_gb, "url": url, "license": "Apache-2.0", "downloads": None},
        engine={"id": engine_id,
                "config": "SGLang from our recipe card. " + (spec or "Speculative decoding off."),
                "image": "lmsysorg/sglang:qwen38-27b", "requires_fork": False,
                "draft_model": None, "spec_decode": spec_decode,
                "flags": [f"--mem-fraction-static {mem_frac}", f"--max-running-requests {conc}",
                          f"--context-length {ctx}"]},
        hardware=hardware or SPARK,
        requirements={"memory_gb": mem_gb if mem_gb is not None else round(size_gb * 1.25),
                      "disk_gb": size_gb, "min_vram_gb": None,
                      "notes": f"mem-fraction {mem_frac}, concurrency {conc}, context {ctx}."},
        capabilities={"vision": False, "video": False, "tools": True, "thinking": True,
                      "long_context": ctx, "max_context": ctx},
        run={"command": f"PROFILE=profiles/{pid.split('-card-')[-1]}.env ./start-model.sh",
             "repo": REPO, "profile": None,
             "steps": [f"PROFILE=profiles/<card>.env ./start-model.sh"],
             "auto_bootable": engine_id == "sglang"},
        measurements=[],
        caveats=list(extra_caveats) + [
            "Recipe card validates and the container reaches 'Starting container', but no benchmark has been run. There are no numbers for this entry yet.",
        ],
        provenance_tier=None,
        sources=[{"url": REPO, "kind": "repo", "note": "recipe card in profiles/"},
                 {"url": url, "kind": "model", "note": "weights"}],
    )


PROFILES = [
    dict(pid="qwen36-35b-a3b-nvidia-nvfp4-sglang", model="qwen3-6-35b-a3b",
         title="Qwen3.6-35B-A3B — nvidia NVFP4 on SGLang (our default card)",
         checkpoint="nvidia/Qwen3.6-35B-A3B-NVFP4", publisher="nvidia", quant="nvfp4",
         quant_detail="ModelOpt v0.44 NVFP4, ~21-24GB. The default in our recipe card.",
         size_gb=23, url="https://huggingface.co/nvidia/Qwen3.6-35B-A3B-NVFP4",
         ctx=262144, mem_frac=0.85, conc=10, spec_decode="eagle",
         spec="EAGLE 3/1/4 speculative decoding.",
         slug="Our default recipe card for the MoE challenger. Needs SGLang >=0.5.10 with both the qwen3 and qwen3_coder parsers.",
         extra_caveats=[
             "If boot rejects the qwen3_5_moe arch, set IMAGE=lmsysorg/sglang:v0.5.15-cu130 — the first release with native ModelOpt mixed-precision load, no patch needed.",
             "mem-fraction 0.80-0.85 for this family, versus 0.95 on 3.8/MTP.",
             "The DSpark draft is 3.8-only, so start-model.sh refuses dspark for this card and forces mtp.",
         ]),
    dict(pid="qwen36-35b-a3b-unsloth-nvfp4-vllm", model="qwen3-6-35b-a3b",
         title="Qwen3.6-35B-A3B — unsloth NVFP4 Fast on vLLM",
         checkpoint="unsloth/Qwen3.6-35B-A3B-NVFP4", publisher="unsloth", quant="nvfp4",
         quant_detail="unsloth 'Fast' NVFP4 with tool-call fixes and a developer role.",
         size_gb=22, url="https://huggingface.co/unsloth",
         ctx=262144, mem_frac=0.85, conc=10, spec_decode="mtp", spec=None,
         engine_id="vllm", mem_gb=30,
         slug="The tool-calling lane: reported +6.7% on tool-call accuracy and 83.8 tok/s on vLLM.",
         extra_caveats=[
             "The 83.8 tok/s and +6.7% figures are publisher claims, not measurements, and are recorded in the model notes rather than as measurements on this entry until we can source them to a specific page.",
             "Manual-only lane: start-model.sh refuses ENGINE=vllm cards.",
             "Exact repo id needs re-verification against the publisher before download.",
         ]),
    dict(pid="qwen36-35b-a3b-fp8-official", model="qwen3-6-35b-a3b",
         title="Qwen3.6-35B-A3B — official FP8 on SGLang",
         checkpoint="Qwen/Qwen3.6-35B-A3B-FP8", publisher="qwen", quant="fp8",
         quant_detail="Official FP8 export.",
         size_gb=35, url="https://huggingface.co/Qwen/Qwen3.6-35B-A3B-FP8",
         ctx=262144, mem_frac=0.85, conc=10, spec_decode="eagle",
         spec="EAGLE 3/1/4 speculative decoding.", mem_gb=44,
         slug="The single-stream-latency winner of the three 3.6-35B lanes, at the cost of footprint.",
         extra_caveats=["Needs a chat-template fix under SGLang before it will serve correctly."]),
    dict(pid="qwen36-27b-fp8-sglang", model="qwen3-6-27b",
         title="Qwen3.6-27B — official FP8 on SGLang",
         checkpoint="Qwen/Qwen3.6-27B-FP8", publisher="qwen", quant="fp8",
         quant_detail="Official FP8 export, ~28GB.",
         size_gb=28, url="https://huggingface.co/Qwen/Qwen3.6-27B-FP8",
         ctx=262144, mem_frac=0.90, conc=10, spec_decode="eagle",
         spec="EAGLE 3/1/4 speculative decoding.", mem_gb=36,
         slug="The dense sibling one generation back. The cleanest A/B for the reported 3.8 regressions in trivia recall and long analytical documents.",
         extra_caveats=["MTP head presence is unverified on this checkpoint. If boot rejects EAGLE spec, set SPEC_ENABLE=0 and relaunch."]),
    dict(pid="qwen35-27b-fp8-sglang", model="qwen3-5-27b",
         title="Qwen3.5-27B — official FP8 on SGLang",
         checkpoint="Qwen/Qwen3.5-27B-FP8", publisher="qwen", quant="fp8",
         quant_detail="Official FP8 export.",
         size_gb=28, url="https://huggingface.co/Qwen/Qwen3.5-27B-FP8",
         ctx=262144, mem_frac=0.90, conc=10, spec_decode="eagle",
         spec="EAGLE 3/1/4 speculative decoding.", mem_gb=36,
         slug="Two generations back on the dense line. In the directory as the baseline for the 3.6 -> 3.8 dense comparison.",
         extra_caveats=["MTP on this checkpoint is unverified; set SPEC_ENABLE=0 if boot rejects it."]),
    dict(pid="qwen35-35b-a3b-fp8-sglang", model="qwen3-5-35b-a3b",
         title="Qwen3.5-35B-A3B — official FP8 on SGLang",
         checkpoint="Qwen/Qwen3.5-35B-A3B-FP8", publisher="qwen", quant="fp8",
         quant_detail="Official FP8 export.",
         size_gb=35, url="https://huggingface.co/Qwen/Qwen3.5-35B-A3B-FP8",
         ctx=262144, mem_frac=0.85, conc=10, spec_decode="eagle",
         spec="EAGLE 3/1/4 speculative decoding.", mem_gb=44,
         slug="First Gated-DeltaNet hybrid MoE generation. The 3.6-35B-A3B is its direct child.",
         extra_caveats=["MTP on this checkpoint is unverified; set SPEC_ENABLE=0 if boot rejects it."]),
    dict(pid="qwen35-9b-bf16-sglang", model="qwen3-5-9b",
         title="Qwen3.5-9B — BF16 on SGLang",
         checkpoint="Qwen/Qwen3.5-9B", publisher="qwen", quant="bf16",
         quant_detail="Full precision, ~18GB. No quantization needed at this size.",
         size_gb=18, url="https://huggingface.co/Qwen/Qwen3.5-9B",
         ctx=131072, mem_frac=0.90, conc=16, spec_decode="none", spec=None, mem_gb=23,
         hardware=["dgx-spark", "gpu-24gb", "mac-128gb"],
         slug="Fits essentially anywhere: 24GB cards, 32GB Macs, and comfortably on a Spark. Vendor-reported MMLU-Pro 82.5.",
         extra_caveats=[
             "Small models in this family carry no MTP head, so speculative decoding is off and there is no free speed available.",
             "The MMLU-Pro 82.5 figure is a vendor claim recorded in the model notes, not a measurement on this entry.",
         ]),
    dict(pid="qwen30-32b-fp8-sglang", model="qwen3-0-32b",
         title="Qwen3-32B — official FP8 on SGLang",
         checkpoint="Qwen/Qwen3-32B-FP8", publisher="qwen", quant="fp8",
         quant_detail="Official FP8 export.",
         size_gb=33, url="https://huggingface.co/Qwen/Qwen3-32B-FP8",
         ctx=131072, mem_frac=0.90, conc=10, spec_decode="none", spec=None, mem_gb=41,
         slug="Pre-hybrid dense control. Pure Transformer, no GDN, no MTP head — dense-vs-dense against 3.8-27B isolates the architecture generation at a fixed serving stack.",
         extra_caveats=["No MTP head, so speculative decoding is off. Any speed comparison against 3.8-27B measures the architecture change, not the quant."]),
    dict(pid="qwen30-30b-a3b-fp8-sglang", model="qwen3-0-30b-a3b",
         title="Qwen3-30B-A3B — official FP8 on SGLang",
         checkpoint="Qwen/Qwen3-30B-A3B-FP8", publisher="qwen", quant="fp8",
         quant_detail="Official FP8 export.",
         size_gb=31, url="https://huggingface.co/Qwen/Qwen3-30B-A3B-FP8",
         ctx=131072, mem_frac=0.85, conc=10, spec_decode="none", spec=None, mem_gb=39,
         slug="Pre-hybrid MoE control. Shows what the GDN hybrid bought versus the Wave-1 MoEs at the same active-parameter count.",
         extra_caveats=["No MTP head, so speculative decoding is off."]),
]
for p in PROFILES:
    card = profile_lane(**p)
    prof = {
        "qwen36-35b-a3b-nvidia-nvfp4-sglang": "qwen3.6-35b-a3b",
        "qwen36-35b-a3b-unsloth-nvfp4-vllm": None,
        "qwen36-35b-a3b-fp8-official": None,
        "qwen36-27b-fp8-sglang": "qwen3.6-27b-fp8",
        "qwen35-27b-fp8-sglang": "qwen3.5-27b-fp8",
        "qwen35-35b-a3b-fp8-sglang": "qwen3.5-35b-a3b-fp8",
        "qwen35-9b-bf16-sglang": "qwen3.5-9b",
        "qwen30-32b-fp8-sglang": "qwen3.0-32b-fp8",
        "qwen30-30b-a3b-fp8-sglang": "qwen3.0-30b-a3b-fp8",
    }.get(p["pid"])
    if prof:
        card["run"]["profile"] = f"profiles/{prof}.env"
        card["run"]["command"] = f"PROFILE=profiles/{prof}.env ./start-model.sh"
        card["run"]["steps"] = [f"PROFILE=profiles/{prof}.env ./start-model.sh"]
    card.setdefault("updated", "2026-09-05")
    setups.append(card)

os.makedirs(OUT, exist_ok=True)
for s in setups:
    path = os.path.join(OUT, s["id"] + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
print(f"wrote {len(setups)} setups to {OUT}")
