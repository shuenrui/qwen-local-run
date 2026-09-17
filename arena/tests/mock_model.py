#!/usr/bin/env python3
"""arena/tests/mock_model.py — OpenAI-compatible stand-in for backend tests.

Serves /v1/models and streams a fixed short reply on
/v1/chat/completions (SSE with a usage event), so the arena orchestrator,
SSE stream, blind slots, voting and scoreboard can be exercised WITHOUT
booting a real model. Listens on 127.0.0.1:8899; pair it with throwaway
profiles pointing at that port and POST /api/run with auto:false.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8899
TOKENS = ["Hel", "lo", " from", " the", " little", " engine", "."]


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
