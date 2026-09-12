/* Qwen Local-Run Directory — application.
   Hash-routed, no dependencies, no network requests after load.
   See docs/redesign-2026-09-10/ for the design this implements. */
(function () {
"use strict";

var D = JSON.parse(document.getElementById("data").textContent);
var MODELS = D.models, ENG = D.engines, HW = D.hardware, PUB = D.publishers;
var SETUPS = D.setups;
var TODAY = new Date(D.generated + "T00:00:00Z");

/* ---------------------------------------------------------------- helpers */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
// NB: any string passed through esc() must use literal Unicode, never an HTML
// entity — esc() escapes the ampersand and the entity would leak to the page.
function el(id) { return document.getElementById(id); }
function na(t) { return '<span class="na">' + esc(t || "not recorded") + "</span>"; }
function modelOf(s) { return MODELS[s.model] || {}; }
function engOf(s) { return ENG[(s.engine || {}).id] || {}; }
function pubName(id) { return (PUB[id] || {}).name || id || "unknown"; }
function gb(v) { return v == null ? null : (v >= 100 ? Math.round(v) : Math.round(v * 10) / 10) + " GB"; }
function ctx(n) {
  if (n == null) return null;
  return n >= 1000000 ? (Math.round(n / 100000) / 10) + "M" : n >= 1000 ? Math.round(n / 1024) + "K" : String(n);
}
function tail(cp) { var p = String(cp || "").split("/"); return p[p.length - 1] || cp; }
function days(iso) {
  if (!iso) return null;
  var d = new Date(iso + "T00:00:00Z");
  return Math.round((TODAY - d) / 86400000);
}
function plural(n, one, many) { return n + " " + (n === 1 ? one : many || one + "s"); }
function uniq(a) { var s = []; a.forEach(function (x) { if (x != null && s.indexOf(x) < 0) s.push(x); }); return s; }

/* ------------------------------------------------------------ derivations */
/* Every value below is computed from recorded data and labelled as derived
   wherever it is shown. Nothing here invents a measurement. */

var EASE = { ollama: 1, "lm-studio": 1, "llama-cpp": 2, "mlx-lm": 2, vllm: 3, sglang: 3, "custom-fork": 4 };

function complexity(s) {
  var e = s.engine || {}, n = EASE[e.id] != null ? EASE[e.id] : 3;
  if (e.requires_fork) n += 1;
  if (((s.run || {}).steps || []).length > 4) n += 1;
  if (e.draft_model) n += 1;
  return n;
}
function complexityWord(s) {
  var n = complexity(s);
  return n <= 2 ? "one command" : n <= 4 ? "moderate setup" : "involved build";
}
function readiness(s) {
  var r = s.run || {}, steps = r.steps || [];
  if (r.command) return "runnable";
  if (steps.length >= 2) return "recipe";
  return "lead";
}
var READY_WORD = { runnable: "runnable", recipe: "recipe only", lead: "lead only" };
var READY_GLYPH = { runnable: "●", recipe: "◔", lead: "○" };

function speeds(s) {
  return (s.measurements || []).filter(function (m) {
    return m.unit === "tok/s" && String(m.metric || "").indexOf("decode") === 0;
  });
}
function isSingle(m) { return m.concurrency == null || m.concurrency <= 1; }

/* Single-stream always wins the headline; aggregate is never promoted into it. */
function repDecode(s) {
  var rows = speeds(s).filter(isSingle);
  var pref = ["decode_chat", "decode_code", "decode_essay", "decode_per_stream"];
  for (var i = 0; i < pref.length; i++) {
    var c = rows.filter(function (m) { return m.metric === pref[i]; });
    if (!c.length) continue;
    var nonPeak = c.filter(function (m) { return m.stat !== "peak"; });
    return (nonPeak.length ? nonPeak : c).sort(function (a, b) { return b.value - a.value; })[0];
  }
  return null;
}
function aggDecode(s) {
  var a = speeds(s).filter(function (m) { return m.metric === "decode_agg"; });
  return a.length ? a.sort(function (x, y) { return y.value - x.value; })[0] : null;
}
function perStreamAtLoad(s, conc) {
  var rows = (s.measurements || []).filter(function (m) {
    return m.metric === "decode_per_stream" && m.concurrency != null && m.concurrency > 1 &&
      (conc == null || m.concurrency === conc);
  });
  return rows.length ? rows[0] : null;
}
var METRIC_WORD = {
  decode_chat: "chat", decode_code: "code", decode_essay: "essay",
  decode_per_stream: "per stream", decode_agg: "aggregate",
  prefill_tok_s: "prefill", ttft_ms: "time to first token", task_time_min: "task time",
  quality_index: "quality index", bench_code: "code benchmark", bench_toolcall: "tool-call benchmark",
  bench_mmlu: "MMLU", bench_gsm8k: "GSM8K", bench_humaneval: "HumanEval", bench_other: "benchmark",
  memory_gb: "resident memory", disk_gb: "disk"
};
function metricWord(m) { return METRIC_WORD[m] || m; }
function condOf(m) {
  var bits = [metricWord(m.metric)];
  if (m.stat) bits.push(m.stat);
  if (m.concurrency != null) bits.push(m.concurrency === 1 ? "1 stream" : m.concurrency + " streams");
  else if (String(m.metric).indexOf("decode") === 0) bits.push("streams unstated");
  bits.push(m.provenance);
  return bits.join(" · ");
}

function freshness(s) {
  var d = days(s.updated);
  if (d == null) return { word: "date unrecorded", level: "none" };
  if (d <= 90) return { word: "fresh", level: "ok" };
  if (d <= 180) return { word: "aging", level: "est" };
  return { word: "stale", level: "warn" };
}

var OS_BY_ARCH = [
  [/arm64, Metal/i, "macos"],
  [/aarch64|x86_64/i, "linux"]
];
function impliedOS(s) {
  var out = [];
  (s.hardware || []).forEach(function (id) {
    var a = (HW[id] || {}).arch || "";
    for (var i = 0; i < OS_BY_ARCH.length; i++) {
      if (OS_BY_ARCH[i][0].test(a)) { if (out.indexOf(OS_BY_ARCH[i][1]) < 0) out.push(OS_BY_ARCH[i][1]); break; }
    }
  });
  return out;
}

var MODALITY_CAP = { image: "vision", video: "video", audio: "audio" };
function capConflicts(s) {
  var m = modelOf(s), caps = s.capabilities || {}, out = [];
  (m.modalities || []).forEach(function (mod) {
    var key = MODALITY_CAP[mod];
    if (key && caps[key] === false) out.push(key);
  });
  return out;
}

var FAIL_RE = /\bcorrupts?\b|\bcrash(es|ed)?\b|\bOOM\b|\bfails?\b|\bbroken\b|does not work|unsupported|silently/i;
// A caveat that reports a failure as fixed is not a live failure. Prose matching
// is a stopgap until the schema carries structured failure records.
var FIXED_RE = /\bwas gone\b|\bno longer\b|\bfixed\b|\bresolved\b|which proved|\bproved the\b|without a reboot/i;
function failures(s) {
  return (s.caveats || []).filter(function (c) { return FAIL_RE.test(c) && !FIXED_RE.test(c); });
}

/* ---- the four confidence dimensions. Never averaged, never summed. ---- */
var LV = {
  ok: { cls: "v-ok", g: "●" }, mid: { cls: "v-ok", g: "◑" },
  est: { cls: "v-est", g: "◐" }, weak: { cls: "v-est", g: "◔" },
  none: { cls: "v-none", g: "○" }, bad: { cls: "v-bad", g: "✕" }
};
function confRecipe(s) {
  var r = s.run || {}, req = s.requirements || {};
  if (r.verified_clean_install) return { k: "ok", t: "Clean-install tested", why: "a source records a verified clean install" };
  var complete = r.repo && (r.command || (r.steps || []).length >= 2) && req.memory_gb != null;
  if (complete) return { k: "mid", t: "Complete community recipe", why: "repository, run instructions and a recorded memory requirement" };
  return { k: "est", t: "Incomplete recipe", why: "a sourced lane missing run instructions or a memory requirement" };
}
function confCompat(s) {
  var hw = s.hardware || [];
  if (failures(s).some(function (c) { return /unsupported|does not work/i.test(c); }))
    return { k: "bad", t: "Unsupported on a recorded path", why: "a caveat records a path that does not run" };
  var exact = hw.some(function (id) { return (HW[id] || {}).measured_by_us === true; });
  var measured = (s.measurements || []).length > 0;
  if (exact && measured) return { k: "ok", t: "Exact-device evidence", why: "measured on a single-SKU class the owner runs" };
  if (measured) return { k: "mid", t: "Similar-device evidence", why: "measured on a hardware class, not a single device" };
  if ((s.requirements || {}).memory_gb != null) return { k: "est", t: "Estimated", why: "a recorded memory requirement, but no measurement on this hardware" };
  return { k: "none", t: "Unknown", why: "no measurement and no recorded requirement" };
}
function confPerf(s) {
  var sp = speeds(s);
  if (!sp.length) return { k: "none", t: "Unknown", why: "no speed measurement" };
  var box = sp.filter(function (m) { return m.provenance === "box"; });
  if (box.some(function (m) { return (m.n || 0) > 1 && m.method; }))
    return { k: "ok", t: "Controlled repeated measurement", why: "owner-measured, repeated, with a stated method" };
  var forum = sp.filter(function (m) { return m.provenance === "forum"; });
  if (forum.some(function (m) { return (m.n || 0) > 1 || m.stat; }))
    return { k: "mid", t: "Repeated community measurement", why: "a community result over a stated sample or statistic" };
  if (box.length) return { k: "mid", t: "Repeated community measurement", why: "owner-measured but a single run — the record's own caveat calls it indicative" };
  if (forum.length) return { k: "est", t: "Single community report", why: "one builder's reported figure" };
  return { k: "weak", t: "Vendor claim", why: "the publisher's own claim" };
}
function confCap(s) {
  var caps = s.capabilities || {}, m = modelOf(s), e = engOf(s);
  if (caps.tools == null && caps.thinking == null && caps.vision == null)
    return { k: "none", t: "Unknown", why: "the recipe records no capability flags" };
  if (capConflicts(s).length)
    return { k: "weak", t: "Partial", why: "the model supports a modality this runtime does not implement" };
  var feats = (e.features || []).join(" ");
  var corroborated = caps.vision === true ? /vision/.test(feats) : true;
  if (corroborated && (caps.tools != null || caps.thinking != null))
    return { k: "mid", t: "Runtime-declared", why: "recipe flags corroborated by the engine's own feature list" };
  return { k: "est", t: "Model-declared", why: "only the model card supports this claim" };
}
function conf(s) {
  if (!s.__conf) s.__conf = { r: confRecipe(s), c: confCompat(s), p: confPerf(s), a: confCap(s) };
  return s.__conf;
}
var CONF_RANK = { ok: 5, mid: 4, est: 3, weak: 2, none: 1, bad: 0 };
function confScore(s) {
  var c = conf(s);
  return CONF_RANK[c.r.k] * 1e6 + CONF_RANK[c.c.k] * 1e4 + CONF_RANK[c.p.k] * 1e2 + CONF_RANK[c.a.k];
}
var DIMS = [["r", "Recipe"], ["c", "Compatibility"], ["p", "Performance"], ["a", "Capability"]];
function evStrip(s) {
  var c = conf(s), cells = "", label = [];
  DIMS.forEach(function (d) {
    var v = c[d[0]], l = LV[v.k];
    cells += '<i class="' + l.cls + '" aria-hidden="true">' + l.g + "</i>";
    label.push(d[1] + ": " + v.t);
  });
  return '<button type="button" class="ev" data-ev="' + esc(s.id) + '" aria-label="' + esc(label.join(". ") + ".") + '">' +
    cells + "</button>";
}

/* searchable blob */
function blob(s) {
  if (s.__blob) return s.__blob;
  var m = modelOf(s), v = s.variation || {}, e = s.engine || {}, r = s.run || {};
  var parts = [s.id, s.title, s.slug_note, m.name, m.family, m.generation, v.checkpoint,
    v.quant, v.quant_detail, v.format, pubName(v.publisher), pubName(s.builder),
    (ENG[e.id] || {}).name, e.id, e.config, e.spec_decode, e.draft_model, (e.flags || []).join(" "),
    r.command, (r.steps || []).map(function (x) { return x.text; }).join(" "),
    (s.hardware || []).map(function (h) { return (HW[h] || {}).name; }).join(" "),
    (s.caveats || []).join(" "),
    (s.measurements || []).map(function (x) { return [x.metric, x.method, x.note].join(" "); }).join(" ")];
  s.__blob = parts.join(" ").toLowerCase();
  return s.__blob;
}

/* ------------------------------------------------------------- app state */
var state = {
  route: "models-home", params: {}, q: "",
  f: {}, sort: "updated", adv: false, flat: false,
  expanded: {}, compare: [], profile: null,
  modelQ: "", modelGen: "", modelArch: "", modelBaseline: "", selectedModel: null,
  assume: { context: 8192, concurrency: 1, reserve: null },
  mobile: false
};
var MOBILE = window.matchMedia("(max-width: 719px)");
state.mobile = MOBILE.matches;

function store(k, v) { try { if (v === undefined) return JSON.parse(localStorage.getItem(k)); localStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } }
function sess(k, v) { try { if (v === undefined) return JSON.parse(sessionStorage.getItem(k)); sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) { return null; } }

function setupById(id) { return SETUPS.filter(function (s) { return s.id === id; })[0] || null; }
function baselineSetup(m) {
  var b = (m || {}).practical_baseline || {};
  return b.status === "selected" ? setupById(b.setup) : null;
}
function modelRecipes(mid) { return SETUPS.filter(function (s) { return s.model === mid; }); }
function modelSearchBlob(m) {
  var a = m.architecture || {};
  return [m.id, m.name, m.family, m.generation, a.kind, a.params_total_b,
    a.params_active_b, (m.modalities || []).join(" "), m.summary].join(" ").toLowerCase();
}

/* ------------------------------------------------------------- filtering */
var FACETS = {
  gen: { label: "Generation", get: function (s) { return String(modelOf(s).generation || ""); } },
  arch: { label: "Architecture", get: function (s) { return (modelOf(s).architecture || {}).kind || ""; } },
  engine: { label: "Engine", get: function (s) { return (s.engine || {}).id || ""; }, name: function (v) { return (ENG[v] || {}).name || v; } },
  quant: { label: "Quantization", get: function (s) { return (s.variation || {}).quant || ""; } },
  hw: { label: "Tested on", get: function (s) { return s.hardware || []; }, name: function (v) { return (HW[v] || {}).name || v; } },
  evid: { label: "Evidence", get: function (s) { return s.provenance_tier || "none"; },
    name: function (v) { return { box: "owner-measured", forum: "community-reported", vendor: "vendor claim", none: "no measurement" }[v] || v; } },
  ready: { label: "Ready", get: function (s) { return readiness(s); }, name: function (v) { return READY_WORD[v] || v; } },
  family: { label: "Family", get: function (s) { return s.model; }, name: function (v) { return (MODELS[v] || {}).name || v; } },
  format: { label: "Artifact format", get: function (s) { return (s.variation || {}).format || ""; } },
  os: { label: "Operating system", get: function (s) { return impliedOS(s); },
    name: function (v) { return { macos: "macOS (implied)", linux: "Linux (implied)" }[v] || v; } },
  fork: { label: "Engine build", get: function (s) { return (s.engine || {}).requires_fork ? "fork" : "stock"; },
    name: function (v) { return v === "fork" ? "custom fork required" : "stock engine"; } },
  spec: { label: "Speculative decoding", get: function (s) { return (s.engine || {}).spec_decode || "none"; } },
  cplx: { label: "Setup complexity", get: function (s) { var n = complexity(s); return n <= 2 ? "easy" : n <= 4 ? "moderate" : "involved"; },
    name: function (v) { return { easy: "one command", moderate: "moderate setup", involved: "involved build" }[v] || v; } },
  perf: { label: "Has speed data", get: function (s) { return speeds(s).length ? "yes" : "no"; },
    name: function (v) { return v === "yes" ? "has a speed measurement" : "no speed measurement"; } },
  pub: { label: "Publisher or builder", get: function (s) { return uniq([(s.variation || {}).publisher, s.builder]); },
    name: function (v) { return pubName(v); } },
  fresh: { label: "Maintenance", get: function (s) { return freshness(s).word; } },
  fail: { label: "Known failure", get: function (s) { return failures(s).length ? "yes" : "no"; },
    name: function (v) { return v === "yes" ? "records a known failure" : "no failure recorded"; } },
  cap: { label: "Capability", get: function (s) {
      var c = s.capabilities || {}, out = [];
      ["vision", "video", "tools", "thinking"].forEach(function (k) { if (c[k] === true) out.push(k); });
      if (capConflicts(s).length) out.push("disabled-by-runtime");
      return out;
    }, name: function (v) { return v === "disabled-by-runtime" ? "a capability disabled by the runtime" : v; } }
};
var COMMON = ["gen", "arch", "engine", "quant", "hw", "evid", "ready"];
var ADVANCED = ["family", "cap", "format", "os", "fork", "spec", "cplx", "perf", "pub", "fresh", "fail"];

function facetValues(key) {
  var f = FACETS[key], counts = {};
  SETUPS.forEach(function (s) {
    var v = f.get(s);
    (Array.isArray(v) ? v : [v]).forEach(function (x) { if (x !== "" && x != null) counts[x] = (counts[x] || 0) + 1; });
  });
  return Object.keys(counts).sort(function (a, b) {
    if (key === "gen") return parseFloat(b) - parseFloat(a);
    return counts[b] - counts[a] || String(a).localeCompare(String(b));
  }).map(function (v) { return { v: v, n: counts[v], name: (f.name ? f.name(v) : v) }; });
}
function facetName(key, v) { var f = FACETS[key]; return f.name ? f.name(v) : v; }

function matches(s) {
  if (state.q) {
    var b = blob(s), terms = state.q.toLowerCase().split(/\s+/).filter(Boolean);
    for (var i = 0; i < terms.length; i++) if (b.indexOf(terms[i]) < 0) return false;
  }
  for (var k in state.f) {
    if (!state.f[k]) continue;
    var got = FACETS[k].get(s);
    got = Array.isArray(got) ? got : [got];
    if (got.indexOf(state.f[k]) < 0) return false;
  }
  if (state.f.pmin || state.f.pmax) {
    var p = (modelOf(s).architecture || {}).params_total_b;
    if (p == null) return false;
    if (state.f.pmin && p < +state.f.pmin) return false;
    if (state.f.pmax && p > +state.f.pmax) return false;
  }
  return true;
}
function activeFilters() {
  var out = [];
  Object.keys(state.f).forEach(function (k) {
    if (!state.f[k]) return;
    if (k === "pmin") out.push({ k: k, label: "Min params", val: state.f[k] + "B" });
    else if (k === "pmax") out.push({ k: k, label: "Max params", val: state.f[k] + "B" });
    else out.push({ k: k, label: FACETS[k].label, val: facetName(k, state.f[k]) });
  });
  return out;
}

var SORTS = {
  updated: { label: "Recently updated", key: function (s) { return -(days(s.updated) == null ? 1e9 : days(s.updated)); } },
  generation: { label: "Model generation", key: function (s) { var m = modelOf(s); return parseFloat(m.generation || 0) * 1e4 + ((m.architecture || {}).params_total_b || 0); } },
  size: { label: "Model size", key: function (s) { return (modelOf(s).architecture || {}).params_total_b || 0; } },
  easiest: { label: "Easiest to run", key: function (s) { return -complexity(s) * 10 - ((s.run || {}).command ? 0 : 1); } },
  complete: { label: "Most complete", key: function (s) {
      var r = s.run || {}, n = 0;
      if (r.command) n += 3; n += Math.min((r.steps || []).length, 6);
      if ((s.requirements || {}).memory_gb != null) n += 2;
      if ((s.requirements || {}).disk_gb != null) n += 1;
      if ((s.sources || []).length) n += Math.min(s.sources.length, 3);
      return n;
    } },
  evidence: { label: "Strongest evidence", key: confScore },
  measured: { label: "Most measured", key: function (s) { return (s.measurements || []).length; } },
  speed: { label: "Decode speed", key: function (s) { var r = repDecode(s); return r ? r.value : -1; } },
  footprint: { label: "Smallest footprint", key: function (s) { var m = (s.requirements || {}).memory_gb; return m == null ? -1e6 : -m; } }
};
function sorted(list) {
  var k = SORTS[state.sort] ? state.sort : "updated", f = SORTS[k].key;
  return list.slice().sort(function (a, b) {
    var d = f(b) - f(a);
    if (d) return d;
    return String(a.title).localeCompare(String(b.title));
  });
}

/* ----------------------------------------------------------- shared bits */
function copyBtn(text, label) {
  return '<button type="button" class="copy" data-copy="' + esc(text) + '">' + esc(label || "copy") + "</button>";
}
function cmdBlock(text) {
  return '<div class="cmd"><code>' + esc(text) + "</code>" + copyBtn(text) + "</div>";
}
function stepsHtml(s) {
  var steps = (s.run || {}).steps || [];
  if (!steps.length) return '<p class="prose">' + esc("No ordered steps are recorded for this recipe. The linked repository is the source.") + "</p>";
  return '<ol class="steps">' + steps.map(function (x) {
    if (x.kind === "cmd") return "<li>" + cmdBlock(x.text) + "</li>";
    return '<li><span class="do">' + esc(x.text) + "</span></li>";
  }).join("") + "</ol>";
}
function capLine(s) {
  var c = s.capabilities || {}, m = modelOf(s), out = [];
  ["vision", "video", "audio", "tools", "thinking"].forEach(function (k) {
    if (c[k] === true) out.push('<span class="mark m-ok">' + esc("● " + k) + "</span>");
    else if (c[k] === false) {
      var conflict = capConflicts(s).indexOf(k) >= 0;
      if (conflict) out.push('<span class="mark m-bad">' + esc("✕ " + k + " off (runtime)") + "</span>");
    } else if (c[k] === undefined || c[k] === null) {
      out.push('<span class="mark m-none">' + esc("○ " + k + " unknown") + "</span>");
    }
  });
  var mods = (m.modalities || []).join(" · ");
  return '<div class="kv"><dt>Model capability</dt><dd>' + (mods ? esc(mods) : na()) +
    '</dd><dt>This recipe</dt><dd style="display:flex;gap:5px;flex-wrap:wrap">' + (out.join("") || na("nothing recorded")) + "</dd></div>";
}
function measurementTable(s) {
  var ms = s.measurements || [];
  if (!ms.length) return '<p class="prose">' + esc("No measurements are recorded. This is a sourced runnable lane, not a measured result.") + "</p>";
  var order = { box: 0, forum: 1, vendor: 2 };
  var rows = ms.slice().sort(function (a, b) { return (order[a.provenance] || 9) - (order[b.provenance] || 9); });
  var out = '<div class="scrollx"><table class="mtab"><thead><tr><th>Metric</th><th>Value</th>' +
    "<th>Conditions</th><th>Method</th><th>Date</th><th>Source</th></tr></thead><tbody>";
  var lastTier = null;
  rows.forEach(function (m) {
    if (m.provenance !== lastTier) {
      lastTier = m.provenance;
      out += '<tr><td colspan="6" class="tier-band">' + esc({
        box: "Owner-measured (box)", forum: "Community-reported (forum)", vendor: "Vendor claim"
      }[m.provenance] || m.provenance) + "</td></tr>";
    }
    var cond = [];
    if (m.stat) cond.push(m.stat);
    if (m.concurrency != null) cond.push(m.concurrency === 1 ? "1 stream" : m.concurrency + " streams");
    if (m.n != null) cond.push("n=" + m.n);
    if (m.range) cond.push("range " + m.range[0] + "–" + m.range[1]);
    out += "<tr><td>" + esc(metricWord(m.metric)) + '</td><td class="v">' + esc(m.value) +
      ' <span class="g">' + esc(m.unit) + "</span></td><td>" + (cond.length ? esc(cond.join(" · ")) : na("unstated")) +
      "</td><td>" + (m.method ? esc(m.method) : na("unstated")) +
      "</td><td>" + (m.date ? esc(m.date) : na("undated")) + '</td><td><span class="tier t-' + esc(m.provenance) + '">' +
      esc(m.provenance) + "</span>" + (m.source ? ' <a href="' + esc(m.source) + '" target="_blank" rel="noopener">link</a>' : "") + "</td></tr>";
    if (m.note) out += '<tr><td colspan="6" class="g" style="padding-top:0">' + esc(m.note) + "</td></tr>";
  });
  return out + "</tbody></table></div>";
}
function aggNote(s) {
  var a = aggDecode(s);
  if (!a) return "";
  var ps = perStreamAtLoad(s, a.concurrency);
  var t = a.value + " tok/s across " + (a.concurrency != null ? a.concurrency + " streams" : "an unstated number of streams");
  if (ps) t += " — " + ps.value + " tok/s each at that load";
  return '<p class="prose" style="margin-top:6px">' + esc(t + ".") + "</p>";
}
function sourcesHtml(s) {
  return '<div class="srcs">' + (s.sources || []).map(function (x) {
    return '<div><span class="srck">' + esc(x.kind || "source") + '</span><a href="' + esc(x.url) +
      '" target="_blank" rel="noopener">' + esc(x.url) + "</a>" + (x.note ? ' <span class="g">' + esc("— " + x.note) + "</span>" : "") + "</div>";
  }).join("") + "</div>";
}

/* the detail body, shared by the in-place expansion and the recipe page */
function detailBody(s, opts) {
  opts = opts || {};
  var H = opts.page ? "h2" : "h3";
  var v = s.variation || {}, e = s.engine || {}, r = s.run || {}, req = s.requirements || {}, m = modelOf(s);
  var fails = failures(s), cav = (s.caveats || []).filter(function (c) { return fails.indexOf(c) < 0; });
  var h = "";

  h += '<div class="sec"><' + H + '>What this runs</' + H + '><p class="prose">' + esc(s.slug_note || "") + "</p>" +
    '<div class="kv" style="margin-top:9px">' +
    "<dt>Model</dt><dd><a href=\"#/models/" + esc(s.model) + '">' + esc(m.name || s.model) + "</a> " +
    '<span class="g">' + esc((m.architecture || {}).kind || "") + "</span></dd>" +
    '<dt>Checkpoint</dt><dd><span class="mono">' + esc(v.checkpoint) + "</span>" +
    (v.url ? ' <a href="' + esc(v.url) + '" target="_blank" rel="noopener">card</a>' : "") + "</dd>" +
    "<dt>Publisher</dt><dd><a href=\"#/publishers/" + esc(v.publisher) + '">' + esc(pubName(v.publisher)) + "</a>" +
    (s.builder ? ' <span class="g">' + esc("· recipe by ") + "</span><a href=\"#/publishers/" + esc(s.builder) + '">' + esc(pubName(s.builder)) + "</a>" : "") + "</dd>" +
    "<dt>Quantization</dt><dd>" + esc(v.quant) + (v.quant_detail ? ' <span class="g">' + esc("— " + v.quant_detail) + "</span>" : "") + "</dd>" +
    "<dt>Artifact</dt><dd>" + esc(v.format) + " · " + (gb(v.size_gb) || na()) + " · " + esc(v.license || "license not recorded") + "</dd>" +
    "</div></div>";

  h += '<div class="sec"><' + H + '>How to run it</' + H + '>';
  if (r.command) h += cmdBlock(r.command);
  else h += '<p class="prose">' + esc("No single copyable command is recorded. Follow the ordered steps below.") + "</p>";
  h += stepsHtml(s);
  h += '<div class="kv" style="margin-top:9px"><dt>Repository</dt><dd><a href="' + esc(r.repo) + '" target="_blank" rel="noopener">' + esc(r.repo) + "</a></dd>" +
    (r.profile ? "<dt>Profile</dt><dd><span class=\"mono\">" + esc(r.profile) + "</span></dd>" : "") +
    "<dt>Setup complexity</dt><dd>" + esc(complexityWord(s)) + ' <span class="g">' + esc("(derived — see methodology)") + "</span></dd></div></div>";

  h += '<div class="sec"><' + H + '>Requirements and runtime</' + H + '><div class="kv">' +
    "<dt>Resident memory</dt><dd>" + (gb(req.memory_gb) || na()) + "</dd>" +
    "<dt>Disk</dt><dd>" + (gb(req.disk_gb) || na()) + "</dd>" +
    (req.min_vram_gb != null ? "<dt>Min VRAM</dt><dd>" + gb(req.min_vram_gb) + "</dd>" : "") +
    (req.notes ? "<dt>Notes</dt><dd>" + esc(req.notes) + "</dd>" : "") +
    "<dt>Engine</dt><dd><a href=\"" + esc((ENG[e.id] || {}).url || "#/methodology") + '" target="_blank" rel="noopener">' + esc((ENG[e.id] || {}).name || e.id) + "</a>" +
    (e.requires_fork ? ' <span class="mark m-warn">' + esc("⤴ custom fork required") + "</span>" : ' <span class="g">' + esc("stock") + "</span>") + "</dd>" +
    "<dt>Engine version</dt><dd>" + (e.version ? esc(e.version) : na("not recorded — the schema has no field for it yet")) + "</dd>" +
    "<dt>Configuration</dt><dd>" + esc(e.config || "") + "</dd>" +
    "<dt>Speculative decoding</dt><dd>" + esc(e.spec_decode || "none") + (e.draft_model ? ' <span class="mono">' + esc(e.draft_model) + "</span>" : "") + "</dd>" +
    (e.image ? "<dt>Image</dt><dd><span class=\"mono\">" + esc(e.image) + "</span></dd>" : "") +
    ((e.flags || []).length ? "<dt>Flags</dt><dd><span class=\"mono\">" + esc(e.flags.join("  ")) + "</span></dd>" : "") +
    "</div></div>";

  h += '<div class="sec"><' + H + '>Tested hardware</' + H + '><div class="kv">' + (s.hardware || []).map(function (id) {
    var hw = HW[id] || {};
    var bits = [gb(hw.memory_gb) || "memory not recorded"];
    if (hw.bandwidth_gbs) bits.push(hw.bandwidth_gbs + " GB/s");
    else if (hw.bandwidth_range_gbs) bits.push(hw.bandwidth_range_gbs[0] + "–" + hw.bandwidth_range_gbs[1] + " GB/s");
    if (hw.arch) bits.push(hw.arch);
    bits.push(hw.measured_by_us ? "measured by the owner" : "not measured by the owner");
    return "<dt>" + esc(hw.name || id) + "</dt><dd>" + esc(bits.join(" · ")) + "</dd>";
  }).join("") + "</div></div>";

  h += '<div class="sec"><' + H + '>Measurements <span class="g">' +
    esc(plural((s.measurements || []).length, "record")) + "</span></' + H + '>" + measurementTable(s) + aggNote(s) + "</div>";

  h += '<div class="sec"><' + H + '>Capability support</' + H + '>' + capLine(s) + "</div>";

  if (fails.length) h += '<div class="sec"><' + H + ' style="color:var(--bad)">' + esc("✕ Known failures") +
    '</' + H + '><ul class="notes bad">' + fails.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("") + "</ul></div>";
  if (cav.length) h += '<div class="sec"><' + H + '>Caveats <span class="g">' + esc("— what these numbers do not mean") +
    '</span></' + H + '><ul class="notes warn">' + cav.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("") + "</ul></div>";
  var got = (ENG[e.id] || {}).gotchas || [];
  if (got.length) h += '<div class="sec"><' + H + '>Engine gotchas <span class="g">' + esc((ENG[e.id] || {}).name || e.id) +
    '</span></' + H + '><ul class="notes">' + got.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("") + "</ul></div>";

  h += '<div class="sec"><' + H + '>Sources and revision</' + H + '>' + sourcesHtml(s) +
    '<p class="prose" style="margin-top:7px">' + esc("Last updated " + (s.updated || "—") + " · " + freshness(s).word +
      " · status: " + (s.status || "unrecorded")) + "</p>";
  if (!opts.page) h += "</div>";
  else h += '<details class="rawjson"><summary>Raw JSON</summary><pre>' + esc(JSON.stringify(s, function (k, v2) { return k.indexOf("__") === 0 ? undefined : v2; }, 2)) + "</pre>" +
    copyBtn(JSON.stringify(s, function (k, v2) { return k.indexOf("__") === 0 ? undefined : v2; }, 2), "copy JSON") + "</details></div>";

  if (!opts.page) {
    h += '<div class="det-foot"><a class="btn" href="#/recipes/' + esc(s.id) + '">Open recipe page →</a>' +
      '<button type="button" class="btn" data-cmp="' + esc(s.id) + '">' +
      (state.compare.indexOf(s.id) >= 0 ? "Remove from compare" : "Add to compare") + "</button></div>";
  }
  return h;
}

/* --------------------------------------------------------------- the row */
function decodeCell(s) {
  var r = repDecode(s);
  if (r) {
    return '<span class="dec-v">' + esc(r.value) + '<span class="dec-u">' + esc(r.unit) + "</span></span>" +
      '<div class="l2">' + esc(condOf(r)) + "</div>";
  }
  var a = aggDecode(s);
  if (a) {
    return '<span class="dec-v">' + esc(a.value) + '<span class="dec-u">' + esc(a.unit) + "</span></span>" +
      '<div class="l2"><span class="warn">' + esc("▲ aggregate only") + "</span> " + esc(condOf(a)) + "</div>";
  }
  return '<span class="na">' + esc("no speed data") + "</span>";
}
function artifactCell(s) {
  var v = s.variation || {}, confl = capConflicts(s), fails = failures(s);
  var l2 = [esc(pubName(v.publisher))];
  if (v.quant_detail) l2.push(esc(String(v.quant_detail).split(".")[0]));
  var extra = "";
  if (confl.length) extra += ' <span class="bad">' + esc("✕ " + confl.join(", ") + " off (runtime)") + "</span>";
  else if (fails.length) extra += ' <span class="bad">' + esc("✕ " + fails[0].slice(0, 88) + (fails[0].length > 88 ? "…" : "")) + "</span>";
  else if ((s.caveats || []).length) extra += ' <span class="warn">' + esc("▲ " + plural(s.caveats.length, "caveat")) + "</span>";
  return '<div class="l1 mono">' + esc(tail(v.checkpoint)) + "</div>" +
    '<div class="l2 clamp">' + l2.join(" · ") + extra + "</div>";
}
function hwCell(s) {
  var ids = s.hardware || [];
  if (!ids.length) return na();
  var first = (HW[ids[0]] || {}).name || ids[0];
  var need = gb((s.requirements || {}).memory_gb);
  var l2 = (need ? "needs " + need : "requirement not recorded") + (ids.length > 1 ? " · +" + (ids.length - 1) : "");
  return '<div class="l1 clamp" style="font-weight:400;font-size:13px">' + esc(String(first).split(",")[0]) + "</div>" +
    '<div class="l2">' + esc(l2) + "</div>";
}
function readyCell(s) {
  var k = readiness(s);
  return '<div class="l1" style="font-weight:400;font-size:13px">' + esc(READY_GLYPH[k] + " " + READY_WORD[k]) + "</div>" +
    '<div class="l2">' + esc(complexityWord(s)) + "</div>";
}
function engineCell(s) {
  var e = s.engine || {};
  return '<div class="l1" style="font-weight:400;font-size:13px">' + esc((ENG[e.id] || {}).name || e.id) +
    (e.requires_fork ? ' <span style="color:var(--warn)">' + esc("⤴") + "</span>" : "") + "</div>" +
    '<div class="l2">' + esc(e.requires_fork ? "custom fork" : "stock") +
    (e.spec_decode && e.spec_decode !== "none" ? esc(" · " + e.spec_decode) : "") + "</div>";
}

function rowTr(s) {
  var v = s.variation || {}, open = !!state.expanded[s.id], picked = state.compare.indexOf(s.id) >= 0;
  var cls = [];
  if (picked) cls.push("sel-on");
  if (open) cls.push("open");
  if (failures(s).length) cls.push("fail");
  var f = freshness(s);
  var h = '<tr class="' + cls.join(" ") + '" data-row="' + esc(s.id) + '">' +
    '<td class="c-sel"><input type="checkbox" class="cbx" data-cmp="' + esc(s.id) + '"' + (picked ? " checked" : "") +
    ' aria-label="' + esc("Compare " + s.title) + '"></td>' +
    "<td>" + artifactCell(s) + "</td>" +
    '<td class="c-quant"><div class="l1" style="font-weight:400;font-size:13px">' + esc(v.quant) + "</div>" +
      '<div class="l2">' + esc(v.format) + " · " + esc(gb(v.size_gb) || "size ?") + "</div></td>" +
    '<td class="c-eng">' + engineCell(s) + "</td>" +
    '<td class="c-hw">' + hwCell(s) + "</td>" +
    '<td class="c-ready">' + readyCell(s) + "</td>" +
    '<td class="c-dec r">' + decodeCell(s) + "</td>" +
    '<td class="c-ev">' + evStrip(s) + "</td>" +
    '<td class="c-upd"><div class="l1" style="font-weight:400;font-size:13px">' + esc(String(s.updated || "").slice(0, 7)) + "</div>" +
      '<div class="l2">' + esc(f.word) + "</div></td>" +
    '<td class="c-exp"><button type="button" class="exp-btn" data-exp="' + esc(s.id) + '" aria-expanded="' + open +
      '" aria-controls="d-' + esc(s.id) + '" aria-label="' + esc((open ? "Collapse " : "Expand ") + s.title) + '">' +
      esc(open ? "▾" : "▸") + "</button></td></tr>";
  if (open) {
    h += '<tr class="det" id="d-' + esc(s.id) + '"><td colspan="10"><div class="det-in">' + detailBody(s) + "</div></td></tr>";
  }
  return h;
}

function rowLi(s) {
  var v = s.variation || {}, e = s.engine || {}, open = !!state.expanded[s.id], picked = state.compare.indexOf(s.id) >= 0;
  var cls = [];
  if (picked) cls.push("sel-on");
  if (failures(s).length) cls.push("fail");
  var k = readiness(s), req = s.requirements || {};
  var h = '<li class="' + cls.join(" ") + '" data-row="' + esc(s.id) + '"><div class="mrow-top">' +
    '<input type="checkbox" class="cbx" data-cmp="' + esc(s.id) + '"' + (picked ? " checked" : "") +
    ' aria-label="' + esc("Compare " + s.title) + '">' +
    '<div class="mrow-body">' + artifactCell(s) +
    '<div class="mrow-l">' +
      '<span><span class="lbl">Engine</span>' + esc((ENG[e.id] || {}).name || e.id) + (e.requires_fork ? esc(" ⤴ fork") : "") + "</span>" +
      '<span><span class="lbl">Quant</span>' + esc(v.quant) + " · " + esc(gb(v.size_gb) || "?") + "</span>" +
      '<span><span class="lbl">Tested on</span>' + esc(String((HW[(s.hardware || [])[0]] || {}).name || "not recorded").split(",")[0]) + "</span>" +
      '<span><span class="lbl">Needs</span>' + esc(gb(req.memory_gb) || "not recorded") + "</span>" +
    "</div>" +
    '<div class="mrow-dec">' + decodeCell(s) + "</div>" +
    '<div class="mrow-act"><span class="mark m-none">' + esc(READY_GLYPH[k] + " " + READY_WORD[k]) + "</span>" +
    evStrip(s) +
    '<button type="button" class="btn" data-exp="' + esc(s.id) + '" aria-expanded="' + open +
      '" aria-controls="d-' + esc(s.id) + '">' + esc(open ? "▾ less" : "▸ details") + "</button></div>";
  if (open) h += '<div class="det-in" id="d-' + esc(s.id) + '">' + detailBody(s) + "</div>";
  return h + "</div></div></li>";
}

var COLS = [
  ["c-sel", "Compare"], ["", "Artifact"], ["c-quant", "Quant"], ["c-eng", "Engine"],
  ["c-hw", "Tested on"], ["c-ready", "Ready"], ["c-dec r", "Decode"], ["c-ev", "Evidence"],
  ["c-upd", "Updated"], ["c-exp", "Expand"]
];
function rowsHtml(list, caption) {
  if (state.mobile) return '<ul class="rows-m">' + list.map(rowLi).join("") + "</ul>";
  return '<table class="rows"><caption>' + esc(caption) + "</caption><thead><tr>" +
    COLS.map(function (c) {
      var sr = (c[1] === "Compare" || c[1] === "Expand") ? ' class="' + c[0] + '"' : ' class="' + c[0] + '"';
      var inner = (c[1] === "Compare" || c[1] === "Expand") ? '<span class="sr">' + c[1] + "</span>" : esc(c[1]);
      if (c[1] === "Evidence") inner += '<span class="ev-hd" aria-hidden="true">R C P A</span>';
      return '<th scope="col"' + sr + ">" + inner + "</th>";
    }).join("") + "</tr></thead><tbody>" + list.map(rowTr).join("") + "</tbody></table>";
}

/* ------------------------------------------------------------- the shelf */
function shelfHead(mid, shown, total) {
  var m = MODELS[mid] || {}, a = m.architecture || {}, c = m.context || {};
  var all = SETUPS.filter(function (s) { return s.model === mid; });
  var measured = all.filter(function (s) { return speeds(s).length > 0; }).length;
  var upd = all.map(function (s) { return s.updated; }).sort().pop();
  function fld(label, val) {
    return "<div><span class=\"lbl\">" + esc(label) + '</span><span class="v">' + (val == null ? na() : val) + "</span></div>";
  }
  var active = a.params_active_b != null ? esc(a.params_active_b + "B")
    : (a.kind === "dense" ? esc("all — dense") : null);
  var h = '<div class="shelf-head"><div class="shelf-top"><h2 id="h-' + esc(mid) + '">' +
    '<a href="#/models/' + esc(mid) + '">' + esc(m.name || mid) + "</a></h2>" +
    '<span class="shelf-meta"><b>' + esc(shown === total ? plural(total, "recipe") : shown + " of " + total + " recipes") +
    "</b> · " + esc(measured + " measured") + " · " + esc("updated " + (upd || "—")) + "</span></div>" +
    '<div class="spec">' +
    fld("Generation", esc(m.generation || "")) +
    fld("Architecture", esc(a.kind === "moe" ? "MoE" : a.kind || "")) +
    fld("Total params", a.params_total_b != null ? esc(a.params_total_b + "B") : null) +
    fld("Active params", active) +
    fld("Native context", c.native != null ? '<span class="mono">' + esc(ctx(c.native)) + "</span>" : na("unstated by the publisher")) +
    fld("Max context", c.max != null ? '<span class="mono">' + esc(ctx(c.max)) + "</span>" : na("not stated")) +
    fld("Modalities", esc((m.modalities || []).join(" · "))) +
    fld("Weight license", esc(m.license || "")) +
    "</div>";
  if ((m.known_regressions || []).length) {
    h += '<details class="regr"><summary>' + esc("▲ " + plural(m.known_regressions.length, "known regression")) +
      " in this family</summary><ul>" + m.known_regressions.map(function (r) { return "<li>" + esc(r) + "</li>"; }).join("") + "</ul></details>";
  }
  return h + "</div>";
}

/* --------------------------------------------------------- directory view */
function selHtml(id, key, opts, cur, allLabel) {
  var o = '<option value="">' + esc(allLabel) + "</option>";
  opts.forEach(function (x) {
    o += '<option value="' + esc(x.v) + '"' + (cur === x.v ? " selected" : "") + ">" +
      esc(x.name + " (" + x.n + ")") + "</option>";
  });
  return '<label class="fsel' + (cur ? " on" : "") + '"><span>' + esc(FACETS[key].label) +
    '</span><select id="' + esc(id) + '" data-f="' + esc(key) + '" aria-label="' +
    esc("Filter by " + FACETS[key].label.toLowerCase()) + '">' + o + "</select></label>";
}

function barHtml(shown) {
  var h = '<div class="bar"><div class="bar-search">' +
    '<input type="search" id="q" value="' + esc(state.q) + '" placeholder="' +
    esc("Search model, checkpoint, builder, command, engine, notes…") + '" aria-label="Search the directory">' +
    "</div>";
  if (state.mobile) {
    h += '<div class="filters"><button type="button" class="btn' + (state.filtersOpen ? " on" : "") +
      '" id="m-filters" aria-expanded="' + !!state.filtersOpen + '" aria-controls="filters">' +
      esc("Filters") + (activeFilters().length ? " (" + activeFilters().length + ")" : "") + "</button>" +
      '<span class="count" id="count"><b>' + shown + "</b> of " + SETUPS.length + "</span></div>";
  }
  h += '<div class="filters" id="filters"' + (state.mobile && !state.filtersOpen ? " hidden" : "") + ">";
  COMMON.forEach(function (k) { h += selHtml("f-" + k, k, facetValues(k), state.f[k] || "", "any"); });
  h += '<button type="button" class="btn' + (state.adv ? " on" : "") + '" id="adv-toggle" aria-expanded="' + state.adv +
    '" aria-controls="adv-panel">' + esc("⚙ Advanced") +
    (advCount() ? " (" + advCount() + ")" : "") + "</button>";
  h += '<span class="bar-end">' +
    '<label class="fsel"><span>Sort</span><select id="sort" aria-label="Sort order">' +
    Object.keys(SORTS).map(function (k) {
      return '<option value="' + k + '"' + (state.sort === k ? " selected" : "") + ">" + esc(SORTS[k].label) + "</option>";
    }).join("") + "</select></label>" +
    (state.mobile ? "" : '<span class="count" id="count"><b>' + shown + "</b> of " + SETUPS.length + " recipes</span>") + "</span>";
  h += "</div>";

  if (state.adv) {
    h += '<div class="adv" id="adv-panel"><div class="adv-grid">';
    ADVANCED.forEach(function (k) {
      var vals = facetValues(k);
      h += '<label class="fld"><span class="lbl">' + esc(FACETS[k].label) + '</span><select data-f="' + esc(k) +
        '" id="f-' + esc(k) + '"><option value="">any</option>' +
        vals.map(function (x) {
          return '<option value="' + esc(x.v) + '"' + (state.f[k] === x.v ? " selected" : "") + ">" + esc(x.name + " (" + x.n + ")") + "</option>";
        }).join("") + "</select></label>";
    });
    h += '<div class="fld"><span class="lbl">Total parameters (B)</span><div class="range">' +
      '<input type="number" id="f-pmin" placeholder="min" value="' + esc(state.f.pmin || "") + '" aria-label="Minimum total parameters in billions">' +
      '<span class="g">to</span>' +
      '<input type="number" id="f-pmax" placeholder="max" value="' + esc(state.f.pmax || "") + '" aria-label="Maximum total parameters in billions"></div></div>';
    h += "</div><p class=\"adv-note\">" + esc("Hardware filtering here means “this recipe was tested on that hardware class”. It is not a fit calculation and produces no verdict — for that, open ") +
      '<a href="#/hardware">My Hardware</a>' + esc(". Operating system is implied from the tested hardware class's architecture string; the dataset has no OS field. Setup complexity is derived — the formula is on the ") +
      '<a href="#/methodology">methodology page</a>.</p></div>';
  }

  var chips = activeFilters();
  if (chips.length || state.q) {
    h += '<div class="chips" id="chips">';
    if (state.q) h += '<button type="button" class="chip" data-clear="q"><b>Search</b> ' + esc(state.q) + '<span class="x" aria-hidden="true">✕</span><span class="sr">remove</span></button>';
    chips.forEach(function (c) {
      h += '<button type="button" class="chip" data-clear="' + esc(c.k) + '" aria-label="' +
        esc("Remove filter: " + c.label + " " + c.val) + '"><b>' + esc(c.label) + "</b> " + esc(c.val) +
        '<span class="x" aria-hidden="true">✕</span></button>';
    });
    if (chips.length + (state.q ? 1 : 0) > 1) h += '<button type="button" class="btn" id="clear-all">Clear all</button>';
    h += "</div>";
  }
  return h + "</div>";
}
function advCount() {
  var n = 0;
  ADVANCED.concat(["pmin", "pmax"]).forEach(function (k) { if (state.f[k]) n++; });
  return n;
}

function railHtml(groups) {
  var famCounts = {};
  groups.forEach(function (g) { famCounts[g.id] = g.list.length; });
  function item(label, count, attrs) {
    return "<li>" + attrs + '<span>' + esc(label) + '</span><span class="rc">' + (count == null ? "" : count) + "</span></button></li>";
  }
  var h = '<div class="rail-grp"><ul>' +
    "<li><button type=\"button\" data-rail-clear=\"1\"" + (!state.f.gen && !state.f.arch && !state.f.cap ? ' aria-pressed="true"' : "") +
    '><span>All model families</span><span class="rc">' + D.model_order.length + "</span></button></li></ul></div>";

  var gens = facetValues("gen");
  h += '<div class="rail-grp"><span class="lbl">Generation</span><ul>' + gens.map(function (g) {
    var fams = uniq(SETUPS.filter(function (s) { return String(modelOf(s).generation) === g.v; }).map(function (s) { return s.model; })).length;
    return item("Qwen " + g.v, fams, '<button type="button" data-rail-f="gen" data-rail-v="' + esc(g.v) + '"' +
      (state.f.gen === g.v ? ' aria-pressed="true"' : "") + ">");
  }).join("") + "</ul></div>";

  h += '<div class="rail-grp"><span class="lbl">Architecture</span><ul>' +
    item("Dense models", uniq(SETUPS.filter(function (s) { return (modelOf(s).architecture || {}).kind === "dense"; }).map(function (s) { return s.model; })).length,
      '<button type="button" data-rail-f="arch" data-rail-v="dense"' + (state.f.arch === "dense" ? ' aria-pressed="true"' : "") + ">") +
    item("MoE models", uniq(SETUPS.filter(function (s) { return (modelOf(s).architecture || {}).kind === "moe"; }).map(function (s) { return s.model; })).length,
      '<button type="button" data-rail-f="arch" data-rail-v="moe"' + (state.f.arch === "moe" ? ' aria-pressed="true"' : "") + ">") +
    item("Vision and multimodal", uniq(SETUPS.filter(function (s) { return (modelOf(s).modalities || []).length > 1; }).map(function (s) { return s.model; })).length,
      '<button type="button" data-rail-f="cap" data-rail-v="vision"' + (state.f.cap === "vision" ? ' aria-pressed="true"' : "") + ">") +
    "</ul></div>";

  h += '<div class="rail-grp"><span class="lbl">Families</span><ul>' + groups.map(function (g) {
    return "<li><a href=\"#h-" + esc(g.id) + '" data-jump="' + esc(g.id) + '"><span>' + esc((MODELS[g.id] || {}).name || g.id) +
      '</span><span class="rc">' + g.list.length + "</span></a></li>";
  }).join("") + "</ul></div>";
  return h;
}

function emptyDirectory() {
  var sug = [];
  Object.keys(state.f).forEach(function (k) {
    if (!state.f[k]) return;
    var save = state.f[k]; state.f[k] = "";
    var n = SETUPS.filter(matches).length;
    state.f[k] = save;
    if (n > 0) sug.push("Removing “" + (FACETS[k] ? FACETS[k].label : k) + ": " + facetName(k, save) + "” would show " + n + ".");
  });
  var h = '<div class="empty"><h2>' + esc("No recipes match " + (state.q ? "that search and " : "") + plural(activeFilters().length, "filter") + ".") + "</h2>";
  if (state.q) h += "<p>" + esc("Searched model, family, checkpoint, publisher, builder, engine, configuration, quantization, command, step text, caveats and measurement methods for: ") +
    '<span class="mono">' + esc(state.q) + "</span></p>";
  if (sug.length) h += "<p>" + sug.slice(0, 3).map(esc).join("<br>") + "</p>";
  h += '<div class="acts"><button type="button" class="btn btn-p" id="clear-all">Clear all filters</button>' +
    '<a class="btn" href="#/methodology">What the fields mean</a></div></div>';
  return h;
}

function viewDirectory() {
  var list = SETUPS.filter(matches);
  var groups = [];
  D.model_order.forEach(function (mid) {
    var sub = list.filter(function (s) { return s.model === mid; });
    if (sub.length) groups.push({ id: mid, list: sorted(sub) });
  });

  setRail(railHtml(groups));
  el("mast-sub").innerHTML = esc("The complete advanced index — ") +
    "<b>" + SETUPS.length + "</b>" + esc(" recipes across ") + "<b>" + D.model_order.length + "</b>" +
    esc(" model families, each number carrying its source.");

  var h = '<h1 class="sr">Every recorded recipe for running Qwen on hardware you own</h1>' +
    barHtml(list.length);
  if (state.sort === "speed") {
    h += '<div class="disclose"><b>' + esc("▲ This ordering is a discovery aid, not a leaderboard.") + "</b> " +
      esc("These numbers were produced on different hardware, at different context lengths, with different workloads and concurrency, by different people, using different clocks. " +
        SETUPS.filter(function (s) { return s.provenance_tier === "box"; }).length + " are owner-measured, " +
        SETUPS.filter(function (s) { return s.provenance_tier === "forum"; }).length + " are community-reported, and " +
        SETUPS.filter(function (s) { return !speeds(s).length; }).length + " carry no speed measurement and sort last.") + "</div>";
  }
  if (!groups.length) h += emptyDirectory();
  else h += groups.map(function (g) {
    var total = SETUPS.filter(function (s) { return s.model === g.id; }).length;
    return '<section class="shelf" id="' + esc(g.id) + '" aria-labelledby="h-' + esc(g.id) + '">' +
      shelfHead(g.id, g.list.length, total) + rowsHtml(g.list, (MODELS[g.id] || {}).name || g.id) + "</section>";
  }).join("");
  el("main").innerHTML = h;
  announce(list.length + " of " + SETUPS.length + " recipes");
  spy();
}

/* ------------------------------------------------------ model-first home */
function modelFloor(s) {
  if (!s) return "Not verified yet";
  var req = s.requirements || {}, hw = HW[(s.hardware || [])[0]] || {};
  if (req.min_vram_gb != null) {
    return gb(req.min_vram_gb) + " VRAM" + (req.memory_gb != null && req.memory_gb > req.min_vram_gb
      ? " · " + gb(req.memory_gb) + " recorded memory" : "");
  }
  return (hw.name ? String(hw.name).split(",")[0] + " · " : "") + (gb(req.memory_gb) || "memory not recorded");
}
function baselineSpeed(s) { return s ? repDecode(s) : null; }
function modelMatches(m) {
  if (state.modelQ) {
    var terms = state.modelQ.toLowerCase().split(/\s+/).filter(Boolean), b = modelSearchBlob(m);
    for (var i = 0; i < terms.length; i++) if (b.indexOf(terms[i]) < 0) return false;
  }
  if (state.modelGen && String(m.generation) !== state.modelGen) return false;
  if (state.modelArch && ((m.architecture || {}).kind || "") !== state.modelArch) return false;
  if (state.modelBaseline) {
    var has = !!baselineSetup(m);
    if (state.modelBaseline === "selected" && !has) return false;
    if (state.modelBaseline === "missing" && has) return false;
  }
  return true;
}
function modelOptions(field) {
  var counts = {};
  D.model_order.forEach(function (id) {
    var m = MODELS[id] || {}, v = field === "generation" ? String(m.generation || "") : ((m.architecture || {}).kind || "");
    if (v) counts[v] = (counts[v] || 0) + 1;
  });
  return Object.keys(counts).sort(function (a, b) {
    return field === "generation" ? parseFloat(b) - parseFloat(a) : a.localeCompare(b);
  }).map(function (v) {
    var selected = (field === "generation" ? state.modelGen : state.modelArch) === v;
    var label = (field === "generation" ? "Qwen " : "") + (v === "moe" ? "MoE" : v) + " (" + counts[v] + ")";
    return '<option value="' + esc(v) + '"' + (selected ? " selected" : "") + '>' + esc(label) + '</option>';
  }).join("");
}
function modelListRow(m) {
  var a = m.architecture || {}, c = m.context || {}, s = baselineSetup(m), speed = baselineSpeed(s);
  var active = a.params_active_b != null ? a.params_active_b + "B active" : (a.kind === "dense" ? "all active" : "active params not recorded");
  var selected = state.selectedModel === m.id;
  return '<li><button type="button" class="model-row' + (selected ? " is-selected" : "") + '" data-model-select="' + esc(m.id) +
    '" aria-pressed="' + selected + '"><span class="model-id"><strong>' + esc(m.name) + '</strong><span>' +
    esc((a.kind === "moe" ? "MoE" : a.kind || "architecture not recorded") + " · " +
      (a.params_total_b != null ? a.params_total_b + "B" : "params not recorded") + " · " + active) + '</span></span>' +
    '<span class="model-context"><span class="lbl">Context</span><span>' +
    (c.native != null ? esc(ctx(c.native)) : na("unstated")) + '</span><small>' + esc((m.modalities || []).join(" · ")) + '</small></span>' +
    '<span class="model-floor"><span class="lbl">Practical minimum</span><span>' +
    (s ? esc(modelFloor(s)) : '<span class="na">Not verified yet</span>') + '</span><small>' +
    (s ? esc((s.variation || {}).quant + " · " + ((ENG[(s.engine || {}).id] || {}).name || (s.engine || {}).id)) : esc((m.practical_baseline || {}).reason || "No qualifying baseline")) + '</small></span>' +
    '<span class="model-speed"><span class="lbl">Recorded here</span>' + (speed
      ? '<strong>' + esc(speed.value) + '<small>' + esc(" " + speed.unit) + '</small></strong><small>' + esc(condOf(speed)) + '</small>'
      : '<span class="na">Not measured</span><small>' + esc(s ? "No single-stream decode on this baseline" : "Baseline not verified") + '</small>') +
    '</span><span class="model-open" aria-hidden="true">' + esc(state.mobile ? "open" : "view") + '</span></button></li>';
}
function modelPreview(m) {
  var a = m.architecture || {}, c = m.context || {}, b = m.practical_baseline || {}, s = baselineSetup(m);
  var recipes = modelRecipes(m.id), h = '<div class="model-preview-head"><span class="lbl">Selected model</span><h2>' + esc(m.name) + '</h2>' +
    '<p>' + esc(m.summary || "No model summary is recorded.") + '</p><div class="model-tags"><span>' +
    esc(a.kind === "moe" ? "MoE" : a.kind || "architecture not recorded") + '</span><span>' +
    esc(a.params_total_b != null ? a.params_total_b + "B total" : "params not recorded") + '</span><span>' +
    esc(a.params_active_b != null ? a.params_active_b + "B active" : (a.kind === "dense" ? "all parameters active" : "active params not recorded")) +
    '</span><span>' + esc(c.native != null ? ctx(c.native) + " native context" : "native context unstated") + '</span></div></div>';
  if (!s) {
    h += '<section class="baseline-missing"><h3>Practical minimum not verified yet</h3><p>' +
      esc(b.reason || "No qualifying baseline is recorded for this model.") + '</p><p>' +
      esc("Available recipes remain visible, but none is promoted into a hardware recommendation without reported or measured evidence.") + '</p></section>';
  } else {
    var req = s.requirements || {}, v = s.variation || {}, e = s.engine || {}, speed = baselineSpeed(s);
    h += '<section class="baseline"><div class="baseline-title"><div><span class="lbl">Practical minimum</span><h3>' +
      esc(modelFloor(s)) + '</h3></div><span class="mark m-est">' + esc("curated · reviewed " + b.reviewed) + '</span></div>' +
      '<p class="baseline-why">' + esc(b.rationale) + '</p><dl class="baseline-spec">' +
      '<div><dt>Tested hardware</dt><dd>' + esc((s.hardware || []).map(function (id) { return (HW[id] || {}).name || id; }).join(" · ")) + '</dd></div>' +
      '<div><dt>Resident memory</dt><dd>' + (gb(req.memory_gb) || na()) + '</dd></div>' +
      '<div><dt>Minimum VRAM</dt><dd>' + (gb(req.min_vram_gb) || na("unified or not separated")) + '</dd></div>' +
      '<div><dt>Disk</dt><dd>' + (gb(req.disk_gb) || na()) + '</dd></div>' +
      '<div><dt>Recipe</dt><dd>' + esc(v.quant + " · " + v.format + " · " + (gb(v.size_gb) || "size not recorded")) + '</dd></div>' +
      '<div><dt>Engine</dt><dd>' + esc((ENG[e.id] || {}).name || e.id) + (e.requires_fork ? ' <span class="mark m-warn">custom fork</span>' : ' <span class="g">stock</span>') + '</dd></div>' +
      '<div><dt>Recorded context</dt><dd>' + ((s.capabilities || {}).long_context != null ? esc(ctx(s.capabilities.long_context)) : na("not recorded")) + '</dd></div>' +
      '<div class="wide"><dt>Memory and offload notes</dt><dd>' + (req.notes ? esc(req.notes) : na("not recorded")) + '</dd></div></dl>';
    h += '<div class="baseline-speed"><span class="lbl">Recorded on this exact baseline</span>';
    if (speed) {
      h += '<div class="speed-line"><strong>' + esc(speed.value) + '<small>' + esc(" " + speed.unit) + '</small></strong><span>' +
        esc(condOf(speed)) + '</span></div>' + (speed.note ? '<p>' + esc(speed.note) + '</p>' : '') +
        (speed.source ? '<a href="' + esc(speed.source) + '" target="_blank" rel="noopener">Open measurement source</a>' : '');
    } else h += '<p class="na">No single-stream decode measurement is recorded for this baseline.</p>';
    h += '</div>';
    var trade = [];
    if (e.requires_fork) trade.push("This baseline requires a custom engine build.");
    capConflicts(s).forEach(function (x) { trade.push(x + " is disabled by this runtime."); });
    (s.caveats || []).slice(0, 3).forEach(function (x) { trade.push(x); });
    if (trade.length) h += '<div class="baseline-trade"><h3>Trade-offs to read first</h3><ul>' +
      trade.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") + '</ul></div>';
    h += '</section>';
  }
  h += '<div class="model-preview-actions"><a class="btn btn-p" href="#/models/' + esc(m.id) + '">' +
    esc("View " + plural(recipes.length, "recipe")) + '</a><a class="btn" href="#/hardware">Check my hardware</a>' +
    (s ? '<a class="btn" href="#/recipes/' + esc(s.id) + '">Open baseline recipe</a>' : '') + '</div>';
  return h;
}
function writeModelHash() {
  if (state.route !== "models-home") return;
  var q = [];
  if (state.selectedModel) q.push("model=" + encodeURIComponent(state.selectedModel));
  if (state.modelQ) q.push("q=" + encodeURIComponent(state.modelQ));
  if (state.modelGen) q.push("gen=" + encodeURIComponent(state.modelGen));
  if (state.modelArch) q.push("arch=" + encodeURIComponent(state.modelArch));
  if (state.modelBaseline) q.push("baseline=" + encodeURIComponent(state.modelBaseline));
  var next = "#/" + (q.length ? "?" + q.join("&") : "");
  if (location.hash !== next) history.replaceState(null, "", next);
}
function viewModelsHome() {
  setRail("");
  var list = D.model_order.map(function (id) { return MODELS[id]; }).filter(modelMatches);
  if (!state.selectedModel || !MODELS[state.selectedModel] || list.indexOf(MODELS[state.selectedModel]) < 0) {
    state.selectedModel = list.length ? list[0].id : null;
  }
  var verified = Object.keys(MODELS).filter(function (id) { return !!baselineSetup(MODELS[id]); }).length;
  el("mast-sub").innerHTML = esc("Choose the model first. Practical minimums point to exact sourced recipes; missing evidence stays visible — ") +
    '<b>' + verified + '</b>' + esc(" of " + D.model_order.length + " models currently have a curated baseline.");
  var h = '<div class="models-home"><header class="models-intro"><h1>Choose a Qwen model</h1><p>' +
    esc("Start with what you want to run. Each practical minimum is tied to one reported or measured recipe, and its speed is shown only when that same setup was measured.") +
    '</p></header><div class="model-controls"><label class="model-search"><span class="lbl">Find a model</span><input type="search" id="model-q" value="' +
    esc(state.modelQ) + '" placeholder="Flash-Next, 27B, vision…"></label><label><span class="lbl">Generation</span><select id="model-gen"><option value="">all</option>' +
    modelOptions("generation") + '</select></label><label><span class="lbl">Architecture</span><select id="model-arch"><option value="">all</option>' +
    modelOptions("architecture") + '</select></label><label><span class="lbl">Baseline</span><select id="model-baseline"><option value="">all</option>' +
    '<option value="selected"' + (state.modelBaseline === "selected" ? " selected" : "") + '>practical minimum verified</option>' +
    '<option value="missing"' + (state.modelBaseline === "missing" ? " selected" : "") + '>not verified yet</option></select></label>' +
    '<span class="model-count"><b>' + list.length + '</b> of ' + D.model_order.length + ' models</span></div>';
  if (!list.length) h += '<div class="empty"><h2>No models match</h2><p>Clear the search or filters to return to all models.</p><button type="button" class="btn btn-p" id="model-clear">Clear model filters</button></div>';
  else h += '<div class="model-master"><section class="model-index" aria-label="Qwen models"><div class="model-list-head"><span>Model</span><span>Context</span><span>Practical minimum</span><span>Recorded speed</span><span></span></div><ol class="model-list">' +
    list.map(modelListRow).join("") + '</ol></section><aside class="model-preview" aria-live="polite">' +
    modelPreview(MODELS[state.selectedModel]) + '</aside></div>';
  h += '</div>';
  el("main").innerHTML = h;
  announce(list.length + " of " + D.model_order.length + " models");
  writeModelHash();
}

/* ------------------------------------------------------------ compare rail */
var CMP_MAX = 4;
function cmpSetups() {
  return state.compare.map(function (id) {
    return SETUPS.filter(function (s) { return s.id === id; })[0];
  }).filter(Boolean);
}
function comparability(list) {
  var out = [];
  if (list.length < 2) return out;
  function vals(fn) { return uniq(list.map(fn)); }
  var hws = vals(function (s) { return (s.hardware || []).join(","); });
  if (hws.length > 1) {
    var bw = list.map(function (s) {
      var h = HW[(s.hardware || [])[0]] || {};
      return h.bandwidth_gbs || (h.bandwidth_range_gbs || [])[0] || null;
    }).filter(Boolean);
    var extra = "";
    if (bw.length > 1) {
      var r = Math.max.apply(null, bw) / Math.min.apply(null, bw);
      if (r >= 1.2) extra = " Memory bandwidth differs by about " + (Math.round(r * 10) / 10) + "×.";
    }
    out.push({ k: "hardware", t: "Measured on different hardware — " + list.map(function (s) {
      return String((HW[(s.hardware || [])[0]] || {}).name || "unrecorded").split(",")[0];
    }).join(" vs ") + "." + extra });
  }
  if (vals(function (s) { return (s.engine || {}).id; }).length > 1)
    out.push({ k: "engine", t: "Different engines — " + list.map(function (s) { return (ENG[(s.engine || {}).id] || {}).name || "?"; }).join(" vs ") + ". Engine choice changes decode speed independently of the weights." });
  if (vals(function (s) { return s.model; }).length > 1)
    out.push({ k: "model", t: "Different model families — this compares runtimes and artifacts, not the same weights." });
  var reps = list.map(repDecode);
  var withRep = reps.filter(Boolean);
  if (withRep.length > 1) {
    if (uniq(withRep.map(function (m) { return m.metric; })).length > 1)
      out.push({ k: "metric", t: "Different workloads — " + uniq(withRep.map(function (m) { return metricWord(m.metric); })).join(" vs ") + " decode." });
    if (uniq(withRep.map(function (m) { return m.stat || "unstated"; })).length > 1)
      out.push({ k: "stat", t: "Different statistics — " + uniq(withRep.map(function (m) { return m.stat || "unstated"; })).join(" vs ") + "." });
    if (uniq(withRep.map(function (m) { return m.concurrency == null ? "unstated" : String(m.concurrency); })).length > 1)
      out.push({ k: "conc", t: "Different concurrency on the compared figure. These are different quantities." });
    if (uniq(withRep.map(function (m) { return m.provenance; })).length > 1)
      out.push({ k: "prov", t: "Different evidence tiers — " + uniq(withRep.map(function (m) { return m.provenance; })).join(" and ") + ". Tiers are never blended." });
  }
  if (withRep.length < list.length)
    out.push({ k: "coverage", t: (list.length - withRep.length) + " of " + list.length + " recipes carry no single-stream speed measurement — the performance section is partly empty by design." });
  var tc = uniq(list.map(function (s) { return (s.capabilities || {}).long_context; }));
  if (tc.length > 1) out.push({ k: "context", t: "Different recorded context ceilings — " + tc.map(function (x) { return x == null ? "unrecorded" : ctx(x); }).join(" vs ") + "." });
  return out;
}
function railSummary(list) {
  var issues = comparability(list);
  if (list.length < 2) return { cls: "m-none", t: "Select one more recipe to compare" };
  if (!issues.length) return { cls: "m-ok", t: "● Same engine, same hardware, same statistic — these speeds are directly comparable" };
  var head = issues.filter(function (i) { return i.k === "hardware" || i.k === "engine"; });
  if (head.length) return { cls: "m-warn", t: "▲ Mixed " + head.map(function (i) { return i.k; }).join(" and ") + " — speeds are not directly comparable" };
  return { cls: "m-warn", t: "▲ " + issues[0].t };
}
function renderRail() {
  var host = el("compare-host"), list = cmpSetups();
  var badge = el("tab-compare-n");
  if (!list.length) { host.innerHTML = ""; badge.hidden = true; return; }
  badge.hidden = false; badge.textContent = list.length;
  var sum = railSummary(list);
  host.innerHTML = '<div class="crail" role="region" aria-label="Compare selection" aria-live="polite">' +
    '<div class="crail-in"><span class="crail-hd">' + esc("▣ Comparing " + list.length + " of " + CMP_MAX) + "</span>" +
    '<div class="crail-items">' + list.map(function (s) {
      return '<div class="citem"><div class="cbody"><div class="cn" title="' + esc(s.variation.checkpoint) + '">' +
        esc(tail(s.variation.checkpoint)) + '</div><div class="cs">' +
        esc(((ENG[(s.engine || {}).id] || {}).name || "?") + ((s.engine || {}).requires_fork ? " ⤴" : "") + " · " + s.variation.quant) +
        '</div><div class="cs">' + esc(String((HW[(s.hardware || [])[0]] || {}).name || "hardware not recorded").split(",")[0]) + "</div></div>" +
        '<button type="button" class="cx" data-cmp="' + esc(s.id) + '" aria-label="' + esc("Remove " + s.title + " from compare") + '">' + esc("✕") + "</button></div>";
    }).join("") + "</div>" +
    '<span class="crail-end"><button type="button" class="btn" id="cmp-clear">Clear all</button>' +
    '<a class="btn btn-p' + (list.length < 2 ? " disabled" : "") + '" href="#/compare"' +
    (list.length < 2 ? ' aria-disabled="true"' : "") + ">" + esc(list.length < 2 ? "Select one more to compare" : "Compare " + list.length + " →") + "</a></span>" +
    '<span class="crail-cmp mark ' + sum.cls + '">' + esc(sum.t) + "</span>" +
    "</div></div>";
}
function toggleCompare(id) {
  var i = state.compare.indexOf(id);
  if (i >= 0) state.compare.splice(i, 1);
  else if (state.compare.length >= CMP_MAX) { announce("Compare holds " + CMP_MAX + " recipes — remove one first."); return false; }
  else state.compare.push(id);
  sess("qlr.compare", state.compare);
  renderRail();
  return true;
}

/* -------------------------------------------------------- compare workspace */
function cval(v, cond, flagged) {
  if (v == null || v === "") return '<td>' + na() + "</td>";
  return "<td>" + v + (cond ? '<span class="cond">' + esc(cond) + "</span>" : "") +
    (flagged ? '<span class="rowflag">' + esc("▲ not directly comparable") + "</span>" : "") + "</td>";
}
function cmpRow(label, list, fn, flagFn) {
  var cells = list.map(function (s) { return fn(s); });
  var flagged = flagFn ? flagFn(list) : false;
  return '<tr><th class="k" scope="row">' + esc(label) + "</th>" +
    cells.map(function (c) {
      if (c == null || c === "") return "<td>" + na() + "</td>";
      return "<td>" + c + (flagged ? '<span class="rowflag">' + esc("▲ not directly comparable") + "</span>" : "") + "</td>";
    }).join("") + "</tr>";
}
function grpRow(label, n) {
  return '<tr class="grp"><th class="k" scope="row">' + esc(label) + '</th><th colspan="' + n + '"></th></tr>';
}
function metricCell(s, metric, single) {
  var rows = (s.measurements || []).filter(function (m) {
    if (m.metric !== metric) return false;
    if (single === true) return isSingle(m);
    if (single === false) return !isSingle(m);
    return true;
  });
  if (!rows.length) return '<span class="na">no measurement</span>';
  return rows.map(function (m) {
    return '<b class="num">' + esc(m.value) + "</b> " + esc(m.unit) +
      '<span class="cond">' + esc(condOf(m)) + (m.method ? " · " + m.method.slice(0, 70) + (m.method.length > 70 ? "…" : "") : "") + "</span>";
  }).join('<span class="cond" style="height:5px"></span>');
}
function viewCompare() {
  var list = cmpSetups();
  setRail("");
  el("mast-sub").innerHTML = esc("Put two to four recipes side by side. Every axis on which their measurements are not comparable is named. No winner is declared.");
  if (!list.length) {
    el("main").innerHTML = '<div class="page"><h1>Compare</h1>' +
      '<p class="lede">' + esc("Nothing is selected yet. Tick the compare box on any recipe row — in the Directory, on a model-family page, on a recipe page, or in a My Hardware result — and a selection rail appears at the bottom of the screen.") + "</p>" +
      '<div class="empty"><h2>Good places to start</h2><p>' + esc("The families with the most alternatives to weigh up:") + "</p><ul class=\"notes\">" +
      D.model_order.map(function (mid) { return { id: mid, n: SETUPS.filter(function (s) { return s.model === mid; }).length }; })
        .sort(function (a, b) { return b.n - a.n; }).slice(0, 4)
        .map(function (x) { return '<li><a href="#/models/' + esc(x.id) + '">' + esc((MODELS[x.id] || {}).name) + "</a> " + esc("— " + plural(x.n, "recipe")) + "</li>"; }).join("") +
      '</ul><div class="acts"><a class="btn btn-p" href="#/recipes">Open Recipes</a></div></div></div>';
    return;
  }
  var n = list.length, issues = comparability(list);
  var h = '<div class="page wide"><h1>' + esc("Comparing " + plural(n, "recipe")) + "</h1>";

  if (n < 2) h += '<div class="banner b-info"><h3>' + esc("One recipe selected") + "</h3><p>" +
    esc("Comparison needs at least two. Add another from Recipes or a model page.") + "</p></div>";
  else if (!issues.length) h += '<div class="banner b-ok"><h3>' + esc("● These are directly comparable") + "</h3><p>" +
    esc("Same engine, same hardware class, same metric, same statistic and same concurrency. This is the one case where the numbers can be read against each other.") + "</p></div>";
  else h += '<div class="banner b-warn"><h3>' + esc("▲ These recipes are not directly comparable") + "</h3><ul>" +
    issues.map(function (i) { return "<li>" + esc(i.t) + "</li>"; }).join("") + "</ul></div>";

  h += '<p class="lede" style="margin-top:12px">' + esc("No overall winner is calculated. Nothing below is highlighted as best — the sections state what each recipe records, and the banner states why the records may not line up.") + "</p>";

  h += '<div class="cmp-wrap"><table class="cmp"><colgroup><col class="k">' +
    list.map(function () { return "<col>"; }).join("") + "</colgroup><thead><tr>" +
    '<th class="k" scope="col"><span class="sr">Field</span></th>' +
    list.map(function (s, i) {
      return '<th scope="col">' + esc(String.fromCharCode(65 + i) + " · " + tail(s.variation.checkpoint)) +
        '<span class="cond">' + esc(((ENG[(s.engine || {}).id] || {}).name || "?") + " · " + s.variation.quant) + "</span>" +
        '<span class="cond"><a href="#/recipes/' + esc(s.id) + '">' + esc("open recipe →") + "</a></span></th>";
    }).join("") + "</tr></thead><tbody>";

  var mixedHw = issues.some(function (i) { return i.k === "hardware"; });
  var mixedMetric = issues.some(function (i) { return i.k === "metric" || i.k === "stat" || i.k === "conc" || i.k === "prov"; });
  var perfFlag = function () { return mixedHw || mixedMetric; };

  h += grpRow("Identity", n);
  h += cmpRow("Model family", list, function (s) { return '<a href="#/models/' + esc(s.model) + '">' + esc(modelOf(s).name || s.model) + "</a>"; });
  h += cmpRow("Checkpoint", list, function (s) { return '<span class="mono">' + esc(s.variation.checkpoint) + "</span>"; });
  h += cmpRow("Publisher", list, function (s) { return '<a href="#/publishers/' + esc(s.variation.publisher) + '">' + esc(pubName(s.variation.publisher)) + "</a>"; });
  h += cmpRow("Recipe by", list, function (s) { return s.builder ? esc(pubName(s.builder)) : null; });
  h += cmpRow("Quantization", list, function (s) { return esc(s.variation.quant) + '<span class="cond">' + esc(s.variation.quant_detail || "no detail recorded") + "</span>"; });
  h += cmpRow("Format", list, function (s) { return esc(s.variation.format); });
  h += cmpRow("Artifact size", list, function (s) { return esc(gb(s.variation.size_gb) || ""); });
  h += cmpRow("Weight license", list, function (s) { return esc(s.variation.license || ""); });

  h += grpRow("Runtime", n);
  h += cmpRow("Engine", list, function (s) { return esc((ENG[(s.engine || {}).id] || {}).name || s.engine.id); });
  h += cmpRow("Engine version", list, function (s) { return s.engine.version ? esc(s.engine.version) : null; });
  h += cmpRow("Operating system", list, function (s) {
    var o = impliedOS(s);
    return o.length ? esc(o.map(function (x) { return FACETS.os.name(x); }).join(", ")) : null;
  });
  h += cmpRow("Required fork", list, function (s) {
    return s.engine.requires_fork ? '<span class="mark m-warn">' + esc("⤴ yes") + "</span>" : esc("no — stock engine");
  });
  h += cmpRow("Speculative decoding", list, function (s) { return esc(s.engine.spec_decode || "none"); });
  h += cmpRow("Draft model", list, function (s) { return s.engine.draft_model ? '<span class="mono">' + esc(s.engine.draft_model) + "</span>" : null; });
  h += cmpRow("Important flags", list, function (s) { return (s.engine.flags || []).length ? '<span class="mono">' + esc(s.engine.flags.join("  ")) + "</span>" : null; });
  h += cmpRow("Container image", list, function (s) { return s.engine.image ? '<span class="mono">' + esc(s.engine.image) + "</span>" : null; });
  h += cmpRow("Installation complexity", list, function (s) { return esc(complexityWord(s)) + '<span class="cond">' + esc("derived — see methodology") + "</span>"; });

  h += grpRow("Hardware", n);
  h += cmpRow("Tested devices", list, function (s) {
    return (s.hardware || []).map(function (id) {
      var hw = HW[id] || {};
      return esc(hw.name || id) + '<span class="cond">' + esc((hw.measured_by_us ? "measured by the owner" : "not measured by the owner") + " · " + (hw.arch || "")) + "</span>";
    }).join("");
  });
  h += cmpRow("Recorded resident memory", list, function (s) { return esc(gb((s.requirements || {}).memory_gb) || ""); });
  h += cmpRow("Minimum VRAM", list, function (s) { return (s.requirements || {}).min_vram_gb != null ? esc(gb(s.requirements.min_vram_gb)) : null; });
  h += cmpRow("Disk requirement", list, function (s) { return esc(gb((s.requirements || {}).disk_gb) || ""); });
  h += cmpRow("Offload strategy", list, function (s) {
    var t = (s.requirements || {}).notes || "";
    return /offload|stream|ssd|mmap|disk/i.test(t) ? esc(t) : null;
  });
  h += cmpRow("Power and thermal notes", list, function (s) {
    var hw = HW[(s.hardware || [])[0]] || {};
    var note = (hw.notes || []).filter(function (x) { return /power|thermal|watt|throttl/i.test(x); })[0];
    return note ? esc(note) : null;
  });

  h += grpRow("Capabilities", n);
  h += cmpRow("Model capability", list, function (s) { return esc((modelOf(s).modalities || []).join(" · ")); });
  ["vision", "video", "audio", "tools", "thinking"].forEach(function (k) {
    h += cmpRow("Recipe: " + k, list, function (s) {
      var v = (s.capabilities || {})[k];
      if (v === true) return '<span class="mark m-ok">' + esc("● yes") + "</span>";
      if (v === false) {
        var conflict = capConflicts(s).indexOf(k) >= 0;
        return '<span class="mark ' + (conflict ? "m-bad" : "m-none") + '">' + esc(conflict ? "✕ off — runtime does not implement it" : "not supported") + "</span>";
      }
      return null;
    });
  });
  h += cmpRow("Native context", list, function (s) { var c = modelOf(s).context || {}; return c.native != null ? '<span class="mono">' + esc(c.native.toLocaleString()) + "</span>" : null; });
  h += cmpRow("Tested context", list, function (s) { var c = (s.capabilities || {}).long_context; return c != null ? '<span class="mono">' + esc(c.toLocaleString()) + "</span>" : null; });
  h += cmpRow("Runtime limitations", list, function (s) {
    var lim = (s.caveats || []).filter(function (c) { return /context|YaRN|>\s*\d|limit/i.test(c); });
    return lim.length ? esc(lim[0]) : null;
  });

  h += grpRow("Performance", n);
  h += cmpRow("Single-stream decode", list, function (s) { return metricCell(s, "decode_chat", true) === '<span class="na">no measurement</span>' ? (function () {
    var r = repDecode(s);
    return r ? '<b class="num">' + esc(r.value) + "</b> tok/s" + '<span class="cond">' + esc(condOf(r)) + "</span>" : '<span class="na">no measurement</span>';
  })() : metricCell(s, "decode_chat", true); }, perfFlag);
  h += cmpRow("Prefill", list, function (s) { return metricCell(s, "prefill_tok_s"); }, perfFlag);
  h += cmpRow("Time to first token", list, function (s) { return metricCell(s, "ttft_ms"); }, perfFlag);
  h += cmpRow("Aggregate throughput", list, function (s) { return metricCell(s, "decode_agg"); }, perfFlag);
  h += cmpRow("Per-stream at load", list, function (s) { return metricCell(s, "decode_per_stream", false); }, perfFlag);
  h += cmpRow("Concurrency recorded", list, function (s) {
    var c = uniq(speeds(s).map(function (m) { return m.concurrency; }).filter(function (x) { return x != null; }));
    return c.length ? esc(c.sort(function (a, b) { return a - b; }).join(", ") + " stream(s)") : null;
  });
  h += cmpRow("Statistic type", list, function (s) {
    var st = uniq(speeds(s).map(function (m) { return m.stat; }).filter(Boolean));
    return st.length ? esc(st.join(", ")) : na("unstated");
  }, perfFlag);
  h += cmpRow("Measurement protocol", list, function (s) {
    var r = repDecode(s) || aggDecode(s);
    return r && r.method ? esc(r.method) : null;
  });

  h += grpRow("Trust", n);
  DIMS.forEach(function (d) {
    h += cmpRow(d[1] + " confidence", list, function (s) {
      var v = conf(s)[d[0]], l = LV[v.k];
      return '<span class="' + l.cls + '">' + esc(l.g + " " + v.t) + '</span><span class="cond">' + esc(v.why) + "</span>";
    });
  });
  h += cmpRow("Last verification", list, function (s) { return esc((s.updated || "") + " · " + freshness(s).word); });
  h += cmpRow("Source quality", list, function (s) {
    var kinds = {};
    (s.sources || []).forEach(function (x) { kinds[x.kind] = (kinds[x.kind] || 0) + 1; });
    return esc(Object.keys(kinds).map(function (k) { return kinds[k] + " " + k; }).join(", ") || "");
  });

  h += grpRow("Risks", n);
  h += cmpRow("Known failures", list, function (s) {
    var f = failures(s);
    return f.length ? '<ul class="notes bad" style="font-size:12.5px">' + f.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("") + "</ul>"
      : '<span class="g">' + esc("none recorded") + "</span>";
  });
  h += cmpRow("Disabled capabilities", list, function (s) {
    var c = capConflicts(s);
    return c.length ? '<span class="mark m-bad">' + esc("✕ " + c.join(", ")) + "</span>" : '<span class="g">' + esc("none") + "</span>";
  });
  h += cmpRow("Family quality regressions", list, function (s) {
    var r = modelOf(s).known_regressions || [];
    return r.length ? '<ul class="notes warn" style="font-size:12.5px">' + r.map(function (c) { return "<li>" + esc(c) + "</li>"; }).join("") + "</ul>"
      : '<span class="g">' + esc("none recorded for this family") + "</span>";
  });
  h += cmpRow("Caveats", list, function (s) {
    var c = (s.caveats || []).filter(function (x) { return failures(s).indexOf(x) < 0; });
    return c.length ? '<ul class="notes warn" style="font-size:12.5px">' + c.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>"
      : '<span class="g">' + esc("none recorded") + "</span>";
  });
  h += cmpRow("Maintenance status", list, function (s) { return esc((s.status || "unrecorded") + " · " + freshness(s).word); });

  h += "</tbody></table></div>";
  h += '<div class="cmp-key">' + list.map(function (s, i) {
    return "<span><b>" + esc(String.fromCharCode(65 + i)) + "</b> " + esc(s.title) + "</span>";
  }).join("") + "</div></div>";
  el("main").innerHTML = h;
}

/* ----------------------------------------------------------- my hardware */
var HW_FIELDS = [
  ["os", "Operating system", "select", ["", "macos", "linux", "windows"]],
  ["chip", "Exact CPU or Apple chip", "text"],
  ["gpu", "Exact GPU", "text"],
  ["gpuCount", "GPU count", "number"],
  ["ramGb", "RAM (GB)", "number"],
  ["vramGb", "VRAM (GB)", "number"],
  ["unified", "Memory layout", "select", ["", "unified", "separate"]],
  ["diskGb", "Free storage (GB)", "number"],
  ["driver", "Driver version", "text"],
  ["runtime", "Runtime version", "text"],
  ["powerW", "Power limit (W, optional)", "number"]
];
function blankProfile() {
  return { name: "", os: "", chip: "", gpu: "", gpuCount: null, ramGb: null, vramGb: null,
    unified: "", diskGb: null, driver: "", runtime: "", powerW: null, deviceId: "", detected: {} };
}
function defaultReserve(p) {
  if (state.assume.reserve != null) return state.assume.reserve;
  return p && p.os === "macos" ? 6 : p && p.os === "linux" ? 4 : 8;
}
function availableGb(p) {
  if (!p) return null;
  if (p.unified === "separate") return p.vramGb != null ? p.vramGb : null;
  if (p.ramGb != null) return p.ramGb;
  if (p.vramGb != null) return p.vramGb;
  return null;
}
function profileClasses(p) {
  if (!p) return [];
  if (p.deviceId) {
    var out = [p.deviceId], a = (HW[p.deviceId] || {}).arch;
    Object.keys(HW).forEach(function (id) { if (id !== p.deviceId && HW[id].arch === a) out.push(id); });
    return out;
  }
  var ram = p.ramGb, out2 = [];
  var chip = (p.chip || "") + " " + (p.gpu || "");
  if (/GB10|Grace|Spark|PGX/i.test(chip)) return ["dgx-spark", "thinkstation-pgx"];
  if (p.os === "macos" || /Apple|M[1-9]\b/i.test(chip)) {
    if (ram != null && ram >= 96) out2.push("mac-128gb");
    if (ram == null || ram < 96) out2.push("mac-64gb");
    if (ram != null && ram >= 96) out2.push("mac-64gb");
    return out2;
  }
  if ((p.gpuCount || 1) > 1) return ["gpu-multigpu-72gb", "gpu-24gb"];
  return ["gpu-24gb"];
}
function archFamily(id) {
  var a = (HW[id] || {}).arch || "";
  return /Metal/i.test(a) ? "apple" : "nvidia";
}
function profileArch(p) {
  if (p.deviceId) return archFamily(p.deviceId);
  if (p.os === "macos" || /Apple|M[1-9]\b/i.test((p.chip || "") + (p.gpu || ""))) return "apple";
  return "nvidia";
}
function kvGb(s, assume) {
  var b = modelOf(s).kv_bytes_per_token;
  if (b == null) return null;
  return (b * assume.context * assume.concurrency) / (1024 * 1024 * 1024);
}
function classify(s, p) {
  var a = state.assume, reserve = defaultReserve(p);
  var req = (s.requirements || {}).memory_gb;
  var raw = availableGb(p);
  var avail = raw == null ? null : Math.max(0, raw - reserve);
  var classes = profileClasses(p);
  var onHw = (s.hardware || []).filter(function (id) { return classes.indexOf(id) >= 0; });
  var measured = (s.measurements || []).length > 0;
  var exact = onHw.some(function (id) { return (HW[id] || {}).measured_by_us === true; }) &&
    p.deviceId && onHw.indexOf(p.deviceId) >= 0 && measured;
  var archOk = (s.hardware || []).some(function (id) { return archFamily(id) === profileArch(p); });

  var group, verdict;
  if (req != null && avail != null && req > avail) {
    group = "unsupported";
    verdict = "Will not fit as recorded: this recipe records a " + gb(req) + " resident requirement and " +
      gb(Math.round(avail * 10) / 10) + " is available after a " + gb(reserve) + " reserve.";
  } else if (exact) {
    group = "exact";
    verdict = "Verified on this exact machine. Measurements on this record were taken on " +
      ((HW[p.deviceId] || {}).name || p.deviceId) + ", the device this profile names.";
  } else if (onHw.length && (measured || req != null)) {
    group = "similar";
    verdict = "Verified on similar hardware: recorded on " + onHw.map(function (id) { return (HW[id] || {}).name; }).join(" and ") +
      ", which is a hardware class rather than your exact device." +
      (req != null && avail != null ? " Its recorded " + gb(req) + " requirement leaves approximately " +
        gb(Math.round((avail - req) * 10) / 10) + " free on your machine." : "");
  } else if (req != null && avail != null) {
    group = "estimated";
    verdict = "Likely to fit with approximately " + gb(Math.round((avail - req) * 10) / 10) + " remaining, assuming " +
      ctx(a.context) + " context and " + (a.concurrency === 1 ? "one active conversation" : a.concurrency + " concurrent streams") +
      ". This recipe has not been tested on this exact " + (p.chip || p.gpu || "configuration") + ".";
  } else {
    group = "uncertain";
    verdict = req == null
      ? "Uncertain: this recipe records no resident memory requirement, so nothing can be worked out about whether it fits."
      : "Uncertain: your profile does not record the memory figure this calculation needs.";
  }
  if (!archOk) {
    verdict += " Note: this recipe is only recorded on " +
      uniq((s.hardware || []).map(function (id) { return archFamily(id) === "apple" ? "Apple Silicon" : "NVIDIA hardware"; })).join(" and ") +
      ", and your profile is " + (profileArch(p) === "apple" ? "Apple Silicon" : "NVIDIA") +
      ". Memory is not the binding constraint here — the engine path is.";
    if (group === "estimated") group = "uncertain";
  }
  return { group: group, verdict: verdict, req: req, avail: avail, reserve: reserve, onHw: onHw, exact: exact, archOk: archOk };
}
var GROUPS = [
  ["exact", "● Verified on this exact machine", "v-ok", "A measurement on this record was taken on the device this profile names."],
  ["similar", "● Verified on similar hardware", "v-ok", "Recorded on a hardware class you belong to, not on your exact device."],
  ["estimated", "◐ Estimated to fit", "v-est", "No evidence on this hardware. The recipe's own recorded requirement fits your memory."],
  ["uncertain", "○ Uncertain", "v-none", "Something the calculation needs is not recorded, or the engine path is not recorded on your architecture."],
  ["unsupported", "✕ Will not fit as recorded", "v-bad", "The recorded resident requirement exceeds what is available. Often the most useful group: it says what a bigger machine buys you."]
];
function calcTable(s, r, p) {
  var v = s.variation || {}, req2 = s.requirements || {}, kv = kvGb(s, state.assume);
  var rows = [
    ["Model memory", (gb(v.size_gb) || "not recorded"), "artifact size, from the HuggingFace tree endpoint"],
    ["Runtime buffers", r.req != null && v.size_gb != null && r.req > v.size_gb
      ? "included — " + gb(Math.round((r.req - v.size_gb) * 10) / 10) + " above the artifact"
      : "not recorded separately",
      req2.notes || "the recipe's own resident figure is the primary input"],
    ["KV-cache allowance", kv != null ? gb(Math.round(kv * 100) / 100) : "not derivable",
      kv != null ? "from this family's recorded " + modelOf(s).kv_bytes_per_token.toLocaleString() + " bytes/token at the assumed context and concurrency"
        : "this model family does not record bytes per token, so no KV figure can be computed. It is never estimated from parameter count."],
    ["Assumed context", ctx(state.assume.context) + " tokens", "your assumption, adjustable above"],
    ["Assumed concurrency", state.assume.concurrency === 1 ? "1 stream" : state.assume.concurrency + " streams", "your assumption, adjustable above"],
    ["Safety reserve", gb(r.reserve), "an assumption about your machine, not a claim about this recipe"],
    ["CPU / disk offload", /offload|stream|ssd|mmap/i.test(req2.notes || "") ? req2.notes : "none recorded", ""]
  ];
  var h = '<table class="calc-tab"><tbody>' + rows.map(function (x) {
    return "<tr><th>" + esc(x[0]) + "</th><td><b>" + esc(x[1]) + "</b>" +
      (x[2] ? '<br><span class="g">' + esc(x[2]) + "</span>" : "") + "</td></tr>";
  }).join("");
  h += '<tr class="tot"><th>Recorded resident</th><td><b>' + esc(gb(r.req) || "not recorded") + "</b></td></tr>" +
    "<tr><th>Your usable memory</th><td><b>" + esc(r.avail != null ? gb(Math.round(r.avail * 10) / 10) : "not recorded") + "</b>" +
    (r.avail != null ? '<br><span class="g">' + esc(gb(availableGb(p)) + " less the " + gb(r.reserve) + " reserve") + "</span>" : "") + "</td></tr>" +
    "<tr><th>Remaining</th><td><b>" + esc(r.req != null && r.avail != null ? gb(Math.round((r.avail - r.req) * 10) / 10) : "not derivable") + "</b></td></tr>" +
    "<tr><th>Evidence</th><td>" + esc(r.exact ? "Exact device." : r.onHw.length ? "Similar hardware — recorded on a class, not your device." : "No evidence on your hardware.") +
    (r.onHw.length ? '<br><span class="g">' + esc("Recorded on: " + r.onHw.map(function (id) { return (HW[id] || {}).name; }).join("; ")) + "</span>" : "") + "</td></tr>";
  return h + "</tbody></table>";
}
function resultCard(s, r, p) {
  var g = GROUPS.filter(function (x) { return x[0] === r.group; })[0];
  var picked = state.compare.indexOf(s.id) >= 0;
  return '<div class="res ' + g[2] + '"><div class="res-top"><h3><a href="#/recipes/' + esc(s.id) + '">' + esc(s.title) + "</a></h3>" +
    evStrip(s) + "</div>" +
    '<p class="verdict">' + esc(r.verdict) + "</p>" +
    '<details class="calc"><summary>' + esc("▸ How this was worked out") + "</summary>" + calcTable(s, r, p) + "</details>" +
    '<div class="res-act"><label class="mark m-none" style="cursor:pointer"><input type="checkbox" class="cbx" data-cmp="' +
    esc(s.id) + '"' + (picked ? " checked" : "") + ' aria-label="' + esc("Compare " + s.title) + '"> compare</label>' +
    '<a class="btn" href="#/recipes/' + esc(s.id) + '">' + esc("open recipe →") + "</a>" +
    '<span class="g" style="font-size:12px">' + esc(((ENG[(s.engine || {}).id] || {}).name || "?") + " · " + s.variation.quant + " · " + complexityWord(s)) + "</span></div></div>";
}

var GOALS = [
  ["chat", "General chat", "filter", null],
  ["coding", "Coding", "evidence-only", null],
  ["vision", "Vision", "filter", function (s) { return (s.capabilities || {}).vision === true; }],
  ["tools", "Tool use", "filter", function (s) { return (s.capabilities || {}).tools === true; }],
  ["long", "Long documents", "filter", function (s) { return ((s.capabilities || {}).long_context || 0) >= 131072; }],
  ["api", "Single-user API", "filter", function (s) { return ((ENG[(s.engine || {}).id] || {}).api || []).indexOf("openai") >= 0; }],
  ["multi", "Multi-user serving", "filter", function (s) { return !!aggDecode(s); }],
  ["easy", "Lowest setup complexity", "sort", function (s) { return -complexity(s); }],
  ["fast", "Highest measured throughput", "sort", function (s) { var r = repDecode(s); return r ? r.value : -1; }]
];

function viewHardware() {
  var p = state.profile;
  setRail("");
  el("mast-sub").innerHTML = esc("Check the directory against one machine. Nothing here narrows the Directory, and no unconditional “fits” verdict is ever shown.");

  var h = '<div class="hw"><section class="hw-pane" aria-label="Your machine"><h2 class="lbl" style="font-size:11px">Your machine</h2>';
  h += '<div class="hw-modes">' +
    '<button type="button" class="btn" id="hw-detect">Detect this machine</button>' +
    '<label class="fld"><select id="hw-known" aria-label="Select a known device"><option value="">Known device…</option>' +
    Object.keys(HW).map(function (id) {
      return '<option value="' + esc(id) + '"' + (p && p.deviceId === id ? " selected" : "") + ">" + esc(HW[id].name) + "</option>";
    }).join("") + "</select></label>" +
    '<button type="button" class="btn" id="hw-import">Import profile</button>' +
    '<button type="button" class="btn" id="hw-export"' + (p ? "" : " disabled") + ">Export profile</button>" +
    "</div>";
  h += '<div id="hw-detect-out"></div>';
  function fieldHtml(f) {
    var val = p ? p[f[0]] : "";
    var det = p && p.detected && p.detected[f[0]];
    var inner;
    if (f[2] === "select") {
      inner = '<select id="hwf-' + f[0] + '" data-hwf="' + f[0] + '" aria-label="' + esc(f[1]) + '">' + f[3].map(function (o) {
        return '<option value="' + esc(o) + '"' + (String(val || "") === o ? " selected" : "") + ">" + esc(o || "—") + "</option>";
      }).join("") + "</select>";
    } else {
      inner = '<input type="' + (f[2] === "number" ? "number" : "text") + '" id="hwf-' + f[0] + '" data-hwf="' + f[0] +
        '" aria-label="' + esc(f[1]) + '" value="' + esc(val == null ? "" : val) + '">';
    }
    return '<label class="fld"><span class="lbl">' + esc(f[1]) +
      (det ? ' <span style="color:var(--ok)">' + esc("detected") + "</span>" : "") + "</span>" + inner + "</label>";
  }
  var PRIMARY = ["os", "chip", "gpu", "gpuCount", "ramGb", "vramGb", "unified"];
  h += '<div class="hw-form two-up">' + HW_FIELDS.filter(function (f) { return PRIMARY.indexOf(f[0]) >= 0; }).map(fieldHtml).join("") + "</div>";
  h += '<details class="calc"><summary>' + esc("▸ More machine detail (optional)") + '</summary><div class="hw-form two-up" style="margin-top:8px">' +
    HW_FIELDS.filter(function (f) { return PRIMARY.indexOf(f[0]) < 0; }).map(fieldHtml).join("") + "</div></details>";
  h += '<div class="res-act" style="margin-top:11px"><button type="button" class="btn btn-p" id="hw-save">Save profile</button>' +
    '<button type="button" class="btn" id="hw-clear">Clear</button></div>';
  var saved = store("qlr.profiles.v2") || [];
  if (saved.length) h += '<p class="det-line">' + esc("Saved: ") + saved.map(function (x, i) {
    return '<button type="button" class="btn" style="height:22px;padding:0 7px" data-load="' + i + '">' + esc(x.name || "profile " + (i + 1)) + "</button>";
  }).join(" ") + "</p>";
  h += '<div class="privacy"><b>' + esc("Nothing leaves this device.") + "</b> " +
    esc("The whole dataset is inlined in this page, so it makes no network request after load — you can confirm that in your browser's network panel. Detection reads only navigator.userAgentData, navigator.hardwareConcurrency, navigator.deviceMemory, the WebGPU adapter description and the WebGL renderer string. Profiles are stored in this browser only.") + "</div>";
  h += "</section><section aria-label=\"Compatibility results\">";

  if (!p) {
    h += '<div class="empty"><h2>' + esc("No machine described yet") + "</h2>" +
      "<p>" + esc("Detect this machine, pick one of the six hardware classes the dataset records, or type your own. Every field is optional — a missing field degrades the result rather than blocking it, and the result says which field it lacked.") + "</p>" +
      "<p>" + esc("Whatever you enter stays in this browser. The Directory is unaffected either way: nothing here filters it.") + "</p>" +
      '<div class="acts"><a class="btn" href="#/">Browse the full directory instead</a></div></div>';
    return finishHardware(h);
  }

  var a = state.assume;
  h += '<p class="lede">' + esc(SETUPS.length + " recipes checked against ") + "<b>" + esc(p.name || p.chip || p.gpu || "your machine") + "</b></p>";
  h += '<div class="assump"><label class="fld"><span class="lbl">Assumed context</span><select id="as-ctx">' +
    [4096, 8192, 16384, 32768, 131072, 262144].map(function (n) {
      return '<option value="' + n + '"' + (a.context === n ? " selected" : "") + ">" + esc(ctx(n)) + "</option>";
    }).join("") + "</select></label>" +
    '<label class="fld"><span class="lbl">Concurrent streams</span><select id="as-conc">' +
    [1, 2, 4, 8, 16, 48].map(function (n) {
      return '<option value="' + n + '"' + (a.concurrency === n ? " selected" : "") + ">" + n + "</option>";
    }).join("") + "</select></label>" +
    '<label class="fld"><span class="lbl">Safety reserve (GB)</span><input type="number" id="as-res" value="' + defaultReserve(p) + '"></label>' +
    '<span class="g" style="font-size:12px;max-width:32ch">' + esc("These are assumptions about your machine and your use, not claims from the dataset. Every result states them.") + "</span></div>";

  h += '<details class="calc" style="margin-top:12px"><summary>' + esc("▸ Narrow by what you want to do (optional)") + "</summary>" +
    '<div class="filters" style="margin-top:9px">' + GOALS.map(function (g) {
      return '<button type="button" class="btn' + (state.goal === g[0] ? " on" : "") + '" data-goal="' + g[0] + '">' + esc(g[1]) + "</button>";
    }).join("") + "</div>" +
    '<p class="adv-note">' + esc("A goal filters or sorts on recorded facts only. Model capability belongs to the model family, runtime support belongs to the recipe, and task quality needs comparable benchmark evidence — the three are never conflated, and no recipe is ever labelled “best for” anything.") + "</p></details>";

  var goal = GOALS.filter(function (g) { return g[0] === state.goal; })[0];
  var pool = SETUPS.slice();
  if (goal && goal[2] === "filter" && goal[3]) pool = pool.filter(goal[3]);
  if (goal && goal[2] === "evidence-only") {
    var withEv = SETUPS.filter(function (s) {
      return (s.measurements || []).some(function (m) { return /bench_code|bench_humaneval|decode_code/.test(m.metric); });
    });
    h += '<div class="banner b-info" style="margin-top:12px"><h3>' + esc("Coding does not reorder anything") + "</h3><p>" +
      esc("Only " + withEv.length + " of " + SETUPS.length + " recipes carry any coding-related measurement, and they come from different harnesses. Ranking across harnesses would be false precision, so this goal filters to the recipes that carry coding evidence and names the harness on each — judge them yourself.") + "</p></div>";
    pool = withEv;
  }
  if (goal && goal[2] === "sort") pool = pool.slice().sort(function (x, y) { return goal[3](y) - goal[3](x); });

  var buckets = { exact: [], similar: [], estimated: [], uncertain: [], unsupported: [] };
  pool.forEach(function (s) {
    var r = classify(s, p);
    buckets[r.group].push({ s: s, r: r });
  });
  GROUPS.forEach(function (g) {
    var items = buckets[g[0]], open = g[0] !== "unsupported" && g[0] !== "uncertain";
    h += '<button type="button" class="grp-hd" data-grp="' + g[0] + '" aria-expanded="' + open + '" aria-controls="grp-' + g[0] + '">' +
      "<h2>" + esc(g[1]) + '</h2><span class="n">' + items.length + "</span></button>" +
      '<p class="det-line" style="max-width:74ch">' + esc(g[3]) + "</p>" +
      '<div id="grp-' + g[0] + '"' + (open ? "" : " hidden") + ">";
    if (!items.length) h += '<p class="prose" style="margin-top:8px">' + esc("Nothing lands in this group for this machine, which is itself the answer.") + "</p>";
    else h += items.map(function (x) { return resultCard(x.s, x.r, p); }).join("");
    h += "</div>";
  });
  finishHardware(h);
}
function finishHardware(h) { el("main").innerHTML = h + "</section></div>"; }

/* ------------------------------------------------------------- detection */
function detectMachine(cb) {
  var got = {}, notes = [], done = 0, expect = 1;
  var nav = navigator;
  var uad = nav.userAgentData;
  var plat = (uad && uad.platform) || nav.platform || "";
  if (/mac/i.test(plat)) got.os = "macos";
  else if (/win/i.test(plat)) got.os = "windows";
  else if (/linux|x11/i.test(plat)) got.os = "linux";
  if (got.os) notes.push(["Platform", got.os, "from navigator.userAgentData"]);
  else notes.push(["Platform", "not detectable", "the browser does not expose it"]);

  if (nav.hardwareConcurrency) notes.push(["CPU threads", String(nav.hardwareConcurrency), "logical cores, from navigator.hardwareConcurrency — not the chip name"]);
  else notes.push(["CPU threads", "not detectable", "navigator.hardwareConcurrency unavailable"]);

  if (nav.deviceMemory) notes.push(["RAM", nav.deviceMemory + " GB reported", "navigator.deviceMemory rounds down to a power of two and caps at 8 — enter your real figure below"]);
  else notes.push(["RAM", "not detectable", "navigator.deviceMemory is Chromium-only — enter it yourself"]);

  var gl = null;
  try {
    var c = document.createElement("canvas");
    gl = c.getContext("webgl") || c.getContext("experimental-webgl");
    if (gl) {
      var ext = gl.getExtension("WEBGL_debug_renderer_info");
      var r = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
      if (r) { got.gpu = String(r); notes.push(["GPU", got.gpu, "from the WebGL renderer string — often masked for fingerprinting reasons"]); }
    }
  } catch (e) { /* blocked contexts are expected */ }
  if (!got.gpu) notes.push(["GPU", "not detectable", "the WebGL renderer string is masked or unavailable"]);

  notes.push(["VRAM · free disk · driver · runtime · power limit", "not detectable", "no browser API exposes these — they are always manual"]);

  function finish() {
    done++;
    if (done >= expect) cb(got, notes);
  }
  var timer = setTimeout(function () { expect = 0; cb(got, notes); }, 2000);
  if (nav.gpu && nav.gpu.requestAdapter) {
    nav.gpu.requestAdapter().then(function (ad) {
      try {
        var info = ad && (ad.info || (ad.requestAdapterInfo ? null : null));
        if (info && (info.vendor || info.architecture)) {
          var t = [info.vendor, info.architecture, info.description].filter(Boolean).join(" ");
          if (t.trim()) { got.gpu = got.gpu || t; notes.push(["WebGPU adapter", t, "from navigator.gpu adapter info"]); }
        } else notes.push(["WebGPU adapter", "masked", "the browser exposes no adapter vendor or architecture"]);
      } catch (e) { notes.push(["WebGPU adapter", "masked", "adapter info unavailable"]); }
      clearTimeout(timer); if (expect) finish();
    }, function () {
      notes.push(["WebGPU adapter", "unavailable", "no WebGPU adapter could be requested"]);
      clearTimeout(timer); if (expect) finish();
    });
  } else {
    notes.push(["WebGPU adapter", "unavailable", "navigator.gpu is not present in this browser"]);
    clearTimeout(timer); finish();
  }
}

/* -------------------------------------------------------- other routes */
function viewRecipe(id) {
  var s = SETUPS.filter(function (x) { return x.id === id; })[0];
  setRail("");
  if (!s) return notFound("No recipe with the id " + id + " is in this dataset.");
  var m = modelOf(s), c = conf(s);
  el("mast-sub").innerHTML = esc(s.slug_note || "");
  var h = '<div class="page"><p class="crumb"><a href="#/recipes">Recipes</a> ' + esc("→") +
    ' <a href="#/models/' + esc(s.model) + '">' + esc(m.name || s.model) + "</a> " + esc("→ this recipe") + "</p>" +
    "<h1>" + esc(s.title) + "</h1>" +
    '<div class="res-act" style="margin-top:10px">' + evStrip(s) +
    '<span class="mark m-none">' + esc(READY_GLYPH[readiness(s)] + " " + READY_WORD[readiness(s)]) + "</span>" +
    '<span class="mark m-none">' + esc(s.status || "status unrecorded") + "</span>" +
    '<span class="mark m-none">' + esc("updated " + (s.updated || "—") + " · " + freshness(s).word) + "</span>" +
    '<label class="mark m-none" style="cursor:pointer"><input type="checkbox" class="cbx" data-cmp="' + esc(s.id) + '"' +
    (state.compare.indexOf(s.id) >= 0 ? " checked" : "") + ' aria-label="' + esc("Compare " + s.title) + '"> compare</label></div>';
  h += '<div class="psec">' + detailBody(s, { page: true }) + "</div></div>";
  el("main").innerHTML = h;
}
function viewModel(id) {
  var m = MODELS[id];
  setRail("");
  if (!m) return notFound("No model family with the id " + id + " is in this dataset.");
  var list = sorted(SETUPS.filter(function (s) { return s.model === id; }));
  var a = m.architecture || {}, c = m.context || {};
  el("mast-sub").innerHTML = esc(m.summary ? String(m.summary).slice(0, 190) : "");
  var h = '<div class="page wide"><p class="crumb"><a href="#/">Models</a> ' + esc("→ model family") + "</p>" +
    "<h1>" + esc(m.name) + "</h1>";
  if (m.summary) h += '<p class="lede">' + esc(m.summary) + "</p>";
  h += '<div class="psec model-page-baseline">' + modelPreview(m) + '</div>';
  h += '<div class="psec"><h2>Architecture and limits</h2><div class="kv two">' +
    "<dt>Generation</dt><dd>" + esc(m.generation) + "</dd>" +
    "<dt>Architecture</dt><dd>" + esc(a.kind === "moe" ? "MoE" : a.kind || "") + (a.hybrid ? esc(" · hybrid") : "") + "</dd>" +
    "<dt>Total params</dt><dd>" + (a.params_total_b != null ? esc(a.params_total_b + "B") : na()) + "</dd>" +
    "<dt>Active params</dt><dd>" + (a.params_active_b != null ? esc(a.params_active_b + "B") : (a.kind === "dense" ? esc("all — dense") : na())) + "</dd>" +
    "<dt>Layers</dt><dd>" + (a.layers != null ? esc(a.layers) : na()) + (a.layer_mix ? ' <span class="g">' + esc(a.layer_mix) + "</span>" : "") + "</dd>" +
    "<dt>MTP head</dt><dd>" + (a.mtp_head == null ? na() : esc(a.mtp_head ? "yes" : "no")) + "</dd>" +
    "<dt>Native context</dt><dd>" + (c.native != null ? esc(c.native.toLocaleString()) : na("unstated by the publisher")) + "</dd>" +
    "<dt>Max context</dt><dd>" + (c.max != null ? esc(c.max.toLocaleString()) : na("not stated")) + "</dd>" +
    (c.extension ? "<dt>Extension</dt><dd>" + esc(c.extension) + "</dd>" : "") +
    "<dt>Modalities</dt><dd>" + esc((m.modalities || []).join(" · ")) + "</dd>" +
    "<dt>Weight license</dt><dd>" + esc(m.license || "") + "</dd>" +
    "<dt>Released</dt><dd>" + (m.released ? esc(m.released) : na()) + "</dd>" +
    "<dt>Official card</dt><dd><a href=\"" + esc(m.url) + '" target="_blank" rel="noopener">' + esc(m.url) + "</a></dd>" +
    "</div></div>";
  if ((m.known_regressions || []).length) h += '<div class="psec"><h2 style="color:var(--warn)">' + esc("▲ Known regressions") +
    '</h2><ul class="notes warn">' + m.known_regressions.map(function (r) { return "<li>" + esc(r) + "</li>"; }).join("") + "</ul></div>";
  if (m.sampler_guidance) h += '<div class="psec"><h2>Sampler guidance</h2><p>' + esc(m.sampler_guidance) + "</p></div>";
  if (m.fit_note) h += '<div class="psec"><h2>Fit note</h2><p>' + esc(m.fit_note) + "</p></div>";
  h += '<div class="psec"><h2>' + esc(plural(list.length, "recipe") + " for this family") + "</h2>" +
    rowsHtml(list, m.name) + "</div></div>";
  el("main").innerHTML = h;
}
function viewPublisher(id) {
  var p = PUB[id];
  setRail("");
  if (!p) return notFound("No publisher with the id " + id + " is in this registry.");
  var asPub = SETUPS.filter(function (s) { return (s.variation || {}).publisher === id; });
  var asBuilder = SETUPS.filter(function (s) { return s.builder === id; });
  el("mast-sub").innerHTML = esc(p.role || "");
  var h = '<div class="page wide"><p class="crumb"><a href="#/recipes">Recipes</a> ' + esc("→ publisher") + "</p><h1>" + esc(p.name) + "</h1>" +
    '<p class="lede">' + esc(p.role || "") + "</p>" +
    '<div class="psec"><div class="kv two"><dt>Kind</dt><dd>' + esc(p.kind || "") + "</dd>" +
    (p.url ? "<dt>Home</dt><dd><a href=\"" + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.url) + "</a></dd>" : "") +
    "<dt>Artifacts published</dt><dd>" + asPub.length + "</dd><dt>Recipes maintained</dt><dd>" + asBuilder.length + "</dd></div></div>";
  if (asPub.length) h += '<div class="psec"><h2>' + esc("Artifacts published " + "(" + asPub.length + ")") + "</h2>" + rowsHtml(sorted(asPub), p.name + " artifacts") + "</div>";
  if (asBuilder.length) h += '<div class="psec"><h2>' + esc("Recipes maintained (" + asBuilder.length + ")") + "</h2>" + rowsHtml(sorted(asBuilder), p.name + " recipes") + "</div>";
  if (!asPub.length && !asBuilder.length) h += '<div class="empty"><h2>Nothing recorded yet</h2><p>' +
    esc("This publisher is in the attribution registry but no setup currently references it.") + "</p></div>";
  el("main").innerHTML = h + "</div>";
}
function notFound(msg) {
  el("mast-sub").textContent = "";
  el("main").innerHTML = '<div class="page"><h1>Not found</h1><p class="lede">' + esc(msg) + "</p>" +
    '<div class="empty"><h2>Where to go instead</h2><ul class="notes">' +
    '<li><a href="#/">Models</a> — choose a model and inspect its practical minimum</li>' +
    '<li><a href="#/recipes">Recipes</a> — every recipe, no personalization</li>' +
    '<li><a href="#/hardware">My Hardware</a> — check the directory against one machine</li>' +
    '<li><a href="#/compare">Compare</a> — two to four recipes side by side</li>' +
    '<li><a href="#/methodology">Methodology</a> — what the evidence labels mean</li>' +
    "</ul></div></div>";
}

function viewMethodology() {
  setRail("");
  el("mast-sub").innerHTML = esc("How the evidence labels are defined, how derived values are computed, and what the dataset does not record.");
  var tiers = { box: 0, forum: 0, vendor: 0, none: 0 };
  SETUPS.forEach(function (s) { tiers[s.provenance_tier || "none"]++; });
  var noSpeed = SETUPS.filter(function (s) { return !speeds(s).length; }).length;
  var noCmd = SETUPS.filter(function (s) { return !(s.run || {}).command; }).length;
  var kvKnown = Object.keys(MODELS).filter(function (id) { return MODELS[id].kv_bytes_per_token != null; }).length;

  var h = '<div class="page"><h1>Methodology</h1>' +
    '<p class="lede">' + esc("This directory would rather show a slow number with its source than a fast number without one. Everything below states where a value comes from, and what it does not mean.") + "</p>";

  h += '<div class="psec"><h2>Evidence tiers, never blended</h2>' +
    '<div class="kv"><dt>box</dt><dd>' + esc("Measured on the owner's own hardware, with a date, a sample count and a stated method. " + tiers.box + " recipes.") + "</dd>" +
    "<dt>forum</dt><dd>" + esc("Reported by a community builder, with a resolving source URL. " + tiers.forum + " recipes.") + "</dd>" +
    "<dt>vendor</dt><dd>" + esc("Claimed by the publisher of the artifact. " + tiers.vendor + " recipes.") + "</dd>" +
    "<dt>no measurement</dt><dd>" + esc("A sourced runnable lane that nobody has measured. " + tiers.none + " recipes — nearly half the directory, and it is shown as such rather than hidden.") + "</dd></div>" +
    "<p>" + esc("A number with no source is deleted, never downgraded and never kept. Tiers are never averaged or mixed inside one figure.") + "</p></div>";

  h += '<div class="psec"><h2>Four confidence dimensions</h2>' +
    "<p>" + esc("One badge cannot answer four different questions. A recipe may have strong installation evidence and no performance evidence at all; the strip shows that shape instead of averaging it away. The order is always recipe, compatibility, performance, capability.") + "</p>";
  var DEFS = [
    ["Recipe confidence", "can I install this?", ["Clean-install tested", "Complete community recipe", "Incomplete recipe"]],
    ["Compatibility confidence", "will it run on my hardware?", ["Exact-device evidence", "Similar-device evidence", "Estimated", "Unknown", "Unsupported"]],
    ["Performance confidence", "is the number real?", ["Controlled repeated measurement", "Repeated community measurement", "Single community report", "Vendor claim", "Unknown"]],
    ["Capability confidence", "does this recipe actually do vision or tools?", ["Tested through this recipe", "Runtime-declared", "Model-declared", "Partial", "Unsupported", "Unknown"]]
  ];
  h += DEFS.map(function (d) {
    return "<h3>" + esc(d[0]) + ' <span class="g">' + esc("— " + d[1]) + "</span></h3><p class=\"tight\">" + esc(d[2].join(" · ")) + "</p>";
  }).join("");
  h += "<p>" + esc("An owner-measured figure from a single boot lands at “repeated community measurement”, not at the top level — the records' own caveats call those runs indicative rather than a guarantee, and the interface agrees with the caveat rather than with the tier label.") + "</p></div>";

  h += '<div class="psec"><h2>How the headline decode figure is chosen</h2>' +
    "<p>" + esc("Single-stream metrics only, in the order chat, code, essay, per-stream, preferring a non-peak statistic where both exist. Aggregate throughput is never promoted into that slot: it is a different quantity, and on this dataset it runs up to 17× the single-stream figure for the same recipe.") + "</p>" +
    "<p>" + esc("Where a recipe records both, the expanded row shows them together — total across N streams, and what each stream actually gets at that load. No number is ever rendered without its metric, its concurrency condition and its provenance.") + "</p></div>";

  h += '<div class="psec"><h2>No quality leaderboard</h2>' +
    "<p>" + esc("Quality canaries come from different harnesses with different prompts and scoring. Ranking across them would be false precision, so they are recorded per recipe and never aggregated into a score. No recipe is labelled best for coding, or best for anything.") + "</p>" +
    "<p>" + esc("Sorting by decode speed is a discovery aid and carries a disclosure that cannot be dismissed. Model capability belongs to the model family, runtime support belongs to the recipe, and task quality needs comparable benchmark evidence — the three are never conflated.") + "</p></div>";

  h += '<div class="psec"><h2>Derived values</h2>' +
    "<p>" + esc("Three things on this site are computed rather than recorded, and are labelled as derived wherever they appear.") + "</p>" +
    "<h3>Setup complexity</h3><p class=\"tight\">" + esc("Engine base — ollama 1, lm-studio 1, llama.cpp 2, mlx-lm 2, vLLM 3, SGLang 3, custom fork 4 — plus 1 if the recipe needs an engine fork, plus 1 if it has more than four steps, plus 1 if it needs a draft model. 1–2 is “one command”, 3–4 “moderate setup”, 5 and above “involved build”.") + "</p>" +
    "<h3>Readiness</h3><p class=\"tight\">" + esc("A copyable command makes a recipe runnable; two or more ordered steps make it a recipe; anything less is a lead. " + noCmd + " of " + SETUPS.length + " recipes carry no single copyable command.") + "</p>" +
    "<h3>Operating system</h3><p class=\"tight\">" + esc("Implied from the tested hardware class's architecture string, because the dataset has no OS field. It is labelled implied everywhere it appears.") + "</p></div>";

  h += '<div class="psec"><h2>Reading-speed anchor</h2>' +
    "<p>" + esc("Roughly 5 tok/s is comfortable adult reading speed, assuming about 250 words per minute and about 0.75 words per token. The constant is stated here so the multiplier is auditable rather than folded silently into a claim.") + "</p></div>";

  h += '<div class="psec"><h2>Coverage</h2><div class="kv two">' +
    "<dt>Runnable recipes</dt><dd>" + SETUPS.length + "</dd>" +
    "<dt>Model families</dt><dd>" + Object.keys(MODELS).length + "</dd>" +
    "<dt>Hardware classes</dt><dd>" + Object.keys(HW).length + "</dd>" +
    "<dt>Engines</dt><dd>" + Object.keys(ENG).length + "</dd>" +
    "<dt>Publishers and builders</dt><dd>" + Object.keys(PUB).length + "</dd>" +
    "<dt>With a speed measurement</dt><dd>" + (SETUPS.length - noSpeed) + "</dd>" +
    "</div></div>";

  h += '<div class="psec"><h2>What this dataset does not record</h2><ul class="notes">' +
    "<li>" + esc("Bytes per token of KV cache on " + (Object.keys(MODELS).length - kvKnown) + " of " + Object.keys(MODELS).length +
      " model families. Without it, a KV-cache allowance cannot be computed, and it is never estimated from parameter count.") + "</li>" +
    "<li>" + esc("Engine version — there is no field for it, so every comparison of engine versions reads “not recorded”.") + "</li>" +
    "<li>" + esc("Operating system as a recorded fact, rather than implied from hardware.") + "</li>" +
    "<li>" + esc("Failures as structured records. They live in caveat prose and are surfaced by matching that prose, which is a stopgap.") + "</li>" +
    "<li>" + esc("Clean-install verification, so the strongest level of recipe confidence is currently unreachable by any entry.") + "</li>" +
    "<li>" + esc("Reddit-sourced numbers. The collection environment is hard-blocked by the platform, so no Reddit-sourced figure is recorded anywhere rather than being recorded unverified.") + "</li>" +
    "</ul></div>";

  h += '<div class="psec"><h2>Scope</h2><p>' +
    esc("The family list covers Qwen 3.0, 3.5, 3.6 and 3.8 text, vision and omni branches with a plausible single-box local lane. Deliberately excluded: cluster-scale models with no single-box lane, sub-4B edge models below the smallest hardware class recorded here, and the embedding, reranker, ASR and TTS families, which are not text-generation serving.") +
    "</p></div></div>";
  el("main").innerHTML = h;
}

function viewContribute() {
  setRail("");
  el("mast-sub").innerHTML = esc("What a recipe needs before it can be accepted, and why a number without a source is deleted rather than downgraded.");
  var h = '<div class="page"><h1>Contribute a recipe</h1>' +
    '<p class="lede">' + esc("The unit of an entry is one runnable setup: one checkpoint, one engine configuration, one hardware class. A model with eight checkpoints across three engines is twenty-four entries, not one row — because that is the thing that actually gets run and actually gets measured.") + "</p>";
  h += '<div class="psec"><h2>What an entry needs</h2><ul class="notes">' +
    "<li>" + esc("A checkpoint with a resolving URL, its publisher, its quantization and its format.") + "</li>" +
    "<li>" + esc("An engine, its configuration string, and whether it needs a fork of that engine.") + "</li>" +
    "<li>" + esc("The hardware class it was run on.") + "</li>" +
    "<li>" + esc("A resident memory requirement, and a disk figure where you know it.") + "</li>" +
    "<li>" + esc("Run instructions: a copyable command, or ordered steps marked as commands or as prose actions. Prose is never dressed up as a command.") + "</li>" +
    "<li>" + esc("At least one source URL that resolves.") + "</li>" +
    "</ul></div>";
  h += '<div class="psec"><h2>What a measurement needs</h2><p>' +
    esc("A metric from the enum, a value and unit, and a provenance tier. Owner-measured figures need a date, a sample count and a method. Community and vendor figures need a source URL. Record concurrency when the source states it, and never derive it from request counts, prompt counts or config names. Say which statistic it is — mean, median or peak — when the source distinguishes them.") + "</p>" +
    "<p>" + esc("A number with no source is deleted. That is the rule, and the fix is never to downgrade the rule.") + "</p></div>";
  h += '<div class="psec"><h2>Negative results are wanted</h2><p>' +
    esc("A slow figure with a method, a quantization that turned out worse than its label suggests, a speculative-decoding path that silently corrupts output — these are among the most valuable rows here. They stay in the dataset, they stay visible in the interface, and they are promoted rather than buried.") + "</p></div>";
  h += '<div class="psec"><h2>The gate</h2><p>' +
    esc("Every change runs directory/check.sh, which validates the data, re-fetches every cited URL, rebuilds the site and exercises the real interface in a headless browser at several widths. Every stage must pass before anything is published. The generated page is never edited by hand.") + "</p>" +
    '<p><a href="https://github.com/shuenrui/qwen-local-run" target="_blank" rel="noopener">' + esc("The repository, the schema and the agent brief") + "</a></p></div></div>";
  el("main").innerHTML = h;
}

/* ---------------------------------------------------------------- router */
function parseHash() {
  var h = location.hash.replace(/^#/, "") || "/";
  var qi = h.indexOf("?");
  var path = qi < 0 ? h : h.slice(0, qi);
  var qs = qi < 0 ? "" : h.slice(qi + 1);
  var q = {};
  qs.split("&").forEach(function (kv) {
    if (!kv) return;
    var i = kv.indexOf("=");
    var k = decodeURIComponent(i < 0 ? kv : kv.slice(0, i));
    q[k] = decodeURIComponent((i < 0 ? "" : kv.slice(i + 1)).replace(/\+/g, " "));
  });
  var parts = path.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
  return { parts: parts, q: q };
}
function writeHash() {
  if (state.route !== "directory") return;
  var q = [];
  if (state.q) q.push("q=" + encodeURIComponent(state.q));
  Object.keys(state.f).forEach(function (k) { if (state.f[k]) q.push(k + "=" + encodeURIComponent(state.f[k])); });
  if (state.sort !== "updated") q.push("sort=" + state.sort);
  if (state.adv) q.push("adv=1");
  var next = "#/recipes" + (q.length ? "?" + q.join("&") : "");
  if (location.hash !== next) history.replaceState(null, "", next);
}
function route() {
  var r = parseHash(), p = r.parts;
  var name = p.length === 0 ? "models-home" : p[0];
  state.route = name === "models-home" ? "models-home" : name === "recipes" ? (p[1] ? "recipe" : "directory") :
    ({ hardware: "hardware", compare: "compare", models: "model", publishers: "publisher",
      methodology: "methodology", contribute: "contribute" }[name] || "404");
  if (state.route === "models-home") {
    state.modelQ = r.q.q || "";
    state.modelGen = r.q.gen || "";
    state.modelArch = r.q.arch || "";
    state.modelBaseline = r.q.baseline === "selected" || r.q.baseline === "missing" ? r.q.baseline : "";
    state.selectedModel = MODELS[r.q.model] ? r.q.model : state.selectedModel;
  }
  if (state.route === "directory") {
    state.q = r.q.q || "";
    state.sort = SORTS[r.q.sort] ? r.q.sort : "updated";
    state.adv = r.q.adv === "1";
    state.f = {};
    Object.keys(r.q).forEach(function (k) {
      if (FACETS[k] || k === "pmin" || k === "pmax") state.f[k] = r.q[k];
      if (FACETS[k] || k === "pmin" || k === "pmax") { if (ADVANCED.indexOf(k) >= 0 || k === "pmin" || k === "pmax") state.adv = true; }
    });
  }
  if (state.route === "compare" && r.q.sel) {
    state.compare = r.q.sel.split(",").filter(function (id) {
      return SETUPS.some(function (s) { return s.id === id; });
    }).slice(0, CMP_MAX);
    sess("qlr.compare", state.compare);
  }
  document.querySelectorAll(".tab").forEach(function (t) {
    var active = state.route === "model" || state.route === "models-home" ? "models-home" :
      state.route === "recipe" || state.route === "directory" ? "directory" : state.route;
    var on = t.getAttribute("data-route") === active;
    if (on) t.setAttribute("aria-current", "page"); else t.removeAttribute("aria-current");
  });
  document.body.setAttribute("data-route", state.route);
  el("shell").style.gridTemplateColumns = state.route === "directory" && !state.mobile && window.innerWidth >= 1180
    ? "var(--rail-w) minmax(0,1fr)" : "minmax(0,1fr)";

  if (state.route === "models-home") viewModelsHome();
  else if (state.route === "directory") { viewDirectory(); writeHash(); }
  else if (state.route === "hardware") viewHardware();
  else if (state.route === "compare") viewCompare();
  else if (state.route === "recipe") viewRecipe(p[1]);
  else if (state.route === "model") viewModel(p[1]);
  else if (state.route === "publisher") viewPublisher(p[1]);
  else if (state.route === "methodology") viewMethodology();
  else if (state.route === "contribute") viewContribute();
  else notFound("The route “" + location.hash + "” does not exist in this directory.");
  renderRail();
  window.scrollTo(0, 0);
}
function setRail(html) { var r = el("rail"); r.innerHTML = html; r.hidden = !html; }
function announce(msg) { var l = el("live"); if (l) l.textContent = msg; }

/* ---------------------------------------------------------------- events */
function nav(hash) { if (location.hash === hash) route(); else location.hash = hash; }
function setFilter(k, v) {
  if (v) state.f[k] = v; else delete state.f[k];
  writeHash(); viewDirectory();
}
var qTimer = null;
document.addEventListener("input", function (e) {
  var t = e.target;
  if (t.id === "q") {
    clearTimeout(qTimer);
    qTimer = setTimeout(function () {
      var pos = t.selectionStart;
      state.q = t.value;
      writeHash(); viewDirectory();
      var nq = el("q");
      if (nq) { nq.focus(); try { nq.setSelectionRange(pos, pos); } catch (err) {} }
    }, 130);
  }
  if (t.id === "model-q") {
    clearTimeout(qTimer);
    qTimer = setTimeout(function () {
      var pos = t.selectionStart;
      state.modelQ = t.value;
      viewModelsHome();
      var nq = el("model-q");
      if (nq) { nq.focus(); try { nq.setSelectionRange(pos, pos); } catch (err) {} }
    }, 130);
  }
  if (t.getAttribute("data-hwf")) {
    var k = t.getAttribute("data-hwf");
    if (!state.profile) state.profile = blankProfile();
    var v = t.value;
    state.profile[k] = (t.type === "number") ? (v === "" ? null : Number(v)) : v;
    if (k === "ramGb" || k === "vramGb" || k === "os" || k === "unified" || k === "chip" || k === "gpu" || k === "gpuCount") {
      clearTimeout(qTimer);
      qTimer = setTimeout(function () { var a = document.activeElement && document.activeElement.id; viewHardware(); var n = a && el(a); if (n) n.focus(); }, 320);
    }
  }
});
document.addEventListener("change", function (e) {
  var t = e.target, f = t.getAttribute("data-f");
  if (t.id === "model-gen") { state.modelGen = t.value; viewModelsHome(); return; }
  if (t.id === "model-arch") { state.modelArch = t.value; viewModelsHome(); return; }
  if (t.id === "model-baseline") { state.modelBaseline = t.value; viewModelsHome(); return; }
  if (f) { setFilter(f, t.value); return; }
  if (t.id === "f-pmin") { setFilter("pmin", t.value); return; }
  if (t.id === "f-pmax") { setFilter("pmax", t.value); return; }
  if (t.id === "sort") { state.sort = t.value; writeHash(); viewDirectory(); return; }
  if (t.id === "hw-known") {
    var id = t.value;
    if (!id) return;
    var hw = HW[id];
    state.profile = blankProfile();
    state.profile.deviceId = id;
    state.profile.name = hw.name;
    state.profile.ramGb = hw.memory_gb;
    state.profile.chip = hw.chip || "";
    state.profile.gpu = hw.gpu || "";
    state.profile.unified = /unified/i.test(hw.memory_type || "") ? "unified" : "separate";
    state.profile.os = /Metal/i.test(hw.arch || "") ? "macos" : "linux";
    state.profile.gpuCount = /multi/i.test(hw.form_factor || "") ? 2 : 1;
    viewHardware();
    return;
  }
  if (t.id === "as-ctx") { state.assume.context = Number(t.value); viewHardware(); return; }
  if (t.id === "as-conc") { state.assume.concurrency = Number(t.value); viewHardware(); return; }
  if (t.id === "as-res") { state.assume.reserve = t.value === "" ? null : Number(t.value); viewHardware(); return; }
  var cmp = t.getAttribute("data-cmp");
  if (cmp && t.type === "checkbox") {
    if (!toggleCompare(cmp)) { t.checked = false; return; }
    document.querySelectorAll('[data-cmp="' + cmp + '"]').forEach(function (n) {
      if (n.type === "checkbox") n.checked = state.compare.indexOf(cmp) >= 0;
    });
    var row = document.querySelector('[data-row="' + cmp + '"]');
    if (row) row.classList.toggle("sel-on", state.compare.indexOf(cmp) >= 0);
  }
});
document.addEventListener("click", function (e) {
  var t = e.target.closest ? e.target.closest("[data-exp],[data-copy],[data-clear],[data-rail-f],[data-rail-clear],[data-jump],[data-cmp],[data-ev],[data-grp],[data-goal],[data-load],[data-model-select],#model-clear,#clear-all,#adv-toggle,#cmp-clear,#theme,#hw-detect,#hw-save,#hw-clear,#hw-export,#hw-import") : null;
  if (!t) {
    hidePop();
    /* Clicking anywhere on a row header toggles it — the expander triangle is
       the keyboard affordance, but pointer users expect the whole row to be
       the target. Interactive children (compare checkbox, buttons, links,
       evidence popovers) and the open detail panel are excluded. */
    var rowEl = e.target.closest ? e.target.closest("[data-row]") : null;
    if (rowEl && !e.target.closest("input,button,a,select,textarea,label,.det-in")) {
      var rid = rowEl.getAttribute("data-row");
      if (state.expanded[rid]) delete state.expanded[rid]; else state.expanded[rid] = 1;
      rerenderRow(rid);
    }
    return;
  }

  if (t.id === "theme") {
    var cur = document.documentElement.getAttribute("data-theme");
    var next = cur === "dark" ? "light" : cur === "light" ? "" : "dark";
    if (next) document.documentElement.setAttribute("data-theme", next);
    else document.documentElement.removeAttribute("data-theme");
    store("qlr.theme", next);
    return;
  }
  var modelSelect = t.getAttribute("data-model-select");
  if (modelSelect) {
    if (state.mobile) { nav("#/models/" + modelSelect); return; }
    state.selectedModel = modelSelect;
    viewModelsHome();
    var selected = document.querySelector('[data-model-select="' + modelSelect + '"]');
    if (selected) selected.focus();
    return;
  }
  if (t.id === "model-clear") {
    state.modelQ = ""; state.modelGen = ""; state.modelArch = ""; state.modelBaseline = "";
    viewModelsHome(); return;
  }
  if (t.id === "m-filters") { state.filtersOpen = !state.filtersOpen; viewDirectory(); return; }
  if (t.id === "adv-toggle") { state.adv = !state.adv; writeHash(); viewDirectory(); return; }
  if (t.id === "clear-all") { state.f = {}; state.q = ""; writeHash(); viewDirectory(); return; }
  if (t.id === "cmp-clear") { state.compare = []; sess("qlr.compare", []); renderRail(); route(); return; }

  var clear = t.getAttribute("data-clear");
  if (clear) { if (clear === "q") state.q = ""; else delete state.f[clear]; writeHash(); viewDirectory(); return; }

  if (t.getAttribute("data-rail-clear")) { state.f = {}; writeHash(); viewDirectory(); return; }
  var rf = t.getAttribute("data-rail-f");
  if (rf) {
    var rv = t.getAttribute("data-rail-v");
    if (rf !== "gen") delete state.f.gen;
    if (rf !== "arch") delete state.f.arch;
    if (rf !== "cap") delete state.f.cap;
    if (state.f[rf] === rv) delete state.f[rf]; else state.f[rf] = rv;
    writeHash(); viewDirectory();
    return;
  }
  var jump = t.getAttribute("data-jump");
  if (jump) { e.preventDefault(); var s = el("h-" + jump); if (s) { s.scrollIntoView(); s.closest(".shelf").focus && s.closest(".shelf").focus(); } spy(); return; }

  var exp = t.getAttribute("data-exp");
  if (exp) {
    if (state.expanded[exp]) delete state.expanded[exp]; else state.expanded[exp] = 1;
    rerenderRow(exp);
    return;
  }
  var cp = t.getAttribute("data-copy");
  if (cp != null && t.classList.contains("copy")) {
    var old = t.textContent;
    function done(ok) { t.textContent = ok ? "copied" : "copy failed"; setTimeout(function () { t.textContent = old; }, 1400); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(cp).then(function () { done(true); }, function () { done(false); });
    else done(false);
    return;
  }
  var cbtn = t.getAttribute("data-cmp");
  if (cbtn && t.tagName === "BUTTON") {
    toggleCompare(cbtn);
    if (state.route === "compare") route(); else rerenderRow(cbtn);
    return;
  }
  var ev = t.getAttribute("data-ev");
  if (ev) { showPop(t, ev); return; }
  var grp = t.getAttribute("data-grp");
  if (grp) {
    var box = el("grp-" + grp), on = box.hidden;
    box.hidden = !on; t.setAttribute("aria-expanded", String(on));
    return;
  }
  var goal = t.getAttribute("data-goal");
  if (goal) { state.goal = state.goal === goal ? null : goal; viewHardware(); return; }
  var load = t.getAttribute("data-load");
  if (load != null) { var arr = store("qlr.profiles.v2") || []; state.profile = arr[+load] || null; viewHardware(); return; }

  if (t.id === "hw-detect") {
    var out = el("hw-detect-out");
    out.innerHTML = '<p class="det-line">' + esc("detecting…") + "</p>";
    detectMachine(function (got, notes) {
      if (!state.profile) state.profile = blankProfile();
      Object.keys(got).forEach(function (k) { state.profile[k] = got[k]; state.profile.detected[k] = true; });
      state.profile.__notes = notes;
      viewHardware();
      var o = el("hw-detect-out");
      if (o) o.innerHTML = '<div class="det-res">' + notes.map(function (n) {
        return '<div class="row"><span class="lbl">' + esc(n[0]) + "</span><span>" +
          (/not detectable|masked|unavailable/.test(n[1]) ? '<span class="na">' + esc(n[1]) + "</span>" : "<b>" + esc(n[1]) + "</b>") +
          '<br><span class="g">' + esc(n[2]) + "</span></span></div>";
      }).join("") + "</div>";
    });
    return;
  }
  if (t.id === "hw-save") {
    if (!state.profile) return;
    var arr2 = store("qlr.profiles.v2") || [];
    state.profile.name = state.profile.name || state.profile.chip || state.profile.gpu || ("profile " + (arr2.length + 1));
    arr2 = arr2.filter(function (x) { return x.name !== state.profile.name; });
    arr2.push(JSON.parse(JSON.stringify(state.profile, function (k, v) { return k.indexOf("__") === 0 ? undefined : v; })));
    if (store("qlr.profiles.v2", arr2) === null && !window.localStorage) announce("Profiles cannot be saved in this browser.");
    store("qlr.profile.current", state.profile);
    viewHardware();
    announce("Profile saved.");
    return;
  }
  if (t.id === "hw-clear") { state.profile = null; store("qlr.profile.current", null); viewHardware(); return; }
  if (t.id === "hw-export") {
    if (!state.profile) return;
    var txt = JSON.stringify(state.profile, function (k, v) { return k.indexOf("__") === 0 ? undefined : v; }, 2);
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt);
    var o2 = el("hw-detect-out");
    if (o2) o2.innerHTML = '<div class="privacy"><b>Profile JSON</b> (copied to the clipboard where the browser allows it)<pre style="white-space:pre-wrap;margin-top:6px">' + esc(txt) + "</pre></div>";
    return;
  }
  if (t.id === "hw-import") {
    var o3 = el("hw-detect-out");
    o3.innerHTML = '<label class="fld"><span class="lbl">Paste a profile JSON</span>' +
      '<textarea id="hw-import-ta" rows="4" style="width:100%;font:450 11.5px var(--font-mono)"></textarea></label>' +
      '<button type="button" class="btn" id="hw-import-go" style="margin-top:6px">Load it</button>';
    return;
  }
}, false);
document.addEventListener("click", function (e) {
  if (e.target.id !== "hw-import-go") return;
  try {
    var p = JSON.parse(el("hw-import-ta").value);
    state.profile = Object.assign(blankProfile(), p);
    viewHardware();
    announce("Profile imported.");
  } catch (err) { announce("That is not valid profile JSON."); }
});
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    if (!el("pop").hidden) { hidePop(); return; }
    var open = e.target.closest && e.target.closest(".det-in");
    if (open) {
      var row = open.closest("[data-row]") || open.closest("tr").previousElementSibling;
      var id = row && (row.getAttribute("data-row") || (row.querySelector("[data-exp]") || {}).getAttribute && row.querySelector("[data-exp]").getAttribute("data-exp"));
      if (id) { delete state.expanded[id]; rerenderRow(id); var b = document.querySelector('[data-exp="' + id + '"]'); if (b) b.focus(); }
    }
  }
});
document.addEventListener("focusout", function (e) {
  if (e.target.getAttribute && e.target.getAttribute("data-ev")) setTimeout(hidePop, 60);
});

