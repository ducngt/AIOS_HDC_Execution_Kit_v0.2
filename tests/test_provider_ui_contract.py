import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProviderUiContractTests(unittest.TestCase):
    def test_runtime_and_pages_ui_expose_provider_key_configuration(self):
        for path in (ROOT / "ui/app.js", ROOT / "app.js"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Cấu hình API AI", text)
            self.assertIn('id="pvKey" type="password"', text)
            self.assertIn("Lưu & kiểm tra", text)
            self.assertIn("/api/admin/provider-secret", text)
            self.assertIn("/api/admin/provider-test", text)

    def test_admin_lands_on_provider_registry(self):
        for path in (ROOT / "ui/app.js", ROOT / "app.js"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("showAdminSection('providers')", text)

    def test_browser_does_not_persist_provider_secret(self):
        for path in (ROOT / "ui/app.js", ROOT / "app.js"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("localStorage.setItem('OPENAI_API_KEY'", text)
            self.assertNotIn('localStorage.setItem("OPENAI_API_KEY"', text)


if __name__ == "__main__":
    unittest.main()
