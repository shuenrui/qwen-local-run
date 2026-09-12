---
base_model: Qwen/Qwen3.8-27B
base_model_relation: quantized
quantized_by: AtomicChat
pipeline_tag: image-text-to-text
library_name: gguf
tags:
- gguf
- llama.cpp
- qwen3.8
- qwen
- imatrix
- quantized
- conversational
- atomic-chat
---

# How to Run Qwen3.8 27B Locally
<p style="margin-top: 0; margin-bottom: 0;">
  <em>Built from Qwen's original weights with our own importance matrix. The <a href="https://huggingface.co/datasets/AtomicChat/calib-corpora">calibration corpora</a> behind our builds are public.</em>
</p>
<div style="display: flex; gap: 8px; align-items: center; margin-top: 10px; margin-bottom: 10px;">
  <a href="https://atomic.chat/?utm_source=huggingface&utm_medium=referral&utm_campaign=hf_qwen3_8_27b&utm_content=btn_atomic"><img src="https://huggingface.co/AtomicChat/Qwen3.8-27B-GGUF/resolve/main/btn_atomic.png" width="162" alt="Atomic Chat"></a>
  <a href="https://discord.gg/8wGSsvmg4V"><img src="https://huggingface.co/AtomicChat/Qwen3.8-27B-GGUF/resolve/main/btn_discord.png" width="119" alt="Discord"></a>
  <a href="https://github.com/AtomicBot-ai/Atomic-Chat"><img src="https://huggingface.co/AtomicChat/Qwen3.8-27B-GGUF/resolve/main/btn_github.png" width="115" alt="GitHub"></a>
</div>
<ul style="margin: 0 0 12px 0;">
  <li>Learn how to run Qwen3.8 27B locally - read <a href="https://atomic.chat/blog/guides/how-to-run-qwen-3-8-locally?utm_source=huggingface&utm_medium=referral&utm_campaign=hf_qwen3_8_27b&utm_content=bullet_guide">our guide</a>.</li>
  <li>You can now run Qwen3.8 in <a href="https://atomic.chat/?utm_source=huggingface&utm_medium=referral&utm_campaign=hf_qwen3_8_27b&utm_content=bullet_app">Atomic Chat</a> with toggles for thinking.</li>
  <li>See our quantization analysis below for measurements and instructions.</li>
</ul>
<hr style="margin: 0 0 16px 0;">


