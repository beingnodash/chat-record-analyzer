import unittest
from unittest.mock import patch

from chat_record_analyzer.forms import FormCatalog
from chat_record_analyzer.parser import load_messages
from chat_record_analyzer.replay import build_replay_timeline, card_from_message
from chat_record_analyzer.runtime import select_draft_client


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.catalog = FormCatalog.load()
        self.messages = load_messages("data/samples/thailand_port_lighting.jsonl")
        self.timeline = build_replay_timeline(self.messages, form_catalog=self.catalog)

    def test_timeline_has_one_item_per_message(self):
        self.assertEqual(len(self.timeline), len(self.messages))
        self.assertEqual([item.chatseq for item in self.timeline], [message.chatseq for message in self.messages])

    def test_replay_key_decisions_match_golden_case(self):
        by_seq = {item.chatseq: item for item in self.timeline}
        self.assertTrue(by_seq[4].decision.should_send)
        self.assertEqual(by_seq[4].decision.action_type, "ask_for_info")
        self.assertTrue(by_seq[6].decision.should_send)
        self.assertEqual(by_seq[6].decision.action_type, "send_form")
        self.assertEqual(by_seq[6].decision.form_id, "thailand-port-lighting")
        self.assertFalse(by_seq[10].decision.should_send)

    def test_candidate_form_card_uses_catalog(self):
        by_seq = {item.chatseq: item for item in self.timeline}
        card = by_seq[6].candidate_card
        self.assertIsNotNone(card)
        self.assertEqual(card.form_id, "thailand-port-lighting")
        self.assertIn("照明解决方案", card.title)

    def test_existing_form_card_is_extracted_from_archive_message(self):
        card = card_from_message(self.messages[6], self.catalog)
        self.assertIsNotNone(card)
        self.assertEqual(card.form_id, "thailand-port-lighting")
        self.assertEqual(card.source, "archive")

    def test_existing_news_card_splits_badge_and_inline_title(self):
        card = card_from_message(self.messages[0], self.catalog)
        self.assertIsNotNone(card)
        self.assertEqual(card.badge, "资讯卡片")
        self.assertIn("泰国港口", card.title)


class RuntimeTest(unittest.TestCase):
    def test_mock_mode_uses_mock_client(self):
        selection = select_draft_client("mock")
        self.assertEqual(selection.active_mode, "mock")
        self.assertFalse(selection.using_fallback)

    def test_deepseek_without_key_falls_back_to_mock(self):
        with patch.dict("os.environ", {"CHAT_RECORD_ANALYZER_SKIP_DOTENV": "1"}, clear=True):
            selection = select_draft_client("deepseek")
        self.assertEqual(selection.requested_mode, "deepseek")
        self.assertEqual(selection.active_mode, "mock")
        self.assertTrue(selection.using_fallback)

    def test_deepseek_with_key_uses_deepseek_client(self):
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key", "CHAT_RECORD_ANALYZER_SKIP_DOTENV": "1"}, clear=True):
            selection = select_draft_client("deepseek")
        self.assertEqual(selection.active_mode, "deepseek")
        self.assertFalse(selection.using_fallback)


if __name__ == "__main__":
    unittest.main()
