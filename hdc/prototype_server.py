"""AIOS Integrated Prototype server.

Serves the AIOS UI and the prototype backend for Foundation Data, accounts,
AI Agent Registry, provider adapters and persisted runtime records.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hdc.agent_store import (
    chat,
    ensure_seeded,
    list_agents,
    list_providers,
    recent_runs,
    save_agent,
    save_provider,
)
from hdc.people_store import (
    authenticate,
    database_info,
    import_workbook,
    list_accounts,
    list_data_records,
    list_imports,
    list_people,
    save_account,
    save_data_record,
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
        q = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/api/health":
            return self._json(200, {"status":"ok","database":database_info(),"providers":list_providers()})
        if parsed.path == "/api/admin/stats":
            return self._json(200, stats())
        if parsed.path == "/api/admin/people":
            return self._json(200, {"items": list_people(
                kind=(q.get("kind") or [None])[0],
                query=(q.get("q") or [None])[0],
                limit=int((q.get("limit") or [100])[0]),
            )})
        if parsed.path == "/api/admin/accounts":
            return self._json(200, {"items": list_accounts()})
        if parsed.path == "/api/admin/imports":
            return self._json(200, {"items": list_imports(int((q.get("limit") or [100])[0]))})
        if parsed.path == "/api/data/records":
            return self._json(200, {"items": list_data_records(int((q.get("limit") or [100])[0]))})
        if parsed.path == "/api/ai/providers":
            return self._json(200, {"items": list_providers()})
        if parsed.path == "/api/ai/agents":
            return self._json(200, {"items": list_agents((q.get("category") or [None])[0], (q.get("domain") or [None])[0])})
        if parsed.path == "/api/ai/runs":
            return self._json(200, {"items": recent_runs(int((q.get("limit") or [100])[0]))})
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
        if self.path in {"/api/ai", "/api/ai/chat"}:
            try:
                return self._json(200, chat(str(body.get("agent_id") or "personal-ai"), str(body.get("prompt") or ""), body.get("context") or {}))
            except ValueError as exc:
                return self._json(400, {"error":"invalid_agent_request","detail":str(exc)})
            except RuntimeError as exc:
                return self._json(502, {"error":"provider_error","detail":str(exc)})
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
        if self.path == "/api/admin/agents":
            try:
                return self._json(200, save_agent(body))
            except ValueError as exc:
                return self._json(400, {"error":"invalid_agent","detail":str(exc)})
        if self.path == "/api/admin/providers":
            try:
                return self._json(200, save_provider(body))
            except ValueError as exc:
                return self._json(400, {"error":"invalid_provider","detail":str(exc)})
        if self.path == "/api/data/records":
            try:
                return self._json(200, save_data_record(body))
            except ValueError as exc:
                return self._json(400, {"error":"invalid_record","detail":str(exc)})
        self.send_error(404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            raise ValueError(str(exc)) from exc

    def _json(self, code, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    parser = argparse.ArgumentParser(description="Run the AIOS Integrated Prototype server")
    parser.add_argument("--host", default=os.getenv("AIOS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AIOS_PORT", "8000")))
    args = parser.parse_args()
    ensure_seeded()
    print(f"AIOS prototype: http://{args.host}:{args.port}")
    print(f"Runtime database: {database_info()['path']}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
