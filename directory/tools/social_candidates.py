#!/usr/bin/env python3
"""Pass-4 social collector for the Qwen local-run directory (AGENTS laws 9-11).

Social channels are a discovery layer. This tool fetches the raw payload of a
post / video / thread / discussion, saves it under
tools/history/inputs/pass4-social/raw/, and appends a skeleton ledger entry to
tools/history/inputs/pass4-social/candidates.json. The agent then reads the
raw payload, extracts measurements per the SCHEMA.md eligibility ladder, and
fills the entry via `add`. Nothing here writes to data/.

Reddit is fetched exclusively through the pullpush mirror (law 10); the
permalink is recorded as discovery_url and the mirror query as mirror_url.

Usage:
    social_candidates.py fetch URL [URL ...]        auto-detect channel per URL
    social_candidates.py fetch-urls FILE            one URL per line
    social_candidates.py search reddit QUERY [--subreddit LocalLLaMA]
    social_candidates.py search youtube QUERY
    social_candidates.py search discussions KEYWORD --repo ggml-org/llama.cpp [--pages N]
    social_candidates.py search forum QUERY [--site hf|nvidia]
    social_candidates.py sweep-x USER [USER ...] [--cutoff YYYY-MM-DD] [--max N]
    social_candidates.py add FILE                   merge filled candidate(s) into ledger
    social_candidates.py list

Stdlib only, plus two optional CLIs: `gh` (authenticated on this box) for
GitHub, and `twitter` (twitter-cli, authenticated) for X — tweet fetch and
user-posts sweeps. The twitter CLI's search endpoint currently 404s
(ClientTransaction init broken), so X discovery runs as sweep-x over curated
accounts with a local keyword filter. X fetch falls back to fxtwitter when the
CLI is unavailable. Reddit is fetched exclusively through mirrors (law 10):
pullpush ids lookup with arctic-shift fallback; the permalink is recorded as
discovery_url and the mirror query as mirror_url.
"""
import argparse
import html as htmlmod
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PASS4 = os.path.join(HERE, "history", "inputs", "pass4-social")
RAW = os.path.join(PASS4, "raw")
LEDGER = os.path.join(PASS4, "candidates.json")
UA = "Mozilla/5.0 (compatible; qwen-directory-pass4-collector; research use)"


def http_get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        raise RuntimeError(f"HTTP {e.code} for {url}: {body}") from None


def jget(url, timeout=25):
    status, body = http_get(url, timeout)
    return json.loads(body)


def save_raw(name, payload):
    os.makedirs(RAW, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120]
    path = os.path.join(RAW, safe)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    return os.path.relpath(path, PASS4)


def load_ledger():
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def save_ledger(rows):
    os.makedirs(PASS4, exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)


def skeleton(**kw):
    e = {
        "channel": "", "discovery_url": "", "discovery_quote": "",
        "discovery_date": "", "author": "", "mirror_url": "",
        "raw_file": "", "canonical_urls": [], "meta": {},
        "model": "", "checkpoint": "", "publisher": "", "quant": "",
        "format": "", "engine": "", "hardware": "", "config": "",
        "spec_decode": "", "size_gb": None, "status": "",
        "tier_eligibility": "", "measurements": [], "method_note": "",
        "collected": datetime.now(timezone.utc).date().isoformat(),
        "state": "raw",
    }
    e.update({k: v for k, v in kw.items() if v not in (None, "", [])})
    return e


def upsert(entry):
    rows = load_ledger()
    for i, r in enumerate(rows):
        if r.get("discovery_url") == entry["discovery_url"]:
            merged = dict(r)
            for k, v in entry.items():
                if v not in (None, "", [], {}):
                    merged[k] = v
            if r.get("state") in ("extracted", "vetted", "merged") \
                    and entry.get("state") == "raw":
                merged["state"] = r["state"]
            rows[i] = merged
            save_ledger(rows)
            return "updated", i
    rows.append(entry)
    save_ledger(rows)
    return "added", len(rows) - 1


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", htmlmod.unescape(s)).strip()


