#!/usr/bin/env python3
"""arena/tests/slow_model.py — slow streaming OpenAI-compatible stand-in.

Same contract as mock_model.py but emits ~120 content events 150 ms apart
(~18 s of live generation, close-delimited so the client can hang up early),
so the arena stop flow (POST /api/stop mid-stream, partial-save, run-lock
release) can be tested deterministically without a GPU. Listens on
127.0.0.1:8897.
"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8897
NCHUNKS = 120
PAUSE_S = 0.15


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            body = json.dumps({"data": [{"id": "slow-mock"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        self.rfile.read(n)
        if not self.path.endswith("/chat/completions"):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for i in range(NCHUNKS):
                ev = ("data: " + json.dumps(
                    {"choices": [{"delta": {"content": "chunk%d " % i}}]})
                      + "\n\n").encode()
                self.wfile.write(ev)
                self.wfile.flush()
                time.sleep(PAUSE_S)
            fin = ("data: " + json.dumps({
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": NCHUNKS}}) + "\n\ndata: [DONE]\n\n").encode()
            self.wfile.write(fin)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