function rerenderRow(id) {
  // Re-render just the shelf containing the row, so scroll position is kept.
  var node = document.querySelector('[data-row="' + id + '"]');
  if (!node) { route(); return; }
  var s = SETUPS.filter(function (x) { return x.id === id; })[0];
  if (state.mobile) {
    var li = document.createElement("li");
    li.innerHTML = rowLi(s);
    node.replaceWith(li.firstElementChild);
  } else {
    var tb = node.parentNode, tmp = document.createElement("tbody");
    tmp.innerHTML = rowTr(s);
    var next = node.nextElementSibling;
    if (next && next.classList.contains("det")) next.remove();
    var frag = document.createDocumentFragment();
    while (tmp.firstChild) frag.appendChild(tmp.firstChild);
    tb.replaceChild(frag, node);
  }
  var btn = document.querySelector('[data-exp="' + id + '"]');
  if (btn) btn.focus();
  renderRail();
}

/* popover for the evidence strip */
function showPop(anchor, id) {
  var s = SETUPS.filter(function (x) { return x.id === id; })[0];
  if (!s) return;
  var c = conf(s), pop = el("pop");
  pop.innerHTML = "<b>" + esc("Evidence for this recipe") + "</b><dl>" + DIMS.map(function (d) {
    var v = c[d[0]], l = LV[v.k];
    return "<dt>" + esc(d[1]) + '</dt><dd><span class="' + l.cls + '">' + esc(l.g + " " + v.t) + "</span><br>" +
      '<span class="g">' + esc(v.why) + "</span></dd>";
  }).join("") + "</dl>";
  pop.hidden = false;
  var r = anchor.getBoundingClientRect();
  var w = Math.min(320, window.innerWidth - 16);
  pop.style.width = w + "px";
  var left = Math.max(8, Math.min(r.left, window.innerWidth - w - 8));
  pop.style.left = left + "px";
  var top = r.bottom + 6;
  if (top + pop.offsetHeight > window.innerHeight - 8) top = Math.max(8, r.top - pop.offsetHeight - 6);
  pop.style.top = top + "px";
}
function hidePop() { var p = el("pop"); if (p) p.hidden = true; }
document.addEventListener("mouseover", function (e) {
  var t = e.target.closest && e.target.closest("[data-ev]");
  if (t) showPop(t, t.getAttribute("data-ev"));
});
document.addEventListener("scroll", function () { hidePop(); spy(); }, true);

