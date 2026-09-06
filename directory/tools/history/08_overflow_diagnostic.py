#!/usr/bin/env python3
"""Find exactly which elements overflow the viewport at mobile width."""
import json
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    p = b.new_context(viewport={"width": 390, "height": 844}).new_page()
    p.goto("http://127.0.0.1:8848/index.html", wait_until="networkidle")
    p.evaluate("document.getElementById('expand-all').click()")  # measure with bodies open
    p.wait_for_timeout(300)
    out = p.evaluate("""() => {
      const vw = document.documentElement.clientWidth;
      const bad = [];
      document.querySelectorAll('*').forEach(el => {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        if (r.width === 0 && r.height === 0) return;
        const over = r.right - vw;
        if (over > 0.5 || el.scrollWidth - el.clientWidth > 1 && cs.overflowX === 'visible') {
          bad.push({
            tag: el.tagName.toLowerCase(),
            cls: el.className && el.className.toString().slice(0,40),
            id: el.id || '',
            right: Math.round(r.right), left: Math.round(r.left),
            w: Math.round(r.width), over: Math.round(over),
            scrollW: el.scrollWidth, clientW: el.clientWidth,
            overflowX: cs.overflowX, display: cs.display,
            minW: cs.minWidth, whiteSpace: cs.whiteSpace,
            text: (el.textContent||'').replace(/\\s+/g,' ').trim().slice(0,70)
          });
        }
      });
      return {vw, docScrollW: document.documentElement.scrollWidth, bad};
    }""")
    print("viewport:", out["vw"], "doc scrollWidth:", out["docScrollW"])
    for e in out["bad"]:
        print(json.dumps(e))
    b.close()
