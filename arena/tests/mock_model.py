#!/usr/bin/env python3
"""arena/tests/mock_model.py — OpenAI-compatible stand-in for backend tests.

Serves /v1/models and streams a fixed reply containing a runnable fenced
python snippet on /v1/chat/completions (SSE + usage event), so the arena
orchestrator, SSE stream, blind slots, checks (incl. sandboxed exec),
voting, grading and scoreboard can be exercised WITHOUT booting a real
model. Listens on 127.0.0.1:8899. Tests should run arena with
ARENA_RESULTS=<scratch dir> and auto:false so no GPU work happens and
real saved runs can never be touched.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8899
TOKENS = ["```python", "\n", "print(\"hi\")", "\n", "```"]


def sse_body():
    out = []
    for t in TOKENS:
        out.append("data: " + json.dumps({"choices": [{"delta": {"content": t}}]}) + "\n\n")
    out.append("data: " + json.dumps({
        "choices": [{"delta": {}, "finish_reason": "stop"}],
        "usage": {"completion_tokens": len(TOKENS)}}) + "\n\n")
    out.append("data: [DONE]\n\n")
    return "".join(out)


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            body = json.dumps({"data": [{"id": "mock"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        self.rfile.read(n)
        if self.path.endswith("/chat/completions"):
            body = sse_body().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
