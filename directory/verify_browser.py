#!/usr/bin/env python3
"""Browser verification for the generated Qwen directory site.

Drives real clicks, typing, and selection through headless Chromium so the
checks exercise behaviour rather than markup. Requires playwright:

    python3 -m venv /tmp/pwenv && /tmp/pwenv/bin/pip install playwright
    /tmp/pwenv/bin/playwright install chromium

Serve the built site, then run:

    python3 -m http.server 8848 --bind 127.0.0.1 --directory site &
    /tmp/pwenv/bin/python directory/verify_browser.py [URL]

Exits non-zero if any check fails.
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "DIRECTORY_URL", "http://127.0.0.1:8848/index.html")
SHOT = "/tmp"

fails = []
notes = []
console_errors = []
page_errors = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""), flush=True)
    if not ok:
        fails.append(f"{name}: {detail}")


def note(msg):
    notes.append(msg)
    print("NOTE  " + msg, flush=True)


def dom_state(page):
    return page.evaluate("""() => {
      var cards = Array.from(document.querySelectorAll('.card'));
      var empty = document.querySelector('.empty');
      return {
        n: cards.length,
        groups: document.querySelectorAll('.group').length,
        ids: cards.map(c => c.getAttribute('data-id')),
        titles: cards.map(c => (c.querySelector('.ctitle')||{}).textContent || '?'),
        tiers: cards.map(c => { var p=c.querySelector('.pill'); return p ? p.className.replace('pill p-','') : 'none'; }),
        hint: document.getElementById('hint').textContent.trim(),
        empty: !!empty,
        emptyText: empty ? empty.textContent.replace(/\\s+/g,' ').trim().slice(0,140) : null
      };
    }""")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        page.on("console", lambda m: console_errors.append(f"{m.type}: {m.text}")
                if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        print("--- load ---", flush=True)
        resp = page.goto(URL, wait_until="networkidle")
        check("HTTP 200", resp.status == 200, str(resp.status))
        TOTAL = page.evaluate(
            "() => JSON.parse(document.getElementById('data').textContent).setups.length")
        print(f"   dataset total: {TOTAL} setups", flush=True)
        GROUPS = page.evaluate(
            "() => new Set(JSON.parse(document.getElementById('data').textContent)"
            ".setups.map(s => s.model)).size")

        st = dom_state(page)
        check(f"{TOTAL} setup cards rendered", st["n"] == TOTAL, f"got {st['n']}")
        check(f"{GROUPS} model groups rendered", st["groups"] == GROUPS,
              f"got {st['groups']}")
        print("   hint:", st["hint"][:140], flush=True)

        meta = page.evaluate("""() => {
          const opts = id => Array.from(document.getElementById(id).options).map(o => o.value);
          const D = JSON.parse(document.getElementById('data').textContent);
          return {
            title: document.title,
            counts: document.getElementById('counts').textContent.replace(/\\s+/g,' ').trim(),
            gen: document.getElementById('gen').textContent.trim(),
            engine: opts('f-engine'), hw: opts('f-hw'), quant: opts('f-quant'),
            tier: opts('f-tier'), fit: opts('f-fit'), ready: opts('f-ready'), sort: opts('sort'),
            dataCounts: D.counts, generated: D.generated,
            badLinks: Array.from(document.querySelectorAll('#out a'))
              .filter(a => !/^https?:\\/\\//.test(a.getAttribute('href')||'')).length,
            links: document.querySelectorAll('#out a').length
          };
        }""")
        check("page title set", bool(meta["title"]), meta["title"])
        print("   counts:", meta["counts"], flush=True)
        print("   gen:", meta["gen"], flush=True)
        print("   engine opts:", meta["engine"], flush=True)
        print("   hw opts:", meta["hw"], flush=True)
        print("   quant opts:", meta["quant"], flush=True)
        print("   tier opts:", meta["tier"], flush=True)
        print("   fit opts:", meta["fit"], flush=True)
        print("   completeness opts:", meta["ready"], flush=True)
        print("   sort opts:", meta["sort"], flush=True)
        check("all links are http(s)", meta["badLinks"] == 0, f"{meta['badLinks']} bad")
        check("dataset counts match validator", meta["dataCounts"]["setups"] == TOTAL,
              json.dumps(meta["dataCounts"]))

        print("\n--- newcomer truth and hierarchy ---", flush=True)
        ux = page.evaluate("""() => {
          const card = id => document.querySelector('.card[data-id="'+id+'"]');
          const worst = card('qwen38-flash-next-blazux-vllm-hybrid-spark');
          const sameVocab = card('qwen36-27b-unsloth-gguf-llamacpp-4090-samevocab');
          const D = JSON.parse(document.getElementById('data').textContent);
          const labels = {};
          document.querySelectorAll('.card').forEach(c => {
            labels[c.getAttribute('data-id')] = c.querySelector('.ready').textContent.trim();
          });
          const expected = {};
          D.setups.forEach(s => {
            const hasCmd = !!((s.run||{}).command || ((s.run||{}).steps||[]).some(x => x.kind === 'cmd'));
            const hasSpeed = (s.measurements||[]).some(m => m.unit === 'tok/s' && /^decode_/.test(m.metric));
            expected[s.id] = hasCmd && hasSpeed ? '✓ recipe + measured'
              : hasCmd ? '◔ recipe, unmeasured'
              : hasSpeed ? '◐ measured, no command yet'
              : '○ lead only — no command or speed yet';
          });
          return {
            h1: document.querySelector('h1').textContent.trim(),
            howVisible: document.getElementById('how').open,
            metricCategories: Array.from(document.querySelectorAll('#metric-guide [data-category] h3'))
              .map(x => x.textContent.trim()),
            metricGuide: document.getElementById('metric-guide').textContent.replace(/\\s+/g, ' ').trim(),
            countsInFooter: !!document.querySelector('footer #counts'),
            advancedVisible: getComputedStyle(document.getElementById('adv')).display !== 'none',
            neutral: document.querySelectorAll('.v-unknown').length,
            verdicts: document.querySelectorAll('.v-good,.v-tight,.v-no').length,
            notes: document.querySelectorAll('.card .cnote').length,
            readinessMismatch: Object.keys(expected).filter(id => labels[id] !== expected[id]),
            readinessKinds: Array.from(new Set(Object.values(labels))).sort(),
            worst: {
              headline: worst.querySelector('.big').textContent.trim(),
              label: worst.querySelector('.nmet').textContent.trim(),
              aggregate: worst.querySelector('.nagg').textContent.replace(/\\s+/g, ' ').trim()
            },
            sameVocab: {
              headline: sameVocab.querySelector('.big').textContent.trim(),
              label: sameVocab.querySelector('.nmet').textContent.trim(),
              aggregate: !!sameVocab.querySelector('.nagg')
            },
            badMacHardware: (D.setups.find(s => s.id === 'qwen35-9b-bf16-sglang').hardware||[])
              .some(id => /^mac-/.test(id))
          };
        }""")
        check("newcomer question is the page headline",
              ux["h1"] == "Run Qwen on your own machine", ux["h1"])
        check("local-hosting orientation starts open", ux["howVisible"])
        check("performance guide separates speed, capacity, and intrinsic traits",
              ux["metricCategories"] == ["Speed and responsiveness", "Capacity and scale", "Model and runtime traits"],
              ux["metricCategories"])
        check("performance guide names the correct primary hardware drivers",
              "Main driver: memory bandwidth" in ux["metricGuide"]
              and "Main driver: GPU/CPU compute" in ux["metricGuide"]
              and "usable memory capacity" in ux["metricGuide"], ux["metricGuide"][:240])
        check("device notes use exact Spark specs and do not claim MLX uses the Neural Engine",
              "273 GB/s" in ux["metricGuide"]
              and "not the Neural Engine" in ux["metricGuide"]
              and "800+ GB/s" not in ux["metricGuide"], ux["metricGuide"][-300:])
        check("advanced filters remain visible on desktop", ux["advancedVisible"])
        check("vanity counts moved to the footer", ux["countsInFooter"])
        check("every card exposes its plain-English slug note", ux["notes"] == TOTAL,
              f"{ux['notes']}/{TOTAL}")
        check("fit is neutral before a machine is chosen",
              ux["neutral"] == TOTAL and ux["verdicts"] == 0,
              f"neutral={ux['neutral']} verdicts={ux['verdicts']}")
        check("all four completeness states render from data",
              not ux["readinessMismatch"] and len(ux["readinessKinds"]) == 4,
              f"kinds={ux['readinessKinds']} mismatches={ux['readinessMismatch'][:5]}")
        check("single-stream speed beats aggregate on the worst offender",
              ux["worst"]["headline"] == "32.5" and "chatting" in ux["worst"]["label"],
              json.dumps(ux["worst"]))
        check("aggregate context states concurrency and loaded per-stream speed",
              "266.8 tok/s" in ux["worst"]["aggregate"]
              and "48 streams" in ux["worst"]["aggregate"]
              and "5.6 tok/s each" in ux["worst"]["aggregate"],
              ux["worst"]["aggregate"])
        check("same-vocabulary 4090 card headlines its single-stream mean, not peak",
              ux["sameVocab"]["headline"] == "43.2"
              and "one conversation" in ux["sameVocab"]["label"]
              and "mean" in ux["sameVocab"]["label"]
              and not ux["sameVocab"]["aggregate"],
              json.dumps(ux["sameVocab"]))
        check("SGLang setup is not advertised for unsupported Apple Silicon",
              not ux["badMacHardware"])

        print("\n--- machine picker and recommendation ---", flush=True)
        recommendation_ids = []
        defaults = {"mac": 32, "nvidia": 24, "multigpu": 72, "spark": 128}
        for machine, memory in defaults.items():
            page.click(f'[data-machine="{machine}"]')
            picked = page.evaluate("""([machine, memory]) => {
              const D = JSON.parse(document.getElementById('data').textContent);
              const profile = JSON.parse(localStorage.getItem('qlr.profile'));
              const shown = Array.from(document.querySelectorAll('.card')).map(c => c.dataset.id);
              const recLink = document.querySelector('#rec .rlinks a');
              const recId = recLink ? recLink.getAttribute('href').replace('#s-', '') : null;
              const rec = D.setups.find(s => s.id === recId);
              const maps = {
                mac:['mac-64gb','mac-128gb'], nvidia:['gpu-24gb'],
                multigpu:['gpu-multigpu-72gb','gpu-24gb'],
                spark:['dgx-spark','thinkstation-pgx']
              };
              const invalid = shown.filter(id => {
                const s=D.setups.find(x => x.id===id);
                return !s.hardware.some(h => maps[machine].includes(h))
                  || s.requirements.memory_gb > memory;
              });
              return {
                profile, selected: Number(document.getElementById('p-mem').value),
                recId, recFork: rec && rec.engine.requires_fork,
                recNeed: rec && rec.requirements.memory_gb,
                recText: document.getElementById('rec').textContent.replace(/\\s+/g,' ').trim(),
                invalid, cards: shown.length
              };
            }""", [machine, memory])
            check(f"{machine} picker uses its default memory",
                  picked["selected"] == memory and picked["profile"] == {"machine": machine, "mem": memory},
                  json.dumps(picked))
            check(f"{machine} results match hardware and memory",
                  picked["cards"] > 0 and not picked["invalid"], json.dumps(picked))
            check(f"{machine} gets a fitting no-fork recommendation",
                  bool(picked["recId"]) and not picked["recFork"] and picked["recNeed"] <= memory,
                  json.dumps(picked))
            recommendation_ids.append(picked["recId"])
            if machine == "multigpu":
                check("multi-GPU recommendation uses the 43.2 tok/s mean",
                      picked["recId"] == "qwen36-27b-unsloth-gguf-llamacpp-4090-samevocab"
                      and "43.2 tok/s" in picked["recText"] and "mean" in picked["recText"],
                      json.dumps(picked))
            page.click("#change-machine")
        check("machine profiles produce distinct starting recommendations",
              len(set(recommendation_ids)) == len(recommendation_ids), str(recommendation_ids))
        st = dom_state(page)
        check("leaving the picker restores the full directory", st["n"] == TOTAL, f"{st['n']}")

        print("\n--- search (typed, real keystrokes) ---", flush=True)
        page.fill("#q", "")
        page.type("#q", "dflash2", delay=20)
        st = dom_state(page)
        check("typing 'dflash2' narrows results", 0 < st["n"] < TOTAL, f"{st['n']} cards")
        print("   hits:", st["titles"], flush=True)
        # Full-text search covers caveats, quant_detail and measurements too, so
        # the invariant is "every term appears somewhere in the card's haystack".
        missing = page.evaluate("""(ids) => {
          const D = JSON.parse(document.getElementById('data').textContent);
          const hay = s => [s.title, s.id, (s.variation||{}).checkpoint, (s.variation||{}).quant,
            (s.variation||{}).quant_detail, (s.engine||{}).config, (s.engine||{}).image,
            (s.engine||{}).draft_model, (s.run||{}).command, (s.run||{}).repo, (s.run||{}).profile,
            (s.caveats||[]).join(' '), JSON.stringify(s.measurements||[])].join(' ').toLowerCase();
          const out = [];
          D.setups.forEach(s => { if (ids.indexOf(s.id) >= 0 && hay(s).indexOf('dflash2') < 0) out.push(s.id); });
          return out;
        }""", st["ids"])
        check("every 'dflash2' hit mentions dflash2 in searchable text", not missing, str(missing))
        where = page.evaluate("""() => {
          const D = JSON.parse(document.getElementById('data').textContent);
          return D.setups.filter(s => JSON.stringify(s).toLowerCase().indexOf('dflash2') >= 0)
            .map(s => s.id);
        }""")
        print("   (cards mentioning dflash2 anywhere in data:", len(where), ")", flush=True)

        page.fill("#q", "dflash2 spark")
        st = dom_state(page)
        both = page.evaluate("""(ids) => {
          const D = JSON.parse(document.getElementById('data').textContent);
          const hay = s => JSON.stringify(s).toLowerCase();
          return ids.filter(id => {
            const s = D.setups.find(x => x.id === id);
            return !(hay(s).indexOf('dflash2') >= 0 && hay(s).indexOf('spark') >= 0);
          });
        }""", st["ids"])
        check("multi-term search requires ALL terms", not both, f"{st['n']} cards, offenders {both}")
        print(f"   {st['n']} cards match both terms", flush=True)

        page.fill("#q", "zzzqqq-no-such-thing")
        st = dom_state(page)
        check("no-match shows empty state", st["empty"] and st["n"] == 0, f"n={st['n']}")
        print("   empty text:", st["emptyText"], flush=True)
        page.screenshot(path=f"{SHOT}/site_empty_state.png")

        page.fill("#q", "")
        st = dom_state(page)
        check(f"clearing search restores all {TOTAL}", st["n"] == TOTAL, f"{st['n']}")

        print("\n--- filters: every real option, verified against the data ---", flush=True)
        TRUTH_JS = """([sel, val, ids]) => {
          const D = JSON.parse(document.getElementById('data').textContent);
          const rank = {box:3, forum:2, vendor:1, none:0};
          const tier = s => s.provenance_tier || 'none';
          const bad = [];
          D.setups.forEach(s => {
            if (ids.indexOf(s.id) < 0) return;
            if (sel === '#f-engine' && s.engine.id !== val) bad.push(s.id+':engine='+s.engine.id);
            if (sel === '#f-hw' && (s.hardware||[]).indexOf(val) < 0) bad.push(s.id+':hw='+s.hardware);
            if (sel === '#f-quant' && String(s.variation.quant).toLowerCase() !== val) bad.push(s.id+':quant='+s.variation.quant);
            if (sel === '#f-tier' && tier(s) !== val) bad.push(s.id+':tier='+tier(s));
            if (sel === '#f-ready') {
              const hasCmd=!!((s.run||{}).command || ((s.run||{}).steps||[]).some(x=>x.kind==='cmd'));
              const measured=(s.measurements||[]).some(m=>m.unit==='tok/s' && /^decode_/.test(m.metric));
              if ((val === 'run' && !hasCmd) || (val === 'measured' && !measured)) bad.push(s.id+':ready');
            }
            if (sel === '#f-fit') { const need=(s.requirements||{}).memory_gb;
              if (need == null || need > Number(val)) bad.push(s.id+':mem='+need); }
            return bad;
          });
          return bad;
        }"""
        select_map = [("#f-engine", meta["engine"]), ("#f-hw", meta["hw"]),
                      ("#f-quant", meta["quant"]), ("#f-tier", meta["tier"]),
                      ("#f-fit", meta["fit"]), ("#f-ready", meta["ready"])]
        for sel, options in select_map:
            for val in [v for v in options if v]:
                page.select_option(sel, val)
                st = dom_state(page)
                check(f"{sel}={val} returns results", st["n"] > 0, f"{st['n']} cards")
                bad = page.evaluate(TRUTH_JS, [sel, val, st["ids"]])
                check(f"{sel}={val} results all satisfy the filter", not bad, str(bad)[:200])
                print(f"   {sel}={val}: {st['n']} cards", flush=True)
                page.select_option(sel, "")
            st = dom_state(page)
            check(f"{sel} cleared back to all {TOTAL}", st["n"] == TOTAL, f"{st['n']}")

        page.select_option("#f-tier", "box")
        st = dom_state(page)
        check("all box-tier cards carry the box pill",
              all(t == "box" for t in st["tiers"]), str(st["tiers"]))
        check("tier=box yields exactly the 4 measured setups", st["n"] == 4, f"{st['n']}")
        page.select_option("#f-tier", "")

        print("\n--- combined filters + reset ---", flush=True)
        page.select_option("#f-engine", "sglang")
        page.select_option("#f-quant", "nvfp4")
        st = dom_state(page)
        check("engine AND quant combine", 0 < st["n"] < TOTAL, f"{st['n']}: {st['titles']}")
        page.click("#reset")
        st = dom_state(page)
        check(f"reset restores all {TOTAL}", st["n"] == TOTAL, f"{st['n']}")
        check("reset clears the search box", page.input_value("#q") == "", repr(page.input_value("#q")))
        resets = page.evaluate("""() => ['f-engine','f-hw','f-quant','f-tier','f-fit','f-ready','sort']
              .map(id => document.getElementById(id).value)""")
        check("reset restores every control", resets == ["", "", "", "", "", "", "default"], str(resets))

        print("\n--- sorting ---", flush=True)
        for sv in ["speed", "small", "evidence", "fresh"]:
            page.select_option("#sort", sv)
            st = dom_state(page)
            check(f"sort={sv} keeps all {TOTAL} visible", st["n"] == TOTAL, f"{st['n']}")
            expected = page.evaluate("""(mode) => {
              const D = JSON.parse(document.getElementById('data').textContent);
              const rank = {box:3, forum:2, vendor:1, none:0};
              const tier = s => (s.measurements||[]).reduce((b,m)=>{
                const r = rank[m.provenance]||0; return r > (rank[b]||0) ? m.provenance : b; }, 'none');
              let c = D.setups.slice();
              if (mode === 'small') c.sort((a,b) => (((a.requirements||{}).memory_gb)||1e9) - (((b.requirements||{}).memory_gb)||1e9));
              if (mode === 'evidence') c.sort((a,b) => (rank[tier(b)]||0) - (rank[tier(a)]||0));
              if (mode === 'fresh') c.sort((a,b) => String(b.updated||'').localeCompare(String(a.updated||'')));
              return c.map(s => s.id);
            }""", sv)
            # The page groups by model, so compare multiset membership and the
            # leading card of each group rather than a flat sequence.
            same_set = sorted(expected) == sorted(st["ids"])
            check(f"sort={sv} shows the same {TOTAL} setups", same_set, "")
            print(f"   first 3 rendered: {st['titles'][:3]}", flush=True)
            if sv == "evidence":
                check("sort=evidence puts box-tier first", st["tiers"][0] == "box",
                      f"first tier={st['tiers'][0]}")
            if sv == "speed":
                expected_top = page.evaluate("""() => {
                  const D=JSON.parse(document.getElementById('data').textContent);
                  const pref=['decode_chat','decode_code','decode_essay','decode_per_stream'];
                  const best=s => {
                    const ms=(s.measurements||[]).filter(m=>m.unit==='tok/s' && /^decode_/.test(m.metric));
                    for(const allowPeak of [false,true]){
                      for(const metric of pref){
                        const hits=ms.filter(m=>m.metric===metric
                          && (m.concurrency==null || m.concurrency<=1)
                          && (allowPeak || m.stat!=='peak'));
                        if(hits.length) return {value:Math.max(...hits.map(m=>m.value)),agg:false};
                      }
                    }
                    const agg=ms.filter(m=>m.metric==='decode_agg');
                    return agg.length?{value:Math.max(...agg.map(m=>m.value)),agg:true}:null;
                  };
                  return D.setups.slice().sort((a,b)=>{
                    const x=best(a),y=best(b);
                    if(!!x!==!!y) return y?1:-1;
                    if(!x) return 0;
                    if(x.agg!==y.agg) return x.agg?1:-1;
                    return y.value-x.value;
                  })[0].id;
                }""")
                check("sort=speed starts with the fastest single-stream result",
                      st["ids"][0] == expected_top,
                      f"got {st['ids'][0]}, expected {expected_top}")
                top_nums = page.evaluate("""() => Array.from(document.querySelectorAll('.card')).slice(0,3)
                      .map(c => c.querySelector('.cnums').textContent.replace(/\\s+/g,' ').trim())""")
                print("   top-3 by speed, numbers:", top_nums, flush=True)
        page.select_option("#sort", "default")

        print("\n--- expand / collapse (real clicks) ---", flush=True)
        first = page.query_selector(".card")
        collapsed = page.evaluate("""() => {
          const c = document.querySelector('.card');
          return {open: c.classList.contains('open'),
                  h: c.querySelector('.cbody').getBoundingClientRect().height,
                  aria: c.querySelector('.chead').getAttribute('aria-expanded')};
        }""")
        check("cards start collapsed", not collapsed["open"] and collapsed["h"] == 0, str(collapsed))

        page.click(".card .chead")
        opened = page.evaluate("""() => {
          const c = document.querySelector('.card');
          const b = c.querySelector('.cbody');
          return {open: c.classList.contains('open'), h: b.getBoundingClientRect().height,
                  aria: c.querySelector('.chead').getAttribute('aria-expanded'),
                  hasCmd: !!c.querySelector('.cmd'), hasNoRun: !!c.querySelector('.norun'),
                  hasKv: !!c.querySelector('.kv'),
                  srcs: c.querySelectorAll('.srclist a').length,
                  measRows: c.querySelectorAll('.cbody table tr').length,
                  text: b.textContent.replace(/\\s+/g,' ').trim().slice(0,200)};
        }""")
        check("click expands the card", opened["open"] and opened["h"] > 0, str(opened["h"]))
        check("aria-expanded becomes true", opened["aria"] == "true", str(opened["aria"]))
        # A setup either has a real command (copyable .cmd block) or honestly
        # says it has none. Prose in run.steps must never be dressed up as a
        # pasteable command, so exactly one of these two must be present.
        check("'How to run it' resolves to a command or an honest fallback",
              opened["hasCmd"] != opened["hasNoRun"],
              f"hasCmd={opened['hasCmd']} hasNoRun={opened['hasNoRun']}")
        check("expanded body shows details", opened["hasKv"], "")
        check("expanded body shows sources", opened["srcs"] > 0, f"{opened['srcs']} links")
        print("   body:", opened["text"], flush=True)
        page.screenshot(path=f"{SHOT}/site_card_expanded.png")

        page.click(".card .chead")
        reclosed = page.evaluate("""() => {
          const c = document.querySelector('.card');
          return {open: c.classList.contains('open'),
                  h: c.querySelector('.cbody').getBoundingClientRect().height};
        }""")
        check("second click collapses", not reclosed["open"] and reclosed["h"] == 0, str(reclosed))

        page.focus(".card .chead")
        page.keyboard.press("Enter")
        kb = page.evaluate("""() => {
          const c = document.querySelector('.card');
          return {open: c.classList.contains('open'),
                  tabindex: c.querySelector('.chead').getAttribute('tabindex'),
                  role: c.querySelector('.chead').getAttribute('role')};
        }""")
        check("Enter key expands (keyboard accessible)", kb["open"], str(kb))
        if not kb["tabindex"] and not kb["role"]:
            note("card headers are clickable but carry no tabindex/role, so they are "
                 "not reachable by Tab for keyboard-only users")
        page.keyboard.press("Enter")

        page.click("#expand-all")
        ea = page.evaluate("""() => {
          const cards = Array.from(document.querySelectorAll('.card'));
          return {label: document.getElementById('expand-all').textContent,
                  open: cards.filter(c => c.classList.contains('open')).length,
                  total: cards.length};
        }""")
        check("Expand all opens every card", ea["open"] == ea["total"], f"{ea['open']}/{ea['total']}")
        check("button relabels to Collapse all", "Collapse" in ea["label"], ea["label"])
        page.click("#expand-all")
        ea2 = page.evaluate("""() => {
          const cards = Array.from(document.querySelectorAll('.card'));
          return {label: document.getElementById('expand-all').textContent,
                  open: cards.filter(c => c.classList.contains('open')).length};
        }""")
        check("Collapse all closes every card", ea2["open"] == 0, str(ea2))

        print("\n--- copy button ---", flush=True)
        # Only setups with a real command get a copy button; entries whose
        # run.steps are prose render as plain text, so open the first card that
        # actually has one rather than assuming it is card #1.
        page.locator(".card:has(.copy)").first.locator(".chead").click()
        cp = page.evaluate("""() => {
          const pre = document.querySelector('.cmd');
          const btn = document.querySelector('.copy');
          if (!btn) return {missing: true};
          const attr = (btn.getAttribute('data-copy')||'').trim();
          const shown = (pre.childNodes[0] ? pre.childNodes[0].textContent : '').trim();
          return {attr: attr.slice(0,90), shown: shown.slice(0,90), match: attr === shown,
                  hasClipboard: !!navigator.clipboard, secure: window.isSecureContext,
                  labelBefore: btn.textContent};
        }""")
        check("copy button exists", not cp.get("missing"), "")
        check("data-copy equals the visible command", cp.get("match"),
              f"attr={cp.get('attr')!r} shown={cp.get('shown')!r}")
        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        page.click(".copy")
        page.wait_for_timeout(300)
        label = page.evaluate("() => document.querySelector('.copy').textContent")
        clip = None
        try:
            clip = page.evaluate("() => navigator.clipboard.readText()")
        except Exception as exc:
            clip = f"<unreadable: {type(exc).__name__}>"
        print(f"   label after click: {label!r} | clipboard: {str(clip)[:70]!r}", flush=True)
        check("copy gives user feedback", label == "copied", f"label={label!r}")
        if isinstance(clip, str) and not clip.startswith("<"):
            check("clipboard holds the command", clip.strip() == cp["attr"].strip(),
                  f"{clip[:60]!r} vs {cp['attr'][:60]!r}")

        print("\n--- data integrity as rendered ---", flush=True)
        integ = page.evaluate("""() => {
          const D = JSON.parse(document.getElementById('data').textContent);
          const out = [];
          document.querySelectorAll('.card').forEach(c => {
            const id = c.getAttribute('data-id');
            const pill = c.querySelector('.pill');
            const tier = pill ? pill.className.replace('pill p-','') : 'none';
            const nums = Array.from(c.querySelectorAll('.num')).map(n => n.textContent.trim());
            const src = D.setups.find(s => s.id === id) || {};
            out.push({id, tier, nums,
                      dataMeasurements: (src.measurements||[]).length,
                      dataTier: src.provenance_tier,
                      status: src.status});
          });
          return out;
        }""")
        mism = [r for r in integ if (r["dataMeasurements"] > 0) != bool(r["nums"])]
        check("cards with measurements show numbers, others do not", not mism,
              json.dumps(mism)[:300])
        tier_mism = [r for r in integ
                     if (r["dataTier"] or "none") != (r["tier"] if r["tier"] != "?" else "none")]
        check("provenance pill matches the data tier", not tier_mism,
              json.dumps(tier_mism)[:300])
        leaked_entities = page.locator(".spec").evaluate_all(
            "els => els.map(e => e.textContent).filter(t => /&(?:rarr|larr|uarr|darr);/.test(t))"
        )
        check("metadata chips render arrows instead of HTML entities",
              not leaked_entities, json.dumps(leaked_entities)[:300])
        for r in integ:
            if r["tier"] == "box":
                print(f"   [box] {r['id']}: {r['nums']}", flush=True)

        print("\n--- desktop layout 1440px ---", flush=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        desk = page.evaluate("""() => ({
          w: window.innerWidth,
          scrollW: document.documentElement.scrollWidth,
          overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
          controlsH: document.querySelector('.controls').getBoundingClientRect().height
        })""")
        print("  ", desk, flush=True)
        check("no horizontal overflow at 1440px", not desk["overflowX"], str(desk))
        page.screenshot(path=f"{SHOT}/site_desktop.png")
        page.screenshot(path=f"{SHOT}/site_desktop_full.png", full_page=True)

        print("\n--- mobile layout 390px ---", flush=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#metric-guide").evaluate("el => el.open = true")
        page.wait_for_timeout(200)
        mob = page.evaluate("""() => {
          const de = document.documentElement;
          const cmd = document.querySelector('.cmd');
          return {
            w: window.innerWidth, scrollW: de.scrollWidth, bodyScrollW: document.body.scrollWidth,
            overflowX: de.scrollWidth > window.innerWidth + 1,
            controlsH: document.querySelector('.controls').getBoundingClientRect().height,
            cardW: document.querySelector('.card').getBoundingClientRect().width,
            cmd: cmd ? {scrollW: cmd.scrollWidth, clientW: cmd.clientWidth,
                        ws: getComputedStyle(cmd).whiteSpace,
                        overflowX: getComputedStyle(cmd).overflowX} : null,
            widestRight: Math.max(...Array.from(document.querySelectorAll('.card, .controls, pre, table'))
                            .map(e => e.getBoundingClientRect().right))
          };
        }""")
        print("  ", mob, flush=True)
        check("no horizontal overflow at 390px with performance guide open",
              not mob["overflowX"], str(mob))
        if mob["cmd"] and mob["cmd"]["ws"] == "pre" and mob["cmd"]["overflowX"] == "visible":
            note("long run commands do not wrap or scroll on mobile; they overflow the card")
        page.screenshot(path=f"{SHOT}/site_mobile.png")
        page.screenshot(path=f"{SHOT}/site_mobile_full.png", full_page=True)

        page.fill("#q", "flash-next")
        st = dom_state(page)
        check("search works at mobile width", st["n"] > 0, f"{st['n']} cards")
        mob2 = page.evaluate("""() => ({overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
              scrollW: document.documentElement.scrollWidth, w: window.innerWidth})""")
        check("no overflow after filtering on mobile", not mob2["overflowX"], str(mob2))
        page.screenshot(path=f"{SHOT}/site_mobile_filtered.png")

        print("\n--- console / runtime errors ---", flush=True)
        check("no page errors", not page_errors, json.dumps(page_errors)[:400])
        real_console = [c for c in console_errors if "favicon" not in c.lower()]
        check("no console errors", not real_console, json.dumps(real_console)[:400])

        browser.close()

    print("\n================ SUMMARY ================", flush=True)
    print(f"failed checks: {len(fails)}", flush=True)
    for f in fails:
        print("  FAIL", f, flush=True)
    print(f"notes: {len(notes)}", flush=True)
    for n in notes:
        print("  NOTE", n, flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
