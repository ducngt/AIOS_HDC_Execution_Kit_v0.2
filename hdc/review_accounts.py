"""Provision historical AIOS review identities as real backend accounts.

This is a local operator command; filesystem access to the database is required.
Never resets existing users or prints stored passwords.
"""
from __future__ import annotations

import secrets

from hdc.people_store import connect, ensure_schema, save_account

REVIEW_ACCOUNTS = (
    ('human@aios.demo', 'Nguyễn Minh An', 'Giảng viên', 'Teaching & Research scope'),
    ('leader@aios.demo', 'Trần Thu Hà', 'Hiệu trưởng', 'Institutional scope'),
    ('admin@aios.demo', 'Lê Quốc Nam', 'Platform Admin', 'Platform operations scope'),
)


def provision() -> list[tuple[str, str | None]]:
    """Create missing review identities on the current AIOS_DB_PATH only."""
    with connect() as con:
        ensure_schema(con)
    results = []
    for username, display_name, role_code, scope in REVIEW_ACCOUNTS:
        with connect() as con:
            exists = con.execute('SELECT 1 FROM accounts WHERE lower(username)=lower(?) OR lower(email)=lower(?)',
                                 (username, username)).fetchone()
        if exists:
            results.append((username, None))
            continue
        password = secrets.token_urlsafe(18)
        save_account({'username': username, 'email': username, 'display_name': display_name,
                      'temporary_password': password,
                      'roles': [{'role_code': role_code, 'scope': scope, 'active': True}]})
        results.append((username, password))
    return results


def main():
    print('Database:', __import__('hdc.people_store', fromlist=['db_path']).db_path().resolve())
    for username, password in provision():
        print(f'{username} | {password or "ALREADY EXISTS: password unchanged"}')
    print('New passwords are temporary: change each after first login. Keep these credentials private.')


if __name__ == '__main__':
    main()