def extract_links(text, limit=25):
    urls = re.findall(r"https?://[^\s\"'<>()\[\]]+", text or "")
    out = []
    for u in urls:
        u = u.rstrip(".,;:!?\u201d")
        if u not in out:
            out.append(u)
        if len(out) >= limit:
            break
    return out


def detect_channel(url):
    netloc = urllib.parse.urlparse(url).netloc.lower()
    path = urllib.parse.urlparse(url).path
    if "x.com" in netloc or "twitter.com" in netloc:
        return "x"
    if "youtube.com" in netloc or "youtu.be" in netloc:
        return "video-page" if "/watch" not in path and "youtu.be" not in netloc else "youtube"
    if "reddit.com" in netloc:
        return "reddit"
    if "github.com" in netloc:
        return "github-discussion" if "/discussions/" in path else "github-issue"
    if "discuss.huggingface.co" in netloc:
        return "forum-hf"
    if "forums.developer.nvidia.com" in netloc:
        return "forum-nvidia"
    return None


def extract_json_blob(text, marker):
    i = text.find(marker)
    if i < 0:
        return None
    i = text.find("{", i)
    if i < 0:
        return None
    depth, in_str, esc = 0, False, False
    for j in range(i, len(text)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:j + 1])
                    except json.JSONDecodeError:
                        return None
    return None


# ---- channel fetchers -------------------------------------------------------

def twitter_cli(args_list, timeout=120):
    """Run the authenticated `twitter` CLI; return parsed ok-JSON or None."""
    if not shutil.which("twitter"):
        return None
    try:
        r = subprocess.run(["twitter"] + args_list, capture_output=True,
                           text=True, timeout=timeout)
        i = r.stdout.find("{")
        if i < 0:
            return None
        data = json.loads(r.stdout[i:])
        return data if data.get("ok") else None
    except Exception:
        return None


def fetch_x(url):
    m = re.search(r"/status(?:es)?/(\d+)", url)
    if not m:
        raise SystemExit(f"not an X status URL: {url}")
    tid = m.group(1)
    cli = twitter_cli(["tweet", tid, "--json"])
    if cli:
        posts = cli.get("data") or []
        t = posts[0] if posts else {}
        raw = save_raw(f"x_{tid}.json", {"via": "twitter-cli", "tweet_and_replies": posts})
        author = t.get("author") or {}
        metrics = t.get("metrics") or {}
        return skeleton(
            channel="x",
            discovery_url=f"https://x.com/{author.get('screenName', 'i')}/status/{tid}",
            discovery_quote=(t.get("text") or "")[:1000],
            discovery_date=(t.get("createdAtISO") or "")[:10],
            author=f"@{author.get('screenName', '?')}",
            raw_file=raw,
            canonical_urls=extract_links(" ".join(p.get("text") or "" for p in posts)),
            meta={"likes": metrics.get("likes"), "retweets": metrics.get("retweets"),
                  "views": metrics.get("views"), "replies_fetched": max(0, len(posts) - 1)},
        )
    data = jget(f"https://api.fxtwitter.com/status/{tid}")
    t = data.get("tweet") or {}
    raw = save_raw(f"x_{tid}.json", {"via": "fxtwitter", "response": data})
    author = (t.get("author") or {})
    entry = skeleton(
        channel="x",
        discovery_url=t.get("url") or url,
        discovery_quote=(t.get("text") or "")[:1000],
        discovery_date=(t.get("created_at") or "")[:10],
        author=f"@{author.get('screen_name', '?')}",
        raw_file=raw,
        canonical_urls=extract_links(t.get("text") or ""),
        meta={"likes": t.get("likes"), "retweets": t.get("retweets"),
              "views": t.get("views"), "fxtwitter": f"https://api.fxtwitter.com/status/{tid}"},
    )
    return entry


