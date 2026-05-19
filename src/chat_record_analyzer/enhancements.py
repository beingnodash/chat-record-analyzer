from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .llm import DraftClient
from .models import ChatMessage, Decision


@dataclass(frozen=True)
class SemanticSignals:
    has_project_opportunity: bool
    has_information_gap: bool
    has_vendor_readiness: bool
    has_timing_signal: bool
    summary: str
    evidence_chatseqs: list[int] = field(default_factory=list)
    source: str = "fallback"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_semantic_signals(messages: list[ChatMessage], client: DraftClient | None = None) -> SemanticSignals:
    fallback = _fallback_semantic_signals(messages)
    if client is None:
        return fallback

    complete_json = getattr(client, "complete_json", None)
    if complete_json is None:
        return fallback

    try:
        raw = complete_json(_semantic_prompt(messages), fallback.to_dict())
        return _signals_from_dict(raw)
    except Exception:
        return fallback


def explain_decision(messages: list[ChatMessage], decision: Decision, client: DraftClient | None = None) -> str:
    fallback = decision.rationale
    if client is None:
        return fallback

    complete_text = getattr(client, "complete_text", None)
    if complete_text is None:
        return fallback

    try:
        text = complete_text(_explanation_prompt(messages, decision), fallback)
    except Exception:
        return fallback
    return text.strip() or fallback


def _fallback_semantic_signals(messages: list[ChatMessage]) -> SemanticSignals:
    text = "\n".join(message.content for message in messages)
    project_words = ["项目", "工程", "港口", "园区", "铁路", "水务", "电力", "物流", "业主", "总包"]
    gap_words = ["不明确", "还没", "后续", "讨论", "清单", "参数", "案例", "方案", "支持范围"]
    readiness_words = ["整理", "提交", "提供", "发给", "资料", "可以"]
    timing_words = ["启动会", "下周", "下个月", "后续", "7月", "技术会", "专题会"]
    evidence = [
        message.chatseq
        for message in messages
        if any(word in message.content for word in project_words + readiness_words + timing_words)
    ][:5]
    has_project = any(word in text for word in project_words)
    has_gap = any(word in text for word in gap_words)
    has_readiness = any(word in text for word in readiness_words)
    has_timing = any(word in text for word in timing_words)
    summary = "规则回退识别到"
    summary += "项目机会" if has_project else "暂无明确项目机会"
    if has_gap:
        summary += "、信息缺口"
    if has_readiness:
        summary += "、资料意愿"
    if has_timing:
        summary += "、时间窗口"
    return SemanticSignals(
        has_project_opportunity=has_project,
        has_information_gap=has_gap,
        has_vendor_readiness=has_readiness,
        has_timing_signal=has_timing,
        summary=summary,
        evidence_chatseqs=evidence,
        source="fallback",
    )


def _signals_from_dict(raw: dict[str, Any]) -> SemanticSignals:
    return SemanticSignals(
        has_project_opportunity=bool(raw.get("has_project_opportunity")),
        has_information_gap=bool(raw.get("has_information_gap")),
        has_vendor_readiness=bool(raw.get("has_vendor_readiness")),
        has_timing_signal=bool(raw.get("has_timing_signal")),
        summary=str(raw.get("summary") or "LLM 未返回摘要。"),
        evidence_chatseqs=[int(seq) for seq in raw.get("evidence_chatseqs", [])],
        source=str(raw.get("source") or "llm"),
    )


def _semantic_prompt(messages: list[ChatMessage]) -> str:
    payload = [
        {
            "chatseq": message.chatseq,
            "role": message.role,
            "name": message.display_name,
            "content": message.content,
        }
        for message in messages[-12:]
    ]
    return (
        "请分析企业微信外部群聊天，返回 JSON："
        "has_project_opportunity, has_information_gap, has_vendor_readiness, "
        "has_timing_signal, summary, evidence_chatseqs。只返回 JSON。\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def _explanation_prompt(messages: list[ChatMessage], decision: Decision) -> str:
    payload = [
        {
            "chatseq": message.chatseq,
            "role": message.role,
            "name": message.display_name,
            "content": message.content,
        }
        for message in messages[-10:]
    ]
    return (
        "请用业务方容易理解的中文解释这个 AI 介入判断。"
        "需要说明为什么介入或不介入，引用关键证据，但不要新增表单链接或承诺。\n"
        f"决策：{json.dumps(decision.to_dict(), ensure_ascii=False)}\n"
        f"聊天：{json.dumps(payload, ensure_ascii=False)}"
    )
