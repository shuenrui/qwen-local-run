# Installing recipes in the Qwen Local-Run Directory

**Research snapshot: 2026-10-07.** Upstream repositories and runtime support
change quickly. Before installing, reopen the linked recipe and its primary
source; this guide records what was verified in this audit, not a promise that
an upstream command still works today.

## Give an agent the machine facts first

Ask the person for these details before selecting a recipe:

- Operating system and version; CPU architecture (`arm64`/`aarch64` or
  `x86_64`).
- Exact GPU(s), VRAM per GPU, unified/system memory, and available disk space.
- Desired model, context length, number of simultaneous users, and whether an
  OpenAI-compatible local API is needed.
- Whether they want a desktop app or a command-line/server install.

Do not ask them to paste credentials, access tokens, or private configuration.
Do not treat a device family name as proof that the exact machine is compatible.

## Choose and install safely

1. Filter the **Models** or **My Hardware** views for the exact model and
   hardware. If the exact machine is not listed, explain the gap instead of
   claiming it fits. The directory records compatibility evidence; it does not
   guarantee performance or fit for every context length.
2. Open the recipe. Match the checkpoint, quantization, engine, runtime/fork,
   and hardware to the setup. Read `requirements`, `run.steps`, `caveats`, and
   the source links together. A command copied from another quant or engine is
   not a substitute.
3. Check disk for both weights and runtime/container/build files. The model
   file size alone is not the full installation requirement. For long context,
   reserve additional memory for the KV cache.
4. Follow only commands the recipe or its primary upstream source actually
   documents. Replace explicit placeholders such as `/path/to/...` with the
   user's real path. Never guess tensor parallelism, GPU split, quant, model
   tag, runtime version, or a missing installer command.
5. Before a command downloads large weights, builds a runtime, uses `sudo`, or
   installs a persistent service, state what it will change and get the user's
   go-ahead. In particular, inspect install scripts before running them.
6. Start the documented server and use its documented health or smoke test.
   Where the service exposes the OpenAI API, verify `/v1/models` and make one
   small local request. Report the actual command, output, host, runtime
   version, context, and any error; do not convert a reported benchmark into a
   local measurement.

## Results of the 40-recipe audit

Fourteen recipes now have at least one source-backed copyable command in their
recipe record. The command is a starting point, not a one-click installer:
check each recipe's prerequisites and notes first.

