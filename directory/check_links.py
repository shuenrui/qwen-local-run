#!/usr/bin/env python3
"""Link-rot guard for the directory dataset.

Re-fetches every URL the dataset cites — setup sources, measurement sources,
variation checkpoints, run recipes, model cards, hardware and publisher pages —
and reports any that no longer resolve. A dead source URL is a provenance
failure: the number it backs can no longer be checked, so the fix is to
re-source or delete the measurement, never to leave the link rotting.

Usage:
    python3 directory/check_links.py            # report, exit 1 if any dead
    python3 directory/check_links.py --quiet    # only dead links

Exit codes: 0 all reachable, 1 at least one dead, 2 fetch machinery error.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import urlparse

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HOST_LOCKS = defaultdict(Lock)
LAST_REQUEST = defaultdict(float)

# Pacing keeps repeated gate runs from tripping host-side rate limiters
# (HuggingFace in particular starts serving 429 after a burst of sweeps).
MIN_HOST_INTERVAL_S = 0.25
RETRY_5XX = [0.5, 1.0]
RETRY_429 = [2.0, 6.0, 14.0]
RETRY_AFTER_CAP_S = 20.0


def load_dir(rel):
    out = {}
    d = os.path.join(DATA, rel)
    for n in sorted(os.listdir(d)):
        if n.endswith(".json"):
            out[n[:-5]] = json.load(open(os.path.join(d, n), encoding="utf-8"))
    return out


def _pace(netloc):
    last = LAST_REQUEST[netloc]
    wait = MIN_HOST_INTERVAL_S - (time.monotonic() - last)
    if wait > 0:
        time.sleep(wait)
    LAST_REQUEST[netloc] = time.monotonic()


def status(url):
    netloc = urlparse(url).netloc
    with HOST_LOCKS[netloc]:
        result = None
        for attempt in range(max(len(RETRY_5XX), len(RETRY_429)) + 1):
            _pace(netloc)
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 directory-check-links"}
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    return r.status
            except urllib.error.HTTPError as e:
                result = e.code
                if e.code == 429:
                    sleeps = RETRY_429
                    if attempt < len(sleeps):
                        retry_after = e.headers.get("Retry-After") if e.headers else None
                        try:
                            delay = min(float(retry_after), RETRY_AFTER_CAP_S)
                        except (TypeError, ValueError):
                            delay = sleeps[attempt]
                        time.sleep(max(delay, 0.0))
                        continue
                    return result
                if e.code in {500, 502, 503, 504} and attempt < len(RETRY_5XX):
                    time.sleep(RETRY_5XX[attempt])
                    continue
                return result
            except (urllib.error.URLError, TimeoutError) as e:
                result = f"err:{type(e).__name__}"
                if attempt < len(RETRY_5XX):
                    time.sleep(RETRY_5XX[attempt])
                    continue
                return result
        return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--strict", action="store_true",
                    help="treat persistent rate-limits (429) as failures")
    args = ap.parse_args()

    setups = load_dir("setups")
    models = load_dir("models")
    hardware = load_dir("hardware")
    publishers = json.load(open(os.path.join(DATA, "publishers.json"),
                                encoding="utf-8"))["publishers"]

    urls = defaultdict(list)
    for sid, s in setups.items():
        for src in s.get("sources", []):
            u = src["url"]
            m = src.get("mirror_url")
            if m and urlparse(u).netloc.endswith("reddit.com"):
                # Reddit hard-403s this environment (AGENTS law 10): the mirror
                # is the verifiable evidence, the permalink the human citation.
                urls[m].append(f"setups/{sid} (mirror of {u})")
            else:
                urls[u].append(f"setups/{sid}")
        for m in s.get("measurements", []):
            if m.get("source"):
                urls[m["source"]].append(f"setups/{sid}:measurement")
        urls[s["variation"]["url"]].append(f"setups/{sid}:checkpoint")
        if s["run"].get("repo"):
            urls[s["run"]["repo"]].append(f"setups/{sid}:run")
    for mid, m in models.items():
        urls[m["url"]].append(f"models/{mid}")
    for hid, h in hardware.items():
        if h.get("url"):
            urls[h["url"]].append(f"hardware/{hid}")
    for pid, p in publishers.items():
        if p.get("url"):
            urls[p["url"]].append(f"publishers/{pid}")

    if not args.quiet:
        print(f"checking {len(urls)} distinct URLs with {args.workers} workers")
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        codes = list(ex.map(status, urls))
    dead = [(u, c, urls[u]) for u, c in zip(urls, codes)
            if c != 200 and c != 429]
    limited = [(u, urls[u]) for u, c in zip(urls, codes) if c == 429]
    for u, where in limited:
        print(f"RATE-LIMITED 429  {u}\n     cited by: {', '.join(where[:4])}\n"
              f"     not dead; re-run later or fetch manually to confirm")
    for u, c, where in dead:
        print(f"DEAD {c}  {u}\n     cited by: {', '.join(where[:4])}")
    if not args.quiet:
        state = f"{len(urls) - len(dead) - len(limited)}/{len(urls)} reachable"
        if limited:
            state += f", {len(limited)} rate-limited"
        print(state)
    if dead:
        return 1
    if limited and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
