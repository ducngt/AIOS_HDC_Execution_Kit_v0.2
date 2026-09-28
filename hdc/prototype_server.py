"""AIOS Integrated Prototype server.

Serves the AIOS UI and the prototype backend for Foundation Data, accounts,
AI Agent Registry, provider adapters and persisted runtime records.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hdc.auth import current_user, is_admin, issue_session, revoke_session
from hdc.agent_store import (
    chat,
    get_agent,
    ensure_seeded,
    list_agents,
    list_providers,
    recent_runs,
    provider_diagnostic,
    save_agent,
    save_provider,
    save_provider_secret,
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
LOGIN_ATTEMPTS = defaultdict(list)


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env without overriding real env vars."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"\'")
        if key and key not in os.environ:
            os.environ[key] = value



class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI), **kwargs)

    def end_headers(self):
        origin = self.headers.get("Origin")
        allowed = {x.strip() for x in os.getenv("AIOS_CORS_ORIGIN", "").split(",") if x.strip()}
        if origin and origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        origin = self.headers.get("Origin")
        allowed = {x.strip() for x in os.getenv("AIOS_CORS_ORIGIN", "").split(",") if x.strip()}
        if origin and origin not in allowed:
            return self._json(403, {"error": "origin_forbidden"})
        self.send_response(204)
        self.end_headers()

    def _token(self):
        header = self.headers.get("Authorization", "")
        return header[7:] if header.startswith("Bearer ") else ""

    def _authorize(self, path):
        origin = self.headers.get("Origin")
        allowed = {x.strip() for x in os.getenv("AIOS_CORS_ORIGIN", "").split(",") if x.strip()}
        if origin and origin not in allowed:
            self._json(403, {"error": "origin_forbidden"})
            return False
        user = current_user(self._token())
        if not user:
            self._json(401, {"error": "authentication_required"})
            return False
        if user['must_change_password'] and path not in {'/api/auth/change-password', '/api/auth/logout'}:
            self._json(403, {"error": "password_change_required"})
            return False
        if (path.startswith('/api/admin/') or path in {'/api/ai/providers', '/api/ai/runs', '/api/data/records'}) and not is_admin(user):
            self._json(403, {"error": "admin_required"})
            return False
        self.actor = user
        return True

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        if parsed.path.startswith("/api/") and parsed.path != "/api/health" and not self._authorize(parsed.path):
            return
        if parsed.path == "/api/health":
            return self._json(200, {"status": "ok"})
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
        if self.path.startswith("/api/") and self.path != "/api/auth/login" and not self._authorize(self.path):
            return
        try:
            body = self._read_json()
        except ValueError as exc:
            return self._json(400, {"error": "invalid_json", "detail": str(exc)})

        if self.path == "/api/auth/login":
            origin = self.headers.get("Origin")
            allowed = {x.strip() for x in os.getenv("AIOS_CORS_ORIGIN", "").split(",") if x.strip()}
            if origin and origin not in allowed:
                return self._json(403, {"error": "origin_forbidden"})
            ip = self.client_address[0]
            now = time.monotonic()
            LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS[ip] if now - t < 300]
            if len(LOGIN_ATTEMPTS[ip]) >= 10:
                return self._json(429, {"error": "too_many_attempts"})
            user = authenticate(str(body.get("username") or ""), str(body.get("password") or ""))
            if not user:
                LOGIN_ATTEMPTS[ip].append(now)
                return self._json(401, {"error":"invalid_credentials"})
            LOGIN_ATTEMPTS.pop(ip, None)
            return self._json(200, {"user": user, "token": issue_session(user['account_id'])})
        if self.path == "/api/auth/logout":
            revoke_session(self._token())
            return self._json(200, {"ok": True})
        if self.path == "/api/auth/change-password":
            from hdc.people_store import change_password
            try:
                change_password(self.actor['account_id'], str(body.get('current_password') or ''), str(body.get('new_password') or ''))
                revoke_session(self._token())
                return self._json(200, {"ok": True})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
        if self.path in {"/api/ai", "/api/ai/chat"}:
            try:
                agent_id = str(body.get("agent_id") or "personal-ai")
                agent = get_agent(agent_id)
                if agent and agent.get('category') in {'admin', 'institutional', 'data'} and not is_admin(self.actor):
                    return self._json(403, {"error": "agent_forbidden"})
                context = {"identity": self.actor['account_id'], "role": ', '.join(r['role_code'] for r in self.actor['roles']), "authority": 'server-verified role context'}
                return self._json(200, chat(agent_id, str(body.get("prompt") or ""), context))
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
        if self.path == "/api/admin/provider-secret":
            try:
                provider_id = str(body.get("provider_id") or "")
                api_key = str(body.get("api_key") or "")
                if not api_key:
                    return self._json(400, {"error":"missing_api_key"})
                return self._json(200, save_provider_secret(provider_id, api_key))
            except ValueError as exc:
                return self._json(400, {"error":"invalid_provider_secret","detail":str(exc)})
        if self.path == "/api/admin/provider-test":
            try:
                return self._json(200, provider_diagnostic(str(body.get("provider_id") or ""), str(body.get("prompt") or "Reply only with OK")))
            except ValueError as exc:
                return self._json(400, {"error":"invalid_provider_test","detail":str(exc)})
        if self.path == "/api/data/records":
            try:
                return self._json(200, save_data_record(body))
            except ValueError as exc:
                return self._json(400, {"error":"invalid_record","detail":str(exc)})
        self.send_error(404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 12 * 1024 * 1024:
            raise ValueError("request_too_large")
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
    _load_env_file(ROOT / ".env")
    ensure_seeded()
    print(f"AIOS prototype: http://{args.host}:{args.port}")
    print(f"Runtime database: {database_info()['path']}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