| Recipe | What the record now documents |
|---|---|
| [`qwen38-27b-unsloth-gguf-llamacpp`](data/setups/qwen38-27b-unsloth-gguf-llamacpp.json) | Unsloth GGUF through llama.cpp; current-version/Flash Attention caveat. |
| [`qwen38-27b-mlx-community-4bit-mac`](data/setups/qwen38-27b-mlx-community-4bit-mac.json) | Apple Silicon MLX server install and launch. |
| [`qwen38-27b-r0b0tlab-nvfp4-mtp-sm121-sglang`](data/setups/qwen38-27b-r0b0tlab-nvfp4-mtp-sm121-sglang.json) | GB10/Docker setup script and prerequisites. |
| [`qwen38-flash-next-blazux-vllm-hybrid-spark`](data/setups/qwen38-flash-next-blazux-vllm-hybrid-spark.json) | DGX Spark doctor, setup, and serve flow. |
| [`qwen38-flash-next-azampatti-sglang-spark`](data/setups/qwen38-flash-next-azampatti-sglang-spark.json) | Single-Spark download, install, and launch flow. |
| [`qwen38-27b-hasso-nvfp4-dflash2-sglang-spark`](data/setups/qwen38-27b-hasso-nvfp4-dflash2-sglang-spark.json) | GB10 installer and benchmark; notes that installer adds a systemd service. |
| [`qwen38-flash-next-hasso-nvfp4-mtp-sglang-spark`](data/setups/qwen38-flash-next-hasso-nvfp4-mtp-sglang-spark.json) | Flash model choice for the GB10 installer; disk and systemd notes. |
| [`qwen35-122b-a10b-entrpi-dflash-vllm-spark`](data/setups/qwen35-122b-a10b-entrpi-dflash-vllm-spark.json) | DGX Spark Docker installer, disk requirements, API smoke test. |
| [`qwen3-30b-a3b-vllm-mlx-server-mac`](data/setups/qwen3-30b-a3b-vllm-mlx-server-mac.json) | Pinned `vllm-mlx` install and Apple Silicon server command. |
| [`qwen35-35b-a3b-bartowski-gguf-llamacpp`](data/setups/qwen35-35b-a3b-bartowski-gguf-llamacpp.json) | Bartowski GGUF launch through llama.cpp. |
| [`qwen36-27b-unsloth-mtp-gguf-llamacpp`](data/setups/qwen36-27b-unsloth-mtp-gguf-llamacpp.json) | llama.cpp MTP launch flags and single-slot limitation. |
| [`qwen35-35b-a3b-petems-gguf-llamacpp-macbook-32-64`](data/setups/qwen35-35b-a3b-petems-gguf-llamacpp-macbook-32-64.json) | Apple Silicon compatibility check, Homebrew runtime, launcher. |
| [`qwen36-27b-unsloth-gguf-llamacpp-4090-samevocab`](data/setups/qwen36-27b-unsloth-gguf-llamacpp-4090-samevocab.json) | Linux/WSL RTX 4090 build and recipe launch; requires two local GGUF files and a configured model directory. |
| [`qwen35-122b-a10b-albond-int4-vllm-spark`](data/setups/qwen35-122b-a10b-albond-int4-vllm-spark.json) | DGX Spark vLLM installer, prerequisite checks, optional launch. |

The other 26 records still need upstream-specific review before an agent should
present them as installation instructions. “Manual” means a GUI or upstream
procedure needs to be followed; “incomplete/conflict” means the evidence does
not support a safe, exact install command for the setup as currently described.

