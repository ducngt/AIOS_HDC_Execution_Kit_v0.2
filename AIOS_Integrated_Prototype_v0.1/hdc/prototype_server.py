"""AIOS Integrated Prototype server.

Serves the prototype UI and optionally proxies AI requests to an
OpenAI-compatible provider without exposing the provider API key to browsers.
"""
from __future__ import annotations
import json, os, urllib.request, urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI), **kwargs)

    def do_POST(self):
        if self.path != "/api/ai":
            self.send_error(404); return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error":"invalid_json"}); return
        key = os.getenv("AIOS_AI_API_KEY")
        base = os.getenv("AIOS_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("AIOS_AI_MODEL", "gpt-5.6")
        if not key:
            self._json(503, {"error":"provider_not_configured"}); return
        context = body.get("context", {})
        prompt = str(body.get("prompt", ""))[:12000]
        payload = {
            "model": model,
            "messages": [
                {"role":"system","content":"You are the AIOS contextual assistant. Treat recommendations as non-authoritative. Never claim institutional approval. Context: " + json.dumps(context, ensure_ascii=False)},
                {"role":"user","content":prompt},
            ],
        }
        req = urllib.request.Request(
            base + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization":"Bearer " + key, "Content-Type":"application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            text = data["choices"][0]["message"]["content"]
            self._json(200, {"text":text, "provider":"configured"})
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            self._json(502, {"error":"provider_error", "detail":str(exc)})

    def _json(self, code, data):
        raw=json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)


def main():
    host=os.getenv("AIOS_HOST","127.0.0.1"); port=int(os.getenv("AIOS_PORT","8000"))
    print(f"AIOS prototype: http://{host}:{port}")
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__ == "__main__": main()
