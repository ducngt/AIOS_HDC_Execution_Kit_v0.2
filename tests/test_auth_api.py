"""Authorization boundaries exercised over actual HTTP requests."""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from hdc.auth import bootstrap_admin, current_user
from hdc.people_store import save_account
from hdc.prototype_server import Handler


class AuthAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = patch.dict(os.environ, {'AIOS_DB_PATH': str(Path(self.tmp.name) / 'db.sqlite3'), 'AIOS_CORS_ORIGIN': 'https://review.example'})
        env.start()
        self.addCleanup(env.stop)
        bootstrap_admin('firstadmin', 'StrongPassword123!')
        save_account({'username': 'lecturer', 'display_name': 'Lecturer', 'temporary_password': 'StrongPassword234!', 'roles': [{'role_code': 'LECTURER'}]})
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def call(self, path, token='', payload=None, origin=None):
        headers = {}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if origin:
            headers['Origin'] = origin
        data = None if payload is None else json.dumps(payload).encode()
        if data is not None:
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(self.base + path, headers=headers, data=data)
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def login(self, username, password):
        return self.call('/api/auth/login', payload={'username': username, 'password': password})

    def test_requires_auth_and_enforces_admin_and_password_change(self):
        self.assertEqual(self.call('/api/admin/provider-secret', payload={'provider_id': 'openai', 'api_key': 'SECRET'})[0], 401)
        status, result = self.login('firstadmin', 'StrongPassword123!')
        self.assertEqual(status, 200)
        admin = result['token']
        self.assertEqual(self.call('/api/admin/accounts', admin)[0], 403)
        self.assertEqual(self.call('/api/auth/change-password', admin, {'current_password': 'StrongPassword123!', 'new_password': 'NewPassword123!'} )[0], 200)
        self.assertEqual(self.call('/api/admin/accounts', admin)[0], 401)
        admin = self.login('firstadmin', 'NewPassword123!')[1]['token']
        self.assertEqual(self.call('/api/admin/accounts', admin)[0], 200)
        lecturer = self.login('lecturer', 'StrongPassword234!')[1]['token']
        self.call('/api/auth/change-password', lecturer, {'current_password': 'StrongPassword234!', 'new_password': 'AnotherPassword234!'})
        lecturer = self.login('lecturer', 'AnotherPassword234!')[1]['token']
        for path in ('/api/admin/accounts', '/api/ai/providers', '/api/data/records'):
            self.assertEqual(self.call(path, lecturer)[0], 403)
        self.assertEqual(self.call('/api/admin/provider-secret', lecturer, {'provider_id': 'openai', 'api_key': 'SECRET'})[0], 403)
        self.assertEqual(self.call('/api/admin/accounts', admin, origin='https://evil.example')[0], 403)
        self.assertEqual(self.call('/api/admin/accounts', admin, origin='https://review.example')[0], 200)
        self.assertEqual(self.call('/api/auth/logout', admin, {})[0], 200)
        self.assertEqual(self.call('/api/admin/accounts', admin)[0], 401)


if __name__ == '__main__':
    unittest.main()
