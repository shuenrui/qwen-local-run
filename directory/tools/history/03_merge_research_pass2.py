#!/usr/bin/env python3
"""Merge pass 2: GitHub-recipe findings into the directory dataset.

Measurements are converted from each repo's claimed numbers (source = the repo,
quote kept in the note). Outliers and mis-scoped numbers are dropped per setup
and explained in caveats instead of silently kept.
"""
import json
import os
import urllib.request

SETUPS = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data/setups"
PUB = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data/publishers.json"
UPDATED = "2026-09-05"
G = {i: e for i, e in enumerate(json.load(open("/tmp/research_github.json", encoding="utf-8")))}


def hf_api_size(checkpoint, pattern=None):
    req = urllib.request.Request("https://huggingface.co/api/models/" + checkpoint,
                                 headers={"User-Agent": "directory-merge"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            info = json.load(r)
    except Exception:
        return None
    files = [(s.get("rfilename") or "", s.get("size") or 0) for s in info.get("siblings", [])]
    if pattern:
        pick = [sz for n, sz in files if pattern in n.lower() and n.lower().endswith(".gguf")]
        if pick:
            return round(sum(pick) / 1e9, 1)
        return None
    sh = [sz for n, sz in files if n.lower().endswith(".safetensors")]
    if sh:
        return round(sum(sh) / 1e9, 1)
    gg = [sz for n, sz in files if n.lower().endswith(".gguf")]
    return round(max(gg) / 1e9, 1) if gg else None


def ms_from(idx, drop=(), method=""):
    e = G[idx]
    out = []
    for m in e["claimed"]:
        if (m["metric"], m["value"]) in drop:
            continue
        d = {"metric": m["metric"], "value": m["value"], "unit": m["unit"],
             "provenance": "forum", "source": e["repo"], "date": e.get("date"),
             "method": method or "builder's own harness, see repo README",
             "note": m["context"]}
        out.append(d)
    return out


def write_setup(sid, title, slug, model, var, engine, hardware, req, steps,
                measurements, caveats, sources, caps=None):
    var = dict(var)
    if var.get("size_gb") is None:
        var["size_gb"] = hf_api_size(var["checkpoint"], var.pop("file_match", None))
    else:
        var.pop("file_match", None)
    if var["size_gb"] is None:
        print("SKIP (no size):", sid)
        return
    e = {"image": None, "requires_fork": False, "draft_model": None,
         "spec_decode": "none", "flags": []}
    e.update(engine)
    s = {"id": sid, "title": title, "slug_note": slug, "model": model,
         "status": "reported" if measurements else "untested",
         "variation": var, "engine": e, "hardware": hardware,
         "requirements": req,
         "capabilities": caps or {"vision": False, "video": False, "tools": True,
                                  "thinking": True, "long_context": 262144,
                                  "max_context": 262144},
         "run": {"repo": sources[0]["url"], "command": None, "steps": steps},
         "measurements": measurements, "caveats": caveats,
         "provenance_tier": "forum" if measurements else None,
         "sources": sources, "updated": UPDATED}
    with open(os.path.join(SETUPS, sid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wrote", sid)


# publishers + hardware needed by this pass -------------------------------
p = json.load(open(PUB, encoding="utf-8"))
for k, v in {
    "ollama": {"name": "Ollama library", "kind": "vendor", "url": "https://ollama.com",
               "note": "Packaged default-quant pulls of open weights."},
    "entrpi": {"name": "Entrpi", "kind": "individual",
               "url": "https://github.com/Entrpi/qwen3.5-122B-A10B-on-spark",
               "note": "DFlash block-diffusion spec-dec installer for the 122B on Spark."},
    "sojufx": {"name": "sojufx", "kind": "individual",
               "url": "https://github.com/sojufx/Qwen3.5-122B-A10B-DFlash-DGX-Spark-Recipe",
               "note": "Native-vLLM production serve recipe for 122B NVFP4 + DFlash on Spark."},
    "hudsonwa": {"name": "hudsonwa", "kind": "individual",
                 "url": "https://github.com/hudsonwa/Qwen3.8-Flash-Next-oMLX-Recipe",
                 "note": "oMLX 8-slot concurrent Flash-Next serving recipe on 128 GB Macs."},
    "pipenetwork": {"name": "PipeNetwork", "kind": "community-org",
                    "url": "https://github.com/PipeNetwork/qwen38-flash-next-mlx",
                    "note": "MLX runtime + streaming quantization for the Flash-Next architecture."},
    "petems": {"name": "petems", "kind": "individual",
               "url": "https://github.com/petems/qwen-local-silicon-32to64gb-macbook-guide",
               "note": "Decision-tree runbook for Qwen on 32-64 GB Apple Silicon MacBooks."},
}.items():
    p["publishers"].setdefault(k, v)
json.dump(p, open(PUB, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(PUB, "a", encoding="utf-8").write("\n")

HW = "/home/shuenrui/Qwen3.8-27B-SGLang-DGX-Spark/directory/data/hardware/mac-64gb.json"
if not os.path.exists(HW):
    json.dump({
        "id": "mac-64gb",
        "name": "Apple Silicon Mac, 32-64 GB unified (M1-M5 Pro/Max class)",
        "vendor": "Apple", "chip": "M1-M5 Pro/Max", "arch": "arm64, Metal",
        "form_factor": "laptop/desktop", "memory_gb": 64, "memory_usable_gb": 58,
        "memory_type": "unified LPDDR4x/LPDDR5", "bandwidth_gbs": 200,
        "bandwidth_range_gbs": [68, 546],
        "cpu": "Apple Silicon Pro/Max class",
        "gpu": "integrated, shares the unified pool",
        "notes": [
            "A wide class on purpose: 32 GB and 64 GB Macs behave differently, and bandwidth spans 68 GB/s (M1 8-core) to 546 GB/s (M4 Max). Reported numbers name the exact chip in the measurement note.",
            "The binding constraint is RAM, not bandwidth: a 35B MoE at Q4 needs ~22 GB, which a 32 GB Mac runs with almost nothing left for context.",
            "MoE expert streaming from SSD (mlx-flash style) is what makes over-RAM models possible here at a large speed cost."
        ],
        "measured_by_us": False,
        "url": "https://github.com/petems/qwen-local-silicon-32to64gb-macbook-guide",
        "updated": UPDATED,
    }, open(HW, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(HW, "a", encoding="utf-8").write("\n")
    print("wrote hardware mac-64gb")

# ------------------------------------------------------------- new setups ---
e1 = G[1]
write_setup(
    "qwen36-35b-a3b-ollama-gb10-pgx",
    "Qwen3.6-35B-A3B via Ollama on a ThinkStation PGX (GB10)",
    "The zero-effort lane on GB10 silicon: Ollama's default quant does 60.2 tok/s "
    "on the 35B MoE, and 11.5 on the dense 27B — the MoE gap in one row.",
    "qwen3-6-35b-a3b",
    {"checkpoint": "ollama.com/library/qwen3.6:35b-a3b", "publisher": "ollama",
     "quant": "gguf-q4", "quant_detail": "Ollama default Q4 quant",
     "format": "gguf", "size_gb": 23,
     "url": "https://ollama.com/library/qwen3.6:35b-a3b"},
    {"id": "ollama", "config": "Ollama 0.24.0 with Flash Attention on GB10"},
    ["thinkstation-pgx"],
    {"memory_gb": 27, "disk_gb": 23, "min_vram_gb": None,
     "notes": "ollama ps footprint at 32K context."},
    ["ollama pull qwen3.6:35b-a3b", "ollama run qwen3.6:35b-a3b"],
    ms_from(1, drop={("decode_chat", 11.5), ("ttft_ms", 40000), ("memory_gb", 15.4)},
            method="Ollama benchmark script in the repo, 0.5K prompt"),
    ["The dense 27B on the same box does 11.5 tok/s with TTFT 40 s at 32K (175 s at "
     "128K) — kept as context here because this card is the 35B MoE lane.",
     "Ollama's default quant is a convenience choice, not a quality-optimised one; "
     "compare against the GGUF/MLX lanes before trusting it for quality work."],
    [{"url": e1["repo"], "kind": "repo", "note": "benchmark repo and script"},
     {"url": "https://ollama.com/library/qwen3.6:35b-a3b", "kind": "model", "note": "model pull"}])

e2 = G[2]
write_setup(
    "qwen36-35b-a3b-mlx-flash-ssd-streaming-mac",
    "Qwen3.6-35B-A3B on mlx-flash: MoE experts streamed from SSD on a Mac",
    "The lane that runs models bigger than RAM: 101 tok/s on the 3.6 35B MoE on an "
    "M5 Pro 64 GB by keeping cold experts on SSD.",
    "qwen3-6-35b-a3b",
    {"checkpoint": "mlx-community/Qwen3.6-35B-A3B-4bit", "publisher": "mlx-community",
     "quant": "mlx-4", "quant_detail": "4-bit MLX with expert caching / SSD streaming",
     "format": "mlx", "size_gb": None,
     "url": "https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit"},
    {"id": "mlx-lm", "requires_fork": True,
     "config": "mlx-flash runtime: cold MoE experts streamed from SSD, hot experts cached in RAM"},
    ["mac-64gb"],
    {"memory_gb": 24, "disk_gb": 20, "min_vram_gb": None,
     "notes": "19 GB of weights; expert cache keeps RAM use near the hot-expert set."},
    ["Install mlx-flash from the repo", "Point it at the 4-bit MLX build",
     "Keep the model directory on fast SSD storage; cold experts stream from disk"],
    ms_from(2, drop={("decode_chat", 82.6), ("decode_chat", 122.1), ("decode_chat", 53.5),
                     ("decode_chat", 100.6), ("decode_chat", 17.8), ("decode_chat", 4.4),
                     ("memory_gb", 36)},
            method="mlx-flash benchmark runs quoted in the repo README"),
    ["Only the 3.6-35B-A3B number belongs to this card; the repo's other rows "
     "(30B-A3B 82.6 on M3 Max 36 GB, Qwen1.5-MoE 122.1, Qwen3.5-27B 17.8 flagged "
     "slow, Qwen3.5-397B 4.4 via SSD streaming) are other models on other Macs.",
     "SSD streaming trades latency for capacity: expect stalls when a cold expert "
     "set is touched for the first time."],
    [{"url": e2["repo"], "kind": "repo", "note": "the mlx-flash runtime and benchmarks"},
     {"url": "https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit", "kind": "model",
      "note": "weights"}])

e3 = G[3]
write_setup(
    "qwen36-27b-unsloth-gguf-llamacpp-4090-samevocab",
    "Qwen3.6-27B Q4 on one RTX 4090: mainline llama.cpp + same-vocab draft",
    "The 24 GB-card lane with a quality gate: 43.2 tok/s aggregate with a "
    "Qwen3.5-4B same-vocab draft, and a documented warning that ik_llama.cpp "
    "cross-vocab spec-dec silently corrupts output here.",
    "qwen3-6-27b",
    {"checkpoint": "unsloth/Qwen3.6-27B-GGUF", "publisher": "unsloth",
     "quant": "gguf-q4", "quant_detail": "Q4_K_M target with Qwen3.5-4B-Q4_K_M same-vocab draft",
     "format": "gguf", "size_gb": None, "file_match": "q4_k_m",
     "url": "https://huggingface.co/unsloth/Qwen3.6-27B-GGUF"},
    {"id": "llama-cpp", "spec_decode": "other",
     "config": "mainline llama.cpp -DGGML_CUDA=ON CUDA 12.8, same-vocab speculative draft, q4 KV",
     "draft_model": "Qwen3.5-4B-Q4_K_M"},
    ["gpu-24gb"],
    {"memory_gb": 22, "disk_gb": 32, "min_vram_gb": 22,
     "notes": "22 GB VRAM for the C1-agg stack; 32K/64K/256K configs sit at 21-22 GB with q4 KV."},
    ["Build mainline llama.cpp with CUDA 12.8",
     "Load the Q4_K_M target plus the Qwen3.5-4B same-vocab draft",
     "Run the repo's bench-split.py quality gate before trusting any speed number"],
    ms_from(3, drop={("bench_code", 63), ("bench_other", 102)},
            method="repo's per-category bench with the quality gate"),
    ["The dropped ik_llama.cpp numbers (63 code / 102 json tok/s) FAIL the repo's own "
     "quality check: cross-vocab speculative decoding silently corrupts output on "
     "this stack. Speed without the gate is a trap here.",
     "Quality gate score 6/6 categories is recorded in the measurements; treat any "
     "config that scores below that as broken, not fast."],
    [{"url": e3["repo"], "kind": "repo", "note": "recipes, benches and the quality gate"},
     {"url": "https://huggingface.co/unsloth/Qwen3.6-27B-GGUF", "kind": "model", "note": "weights"}])

e6 = G[6]
write_setup(
    "qwen38-27b-r0b0tlab-nvfp4-mtp-sm121-sglang",
    "Qwen3.8-27B NVFP4 — r0b0tlab click-run SGLang profiles on SM121",
    "Click-run scripts with a matched draft-block sweep: DFlash2 K8 at 27.9 tok/s "
    "single stream, 276.4 aggregate at C6, plus think-on/think-off quality canaries.",
    "qwen3-8-27b",
    {"checkpoint": "r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121", "publisher": "r0b0tlab",
     "quant": "nvfp4", "quant_detail": "NVFP4 body with MTP head retained for SM121",
     "format": "safetensors", "size_gb": None,
     "url": "https://huggingface.co/r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121"},
    {"id": "sglang", "spec_decode": "dflash2",
     "config": "click_run_dflash2.sh / dspark / eagle scripts; DFlash2 K8 draft, draft-block sweep included",
     "draft_model": "z-lab/Qwen3.8-27B-DFlash2"},
    ["dgx-spark"],
    {"memory_gb": 30, "disk_gb": 25, "min_vram_gb": None,
     "notes": "21 GB body + 4 GB DFlash2 draft plus KV; scripts validate the draft before serving."},
    ["./click_run_dflash2.sh (or dspark / eagle variants)",
     "Scripts download and validate checkpoints and drafts automatically"],
    ms_from(6, drop={("decode_agg", 22663)},
            method="r0b0bench ladders in the repo, medians over repeated runs"),
    ["The 22,663 tok/s figure is server-side prefill throughput on a ~22.8K-token "
     "prompt, mislabelled as decode aggregate in the source; excluded rather than "
     "quoted as a decode number.",
     "Quality canaries are think-off by default in his harness (GSM8K 0.865 vs 0.970 "
     "think-on): compare tiers, not absolutes, against other cards."],
    [{"url": e6["repo"], "kind": "repo", "note": "click-run scripts and benches"},
     {"url": "https://huggingface.co/r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121", "kind": "model",
      "note": "weights"}])

e7 = G[7]
write_setup(
    "qwen3-30b-a3b-vllm-mlx-server-mac",
    "Qwen3-30B-A3B 4-bit on vllm-mlx: continuous batching on Apple Silicon",
    "A vLLM-style server on native MLX: 127.7 tok/s single-stream decode on an M4 "
    "Max 128 GB, with continuous batching and warm-prompt preloading.",
    "qwen3-0-30b-a3b",
    {"checkpoint": "mlx-community/Qwen3-30B-A3B-4bit", "publisher": "mlx-community",
     "quant": "mlx-4", "quant_detail": "4-bit MLX served by the vllm-mlx continuous-batching server",
     "format": "mlx", "size_gb": None,
     "url": "https://huggingface.co/mlx-community/Qwen3-30B-A3B-4bit"},
    {"id": "mlx-lm", "requires_fork": True,
     "config": "vllm-mlx server: continuous batching, --moe-top-k expert reduction, --warm-prompts preloading"},
    ["mac-128gb"],
    {"memory_gb": 18, "disk_gb": 18, "min_vram_gb": None,
     "notes": "18 GB footprint while decoding on the M4 Max fixture."},
    ["Install vllm-mlx from the repo", "Serve the 4-bit MLX model",
     "Optionally set --moe-top-k and --warm-prompts for the quoted gains"],
    ms_from(7, drop={("decode_chat", 417.9), ("bench_other", 16), ("bench_other", 2.25)},
            method="vllm-mlx benchmark fixture, greedy single stream"),
    ["The 417.9 tok/s row is Qwen3-0.6B, a different model used as a harness sanity "
     "check; not a number for this card.",
     "The --moe-top-k gain (up to 16%) and --warm-prompts TTFT factor (2.25x) are "
     "configuration levers, recorded as caveats rather than measurements."],
    [{"url": e7["repo"], "kind": "repo", "note": "the vllm-mlx server and benchmarks"},
     {"url": "https://huggingface.co/mlx-community/Qwen3-30B-A3B-4bit", "kind": "model",
      "note": "weights"}])

e9 = G[9]
write_setup(
    "qwen35-122b-a10b-entrpi-dflash-vllm-spark",
    "Qwen3.5-122B-A10B + DFlash block-diffusion spec-dec on one Spark",
    "The 122B lane that applies block-diffusion drafting to agent workloads: 81 "
    "tok/s median on real tool-call turns, accept length ~5.4 on code.",
    "qwen3-5-122b-a10b",
    {"checkpoint": "Intel/Qwen3.5-122B-A10B-int4-AutoRound", "publisher": "intel",
     "quant": "int4-hybrid", "quant_detail": "AutoRound INT4 hybrid served with a DFlash block-diffusion draft",
     "format": "safetensors", "size_gb": None,
     "url": "https://huggingface.co/Intel/Qwen3.5-122B-A10B-int4-AutoRound"},
    {"id": "vllm", "spec_decode": "dflash2", "requires_fork": True,
     "config": "one-shot curl|bash installer, prebuilt sm121 vLLM 0.23 image, DFlash draft for the 122B"},
    ["dgx-spark"],
    {"memory_gb": 112, "disk_gb": 75, "min_vram_gb": None,
     "notes": "40 GiB image + 67 GiB hybrid checkpoint; 16 GB unified free at READY on the dense profile."},
    ["Run the repo's one-shot installer", "Choose the DFlash profile for agent workloads",
     "--load-format fastsafetensors cuts time-to-READY to ~3 min versus ~12"],
    ms_from(9, drop={("memory_gb", 119)},
            method="repo harness: real agent tool-call turns regenerated, per-workload ladders"),
    ["The 119 GB figure is the box's usable unified memory, not this setup's "
     "footprint; kept out of the measurements.",
     "DFlash on the 122B is a fork-path feature: stock vLLM will not reproduce it, "
     "so reproducibility depends on the prebuilt image."],
    [{"url": e9["repo"], "kind": "repo", "note": "installer and workload benches"},
     {"url": "https://huggingface.co/Intel/Qwen3.5-122B-A10B-int4-AutoRound", "kind": "model",
      "note": "weights"}])

e10 = G[10]
write_setup(
    "qwen35-122b-a10b-sojufx-nvfp4-dflash-native-vllm-spark",
    "Qwen3.5-122B-A10B NVFP4 + DFlash on native vLLM 0.26 (no Docker), Spark",
    "The production-serve recipe: native vLLM from a venv with CUTE_DSL_ARCH=sm_121a, "
    "36 tok/s single stream and 34.3 aggregate at agent-shaped concurrency 2.",
    "qwen3-5-122b-a10b",
    {"checkpoint": "RedHatAI/Qwen3.5-122B-A10B-NVFP4", "publisher": "redhatai",
     "quant": "nvfp4", "quant_detail": "NVFP4 with DFlash draft, native vLLM 0.26.0 from a venv",
     "format": "safetensors", "size_gb": None,
     "url": "https://huggingface.co/RedHatAI/Qwen3.5-122B-A10B-NVFP4"},
    {"id": "vllm", "spec_decode": "dflash2", "requires_fork": False,
     "config": "native vLLM 0.26.0 in a venv, CUTE_DSL_ARCH=sm_121a, PYTORCH_CUDA alloc tuning, no Docker"},
    ["dgx-spark"],
    {"memory_gb": 102, "disk_gb": 70, "min_vram_gb": None,
     "notes": "102 GB unified used post-start, ~18 GB left; 17.83 GB available KV at the stable config."},
    ["Create the venv and install native vLLM 0.26.0 per the recipe",
     "Export CUTE_DSL_ARCH=sm_121a before serving",
     "Launch the NVFP4 checkpoint with the DFlash draft config from the recipe"],
    ms_from(10, method="fixed 256-token single-stream benchmark and agent-shaped concurrency runs"),
    ["Deliberately Docker-free: the recipe's point is that the sm_121a CUTLASS path "
     "works from a venv, which changes what 'native' FP4 performance looks like.",
     "Contrast with the RedHatAI NVFP4 row measured at 16.6 tok/s on stock vLLM: "
     "same weights, different kernel path, 2x apart."],
    [{"url": e10["repo"], "kind": "repo", "note": "the serve recipe and benches"},
     {"url": "https://huggingface.co/RedHatAI/Qwen3.5-122B-A10B-NVFP4", "kind": "model",
      "note": "weights"}])

e11 = G[11]
write_setup(
    "qwen38-flash-next-hudsonwa-omlx-8slot-mac",
    "Qwen3.8-Flash-Next on oMLX: 8 concurrent 252K slots on a 128 GB Mac",
    "The Mac answer to the 180B MoE: oMLX pages the PLE table through an SSD tier "
    "and holds eight ~252K orchestrator slots, 60.9 tok/s solo decode with MTP on.",
    "qwen3-8-flash-next",
    {"checkpoint": "RadixArk/Qwen3.8-Flash-Next-NVFP4", "publisher": "radixark",
     "quant": "mlx-4", "quant_detail": "NVFP4 weights converted to oMLX 'flash oQ4e' with SSD-paged PLE tables",
     "format": "mlx", "size_gb": 136,
     "url": "https://huggingface.co/RadixArk/Qwen3.8-Flash-Next-NVFP4"},
    {"id": "mlx-lm", "requires_fork": True,
     "config": "oMLX 0.6.4 single process: SSD tier for PLE tables, self-managed prefix promotion, MTP spec-dec on"},
    ["mac-128gb"],
    {"memory_gb": 102, "disk_gb": 140, "min_vram_gb": None,
     "notes": "69 GB booted idle; 102 GB peak during dual-252K cold fill; ~9.25 GB KV per 252K slot."},
    ["Follow the oMLX recipe in the repo", "Keep the PLE tables on fast SSD; they page in and out",
     "Enable MTP speculative decode for the quoted solo decode"],
    ms_from(11, method="oMLX recipe runs: dual-252K cold prefill walls, solo decode with MTP, prefix re-promotion"),
    ["This is oMLX, not stock mlx-lm: the runtime carries the qwen4_exp/PLE paging "
     "that stock MLX lacks, so the recipe is runtime-specific.",
     "Cold-fill walls (483.6 s for dual ~252K) are the price of the SSD tier; warm "
     "re-promotion at 8.7 s is the number that makes the lane usable."],
    [{"url": e11["repo"], "kind": "repo", "note": "the oMLX recipe and measured walls"},
     {"url": "https://huggingface.co/RadixArk/Qwen3.8-Flash-Next-NVFP4", "kind": "model",
      "note": "source weights"}])

e12 = G[12]
write_setup(
    "qwen38-flash-next-pipenetwork-mlx-streaming-quant-mac",
    "Qwen3.8-Flash-Next on PipeNetwork's MLX runtime with streaming quantization",
    "The only MLX path that carries the Flash-Next architecture at all, with the "
    "quantization economics measured: mixed 4/8-bit costs +1.3% NLL versus +20.6% "
    "for uniform 4-bit.",
    "qwen3-8-flash-next",
    {"checkpoint": "RadixArk/Qwen3.8-Flash-Next-NVFP4", "publisher": "radixark",
     "quant": "mixed", "quant_detail": "mixed 4/8-bit MLX build (106.2 GB), the repo's recommended one",
     "format": "mlx", "size_gb": 136,
     "url": "https://huggingface.co/RadixArk/Qwen3.8-Flash-Next-NVFP4"},
    {"id": "mlx-lm", "requires_fork": True,
     "config": "PipeNetwork runtime shipping qwen4_exp support + streaming quantization; mixed-4_8bit build recommended"},
    ["mac-128gb"],
    {"memory_gb": 110, "disk_gb": 107, "min_vram_gb": None,
     "notes": "Mixed build is 106.2 GB on disk; the 51B n-gram tables alone would be 102 GB unquantized."},
    ["Build the mixed-4_8bit quant with the repo's streaming quantizer",
     "Serve through the repo's MLX runtime (stock mlx-lm cannot load qwen4_exp)"],
    ms_from(12, drop={("quality_index", 1.3)},
            method="wikitext-2 perplexity of each build plus a coherent-generation check"),
    ["The +1.3% NLL penalty of the mixed build (versus +20.6% uniform 4-bit) is a "
     "ratio, not a perplexity; kept as a caveat so it is not mistaken for a score.",
     "Perplexity rows compare builds of the same weights: 4.4708 bf16, 4.4749 8-bit, "
     "4.5286 mixed, 5.3914 uniform 4-bit."],
    [{"url": e12["repo"], "kind": "repo", "note": "runtime, quantizer and perplexity tables"},
     {"url": "https://huggingface.co/RadixArk/Qwen3.8-Flash-Next-NVFP4", "kind": "model",
      "note": "source weights"}])

e13 = G[13]
write_setup(
    "qwen35-35b-a3b-petems-gguf-llamacpp-macbook-32-64",
    "Qwen3.5-35B-A3B Q4 on 32-64 GB MacBooks: the decision-tree runbook",
    "The small-Mac lane: a compatibility probe and RAM-detecting launcher put the "
    "35B MoE at an expected 15-25 tok/s on 32-64 GB Apple Silicon.",
    "qwen3-5-35b-a3b",
    {"checkpoint": "unsloth/Qwen3.5-35B-A3B-GGUF", "publisher": "unsloth",
     "quant": "gguf-q4", "quant_detail": "Q4_K_M chosen by the guide's RAM auto-detection",
     "format": "gguf", "size_gb": None, "file_match": "q4_k_m",
     "url": "https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF"},
    {"id": "llama-cpp", "config": "mainline llama.cpp Metal, guide's start-launcher picks ctx and threads by RAM"},
    ["mac-64gb"],
    {"memory_gb": 22, "disk_gb": 50, "min_vram_gb": None,
     "notes": "22 GB RAM for Q4_K_M on a 32 GB Mac, which is what makes it fit; ~30-50 GB disk."},
    ["Run the guide's check-compatibility.sh probe",
     "Use the RAM auto-detecting start-launcher",
     "Stay at Q4_K_M or below on 32 GB machines"],
    ms_from(13, drop={("decode_chat", 25), ("memory_gb", 45), ("bench_other", 72)},
            method="guide's expected-range figures, not a controlled bench"),
    ["These are expected ranges (15-25 tok/s), not measured benchmarks: the guide "
     "states them as planning numbers, so treat this card as a fit-check, not a "
     "performance claim.",
     "Qwen3-Coder-Next at Q4_K_M needs ~45 GB RAM and is out of reach on 32 GB "
     "Macs; the SWE-Bench 72% quote belongs to a 27B variant, not this model."],
    [{"url": e13["repo"], "kind": "repo", "note": "the runbook, probe and launcher"},
     {"url": "https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF", "kind": "model",
      "note": "weights"}])

# --------------------------------------------------------------- upgrades ---
def add_unique(d, new_ms):
    have = {(m["metric"], m["value"]) for m in d["measurements"]}
    for m in new_ms:
        if (m["metric"], m["value"]) not in have:
            d["measurements"].append(m)


p = os.path.join(SETUPS, "qwen38-flash-next-blazux-vllm-hybrid-spark.json")
d = json.load(open(p, encoding="utf-8"))
add_unique(d, ms_from(4, drop={("decode_agg", 2904)},
                      method="blazux's serve.sh benches: kernel-level decode, concurrency ladders, prefix-cache probes"))
for s in d["sources"]:
    if s["url"] == "https://github.com/blazux":
        s["url"] = G[4]["repo"]
        s["note"] = "the builder's pinned repo (located after the first seed)"
if not any(s["url"] == G[4]["repo"] for s in d["sources"]):
    d["sources"].append({"url": G[4]["repo"], "kind": "repo", "note": "the build and its benches"})
d["caveats"] = [c for c in d["caveats"]
                if "could not be pinned" not in c and "beyond the GitHub account" not in c]
d["caveats"].append(
    "The 2,904 tok/s figure in the repo is prefill throughput at a 32K prompt with "
    "the deterministic top-k kernel, not decode; excluded from the measurements.")
d["caveats"].append(
    "DET_TOPK=1 deterministic top-k is what makes his kernel-level numbers "
    "reproducible; without it GB10 top-k is non-deterministic run to run.")
d["updated"] = UPDATED
json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(p, "a", encoding="utf-8").write("\n")
print("upgraded qwen38-flash-next-blazux-vllm-hybrid-spark")

p = os.path.join(SETUPS, "qwen35-122b-a10b-albond-int4-vllm-spark.json")
d = json.load(open(p, encoding="utf-8"))
add_unique(d, ms_from(8, drop={("decode_chat", 112), ("decode_chat", 28.3),
                               ("decode_chat", 38.4), ("decode_chat", 16.6),
                               ("memory_gb", 128)},
                      method="Albond's bench_qwen35 harness, v2.4 cross-prompt means"))
for cav in (
    "The same optimization stack on Qwen3.5-35B-A3B reaches 112 tok/s on this box; "
    "different model, kept as context rather than a measurement here.",
    "TurboQuant 3.5-bit KV buys ~4x KV capacity for -22% speed (39 tok/s aggregate): "
    "a capacity lever, recorded as a caveat.",
):
    if cav not in d["caveats"]:
        d["caveats"].append(cav)
d["updated"] = UPDATED
json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(p, "a", encoding="utf-8").write("\n")
print("upgraded qwen35-122b-a10b-albond-int4-vllm-spark")
