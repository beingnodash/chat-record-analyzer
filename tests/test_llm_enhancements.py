import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chat_record_analyzer.agent import analyze_session
from chat_record_analyzer.config import load_environment
from chat_record_analyzer.enhancements import explain_decision, extract_semantic_signals
from chat_record_analyzer.forms import FormCatalog
from chat_record_analyzer.llm import DeepSeekDraftClient
from chat_record_analyzer.parser import load_messages, messages_until


class BrokenJsonClient:
    def complete_json(self, prompt, fallback):
        raise ValueError("bad json")


class BrokenTextClient:
    def complete_text(self, prompt, fallback):
        raise TimeoutError("timeout")


class LlmEnhancementTest(unittest.TestCase):
    def setUp(self):
        self.messages = messages_until(load_messages("data/samples/thailand_port_lighting.jsonl"), 6)
        self.decision = analyze_session(self.messages, form_catalog=FormCatalog.load())

    def test_dotenv_loads_without_overriding_existing_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("DEEPSEEK_API_KEY=from-file\nDEEPSEEK_MODEL=from-file-model\n", encoding="utf-8")
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "already-set"}, clear=True):
                loaded = load_environment(env_path)
                self.assertTrue(loaded)
                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "already-set")
                self.assertEqual(os.environ["DEEPSEEK_MODEL"], "from-file-model")

    def test_deepseek_polish_failure_returns_fallback(self):
        client = DeepSeekDraftClient(api_key="test", base_url="https://example.invalid", timeout_seconds=1)
        with patch("urllib.request.urlopen", side_effect=TimeoutError):
            self.assertEqual(client.polish("prompt", "fallback"), "fallback")

    def test_semantic_signal_parse_failure_returns_fallback(self):
        signals = extract_semantic_signals(self.messages, BrokenJsonClient())
        self.assertEqual(signals.source, "fallback")
        self.assertTrue(signals.has_project_opportunity)
        self.assertTrue(signals.has_vendor_readiness)

    def test_semantic_signal_failure_does_not_change_rule_decision(self):
        before = analyze_session(self.messages, form_catalog=FormCatalog.load())
        extract_semantic_signals(self.messages, BrokenJsonClient())
        after = analyze_session(self.messages, form_catalog=FormCatalog.load())
        self.assertEqual(before.to_dict(), after.to_dict())

    def test_explanation_failure_returns_decision_rationale(self):
        explanation = explain_decision(self.messages, self.decision, BrokenTextClient())
        self.assertEqual(explanation, self.decision.rationale)


if __name__ == "__main__":
    unittest.main()
