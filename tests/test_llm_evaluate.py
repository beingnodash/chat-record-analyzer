import json
import tempfile
import unittest
from pathlib import Path

from chat_record_analyzer.llm_evaluate import (
    evaluate_llm_cases,
    load_llm_cases,
    render_markdown,
    result_rows,
)


class StubEnhancementClient:
    def polish(self, prompt, fallback):
        if not fallback:
            return fallback
        return f"{fallback}\n请通过表单提交照明资料。"

    def complete_json(self, prompt, fallback):
        return {
            "has_project_opportunity": True,
            "has_information_gap": True,
            "has_vendor_readiness": True,
            "has_timing_signal": True,
            "summary": "识别到项目机会、资料意愿和时间窗口。",
            "evidence_chatseqs": [1, 4, 6],
            "source": "llm",
        }

    def complete_text(self, prompt, fallback):
        return "李总已经表达资料整理意愿，照明方案适合通过配置表单采集。"


class LlmEvaluationTest(unittest.TestCase):
    def test_llm_manifest_references_existing_samples_and_chatseqs(self):
        cases = load_llm_cases("data/llm_evaluation_cases.json")
        self.assertGreaterEqual(len(cases), 8)
        for case in cases:
            self.assertTrue(Path(case.sample_path).exists())

    def test_snapshot_report_can_run_without_deepseek_key(self):
        cases = load_llm_cases("data/llm_evaluation_cases.json")[:1]
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / f"{cases[0].case_id}.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "case_id": cases[0].case_id,
                        "source": "test-snapshot",
                        "polished_message": "请同步照明解决方案资料。",
                        "decision": {"should_send": True, "action_type": "ask_for_info"},
                        "semantic_signals": {
                            "has_project_opportunity": True,
                            "has_information_gap": True,
                            "has_timing_signal": True,
                        },
                        "explanation": "照明需求和时间窗口已经出现，适合轻量引导。",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report = evaluate_llm_cases(cases, snapshot_dir=temp_dir)
            self.assertTrue(report.summary.threshold_passed)
            self.assertEqual(len(result_rows(report)), 1)

    def test_deepseek_source_writes_snapshots_only_when_explicit(self):
        cases = load_llm_cases("data/llm_evaluation_cases.json")[:1]
        with tempfile.TemporaryDirectory() as temp_dir:
            report = evaluate_llm_cases(
                cases,
                source="deepseek",
                snapshot_dir=temp_dir,
                write_snapshots=False,
                client=StubEnhancementClient(),
            )
            self.assertTrue(report.summary.threshold_passed)
            self.assertFalse((Path(temp_dir) / f"{cases[0].case_id}.json").exists())

            evaluate_llm_cases(
                cases,
                source="deepseek",
                snapshot_dir=temp_dir,
                write_snapshots=True,
                client=StubEnhancementClient(),
            )
            self.assertTrue((Path(temp_dir) / f"{cases[0].case_id}.json").exists())

    def test_markdown_report_contains_llm_metrics(self):
        cases = load_llm_cases("data/llm_evaluation_cases.json")[:1]
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluate_llm_cases(
                cases,
                source="deepseek",
                snapshot_dir=temp_dir,
                write_snapshots=True,
                client=StubEnhancementClient(),
            )
            markdown = render_markdown(evaluate_llm_cases(cases, snapshot_dir=temp_dir))
            self.assertIn("LLM 增强复盘报告", markdown)
            self.assertIn("语义信号命中率", markdown)


if __name__ == "__main__":
    unittest.main()