| Recipe | Audit finding |
|---|---|
| `qwen38-flash-next-radixark-nvfp4-sglang-pennyroyal-rtx-pro-6000` | Follow Pennyroyal's current AI-agent guide and choose the model-specific runtime profile; the recipe does not yet pin a complete local install path. |
| `qwen36-35b-a3b-quanttrio-awq-vllm` | The model card's example uses tensor parallel 8; that does not establish a valid single-24-GB-card command. Do not change it to TP=1 by guess. |
| `qwen36-27b-fp8-vllm-mtp3-spark` | Benchmark evidence describes a setup, but the audit did not establish a pinned, reproducible installer/launch sequence for this exact FP8 plus MTP configuration. |
| `qwen38-flash-next-atomicchat-gguf-llamacpp-mac64` | GUI path. Select the recipe's special AD-IQ4 artifact and follow Atomic Chat's current model-import instructions; generic GGUF flags may omit its PLE setup. |
| `qwen36-27b-nvidia-nvfp4-sglang` | NVIDIA's exact published serve example is for vLLM, while this record specifies SGLang. Resolve the engine mismatch before instructing installation. |
| `qwen38-flash-next-strix-halo-llamacpp-mtp` | Upstream instructions have moved to Vulkan/Q5K and warn against the older ROCm path; the catalog setup is stale relative to that change. Reconcile quant and backend first. |
| `qwen35-397b-a17b-szibis-mlx-flash-ssd-mac64` | Upstream mlx-flash supports SSD streaming, but model selection and the exact 397B launch flow need to be made explicit in the recipe. |
| `qwen38-flash-next-unsloth-ud-q2kxl-ollama-vulkan-strix-halo` | The cited report describes a third-party Windows/Vulkan run, while current public Ollama model support found in the audit was Apple/MLX-oriented. Treat as a reported experiment, not a general install recipe. |
| `qwen35-122b-a10b-unsloth-gguf-q4-llamacpp-multigpu` | No exact multi-GPU tensor split was sourced. Do not invent a split based on total VRAM. |
| `qwen36-35b-a3b-mlx-flash-ssd-streaming-mac` | Upstream mlx-flash exists, but this record needs the exact model selection and SSD-streaming invocation. |
| `qwen38-flash-next-hudsonwa-omlx-8slot-mac` | Upstream bootstrap does not install oMLX or download weights; it requires a specific oMLX version and manual checkpoint setup. |
| `qwen35-122b-a10b-qwen-gptq-int4-vllm` | Official model-card example uses tensor parallel 4; it does not establish a valid single-Spark command. Do not silently reduce TP. |
| `qwen38-27b-unsloth-gguf-lm-studio` | GUI path. Install LM Studio from its official distribution, then locate the exact Unsloth Q4_K_M model and follow the app's import/load steps. |
| `qwen38-flash-next-orcarouter-gguf-uncensored` | Access-gated weights and a custom Rust engine fork are involved; exact fork/revision and access steps are not pinned. |
| `qwen35-35b-a3b-mxfp4-llamacpp-spark-implied` | Source thread mixes measured user reports with proposed/generated configurations; it does not establish a reproducible install for this row. |
| `qwen35-35b-a3b-vllm-nightly-mtp2-spark-c100` | Source includes proposed configurations rather than an exact pinned nightly/runtime build and install sequence. |
| `qwen35-122b-a10b-redhatai-nvfp4-vllm-spark` | Model-card serve command exists, but Spark-specific runtime/kernel prerequisites remain unverified. Do not claim the model card alone is a tested Spark setup. |
| `qwen35-35b-a3b-bf16-mxfp4-marlin-vllm-spark` | Thread evidence is not a complete pinned runtime build and install procedure; establish compatible kernel/runtime versions first. |
| `qwen38-27b-jonathancoletti-uncensored-q6k-lmstudio-mtp-rtx-5090` | GUI path. The forum documents model and MTP settings, not a reproducible command-line installer. |
| `qwen35-122b-a10b-unsloth-gguf-q3-llamacpp-multigpu-256k` | No exact multi-GPU split/configuration is sourced; long-context fit cannot be inferred from aggregate VRAM. |
| `qwen38-flash-next-pipenetwork-mlx-streaming-quant-mac` | The referenced experimental `qwen4_exp` support depends on unreleased/unfinished MLX changes with known issues. Wait for a supported release or pin a verified commit. |
| `qwen38-27b-mlx-8bit-dflash2-atomic-chat-mac256` | GUI path. Install Atomic Chat and follow its exact MLX/DFlash model instructions; no verified model-specific copyable command was found. |
| `qwen38-27b-unsloth-gguf-dflash2-llamacpp-4090` | DFlash support depends on a custom llama.cpp change; do not imply stock llama.cpp is sufficient. Pin a verified build before writing install steps. |
| `qwen35-122b-a10b-sojufx-nvfp4-dflash-native-vllm-spark` | Native vLLM 0.26 path is reported, but custom SM121/DFlash build details and prerequisites need to be pinned before this is a safe install guide. |
| `qwen38-27b-vllm-mtp-community` | This entry is a collection of community configurations, not one reproducible recipe. Pick and source a single configuration before adding commands. |
| `qwen35-35b-a3b-intel-int4-vllm-spark-concurrency` | The source thread does not establish a complete pinned installation for the concurrency sweep. Treat figures as reported evidence, not an install procedure. |

## Keeping the guide useful

When an upstream source changes, update the recipe record first: pin the exact
runtime/revision, prerequisites, commands, and expected local check. Then
reclassify it here. Keep reported results distinct from locally verified
installation results. The source links in each recipe are the authority for
that setup; this document is an index and operating guide, not a replacement
for them.
