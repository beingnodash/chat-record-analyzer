from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .agent import analyze_session
from .config import load_environment
from .forms import FormCatalog
from .models import ActionType, Decision
from .parser import load_messages, messages_until


DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "evaluation_cases.json"
DEFAULT_THRESHOLDS = {
    "accuracy": 0.8,
    "positive_recall": 0.8,
    "false_trigger_rate": 0.2,
}


@dataclass(frozen=True)
class ExpectedDecision:
    should_send: bool
    action_type: ActionType
    form_id: str | None = None
    message_keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ExpectedDecision":
        return cls(
            should_send=bool(raw["should_send"]),
            action_type=raw["action_type"],
            form_id=raw.get("form_id"),
            message_keywords=[str(keyword) for keyword in raw.get("message_keywords", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    sample_path: str
    chatseq: int
    expected: ExpectedDecision
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvaluationCase":
        return cls(
            case_id=str(raw["case_id"]),
            sample_path=str(raw["sample_path"]),
            chatseq=int(raw["chatseq"]),
            expected=ExpectedDecision.from_dict(raw["expected"]),
            tags=[str(tag) for tag in raw.get("tags", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["expected"] = self.expected.to_dict()
        return data


@dataclass(frozen=True)
class EvaluationResult:
    case: EvaluationCase
    decision: Decision
    passed: bool
    failures: list[str]
    checks: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case": self.case.to_dict(),
            "decision": self.decision.to_dict(),
            "passed": self.passed,
            "failures": self.failures,
            "checks": self.checks,
        }


@dataclass(frozen=True)
class EvaluationSummary:
    total_cases: int
    passed_cases: int
    accuracy: float
    positive_recall: float
    false_trigger_rate: float
    action_accuracy: float
    form_accuracy: float
    keyword_match_rate: float
    threshold_passed: bool
    thresholds: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationReport:
    summary: EvaluationSummary
    results: list[EvaluationResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "results": [result.to_dict() for result in self.results],
        }


def load_cases(path: str | Path = DEFAULT_MANIFEST_PATH) -> list[EvaluationCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = [EvaluationCase.from_dict(raw) for raw in raw_cases]
    _validate_cases(cases)
    return cases


def evaluate_cases(
    cases: list[EvaluationCase],
    *,
    form_catalog: FormCatalog | None = None,
    thresholds: dict[str, float] | None = None,
) -> EvaluationReport:
    catalog = form_catalog or FormCatalog.load()
    results = [_evaluate_case(case, catalog) for case in cases]
    summary = _summarize(results, thresholds or DEFAULT_THRESHOLDS)
    return EvaluationReport(summary=summary, results=results)


def evaluate_manifest(path: str | Path = DEFAULT_MANIFEST_PATH) -> EvaluationReport:
    return evaluate_cases(load_cases(path))


def render_markdown(report: EvaluationReport) -> str:
    summary = report.summary
    status = "PASS" if summary.threshold_passed else "FAIL"
    lines = [
        "# 批量稳定性报告",
        "",
        f"整体状态：**{status}**",
        "",
        "| 指标 | 数值 | 阈值 |",
        "| --- | ---: | ---: |",
        f"| 总体准确率 | {summary.accuracy:.2%} | {summary.thresholds['accuracy']:.0%} |",
        f"| 正例召回 | {summary.positive_recall:.2%} | {summary.thresholds['positive_recall']:.0%} |",
        f"| 误触发率 | {summary.false_trigger_rate:.2%} | <= {summary.thresholds['false_trigger_rate']:.0%} |",
        f"| 动作准确率 | {summary.action_accuracy:.2%} | - |",
        f"| 表单准确率 | {summary.form_accuracy:.2%} | - |",
        f"| 话术关键词匹配率 | {summary.keyword_match_rate:.2%} | - |",
        "",
        f"通过用例：{summary.passed_cases}/{summary.total_cases}",
        "",
        "## 失败用例",
        "",
    ]
    failed = [result for result in report.results if not result.passed]
    if not failed:
        lines.append("无。")
    else:
        lines.extend(["| Case | 实际动作 | 失败原因 |", "| --- | --- | --- |"])
        for result in failed:
            lines.append(
                f"| {result.case.case_id} | {result.decision.action_type} | {'; '.join(result.failures)} |"
            )
    return "\n".join(lines)


def result_rows(report: EvaluationReport) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in report.results:
        rows.append(
            {
                "case_id": result.case.case_id,
                "sample_path": result.case.sample_path,
                "chatseq": result.case.chatseq,
                "tags": ", ".join(result.case.tags),
                "passed": result.passed,
                "expected_action": result.case.expected.action_type,
                "actual_action": result.decision.action_type,
                "expected_send": result.case.expected.should_send,
                "actual_send": result.decision.should_send,
                "expected_form": result.case.expected.form_id or "",
                "actual_form": result.decision.form_id or "",
                "failures": "; ".join(result.failures),
                "confidence": result.decision.confidence,
                "rubric_overall": result.decision.rubric_scores.overall,
            }
        )
    return rows


def _evaluate_case(case: EvaluationCase, catalog: FormCatalog) -> EvaluationResult:
    messages = messages_until(load_messages(case.sample_path), case.chatseq)
    decision = analyze_session(messages, form_catalog=catalog)
    expected = case.expected
    checks = {
        "should_send": decision.should_send == expected.should_send,
        "action_type": decision.action_type == expected.action_type,
        "form_id": expected.form_id is None or decision.form_id == expected.form_id,
        "message_keywords": all(keyword in decision.draft_message for keyword in expected.message_keywords),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return EvaluationResult(
        case=case,
        decision=decision,
        passed=all(checks.values()),
        failures=failures,
        checks=checks,
    )


def _summarize(results: list[EvaluationResult], thresholds: dict[str, float]) -> EvaluationSummary:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    positives = [result for result in results if result.case.expected.should_send]
    negatives = [result for result in results if not result.case.expected.should_send]
    form_cases = [result for result in results if result.case.expected.form_id is not None]
    keyword_cases = [result for result in results if result.case.expected.message_keywords]

    accuracy = _rate(passed, total)
    positive_recall = _rate(sum(1 for result in positives if result.decision.should_send), len(positives))
    false_trigger_rate = _rate(sum(1 for result in negatives if result.decision.should_send), len(negatives))
    action_accuracy = _rate(sum(1 for result in results if result.checks["action_type"]), total)
    form_accuracy = _rate(sum(1 for result in form_cases if result.checks["form_id"]), len(form_cases))
    keyword_match_rate = _rate(
        sum(1 for result in keyword_cases if result.checks["message_keywords"]),
        len(keyword_cases),
    )
    threshold_passed = (
        accuracy >= thresholds["accuracy"]
        and positive_recall >= thresholds["positive_recall"]
        and false_trigger_rate <= thresholds["false_trigger_rate"]
    )
    return EvaluationSummary(
        total_cases=total,
        passed_cases=passed,
        accuracy=accuracy,
        positive_recall=positive_recall,
        false_trigger_rate=false_trigger_rate,
        action_accuracy=action_accuracy,
        form_accuracy=form_accuracy,
        keyword_match_rate=keyword_match_rate,
        threshold_passed=threshold_passed,
        thresholds=thresholds,
    )


def _validate_cases(cases: list[EvaluationCase]) -> None:
    seen_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_ids:
            raise ValueError(f"duplicate evaluation case id: {case.case_id}")
        seen_ids.add(case.case_id)
        messages = load_messages(case.sample_path)
        if not any(message.chatseq == case.chatseq for message in messages):
            raise ValueError(f"case {case.case_id} points to missing chatseq {case.chatseq}")
        if case.expected.action_type == "none" and case.expected.should_send:
            raise ValueError(f"case {case.case_id} cannot send with action_type=none")


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)


def main() -> None:
    load_environment()
    parser = argparse.ArgumentParser(description="Run batch stability evaluation for chat intervention decisions.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_MANIFEST_PATH), help="Path to evaluation manifest JSON")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    report = evaluate_manifest(args.manifest)
    if args.format == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