/* scroll-spy on the family rail */
var spyTimer = null;
function spy() {
   if (state.route !== "directory" || state.mobile) return;
  clearTimeout(spyTimer);
  spyTimer = setTimeout(function () {
    var best = null, bestTop = Infinity;
    document.querySelectorAll(".shelf").forEach(function (sec) {
      var t = sec.getBoundingClientRect().top;
      if (t <= 160 && t > -sec.offsetHeight) { if (Math.abs(t) < bestTop) { bestTop = Math.abs(t); best = sec.id; } }
    });
    document.querySelectorAll("[data-jump]").forEach(function (a) {
      if (a.getAttribute("data-jump") === best) a.setAttribute("data-spy", "1"); else a.removeAttribute("data-spy");
    });
  }, 90);
}

/* ------------------------------------------------------------------ boot */
(function boot() {
  var th = store("qlr.theme");
  if (th) document.documentElement.setAttribute("data-theme", th);
  var saved = sess("qlr.compare");
  if (Array.isArray(saved)) state.compare = saved.filter(function (id) { return SETUPS.some(function (s) { return s.id === id; }); }).slice(0, CMP_MAX);
  var prof = store("qlr.profile.current");
  if (prof) state.profile = prof;

  // Path shim: keep the documented paths working if the site ever moves to a
  // host with directory rewrites. ifhost serves exactly one file at /.
  if (/^https?:$/.test(location.protocol)) {
    var pn = location.pathname.replace(/\/index\.html$/, "");
    var m = pn.match(/\/(hardware|compare|methodology|contribute|models\/[^/]+|recipes(?:\/[^/]+)?|publishers\/[^/]+)\/?$/);
    if (m && !location.hash) { location.replace(location.origin + "/#/" + m[1]); return; }
  }

  el("gen").textContent = D.generated;
  MOBILE.addEventListener ? MOBILE.addEventListener("change", function (e) { state.mobile = e.matches; route(); })
    : MOBILE.addListener(function (e) { state.mobile = e.matches; route(); });
  window.addEventListener("hashchange", route);
  window.addEventListener("resize", function () {
    var mob = MOBILE.matches;
    if (mob !== state.mobile) { state.mobile = mob; route(); }
  });
  route();
})();

})();
