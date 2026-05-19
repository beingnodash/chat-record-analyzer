import unittest

from chat_record_analyzer.agent import analyze_session
from chat_record_analyzer.forms import FormCatalog
from chat_record_analyzer.parser import load_messages, messages_until


class FormsAndRubricTest(unittest.TestCase):
    def test_form_catalog_selects_lighting_form(self):
        catalog = FormCatalog.load()
        form = catalog.best_match("港口 高杆灯 堆场照明 智能配电 远程运维 节能测算")
        self.assertEqual(form.form_id, "thailand-port-lighting")

    def test_form_catalog_selects_non_port_vertical_forms(self):
        catalog = FormCatalog.load()
        self.assertEqual(catalog.best_match("储能 并网 光伏 电力").form_id, "power-energy-solution")
        self.assertEqual(catalog.best_match("水处理 膜系统 泵站 运维").form_id, "water-treatment-solution")
        self.assertEqual(catalog.best_match("园区 物流 WMS 车队 调度").form_id, "logistics-park-solution")

    def test_positive_decision_has_explainable_rubric(self):
        messages = messages_until(load_messages("data/samples/thailand_port_lighting.jsonl"), 6)
        decision = analyze_session(messages, form_catalog=FormCatalog.load())
        scores = decision.rubric_scores.to_dict()
        self.assertGreaterEqual(scores["overall"], 4)
        self.assertGreaterEqual(scores["evidence_strength"], 3)
        self.assertGreaterEqual(scores["form_fit"], 4)


if __name__ == "__main__":
    unittest.main()
