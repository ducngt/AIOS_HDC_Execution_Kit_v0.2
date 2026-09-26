"""AIOS Integrated Prototype server.

Serves the UI, proxies AI requests, and provides prototype Admin APIs for
Foundation Identity & People data. Institutional workbook uploads are parsed
at runtime and persisted to a local SQLite database; source workbooks are not
stored by the application.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hdc.people_store import (
    authenticate,
    import_workbook,
    list_accounts,
    list_people,
    save_account,
    stats,
    toggle_account,
)

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/admin/stats":
            return self._json(200, stats())
        if parsed.path == "/api/admin/people":
            q = urllib.parse.parse_qs(parsed.query)
            return self._json(200, {"items": list_people(
                kind=(q.get("kind") or [None])[0],
                query=(q.get("q") or [None])[0],
                limit=int((q.get("limit") or [100])[0]),
            )})
        if parsed.path == "/api/admin/accounts":
            return self._json(200, {"items": list_accounts()})
        return super().do_GET()

    def do_POST(self):
        try:
            body = self._read_json()
        except ValueError as exc:
            return self._json(400, {"error": "invalid_json", "detail": str(exc)})

        if self.path == "/api/auth/login":
            user = authenticate(str(body.get("username") or ""), str(body.get("password") or ""))
            if not user:
                return self._json(401, {"error":"invalid_credentials"})
            return self._json(200, {"user": user})
        if self.path == "/api/ai":
            return self._ai(body)
        if self.path == "/api/admin/import":
            filename = str(body.get("filename") or "upload.xlsx")
            data = str(body.get("data_base64") or "")
            if not data:
                return self._json(400, {"error": "missing_file"})
            try:
                report = import_workbook(filename, data)
                return self._json(200 if not report["error_count"] else 422, report)
            except Exception as exc:
                return self._json(422, {"error": "import_failed", "detail": str(exc)})
        if self.path == "/api/admin/accounts":
            try:
                return self._json(200, save_account(body))
            except (ValueError, TypeError) as exc:
                return self._json(400, {"error": "invalid_account", "detail": str(exc)})
        if self.path == "/api/admin/account-status":
            try:
                return self._json(200, toggle_account(str(body.get("account_id")), str(body.get("status"))))
            except ValueError as exc:
                return self._json(400, {"error": "invalid_status", "detail": str(exc)})
        self.send_error(404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            raise ValueError(str(exc)) from exc

    def _ai(self, body):
        key = os.getenv("AIOS_AI_API_KEY")
        base = os.getenv("AIOS_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("AIOS_AI_MODEL", "gpt-5.6")
        if not key:
            return self._json(503, {"error": "provider_not_configured"})
        context = body.get("context", {})
        prompt = str(body.get("prompt", ""))[:12000]
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are the AIOS contextual assistant. Treat recommendations as non-authoritative. Never claim institutional approval. Context: " + json.dumps(context, ensure_ascii=False)},
                {"role": "user", "content": prompt},
            ],
        }
        req = urllib.request.Request(
            base + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            return self._json(200, {"text": data["choices"][0]["message"]["content"], "provider": "configured"})
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            return self._json(502, {"error": "provider_error", "detail": str(exc)})

    def _json(self, code, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    host = os.getenv("AIOS_HOST", "127.0.0.1")
    port = int(os.getenv("AIOS_PORT", "8000"))
    print(f"AIOS prototype: http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
