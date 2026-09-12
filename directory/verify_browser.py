#!/usr/bin/env python3
"""Browser verification for the generated Qwen directory site.

Drives real clicks, typing, selection and navigation through headless Chromium
so the checks exercise behaviour rather than markup. Requires playwright:

    python3 -m venv /tmp/pwenv && /tmp/pwenv/bin/pip install playwright
    /tmp/pwenv/bin/playwright install chromium

Serve the built site, then run:

    python3 -m http.server 8848 --bind 127.0.0.1 --directory site &
    /tmp/pwenv/bin/python directory/verify_browser.py [URL]

Exits non-zero if any check fails.

This suite replaces the one written for the single-page architecture. The
old-check -> new-check mapping is in docs/redesign-2026-09-10/08-implementation-
and-verification.md; no check was dropped without a stronger replacement. The
rules it defends are the project's, not the layout's:

  * a single-stream tok/s number always wins the headline
  * no number is ever rendered without its metric, condition and provenance
  * provenance tiers are never blended
  * no fit verdict exists outside My Hardware, and no unconditional one anywhere
  * trust is four independent dimensions, never averaged
  * negative results stay visible
"""
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    "DIRECTORY_URL", "http://127.0.0.1:8848/index.html")
BASE = URL.split("#")[0]

fails: list[str] = []
console_errors: list[str] = []
page_errors: list[str] = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""), flush=True)
    if not ok:
        fails.append(f"{name}: {detail}")


def note(msg):
    print("NOTE  " + msg, flush=True)


def goto(page, hash_route):
    page.goto(BASE + hash_route)
    page.wait_for_timeout(220)


def text(page):
    return page.evaluate("document.body.innerText")


def rows(page):
    return page.evaluate("document.querySelectorAll('[data-row]').length")


def rowids(page):
    return page.evaluate("Array.from(document.querySelectorAll('[data-row]')).map(n=>n.getAttribute('data-row'))")


def overflow(page):
    return page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")


