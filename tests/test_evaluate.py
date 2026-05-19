import unittest
from pathlib import Path

from chat_record_analyzer.evaluate import evaluate_cases, load_cases, render_markdown, result_rows
from chat_record_analyzer.forms import FormCatalog
from chat_record_analyzer.parser import load_messages


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases("data/evaluation_cases.json")
        self.report = evaluate_cases(self.cases, form_catalog=FormCatalog.load())

    def test_manifest_references_existing_samples_and_chatseqs(self):
        sample_paths = {case.sample_path for case in self.cases}
        self.assertEqual(len(sample_paths), 12)
        for sample_path in sample_paths:
            self.assertTrue(Path(sample_path).exists())
            self.assertGreater(len(load_messages(sample_path)), 0)

    def test_batch_report_meets_stage_2_thresholds(self):
        summary = self.report.summary
        self.assertTrue(summary.threshold_passed)
        self.assertGreaterEqual(summary.accuracy, 0.8)
        self.assertGreaterEqual(summary.positive_recall, 0.8)
        self.assertLessEqual(summary.false_trigger_rate, 0.2)

    def test_batch_report_tracks_form_and_keyword_matches(self):
        self.assertGreaterEqual(self.report.summary.form_accuracy, 0.8)
        self.assertGreaterEqual(self.report.summary.keyword_match_rate, 0.8)

    def test_report_rows_support_streamlit_table(self):
        rows = result_rows(self.report)
        self.assertEqual(len(rows), len(self.cases))
        self.assertIn("case_id", rows[0])
        self.assertIn("rubric_overall", rows[0])

    def test_markdown_report_contains_key_metrics(self):
        markdown = render_markdown(self.report)
        self.assertIn("批量稳定性报告", markdown)
        self.assertIn("总体准确率", markdown)
        self.assertIn("失败用例", markdown)


if __name__ == "__main__":
    unittest.main()
