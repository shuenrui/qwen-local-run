#!/usr/bin/env python3
"""Build the Qwen local-run directory into one self-contained HTML file.

Stdlib only, no build step at runtime, no backend. Reads data/*.json,
validates it, and writes site/index.html with the dataset inlined so the page
works from file:// as well as over http and makes no network request at all
after load.

The page source lives in site_src/ so it can be diffed and reviewed:

    site_src/shell.html   skeleton with __CSS__, __DATA__ and __APP__ slots
    site_src/app.css      design system, layouts, breakpoints, both themes
    site_src/app.js       router, state, views, filters, compare, hardware

Usage:
    python3 directory/build.py                 # validate + build
    python3 directory/build.py --skip-validate # build only
    python3 directory/build.py --out /tmp/x.html

Presentation contract (see docs/redesign-2026-09-10/):
  * Models are the homepage; the complete recipe directory remains at #/recipes.
  * A single-stream tok/s number always wins the headline; aggregate results
    are never promoted into that slot and always state their concurrency.
  * No fit verdict exists outside the My Hardware route, and no unconditional
    "fits" verdict exists anywhere.
  * Trust is four independent dimensions, never averaged into one badge.
  * Any string passed through esc() must use literal Unicode, never an HTML
    entity -- esc() escapes the ampersand and the entity would leak to the page.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SRC = os.path.join(HERE, "site_src")
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


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def collect() -> dict:
    publishers = load_json("publishers.json")["publishers"]
    models = {m["id"]: m for m in load_dir("models")}
    hardware = {h["id"]: h for h in load_dir("hardware")}
    engines = {e["id"]: e for e in load_dir("engines")}
    setups = load_dir("setups")

    # Newest generation first, then biggest model, so shelves read top-down.
    def model_sort_key(m: dict):
        try:
            gen_num = float(str(m.get("generation") or "0"))
        except ValueError:
            gen_num = 0.0
        return (-gen_num, -(m.get("architecture", {}).get("params_total_b") or 0))

    ordered = sorted(models.values(), key=model_sort_key)

    return {
        "generated": datetime.date.today().isoformat(),
        "publishers": publishers,
        "models": {m["id"]: m for m in ordered},
        "model_order": [m["id"] for m in ordered],
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


def render(data: dict) -> str:
    shell = read(os.path.join(SRC, "shell.html"))
    css = read(os.path.join(SRC, "app.css"))
    app = read(os.path.join(SRC, "app.js"))

    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # The dataset sits in a <script type="application/json"> block, so the only
    # sequence that can break out of it is a literal closing script tag.
    blob = blob.replace("</", "<\\/")

    for token, value in (("__CSS__", css), ("__DATA__", blob), ("__APP__", app)):
        if token not in shell:
            raise SystemExit(f"site_src/shell.html is missing the {token} slot")
        shell = shell.replace(token, value)
    return shell


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
    html = render(data)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)

    c = data["counts"]
    print(
        f"wrote {args.out}  ({len(html):,} bytes)\n"
        f"  {c['setups']} setups, {c['models']} model families, "
        f"{c['hardware']} hardware classes, {c['engines']} engines, "
        f"{c['publishers']} publishers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
