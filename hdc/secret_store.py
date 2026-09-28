"""Server-side secret persistence for the AIOS prototype.

Secrets live only under runtime/ (gitignored) and are never returned by APIs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS_FILE = ROOT / "runtime" / "provider-secrets.json"


def _read() -> dict[str, str]:
    if not SECRETS_FILE.exists():
        return {}
    try:
        data = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items() if v}
    except (json.JSONDecodeError, OSError):
        return {}


def get_secret(name: str | None) -> str | None:
    if not name:
        return None
    return os.getenv(name) or _read().get(name)


def set_secret(name: str, value: str) -> None:
    name = str(name or "").strip()
    value = str(value or "").strip()
    if not name:
        raise ValueError("secret_name_required")
    data = _read()
    if value:
        data[name] = value
    else:
        data.pop(name, None)
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRETS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(SECRETS_FILE, 0o600)
    except OSError:
        pass


def has_secret(name: str | None) -> bool:
    return bool(get_secret(name))
