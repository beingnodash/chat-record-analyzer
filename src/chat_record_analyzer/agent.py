from __future__ import annotations

from dataclasses import dataclass

from .forms import FormCatalog
from .llm import DraftClient, MockDraftClient
from .models import ChatMessage, Decision, FormDefinition
from .rubric import evaluate_rubric


PROJECT_KEYWORDS = ["项目", "港口", "码头", "堆场", "总包", "分包", "拆包", "业主", "海外", "工程", "基建"]
NEED_KEYWORDS = ["需求", "方案", "清单", "参数", "案例", "支持范围", "产品", "技术", "测算"]
VENDOR_CAPABILITY_KEYWORDS = [
    "方案",
    "产品",
    "案例",
    "高杆灯",
    "智能配电",
    "远程运维",
    "节能测算",
    "供应",
    "调试",
    "团队",
]
READINESS_KEYWORDS = ["整理", "提交", "发给", "提供", "更新", "资料", "可以先"]
TIMELINE_KEYWORDS = ["启动会", "7月", "后续", "阶段", "明确", "讨论", "推进", "跟进"]
FORM_MARKERS = ["表单", "立即填写", "https://example.com/form"]


@dataclass(frozen=True)
class Signals:
    project_seq: int | None
    vendor_interest_seq: int | None
    vendor_readiness_seq: int | None
    owner_timeline_seq: int | None
    bot_info_request_seq: int | None
    form_sent_seq: int | None
    matched_text: str


def analyze_session(
    messages: list[ChatMessage],
    *,
    form_catalog: FormCatalog | None = None,
    draft_client: DraftClient | None = None,
) -> Decision:
    catalog = form_catalog or FormCatalog.load()
    client = draft_client or MockDraftClient()
    if not messages:
        return _no_send([], "没有可分析的聊天消息。")

    signals = _extract_signals(messages)
    last = messages[-1]

    if signals.form_sent_seq is not None:
        return _no_send(messages, "会话中已经发送过表单，避免重复打扰。")

    if last.role in {"bot", "internal_user"}:
        return _no_send(messages, "最新消息来自机器人或内部用户，不需要 AI 再次介入。")

    if _is_acknowledgement_only(last.content):
        return _no_send(messages, "最新消息主要是确认或寒暄，没有新的商机信息缺口。")

    if _should_send_form(last, signals):
        form = catalog.best_match(signals.matched_text)
        matched_count = _count_keyword_hits(signals.matched_text, form.keywords)
        evidence = _compact_evidence(
            [signals.project_seq, signals.vendor_interest_seq, signals.bot_info_request_seq, signals.vendor_readiness_seq]
        )
        fallback = _build_form_message(last, form)
        prompt = f"请基于群聊上下文生成一段发送表单前的话术，保留表单标题和提交目的。候选话术：{fallback}"
        draft = client.polish(prompt, fallback)
        rubric = evaluate_rubric(
            messages,
            should_send=True,
            action_type="send_form",
            evidence_chatseqs=evidence,
            form_keywords_matched=matched_count,
        )
        return Decision(
            should_send=True,
            action_type="send_form",
            confidence=0.9,
            rubric_scores=rubric,
            rationale="外部供应方已明确有相关方案、产品能力和提交资料意愿，适合选择配置表单采集结构化信息。",
            evidence_chatseqs=evidence,
            draft_message=draft,
            form_id=form.form_id,
            form_url=form.url,
        )

    if _should_ask_for_info(last, signals):
        evidence = _compact_evidence([signals.project_seq, signals.vendor_interest_seq, signals.owner_timeline_seq])
        target = _latest_vendor_name(messages) or "您"
        fallback = (
            f"{target}，您这边方便的话，可以先把相关解决方案、产品清单和海外项目案例发到群里或提交给我们。"
            "我们可以先帮您整理需求点，后续持续跟进项目拆包和对接进展。"
        )
        prompt = f"请把这段企业微信群聊介入话术润色得更自然，但保持克制和业务导向：{fallback}"
        draft = client.polish(prompt, fallback)
        rubric = evaluate_rubric(messages, should_send=True, action_type="ask_for_info", evidence_chatseqs=evidence)
        return Decision(
            should_send=True,
            action_type="ask_for_info",
            confidence=0.82,
            rubric_scores=rubric,
            rationale="项目方透露后续时间点和不确定事项，供应方已有明确关注点，此时适合轻量引导其补充方案资料。",
            evidence_chatseqs=evidence,
            draft_message=draft,
        )

    return _no_send(messages, "未同时看到明确项目机会、供应方能力表达和可采集的信息缺口。")


