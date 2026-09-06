#!/usr/bin/env python3
"""Confirm wide tables are reachable inside their scroll containers, and shoot
mobile views with cards expanded."""
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    p = b.new_context(viewport={"width": 390, "height": 844}).new_page()
    p.goto("http://127.0.0.1:8848/index.html", wait_until="networkidle")
    p.evaluate("document.getElementById('expand-all').click()")
    p.wait_for_timeout(300)

    info = p.evaluate("""() => {
      const de = document.documentElement;
      const wraps = Array.from(document.querySelectorAll('.tscroll'));
      const tables = Array.from(document.querySelectorAll('table.m'));
      return {
        docScrollW: de.scrollWidth, vw: de.clientWidth,
        tables: tables.length,
        wrapped: tables.filter(t => t.parentElement && t.parentElement.classList.contains('tscroll')).length,
        wraps: wraps.length,
        wrapsOverflowX: wraps.map(w => getComputedStyle(w).overflowX),
        // a wide table whose content is NOT reachable would be a real defect
        unreachable: wraps.filter(w => w.scrollWidth > w.clientWidth + 1
            && getComputedStyle(w).overflowX === 'visible').length,
        scrollableCount: wraps.filter(w => w.scrollWidth > w.clientWidth + 1).length
      };
    }""")
    print(info)

    # Prove reachability: scroll the widest container fully right and confirm
    # its last cell comes inside the viewport.
    res = p.evaluate("""() => {
      const wraps = Array.from(document.querySelectorAll('.tscroll'))
        .filter(w => w.scrollWidth > w.clientWidth + 1);
      if (!wraps.length) return {none: true};
      const w = wraps.reduce((a,b) => b.scrollWidth - b.clientWidth > a.scrollWidth - a.clientWidth ? b : a);
      const before = w.getBoundingClientRect().right;
      w.scrollLeft = w.scrollWidth;
      const lastCell = w.querySelector('tr:last-child td:last-child');
      const r = lastCell.getBoundingClientRect();
      const wr = w.getBoundingClientRect();
      return {delta: w.scrollLeft, clientW: w.clientWidth, scrollW: w.scrollWidth,
              lastCellRightInContainer: Math.round(r.right - wr.left),
              fullyScrolled: Math.abs(w.scrollLeft + w.clientWidth - w.scrollWidth) < 2};
    }""")
    print("scroll-to-end:", res)

    p.evaluate("window.scrollTo(0,0)")
    p.evaluate("document.getElementById('expand-all').click()")  # collapse
    p.wait_for_timeout(200)
    p.evaluate("document.querySelector('.card .chead').click()")
    p.wait_for_timeout(200)
    p.screenshot(path="/tmp/site_mobile_card_open.png")
    p.evaluate("document.querySelectorAll('.card .chead')[2].click()")
    p.wait_for_timeout(200)
    p.screenshot(path="/tmp/site_mobile_measurements.png")

    p.set_viewport_size({"width": 1440, "height": 1000})
    p.wait_for_timeout(200)
    p.screenshot(path="/tmp/site_desktop_top.png")
    p.evaluate("document.getElementById('expand-all').click()")
    p.wait_for_timeout(300)
    p.screenshot(path="/tmp/site_desktop_expanded.png")
    b.close()