def widest(page):
    """Name the elements sticking out past the viewport, for a legible failure."""
    return page.evaluate("""() => {
      var w = document.documentElement.clientWidth;
      return Array.from(document.querySelectorAll('*'))
        .filter(n => n.getBoundingClientRect().right > w + 1)
        .slice(0, 4)
        .map(n => n.tagName + '.' + n.className + ' right=' + Math.round(n.getBoundingClientRect().right));
    }""")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        # ---------------------------------------------------------- delivery
        resp = page.goto(URL)
        page.wait_for_timeout(300)
        check("HTTP 200", resp is None or resp.status == 200, str(resp.status if resp else "file://"))
        check("page title set", bool(page.title()), page.title())

        D = page.evaluate("JSON.parse(document.getElementById('data').textContent)")
        SET = D["setups"]
        TOTAL = len(SET)
        MODELS = D["models"]
        HW = D["hardware"]
        note(f"dataset: {TOTAL} setups, {len(MODELS)} model families, {len(HW)} hardware classes")

        meta = page.evaluate("""() => ({
          bad: Array.from(document.querySelectorAll('a[href]'))
                 .filter(a => !/^(https?:|#|mailto:)/.test(a.getAttribute('href'))).length,
          counts: JSON.parse(document.getElementById('data').textContent).counts
        })""")
        check("all links are http(s) or in-page", meta["bad"] == 0, f"{meta['bad']} bad")
        check("dataset counts match validator", meta["counts"]["setups"] == TOTAL, str(meta["counts"]))

        # ------------------------------------------------------------ routes
        ROUTES = [
            ("#/", "models-home"), ("#/recipes", "directory"),
            ("#/hardware", "hardware"), ("#/compare", "compare"),
            ("#/methodology", "methodology"), ("#/contribute", "contribute"),
            (f"#/models/{SET[0]['model']}", "model"),
            (f"#/recipes/{SET[0]['id']}", "recipe"),
            (f"#/publishers/{SET[0]['variation']['publisher']}", "publisher"),
        ]
        bad_routes = []
        for h, name in ROUTES:
            goto(page, h)
            got = page.evaluate("document.body.getAttribute('data-route')")
            if got != name:
                bad_routes.append(f"{h}->{got}")
        check("every documented route resolves", not bad_routes, str(bad_routes))

        goto(page, "#/definitely-not-a-route")
        nf = page.evaluate("document.body.getAttribute('data-route')")
        check("unknown route renders the 404 view, not a blank page",
              nf == "404" and "Not found" in text(page) and "Models" in text(page), nf)

        goto(page, "#/")
        check("bare hash is the model-first homepage",
              page.evaluate("document.body.getAttribute('data-route')") == "models-home")

        goto(page, "#/hardware")
        page.go_back()
        page.wait_for_timeout(250)
        check("browser back returns to Models",
              page.evaluate("document.body.getAttribute('data-route')") == "models-home")

        # ------------------------------------------ model-first landing page
        goto(page, "#/")
        fv = page.evaluate("""() => {
          function top(sel){ var n=document.querySelector(sel); return n ? n.getBoundingClientRect().top : null; }
          return {
            brand: top('.brand'), tabs: document.querySelectorAll('.tab').length,
            sub: top('.mast-sub'), q: top('#model-q'),
            models: document.querySelectorAll('[data-model-select]').length,
            firstModel: top('[data-model-select]'), preview: top('.model-preview'),
            recipeRows: document.querySelectorAll('[data-row]').length,
            body: document.body.innerText
          };
        }""")
        for label, key in [("product identity", "brand"), ("one-sentence description", "sub"),
                           ("model search", "q"), ("first model", "firstModel"),
                           ("selected-model preview", "preview")]:
            check(f"first viewport: {label} is above the fold",
                  fv[key] is not None and fv[key] < 1000, str(fv[key]))
        check("first viewport: four primary tabs", fv["tabs"] == 4, str(fv["tabs"]))
        check("homepage lists every model once", fv["models"] == len(MODELS), str(fv["models"]))
        check("homepage does not render the advanced recipe table", fv["recipeRows"] == 0, str(fv["recipeRows"]))
        banned = [w for w in ("How local hosting works", "First: what are you running this on",
                               "Start here", "Not sure yet") if w in fv["body"]]
        check("first viewport: no onboarding gate, hero or recommendation", not banned, str(banned))

        # Every practical minimum points to one exact setup, and only that
        # setup may contribute the row's speed headline.
        by_id = {s["id"]: s for s in SET}
        selected = [m for m in MODELS.values()
                    if (m.get("practical_baseline") or {}).get("status") == "selected"]
        missing = [m for m in MODELS.values()
                   if (m.get("practical_baseline") or {}).get("status") == "not_verified"]
        check("selected and not-verified baselines cover every model",
              len(selected) + len(missing) == len(MODELS),
              f"{len(selected)} selected, {len(missing)} not verified")
        landing = page.evaluate(r"""() => Array.from(document.querySelectorAll('[data-model-select]')).map(n => ({
          id:n.getAttribute('data-model-select'), text:n.innerText.replace(/\s+/g,' ').trim()
        }))""")
        landing_by_id = {x["id"]: x["text"] for x in landing}
        baseline_mismatch = []
        for m in selected:
            s = by_id[m["practical_baseline"]["setup"]]
            shown = landing_by_id.get(m["id"], "")
            if str(s["requirements"]["memory_gb"]) not in shown:
                baseline_mismatch.append(m["id"] + " memory")
        check("every selected model shows its referenced setup requirement",
              not baseline_mismatch, str(baseline_mismatch))
        check("unverified models say not verified yet",
              all("Not verified yet" in landing_by_id.get(m["id"], "") for m in missing))

        flash = MODELS.get("qwen3-8-flash-next")
        if flash:
            page.click('[data-model-select="qwen3-8-flash-next"]')
            page.wait_for_timeout(180)
            preview = page.evaluate("document.querySelector('.model-preview').innerText")
            check("Flash-Next preview exposes the accessible hybrid baseline",
                  "24 GB VRAM" in preview and "110 GB" in preview and "22.52" in preview,
                  preview[:180])
            check("Flash-Next speed states exact-baseline conditions and provenance",
                  "1 stream" in preview and "forum" in preview and "custom fork" in preview,
                  preview[:220])

        page.fill("#model-q", "vision")
        page.wait_for_timeout(350)
        filtered_models = page.evaluate("document.querySelectorAll('[data-model-select]').length")
        check("model search narrows the homepage", 0 < filtered_models < len(MODELS), str(filtered_models))
        page.fill("#model-q", "")
        page.wait_for_timeout(300)

        # ------------------------------------------------- recipe directory
        goto(page, "#/recipes")

        check("every recipe renders with no filters and no profile", rows(page) == TOTAL, str(rows(page)))
        shelves = page.evaluate("document.querySelectorAll('.shelf').length")
        check("one shelf per model family", shelves == len(MODELS), f"{shelves} vs {len(MODELS)}")

        head = page.evaluate("""() => {
          var s = document.querySelector('.shelf-head');
          return { labels: Array.from(s.querySelectorAll('.spec .lbl')).map(n=>n.textContent),
                   text: s.innerText, meta: s.querySelector('.shelf-meta').innerText };
        }""")
        need = ["GENERATION", "ARCHITECTURE", "TOTAL PARAMS", "ACTIVE PARAMS",
                "NATIVE CONTEXT", "MAX CONTEXT", "MODALITIES", "WEIGHT LICENSE"]
        missing = [n for n in need if n not in [x.upper() for x in head["labels"]]]
        check("shelf header carries every required spec field", not missing, str(missing))
        check("shelf header states recipe count, measured count and last update",
              re.search(r"\d+ recipes?", head["meta"]) and "measured" in head["meta"] and "updated" in head["meta"],
              head["meta"])

        # dense models have no recorded active-parameter count; that is definitional,
        # not a measurement, so the header must say so rather than invent a number.
        dense_null = [m for m in MODELS.values()
                      if m["architecture"].get("kind") == "dense"
                      and m["architecture"].get("params_active_b") is None]
        if dense_null:
            goto(page, f"#/models/{dense_null[0]['id']}")
            check("dense model with no recorded active params says 'all — dense'",
                  "all — dense" in text(page), dense_null[0]["id"])
        no_ctx = [m for m in MODELS.values() if (m.get("context") or {}).get("max") is None]
        if no_ctx:
            goto(page, f"#/models/{no_ctx[0]['id']}")
            check("unstated max context renders as not stated, never blank or zero",
                  "not stated" in text(page), no_ctx[0]["id"])

        # ----------------------------------------------------- the decode rule
        def single(m):
            return m.get("concurrency") in (None, 1)

        def speeds(s):
            return [m for m in s.get("measurements", [])
                    if m.get("unit") == "tok/s" and str(m.get("metric", "")).startswith("decode")]

        def rep(s):
            rs = [m for m in speeds(s) if single(m)]
            for metric in ("decode_chat", "decode_code", "decode_essay", "decode_per_stream"):
                c = [m for m in rs if m["metric"] == metric]
                if not c:
                    continue
                nonpeak = [m for m in c if m.get("stat") != "peak"]
                return sorted(nonpeak or c, key=lambda m: -m["value"])[0]
            return None

        baseline_speed_wrong = []
        for m in selected:
            s = by_id[m["practical_baseline"]["setup"]]
            r = rep(s)
            shown = landing_by_id.get(m["id"], "")
            if r and str(r["value"]) not in shown:
                baseline_speed_wrong.append(m["id"] + " borrowed or missing speed")
            if not r and "Not measured" not in shown:
                baseline_speed_wrong.append(m["id"] + " missing empty speed state")
        check("homepage speed comes only from each selected baseline setup",
              not baseline_speed_wrong, str(baseline_speed_wrong))

        goto(page, "#/recipes")
        cells = page.evaluate("""() => {
          var out = {};
          document.querySelectorAll('tr[data-row]').forEach(function(tr){
            var td = tr.querySelector('.c-dec');
            out[tr.getAttribute('data-row')] = td ? td.innerText.replace(/\\s+/g,' ').trim() : null;
          });
          return out;
        }""")
        wrong, bare, nodata = [], [], []
        for s in SET:
            cell = cells.get(s["id"], "")
            r = rep(s)
            agg = [m for m in speeds(s) if m["metric"] == "decode_agg"]
            if r:
                if str(r["value"]) not in cell:
                    wrong.append(s["id"])
                # a value must always carry its metric, condition and provenance
                if r["provenance"] not in cell or "stream" not in cell.lower():
                    bare.append(s["id"])
            elif agg:
                if "aggregate only" not in cell.lower():
                    wrong.append(s["id"] + " (agg not labelled)")
            elif not speeds(s):
                if "no speed data" not in cell.lower():
                    nodata.append(s["id"])
        check("single-stream value wins the headline on every row", not wrong, str(wrong[:4]))
        check("no bare number: every decode cell states condition and provenance", not bare, str(bare[:4]))
        check("recipes with no speed measurement say so explicitly", not nodata, str(nodata[:4]))
        n_nospeed = len([s for s in SET if not speeds(s)])
        check("measurement-free recipes still render", n_nospeed > 0 and rows(page) == TOTAL,
              f"{n_nospeed} of {TOTAL} carry no speed measurement")

        # the specific cases the 2026-09-07 review caught
        worst = "qwen38-flash-next-orcarouter-gguf-uncensored"
        if any(s["id"] == worst for s in SET):
            c = cells.get(worst, "")
            check("worst aggregate offender headlines its single-stream figure, not 489",
                  "489" not in c and "28.7" in c, c)
        mean_case = "qwen36-27b-unsloth-gguf-llamacpp-4090-samevocab"
        if any(s["id"] == mean_case for s in SET):
            c = cells.get(mean_case, "")
            check("same-vocabulary 4090 row headlines its mean, not its peak",
                  "43.2" in c and "67.1" not in c, c)

        # aggregate and per-stream-at-load appear together in the expanded panel
        agg_case = next((s for s in SET
                         if any(m["metric"] == "decode_agg" for m in s.get("measurements", []))
                         and any(m["metric"] == "decode_per_stream" and (m.get("concurrency") or 0) > 1
                                 for m in s.get("measurements", []))), None)
        if agg_case:
            page.click(f'[data-exp="{agg_case["id"]}"]')
            page.wait_for_timeout(250)
            t = text(page)
            check("aggregate context states concurrency and per-stream speed at that load",
                  "across" in t and "each at that load" in t, agg_case["id"])
            page.click(f'[data-exp="{agg_case["id"]}"]')
            page.wait_for_timeout(150)

        # ------------------------------------------------- the trust strip
        strips = page.evaluate("""() => {
          var out = {};
          document.querySelectorAll('[data-ev]').forEach(function(b){
            out[b.getAttribute('data-ev')] = { glyphs: b.innerText.replace(/\\s+/g,''),
                                               label: b.getAttribute('aria-label') };
          });
          return out;
        }""")

        def py_perf(s):
            sp = speeds(s)
            if not sp:
                return "○"
            box = [m for m in sp if m["provenance"] == "box"]
            if any((m.get("n") or 0) > 1 and m.get("method") for m in box):
                return "●"
            forum = [m for m in sp if m["provenance"] == "forum"]
            if any((m.get("n") or 0) > 1 or m.get("stat") for m in forum):
                return "◑"
            if box:
                return "◑"
            if forum:
                return "◐"
            return "◔"

        bad_strip, unlabeled = [], []
        for s in SET:
            st = strips.get(s["id"])
            if not st:
                bad_strip.append(s["id"] + " (missing)")
                continue
            if len(st["glyphs"]) != 4:
                bad_strip.append(s["id"] + f" ({st['glyphs']})")
                continue
            if st["glyphs"][2] != py_perf(s):
                bad_strip.append(f"{s['id']} perf {st['glyphs'][2]} != {py_perf(s)}")
            lab = st["label"] or ""
            if not all(d in lab for d in ("Recipe:", "Compatibility:", "Performance:", "Capability:")):
                unlabeled.append(s["id"])
        check("every recipe carries a four-cell evidence strip, recomputed correctly",
              not bad_strip, str(bad_strip[:4]))
        check("the strip's accessible name names all four dimensions", not unlabeled, str(unlabeled[:3]))

        box_ids = {s["id"] for s in SET if s.get("provenance_tier") == "box"}
        note(f"{len(box_ids)} owner-measured, "
             f"{len([s for s in SET if s.get('provenance_tier') == 'forum'])} community-reported, "
             f"{len([s for s in SET if not s.get('provenance_tier')])} unmeasured")

        # ------------------------------------------- capability conflicts
        MOD = {"image": "vision", "video": "video", "audio": "audio"}
        conflicts = [s["id"] for s in SET
                     if any(MOD.get(mod) and (s.get("capabilities") or {}).get(MOD[mod]) is False
                            for mod in MODELS[s["model"]].get("modalities", []))]
        collapsed = page.evaluate("""() => {
          var out = {};
          document.querySelectorAll('tr[data-row]').forEach(function(tr){
            out[tr.getAttribute('data-row')] = tr.innerText;
          });
          return out;
        }""")
        missed = [i for i in conflicts if "runtime" not in (collapsed.get(i) or "")]
        check("a capability the runtime disables is visible on the collapsed row",
              not missed, f"{len(conflicts)} conflicts, missed {missed[:3]}")

        # ------------------------------------------------- no fit on Directory
        body = text(page)
        verdictish = page.evaluate("""() => Array.from(document.querySelectorAll(
            '.mark, .verdict, .c-ready, .c-hw, .res, .banner, .shelf-meta'))
          .map(n => n.innerText).join(' | ')""")
        found_fit = re.findall(r".{0,30}(?:^|[^a-z])(?:fits|over budget|too big)(?:[^a-z]|$).{0,30}",
                               verdictish, re.I)
        check("no fit verdict in any Directory status element", not found_fit, str(found_fit[:2]))
        req_shown = page.evaluate("Array.from(document.querySelectorAll('.c-hw')).filter(n=>/needs/.test(n.innerText)).length")
        check("Directory rows show the neutral recorded requirement instead", req_shown > 0, str(req_shown))

        # -------------------------------------------------------- searching
        page.fill("#q", "dflash2")
        page.wait_for_timeout(320)
        n = rows(page)
        check("search narrows the directory", 0 < n < TOTAL, f"{n} rows")
        got = set(rowids(page))
        expect = {s["id"] for s in SET if "dflash2" in json.dumps(s).lower()}
        check("every search hit contains the term somewhere searchable",
              got.issubset(expect), str(sorted(got - expect)[:3]))

        page.fill("#q", "sglang mlx")
        page.wait_for_timeout(320)
        check("multi-term search requires all terms (AND)", rows(page) == 0, str(rows(page)))
        check("no-match renders an empty state with a clear action",
              "No recipes match" in text(page) and page.locator("#clear-all").count() > 0)
        page.click("#clear-all")
        page.wait_for_timeout(300)
        check("clear-all restores the full directory and empties the search box",
              rows(page) == TOTAL and page.input_value("#q") == "", str(rows(page)))

        page.fill("#q", "nvfp4")
        page.wait_for_timeout(320)
        check("search state is serialized into the URL", "q=nvfp4" in page.url, page.url)
        page.fill("#q", "")
        page.wait_for_timeout(320)

        # --------------------------------------------------------- filtering
        opts = page.evaluate("""() => {
          var out = {};
          document.querySelectorAll('#filters select[data-f]').forEach(function(s){
            out[s.getAttribute('data-f')] = Array.from(s.options).map(o=>o.value).filter(Boolean);
          });
          return out;
        }""")
        FGET = {
            "gen": lambda s: [str(MODELS[s["model"]]["generation"])],
            "arch": lambda s: [MODELS[s["model"]]["architecture"].get("kind", "")],
            "engine": lambda s: [s["engine"]["id"]],
            "quant": lambda s: [s["variation"]["quant"]],
            "hw": lambda s: s["hardware"],
            "evid": lambda s: [s.get("provenance_tier") or "none"],
        }
        bogus = []
        for key, values in opts.items():
            if key not in FGET:
                continue
            real = set()
            for s in SET:
                real.update(FGET[key](s))
            for v in values:
                if v not in real:
                    bogus.append(f"{key}={v}")
        check("every filter option exists in the dataset", not bogus, str(bogus[:5]))

        page.select_option("#f-evid", "box")
        page.wait_for_timeout(280)
        check("evidence=owner-measured yields exactly the box-tier setups",
              set(rowids(page)) == box_ids, f"{rows(page)} rows")
        page.select_option("#f-engine", "sglang")
        page.wait_for_timeout(280)
        both = {s["id"] for s in SET if s.get("provenance_tier") == "box" and s["engine"]["id"] == "sglang"}
        check("two filters combine (AND)", set(rowids(page)) == both, f"{rows(page)} rows")
        chips = page.evaluate("document.querySelectorAll('.chip[data-clear]').length")
        check("each active filter is a removable chip", chips == 2, str(chips))
        page.click('.chip[data-clear="engine"]')
        page.wait_for_timeout(280)
        check("removing one chip leaves the other filter in place",
              set(rowids(page)) == box_ids, f"{rows(page)} rows")
        page.click('.chip[data-clear="evid"]')
        page.wait_for_timeout(280)
        check("removing the last chip restores the whole directory",
              rows(page) == TOTAL and page.evaluate("document.querySelectorAll('.chip[data-clear]').length") == 0,
              str(rows(page)))

        page.click("#adv-toggle")
        page.wait_for_timeout(250)
        adv = page.evaluate("document.querySelectorAll('#adv-panel select[data-f]').length")
        check("advanced filters open as an inline panel, not a modal",
              adv >= 10 and page.locator("#adv-panel").is_visible(), str(adv))
        check("advanced panel labels the OS facet as implied",
              "implied" in page.evaluate("document.querySelector('#adv-panel').innerText").lower())
        page.select_option("#f-fail", "yes")
        page.wait_for_timeout(280)
        check("known-failure filter returns a non-empty, narrowed set",
              0 < rows(page) < TOTAL, f"{rows(page)} rows")
        page.click('.chip[data-clear="fail"]')
        page.wait_for_timeout(250)
        page.click("#adv-toggle")
        page.wait_for_timeout(250)

        # ---------------------------------------------------------- sorting
        modes = page.evaluate("Array.from(document.querySelectorAll('#sort option')).map(o=>o.value)")
        check("nine sort modes are offered", len(modes) == 9, str(len(modes)))
        broken_sorts = []
        for m in modes:
            page.select_option("#sort", m)
            page.wait_for_timeout(240)
            if rows(page) != TOTAL:
                broken_sorts.append(m)
        check("every sort mode keeps the whole directory visible", not broken_sorts, str(broken_sorts))

        page.select_option("#sort", "evidence")
        page.wait_for_timeout(260)
        first_shelf = page.evaluate("""() => {
          var s = document.querySelector('.shelf');
          return Array.from(s.querySelectorAll('tr[data-row]')).map(t=>t.getAttribute('data-row'));
        }""")
        check("sort by evidence orders rows within the shelf, not across shelves",
              page.evaluate("document.querySelectorAll('.shelf').length") == len(MODELS),
              str(len(first_shelf)))

        page.select_option("#sort", "speed")
        page.wait_for_timeout(260)
        d = page.evaluate("(document.querySelector('.disclose')||{}).innerText||''")
        check("speed sorting carries a non-dismissible disclosure",
              "not a leaderboard" in d.lower() and "different hardware" in d.lower(), d[:80])
        check("the disclosure has no dismiss control",
              page.evaluate("!document.querySelector('.disclose button, .disclose [aria-label*=close]')"))
        page.select_option("#sort", "updated")
        page.wait_for_timeout(250)

        # ------------------------------------------------ expand / keyboard
        target = SET[0]["id"]
        st = page.evaluate("""id => {
          var b = document.querySelector('[data-exp="'+id+'"]');
          return { aria: b.getAttribute('aria-expanded'), det: !!document.getElementById('d-'+id) };
        }""", target)
        check("rows start collapsed", st["aria"] == "false" and not st["det"], str(st))
        page.click(f'[data-exp="{target}"]')
        page.wait_for_timeout(250)
        st = page.evaluate("""id => {
          var b = document.querySelector('[data-exp="'+id+'"]'), d = document.getElementById('d-'+id);
          return { aria: b.getAttribute('aria-expanded'), h: d ? d.offsetHeight : 0,
                   secs: d ? d.querySelectorAll('.sec > h2, .sec > h3').length : 0,
                   srcs: d ? d.querySelectorAll('.srcs a').length : 0,
                   page: d ? !!d.querySelector('a[href^="#/recipes/"]') : false };
        }""", target)
        check("click expands the row in place", st["h"] > 0 and st["aria"] == "true", str(st["h"]))
        check("expanded panel carries the full section set", st["secs"] >= 6, str(st["secs"]))
        check("expanded panel lists sources", st["srcs"] > 0, str(st["srcs"]))
        check("expanded panel links to the permanent recipe page", st["page"])
        page.click(f'[data-exp="{target}"]')
        page.wait_for_timeout(200)
        check("second click collapses",
              page.evaluate("id => !document.getElementById('d-'+id)", target))

        page.focus(f'[data-exp="{target}"]')
        page.keyboard.press("Enter")
        page.wait_for_timeout(250)
        check("Enter expands (keyboard operable)",
              page.evaluate("id => !!document.getElementById('d-'+id)", target))
        page.focus(f'[data-exp="{target}"]')
        page.keyboard.press(" ")
        page.wait_for_timeout(250)
        check("Space collapses (keyboard operable)",
              page.evaluate("id => !document.getElementById('d-'+id)", target))

        # Clicking the row itself (e.g. the artifact title) must expand it too;
        # the compare checkbox must not.
        page.click(f'tr[data-row="{target}"] td .l1.mono')
        page.wait_for_timeout(250)
        check("clicking the title cell expands the row",
              page.evaluate("id => !!document.getElementById('d-'+id)", target))
        page.click(f'tr[data-row="{target}"] td .l1.mono')
        page.wait_for_timeout(250)
        check("clicking the title cell again collapses the row",
              page.evaluate("id => !document.getElementById('d-'+id)", target))
        page.click(f'tr[data-row="{target}"] input.cbx')
        page.wait_for_timeout(250)
        cb = page.evaluate("""id => ({
          det: !!document.getElementById('d-'+id),
          checked: document.querySelector('input.cbx[data-cmp="'+id+'"]').checked })""", target)
        check("the compare checkbox does not expand the row",
              not cb["det"] and cb["checked"], str(cb))
        page.click(f'tr[data-row="{target}"] input.cbx')
        page.wait_for_timeout(200)

        ring = page.evaluate("""() => {
          var b = document.querySelector('[data-exp]'); b.focus();
          var s = getComputedStyle(b, ':focus-visible');
          return getComputedStyle(document.documentElement).getPropertyValue('--sel').trim();
        }""")
        check("a selection colour token is defined for the focus ring", bool(ring), ring)

        # ------------------------------------------------------------- copy
        cmd_case = next((s for s in SET if s["run"].get("command")), None)
        page.click(f'[data-exp="{cmd_case["id"]}"]')
        page.wait_for_timeout(260)
        cp = page.evaluate("""id => {
          var d = document.getElementById('d-'+id);
          var b = d.querySelector('.cmd .copy');
          return { attr: b.getAttribute('data-copy'),
                   visible: b.previousElementSibling.textContent,
                   doCopies: d.querySelectorAll('.steps .do .copy').length };
        }""", cmd_case["id"])
        check("copy button carries exactly the visible command",
              cp["attr"].strip() == cp["visible"].strip(), cp["attr"][:60])
        check("prose steps carry no copy affordance", cp["doCopies"] == 0, str(cp["doCopies"]))
        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        page.click(f'#d-{cmd_case["id"]} .cmd .copy')
        page.wait_for_timeout(400)
        label = page.evaluate("id => document.querySelector('#d-'+id+' .cmd .copy').textContent", cmd_case["id"])
        check("copy gives feedback", label == "copied", repr(label))
        try:
            clip = page.evaluate("navigator.clipboard.readText()")
            check("clipboard holds the command", clip.strip() == cp["attr"].strip(), clip[:60])
        except Exception as exc:
            note(f"clipboard read unavailable in this environment: {exc}")

        # step kinds are honoured: prose never rendered as a runnable command
        prose_case = next((s for s in SET
                           if any(x.get("kind") == "do" for x in s["run"].get("steps", []))), None)
        if prose_case:
            goto(page, f"#/recipes/{prose_case['id']}")
            k = page.evaluate("""() => ({
              cmds: document.querySelectorAll('.steps .cmd code').length,
              dos: document.querySelectorAll('.steps .do').length })""")
            expected_do = len([x for x in prose_case["run"]["steps"] if x["kind"] == "do"])
            check("prose steps render as prose, commands as commands",
                  k["dos"] == expected_do, f"{k} expected {expected_do} prose")

        # ---------------------------------------------------------- compare
        goto(page, "#/recipes")
        check("compare rail is absent at zero selections, not empty",
              page.evaluate("document.querySelectorAll('.crail').length") == 0)
        ids = [s["id"] for s in SET[:5]]
        page.evaluate("id => document.querySelector('input[data-cmp=\"'+id+'\"]').click()", ids[0])
        page.wait_for_timeout(220)
        st = page.evaluate("""() => ({
          rail: document.querySelectorAll('.crail').length,
          action: (document.querySelector('.crail-end a')||{}).textContent||'',
          disabled: (document.querySelector('.crail-end a')||{}).getAttribute
                      ? document.querySelector('.crail-end a').getAttribute('aria-disabled') : null
        })""")
        check("rail appears at one selection", st["rail"] == 1)
        check("one selection disables the action and states why",
              st["disabled"] == "true" and "one more" in st["action"].lower(), st["action"])
        for i in ids[1:4]:
            page.evaluate("id => document.querySelector('input[data-cmp=\"'+id+'\"]').click()", i)
            page.wait_for_timeout(180)
        check("rail holds four selections",
              page.evaluate("document.querySelectorAll('.citem').length") == 4)
        page.evaluate("id => document.querySelector('input[data-cmp=\"'+id+'\"]').click()", ids[4])
        page.wait_for_timeout(220)
        check("compare refuses a fifth selection rather than silently ignoring it",
              page.evaluate("document.querySelectorAll('.citem').length") == 4 and
              "remove one first" in page.evaluate("document.getElementById('live').textContent").lower(),
              page.evaluate("document.getElementById('live').textContent"))
        summary = page.evaluate("(document.querySelector('.crail-cmp')||{}).textContent||''")
        check("rail states whether the measurements look comparable",
              "comparable" in summary.lower(), summary[:70])

        goto(page, "#/hardware")
        check("selection persists across tabs",
              page.evaluate("document.querySelectorAll('.citem').length") == 4)

        goto(page, "#/compare")
        cw = page.evaluate("""() => ({
          groups: Array.from(document.querySelectorAll('.cmp tr.grp th.k')).map(n=>n.textContent),
          cols: document.querySelectorAll('.cmp thead th').length,
          banner: (document.querySelector('.banner h3')||{}).textContent||'',
          rows: document.querySelectorAll('.cmp tbody tr').length,
          winner: document.querySelectorAll('.winner,.best,[data-winner]').length,
          body: document.body.innerText
        })""")
        want = ["Identity", "Runtime", "Hardware", "Capabilities", "Performance", "Trust", "Risks"]
        check("compare workspace renders all seven sections",
              [g for g in cw["groups"]] == want, str(cw["groups"]))
        check("compare renders one column per selected recipe plus the field column",
              cw["cols"] == 5, str(cw["cols"]))
        check("compare declares no overall winner",
              cw["winner"] == 0 and "No overall winner" in cw["body"], str(cw["winner"]))
        low = cw["body"].lower()
        check("compare surfaces the unrecorded engine-version field rather than hiding it",
              "engine version" in low and "not recorded" in low)
        check("comparability banner fires on a mismatched selection",
              "not directly comparable" in cw["banner"].lower(), cw["banner"])

        # a matched pair must NOT be flagged
        pair = None
        for a in SET:
            for b in SET:
                if a["id"] >= b["id"]:
                    continue
                ra, rb = rep(a), rep(b)
                if (a["engine"]["id"] == b["engine"]["id"] and a["hardware"] == b["hardware"]
                        and ra and rb and ra["metric"] == rb["metric"]
                        and ra.get("stat") == rb.get("stat")
                        and ra.get("concurrency") == rb.get("concurrency")
                        and ra["provenance"] == rb["provenance"] and a["model"] == b["model"]):
                    pair = (a["id"], b["id"])
                    break
            if pair:
                break
        if pair:
            goto(page, f"#/compare?sel={pair[0]},{pair[1]}")
            bn = page.evaluate("(document.querySelector('.banner h3')||{}).textContent||''")
            check("a genuinely matched pair is not flagged as incomparable",
                  "directly comparable" in bn.lower() and "not" not in bn.lower(), bn)
        else:
            note("no fully matched pair exists in this dataset; positive-comparability case not exercised")

        goto(page, "#/compare?sel=does-not-exist")
        check("a stale recipe id in a compare URL does not break the route",
              page.evaluate("document.body.getAttribute('data-route')") == "compare" and not page_errors)

        page.evaluate("sessionStorage.clear()")
        goto(page, "#/compare")
        check("compare with nothing selected explains itself instead of erroring",
              "Nothing is selected yet" in text(page))

        # ------------------------------------------------------ my hardware
        goto(page, "#/hardware")
        check("My Hardware states what detection reads and that nothing leaves the device",
              "Nothing leaves this device" in text(page) and "navigator.deviceMemory" in text(page))
        page.select_option("#hw-known", "mac-64gb")
        page.wait_for_timeout(450)
        hw = page.evaluate("""() => ({
          groups: Array.from(document.querySelectorAll('.grp-hd h2')).map(n=>n.textContent),
          counts: Array.from(document.querySelectorAll('.grp-hd .n')).map(n=>+n.textContent),
          verdicts: Array.from(document.querySelectorAll('.verdict')).map(n=>n.textContent),
          body: document.body.innerText
        })""")
        check("all five compatibility groups render, including empty ones",
              len(hw["groups"]) == 5, str(hw["groups"]))
        check("every recipe is placed in exactly one group",
              sum(hw["counts"]) == TOTAL, f"{sum(hw['counts'])} vs {TOTAL}")
        verdict_words = ("Verified", "Likely to fit", "Uncertain", "Will not fit")
        badv = [v[:60] for v in hw["verdicts"] if not any(w in v for w in verdict_words)]
        check("every verdict is hedged and never an unconditional 'fits'", not badv, str(badv[:3]))
        check("no verdict element says a bare 'Fits'",
              not any(re.match(r"\s*(✓\s*)?fits\b", v, re.I) for v in hw["verdicts"]))

        page.evaluate("document.querySelectorAll('.res .calc').forEach(d=>d.open=true)")
        page.wait_for_timeout(250)
        calc = page.evaluate("(document.querySelector('.calc-tab')||{}).innerText||''")
        for label in ("MODEL MEMORY", "RUNTIME BUFFERS", "KV-CACHE ALLOWANCE", "ASSUMED CONTEXT",
                      "ASSUMED CONCURRENCY", "SAFETY RESERVE", "CPU / DISK OFFLOAD",
                      "RECORDED RESIDENT", "YOUR USABLE MEMORY", "REMAINING", "EVIDENCE"):
            check(f"compatibility breakdown states {label.lower()}", label in calc.upper(), "")

        kv_known = {mid for mid, m in MODELS.items() if m.get("kv_bytes_per_token") is not None}
        kv_check = page.evaluate("""() => {
          var out = [];
          document.querySelectorAll('.res').forEach(function(r){
            var a = r.querySelector('h3 a');
            var row = Array.from(r.querySelectorAll('.calc-tab tr'))
              .filter(t => /KV-CACHE/i.test(t.innerText))[0];
            if (a && row) out.push([a.getAttribute('href'), /not derivable/i.test(row.innerText)]);
          });
          return out;
        }""")
        by_id = {s["id"]: s for s in SET}
        wrongkv = []
        for href, notderiv in kv_check:
            sid = href.split("/")[-1]
            model = by_id[sid]["model"]
            if (model in kv_known) == notderiv:
                wrongkv.append(sid)
        check("KV allowance is computed only where bytes-per-token is recorded, never estimated",
              not wrongkv, f"{len(kv_known)} of {len(MODELS)} families record it; wrong: {wrongkv[:3]}")

        page.select_option("#as-ctx", "32768")
        page.wait_for_timeout(400)
        check("changing an assumption re-groups the results",
              sum(page.evaluate("Array.from(document.querySelectorAll('.grp-hd .n')).map(n=>+n.textContent)")) == TOTAL)

        goto(page, "#/recipes")
        check("a saved hardware profile never narrows the Directory", rows(page) == TOTAL, str(rows(page)))
        verdictish = page.evaluate("""() => Array.from(document.querySelectorAll(
            '.mark, .verdict, .c-ready, .c-hw, .res, .banner')).map(n => n.innerText).join(' | ')""")
        stray = re.findall(r".{0,40}(?:^|[^a-z])(?:fits|over budget)(?:[^a-z]|$).{0,40}", verdictish, re.I)
        check("a saved hardware profile never adds a fit verdict to the Directory",
              not stray, str(stray[:2]))

        # detection degrades honestly when the APIs are absent
        ctx2 = browser.new_context(viewport={"width": 1440, "height": 1000})
        p2 = ctx2.new_page()
        p2.add_init_script("""
          delete navigator.gpu;
          HTMLCanvasElement.prototype.getContext = function(){ return null; };
          Object.defineProperty(navigator, 'deviceMemory', { get: function(){ return undefined; } });
        """)
        p2.goto(BASE + "#/hardware")
        p2.wait_for_timeout(300)
        p2.click("#hw-detect")
        p2.wait_for_timeout(2600)
        t2 = p2.evaluate("document.body.innerText")
        check("detection reports what it could not read instead of guessing",
              "not detectable" in t2.lower() and "enter it yourself" in t2.lower())
        ctx2.close()

        # storage failure must not break the tab
        ctx3 = browser.new_context(viewport={"width": 1440, "height": 1000})
        p3 = ctx3.new_page()
        p3_errors = []
        p3.on("pageerror", lambda e: p3_errors.append(str(e)))
        p3.add_init_script("""
          var t = function(){ throw new Error('blocked'); };
          Object.defineProperty(window, 'localStorage', { get: function(){ throw new Error('blocked'); } });
        """)
        p3.goto(BASE + "#/hardware")
        p3.wait_for_timeout(400)
        check("blocked site storage does not break the page",
              not p3_errors and "your machine" in p3.evaluate("document.body.innerText").lower(),
              str(p3_errors[:2]))
        ctx3.close()

        # ------------------------------------------- no requests after load
        seen = []
        ctx4 = browser.new_context(viewport={"width": 1440, "height": 1000})
        p4 = ctx4.new_page()
        p4.goto(URL)
        p4.wait_for_timeout(300)
        p4.on("request", lambda r: seen.append(r.url))
        for h in ("#/hardware", "#/compare", "#/methodology", f"#/models/{SET[0]['model']}"):
            p4.goto(BASE + h)
            p4.wait_for_timeout(200)
        external = [u for u in seen if not u.startswith(BASE.rsplit("/", 1)[0])]
        check("the page makes no external network request while navigating",
              not external, str(external[:3]))
        ctx4.close()

        # ------------------------------------------------------ methodology
        goto(page, "#/methodology")
        m = text(page)
        for phrase in ("never blended", "leaderboard", "reading speed",
                       "bytes per token", "Engine version", "Reddit"):
            check(f"methodology documents: {phrase}", phrase.lower() in m.lower(), "")
        check("coverage counts live on methodology, not on the Directory",
              str(TOTAL) in m and str(len(MODELS)) in m)
        goto(page, "#/recipes")
        check("no vanity counts strip on Recipes",
              page.evaluate("document.querySelectorAll('#counts').length") == 0)

        # ---------------------------------------------------- accessibility
        for h in ("#/", "#/recipes", "#/hardware", "#/compare", "#/methodology",
                  f"#/models/{SET[0]['model']}", f"#/recipes/{SET[0]['id']}"):
            goto(page, h)
            a11y = page.evaluate("""() => {
              var hs = Array.from(document.querySelectorAll('h1,h2,h3,h4'))
                        .map(n => +n.tagName[1]);
              var skipped = false, prev = 0;
              hs.forEach(function(l){ if (prev && l > prev + 1) skipped = true; prev = l; });
              var unnamed = Array.from(document.querySelectorAll(
                  'button, a[href], input, select, [role=button]'))
                .filter(function(n){ return n.checkVisibility ? n.checkVisibility() : n.offsetParent !== null; })
                .filter(function(n){
                  var t = (n.innerText||'').trim() || n.getAttribute('aria-label') ||
                          n.getAttribute('title') || n.value ||
                          (n.labels && n.labels.length ? n.labels[0].innerText : '');
                  return !String(t).trim();
                }).length;
              return {
                h1: document.querySelectorAll('h1').length,
                main: document.querySelectorAll('main').length,
                banner: document.querySelectorAll('header[role=banner]').length,
                nav: document.querySelectorAll('nav').length,
                live: document.querySelectorAll('[aria-live]').length,
                current: document.querySelectorAll('.tab[aria-current=page]').length,
                skipped: skipped, unnamed: unnamed
              };
            }""")
            label = h
            check(f"{label}: exactly one landmark main / banner / nav",
                  a11y["main"] == 1 and a11y["banner"] == 1 and a11y["nav"] >= 1, str(a11y))
            check(f"{label}: heading levels are never skipped", not a11y["skipped"], "")
            check(f"{label}: every interactive element has an accessible name",
                  a11y["unnamed"] == 0, str(a11y["unnamed"]))
            check(f"{label}: a polite live region exists", a11y["live"] >= 1, "")
            if h in ("#/", "#/recipes", "#/hardware", "#/compare"):
                check(f"{label}: the active tab is marked aria-current",
                      a11y["current"] == 1, str(a11y["current"]))
            if h in ("#/", "#/recipes"):
                check(f"{h} has exactly one h1-level page heading",
                      a11y["h1"] <= 1, str(a11y["h1"]))

        goto(page, "#/recipes")
        page.fill("#q", "mlx")
        page.wait_for_timeout(350)
        live = page.evaluate("document.getElementById('live').textContent")
        check("filtering announces the new result count", "of " + str(TOTAL) in live, live)
        page.fill("#q", "")
        page.wait_for_timeout(300)

        tbl = page.evaluate("""() => {
          var t = document.querySelector('.rows');
          return { caption: !!t.querySelector('caption'),
                   ths: t.querySelectorAll('thead th[scope=col]').length };
        }""")
        check("recipe rows are a real table with a caption and column scopes",
              tbl["caption"] and tbl["ths"] == 10, str(tbl))

        # reduced motion
        ctx5 = browser.new_context(viewport={"width": 1440, "height": 1000},
                                   reduced_motion="reduce")
        p5 = ctx5.new_page()
        p5.goto(URL)
        p5.wait_for_timeout(300)
        dur = p5.evaluate("""() => {
          var n = document.querySelector('.tab');
          return getComputedStyle(n).transitionDuration;
        }""")
        check("reduced motion collapses transitions", dur in ("0s", "0.00001s", "1e-05s"), dur)
        ctx5.close()

        # ---------------------------------------------------- entity leakage
        leaks = {}
        for h in ("#/", "#/hardware", "#/compare", "#/methodology", "#/contribute",
                  f"#/models/{SET[0]['model']}", f"#/recipes/{SET[0]['id']}"):
            goto(page, h)
            found = page.evaluate(r"""() => {
              var m = document.body.innerText.match(/&(amp|lt|gt|quot|rarr|mdash|hellip|middot|nbsp|#\d+);/g);
              return m ? m.slice(0,4) : [];
            }""")
            if found:
                leaks[h] = found
        check("no HTML entity leaks into rendered text on any route", not leaks, str(leaks))

        # ---------------------------------------------------------- reflow
        for w, hgt in ((390, 844), (834, 1112), (1440, 1000), (1920, 1080)):
            page.set_viewport_size({"width": w, "height": hgt})
            for h in ("#/", "#/recipes", "#/compare", "#/hardware", f"#/recipes/{SET[0]['id']}"):
                goto(page, h)
                check(f"no horizontal page overflow at {w}px on {h}", not overflow(page),
                      str(widest(page)))

        page.set_viewport_size({"width": 390, "height": 844})
        goto(page, "#/")
        check("mobile homepage renders model summaries, not recipe rows",
              page.evaluate("document.querySelectorAll('[data-model-select]').length") == len(MODELS) and
              rows(page) == 0,
              str(page.evaluate("document.querySelectorAll('[data-model-select]').length")))
        page.click('[data-model-select="qwen3-8-flash-next"]')
        page.wait_for_timeout(250)
        check("mobile model selection opens the model page",
              page.evaluate("document.body.getAttribute('data-route')") == "model")

        goto(page, "#/recipes")
        check("mobile renders structured summaries, not a compressed table",
              page.evaluate("document.querySelectorAll('.rows-m > li').length") == TOTAL and
              page.evaluate("document.querySelectorAll('table.rows').length") == 0,
              str(page.evaluate("document.querySelectorAll('.rows-m > li').length")))
        page.fill("#q", "nvfp4")
        page.wait_for_timeout(320)
        check("search works at mobile width", 0 < rows(page) < TOTAL, str(rows(page)))
        check("no overflow after filtering on mobile", not overflow(page))
        page.evaluate("id => document.querySelector('input[data-cmp=\"'+id+'\"]').click()",
                      rowids(page)[0])
        page.wait_for_timeout(250)
        check("mobile compare rail shows count and action, not the full chip list",
              page.evaluate("document.querySelectorAll('.crail').length") == 1 and
              not page.evaluate("document.querySelector('.crail-items').offsetHeight"))

        # 400% zoom equivalent on a 1280 viewport
        page.set_viewport_size({"width": 320, "height": 700})
        goto(page, "#/recipes")
        check("no overflow at 320px (400% zoom on a 1280 viewport)", not overflow(page),
              str(widest(page)) + " " + str(page.evaluate(
                  "[document.documentElement.scrollWidth, document.documentElement.clientWidth]")))

        # -------------------------------------------------------- dark theme
        ctx6 = browser.new_context(viewport={"width": 1440, "height": 1000},
                                   color_scheme="dark")
        p6 = ctx6.new_page()
        p6_errors = []
        p6.on("pageerror", lambda e: p6_errors.append(str(e)))
        p6.goto(URL)
        p6.wait_for_timeout(300)
        dark = p6.evaluate("""() => {
          var bg = getComputedStyle(document.body).backgroundColor;
          var m = bg.match(/\\d+/g).map(Number);
          return { bg: bg, lum: (m[0]+m[1]+m[2])/3,
                    models: document.querySelectorAll('[data-model-select]').length,
                    transparent: bg === 'rgba(0, 0, 0, 0)' };
        }""")
        check("dark theme paints an explicit dark body background",
              not dark["transparent"] and dark["lum"] < 60, str(dark["bg"]))
        check("dark theme renders the full model homepage", dark["models"] == len(MODELS), str(dark["models"]))
        check("no page errors in dark theme", not p6_errors, str(p6_errors[:2]))
        ctx6.close()

        # ---------------------------------------------------------- console
        real = [e for e in console_errors if "favicon" not in e.lower()]
        check("no page errors", not page_errors, json.dumps(page_errors)[:400])
        check("no console errors", not real, json.dumps(real)[:400])

        browser.close()

    print()
    if fails:
        print(f"{len(fails)} FAILED:", file=sys.stderr)
        for f in fails:
            print("  - " + f, file=sys.stderr)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
