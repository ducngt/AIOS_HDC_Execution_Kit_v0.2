import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hdc.people_store import authenticate
from hdc.review_accounts import provision


class ReviewAccountsTests(unittest.TestCase):
    def test_provision_creates_real_accounts_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'AIOS_DB_PATH': str(Path(tmp) / 'db.sqlite3')}):
            rows = provision()
            self.assertEqual(len(rows), 3)
            for username, password in rows:
                self.assertTrue(password and len(password) >= 12)
                self.assertIsNotNone(authenticate(username, password))
            self.assertTrue(all(password is None for _, password in provision()))
            self.assertIsNotNone(authenticate(rows[2][0], rows[2][1]))


if __name__ == '__main__':
    unittest.main()