X_SPEED_HINTS = ("tok/s", "t/s", "tokens per second", "decode", "prefill",
                 "dgx", "spark", "strix", "5090", "5080", "3090", "4090",
                 "5060", "7900", "9700", "b580", "mac", "mlx", "gguf",
                 "ollama", "vram", "llama.cpp", "llama-server", "sglang",
                 "vllm", "bench")


def sweep_x(users, cutoff, max_n):
    """X discovery without search: enumerate user-posts, filter locally."""
    if not shutil.which("twitter"):
        raise SystemExit("twitter CLI not found — X discovery needs it "
                         "(search endpoint 404s; user-posts works)")
    hits = 0
    for user in users:
        data = twitter_cli(["user-posts", user, "-n", str(max_n), "--json"])
        if not data:
            print(f"  {user}: fetch failed")
            continue
        posts = data.get("data") or []
        raw = save_raw(f"xsweep_{user}.json",
                       {"via": f"twitter-cli user-posts -n {max_n}",
                        "user": user, "posts": posts})
        kept = 0
        for t in posts:
            iso = t.get("createdAtISO") or ""
            text = t.get("text") or ""
            low = text.lower()
            if iso[:10] < cutoff or "qwen3" not in low:
                continue
            if not any(k in low for k in X_SPEED_HINTS):
                continue
            author = t.get("author") or {}
            metrics = t.get("metrics") or {}
            durl = f"https://x.com/{author.get('screenName', user)}/status/{t.get('id')}"
            action, i = upsert(skeleton(
                channel="x", discovery_url=durl, discovery_quote=text[:1000],
                discovery_date=iso[:10], author=f"@{author.get('screenName', '?')}",
                raw_file=raw, canonical_urls=extract_links(text),
                meta={"likes": metrics.get("likes"), "views": metrics.get("views"),
                      "via": f"twitter-cli user-posts {user}"}))
            kept += 1
            hits += 1
            print(f"  {action} [{i}] {durl}")
            print(f"     {text[:110]!r}")
        print(f"  {user}: {len(posts)} posts scanned, {kept} qwen hits "
              f"-> {raw}")
        time.sleep(1.0)
    print(f"sweep done: {hits} new/updated candidates")


def fetch_youtube(url):
    m = re.search(r"(?:[?&]v=|youtu\.be/)([\w-]{11})", url)
    if not m:
        raise SystemExit(f"not a YouTube watch URL: {url}")
    vid = m.group(1)
    _, page = http_get(f"https://www.youtube.com/watch?v={vid}")
    pr = extract_json_blob(page, "ytInitialPlayerResponse")
    if not pr:
        raise SystemExit("ytInitialPlayerResponse not found — layout change?")
    vd = pr.get("videoDetails") or {}
    micro = ((pr.get("microformat") or {}).get("playerMicroformatRenderer") or {})
    desc = vd.get("shortDescription") or ""
    payload = {"videoDetails": vd, "microformat": micro}
    tracks = (((pr.get("captions") or {}).get("playerCaptionsTracklistRenderer") or {})
              .get("captionTracks") or [])
    transcript_note = "no caption tracks exposed"
    if tracks:
        try:
            _, xml = http_get(tracks[0]["baseUrl"] + "&fmt=json3")
            body = json.loads(xml)
            text = " ".join(
                "".join(seg.get("utf8", "") for seg in ev.get("segs", []))
                for ev in body.get("events", []) if ev.get("segs"))
            payload["transcript"] = text
            transcript_note = f"auto/manual captions fetched ({len(text)} chars)"
        except Exception as e:
            transcript_note = f"caption fetch failed: {type(e).__name__}"
    raw = save_raw(f"youtube_{vid}.json", payload)
    return skeleton(
        channel="youtube",
        discovery_url=f"https://www.youtube.com/watch?v={vid}",
        discovery_quote=(vd.get("title") or "") + " | " + desc[:600],
        discovery_date=(micro.get("publishDate") or "")[:10],
        author=vd.get("author") or "",
        raw_file=raw,
        canonical_urls=extract_links(desc),
        meta={"views": vd.get("viewCount"), "lengthSeconds": vd.get("lengthSeconds"),
              "transcript": transcript_note},
    )


