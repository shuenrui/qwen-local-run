#!/usr/bin/env python3
"""Run the publish gate: validate, check links, build, and verify in Chromium."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread


ROOT = Path(__file__).resolve().parent


def run(label, *command):
    print(f"== {label} ==", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    run("validate", sys.executable, "validate.py")

    run("link rot", sys.executable, "check_links.py", "--quiet")
    print("all source URLs reachable", flush=True)

    run("build", sys.executable, "build.py")

    candidates = [
        Path("/tmp/pwenv/bin/python"),
        ROOT / "tools/.pwenv/bin/python",
    ]
    playwright_python = next(
        (path for path in candidates if path.is_file() and os.access(path, os.X_OK)),
        None,
    )
    if playwright_python is None:
        print(
            "browser verification requires tools/install_verify_env.sh",
            file=sys.stderr,
        )
        return 1

    handler = partial(SimpleHTTPRequestHandler, directory=ROOT / "site")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        run(
            "browser verify (local serve)",
            str(playwright_python),
            "verify_browser.py",
            f"http://127.0.0.1:{port}/",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    print("== done ==", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
