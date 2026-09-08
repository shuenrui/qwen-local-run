#!/usr/bin/env python3
"""Build the Qwen local-run directory into one self-contained HTML file.

Stdlib only, no build step at runtime, no backend. Reads data/*.json,
validates it, and writes site/index.html with the dataset inlined so the
page works from file:// as well as over http.

Usage:
    python3 directory/build.py                 # validate + build
    python3 directory/build.py --skip-validate # build only
    python3 directory/build.py --out /tmp/x.html

Presentation contract (see docs/UX-REVIEW-2026-09-07.md):
  * A single-stream tok/s number always wins the headline. Aggregate-only
    results are explicitly labelled; otherwise aggregate throughput is a
    secondary line with its stated concurrency.
  * A fit verdict is only rendered once the reader has declared a machine.
    Without one, only the neutral requirement is shown.
  * Any string passed through esc() must use literal Unicode, never an HTML
    entity — esc() escapes the ampersand and the entity leaks to the page.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DEFAULT_OUT = os.path.join(HERE, "site", "index.html")


def load_dir(rel: str) -> list[dict]:
    d = os.path.join(DATA, rel)
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        with open(os.path.join(d, name), encoding="utf-8") as fh:
            out.append(json.load(fh))
    return out


def load_json(rel: str):
    with open(os.path.join(DATA, rel), encoding="utf-8") as fh:
        return json.load(fh)


def collect() -> dict:
    publishers = load_json("publishers.json")["publishers"]
    models = {m["id"]: m for m in load_dir("models")}
    hardware = {h["id"]: h for h in load_dir("hardware")}
    engines = {e["id"]: e for e in load_dir("engines")}
    setups = load_dir("setups")

    # Newest generation first, then biggest model, so the shelf reads top-down.
    def model_sort_key(m: dict):
        gen = str(m.get("generation") or "0")
        try:
            gen_num = float(gen)
        except ValueError:
            gen_num = 0.0
        return (-gen_num, -(m.get("architecture", {}).get("params_total_b") or 0))

    ordered_models = sorted(models.values(), key=model_sort_key)

    return {
        "generated": __import__("datetime").date.today().isoformat(),
        "publishers": publishers,
        "models": {m["id"]: m for m in ordered_models},
        "model_order": [m["id"] for m in ordered_models],
        "hardware": hardware,
        "engines": engines,
        "setups": setups,
        "counts": {
            "setups": len(setups),
            "models": len(models),
            "hardware": len(hardware),
            "engines": len(engines),
            "publishers": len(publishers),
            "measured": sum(1 for s in setups if s.get("provenance_tier") == "box"),
        },
    }


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Run Qwen on your own machine</title>
<meta name="description" content="Every community-tested way to run a Qwen model locally. Pick your machine, see what fits, how fast it really goes, and who measured it.">
<meta property="og:title" content="Run Qwen on your own machine">
<meta property="og:description" content="Runnable Qwen setups across DGX Spark, Macs and consumer GPUs; every number tagged box / forum / vendor with its source linked.">
<meta property="og:type" content="website">
<style>
:root{
  --bg:#fff; --fg:#16181d; --mut:#5b6472; --line:#e2e5ea; --soft:#f6f7f9;
  --box:#1b5e20; --boxbg:#e6f4e8; --forum:#8a4b00; --forumbg:#fdf0dc;
  --vendor:#0d47a1; --vendorbg:#e5eefb; --accent:#4338ca; --accentbg:#eef0ff;
  --bad:#8a1c1c; --badbg:#fbeaea; --warn:#7a5200; --warnbg:#fdf3d8;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0f1115; --fg:#e7e9ee; --mut:#98a1b0; --line:#262b34; --soft:#161a21;
  --box:#8ce0a0; --boxbg:#14291a; --forum:#f0b473; --forumbg:#2b1f10;
  --vendor:#8db8f5; --vendorbg:#12203a; --accent:#a9b4ff; --accentbg:#1b1f3d;
  --bad:#f0a0a0; --badbg:#2e1616; --warn:#f2d18a; --warnbg:#2a2010;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}
code,kbd,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.wrap{max-width:1280px;margin:0 auto;padding:0 1rem}

/* ---- header + machine picker ------------------------------------------- */
header.top{border-bottom:1px solid var(--line);padding:1.6rem 0 1.3rem;background:var(--soft)}
h1{margin:0;font-size:1.75rem;letter-spacing:-.025em}
.tag{margin:.4rem 0 0;color:var(--mut);max-width:68ch;font-size:1rem}

.picker{margin-top:1.15rem}
.picker h2{margin:0 0 .55rem;font-size:.98rem;letter-spacing:-.01em}
.mgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.5rem;max-width:900px}
.mopt{text-align:left;padding:.6rem .75rem;border:1px solid var(--line);border-radius:10px;
  background:var(--bg);cursor:pointer;font:inherit;color:var(--fg);line-height:1.35}
.mopt:hover{border-color:var(--accent);background:var(--accentbg)}
.mopt b{display:block;font-size:.92rem;font-weight:650}
.mopt span{display:block;font-size:.78rem;color:var(--mut);margin-top:.1rem}
.mskip{margin-top:.55rem;font-size:.83rem}
.mskip button{border:0;background:none;color:var(--accent);text-decoration:underline;padding:0;cursor:pointer;font:inherit}

.profile{display:flex;flex-wrap:wrap;gap:.55rem;align-items:center;font-size:.9rem}
.profile .who{font-weight:650}
.profile select{max-width:130px}
.profile button.link{border:0;background:none;color:var(--accent);text-decoration:underline;padding:0;cursor:pointer;font:inherit;font-size:.85rem}

/* ---- orientation -------------------------------------------------------- */
.how{border-bottom:1px solid var(--line);background:var(--bg);padding:1rem 0}
.how summary{cursor:pointer;font-weight:650;font-size:.95rem;list-style:none}
.how summary::-webkit-details-marker{display:none}
.gloss .words summary::before{content:"\25b8";display:inline-block;margin-right:.35rem}
.gloss .words[open] summary::before{content:"\25be"}
.how > summary::before{content:"\25be";display:inline-block;margin-right:.4rem;color:var(--mut)}
.how[open] > summary::before{content:"\25b4"}
.hsteps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin:.85rem 0 0}
.hstep{font-size:.86rem;color:var(--mut)}
.hstep b{display:block;color:var(--fg);font-size:.9rem;margin-bottom:.15rem}
.hstep i{font-style:normal;color:var(--accent);font-weight:650;margin-right:.3rem}
.gloss{margin-top:1rem;font-size:.84rem}
.gloss .words{margin-top:.5rem}
.gloss .words summary{cursor:pointer;font-weight:650;color:var(--accent);font-size:.83rem}
.gloss dl{display:grid;grid-template-columns:max-content 1fr;gap:.25rem .9rem;margin:.4rem 0 0}
.gloss dt{font-weight:650}
.gloss dd{margin:0;color:var(--mut)}
.depgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.15rem;margin:.8rem 0 1.1rem}
.depgroup{border-top:2px solid var(--fg);padding-top:.55rem}
.depgroup h3,.specguide h3{font-size:.86rem;margin:0 0 .2rem;letter-spacing:-.01em}
.depgroup .rule{color:var(--mut);margin:0 0 .55rem;line-height:1.4}
.depgroup dl{display:block;margin:0}
.depgroup dt{margin-top:.55rem}
.depgroup dd{margin:.08rem 0 0;line-height:1.45}
.depgroup .driver{display:block;color:var(--fg);font-size:.76rem;margin-top:.08rem}
.specguide{border-top:1px solid var(--line);padding-top:.8rem}
.specguide>p{color:var(--mut);margin:.15rem 0 .65rem;max-width:82ch}
.spectable{width:100%;border-collapse:collapse;font-size:.8rem}
.spectable th,.spectable td{text-align:left;vertical-align:top;padding:.38rem .5rem;border-bottom:1px solid var(--line)}
.spectable th{color:var(--mut);font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;font-weight:650}
.spectable td:first-child{font-weight:650;white-space:nowrap}
.device-notes{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:.85rem}
.device-note{background:var(--soft);border-radius:8px;padding:.65rem .75rem;line-height:1.45}
.device-note b{display:block;margin-bottom:.15rem}
.device-note a{font-size:.76rem}
@media (max-width:780px){.depgrid{grid-template-columns:1fr}.device-notes{grid-template-columns:1fr}}
@media (max-width:640px){.gloss>dl{grid-template-columns:1fr}.gloss>dl dt{margin-top:.35rem}.spectable td:first-child{white-space:normal}}

.pill{font-size:.68rem;font-weight:700;border-radius:4px;padding:.08rem .4rem;white-space:nowrap;letter-spacing:.02em}
.p-box{background:var(--boxbg);color:var(--box)}
.p-forum{background:var(--forumbg);color:var(--forum)}
.p-vendor{background:var(--vendorbg);color:var(--vendor)}
.p-none{background:var(--soft);color:var(--mut);border:1px solid var(--line)}

/* ---- glossary popover (fixed, clamped: must not create page overflow) --- */
.term{border-bottom:1px dotted currentColor;cursor:help}
#pop{position:fixed;z-index:60;max-width:min(320px,calc(100vw - 16px));
  background:var(--bg);color:var(--fg);border:1px solid var(--accent);border-radius:8px;
  padding:.55rem .7rem;font-size:.82rem;line-height:1.45;box-shadow:0 6px 24px rgba(0,0,0,.18)}

/* ---- controls ----------------------------------------------------------- */
.controls{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line);padding:.7rem 0}
.row-main,.row-adv{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}
.row-adv{margin-top:.5rem}
input[type=search]{flex:1 1 260px;min-width:180px;padding:.5rem .7rem;border:1px solid var(--line);
  border-radius:8px;background:var(--bg);color:var(--fg);font-size:.92rem}
input[type=search]:focus{outline:2px solid var(--accentbg);border-color:var(--accent)}
select{padding:.5rem .6rem;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font-size:.86rem;max-width:200px}
input[type=number]{padding:.4rem .5rem;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font-size:.86rem;width:5.5rem}
button{font:inherit;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--fg);
  border-radius:8px;padding:.45rem .8rem;font-size:.85rem}
button:hover{border-color:var(--accent)}
.hint{font-size:.8rem;color:var(--mut);margin-top:.5rem}
.hint button.link{border:0;background:none;color:var(--accent);text-decoration:underline;padding:0;cursor:pointer;font:inherit}
#more-filters{display:none}
@media (max-width:640px){
  #more-filters{display:inline-block}
  .row-adv{display:none}
  .row-adv.show{display:flex}
}

main{padding:1.2rem 0 3rem}

/* ---- recommendation ----------------------------------------------------- */
.rec{border:2px solid var(--accent);border-radius:12px;padding:1rem 1.1rem;margin-bottom:1.6rem;background:var(--accentbg)}
.rec h2{margin:0 0 .1rem;font-size:.72rem;text-transform:uppercase;letter-spacing:.09em;color:var(--accent)}
.rec .rtitle{margin:.25rem 0 .35rem;font-size:1.12rem;font-weight:650;letter-spacing:-.01em}
.rec .rwhy{margin:0 0 .6rem;font-size:.87rem;color:var(--mut)}
.rec .rwhy b{color:var(--fg);font-weight:600}
.rec pre.cmd{background:var(--bg)}
.rec .rlinks{margin-top:.6rem;font-size:.85rem}

/* ---- groups ------------------------------------------------------------- */
.group{margin-bottom:2rem}
.ghead{border-bottom:2px solid var(--fg);padding-bottom:.4rem;margin-bottom:.2rem;
  display:flex;flex-wrap:wrap;gap:.5rem;align-items:baseline;justify-content:space-between}
.ghead h2{margin:0;font-size:1.22rem;letter-spacing:-.01em}
.gmeta{font-size:.78rem;color:var(--mut)}
.gspecs{display:flex;flex-wrap:wrap;gap:.35rem;margin:.55rem 0 .9rem}
.spec{font-size:.74rem;border:1px solid var(--line);border-radius:6px;padding:.2rem .5rem;background:var(--soft)}
.spec b{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:.66rem;letter-spacing:.04em;margin-right:.3rem}
.gsum{font-size:.88rem;color:var(--mut);max-width:96ch;margin:0 0 .9rem}
@media (max-width:640px){.spec.license,.spec.released,.spec.sees{display:none}}

/* ---- card --------------------------------------------------------------- */
.card{border:1px solid var(--line);border-radius:10px;margin-bottom:.6rem;background:var(--bg);overflow:hidden}
.chead{display:flex;gap:1rem;align-items:flex-start;padding:.75rem .85rem;cursor:pointer}
.chead:hover{background:var(--soft)}
.cmain{flex:1 1 auto;min-width:0}
.verdict{display:inline-flex;align-items:center;gap:.3rem;font-size:.8rem;font-weight:650;
  border-radius:6px;padding:.16rem .5rem;margin-bottom:.35rem}
.v-good{background:var(--boxbg);color:var(--box)}
.v-tight{background:var(--warnbg);color:var(--warn)}
.v-no{background:var(--badbg);color:var(--bad)}
.v-unknown{background:var(--soft);color:var(--mut);border:1px solid var(--line);font-weight:600}
.ready{font-size:.72rem;color:var(--mut);margin-left:.4rem;white-space:nowrap}
.ctitle{font-weight:650;font-size:1rem;letter-spacing:-.01em;margin:0 0 .2rem}
.cnote{margin:0 0 .35rem;font-size:.87rem;color:var(--mut);max-width:78ch}
.cmeta{margin:0;font-size:.78rem;color:var(--mut)}
.cmeta .sep{opacity:.5;margin:0 .35rem}
.warnchip{display:inline-block;font-size:.7rem;font-weight:650;border-radius:4px;padding:.1rem .42rem;
  background:var(--badbg);color:var(--bad);margin-top:.35rem}
.cnums{flex:0 0 auto;text-align:right;font-size:.78rem;color:var(--mut);max-width:19rem}
.cnums .big{font-size:1.45rem;font-weight:700;color:var(--fg);font-variant-numeric:tabular-nums;line-height:1.1}
.cnums .unit{font-size:.85rem;font-weight:600;color:var(--fg)}
.cnums .nmet{display:block;margin-top:.1rem}
.cnums .nanc{display:block;color:var(--accent);font-size:.76rem}
.cnums .nagg{display:block;margin-top:.35rem;padding-top:.3rem;border-top:1px dotted var(--line);font-size:.74rem}
.cnums .nmem{display:block;margin-top:.35rem;font-size:.75rem}
.exp{flex:0 0 auto;font-size:.9rem;color:var(--mut);transition:transform .15s}

.cbody{display:none;border-top:1px solid var(--line);padding:.85rem}
.card.open .cbody{display:block}
.card.open .exp{transform:rotate(90deg)}
.sec{margin-bottom:.9rem}
.sec:last-child{margin-bottom:0}
.sec h4{margin:0 0 .35rem;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
pre.cmd{margin:0;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:.6rem 3.6rem .6rem .7rem;
  overflow-x:auto;font-size:.8rem;white-space:pre-wrap;word-break:break-word;position:relative}
.copy{position:absolute;top:.35rem;right:.35rem;font-size:.68rem;padding:.15rem .45rem}
ol.steps{margin:.5rem 0 0;padding-left:1.25rem;font-size:.86rem}
ol.steps li{margin:.3rem 0}
ol.steps li.prose{color:var(--mut)}
ol.steps li code{background:var(--soft);border:1px solid var(--line);border-radius:5px;padding:.08rem .3rem;
  font-size:.82rem;word-break:break-word}
table.m{border-collapse:collapse;width:100%;font-size:.82rem}
/* Long method notes give these tables a wide minimum content width, so they
   scroll inside the card instead of pushing the page past the viewport. */
.tscroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.m td,table.m th{border:1px solid var(--line);padding:.32rem .5rem;text-align:left;vertical-align:top}
table.m th{background:var(--soft);font-weight:600;font-size:.74rem;text-transform:uppercase;letter-spacing:.03em;color:var(--mut)}
td.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
ul.notes{margin:0;padding-left:1.15rem;font-size:.85rem}
ul.notes li{margin:.25rem 0}
.warn{background:var(--forumbg);border-left:3px solid var(--forum);padding:.5rem .7rem;border-radius:0 6px 6px 0;font-size:.83rem;margin:.3rem 0}
.srclist{font-size:.8rem;display:flex;flex-wrap:wrap;gap:.4rem}
.src{border:1px solid var(--line);border-radius:6px;padding:.18rem .5rem;text-decoration:none;background:var(--soft)}
.src:hover{border-color:var(--accent)}
.src span{color:var(--mut);font-size:.7rem;margin-left:.3rem}
.kv{font-size:.83rem}
.kv div{display:flex;gap:.5rem;padding:.14rem 0;border-bottom:1px dotted var(--line)}
.kv div:last-child{border:0}
.kv dt{flex:0 0 130px;color:var(--mut)}
.kv dd{margin:0;flex:1 1 auto;min-width:0;word-break:break-word}

.empty{text-align:center;padding:3rem 1rem;color:var(--mut)}
.empty button{margin-top:.8rem}
footer{border-top:1px solid var(--line);padding:1.4rem 0 2.5rem;color:var(--mut);font-size:.8rem}
footer h3{color:var(--fg);font-size:.9rem;margin:0 0 .4rem}
footer .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1.4rem}
.counts{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 1rem}
.count{font-size:.75rem;border:1px solid var(--line);border-radius:999px;padding:.15rem .6rem;background:var(--bg);color:var(--mut)}
.count b{color:var(--fg)}

@media (max-width:640px){
  h1{font-size:1.4rem}
  .chead{flex-direction:column;gap:.5rem}
  .cnums{text-align:left;max-width:100%}
  .cnums .nagg{border-top:0;padding-top:0}
  .kv div{flex-direction:column;gap:0}
  .kv dt{flex:none}
  select{max-width:100%;min-width:0;flex:1 1 140px}
}
</style>
</head>
<body>

<header class="top"><div class="wrap">
  <h1>Run Qwen on your own machine</h1>
  <p class="tag">Every community-tested way to run a Qwen model on hardware you own.
  Pick your machine and see what fits, how fast it really goes, and who measured it.</p>
  <div class="picker" id="picker"></div>
</div></header>

<details class="how" id="how" open>
  <summary class="wrap">New here? How local hosting works</summary>
  <div class="wrap">
  <div class="hsteps">
    <div class="hstep"><b><i>1</i>Pick a model</b>
      The weights: one big file you download once. Bigger is smarter and slower.
      A <span class="term" data-def="Quantisation: the weights compressed to fewer bits so they fit a smaller machine. Q4 is about a quarter the size of the original. Lower bits fit more places, and cost some quality.">quant</span>
      is a compressed copy that fits a smaller machine.</div>
    <div class="hstep"><b><i>2</i>Pick an engine</b>
      The program that loads those weights and answers you. Ollama and LM Studio
      are the easy ones. vLLM and SGLang go faster and take more setting up.</div>
    <div class="hstep"><b><i>3</i>Run it</b>
      One command on the easy paths. You get a chat box on your own machine:
      no account, no API bill, works with the wifi off.</div>
  </div>
  <div class="gloss">
    <p style="margin:0;color:var(--mut)">One entry here is one <b>runnable setup</b> &mdash; a specific
    checkpoint, a specific engine configuration, on specific hardware. That is the unit that actually
    gets run and actually gets measured, so a model with 8 checkpoints across 3 engines is 24 entries,
    not one row.</p>
    <details class="words" id="metric-guide"><summary>What controls speed, fit, and quality</summary>
      <div class="depgrid">
        <section class="depgroup" data-category="speed">
          <h3>Speed and responsiveness</h3>
          <p class="rule">Hardware and engine dependent. Compare only results with a similar workload and concurrency.</p>
          <dl>
            <dt>Decode speed (tok/s)</dt>
            <dd>The speed text streams after the first token. At low concurrency it is usually limited by memory bandwidth, but quantisation, active parameters, and engine overhead also matter.
              <span class="driver">Main driver: memory bandwidth (GB/s)</span></dd>
            <dt>TTFT / prefill</dt>
            <dd>How long the prompt takes before the first token. Prompt length, queueing, and engine overhead contribute; the matrix work itself is usually compute-bound.
              <span class="driver">Main driver: GPU/CPU compute at the precision used</span></dd>
            <dt>Batch throughput</dt>
            <dd>Total work across simultaneous requests. It uses both compute and bandwidth, and is not the speed one person sees in one chat.
              <span class="driver">Main drivers: compute, bandwidth, batching engine</span></dd>
          </dl>
        </section>
        <section class="depgroup" data-category="capacity">
          <h3>Capacity and scale</h3>
          <p class="rule">Mostly a memory-budget question. We use resident memory, not download size, for fit.</p>
          <dl>
            <dt>Resident memory / model fit</dt>
            <dd>Weights, KV cache, runtime buffers, and any draft model must fit in available RAM or VRAM.
              <span class="driver">Main driver: usable memory capacity</span></dd>
            <dt>Maximum context</dt>
            <dd>Longer conversations grow the KV cache. Memory can constrain the practical limit, while the model architecture and engine set hard compatibility limits.
              <span class="driver">Main drivers: memory, cache precision, model and engine limits</span></dd>
            <dt>Maximum concurrency</dt>
            <dd>Each active session adds cache and scheduling work. More memory helps, but the engine and latency target decide what remains usable.
              <span class="driver">Main drivers: memory per session, scheduler, latency target</span></dd>
          </dl>
        </section>
        <section class="depgroup" data-category="intrinsic">
          <h3>Model and runtime traits</h3>
          <p class="rule">A faster machine does not improve the checkpoint's intelligence or change its legal terms.</p>
          <dl>
            <dt>Quality</dt>
            <dd>Hardware alone does not change benchmark quality. The checkpoint, quantisation, prompt, and runtime correctness can.</dd>
            <dt>Capabilities</dt>
            <dd>Vision, tools, and thinking depend on the model and whether the chosen engine implements them.</dd>
            <dt>License</dt>
            <dd>The weights and runtime licenses are legal constraints, independent of the device.</dd>
          </dl>
        </section>
      </div>
      <div class="specguide">
        <h3>Hardware specs, translated</h3>
        <p>Capacity answers <i>will it fit?</i>; bandwidth and compute help answer <i>how fast?</i> Exact model, quant, engine, prompt, and concurrency still matter.</p>
        <div class="tscroll"><table class="spectable">
          <thead><tr><th>Device spec</th><th>What it predicts here</th><th>Where to find it</th></tr></thead>
          <tbody>
            <tr><td>RAM / VRAM</td><td>Model fit, resident memory, context headroom, and concurrency</td><td>About This Mac or <code>nvidia-smi</code></td></tr>
            <tr><td>Memory bandwidth</td><td>Usually the strongest hardware predictor of low-concurrency decode speed</td><td>Exact chip or GPU specification</td></tr>
            <tr><td>Compute (FLOPS)</td><td>Prefill and high-batch throughput; compare like-for-like precision because FP4, FP8, and FP16 figures are not interchangeable</td><td>Vendor specification for the precision used</td></tr>
            <tr><td>CPU cores</td><td>CPU inference, tokenisation, offload, and runtime scheduling</td><td>System Information or <code>lscpu</code></td></tr>
            <tr><td>Storage speed</td><td>Download and model-load time; also streamed-expert performance. Usually not steady-state speed once the model is resident</td><td>SSD specification or a disk benchmark</td></tr>
          </tbody>
        </table></div>
        <div class="device-notes">
          <div class="device-note"><b>Apple Silicon</b>CPU and GPU share one unified-memory pool, so a 16 GB Mac does not have a separate 16 GB of VRAM. Bandwidth varies widely by exact chip. The MLX and llama.cpp paths in this directory generally use the GPU and CPU, not the Neural Engine.</div>
          <div class="device-note"><b>DGX Spark</b>128 GB unified memory, 273 GB/s memory bandwidth, and up to 1 PFLOP FP4 theoretical compute with sparsity. NVIDIA advertises inference up to 200B parameters, but actual fit depends on quantisation, cache, and runtime; sustained speed can also move with power and thermals. <a href="https://www.nvidia.com/en-us/products/workstations/dgx-spark/">NVIDIA specifications</a></div>
        </div>
      </div>
    </details>
    <details class="words"><summary>Terms and evidence labels</summary>
      <dl>
        <dt>MoE, active params</dt><dd>Mixture-of-Experts models wake only some parameters per token. On memory-bandwidth-limited machines the active params, not the total, set the speed.</dd>
        <dt>KV cache</dt><dd>Memory holding the conversation so far. Long contexts and many parallel chats spend it first.</dd>
        <dt>MTP / DSpark / DFlash2</dt><dd>Speculative decoding: a cheap draft model proposes tokens the big model verifies, trading memory for speed.</dd>
        <dt>needs fork</dt><dd>Will not run on the stock engine; you must build a patched version. The weakest reproducibility tier here.</dd>
        <dt>Who measured it</dt><dd><span class="pill p-box">box</span> we ran it ourselves, method stated &middot;
          <span class="pill p-forum">forum</span> a builder posted it, link included &middot;
          <span class="pill p-vendor">vendor</span> the publisher's own claim &middot;
          <span class="pill p-none">unverified</span> nobody has measured it yet. These are never blended.</dd>
      </dl>
    </details>
  </div>
  </div>
</details>

<div class="controls"><div class="wrap">
  <div class="row-main">
    <input type="search" id="q" placeholder="Search models, checkpoints, engines, publishers, commands&hellip;" aria-label="Search the directory">
    <select id="sort" aria-label="Sort order">
      <option value="default">Sort: generation, then size</option>
      <option value="easy">Sort: easiest to run first</option>
      <option value="speed">Sort: fastest decode first</option>
      <option value="small">Sort: smallest footprint first</option>
      <option value="evidence">Sort: best evidence first</option>
      <option value="fresh">Sort: most recently updated</option>
    </select>
    <button id="more-filters" type="button" aria-expanded="false">More filters</button>
    <button id="expand-all" type="button">Expand all</button>
    <button id="reset" type="button">Reset</button>
  </div>
  <div class="row-adv" id="adv">
    <select id="f-ready" aria-label="Filter by how complete the entry is">
      <option value="">Anything</option>
      <option value="run">Only ones I can run today</option>
      <option value="measured">Only ones with a speed number</option>
    </select>
    <select id="f-engine" aria-label="Filter by engine"></select>
    <select id="f-hw" aria-label="Filter by hardware"></select>
    <select id="f-quant" aria-label="Filter by quantization"></select>
    <select id="f-tier" aria-label="Filter by evidence tier">
      <option value="">Measured by: anyone</option>
      <option value="box">box &mdash; measured here</option>
      <option value="forum">forum &mdash; community reported</option>
      <option value="vendor">vendor &mdash; publisher claimed</option>
      <option value="none">unverified</option>
    </select>
    <select id="f-fit" aria-label="Filter by memory budget">
      <option value="">Fits in: any</option>
    </select>
  </div>
  <div class="hint" id="hint"></div>
</div></div>

<main class="wrap"><div id="rec"></div><div id="out"></div></main>

<footer><div class="wrap">
  <div class="counts" id="counts"></div>
  <div class="cols">
  <div>
    <h3>Method</h3>
    <p><span class="pill p-box">box</span> numbers are net-decode medians, n=5, counted from the
    server's own <code>completion_tokens</code>, re-baselined per session. Code deltas under 15% are
    treated as noise. Wall-time and concurrency-ladder figures are a different clock and are never
    mixed into the same comparison.</p>
    <p><span class="pill p-forum">forum</span> numbers are single-sample unless the thread says
    otherwise, and they rot fast. <span class="pill p-vendor">vendor</span> numbers are marketing
    until somebody reproduces them.</p>
  </div>
  <div>
    <h3>Why the headline number is the slow one</h3>
    <p>When a single-stream figure exists, it always wins the big slot: one person, one conversation.
    Aggregate-only results say so explicitly. Where a builder also reported aggregate throughput, it
    appears underneath with the stated concurrency, because 266 tok/s across 48 chats is 5.6 tok/s
    each &mdash; not a faster experience. Speed sorting is a discovery aid, never a cross-harness leaderboard.</p>
  </div>
  <div>
    <h3>Contributing</h3>
    <p>Each entry is one JSON file under <code>directory/data/setups/</code>. Every measurement needs a
    source URL unless it is a <code>box</code> number, in which case it needs a date, a sample count and
    a method. <code>python3 directory/validate.py</code> rejects anything else, including numbers with no
    source and setups that duplicate an existing one.</p>
    <p id="gen"></p>
  </div>
  </div>
</div></footer>

<div id="pop" hidden></div>

<script id="data" type="application/json">__DATA_JSON__</script>
<script>
(function(){
"use strict";
var D = JSON.parse(document.getElementById('data').textContent);
var MODELS = D.models, HW = D.hardware, ENG = D.engines, PUB = D.publishers;
var TIER_RANK = {box:3, forum:2, vendor:1};

/* Reading-speed anchor. ~250 wpm at ~0.75 words per token lands near 5 tok/s;
   it is stated in the glossary so the multiplier stays auditable. */
var READING_TOKS = 5;

function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
function pub(id){ return (PUB[id]||{}).name || id || 'unknown'; }
function modelName(id){ return (MODELS[id]||{}).name || id; }
function engName(id){ return (ENG[id]||{}).name || id; }
function hwName(id){ return (HW[id]||{}).name || id; }
function fmtGb(v){ return v==null?'?':(v>=100?Math.round(v):Math.round(v*10)/10)+' GB'; }
function fmtCtx(n){ if(n==null) return '?'; return n>=1000000?(n/1000000)+'M':n>=1000?Math.round(n/1000)+'K':n; }

/* ---- plain-English machine profiles ------------------------------------- */
var MACHINES = [
  {id:'mac',      label:'Apple Silicon Mac',  sub:'M1–M4 Pro / Max / Ultra',
   hw:['mac-64gb','mac-128gb'], mems:[16,24,32,48,64,96,128], def:32},
  {id:'nvidia',   label:'NVIDIA GPU',         sub:'One card, RTX 3090 / 4090 class',
   hw:['gpu-24gb'], mems:[8,12,16,24,32], def:24},
  {id:'multigpu', label:'Multi-GPU desktop',  sub:'Two or more cards',
   hw:['gpu-multigpu-72gb','gpu-24gb'], mems:[48,72,96,128], def:72},
  {id:'spark',    label:'DGX Spark / ThinkStation PGX', sub:'GB10, 128 GB unified',
   hw:['dgx-spark','thinkstation-pgx'], mems:[128], def:128}
];
var MACHINE_BY_ID = {};
MACHINES.forEach(function(m){ MACHINE_BY_ID[m.id]=m; });

/* Install effort, lower is easier. Drives the "start here" pick and the sort. */
var EASE = {'ollama':1,'lm-studio':1,'llama-cpp':2,'mlx-lm':2,'vllm':3,'sglang':3,'custom-fork':4};
function easeOf(s){ var e=EASE[(s.engine||{}).id]; if(e==null) e=3;
  if((s.engine||{}).requires_fork) e+=1; return e; }
function easeLabel(s){ var e=easeOf(s), id=(s.engine||{}).id;
  if(id==='lm-studio') return 'guided app setup';
  if(id==='ollama' && runCommand(s)) return 'one command';
  return e<=1?'easy setup':(e<=2?'a few steps':(e<=3?'advanced setup':'needs a patched engine')); }
/* 1 = a beginner can do this, 2 = server-engine territory. */
function easeTier(s){ return easeOf(s)<=2?1:2; }
function modelParams(s){ return ((MODELS[s.model]||{}).architecture||{}).params_total_b||0; }
/* Sub-4-bit builds fit anywhere and read as a bargain, but the quality cost is
   real and often uncharacterised — a 180B at ~1 bit/weight is the wrong first
   run. Soft, not a ban: a small machine can still be offered one. */
var QUANT_RISK={'gguf-q2':2,'gguf-q3':1};
function quantRisk(s){ return QUANT_RISK[String((s.variation||{}).quant||'').toLowerCase()]||0; }

var TERMS = {
  'toks':'Tokens per second while answering — the speed you feel as text streams. Roughly 5 tok/s is comfortable reading speed.',
  'resident':'Memory the setup holds while running: weights plus KV cache plus any draft model. This is what decides whether it fits, not the download size.',
  'download':'Disk space for the weights file. You pay this once; it does not have to fit in memory.',
  'agg':'Total tokens per second summed across every conversation running at the same time. It is not what one person feels — divide by the number of streams for that.',
  'fork':'This will not run on the stock engine; you have to build a patched version yourself. The weakest reproducibility tier here.'
};
function term(label,key){
  var d=TERMS[key]; if(!d) return esc(label);
  return '<span class="term" data-def="'+esc(d)+'">'+esc(label)+'</span>';
}

/* ---- derived helpers ---------------------------------------------------- */
function tierOf(s){
  var ms = s.measurements||[];
  if(!ms.length) return 'none';
  var best = 0, out = 'none';
  ms.forEach(function(m){ var r=TIER_RANK[m.provenance]||0; if(r>best){best=r;out=m.provenance;} });
  return out;
}

var METRIC_LABEL = {
  decode_chat:'chatting', decode_code:'generating code', decode_essay:'writing long text',
  decode_per_stream:'one conversation', decode_agg:'aggregate throughput'
};
/* Single-stream metrics come first. Aggregate is a labelled fallback only when
   no single-stream decode result exists. */
var SINGLE_PREF = ['decode_chat','decode_code','decode_essay','decode_per_stream'];

function decodeToks(s){ return (s.measurements||[]).filter(function(m){
  return m.unit==='tok/s' && /^decode_/.test(m.metric); }); }
/* concurrency is an optional positive int; absent means the builder did not say,
   which we treat as single-stream only for metrics that are single by nature. */
function isSingle(m){ return m.concurrency==null || m.concurrency<=1; }
function representative(rows){
  var nonPeak=rows.filter(function(m){return m.stat!=='peak';});
  var pool=nonPeak.length?nonPeak:rows;
  return pool.reduce(function(a,b){return b.value>a.value?b:a;});
}

function bestSpeed(s){
  var ms=decodeToks(s);
  if(!ms.length) return null;
  /* Prefer any representative single-stream result over a peak, even when the
     peak belongs to a normally preferred workload metric. Fall back to peaks
     only when that is all the source published. */
  for(var pass=0;pass<2;pass++){
    for(var i=0;i<SINGLE_PREF.length;i++){
      var hit=ms.filter(function(m){return m.metric===SINGLE_PREF[i] && isSingle(m)
        && (pass===1 || m.stat!=='peak');});
      if(hit.length){
        var top=representative(hit);
        return {metric:SINGLE_PREF[i], value:top.value, prov:top.provenance, stat:top.stat};
      }
    }
  }
  var agg=ms.filter(function(m){return m.metric==='decode_agg';});
  if(agg.length){
    var t=representative(agg);
    return {metric:'decode_agg', value:t.value, prov:t.provenance, stat:t.stat, conc:t.concurrency, aggOnly:true};
  }
  return {metric:ms[0].metric, value:ms[0].value, prov:ms[0].provenance};
}

/* Aggregate throughput, plus the per-stream collapse it implies. This is the
   honest counterweight to a big parallel number: 266.8 tok/s across 48 streams
   is 5.6 tok/s each, which is not a faster experience for one reader. */
function aggSpeed(s, headline){
  var ms=decodeToks(s);
  var agg=ms.filter(function(m){return m.metric==='decode_agg';});
  if(!agg.length || (headline && headline.metric==='decode_agg')) return null;
  var top=representative(agg);
  var per=ms.filter(function(m){
    return m.metric==='decode_per_stream' && m.concurrency>1;
  });
  /* A collapse line is only valid when both values share structured
     concurrency. Similar-looking values from different fixtures are not joined. */
  var same=per.filter(function(m){return m.concurrency===top.concurrency;});
  var low=same.length?same.reduce(function(a,b){return b.value<a.value?b:a;}):null;
  var collapse=(low && headline)
    ? {value:low.value, conc:low.concurrency} : null;
  return {value:top.value, conc:top.concurrency, prov:top.provenance, collapse:collapse};
}

function anchorText(v){
  if(v==null) return '';
  if(v < READING_TOKS) return '≈ slower than you read';
  var x=v/READING_TOKS;
  return '≈ '+(x>=10?Math.round(x):Math.round(x*10)/10)+'× reading speed';
}

function tierPill(t){
  if(t==='none') return '<span class="pill p-none">unverified</span>';
  return '<span class="pill p-'+t+'">'+t+'</span>';
}
function tierWords(t){
  return t==='box'?'measured here':(t==='forum'?'community-reported':
         (t==='vendor'?'publisher claim':'unverified'));
}

/* run.steps entries are {kind, text} objects: kind "cmd" is a shell command that
   runs as shown, kind "do" is a prose instruction or a UI action. Only "cmd"
   gets monospaced and a copy button — dressing a sentence up as pasteable is
   how a beginner ends up typing prose into a terminal. */
function stepKind(x){ return (x && typeof x==='object') ? x.kind : null; }
function stepText(x){ return (x && typeof x==='object') ? x.text : String(x==null?'':x); }
function runCommand(s){
  var r=s.run||{};
  if(r.command) return r.command;
  var cmds=(r.steps||[]).filter(function(x){return stepKind(x)==='cmd';}).map(stepText);
  return cmds.length?cmds[0]:null;
}
function stepsHtml(s){
  var r=s.run||{}, seen={};
  var steps=[];
  function add(kind,text){
    text=String(text||'').trim();
    if(!text || seen[kind+'\n'+text]) return;
    seen[kind+'\n'+text]=1; steps.push({kind:kind,text:text});
  }
  if(r.command) add('cmd',r.command);
  (r.steps||[]).forEach(function(x){ add(stepKind(x),stepText(x)); });
  return steps.map(function(x){
    return x.kind==='cmd'
      ? '<li class="command-step"><pre class="cmd">'+esc(x.text)+'<button class="copy" type="button" data-copy="'+esc(x.text)+'">copy</button></pre></li>'
      : '<li class="prose">'+esc(x.text)+'</li>'; }).join('');
}
/* Completeness is two independent facts: whether a command exists and whether
   decode speed was measured. Keep all four combinations explicit. */
function readiness(s){
  var hasCmd=!!runCommand(s), hasSpeed=!!bestSpeed(s);
  if(hasCmd&&hasSpeed) return 'full';
  if(hasCmd) return 'recipe';
  return hasSpeed?'measured-lead':'lead';
}
var READY_LABEL={full:'✓ recipe + measured', recipe:'◔ recipe, unmeasured',
  'measured-lead':'◐ measured, no command yet', lead:'○ lead only — no command or speed yet'};

/* ---- reader profile ------------------------------------------------------ */
var profile={machine:'', mem:0};
try{
  var saved=JSON.parse(localStorage.getItem('qlr.profile')||'null');
  var machine=saved&&MACHINE_BY_ID[saved.machine];
  if(machine && machine.mems.indexOf(Number(saved.mem))>=0){
    profile={machine:machine.id,mem:Number(saved.mem)};
  }
}catch(e){}
function saveProfile(){ try{ localStorage.setItem('qlr.profile',JSON.stringify(profile)); }catch(e){} }

/* Fit is meaningless without a reader: with no machine declared we show the
   bare requirement rather than a green or red verdict. */
function fitFor(s){
  var need=(s.requirements||{}).memory_gb;
  if(need==null) return null;
  if(!profile.machine) return {status:'unknown', need:need};
  var mem=profile.mem, spare=Math.round((mem-need)*10)/10;
  if(need>mem) return {status:'no', need:need, mem:mem, spare:spare};
  if(need>mem*0.85) return {status:'tight', need:need, mem:mem, spare:spare};
  return {status:'good', need:need, mem:mem, spare:spare};
}
function verdictHtml(s){
  var f=fitFor(s);
  if(!f) return '';
  if(f.status==='unknown') return '<span class="verdict v-unknown">needs '+fmtGb(f.need)+' '+term('resident','resident')+'</span>';
  if(f.status==='no') return '<span class="verdict v-no">Too big — needs '+fmtGb(f.need)+', you have '+fmtGb(f.mem)+'</span>';
  if(f.status==='tight') return '<span class="verdict v-tight">Tight — '+fmtGb(f.need)+' of your '+fmtGb(f.mem)+', only '+fmtGb(f.spare)+' spare</span>';
  return '<span class="verdict v-good">✓ Fits — '+fmtGb(f.need)+' of your '+fmtGb(f.mem)+', '+fmtGb(f.spare)+' to spare</span>';
}

/* ---- filters ------------------------------------------------------------ */
function fill(sel, items, label){
  var el=document.getElementById(sel);
  el.innerHTML='<option value="">'+label+'</option>'+items.map(function(it){
    return '<option value="'+esc(it[0])+'">'+esc(it[1])+'</option>';}).join('');
}
(function initFilters(){
  var eids={}, hids={}, qs={};
  D.setups.forEach(function(s){
    if(s.engine&&s.engine.id) eids[s.engine.id]=1;
    (s.hardware||[]).forEach(function(h){hids[h]=1;});
    if(s.variation&&s.variation.quant) qs[String(s.variation.quant).toUpperCase()]=1;
  });
  fill('f-engine', Object.keys(eids).sort().map(function(k){return [k,engName(k)];}),'Engine: any');
  fill('f-hw', Object.keys(hids).sort().map(function(k){return [k,hwName(k)];}),'Hardware: any');
  fill('f-quant', Object.keys(qs).sort().map(function(k){return [k.toLowerCase(),'quant '+k];}),'Quant: any');
  var budgets=[[24,'fits in 24 GB'],[32,'fits in 32 GB'],[48,'fits in 48 GB'],[64,'fits in 64 GB'],[128,'fits in 128 GB']];
  var f=document.getElementById('f-fit');
  budgets.forEach(function(b){ var o=document.createElement('option'); o.value=b[0]; o.textContent=b[1]; f.appendChild(o); });
})();

var state={q:'',engine:'',hw:'',quant:'',tier:'',fit:'',ready:'',sort:'default',open:{},onlyFits:true};

function machineMatch(s){
  var m=MACHINE_BY_ID[profile.machine];
  if(!m) return true;
  var ids=s.hardware||[];
  for(var i=0;i<ids.length;i++) if(m.hw.indexOf(ids[i])>=0) return true;
  return false;
}

function matches(s){
  if(state.engine && (!s.engine||s.engine.id!==state.engine)) return false;
  if(state.hw && (s.hardware||[]).indexOf(state.hw)<0) return false;
  if(state.quant && String((s.variation||{}).quant||'').toLowerCase()!==state.quant) return false;
  var t=tierOf(s);
  if(state.tier && t!==state.tier) return false;
  if(state.ready==='run' && !runCommand(s)) return false;
  if(state.ready==='measured' && !bestSpeed(s)) return false;
  if(state.fit){
    var need=(s.requirements||{}).memory_gb;
    if(need==null || need>Number(state.fit)) return false;
  }
  if(profile.machine){
    if(!machineMatch(s)) return false;
    if(state.onlyFits){
      var n=(s.requirements||{}).memory_gb;
      if(n==null || n>profile.mem) return false;
    }
  }
  if(state.q){
    var hay=[s.title,s.id,(s.variation||{}).checkpoint,(s.variation||{}).quant,
      (s.variation||{}).quant_detail,(s.engine||{}).config,(s.engine||{}).image,
      (s.engine||{}).draft_model,(s.run||{}).command,(s.run||{}).repo,(s.run||{}).profile,
      pub((s.variation||{}).publisher), modelName(s.model),
      (s.hardware||[]).map(hwName).join(' '),
      JSON.stringify((s.run||{}).steps||[]),
      (s.caveats||[]).join(' '),
      JSON.stringify(s.measurements||[])].join(' ').toLowerCase();
    var terms=state.q.toLowerCase().split(/\s+/).filter(Boolean);
    for(var i=0;i<terms.length;i++) if(hay.indexOf(terms[i])<0) return false;
  }
  return true;
}

function sortSetups(list){
  var c=list.slice();
  if(state.sort==='speed'){
    c.sort(function(a,b){var x=bestSpeed(a),y=bestSpeed(b);
      if(!!x!==!!y) return y?1:-1;
      if(!x) return 0;
      if(!!x.aggOnly!==!!y.aggOnly) return x.aggOnly?1:-1;
      return (y?y.value:-1)-(x?x.value:-1);});
  } else if(state.sort==='easy'){
    c.sort(function(a,b){ var d=easeOf(a)-easeOf(b); if(d) return d;
      var ra={full:0,recipe:1,'measured-lead':2,lead:3}; d=ra[readiness(a)]-ra[readiness(b)]; if(d) return d;
      return ((a.requirements||{}).memory_gb||1e9)-((b.requirements||{}).memory_gb||1e9);});
  } else if(state.sort==='small'){
    c.sort(function(a,b){return ((a.requirements||{}).memory_gb||1e9)-((b.requirements||{}).memory_gb||1e9);});
  } else if(state.sort==='evidence'){
    c.sort(function(a,b){return (TIER_RANK[tierOf(b)]||0)-(TIER_RANK[tierOf(a)]||0);});
  } else if(state.sort==='fresh'){
    c.sort(function(a,b){return String(b.updated||'').localeCompare(String(a.updated||''));});
  }
  return c;
}

/* ---- recommendation ------------------------------------------------------ */
function recommend(list){
  /* Deliberately does NOT require a copyable command: most of the easy Mac and
     llama.cpp lanes carry prose steps, and requiring a command promotes a hard
     server engine over an easy one purely because someone typed a shell line. */
  var ok=list.filter(function(s){
    var f=fitFor(s);
    /* 'tight' is not a first experience: a setup that leaves no headroom will
       stall the moment the conversation grows the KV cache. */
    if(!f || f.status!=='good') return false;
    return !(s.engine||{}).requires_fork;
  });
  if(!ok.length) return null;
  ok.sort(function(a,b){
    /* Ease is a two-bucket question, not a fine ranking: Ollama, LM Studio,
       llama.cpp and MLX are all "a beginner can do this". Ranking them against
       each other handed every machine the same answer, so inside the easy
       bucket we prefer the most capable model the box can actually hold. */
    var d=easeTier(a)-easeTier(b); if(d) return d;
    d=quantRisk(a)-quantRisk(b); if(d) return d;
    d=(bestSpeed(b)?1:0)-(bestSpeed(a)?1:0); if(d) return d;
    d=modelParams(b)-modelParams(a); if(d) return d;
    d=(TIER_RANK[tierOf(b)]||0)-(TIER_RANK[tierOf(a)]||0); if(d) return d;
    d=(runCommand(b)?1:0)-(runCommand(a)?1:0); if(d) return d;
    var sa=bestSpeed(a), sb=bestSpeed(b);
    return (sb?sb.value:0)-(sa?sa.value:0);
  });
  return ok[0];
}

function recCard(s){
  if(!s) return '';
  var f=fitFor(s), sp=bestSpeed(s), why=[];
  why.push('<b>'+esc(easeLabel(s))+'</b> with '+esc(engName((s.engine||{}).id)));
  if(f) why.push('fits with <b>'+fmtGb(f.spare)+'</b> to spare');
  if(sp) why.push('<b>'+esc(sp.value)+' tok/s</b> '+esc(METRIC_LABEL[sp.metric]||sp.metric)+
    (sp.stat?', '+esc(sp.stat):'')+', '+esc(tierWords(sp.prov)));
  else why.push('no speed measured yet');
  var cmd=runCommand(s);
  /* No command recorded is common on the easy lanes; show the written steps
     rather than an empty box, so the reader still leaves with instructions. */
  var steps=cmd?'':stepsHtml(s);
  return '<section class="rec">'+
    '<h2>Start here</h2>'+
    '<p class="rtitle">'+esc(s.title)+'</p>'+
    (s.slug_note?'<p class="rwhy">'+esc(s.slug_note)+'</p>':'')+
    '<p class="rwhy">'+why.join(' &middot; ')+'</p>'+
    (cmd?'<pre class="cmd">'+esc(cmd)+'<button class="copy" type="button" data-copy="'+esc(cmd)+'">copy</button></pre>':'')+
    (steps?'<ol class="steps">'+steps+'</ol>':'')+
    '<p class="rlinks"><a href="#s-'+esc(s.id)+'">Open the full entry</a> for measurements, caveats and sources.</p>'+
  '</section>';
}

/* ---- rendering ---------------------------------------------------------- */
function measurementTable(s){
  var ms=s.measurements||[];
  if(!ms.length) return '<p class="hint">No measurements recorded for this setup yet.</p>';
  var rows=ms.map(function(m){
    var extra=[];
    if(m.range) extra.push('range '+m.range[0]+'–'+m.range[1]);
    if(m.n) extra.push('n='+m.n);
    if(m.date) extra.push(m.date);
    if(m.stat) extra.push(m.stat);
    var label=METRIC_LABEL[m.metric];
    return '<tr><td><code>'+esc(m.metric)+'</code>'+(label?'<br><span class="hint">'+esc(label)+'</span>':'')+'</td>'+
      '<td class="num">'+esc(m.value)+' '+esc(m.unit||'')+'</td>'+
      '<td>'+tierPill(m.provenance)+'</td>'+
      '<td>'+esc(extra.join(' · '))+(m.method?'<br><span class="hint">'+esc(m.method)+'</span>':'')+
        (m.note?'<br><span class="hint">'+esc(m.note)+'</span>':'')+
        (m.source?'<br><a href="'+esc(m.source)+'" rel="noopener">source</a>':'')+'</td></tr>';
  }).join('');
  return '<div class="tscroll"><table class="m"><thead><tr><th>Metric</th><th>Value</th><th>Measured by</th><th>Context</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
}

function card(s){
  var v=s.variation||{}, e=s.engine||{}, r=s.run||{}, req=s.requirements||{}, caps=s.capabilities||{};
  var t=tierOf(s), sp=bestSpeed(s), ag=aggSpeed(s,sp);
  var isOpen=!!state.open[s.id];

  /* One muted metadata line instead of a row of same-weight chips. */
  var meta=[engName(e.id)];
  if(v.quant) meta.push(String(v.quant).toUpperCase());
  (s.hardware||[]).forEach(function(h){meta.push(hwName(h));});
  if(e.spec_decode&&e.spec_decode!=='none') meta.push('spec: '+e.spec_decode);
  if(s.builder&&PUB[s.builder]) meta.push('by '+(PUB[s.builder].name||s.builder));
  var can=[]; if(caps.vision) can.push('images'); if(caps.tools) can.push('tools'); if(caps.thinking) can.push('thinking');
  var metaHtml=meta.map(esc).join('<span class="sep">·</span>');
  if(can.length) metaHtml+='<span class="sep">·</span>Can: '+esc(can.join(', '));

  var nums='';
  if(sp){
    nums+='<span class="big">'+esc(sp.value)+'</span> <span class="unit">tok/s</span>'+
          '<span class="nmet">'+esc(METRIC_LABEL[sp.metric]||sp.metric)+(sp.stat?' · '+esc(sp.stat):'')+' · '+esc(tierWords(sp.prov))+'</span>'+
          '<span class="nanc">'+esc(anchorText(sp.value))+'</span>';
  } else {
    nums+='<span class="big">—</span><span class="nmet">no speed measured yet</span>';
  }
  if(ag){
    nums+='<span class="nagg">'+esc(ag.value)+' tok/s '+
          term(ag.conc?('total across '+ag.conc+' streams'):'aggregate; concurrency not stated','agg')+
          (ag.collapse?'<br>but only '+esc(ag.collapse.value)+' tok/s each at that load':'')+'</span>';
  }
  nums+='<span class="nmem">'+fmtGb(req.memory_gb)+' '+term('resident','resident')+
        ' · '+fmtGb(req.disk_gb)+' '+term('download','download')+'</span>';

  var steps = stepsHtml(s);

  var kv='';
  function add(k,val){ if(val!=null&&val!=='') kv+='<div><dt>'+k+'</dt><dd>'+val+'</dd></div>'; }
  add('Checkpoint', '<a href="'+esc(v.url)+'" rel="noopener">'+esc(v.checkpoint)+'</a>');
  add('Publisher', esc(pub(v.publisher)));
  add('Builder', s.builder&&PUB[s.builder]
      ? '<a href="'+esc(PUB[s.builder].url||v.url)+'" rel="noopener">'+esc(PUB[s.builder].name||s.builder)+'</a> — recipe and numbers by this builder'
      : null);
  add('Quant detail', esc(v.quant_detail));
  add('Format / size', esc(v.format)+(v.size_gb!=null?' · '+fmtGb(v.size_gb):''));
  add('License', esc(v.license));
  add('Engine config', esc(e.config));
  add('Image', e.image?'<code>'+esc(e.image)+'</code>':null);
  add('Draft model', e.draft_model?'<code>'+esc(e.draft_model)+'</code>':null);
  add('Key flags', (e.flags&&e.flags.length)?e.flags.map(function(f){return '<code>'+esc(f)+'</code>';}).join('<br>'):null);
  add('Context', caps.long_context!=null?(fmtCtx(caps.long_context)+' native'+(caps.max_context&&caps.max_context!==caps.long_context?' · up to '+fmtCtx(caps.max_context):'')):null);
  add('Requirements', esc(req.notes));
  add('Local recipe', r.profile?'<code>'+esc(r.profile)+'</code>':null);
  add('Auto-bootable', r.auto_bootable===false?'No — manual-only lane':(r.auto_bootable===true?'Yes':null));
  add('Downloads', v.downloads!=null?Number(v.downloads).toLocaleString():null);

  var srcs=(s.sources||[]).map(function(x){
    return '<a class="src" href="'+esc(x.url)+'" rel="noopener">'+esc(x.kind)+'<span>'+esc(x.note||'')+
      '</span></a>';}).join(' ');

  var cav=(s.caveats||[]).map(function(c){return '<div class="warn">'+esc(c)+'</div>';}).join('');

  var eg = ENG[e.id]||{};
  var gotchas = (eg.gotchas||[]).slice(0,3).map(function(g){return '<li>'+esc(g)+'</li>';}).join('');

  return '<article class="card'+(isOpen?' open':'')+'" id="s-'+esc(s.id)+'" data-id="'+esc(s.id)+'">'+
    '<div class="chead" role="button" tabindex="0" aria-expanded="'+(isOpen?'true':'false')+'">'+
      '<div class="cmain">'+
        verdictHtml(s)+'<span class="ready">'+esc(READY_LABEL[readiness(s)])+'</span>'+
        '<p class="ctitle">'+esc(s.title)+'</p>'+
        (s.slug_note?'<p class="cnote">'+esc(s.slug_note)+'</p>':'')+
        '<p class="cmeta">'+metaHtml+'</p>'+
        (e.requires_fork?'<span class="warnchip">⚠ '+term('needs fork','fork')+'</span>':'')+
      '</div>'+
      '<div class="cnums">'+nums+'</div>'+
      '<div class="exp" aria-hidden="true">&#9654;</div>'+
      '</div>'+
      '<div class="cbody">'+
      '<div class="sec"><h4>How to run it</h4>'+
        (!runCommand(s)?'<p class="hint norun">No copyable command recorded yet — follow the recipe repo below.</p>':'')+
        (steps?'<ol class="steps">'+steps+'</ol>':'')+
        (r.repo?'<p class="hint" style="margin-top:.5rem">Recipe: <a href="'+esc(r.repo)+'" rel="noopener">'+esc(r.repo)+'</a></p>':'')+
      '</div>'+
      '<div class="sec"><h4>Details</h4><div class="kv">'+kv+'</div></div>'+
      '<div class="sec"><h4>Measurements</h4>'+measurementTable(s)+'</div>'+
      (cav?'<div class="sec"><h4>Caveats — what these numbers do not mean</h4>'+cav+'</div>':'')+
      (gotchas?'<div class="sec"><h4>Engine gotchas ('+esc(engName(e.id))+')</h4><ul class="notes">'+gotchas+'</ul></div>':'')+
      '<div class="sec"><h4>Sources</h4><div class="srclist">'+srcs+'</div>'+
        '<p class="hint" style="margin-top:.4rem">Last updated '+esc(s.updated||'unknown')+'</p></div>'+
    '</div></article>';
}

function group(s){
  var m=MODELS[s.model]||{};
  var a=m.architecture||{}, c=m.context||{};
  var specs=[];
  function sp(cls,k,val){ if(val!=null&&val!=='') specs.push('<span class="spec '+cls+'"><b>'+k+'</b>'+esc(val)+'</span>'); }
  sp('params','params', a.params_total_b!=null?(a.kind==='moe'?(a.params_total_b+'B total / '+a.params_active_b+'B awake per token'):(a.params_total_b+'B dense')):null);
  sp('shape','shape', a.kind==='moe'?'MoE':'dense');
  if(a.hybrid) sp('arch','arch','GDN hybrid');
  if(a.mtp_head) sp('mtp','MTP head','yes');
  sp('context','context', fmtCtx(c.native)+(c.max&&c.max!==c.native?' → '+fmtCtx(c.max):''));
  sp('sees','sees', (m.modalities||[]).join(' + '));
  sp('license','license', m.license);
  sp('released','released', m.released);

  var reg=(m.known_regressions||[]).map(function(x){return '<div class="warn">'+esc(x)+'</div>';}).join('');
  var notes=(m.notes||[]).map(function(x){return '<li>'+esc(x)+'</li>';}).join('');

  return '<section class="group" id="m-'+esc(s.model)+'">'+
    '<div class="ghead"><h2>'+esc(m.name||s.model)+'</h2>'+
      '<span class="gmeta">'+s.items.length+' runnable setup'+(s.items.length===1?'':'s')+
      (m.url?' &middot; <a href="'+esc(m.url)+'" rel="noopener">model card</a>':'')+'</span></div>'+
    '<div class="gspecs">'+specs.join('')+'</div>'+
    (m.summary?'<p class="gsum">'+esc(m.summary)+'</p>':'')+
    reg+
    (notes?'<ul class="notes" style="margin-bottom:.9rem">'+notes+'</ul>':'')+
    (m.sampler_guidance?'<div class="warn"><b>Sampler guidance.</b> '+esc(m.sampler_guidance)+'</div>':'')+
    s.items.map(card).join('')+
    '</section>';
}

/* ---- machine picker ------------------------------------------------------ */
function renderPicker(){
  var el=document.getElementById('picker');
  if(!profile.machine){
    el.innerHTML='<h2>First: what are you running this on?</h2>'+
      '<div class="mgrid">'+MACHINES.map(function(m){
        return '<button class="mopt" type="button" data-machine="'+esc(m.id)+'">'+
          '<b>'+esc(m.label)+'</b><span>'+esc(m.sub)+'</span></button>';}).join('')+'</div>'+
      '<p class="mskip"><button type="button" id="skip-picker">Not sure yet — just show me everything</button></p>';
    return;
  }
  var m=MACHINE_BY_ID[profile.machine];
  el.innerHTML='<div class="profile">'+
    '<span class="who">'+esc(m.label)+'</span>'+
    '<label>Memory: <select id="p-mem" aria-label="Your memory in GB">'+
      m.mems.map(function(g){return '<option value="'+g+'"'+(g===profile.mem?' selected':'')+'>'+g+' GB</option>';}).join('')+
    '</select></label>'+
    '<button class="link" type="button" id="change-machine">change machine</button>'+
  '</div>';
}

function render(){
  var list=D.setups.filter(matches);
  list=sortSetups(list);

  document.getElementById('rec').innerHTML =
    (profile.machine && !state.q && state.sort==='default') ? recCard(recommend(list)) : '';

  var byModel={};
  list.forEach(function(s){ (byModel[s.model]=byModel[s.model]||[]).push(s); });
  /* Group order follows the active sort: with the default sort we keep the
     generation-then-size order, but any explicit sort must be honoured at page
     level too, so groups are emitted in the order their best card appears. */
  var order;
  if(state.sort==='default'){
    order=D.model_order.filter(function(id){return byModel[id];});
    Object.keys(byModel).forEach(function(id){ if(order.indexOf(id)<0) order.push(id); });
  } else {
    order=[];
    list.forEach(function(s){ if(order.indexOf(s.model)<0) order.push(s.model); });
  }

  var out=document.getElementById('out');
  if(!list.length){
    out.innerHTML='<div class="empty"><p><b>Nothing fits those filters.</b></p>'+
      '<p>Try raising the memory budget, or clearing the engine filter.</p>'+
      '<button type="button" id="clear-empty">Clear filters</button></div>';
  } else {
    out.innerHTML=order.map(function(id){ return group({model:id, items:byModel[id]}); }).join('');
  }

  var measured=list.filter(function(s){return tierOf(s)==='box';}).length;
  var forum=list.filter(function(s){return tierOf(s)==='forum';}).length;
  var vendor=list.filter(function(s){return tierOf(s)==='vendor';}).length;
  var none=list.filter(function(s){return tierOf(s)==='none';}).length;
  var head;
  if(profile.machine && state.onlyFits){
    head='<b>'+list.length+'</b> setups fit your '+esc(MACHINE_BY_ID[profile.machine].label)+
         ' with '+profile.mem+' GB &middot; <button class="link" type="button" id="show-all">show all '+D.setups.length+'</button>';
  } else if(profile.machine){
    head='<b>'+list.length+'</b> of '+D.setups.length+' setups shown &middot; '+
         '<button class="link" type="button" id="only-fits">only what fits my '+profile.mem+' GB</button>';
  } else {
    head='<b>'+list.length+'</b> of '+D.setups.length+' setups shown';
  }
  document.getElementById('hint').innerHTML = head+' &middot; '+order.length+' model families &middot; '+
    tierPill('box')+' '+measured+' &nbsp;'+tierPill('forum')+' '+forum+' &nbsp;'+
    tierPill('vendor')+' '+vendor+' &nbsp;'+tierPill('none')+' '+none;
}

function renderCounts(){
  var c=D.counts;
  document.getElementById('counts').innerHTML=[
    ['setups',c.setups],['model families',c.models],['hardware classes',c.hardware],
    ['engines',c.engines],['publishers',c.publishers],['measured on our box',c.measured]
  ].map(function(p){return '<span class="count"><b>'+p[1]+'</b> '+esc(p[0])+'</span>';}).join('');
  document.getElementById('gen').textContent='Dataset generated '+D.generated+'.';
}

/* ---- glossary popover ---------------------------------------------------- */
var pop=document.getElementById('pop');
function showTerm(el){
  pop.textContent=el.getAttribute('data-def');
  pop.hidden=false;
  var r=el.getBoundingClientRect();
  /* position:fixed and clamped to the viewport, so a term near the right edge
     can never push the document into horizontal overflow. */
  pop.style.top=Math.min(r.bottom+8, window.innerHeight-pop.offsetHeight-8)+'px';
  pop.style.left=Math.max(8, Math.min(r.left, window.innerWidth-pop.offsetWidth-8))+'px';
}
function hideTerm(){ pop.hidden=true; }
document.addEventListener('keydown',function(ev){ if(ev.key==='Escape') hideTerm(); });

/* ---- events ------------------------------------------------------------- */
function bind(id,key,ev){
  var el=document.getElementById(id);
  el.addEventListener(ev||'input',function(){ state[key]=el.value; render(); });
}
bind('q','q'); bind('f-engine','engine','change'); bind('f-hw','hw','change');
bind('f-quant','quant','change'); bind('f-tier','tier','change');
bind('f-fit','fit','change'); bind('f-ready','ready','change'); bind('sort','sort','change');

document.getElementById('picker').addEventListener('click',function(ev){
  var opt=ev.target.closest('[data-machine]');
  if(opt){
    var m=MACHINE_BY_ID[opt.getAttribute('data-machine')];
    profile={machine:m.id, mem:m.def}; saveProfile();
    state.onlyFits=true; renderPicker(); render(); return;
  }
  if(ev.target.closest('#skip-picker')){
    profile={machine:'', mem:0}; saveProfile(); renderPicker(); render(); return;
  }
  if(ev.target.closest('#change-machine')){
    profile={machine:'', mem:0}; saveProfile(); renderPicker(); render(); return;
  }
});
document.getElementById('picker').addEventListener('change',function(ev){
  if(ev.target.id==='p-mem'){ profile.mem=Number(ev.target.value); saveProfile(); render(); }
});

document.getElementById('hint').addEventListener('click',function(ev){
  if(ev.target.closest('#show-all')){ state.onlyFits=false; render(); }
  else if(ev.target.closest('#only-fits')){ state.onlyFits=true; render(); }
});

var mf=document.getElementById('more-filters');
mf.addEventListener('click',function(){
  var adv=document.getElementById('adv');
  var showing=adv.classList.toggle('show');
  mf.setAttribute('aria-expanded', showing?'true':'false');
  mf.textContent=showing?'Fewer filters':'More filters';
});

document.getElementById('reset').addEventListener('click',function(){
  state={q:'',engine:'',hw:'',quant:'',tier:'',fit:'',ready:'',sort:'default',open:{},onlyFits:true};
  /* The sort select has no empty option, so resetting it to '' would leave the
     control blank while the state says 'default'. Reset each to its neutral. */
  var neutral={q:'',  'f-engine':'', 'f-hw':'', 'f-quant':'', 'f-tier':'',
               'f-fit':'', 'f-ready':'', sort:'default'};
  Object.keys(neutral).forEach(function(id){ document.getElementById(id).value=neutral[id]; });
  var ea=document.getElementById('expand-all');
  if(ea) ea.textContent='Expand all';
  render();
});

var ea=document.getElementById('expand-all');
ea.addEventListener('click',function(){
  var anyClosed=D.setups.some(function(s){return !state.open[s.id];});
  state.open={};
  if(anyClosed) D.setups.forEach(function(s){state.open[s.id]=1;});
  ea.textContent=anyClosed?'Collapse all':'Expand all';
  render();
});

document.addEventListener('click',function(ev){
  if(!ev.target.closest('.term') && !ev.target.closest('#pop')) hideTerm();
});

function onOutClick(ev){
  var tm=ev.target.closest('.term');
  if(tm){ ev.preventDefault(); ev.stopPropagation(); showTerm(tm); return; }
  var cp=ev.target.closest('.copy');
  if(cp){
    ev.stopPropagation();
    var txt=cp.getAttribute('data-copy');
    if(navigator.clipboard) navigator.clipboard.writeText(txt).then(function(){
      cp.textContent='copied'; setTimeout(function(){cp.textContent='copy';},1200);
    });
    return;
  }
  var ce=ev.target.closest('#clear-empty');
  if(ce){ document.getElementById('reset').click(); return; }
  var head=ev.target.closest('.chead');
  if(!head) return;
  var art=head.closest('.card'), id=art.getAttribute('data-id');
  if(state.open[id]) delete state.open[id]; else state.open[id]=1;
  art.classList.toggle('open');
  head.setAttribute('aria-expanded', art.classList.contains('open')?'true':'false');
}
document.getElementById('out').addEventListener('click',onOutClick);
document.getElementById('rec').addEventListener('click',onOutClick);
document.getElementById('how').addEventListener('click',function(ev){
  var tm=ev.target.closest('.term');
  if(tm){ ev.preventDefault(); ev.stopPropagation(); showTerm(tm); }
});

document.getElementById('out').addEventListener('keydown',function(ev){
  if(ev.key!=='Enter'&&ev.key!==' ') return;
  var head=ev.target.closest('.chead');
  if(!head) return;
  ev.preventDefault(); head.click();
});

renderCounts(); renderPicker(); render();
})();
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()

    if not args.skip_validate:
        rc = subprocess.call([sys.executable, os.path.join(HERE, "validate.py")])
        if rc != 0:
            print("\nbuild aborted: validation failed", file=sys.stderr)
            return rc

    data = collect()
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # The dataset is inlined in a <script> block, so a literal closing tag or an
    # HTML comment opener inside a string would break out of it.
    blob = blob.replace("</", "<\\/").replace("<!--", "<\\!--")
    html = HTML.replace("__DATA_JSON__", blob)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)

    c = data["counts"]
    print(
        f"wrote {args.out} ({os.path.getsize(args.out)/1024:.0f} KB) — "
        f"{c['setups']} setups, {c['models']} model families, {c['measured']} measured on our box"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