def fetch_reddit(url):
    m = re.search(r"reddit\.com/r/([\w-]+)/comments/(\w+)", url)
    if not m:
        raise SystemExit(f"not a reddit permalink: {url}")
    sub, tid = m.group(1), m.group(2)
    mirror_sub = f"https://api.pullpush.io/reddit/search/submission/?ids={tid}"
    p, comments = None, []
    try:
        p = (jget(mirror_sub).get("data") or [None])[0]
    except RuntimeError:
        p = None
    if p:
        time.sleep(1.0)
        mirror_com = (f"https://api.pullpush.io/reddit/search/comment/"
                      f"?link_id={tid}&size=100&sort=desc&sort_type=score")
        try:
            comments = jget(mirror_com).get("data") or []
        except (RuntimeError, json.JSONDecodeError):
            comments = []
    else:
        # pullpush gap or block -> arctic-shift secondary mirror (law 10 allows either)
        mirror_sub = f"https://arctic-shift.photon-reddit.com/api/posts/ids?ids={tid}"
        try:
            p = (jget(mirror_sub).get("data") or [None])[0]
        except RuntimeError:
            p = None
        if p:
            time.sleep(1.0)
            mirror_com = ("https://arctic-shift.photon-reddit.com/api/comments/search"
                          f"?link_id={tid}&limit=100")
            try:
                comments = jget(mirror_com).get("data") or []
            except (RuntimeError, json.JSONDecodeError):
                comments = []
    if not p:
        raise SystemExit(f"neither mirror has submission {tid} — say so, do not guess")
    raw = save_raw(f"reddit_{tid}.json",
                   {"mirror_submission": mirror_sub, "submission": p,
                    "comments": comments})
    permalink = "https://www.reddit.com" + (p.get("permalink") or f"/r/{sub}/comments/{tid}")
    created = datetime.fromtimestamp(p.get("created_utc") or 0, timezone.utc).date().isoformat()
    return skeleton(
        channel="reddit",
        discovery_url=permalink,
        discovery_quote=((p.get("title") or "") + " | " + (p.get("selftext") or ""))[:1000],
        discovery_date=created,
        author=p.get("author") or "",
        mirror_url=mirror_sub,
        raw_file=raw,
        canonical_urls=extract_links((p.get("selftext") or "") + " " +
                                     " ".join(c.get("body", "") for c in comments[:20])),
        meta={"subreddit": sub, "score": p.get("score"),
              "num_comments": p.get("num_comments"),
              "comments_fetched": len(comments)},
    )


def gh(args_list, timeout=90):
    if not shutil.which("gh"):
        return None
    try:
        r = subprocess.run(["gh"] + args_list, capture_output=True, text=True,
                           timeout=timeout)
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def parse_gh_url(url):
    m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)/(discussions|issues|pull)/(\d+)", url)
    if not m:
        raise SystemExit(f"not a github discussion/issue URL: {url}")
    return m.group(1), m.group(2), m.group(3), int(m.group(4))


