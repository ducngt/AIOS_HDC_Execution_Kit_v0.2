import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hdc import agent_store


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"AIOS_DB_PATH": str(Path(self.tmp.name) / "runtime.sqlite3")}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        agent_store.ensure_seeded()

    def test_seed_contains_multi_agent_families(self):
        agents = agent_store.list_agents()
        categories = {a["category"] for a in agents}
        self.assertTrue({"personal", "domain", "admin", "verification", "data", "institutional"}.issubset(categories))
        self.assertGreaterEqual(len(agents), 8)

    def test_provider_registry_has_multiple_adapters_and_no_secret_values(self):
        providers = agent_store.list_providers()
        adapters = {p["adapter_type"] for p in providers}
        self.assertTrue({"openai_responses", "anthropic_messages", "gemini_generate_content", "openai_chat"}.issubset(adapters))
        self.assertTrue(all(p.get("secret_value") is None for p in providers))

    def test_agent_save_persists(self):
        agent_store.save_agent({
            "agent_id": "test-agent",
            "name": "Test Agent",
            "category": "domain",
            "purpose": "Test purpose",
            "domain": "QIS",
            "provider_id": "openai",
            "system_prompt": "Human retains authority.",
        })
        found = {a["agent_id"]: a for a in agent_store.list_agents()}
        self.assertIn("test-agent", found)
        self.assertEqual(found["test-agent"]["domain"], "QIS")

    def test_provider_save_persists_without_key(self):
        agent_store.save_provider({
            "provider_id": "local-provider",
            "name": "Local Provider",
            "adapter_type": "openai_chat",
            "base_url": "http://localhost:9999/v1",
            "api_key_env": "LOCAL_AI_KEY",
            "default_model": "local-model",
            "models": ["local-model"],
        })
        found = {p["provider_id"]: p for p in agent_store.list_providers()}
        self.assertEqual(found["local-provider"]["api_key_env"], "LOCAL_AI_KEY")
        self.assertFalse(found["local-provider"]["configured"])

    def test_chat_records_run_with_mock_provider(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=False):
            with patch.object(agent_store, "_call_provider", return_value="mock answer"):
                result = agent_store.chat("personal-ai", "hello", {"identity": "Tester", "role": "Lecturer", "authority": "scope"})
        self.assertEqual(result["text"], "mock answer")
        runs = agent_store.recent_runs()
        self.assertEqual(runs[0]["status"], "completed")
        self.assertEqual(runs[0]["agent_id"], "personal-ai")


if __name__ == "__main__":
    unittest.main()

class ProviderConfigurationTests(unittest.TestCase):
    def test_provider_diagnostic_reports_missing_secret_without_exposing_value(self):
        import os
        from hdc.agent_store import provider_diagnostic
        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            result = provider_diagnostic("openai")
            self.assertFalse(result["ok"])
            self.assertFalse(result["configured"])
            self.assertIn("OPENAI_API_KEY", result["detail"])
            self.assertNotIn("secret_value", result)
        finally:
            if old is not None:
                os.environ["OPENAI_API_KEY"] = old
