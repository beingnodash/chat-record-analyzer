from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .agent import analyze_session
from .config import load_environment
from .enhancements import explain_decision, extract_semantic_signals
from .forms import FormCatalog
from .llm import DeepSeekDraftClient, DraftClient, MockDraftClient
from .parser import load_messages, messages_until


DEFAULT_LLM_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "llm_evaluation_cases.json"
DEFAULT_SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "data" / "llm_snapshots"
DEFAULT_THRESHOLDS = {
    "semantic_signal_rate": 0.8,
    "explanation_coverage_rate": 0.8,
    "message_quality_rate": 0.8,
}
SnapshotSource = Literal["snapshots", "deepseek"]


@dataclass(frozen=True)
class LlmExpected:
    expected_signals: dict[str, bool] = field(default_factory=dict)
    message_keywords: list[str] = field(default_factory=list)
    explanation_keywords: list[str] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LlmExpected":
        return cls(
            expected_signals={str(key): bool(value) for key, value in raw.get("expected_signals", {}).items()},
            message_keywords=[str(keyword) for keyword in raw.get("message_keywords", [])],
            explanation_keywords=[str(keyword) for keyword in raw.get("explanation_keywords", [])],
            forbidden_terms=[str(term) for term in raw.get("forbidden_terms", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LlmEvaluationCase:
    case_id: str
    sample_path: str
    chatseq: int
    focus: list[str]
    expected: LlmExpected
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LlmEvaluationCase":
        return cls(
            case_id=str(raw["case_id"]),
            sample_path=str(raw["sample_path"]),
            chatseq=int(raw["chatseq"]),
            focus=[str(item) for item in raw.get("focus", [])],
            expected=LlmExpected.from_dict(raw.get("expected", {})),
            tags=[str(tag) for tag in raw.get("tags", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["expected"] = self.expected.to_dict()
        return data


@dataclass(frozen=True)
class LlmEvaluationResult:
    case: LlmEvaluationCase
    snapshot: dict[str, Any]
    passed: bool
    failures: list[str]
    checks: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case": self.case.to_dict(),
            "snapshot": self.snapshot,
            "passed": self.passed,
            "failures": self.failures,
            "checks": self.checks,
        }


@dataclass(frozen=True)
class LlmEvaluationSummary:
    total_cases: int
    passed_cases: int
    semantic_signal_rate: float
    explanation_coverage_rate: float
    message_quality_rate: float
    threshold_passed: bool
    thresholds: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LlmEvaluationReport:
    summary: LlmEvaluationSummary
    results: list[LlmEvaluationResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "results": [result.to_dict() for result in self.results],
        }


def load_llm_cases(path: str | Path = DEFAULT_LLM_MANIFEST_PATH) -> list[LlmEvaluationCase]:
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = [LlmEvaluationCase.from_dict(raw) for raw in raw_cases]
    _validate_cases(cases)
    return cases


def evaluate_llm_cases(
    cases: list[LlmEvaluationCase],
    *,
    source: SnapshotSource = "snapshots",
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    write_snapshots: bool = False,
    client: DraftClient | None = None,
    form_catalog: FormCatalog | None = None,
    thresholds: dict[str, float] | None = None,
) -> LlmEvaluationReport:
    catalog = form_catalog or FormCatalog.load()
    snapshot_root = Path(snapshot_dir)
    results: list[LlmEvaluationResult] = []
    for case in cases:
        snapshot = (
            _build_snapshot(case, catalog, client or _deepseek_client_or_raise())
            if source == "deepseek"
            else _load_snapshot(case, snapshot_root)
        )
        if source == "deepseek" and write_snapshots:
            _write_snapshot(case, snapshot, snapshot_root)
        results.append(_evaluate_case(case, snapshot))
    return LlmEvaluationReport(
        summary=_summarize(results, thresholds or DEFAULT_THRESHOLDS),
        results=results,
    )


def evaluate_llm_manifest(
    path: str | Path = DEFAULT_LLM_MANIFEST_PATH,
    *,
    source: SnapshotSource = "snapshots",
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    write_snapshots: bool = False,
    client: DraftClient | None = None,
) -> LlmEvaluationReport:
    return evaluate_llm_cases(
        load_llm_cases(path),
        source=source,
        snapshot_dir=snapshot_dir,
        write_snapshots=write_snapshots,
        client=client,
    )


def result_rows(report: LlmEvaluationReport) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in report.results:
        decision = result.snapshot.get("decision", {})
        rows.append(
            {
                "case_id": result.case.case_id,
                "tags": ", ".join(result.case.tags),
                "passed": result.passed,
                "focus": ", ".join(result.case.focus),
                "action": decision.get("action_type", ""),
                "should_send": decision.get("should_send", False),
                "semantic": result.checks["semantic_signals"],
                "explanation": result.checks["explanation_keywords"],
                "message_quality": result.checks["message_quality"],
                "restraint": result.checks["forbidden_terms"],
                "failures": "; ".join(result.failures),
                "snapshot_source": result.snapshot.get("source", ""),
            }
        )
    return rows


def render_markdown(report: LlmEvaluationReport) -> str:
    summary = report.summary
    status = "PASS" if summary.threshold_passed else "FAIL"
    lines = [
        "# LLM 增强复盘报告",
        "",
        f"整体状态：**{status}**",
        "",
        "| 指标 | 数值 | 阈值 |",
        "| --- | ---: | ---: |",
        f"| 语义信号命中率 | {summary.semantic_signal_rate:.2%} | {summary.thresholds['semantic_signal_rate']:.0%} |",
        f"| 解释要点覆盖率 | {summary.explanation_coverage_rate:.2%} | {summary.thresholds['explanation_coverage_rate']:.0%} |",
        f"| 话术关键词/克制性 | {summary.message_quality_rate:.2%} | {summary.thresholds['message_quality_rate']:.0%} |",
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
        lines.extend(["| Case | 失败原因 |", "| --- | --- |"])
        for result in failed:
            lines.append(f"| {result.case.case_id} | {'; '.join(result.failures)} |")
    return "\n".join(lines)


def _build_snapshot(case: LlmEvaluationCase, catalog: FormCatalog, client: DraftClient) -> dict[str, Any]:
    messages = messages_until(load_messages(case.sample_path), case.chatseq)
    fallback_decision = analyze_session(messages, form_catalog=catalog, draft_client=MockDraftClient())
    enhanced_decision = analyze_session(messages, form_catalog=catalog, draft_client=client)
    semantic_signals = extract_semantic_signals(messages, client)
    explanation = explain_decision(messages, enhanced_decision, client)
    return {
        "case_id": case.case_id,
        "source": "deepseek",
        "generated_at": datetime.now(UTC).isoformat(),
        "sample_path": case.sample_path,
        "chatseq": case.chatseq,
        "input_summary": {
            "message_count": len(messages),
            "last_message": messages[-1].to_dict() if messages else None,
        },
        "fallback_message": fallback_decision.draft_message,
        "polished_message": enhanced_decision.draft_message,
        "decision": enhanced_decision.to_dict(),
        "semantic_signals": semantic_signals.to_dict(),
        "explanation": explanation,
    }


def _evaluate_case(case: LlmEvaluationCase, snapshot: dict[str, Any]) -> LlmEvaluationResult:
    expected = case.expected
    semantic = snapshot.get("semantic_signals", {})
    polished_message = str(snapshot.get("polished_message") or "")
    explanation = str(snapshot.get("explanation") or "")
    combined_text = f"{polished_message}\n{explanation}"
    checks = {
        "semantic_signals": all(bool(semantic.get(key)) == value for key, value in expected.expected_signals.items()),
        "message_keywords": all(keyword in polished_message for keyword in expected.message_keywords),
        "explanation_keywords": all(keyword in explanation for keyword in expected.explanation_keywords),
        "forbidden_terms": all(term not in combined_text for term in expected.forbidden_terms),
    }
    checks["message_quality"] = checks["message_keywords"] and checks["forbidden_terms"]
    failures = [name for name, passed in checks.items() if not passed and name != "message_quality"]
    if not checks["message_quality"] and "message_keywords" not in failures and "forbidden_terms" not in failures:
        failures.append("message_quality")
    return LlmEvaluationResult(
        case=case,
        snapshot=snapshot,
        passed=all(checks.values()),
        failures=failures,
        checks=checks,
    )


def _summarize(results: list[LlmEvaluationResult], thresholds: dict[str, float]) -> LlmEvaluationSummary:
    semantic_cases = [result for result in results if result.case.expected.expected_signals]
    explanation_cases = [result for result in results if result.case.expected.explanation_keywords]
    message_cases = [
        result
        for result in results
        if result.case.expected.message_keywords or result.case.expected.forbidden_terms
    ]
    semantic_signal_rate = _rate(
        sum(1 for result in semantic_cases if result.checks["semantic_signals"]),
        len(semantic_cases),
    )
    explanation_coverage_rate = _rate(
        sum(1 for result in explanation_cases if result.checks["explanation_keywords"]),
        len(explanation_cases),
    )
    message_quality_rate = _rate(
        sum(1 for result in message_cases if result.checks["message_quality"]),
        len(message_cases),
    )
    threshold_passed = (
        semantic_signal_rate >= thresholds["semantic_signal_rate"]
        and explanation_coverage_rate >= thresholds["explanation_coverage_rate"]
        and message_quality_rate >= thresholds["message_quality_rate"]
    )
    return LlmEvaluationSummary(
        total_cases=len(results),
        passed_cases=sum(1 for result in results if result.passed),
        semantic_signal_rate=semantic_signal_rate,
        explanation_coverage_rate=explanation_coverage_rate,
        message_quality_rate=message_quality_rate,
        threshold_passed=threshold_passed,
        thresholds=thresholds,
    )


def _load_snapshot(case: LlmEvaluationCase, snapshot_dir: Path) -> dict[str, Any]:
    path = snapshot_dir / f"{case.case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"missing LLM snapshot: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_snapshot(case: LlmEvaluationCase, snapshot: dict[str, Any], snapshot_dir: Path) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / f"{case.case_id}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_cases(cases: list[LlmEvaluationCase]) -> None:
    seen_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_ids:
            raise ValueError(f"duplicate LLM evaluation case id: {case.case_id}")
        seen_ids.add(case.case_id)
        messages = load_messages(case.sample_path)
        if not any(message.chatseq == case.chatseq for message in messages):
            raise ValueError(f"case {case.case_id} points to missing chatseq {case.chatseq}")


def _deepseek_client_or_raise() -> DraftClient:
    client = DeepSeekDraftClient.from_env()
    if client is None:
        raise RuntimeError("DEEPSEEK_API_KEY is required when --source deepseek is used")
    return client


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator


def main() -> None:
    load_environment()
    parser = argparse.ArgumentParser(description="Evaluate controlled LLM enhancement snapshots.")
    parser.add_argument("manifest", nargs="?", default=str(DEFAULT_LLM_MANIFEST_PATH))
    parser.add_argument("--source", choices=["snapshots", "deepseek"], default="snapshots")
    parser.add_argument("--snapshot-dir", default=str(DEFAULT_SNAPSHOT_DIR))
    parser.add_argument("--write-snapshots", action="store_true")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    try:
        report = evaluate_llm_manifest(
            args.manifest,
            source=args.source,
            snapshot_dir=args.snapshot_dir,
            write_snapshots=args.write_snapshots,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    if args.format == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))


if __name__ == "__main__":
    main()