def fetch_github_discussion(url):
    owner, repo, _, num = parse_gh_url(url)
    canon = f"https://github.com/{owner}/{repo}/discussions/{num}"
    q = ('query{repository(owner:"%s",name:"%s"){discussion(number:%d){'
         'title body url createdAt author{login} comments(first:100){nodes{'
         'body author{login} createdAt}}}}}' % (owner, repo, num))
    data = gh(["api", "graphql", "-f", f"query={q}"])
    if data and not data.get("errors"):
        d = data["data"]["repository"]["discussion"]
        raw = save_raw(f"gh-discussion_{owner}_{repo}_{num}.json", d)
        body_text = d.get("body") or ""
        com_text = " ".join(c.get("body") or "" for c in d["comments"]["nodes"])
        return skeleton(
            channel="github-discussion", discovery_url=canon,
            discovery_quote=(d.get("title") or "") + " | " + strip_html(body_text)[:800],
            discovery_date=(d.get("createdAt") or "")[:10],
            author=(d.get("author") or {}).get("login", ""),
            raw_file=raw,
            canonical_urls=extract_links(body_text + " " + com_text),
            meta={"comments_fetched": len(d["comments"]["nodes"]),
                  "repo": f"{owner}/{repo}"},
        )
    # HTML fallback (unauthenticated)
    _, page = http_get(canon)
    text = strip_html(page)
    raw = save_raw(f"gh-discussion_{owner}_{repo}_{num}.html.txt", {"text": text[:200000]})
    return skeleton(
        channel="github-discussion", discovery_url=canon,
        discovery_quote=text[:800], raw_file=raw,
        canonical_urls=extract_links(page),
        meta={"note": "HTML fallback; gh graphql unavailable", "repo": f"{owner}/{repo}"},
    )


def fetch_github_issue(url):
    owner, repo, kind, num = parse_gh_url(url)
    canon = f"https://github.com/{owner}/{repo}/{kind}/{num}"
    issue = gh(["api", f"repos/{owner}/{repo}/issues/{num}"])
    comments = gh(["api", f"repos/{owner}/{repo}/issues/{num}/comments?per_page=100"])
    if issue:
        raw = save_raw(f"gh-issue_{owner}_{repo}_{num}.json",
                       {"issue": issue, "comments": comments or []})
        body = issue.get("body") or ""
        com_text = " ".join(c.get("body") or "" for c in (comments or [])[:30])
        return skeleton(
            channel="github-issue", discovery_url=canon,
            discovery_quote=(issue.get("title") or "") + " | " + body[:800],
            discovery_date=(issue.get("created_at") or "")[:10],
            author=(issue.get("user") or {}).get("login", ""),
            raw_file=raw,
            canonical_urls=extract_links(body + " " + com_text),
            meta={"state": issue.get("state"), "repo": f"{owner}/{repo}"},
        )
    _, page = http_get(canon)
    text = strip_html(page)
    raw = save_raw(f"gh-issue_{owner}_{repo}_{num}.html.txt", {"text": text[:200000]})
    return skeleton(channel="github-issue", discovery_url=canon,
                    discovery_quote=text[:800], raw_file=raw,
                    canonical_urls=extract_links(page),
                    meta={"note": "HTML fallback", "repo": f"{owner}/{repo}"})


def fetch_forum(url):
    base = url.split("?")[0].rstrip("/")
    data = jget(base + ".json")
    netloc = urllib.parse.urlparse(url).netloc
    channel = "forum-hf" if "huggingface" in netloc else "forum-nvidia"
    slug = re.sub(r"\W+", "_", base.rsplit("/", 1)[-1])[:60]
    posts = (data.get("post_stream") or {}).get("posts") or []
    cooked = " ".join(p.get("cooked") or "" for p in posts)
    raw = save_raw(f"{channel}_{data.get('id', slug)}.json", data)
    first = posts[0] if posts else {}
    return skeleton(
        channel=channel, discovery_url=base,
        discovery_quote=(data.get("title") or "") + " | " + strip_html(first.get("cooked"))[:800],
        discovery_date=(first.get("created_at") or "")[:10],
        author=first.get("username") or "",
        raw_file=raw,
        canonical_urls=extract_links(cooked),
        meta={"posts_fetched": len(posts), "posts_count": data.get("posts_count"),
              "views": data.get("views")},
    )


