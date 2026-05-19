import unittest

from chat_record_analyzer.parser import load_messages, messages_until, parse_jsonl


class ParserTest(unittest.TestCase):
    def test_parse_jsonl_sorts_by_chatseq(self):
        text = """
{"session_id":"s","chatseq":2,"timestamp":"t","user_id":"u2","display_name":"B","role":"bot","org":"o","message_type":"text","content":"second"}
{"session_id":"s","chatseq":1,"timestamp":"t","user_id":"u1","display_name":"A","role":"external_vendor","org":"o","message_type":"text","content":"first"}
"""
        messages = parse_jsonl(text)
        self.assertEqual([message.chatseq for message in messages], [1, 2])

    def test_messages_until_filters_append_only_prefix(self):
        messages = load_messages("data/samples/thailand_port_lighting.jsonl")
        prefix = messages_until(messages, 4)
        self.assertEqual(len(prefix), 4)
        self.assertEqual(prefix[-1].chatseq, 4)


if __name__ == "__main__":
    unittest.main()
