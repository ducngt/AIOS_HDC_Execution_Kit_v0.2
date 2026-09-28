"""Opaque bearer sessions and explicit first-administrator bootstrap."""
from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import time

from hdc.people_store import connect, ensure_schema, save_account

SESSION_SECONDS = 8 * 60 * 60


def ensure_auth_schema():
    with connect() as con:
        ensure_schema(con)
        con.execute('''CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
        )''')
        con.execute('CREATE INDEX IF NOT EXISTS auth_sessions_expiry ON auth_sessions(expires_at)')


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(account_id):
    ensure_auth_schema()
    token = secrets.token_urlsafe(48)
    with connect() as con:
        con.execute('DELETE FROM auth_sessions WHERE expires_at <= ?', (int(time.time()),))
        con.execute('INSERT INTO auth_sessions VALUES (?,?,?)', (_digest(token), account_id, int(time.time()) + SESSION_SECONDS))
    return token


def revoke_session(token):
    if token:
        with connect() as con:
            con.execute('DELETE FROM auth_sessions WHERE token_hash=?', (_digest(token),))


def current_user(token):
    if not token:
        return None
    ensure_auth_schema()
    with connect() as con:
        row = con.execute('''SELECT a.account_id,a.username,a.display_name,a.email,a.status,a.must_change_password
            FROM auth_sessions s JOIN accounts a ON a.account_id=s.account_id
            WHERE s.token_hash=? AND s.expires_at>? AND a.status='active' ''',
            (_digest(token), int(time.time()))).fetchone()
        if not row:
            return None
        result = dict(row)
        result['roles'] = [dict(r) for r in con.execute('''SELECT role_code,scope,active FROM role_assignments
            WHERE account_id=? AND active=1''', (row['account_id'],))]
        return result


def is_admin(user):
    return bool(user and any(r['role_code'] == 'Platform Admin' for r in user['roles']))


def bootstrap_admin(username, password):
    ensure_auth_schema()
    with connect() as con:
        if con.execute('SELECT 1 FROM accounts LIMIT 1').fetchone():
            raise ValueError('Bootstrap is available only before the first account exists')
    if len(password) < 12:
        raise ValueError('Bootstrap password must contain at least 12 characters')
    return save_account({'username': username, 'display_name': username,
                         'temporary_password': password,
                         'roles': [{'role_code': 'Platform Admin', 'scope': 'platform', 'active': True}]})


def main():
    parser = argparse.ArgumentParser(description='Create the initial platform administrator once')
    parser.add_argument('username')
    args = parser.parse_args()
    import getpass
    password = getpass.getpass('Initial password (12+ characters): ')
    bootstrap_admin(args.username, password)
    print('Initial Platform Admin created. Change the temporary password before public deployment.')


if __name__ == '__main__':
    main()
