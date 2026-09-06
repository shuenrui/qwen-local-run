#!/usr/bin/env python3
"""Build the Qwen local-run directory into one self-contained HTML file.

Stdlib only, no build step at runtime, no backend. Reads data/*.json,
validates it, and writes site/index.html with the dataset inlined so the
page works from file:// as well as over http.

Usage:
    python3 directory/build.py                 # validate + build
    python3 directory/build.py --skip-validate # build only
    python3 directory/build.py --out /tmp/x.html
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
<title>Qwen Local-Run Directory</title>
<meta name="description" content="Every community way to run a Qwen model locally: which checkpoint, which engine, which hardware, what it measured.">
<meta property="og:title" content="Qwen Local-Run Directory">
<meta property="og:description" content="Runnable Qwen setups across DGX Spark, Macs and consumer GPUs; every number tagged box / forum / vendor with its source linked.">
<meta property="og:type" content="website">
<style>
:root{
  --bg:#fff; --fg:#16181d; --mut:#5b6472; --line:#e2e5ea; --soft:#f6f7f9;
  --box:#1b5e20; --boxbg:#e6f4e8; --forum:#8a4b00; --forumbg:#fdf0dc;
  --vendor:#0d47a1; --vendorbg:#e5eefb; --accent:#4338ca; --accentbg:#eef0ff;
  --bad:#8a1c1c; --badbg:#fbeaea;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0f1115; --fg:#e7e9ee; --mut:#98a1b0; --line:#262b34; --soft:#161a21;
  --box:#8ce0a0; --boxbg:#14291a; --forum:#f0b473; --forumbg:#2b1f10;
  --vendor:#8db8f5; --vendorbg:#12203a; --accent:#a9b4ff; --accentbg:#1b1f3d;
  --bad:#f0a0a0; --badbg:#2e1616;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}
code,kbd,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.wrap{max-width:1280px;margin:0 auto;padding:0 1rem}

header.top{border-bottom:1px solid var(--line);padding:1.4rem 0 1.1rem;background:var(--soft)}
h1{margin:0;font-size:1.55rem;letter-spacing:-.02em}
.tag{margin:.35rem 0 0;color:var(--mut);max-width:74ch;font-size:.93rem}
.counts{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.8rem}
.count{font-size:.75rem;border:1px solid var(--line);border-radius:999px;padding:.15rem .6rem;background:var(--bg);color:var(--mut)}
.count b{color:var(--fg)}

.legend{display:flex;flex-wrap:wrap;gap:.9rem;align-items:center;margin:.9rem 0 0;font-size:.8rem;color:var(--mut)}
.guide{margin:.9rem 0 0;font-size:.83rem}
.guide summary{cursor:pointer;font-weight:600}
.guide .steps{margin:.5rem 0 .6rem 1.1rem}
.guide dl{display:grid;grid-template-columns:max-content 1fr;gap:.25rem .9rem;margin:.4rem 0}
.guide dt{font-weight:600}
.guide dd{margin:0;color:var(--mut)}
@media (max-width:640px){.guide dl{grid-template-columns:1fr}.guide dt{margin-top:.3rem}}
.pill{font-size:.68rem;font-weight:700;border-radius:4px;padding:.08rem .4rem;white-space:nowrap;letter-spacing:.02em}
.p-box{background:var(--boxbg);color:var(--box)}
.p-forum{background:var(--forumbg);color:var(--forum)}
.p-vendor{background:var(--vendorbg);color:var(--vendor)}
.p-none{background:var(--soft);color:var(--mut);border:1px solid var(--line)}

.controls{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line);padding:.7rem 0}
.row1{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}
input[type=search]{flex:1 1 260px;min-width:200px;padding:.5rem .7rem;border:1px solid var(--line);
  border-radius:8px;background:var(--bg);color:var(--fg);font-size:.92rem}
input[type=search]:focus{outline:2px solid var(--accentbg);border-color:var(--accent)}
select{padding:.5rem .6rem;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font-size:.86rem;max-width:190px}
button{font:inherit;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--fg);
  border-radius:8px;padding:.45rem .8rem;font-size:.85rem}
button:hover{border-color:var(--accent)}
button.on{background:var(--accentbg);border-color:var(--accent);color:var(--accent);font-weight:600}
.hint{font-size:.78rem;color:var(--mut);margin-top:.45rem}

main{padding:1.2rem 0 3rem}
.group{margin-bottom:2rem}
.ghead{border-bottom:2px solid var(--fg);padding-bottom:.4rem;margin-bottom:.2rem;
  display:flex;flex-wrap:wrap;gap:.5rem;align-items:baseline;justify-content:space-between}
.ghead h2{margin:0;font-size:1.22rem;letter-spacing:-.01em}
.gmeta{font-size:.78rem;color:var(--mut)}
.gspecs{display:flex;flex-wrap:wrap;gap:.35rem;margin:.55rem 0 .9rem}
.spec{font-size:.74rem;border:1px solid var(--line);border-radius:6px;padding:.2rem .5rem;background:var(--soft)}
.spec b{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:.66rem;letter-spacing:.04em;margin-right:.3rem}
.gsum{font-size:.88rem;color:var(--mut);max-width:96ch;margin:0 0 .9rem}

.card{border:1px solid var(--line);border-radius:10px;margin-bottom:.6rem;background:var(--bg);overflow:hidden}
.card.dim{opacity:.62}
.chead{display:flex;gap:.75rem;align-items:flex-start;padding:.7rem .85rem;cursor:pointer}
.chead:hover{background:var(--soft)}
.cmain{flex:1 1 auto;min-width:0}
.ctitle{font-weight:650;font-size:.97rem;letter-spacing:-.01em;margin:0 0 .3rem}
.badges{display:flex;flex-wrap:wrap;gap:.3rem}
.b{font-size:.68rem;border-radius:4px;padding:.1rem .42rem;white-space:nowrap;border:1px solid var(--line);background:var(--soft);color:var(--mut)}
.b.eng{background:var(--accentbg);color:var(--accent);border-color:transparent;font-weight:600}
.b.q{font-family:ui-monospace,Menlo,monospace}
.b.fit{border-color:var(--box);color:var(--box)}
.b.nofit{border-color:var(--bad);color:var(--bad)}
.b.fork{background:var(--badbg);color:var(--bad);border-color:transparent}
.cnums{flex:0 0 auto;text-align:right;font-size:.78rem;color:var(--mut);white-space:nowrap}
.cnums b{display:block;font-size:1rem;color:var(--fg);font-variant-numeric:tabular-nums}
.exp{font-size:.9rem;color:var(--mut);transition:transform .15s}

.cbody{display:none;border-top:1px solid var(--line);padding:.85rem}
.card.open .cbody{display:block}
.card.open .exp{transform:rotate(90deg)}
.sec{margin-bottom:.9rem}
.sec:last-child{margin-bottom:0}
.sec h4{margin:0 0 .35rem;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
pre.cmd{margin:0;background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:.6rem .7rem;
  overflow-x:auto;font-size:.8rem;white-space:pre-wrap;word-break:break-word;position:relative}
.copy{position:absolute;top:.35rem;right:.35rem;font-size:.68rem;padding:.15rem .45rem}
ol.steps{margin:0;padding-left:1.2rem;font-size:.85rem}
ol.steps li{margin:.2rem 0}
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
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:.8rem}
.srclist{font-size:.8rem;display:flex;flex-wrap:wrap;gap:.4rem}
.src{border:1px solid var(--line);border-radius:6px;padding:.18rem .5rem;text-decoration:none;background:var(--soft)}
.src:hover{border-color:var(--accent)}
.src span{color:var(--mut);font-size:.7rem;margin-left:.3rem}
.kv{font-size:.83rem}
.kv div{display:flex;gap:.5rem;padding:.14rem 0;border-bottom:1px dotted var(--line)}
.kv div:last-child{border:0}
.kv dt{flex:0 0 130px;color:var(--mut)}
.kv dd{margin:0;flex:1 1 auto;min-width:0}

.empty{text-align:center;padding:3rem 1rem;color:var(--mut)}
footer{border-top:1px solid var(--line);padding:1.4rem 0 2.5rem;color:var(--mut);font-size:.8rem}
footer h3{color:var(--fg);font-size:.9rem;margin:0 0 .4rem}
footer .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1.4rem}

@media (max-width:640px){
  .chead{flex-direction:column;gap:.45rem}
  .cnums{text-align:left;display:flex;gap:1rem;flex-wrap:wrap}
  .cnums b{display:inline;font-size:.9rem;margin-right:.25rem}
  .kv div{flex-direction:column;gap:0}
  .kv dt{flex:none}
  select{max-width:100%;min-width:0;flex:1 1 130px}
}
</style>
</head>
<body>

<header class="top"><div class="wrap">
  <h1>Qwen Local-Run Directory</h1>
  <p class="tag">Every community way to run a Qwen model on hardware you own. One entry is one
  <b>runnable setup</b>: a specific checkpoint, a specific engine configuration, on specific hardware &mdash;
  because that is the unit that actually gets run and actually gets measured.</p>
  <div class="counts" id="counts"></div>
  <div class="legend">
    <strong>Every number wears its source:</strong>
    <span><span class="pill p-box">box</span> measured on our own hardware, method stated</span>
    <span><span class="pill p-forum">forum</span> reported by a community builder, linked</span>
    <span><span class="pill p-vendor">vendor</span> claimed by the publisher</span>
    <span><span class="pill p-none">unverified</span> no measurement yet</span>
  </div>
  <details class="guide">
    <summary>New to local hosting? How to read this page</summary>
    <p class="hint">Start with three questions, in this order.</p>
    <ol class="steps">
      <li><b>Will it fit my machine?</b> Use <i>Hardware</i> and <i>Memory</i> above.
        They filter by the resident footprint each setup states, so what remains
        is what your box can actually hold.</li>
      <li><b>How fast will it be?</b> Use <i>Sort: fastest decode first</i>. The big
        number on each card is decode throughput in tokens per second; the tag next
        to it says whose stopwatch that is.</li>
      <li><b>How do I run it?</b> Open a card. &ldquo;How to run it&rdquo; gives a
        copyable command or steps plus the recipe repo; &ldquo;Measurements&rdquo;
        shows every number with its fixture and source link; &ldquo;Caveats&rdquo;
        tells you what the number does <i>not</i> mean.</li>
    </ol>
    <dl>
      <dt>tok/s</dt><dd>tokens generated per second while answering &mdash; the speed you feel when text streams.</dd>
      <dt>TTFT</dt><dd>time to first token: how long before the first word appears. Grows with prompt length.</dd>
      <dt>quant / GGUF / NVFP4 / FP8 / MLX</dt><dd>compressed weight formats. Lower bits fit smaller boxes; the quality cost varies, which is why each card names its exact quant.</dd>
      <dt>MoE, active params</dt><dd>Mixture-of-Experts models wake only some parameters per token. On bandwidth-limited boxes active params, not total params, set the speed.</dd>
      <dt>MTP / DSpark / DFlash2</dt><dd>speculative decoding: a cheap draft proposes tokens the big model verifies, trading memory for speed.</dd>
      <dt>KV cache</dt><dd>memory holding the conversation so far. Long contexts and high concurrency spend it first.</dd>
      <dt>box / forum / vendor</dt><dd>who vouches for a number: measured here, reported by a linked builder, or claimed by the publisher. Never blended.</dd>
    </dl>
  </details>
</div></header>

<div class="controls"><div class="wrap">
  <div class="row1">
    <input type="search" id="q" placeholder="Search models, checkpoints, engines, publishers, commands&hellip;" aria-label="Search the directory">
    <select id="f-engine" aria-label="Filter by engine"></select>
    <select id="f-hw" aria-label="Filter by hardware"></select>
    <select id="f-quant" aria-label="Filter by quantization"></select>
    <select id="f-tier" aria-label="Filter by evidence tier">
      <option value="">Evidence: any</option>
      <option value="box">box &mdash; measured here</option>
      <option value="forum">forum &mdash; community reported</option>
      <option value="vendor">vendor &mdash; publisher claimed</option>
      <option value="none">unverified</option>
    </select>
    <select id="f-fit" aria-label="Filter by memory budget">
      <option value="">Memory: any</option>
    </select>
    <select id="sort" aria-label="Sort order">
      <option value="default">Sort: generation, then size</option>
      <option value="speed">Sort: fastest decode first</option>
      <option value="small">Sort: smallest footprint first</option>
      <option value="evidence">Sort: best evidence first</option>
      <option value="fresh">Sort: most recently updated</option>
    </select>
    <button id="expand-all" type="button">Expand all</button>
    <button id="reset" type="button">Reset</button>
  </div>
  <div class="hint" id="hint"></div>
</div></div>

<main class="wrap"><div id="out"></div></main>

<footer><div class="wrap cols">
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
    <h3>Reading a setup</h3>
    <p>A model with eight checkpoints across three engines is twenty-four setups, not one row. They
    share a model id and a checkpoint, which is how they group. The footprint shown is what stays
    <em>resident</em> &mdash; weights plus KV cache plus any draft model &mdash; which is the number that
    decides whether it fits, not the download size.</p>
    <p>Entries marked <span class="b fork">needs fork</span> cannot run on a stock engine. That is the
    weakest reproducibility tier in the directory.</p>
  </div>
  <div>
    <h3>Contributing</h3>
    <p>Each entry is one JSON file under <code>directory/data/setups/</code>. Every measurement needs a
    source URL unless it is a <code>box</code> number, in which case it needs a date, a sample count and
    a method. <code>python3 directory/validate.py</code> rejects anything else, including numbers with no
    source and setups that duplicate an existing one.</p>
    <p id="gen"></p>
  </div>
</div></footer>

<script id="data" type="application/json">__DATA_JSON__</script>
<script>
(function(){
"use strict";
var D = JSON.parse(document.getElementById('data').textContent);
var MODELS = D.models, HW = D.hardware, ENG = D.engines, PUB = D.publishers;
var TIER_RANK = {box:3, forum:2, vendor:1};

function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
function pub(id){ return (PUB[id]||{}).name || id || 'unknown'; }
function modelName(id){ return (MODELS[id]||{}).name || id; }
function engName(id){ return (ENG[id]||{}).name || id; }
function hwName(id){ return (HW[id]||{}).name || id; }
function fmtGb(v){ return v==null?'?':(v>=100?Math.round(v):Math.round(v*10)/10)+'GB'; }
function fmtCtx(n){ if(n==null) return '?'; return n>=1000000?(n/1000000)+'M':n>=1000?Math.round(n/1000)+'K':n; }

/* ---- derived helpers ---------------------------------------------------- */
function tierOf(s){
  var ms = s.measurements||[];
  if(!ms.length) return 'none';
  var best = 0, out = 'none';
  ms.forEach(function(m){ var r=TIER_RANK[m.provenance]||0; if(r>best){best=r;out=m.provenance;} });
  return out;
}
function bestSpeed(s){
  var ms=(s.measurements||[]).filter(function(m){return m.unit==='tok/s';});
  if(!ms.length) return null;
  var pref=['decode_code','decode_agg','decode_chat','decode_essay','decode_per_stream'];
  for(var i=0;i<pref.length;i++){
    var hit=ms.filter(function(m){return m.metric===pref[i];});
    if(hit.length) return {metric:pref[i], value:Math.max.apply(null,hit.map(function(m){return m.value;})),
                           prov:hit[0].provenance};
  }
  return {metric:ms[0].metric, value:ms[0].value, prov:ms[0].provenance};
}
function tierPill(t){
  if(t==='none') return '<span class="pill p-none">unverified</span>';
  return '<span class="pill p-'+t+'">'+t+'</span>';
}
function hwFit(s){
  var ids=s.hardware||[];
  var worst=null;
  ids.forEach(function(id){ var h=HW[id]; if(h&&h.memory_gb!=null){ if(worst==null||h.memory_gb<worst) worst=h.memory_gb; } });
  var need=(s.requirements||{}).memory_gb;
  if(worst==null||need==null) return null;
  return {fits: need<=worst, hwMem:worst, need:need,
          headroom: Math.round((worst-need)*10)/10};
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
  var budgets=[[24,'fits in 24GB'],[32,'fits in 32GB'],[48,'fits in 48GB'],[64,'fits in 64GB'],[128,'fits in 128GB']];
  var f=document.getElementById('f-fit');
  budgets.forEach(function(b){ var o=document.createElement('option'); o.value=b[0]; o.textContent=b[1]; f.appendChild(o); });
})();

var state={q:'',engine:'',hw:'',quant:'',tier:'',fit:'',sort:'default',open:{}};

function matches(s){
  if(state.engine && (!s.engine||s.engine.id!==state.engine)) return false;
  if(state.hw && (s.hardware||[]).indexOf(state.hw)<0) return false;
  if(state.quant && String((s.variation||{}).quant||'').toLowerCase()!==state.quant) return false;
  var t=tierOf(s);
  if(state.tier && t!==state.tier) return false;
  if(state.fit){
    var need=(s.requirements||{}).memory_gb;
    if(need==null || need>Number(state.fit)) return false;
  }
  if(state.q){
    var hay=[s.title,s.id,(s.variation||{}).checkpoint,(s.variation||{}).quant,
      (s.variation||{}).quant_detail,(s.engine||{}).config,(s.engine||{}).image,
      (s.engine||{}).draft_model,(s.run||{}).command,(s.run||{}).repo,(s.run||{}).profile,
      pub((s.variation||{}).publisher), modelName(s.model),
      (s.hardware||[]).map(hwName).join(' '),
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
      return (y?y.value:-1)-(x?x.value:-1);});
  } else if(state.sort==='small'){
    c.sort(function(a,b){return ((a.requirements||{}).memory_gb||1e9)-((b.requirements||{}).memory_gb||1e9);});
  } else if(state.sort==='evidence'){
    c.sort(function(a,b){return (TIER_RANK[tierOf(b)]||0)-(TIER_RANK[tierOf(a)]||0);});
  } else if(state.sort==='fresh'){
    c.sort(function(a,b){return String(b.updated||'').localeCompare(String(a.updated||''));});
  }
  return c;
}

/* ---- rendering ---------------------------------------------------------- */
function measurementTable(s){
  var ms=s.measurements||[];
  if(!ms.length) return '<p class="hint">No measurements recorded for this setup yet.</p>';
  var rows=ms.map(function(m){
    var extra=[];
    if(m.range) extra.push('range '+m.range[0]+'&ndash;'+m.range[1]);
    if(m.n) extra.push('n='+m.n);
    if(m.date) extra.push(m.date);
    return '<tr><td><code>'+esc(m.metric)+'</code></td>'+
      '<td class="num">'+esc(m.value)+' '+esc(m.unit||'')+'</td>'+
      '<td>'+tierPill(m.provenance)+'</td>'+
      '<td>'+esc(extra.join(' · '))+(m.method?'<br><span class="hint">'+esc(m.method)+'</span>':'')+
        (m.note?'<br><span class="hint">'+esc(m.note)+'</span>':'')+
        (m.source?'<br><a href="'+esc(m.source)+'" rel="noopener">source</a>':'')+'</td></tr>';
  }).join('');
  return '<div class="tscroll"><table class="m"><thead><tr><th>Metric</th><th>Value</th><th>Tier</th><th>Context</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
}

function card(s){
  var v=s.variation||{}, e=s.engine||{}, r=s.run||{}, req=s.requirements||{}, caps=s.capabilities||{};
  var t=tierOf(s), sp=bestSpeed(s), fit=hwFit(s);
  var isOpen=!!state.open[s.id];
  var badges=[];
  badges.push('<span class="b eng">'+esc(engName(e.id))+'</span>');
  if(v.quant) badges.push('<span class="b q">'+esc(String(v.quant).toUpperCase())+'</span>');
  (s.hardware||[]).forEach(function(h){badges.push('<span class="b">'+esc(hwName(h))+'</span>');});
  if(e.spec_decode&&e.spec_decode!=='none') badges.push('<span class="b">spec: '+esc(e.spec_decode)+'</span>');
  if(e.requires_fork) badges.push('<span class="b fork">needs fork</span>');
  if(s.builder&&PUB[s.builder]) badges.push('<span class="b">by '+esc(PUB[s.builder].name||s.builder)+'</span>');
  if(caps.vision) badges.push('<span class="b">vision</span>');
  if(caps.tools) badges.push('<span class="b">tools</span>');
  if(caps.thinking) badges.push('<span class="b">thinking</span>');
  if(fit) badges.push('<span class="b '+(fit.fits?'fit':'nofit')+'">'+(fit.fits?'fits ':'over budget ')+fmtGb(fit.need)+' / '+fmtGb(fit.hwMem)+'</span>');

  var nums='';
  if(sp) nums+='<b>'+sp.value+'</b>tok/s '+esc(sp.metric.replace('decode_',''))+' '+tierPill(sp.prov);
  else nums+='<b>&mdash;</b>no speed data';
  nums+='<br>'+fmtGb(req.memory_gb)+' resident · '+fmtGb(req.disk_gb)+' disk';

  var cmd = r.command || (r.steps||[]).join(' && ');
  var steps = (r.steps||[]).map(function(x){return '<li><code>'+esc(x)+'</code></li>';}).join('');

  var kv='';
  function add(k,val){ if(val!=null&&val!=='') kv+='<div><dt>'+k+'</dt><dd>'+val+'</dd></div>'; }
  add('Checkpoint', '<a href="'+esc(v.url)+'" rel="noopener">'+esc(v.checkpoint)+'</a>');
  add('Publisher', esc(pub(v.publisher)));
  add('Builder', s.builder&&PUB[s.builder]
      ? '<a href="'+esc(PUB[s.builder].url||v.url)+'" rel="noopener">'+esc(PUB[s.builder].name||s.builder)+'</a> &mdash; recipe and numbers by this builder'
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
  add('Auto-bootable', r.auto_bootable===false?'No &mdash; manual-only lane':(r.auto_bootable===true?'Yes':null));
  add('Downloads', v.downloads!=null?Number(v.downloads).toLocaleString():null);

  var srcs=(s.sources||[]).map(function(x){
    return '<a class="src" href="'+esc(x.url)+'" rel="noopener">'+esc(x.kind)+'<span>'+esc(x.note||'')+
      '</span></a>';}).join(' ');

  var cav=(s.caveats||[]).map(function(c){return '<div class="warn">'+esc(c)+'</div>';}).join('');

  var eg = ENG[e.id]||{};
  var gotchas = (eg.gotchas||[]).slice(0,3).map(function(g){return '<li>'+esc(g)+'</li>';}).join('');

  return '<article class="card'+(isOpen?' open':'')+'" data-id="'+esc(s.id)+'">'+
    '<div class="chead" role="button" tabindex="0" aria-expanded="'+(isOpen?'true':'false')+'">'+
      '<div class="cmain"><p class="ctitle">'+esc(s.title)+' '+tierPill(t)+'</p>'+
        '<div class="badges">'+badges.join('')+'</div></div>'+
      '<div class="cnums">'+nums+'</div>'+
      '<div class="exp" aria-hidden="true">&#9654;</div>'+
    '</div>'+
    '<div class="cbody">'+
      (s.slug_note?'<p class="gsum">'+esc(s.slug_note)+'</p>':'')+
      '<div class="sec"><h4>How to run it</h4>'+
        (cmd?'<pre class="cmd">'+esc(cmd)+'<button class="copy" type="button" data-copy="'+esc(cmd)+'">copy</button></pre>':'')+
        (steps?'<ol class="steps" style="margin-top:.5rem">'+steps+'</ol>':'')+
        (r.repo?'<p class="hint" style="margin-top:.4rem">Recipe: <a href="'+esc(r.repo)+'" rel="noopener">'+esc(r.repo)+'</a></p>':'')+
      '</div>'+
      '<div class="sec"><h4>Details</h4><div class="kv">'+kv+'</div></div>'+
      '<div class="sec"><h4>Measurements</h4>'+measurementTable(s)+'</div>'+
      (cav?'<div class="sec"><h4>Caveats</h4>'+cav+'</div>':'')+
      (gotchas?'<div class="sec"><h4>Engine gotchas ('+esc(engName(e.id))+')</h4><ul class="notes">'+gotchas+'</ul></div>':'')+
      '<div class="sec"><h4>Sources</h4><div class="srclist">'+srcs+'</div>'+
        '<p class="hint" style="margin-top:.4rem">Last updated '+esc(s.updated||'unknown')+'</p></div>'+
    '</div></article>';
}

function group(s){
  var m=MODELS[s.model]||{};
  var a=m.architecture||{}, c=m.context||{};
  var specs=[];
  function sp(k,val){ if(val!=null&&val!=='') specs.push('<span class="spec"><b>'+k+'</b>'+esc(val)+'</span>'); }
  sp('params', a.params_total_b!=null?(a.kind==='moe'?(a.params_total_b+'B total / '+a.params_active_b+'B active'):(a.params_total_b+'B dense')):null);
  sp('shape', a.kind==='moe'?'MoE':'dense');
  if(a.hybrid) sp('arch','GDN hybrid');
  if(a.mtp_head) sp('MTP head','yes');
  sp('context', fmtCtx(c.native)+(c.max&&c.max!==c.native?' &rarr; '+fmtCtx(c.max):''));
  sp('sees', (m.modalities||[]).join(' + '));
  sp('license', m.license);
  sp('released', m.released);

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

function render(){
  var list=D.setups.filter(matches);
  list=sortSetups(list);

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
    out.innerHTML='<div class="empty"><p><b>No setups match those filters.</b></p>'+
      '<p>Loosen the search or hit Reset. The directory only lists setups with a verified source.</p></div>';
  } else {
    out.innerHTML=order.map(function(id){ return group({model:id, items:byModel[id]}); }).join('');
  }

  var measured=list.filter(function(s){return tierOf(s)==='box';}).length;
  var forum=list.filter(function(s){return tierOf(s)==='forum';}).length;
  var vendor=list.filter(function(s){return tierOf(s)==='vendor';}).length;
  var none=list.filter(function(s){return tierOf(s)==='none';}).length;
  document.getElementById('hint').innerHTML =
    '<b>'+list.length+'</b> of '+D.setups.length+' setups shown &middot; '+order.length+' model families &middot; '+
    tierPill('box')+' '+measured+' &nbsp;'+tierPill('forum')+' '+forum+' &nbsp;'+
    tierPill('vendor')+' '+vendor+' &nbsp;'+tierPill('none')+' '+none;
}

function renderCounts(){
  var c=D.counts;
  document.getElementById('counts').innerHTML=[
    ['setups',c.setups],['models',c.models],['hardware',c.hardware],
    ['engines',c.engines],['publishers',c.publishers],['measured on our box',c.measured]
  ].map(function(p){return '<span class="count"><b>'+p[1]+'</b> '+esc(p[0])+'</span>';}).join('');
  document.getElementById('gen').textContent='Dataset generated '+D.generated+'.';
}

/* ---- events ------------------------------------------------------------- */
function bind(id,key,ev){
  var el=document.getElementById(id);
  el.addEventListener(ev||'input',function(){ state[key]=el.value; render(); });
}
bind('q','q'); bind('f-engine','engine','change'); bind('f-hw','hw','change');
bind('f-quant','quant','change'); bind('f-tier','tier','change');
bind('f-fit','fit','change'); bind('sort','sort','change');

document.getElementById('reset').addEventListener('click',function(){
  state={q:'',engine:'',hw:'',quant:'',tier:'',fit:'',sort:'default',open:{}};
  /* The sort select has no empty option, so resetting it to '' would leave the
     control blank while the state says 'default'. Reset each to its neutral. */
  var neutral={q:'',  'f-engine':'', 'f-hw':'', 'f-quant':'', 'f-tier':'',
               'f-fit':'', sort:'default'};
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

document.getElementById('out').addEventListener('click',function(ev){
  var cp=ev.target.closest('.copy');
  if(cp){
    ev.stopPropagation();
    var txt=cp.getAttribute('data-copy');
    if(navigator.clipboard) navigator.clipboard.writeText(txt).then(function(){
      cp.textContent='copied'; setTimeout(function(){cp.textContent='copy';},1200);
    });
    return;
  }
  var head=ev.target.closest('.chead');
  if(!head) return;
  var art=head.closest('.card'), id=art.getAttribute('data-id');
  if(state.open[id]) delete state.open[id]; else state.open[id]=1;
  art.classList.toggle('open');
  head.setAttribute('aria-expanded', art.classList.contains('open')?'true':'false');
});

document.getElementById('out').addEventListener('keydown',function(ev){
  if(ev.key!=='Enter'&&ev.key!==' ') return;
  var head=ev.target.closest('.chead');
  if(!head) return;
  ev.preventDefault(); head.click();
});

renderCounts(); render();
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
        f"{c['setups']} setups, {c['models']} models, {c['measured']} measured on our box"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
