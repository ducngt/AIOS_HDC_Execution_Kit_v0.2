import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from hdc.people_store import database_info, import_workbook, list_imports, list_people, save_data_record, list_data_records, stats


class RuntimePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "aios.sqlite3"
        self.env = patch.dict(os.environ, {"AIOS_DB_PATH": str(self.db)}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def make_org_workbook(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Data"
        ws.append(["Mã đơn vị", "Loại phòng ban", "Tên", "Tên viết tắt", "Mã đơn vị cấp trên", "Hiển thị"])
        ws.append(["ORG-01", "Khoa", "Khoa Công nghệ", "CN", None, 1])
        from io import BytesIO
        b = BytesIO(); wb.save(b)
        return base64.b64encode(b.getvalue()).decode()

    def test_import_is_persisted_and_visible_after_reconnect(self):
        report = import_workbook("organizations.xlsx", self.make_org_workbook())
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(stats()["organizations"], 1)
        self.assertTrue(database_info()["exists"])
        self.assertEqual(len(list_imports()), 1)
        self.assertEqual(stats()["organizations"], 1)

    def test_data_record_is_persisted(self):
        saved = save_data_record({"type":"Evidence","zone":"D5","value":"Persistent evidence","created_by":"tester"})
        self.assertTrue(saved["saved"])
        rows = list_data_records()
        self.assertEqual(rows[0]["value"], "Persistent evidence")
        self.assertEqual(rows[0]["zone"], "D5")


if __name__ == "__main__":
    unittest.main()
