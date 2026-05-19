import unittest

from chat_record_analyzer.agent import analyze_session
from chat_record_analyzer.forms import FormCatalog
from chat_record_analyzer.parser import load_messages, messages_until


class AgentTest(unittest.TestCase):
    def setUp(self):
        self.catalog = FormCatalog.load()
        self.messages = load_messages("data/samples/thailand_port_lighting.jsonl")

    def test_owner_timeline_after_vendor_interest_triggers_info_request(self):
        decision = analyze_session(messages_until(self.messages, 4), form_catalog=self.catalog)
        self.assertTrue(decision.should_send)
        self.assertEqual(decision.action_type, "ask_for_info")
        self.assertIn(3, decision.evidence_chatseqs)
        self.assertIn(4, decision.evidence_chatseqs)
        self.assertIn("李总", decision.draft_message)

    def test_vendor_readiness_after_bot_request_triggers_form(self):
        decision = analyze_session(messages_until(self.messages, 6), form_catalog=self.catalog)
        self.assertTrue(decision.should_send)
        self.assertEqual(decision.action_type, "send_form")
        self.assertEqual(decision.form_id, "thailand-port-lighting")
        self.assertIn("https://example.com/form/thailand-port-lighting", decision.draft_message)

    def test_after_form_was_sent_does_not_repeat(self):
        decision = analyze_session(messages_until(self.messages, 10), form_catalog=self.catalog)
        self.assertFalse(decision.should_send)
        self.assertEqual(decision.action_type, "none")

    def test_vendor_question_before_owner_response_does_not_interrupt(self):
        decision = analyze_session(messages_until(self.messages, 3), form_catalog=self.catalog)
        self.assertFalse(decision.should_send)

    def test_short_low_signal_sample_does_not_send(self):
        messages = load_messages("data/samples/vietnam_port_equipment.jsonl")
        decision = analyze_session(messages, form_catalog=self.catalog)
        self.assertFalse(decision.should_send)


if __name__ == "__main__":
    unittest.main()