def fetch_one(url):
    ch = detect_channel(url)
    if ch == "x":
        entry = fetch_x(url)
    elif ch == "youtube":
        entry = fetch_youtube(url)
    elif ch == "reddit":
        entry = fetch_reddit(url)
    elif ch == "github-discussion":
        entry = fetch_github_discussion(url)
    elif ch == "github-issue":
        entry = fetch_github_issue(url)
    elif ch in ("forum-hf", "forum-nvidia"):
        entry = fetch_forum(url)
    else:
        raise SystemExit(f"no fetcher for: {url}")
    action, i = upsert(entry)
    print(f"{action} [{i}] {entry['channel']} {entry['discovery_url']}")
    print(f"   raw: {entry['raw_file']}  links: {len(entry['canonical_urls'])}  "
          f"quote: {entry['discovery_quote'][:90]!r}")


# ---- searches (print leads; never write the ledger) -------------------------

def search_reddit(q, subreddit):
    params = {"q": q, "size": "25", "sort": "desc", "sort_type": "score"}
    if subreddit:
        params["subreddit"] = subreddit
    url = "https://api.pullpush.io/reddit/search/submission/?" + urllib.parse.urlencode(params)
    try:
        data = jget(url).get("data") or []
    except RuntimeError as e:
        data = None
        pull_err = e
    if data is None:
        time.sleep(3.0)
        aurl = ("https://arctic-shift.photon-reddit.com/api/posts/search?"
                + urllib.parse.urlencode({"subreddit": subreddit or "LocalLLaMA",
                                          "query": q, "limit": "25"}))
        try:
            data = jget(aurl).get("data") or []
            url = aurl
        except RuntimeError:
            raise SystemExit(
                f"both mirrors refused free-text search right now\n"
                f"  pullpush: {pull_err}\n"
                f"  arctic-shift: timeout/limit\n"
                "fetch-reddit <permalink> (ids lookup) still works on both — find "
                "permalinks via other channels (X posts, GH discussions, forum links, "
                "web search) and fetch them directly.")
    print(f"{len(data)} results (mirror search for {q!r} in r/{subreddit or 'all'})")
    for p in data:
        d = datetime.fromtimestamp(p.get("created_utc") or 0, timezone.utc).date()
        print(f"  {p.get('score', '?'):>5} {d} r/{p.get('subreddit')} "
              f"https://www.reddit.com{p.get('permalink', '')}")
        print(f"        {(p.get('title') or '')[:100]}")


def search_youtube(q):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q)
    _, page = http_get(url)
    ids = re.findall(r'"videoId":"([\w-]{11})"', page)
    seen = []
    for vid in ids:
        if vid not in seen:
            seen.append(vid)
        if len(seen) >= 15:
            break
    for vid in seen:
        m = re.search(r'"videoId":"' + vid + r'".{0,400}?"title":\{"runs":\[\{"text":"(.*?)"\}',
                      page, re.S)
        title = htmlmod.unescape(m.group(1)) if m else "?"
        print(f"  https://www.youtube.com/watch?v={vid}  {title[:90]}")


def search_discussions(keyword, repo, pages):
    if "/" not in repo:
        raise SystemExit("--repo must be owner/name")
    owner, name = repo.split("/", 1)
    cursor, found, scanned = "null", [], 0
    for page in range(pages):
        q = ('query{repository(owner:"%s",name:"%s"){discussions(first:100,after:%s,'
             'orderBy:{field:CREATED_AT,direction:DESC}){totalCount pageInfo{hasNextPage '
             'endCursor}nodes{number title url createdAt body}}}}'
             % (owner, name, cursor))
        data = gh(["api", "graphql", "-f", f"query={q}"])
        if not data or data.get("errors"):
            raise SystemExit("gh graphql failed (auth? rate?) — for older discussions "
                             "fetch known numbers directly with `fetch <url>`")
        disc = data["data"]["repository"]["discussions"]
        nodes = disc["nodes"]
        scanned += len(nodes)
        kw = keyword.lower()
        for n in nodes:
            if kw in (n.get("title") or "").lower() or kw in (n.get("body") or "").lower():
                found.append(n)
        pi = disc["pageInfo"]
        if not pi["hasNextPage"]:
            break
        cursor = '"%s"' % pi["endCursor"]
        time.sleep(0.5)
    print(f"{len(found)} matches for {keyword!r} in {repo} discussions "
          f"(scanned {scanned}, newest-first)")
    for n in found:
        print(f"  #{n['number']} {(n.get('createdAt') or '')[:10]} {n['title'][:80]}")
        print(f"    {n['url']}")


