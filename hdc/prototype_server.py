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
    provider_diagnostic,
    save_agent,
    save_provider,
    save_provider_secret,
)
from hdc.auth import (
    current_user,
    is_admin,
    issue_session,
    revoke_session,
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
        allowed = os.getenv("AIOS_CORS_ORIGIN", "*")
        if origin and (allowed == "*" or origin in {x.strip() for x in allowed.split(",")}):
            self.send_header("Access-Control-Allow-Origin", origin if allowed != "*" else "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def _origin_allowed(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        allowed = os.getenv("AIOS_CORS_ORIGIN", "*")
        if allowed == "*":
            return True
        allowed_origins = {x.strip() for x in allowed.split(",") if x.strip()}
        # Same-origin requests to the runtime itself are permitted.
        host = self.headers.get("Host")
        if host and origin in {"http://" + host, "https://" + host}:
            return True
        return origin in allowed_origins

    def _bearer_token(self):
        value = self.headers.get("Authorization", "")
        if not value.startswith("Bearer "):
            return ""
        return value[7:].strip()

    def _user(self):
        return current_user(self._bearer_token())

    def _require_authenticated(self):
        user = self._user()
        if not user:
            self._json(401, {"error": "authentication_required"})
            return None
        return user

    def _require_admin(self):
        user = self._require_authenticated()
        if not user:
            return None
        if user.get("must_change_password"):
            self._json(403, {"error": "password_change_required"})
            return None
        if not is_admin(user):
            self._json(403, {"error": "admin_required"})
            return None
        return user

    def do_OPTIONS(self):
        if not self._origin_allowed():
            return self._json(403, {"error": "origin_not_allowed"})
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if not self._origin_allowed():
            return self._json(403, {"error": "origin_not_allowed"})
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)

        if parsed.path.startswith("/api/admin/"):
            if not self._require_admin():
                return

        if parsed.path in {"/api/ai/providers", "/api/ai/agents",
                           "/api/ai/runs", "/api/data/records"}:
            if not self._require_admin():
                return
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
        if not self._origin_allowed():
            return self._json(403, {"error": "origin_not_allowed"})
        try:
            body = self._read_json()
        except ValueError as exc:
            return self._json(400, {"error": "invalid_json", "detail": str(exc)})

        if self.path == "/api/auth/login":
            user = authenticate(
                str(body.get("username") or ""),
                str(body.get("password") or ""),
            )
            if not user:
                return self._json(401, {"error": "invalid_credentials"})
            token = issue_session(user["account_id"])
            return self._json(200, {"user": user, "token": token})

        if self.path == "/api/auth/logout":
            token = self._bearer_token()
            if not current_user(token):
                return self._json(401, {"error": "authentication_required"})
            revoke_session(token)
            return self._json(200, {"ok": True})

        if self.path == "/api/auth/change-password":
            user = self._require_authenticated()
            if not user:
                return
            current_password = str(body.get("current_password") or "")
            new_password = str(body.get("new_password") or "")
            if not authenticate(user["username"], current_password):
                return self._json(400, {"error": "invalid_current_password"})
            if len(new_password) < 12:
                return self._json(400, {"error": "password_too_short"})
            from hdc.people_store import connect, set_password
            with connect() as con:
                set_password(
                    con,
                    user["account_id"],
                    new_password,
                    must_change_password=False,
                )
            revoke_session(self._bearer_token())
            return self._json(200, {"ok": True})

        if self.path.startswith("/api/admin/"):
            if not self._require_admin():
                return

        if self.path in {"/api/ai", "/api/ai/chat", "/api/data/records"}:
            if not self._require_admin():
                return

        if self.path in {"/api/ai", "/api/ai/chat"}:
            try:
                user = self._user()
                if not user:
                    return self._json(
                        401,
                        {"error": "authentication_required"},
                    )

                client_context = body.get("context") or {}

                # Security boundary:
                # identity/role/authority used for execution and audit are
                # derived from the authenticated server-side session, never
                # trusted from browser-supplied context.
                roles = [
                    r for r in user.get("roles", [])
                    if r.get("active")
                ]
                role_codes = [
                    str(r.get("role_code") or "")
                    for r in roles
                    if r.get("role_code")
                ]
                scopes = [
                    str(r.get("scope") or "")
                    for r in roles
                    if r.get("scope")
                ]

                trusted_context = dict(client_context)
                trusted_context["identity"] = user["account_id"]
                trusted_context["role"] = ",".join(role_codes)
                trusted_context["authority"] = ",".join(scopes)
                trusted_context["authenticated_username"] = user.get("username")

                return self._json(
                    200,
                    chat(
                        str(body.get("agent_id") or "personal-ai"),
                        str(body.get("prompt") or ""),
                        trusted_context,
                    ),
                )
            except ValueError as exc:
                return self._json(
                    400,
                    {"error": "invalid_agent_request", "detail": str(exc)},
                )
            except RuntimeError as exc:
                return self._json(
                    502,
                    {"error": "provider_error", "detail": str(exc)},
                )
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
