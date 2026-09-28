"""Real HTTP login and persistence for the historical admin identity."""
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

from hdc.agent_store import ensure_seeded, recent_runs
from hdc.prototype_server import Handler
from hdc.review_accounts import provision


class RealReviewFlowTests(unittest.TestCase):
    def test_login_admin_provider_registry_and_ai_run(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'AIOS_DB_PATH': str(Path(tmp) / 'db.sqlite3'), 'AIOS_CORS_ORIGIN': 'https://ducngt.github.io', 'OPENAI_API_KEY': 'test-only'}):
            credentials = dict(provision())
            ensure_seeded()
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            origin = 'https://ducngt.github.io'
            base = f'http://127.0.0.1:{server.server_port}'

            def request(path, payload=None, token=''):
                headers = {'Origin': origin}
                if token:
                    headers['Authorization'] = 'Bearer ' + token
                data = json.dumps(payload).encode() if payload is not None else None
                if data is not None:
                    headers['Content-Type'] = 'application/json'
                try:
                    response = urllib.request.urlopen(urllib.request.Request(base + path, headers=headers, data=data))
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    return response.status, json.load(response)

            try:
                self.assertEqual(request('/api/admin/stats')[0], 401)
                status, login = request('/api/auth/login', {'username': 'admin@aios.demo', 'password': credentials['admin@aios.demo']})
                self.assertEqual(status, 200)
                token = login['token']
                self.assertEqual(request('/api/admin/providers', {})[0], 401)  # Unknown admin POST stays protected
                self.assertEqual(request('/api/admin/stats', token=token)[0], 403)
                self.assertEqual(request('/api/auth/change-password', {'current_password': credentials['admin@aios.demo'], 'new_password': 'RealReviewPassword123!'}, token)[0], 200)
                token = request('/api/auth/login', {'username': 'admin@aios.demo', 'password': 'RealReviewPassword123!'})[1]['token']
                self.assertEqual(request('/api/admin/stats', token=token)[0], 200)
                self.assertEqual(request('/api/ai/providers', token=token)[0], 200)
                with patch('hdc.agent_store._call_provider', return_value='test response'):
                    status, result = request('/api/ai/chat', {'agent_id': 'personal-ai', 'prompt': 'hello', 'context': {'identity': 'forged'}}, token)
                self.assertEqual(status, 200)
                self.assertEqual(result['text'], 'test response')
                self.assertEqual(recent_runs()[0]['identity'], login['user']['account_id'])
            finally:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main()