![image](https://cdn-uploads.huggingface.co/production/uploads/6a54dea4f19f5386700504da/dmMjNbYfWXrhVGAVeBroC.png)

Every quantization of this model we could find, ours and everyone else's,
measured against the original weights on the same held-out text. The dashed
line is the best file available at each size from anyone but us.


## Pick a file

Every number below is measured, not estimated. How we measured it is at the
bottom, and the raw logs are in
[the metrics repo](https://huggingface.co/datasets/AtomicChat/Qwen3.8-27B-GGUF-metrics)
so you can check any of it yourself.

`KL divergence` is how far the quantized model's predictions drift from the
original weights. Lower is better, and zero means identical. `top-1` is how
often it picks the same next word the original would have picked.

| File | Size | KL divergence | top-1 |
|---|---:|---:|---:|
| `Q8_0` | 28.9 GB | 0.00064 | 98.92% |
| `AD-Q6_K` | 25.0 GB | 0.00107 | 98.67% |
| `AD-Q6_K-Q5_K` | 23.1 GB | 0.00252 | 97.94% |
| `AD-Q5_K_M` | 20.2 GB | 0.00419 | 97.34% |
| `AD-Q5_K_M-Q4_K_M` | 18.6 GB | 0.00730 | 96.43% |
| `AD-Q4_K_M` | 17.1 GB | 0.01126 | 95.59% |
| `AD-IQ4_XS` | 16.5 GB | 0.01248 | 95.39% |
| `AD-IQ4_XS-IQ3_S` | 14.4 GB | 0.02660 | 93.15% |
| `AD-IQ3_S` | 13.8 GB | 0.03247 | 92.41% |
| `AD-IQ3_S-IQ3_XXS` | 13.0 GB | 0.04337 | 91.33% |
| `AD-IQ3_XXS` | 12.1 GB | 0.06972 | 89.13% |
| `AD-IQ2_S` | 11.1 GB | 0.09832 | 87.18% |
| `AD-IQ2_S-IQ2_XS` | 10.2 GB | 0.13807 | 84.77% |
| `AD-IQ2_XS` | 9.9 GB | 0.16170 | 83.48% |
| `AD-IQ2_XXS` | 9.0 GB | 0.25663 | 79.44% |
| `AD-IQ1_M` | 8.5 GB | 0.34212 | 76.34% |

`AD-` marks an **Atomic Dynamic** layout. The name says what the two largest
tensor groups got: `AD-<ffn_down>-<ffn_up>`, collapsed to one name when both
match. Nothing is named after a type it does not contain.

## Which one fits your card

The file has to fit, and so does the context. This model keeps 256 KB of
attention cache per token, which is 2 GB at 8k context and 8 GB at 32k. Budget
for both.

| Your card | File | Leaves room for |
|---|---|---|
| 12 GB | `AD-IQ2_S` | short context only, or move some layers to CPU |
| 16 GB | `AD-IQ3_S` | around 8k context |
| 24 GB | `AD-Q5_K_M-Q4_K_M` | around 16k context |
| 32 GB | `AD-Q6_K` | around 24k context |
| 48 GB and up | `Q8_0` | full context |

> [!TIP]
> If you are choosing between two neighbouring files, take the larger one. The
> steps between them cost one or two gigabytes and buy noticeably fewer wrong
> words, especially below 14 GB where the curve gets steep.

## Running it

```bash
llama-server -m Qwen3.8-27B-AD-Q4_K_M.gguf -ngl 99 -c 8192
```

Prompt format:

```
<|im_start|>system
{system}<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
<think>
```

The model ships a multi token prediction head. It is inside every file here
and needs no extra download:

```bash
llama-cli -m Qwen3.8-27B-AD-Q4_K_M.gguf --spec-type draft-mtp -ngl 99 -c 8192
```

## Speed

Measured on 2xRTX_5090 with `AD-Q4_K_M`, full offload:

| | prompt | generation |
|---|---:|---:|
| 8k context | 363 t/s | 77 t/s |
| 32k context | 5244 t/s | 72 t/s |

## Images and video

This model reads images, not only text. That needs one extra file, the vision
projector, which is separate from the quant and shared by all of them:

- `mmproj-Qwen3.8-27B-F16.gguf` for most people
- `mmproj-Qwen3.8-27B-BF16.gguf` if your setup prefers bfloat16

Download it once alongside whichever quant you picked:

```bash
llama-mtmd-cli \
  -m Qwen3.8-27B-AD-IQ4_XS.gguf \
  --mmproj mmproj-Qwen3.8-27B-F16.gguf \
  --image your-photo.jpg --image-min-tokens 1024 \
  -ngl 99 -c 8192 \
  -p "What is in this image?"
```

`--image-min-tokens 1024` is not optional in practice. llama.cpp warns that
this family needs at least that many image tokens or anything positional gets
unreliable.

### How well it survives quantization

`demo.jpg` in this repo is a piece of handwritten calligraphy in a gothic
hand. It is a harder test than a photograph: a misread word is obvious, so you
can score the answer yourself instead of taking our word for it.


![image](https://cdn-uploads.huggingface.co/production/uploads/6a54dea4f19f5386700504da/oDorOfzpnVmi3x9RmRL6t.png)

The text on it reads:

> Peace of mind comes to me through making things with my hands. An added
> bonus comes if my efforts inspire others to try the creative process.

Every file from `AD-IQ3_S` upward transcribed that exactly, line breaks
included. Vision holds up better under quantization than the language half
does, which surprised us. Full transcripts for every file are in the metrics
repo under `logs/vision-*.log`.

![image_2026-08-16_22-01-36](https://cdn-uploads.huggingface.co/production/uploads/6a54dea4f19f5386700504da/GXcFpzczhMDtvgy8dQyne.png)

Try it yourself on the same image:

```bash
llama-mtmd-cli -m <your-quant>.gguf --mmproj mmproj-Qwen3.8-27B-F16.gguf \
  --image demo.jpg --image-min-tokens 1024 -ngl 99 -c 8192 \
  -p "Transcribe the text in this image exactly, then describe the decoration."
```

> [!NOTE]
> While an image is being encoded llama.cpp prints lines about
> `find_slot: non-consecutive token position` and about unused `blk.64`
> tensors. Both are expected. The first is how this family numbers image
> patches, using a multi dimensional rope rather than one running index. The
> second is the multi token prediction head, which a plain forward pass does
> not run.

## How these compare to other builds

Numbers taken against different references cannot be put in the same table, so
we did not copy anyone's published figures. We downloaded their files and
measured them ourselves, against the same original weights, on the same
held-out text. Their logs are in the metrics repo next to ours.

At sizes where the comparison is direct:

| Size | Ours | Best other build at that size |
|---|---|---|
| 20.2 GB | `AD-Q5_K_M` 0.00419 | unsloth `UD-Q5_K_XL` 0.00437 |
| 25.0 vs 25.9 GB | `AD-Q6_K` 0.00107 | unsloth `UD-Q6_K_XL` 0.00110 at 0.9 GB more |
| 16.5 vs 16.1 GB | `AD-IQ4_XS` 0.01248 | unsloth `Q4_K_S` 0.01707 |
| 12.1 vs 11.9 GB | `AD-IQ3_XXS` 0.06972 | unsloth `UD-IQ3_XXS` 0.07330 |

> [!NOTE]
> One honest exception. At 17.9 GB unsloth's `UD-Q4_K_XL` reaches 0.00955,
> which is better than our 17.1 GB file and close to our 18.6 GB one. Around
> 18 GB their build and ours are within a few percent of each other. We are
> ahead across most of the range, not all of it.

One thing worth seeing on its own. Three publishers ship a file called
`Q4_K_M`, and they are not the same file:

| Publisher | Size | KL divergence |
|---|---:|---:|
| lmstudio-community | 16.8 GB | 0.02094 |
| ggml-org | 19.0 GB | 0.01470 |
| ours, `AD-Q4_K_M` | 17.1 GB | 0.01126 |

Same name, two gigabytes apart, and nearly a factor of two in accuracy. A
quant name tells you which recipe was requested, not what you are getting.

## What we found while building these

### Where the bits go matters more than how many there are

We built ten versions of the same 17 to 19 GB file, changing only which
tensors got the extra bits, and measured each one against the original
weights.

| Layout | Size | KL divergence |
|---|---:|---:|
| every layer treated the same | 16.8 GB | 0.01580 |
| 4 layers lifted | 17.1 GB | 0.01449 |
| more bits on `ffn_down` everywhere | 17.8 GB | 0.01189 |
| more bits on attention | 18.2 GB | 0.01010 |
| 16 layers lifted, first and last | 17.8 GB | 0.00981 |
| 32 layers lifted instead | 18.4 GB | 0.00826 |
| 16 lifted, plus the attention gate | 18.4 GB | 0.00821 |
| 16 lifted, plus a richer output head | 18.8 GB | 0.00800 |
| 24 layers lifted | 18.6 GB | 0.00743 |
| **24 lifted, plus attention gate and state output** | **18.6 GB** | **0.00730** |

Half the divergence disappears at the same file size, purely from moving bits
around. Every file in the ladder above uses the last layout.

### The ends of the network are worth more than the middle

Lifting the first four and last twelve layers helped more than anything else
we tried. Widening that band to 32 layers did not help further, and spending
the same bits on the output head helped less. The importance matrix agrees:
the highest activation energy in the whole model sits on layers 52 to 62, with
a second peak on layer 0.

### This model is a hybrid, and two small groups carry a lot

Alongside ordinary attention, Qwen3.8 has an attention gate and a state output
path. They are 5.5% of the weights each. Giving both one extra step of
precision cost 0.16 GB and removed 11% of the remaining divergence. That was
the single best trade we found.

### The embedding table is cheaper than it looks

The token embedding table and the output head weigh the same, 4.7% each, and
behave nothing alike. The head decides the next word directly and has to stay
precise. The embedding table is a lookup whose error stays inside one token,
so it can be cut hard. Paying for the head out of the embedding table is a net
gain at every size we tested.

### `Q8_0` is not lossless

It is very close, but it is not the original: 0.00064 divergence and 98.92%
top-1 agreement. We say so because our whole table is measured against the
real BF16 weights rather than against `Q8_0`, and that changes every number in
it. Anyone measuring against a `Q8_0` reference will get smaller numbers than
these for the same files.

### The prediction head collects no calibration data

The multi token prediction head is never executed during a normal forward
pass, so the importance matrix has nothing to say about it at any corpus size.
Quantize it low and llama.cpp refuses partway through rather than guess. It is
pinned to `q5_k` in every file here.

### Every tensor row divides by 256

Worth checking before you plan a ladder. K and I quants store weights in
superblocks of 256, and a model whose rows do not divide by that number
silently falls back to a coarser type while keeping the name you asked for. On
this model everything divides cleanly, so the whole range from `IQ1_M` upward
is genuinely available. That is not true of every recent release.

## The calibration data

Our importance matrix comes from a corpus we built for this model and
published: [AtomicChat/calib-corpora](https://huggingface.co/datasets/AtomicChat/calib-corpora),
recipe `qwen3.8-27b`. It is 4,967,044 tokens across 3,004 documents:

| Part | Share |
|---|---:|
| agentic and tool use | 24.7% |
| code | 17.8% |
| reasoning | 14.8% |
| multilingual | 13.8% |
| long context | 11.9% |
| vocabulary sweep | 9.9% |
| structured data | 4.1% |
| graphics | 3.0% |

Two details that matter more than the mix.

Every conversation is rendered through **this model's own chat template**, so
`<|im_start|>`, `<think>`, `<tool_call>` and `<tool_response>` appear as the
single tokens the model actually sees. Text rendered for another model is
excluded from the build rather than reused.

The vocabulary sweep is regenerated for this tokenizer. It covers 246,919 of
the 247,133 vocabulary entries that can stand alone, at about two tokens per
entry. A sweep built for a different model covers a different vocabulary and
does nothing here.

> [!IMPORTANT]
> If you build your own importance matrix from this corpus, pass
> `--parse-special` to `llama-imatrix`. Without it the chat markup is read as
> ordinary punctuation, and the agentic and reasoning parts of the corpus
> calibrate on text the model never sees.

## How we measured

Reference: the original BF16 weights, converted to GGUF and run unquantized.
Perplexity on the held-out set is 4.5219 plus or minus 0.0238.

Held-out text: `eval_neutral` from our calibration dataset, never used for
calibration. 87 chunks at 4096 context.

Metric: per-token KL divergence of each file's predictions against the
reference, plus top-1 agreement.

Hardware: 4x RTX 5090, CUDA 13.0. Two cards would have been enough: the BF16
file is 51 GB and the logit buffer adds about 2 GB. I used only 2/4 cards for
all the measurements though, just the servers had 4, so i write about it
openly to avoid any confusion.

The raw logits of the reference are published in the metrics repo, split into
parts because of the file size limit. With them you can measure your own build
against exactly the same point we did:

```bash
cat base-neutral.kld.*.part > base-neutral.kld

llama-perplexity -m your-quant.gguf -f eval_neutral.txt \
  --kl-divergence-base base-neutral.kld --kl-divergence -c 4096 -ngl 99
```

## Reproducing a file

The importance matrix was collected on the BF16 weights rather than on a
quantized copy, split across seven workers and merged. Splitting by chunk
range gives the same result as one long run, because the statistic is a sum:

```bash
llama-imatrix -m Qwen3.8-27B-bf16.gguf -f calib_train.txt -o shard-0.gguf \
  -ngl 99 -c 512 -b 4096 -ub 4096 --parse-special --from-chunk 0 --chunks 1400

llama-imatrix -m Qwen3.8-27B-bf16.gguf --in-file shard-0.gguf,shard-1.gguf,... \
  -o imatrix.gguf
```

Then, for `AD-Q4_K_M`:

```bash
llama-quantize --imatrix imatrix.gguf \
  --tensor-type 'blk\.64\.=q5_k' \
  --tensor-type 'blk\.([0-3]|5[2-9]|6[0-3])\.ffn_.*=q5_k' \
  --tensor-type 'blk\.([4-9]|1[01])\.ffn_.*=q5_k' \
  --tensor-type ffn_down=q4_k --tensor-type ffn_gate=q4_k --tensor-type ffn_up=q4_k \
  --tensor-type attn_q=q4_k --tensor-type attn_gate=q5_k --tensor-type ssm_out=q5_k \
  --tensor-type output=q6_k --tensor-type token_embd=iq4_xs \
  Qwen3.8-27B-bf16.gguf Qwen3.8-27B-AD-Q4_K_M.gguf Q8_0
```

The rules for every other file are in its quantization log in the metrics
repo.

## Also in this repo

`demo.jpg` is the calligraphy used in the vision section, so anyone can run
the same test on the same image. Its source and licence are in
`demo-source.txt`.

The stock `Q4_K_M`, `Q5_K_M` and `Q6_K` mixes were built from the same
importance matrix and measured against the same reference, as a control for
the layout comparison above. Their measurements are in the metrics repo. The
files themselves are not kept here: at every size the `AD-` build of the same
weight is better, so there is no reason to download one.

## Model details

64 layers, hidden size 5120, feed-forward size 17408, vocabulary 248,320,
context 262,144, no sliding window. Hybrid attention with an added gate and a
state path. One multi token prediction head.

Needs a recent llama.cpp with `qwen35` architecture support. Built and tested with llama.cpp b10454.