def _extract_signals(messages: list[ChatMessage]) -> Signals:
    project_seq = None
    vendor_interest_seq = None
    vendor_readiness_seq = None
    owner_timeline_seq = None
    bot_info_request_seq = None
    form_sent_seq = None
    text_parts: list[str] = []

    for message in messages:
        content = message.content
        text_parts.append(content)
        if _contains_any(content, PROJECT_KEYWORDS):
            project_seq = project_seq or message.chatseq
        if message.role == "external_vendor" and _contains_any(content, VENDOR_CAPABILITY_KEYWORDS):
            vendor_interest_seq = message.chatseq
        if message.role == "external_vendor" and _contains_any(content, READINESS_KEYWORDS):
            vendor_readiness_seq = message.chatseq
        if message.role == "external_owner" and _contains_any(content, TIMELINE_KEYWORDS):
            owner_timeline_seq = message.chatseq
        if message.role == "bot" and _contains_any(content, ["产品清单", "项目案例", "提交给我们", "解决方案"]):
            bot_info_request_seq = message.chatseq
        if message.role == "bot" and _contains_any(content, FORM_MARKERS):
            form_sent_seq = message.chatseq

    return Signals(
        project_seq=project_seq,
        vendor_interest_seq=vendor_interest_seq,
        vendor_readiness_seq=vendor_readiness_seq,
        owner_timeline_seq=owner_timeline_seq,
        bot_info_request_seq=bot_info_request_seq,
        form_sent_seq=form_sent_seq,
        matched_text="\n".join(text_parts),
    )


def _should_send_form(last: ChatMessage, signals: Signals) -> bool:
    return (
        last.role == "external_vendor"
        and signals.project_seq is not None
        and signals.vendor_readiness_seq == last.chatseq
        and signals.bot_info_request_seq is not None
        and _contains_any(last.content, NEED_KEYWORDS + READINESS_KEYWORDS)
    )


def _should_ask_for_info(last: ChatMessage, signals: Signals) -> bool:
    return (
        last.role == "external_owner"
        and signals.project_seq is not None
        and signals.vendor_interest_seq is not None
        and signals.owner_timeline_seq == last.chatseq
    )


def _no_send(messages: list[ChatMessage], rationale: str) -> Decision:
    rubric = evaluate_rubric(messages, should_send=False, action_type="none", evidence_chatseqs=[])
    return Decision(
        should_send=False,
        action_type="none",
        confidence=0.72,
        rubric_scores=rubric,
        rationale=rationale,
    )


def _build_form_message(last: ChatMessage, form: FormDefinition) -> str:
    return (
        f"{last.display_name}，感谢您愿意同步资料。为方便后续整理和跟进，您可以先通过这个表单提交：\n"
        f"【{form.title}】\n{form.description}\n{form.url}"
    )


def _latest_vendor_name(messages: list[ChatMessage]) -> str | None:
    for message in reversed(messages):
        if message.role == "external_vendor":
            return message.display_name
    return None


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text.lower() for keyword in keywords)


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword.lower() in text.lower())


def _compact_evidence(values: list[int | None]) -> list[int]:
    result: list[int] = []
    for value in values:
        if value is not None and value not in result:
            result.append(value)
    return result


def _is_acknowledgement_only(content: str) -> bool:
    stripped = content.strip()
    ack_terms = ["好的", "没问题", "收到", "谢谢", "感谢", "期待"]
    has_ack = any(term in stripped for term in ack_terms)
    has_new_need = _contains_any(stripped, VENDOR_CAPABILITY_KEYWORDS + PROJECT_KEYWORDS + NEED_KEYWORDS)
    return has_ack and not has_new_need and len(stripped) <= 35