def search_forum(q, site):
    base = ("https://discuss.huggingface.co" if site == "hf"
            else "https://forums.developer.nvidia.com")
    data = jget(base + "/search.json?q=" + urllib.parse.quote(q))
    topics = data.get("topics") or []
    print(f"{len(topics)} topics on {site} for {q!r}")
    for t in topics[:20]:
        print(f"  {base}/t/{t.get('slug')}/{t.get('id')}  "
              f"{(t.get('title') or '')[:90]}  ({t.get('posts_count')} posts)")


# ---- ledger management ------------------------------------------------------

def add_file(path):
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    items = payload if isinstance(payload, list) else [payload]
    for it in items:
        if not it.get("discovery_url"):
            raise SystemExit("every candidate needs a discovery_url")
        it.setdefault("state", "extracted")
        action, i = upsert(it)
        print(f"{action} [{i}] {it['discovery_url']}")


def list_ledger():
    rows = load_ledger()
    order = {"raw": 0, "extracted": 1, "vetted": 2, "merged": 3, "dropped": 4}
    rows.sort(key=lambda r: (order.get(r.get("state"), 9), r.get("channel", "")))
    for i, r in enumerate(rows):
        meas = len(r.get("measurements") or [])
        print(f"  [{i:2}] {r.get('state', '?'):<9} {r.get('channel', '?'):<18} "
              f"{(r.get('model') or '-')[:26]:<26} {meas}m  {r.get('discovery_url', '')[:70]}")
    print(f"{len(rows)} ledger entries")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch"); p.add_argument("urls", nargs="+")
    p = sub.add_parser("fetch-urls"); p.add_argument("file")
    p = sub.add_parser("search"); p.add_argument("channel"); p.add_argument("query")
    p.add_argument("--subreddit", default=""); p.add_argument("--repo", default="")
    p.add_argument("--site", default="hf"); p.add_argument("--pages", type=int, default=3)
    p = sub.add_parser("sweep-x"); p.add_argument("users", nargs="+")
    p.add_argument("--cutoff", default="2026-06-01"); p.add_argument("--max", type=int, default=50)
    p = sub.add_parser("add"); p.add_argument("file")
    sub.add_parser("list")
    args = ap.parse_args()

    if args.cmd == "fetch":
        for u in args.urls:
            try:
                fetch_one(u)
            except (urllib.error.URLError, RuntimeError, SystemExit) as e:
                print(f"FAILED {u}: {e}", file=sys.stderr)
    elif args.cmd == "fetch-urls":
        with open(args.file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        fetch_one(line)
                    except (urllib.error.URLError, RuntimeError, SystemExit) as e:
                        print(f"FAILED {line}: {e}", file=sys.stderr)
    elif args.cmd == "search":
        if args.channel == "reddit":
            search_reddit(args.query, args.subreddit or "LocalLLaMA")
        elif args.channel == "youtube":
            search_youtube(args.query)
        elif args.channel == "discussions":
            search_discussions(args.query, args.repo or "ggml-org/llama.cpp", args.pages)
        elif args.channel == "forum":
            search_forum(args.query, args.site)
        else:
            raise SystemExit(f"unknown search channel: {args.channel}")
    elif args.cmd == "sweep-x":
        sweep_x(args.users, args.cutoff, args.max)
    elif args.cmd == "add":
        add_file(args.file)
    elif args.cmd == "list":
        list_ledger()
    return 0


if __name__ == "__main__":
    sys.exit(main())
