from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chat_record_analyzer.agent import analyze_session
from chat_record_analyzer.evaluate import DEFAULT_MANIFEST_PATH, evaluate_manifest, render_markdown, result_rows
from chat_record_analyzer.forms import FormCatalog
from chat_record_analyzer.models import ChatMessage, Decision
from chat_record_analyzer.parser import load_messages, messages_until, parse_jsonl
from chat_record_analyzer.replay import FormCardView, ReplayItem, build_replay_timeline
from chat_record_analyzer.runtime import select_draft_client


SAMPLE_DIR = ROOT / "data" / "samples"


def main() -> None:
    st.set_page_config(page_title="企微群聊 AI 介入决策 POC", layout="wide")
    st.title("企微群聊 AI 介入决策 POC")

    form_catalog = FormCatalog.load()
    messages, sample_name, show_json, draft_client = _sidebar_inputs()

    single_tab, replay_tab, batch_tab = st.tabs(["单点分析", "群聊回放", "批量稳定性报告"])
    with single_tab:
        _render_single_analysis(messages, sample_name, form_catalog, draft_client, show_json)
    with replay_tab:
        _render_chat_replay(messages, sample_name, form_catalog, draft_client, show_json)
    with batch_tab:
        _render_batch_report()


def _sidebar_inputs():
    sample_paths = sorted(SAMPLE_DIR.glob("*.jsonl"))
    sample_names = [path.name for path in sample_paths]
    with st.sidebar:
        st.header("输入")
        selected_sample = st.selectbox(
            "选择样本",
            sample_names,
            index=sample_names.index("thailand_port_lighting.jsonl") if "thailand_port_lighting.jsonl" in sample_names else 0,
        )
        uploaded = st.file_uploader("或上传 JSONL", type=["jsonl", "txt"])
        mode_label = st.radio("话术生成", ["Mock", "DeepSeek"], horizontal=True)
        show_json = st.checkbox("显示原始 JSON", value=True)

    _sync_streamlit_secrets()
    selection = select_draft_client("deepseek" if mode_label == "DeepSeek" else "mock")
    if selection.using_fallback:
        st.sidebar.warning(selection.status_message)
    else:
        st.sidebar.info(selection.status_message)

    if uploaded:
        return parse_jsonl(uploaded.read().decode("utf-8")), uploaded.name, show_json, selection.client
    return load_messages(SAMPLE_DIR / selected_sample), selected_sample, show_json, selection.client


def _sync_streamlit_secrets() -> None:
    try:
        for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_BASE_URL"):
            if key not in os.environ and key in st.secrets:
                os.environ[key] = str(st.secrets[key])
    except Exception:
        return


def _render_single_analysis(
    messages: list[ChatMessage],
    sample_name: str,
    form_catalog: FormCatalog,
    draft_client,
    show_json: bool,
) -> None:
    st.subheader(sample_name)
    max_seq = max(message.chatseq for message in messages)
    chatseq = st.slider("分析到 chatseq", min_value=1, max_value=max_seq, value=max_seq, key="single-chatseq")
    visible_messages = messages_until(messages, chatseq)
    decision = analyze_session(visible_messages, form_catalog=form_catalog, draft_client=draft_client)

    left, right = st.columns([1.05, 1])
    with left:
        st.subheader("群聊回放")
        for message in visible_messages:
            _render_chat_message(message, form_catalog)
    with right:
        _render_decision_panel(decision, form_catalog, show_json)


def _render_chat_replay(
    messages: list[ChatMessage],
    sample_name: str,
    form_catalog: FormCatalog,
    draft_client,
    show_json: bool,
) -> None:
    st.subheader(sample_name)
    timeline = build_replay_timeline(messages, form_catalog=form_catalog, draft_client=draft_client)
    selected_seq = st.slider(
        "回放到 chatseq",
        min_value=timeline[0].chatseq,
        max_value=timeline[-1].chatseq,
        value=timeline[-1].chatseq,
        key="replay-chatseq",
    )
    current = next(item for item in timeline if item.chatseq == selected_seq)
    visible_items = [item for item in timeline if item.chatseq <= selected_seq]

    left, right = st.columns([1.08, 1])
    with left:
        st.subheader("企微低保真回放")
        for item in visible_items:
            _render_chat_message(item.message, form_catalog)
    with right:
        st.subheader(f"AI 决策｜chatseq {selected_seq}")
        _render_timeline_status(timeline, selected_seq)
        _render_decision_panel(current.decision, form_catalog, show_json)


def _render_batch_report() -> None:
    report = evaluate_manifest(DEFAULT_MANIFEST_PATH)
    summary = report.summary
    st.subheader("Stage 2 批量稳定性报告")
    metric_cols = st.columns(4)
    metric_cols[0].metric("整体状态", "PASS" if summary.threshold_passed else "FAIL")
    metric_cols[1].metric("总体准确率", f"{summary.accuracy:.2%}", f"{summary.passed_cases}/{summary.total_cases}")
    metric_cols[2].metric("正例召回", f"{summary.positive_recall:.2%}")
    metric_cols[3].metric("误触发率", f"{summary.false_trigger_rate:.2%}")

    st.dataframe(result_rows(report), use_container_width=True, hide_index=True)
    failed = [result for result in report.results if not result.passed]
    if failed:
        st.subheader("失败复盘")
        for result in failed:
            with st.expander(result.case.case_id):
                st.write("失败项：", ", ".join(result.failures))
                st.json(result.to_dict())
    else:
        st.success("当前 manifest 中无失败用例。")

    st.download_button(
        "下载 Markdown 报告",
        render_markdown(report),
        file_name="stage-2-stability-report.md",
        mime="text/markdown",
    )


def _render_chat_message(message: ChatMessage, form_catalog: FormCatalog) -> None:
    label = f"{message.chatseq}｜{message.display_name}｜{message.role}｜{message.timestamp}"
    avatar_type = "assistant" if message.role == "bot" else "user"
    with st.chat_message(avatar_type):
        st.caption(label)
        card = _existing_card(message, form_catalog)
        if card:
            _render_form_card(card)
        else:
            st.write(message.content)


def _render_decision_panel(decision: Decision, form_catalog: FormCatalog, show_json: bool) -> None:
    st.metric("是否建议发送", "是" if decision.should_send else "否", f"confidence {decision.confidence:.2f}")
    st.write(f"动作类型：`{decision.action_type}`")
    st.write(f"判断依据：{decision.rationale}")
    if decision.evidence_chatseqs:
        st.write("证据 chatseq：", ", ".join(str(seq) for seq in decision.evidence_chatseqs))
    if decision.draft_message:
        st.text_area("候选话术", decision.draft_message, height=150)
    candidate_card = _candidate_card(decision, form_catalog)
    if candidate_card:
        _render_form_card(candidate_card)

    st.subheader("Rubric")
    st.json(decision.rubric_scores.to_dict())
    if show_json:
        st.subheader("结构化输出")
        st.json(decision.to_dict())


def _render_timeline_status(timeline: list[ReplayItem], selected_seq: int) -> None:
    rows = [
        {
            "chatseq": item.chatseq,
            "sender": item.message.display_name,
            "send": item.decision.should_send,
            "action": item.decision.action_type,
            "confidence": item.decision.confidence,
        }
        for item in timeline
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    trigger_count = sum(1 for item in timeline if item.chatseq <= selected_seq and item.decision.should_send)
    st.caption(f"已回放触发点：{trigger_count}")


def _render_form_card(card: FormCardView) -> None:
    st.markdown(
        f"""
<div style="border:1px solid #d9dde3;border-radius:8px;padding:14px 16px;margin:8px 0;background:#ffffff">
  <div style="font-size:13px;color:#0a8f62;margin-bottom:6px">【{card.badge}】</div>
  <div style="font-weight:700;font-size:17px;margin-bottom:8px">{card.title}</div>
  <div style="white-space:pre-wrap;color:#3f4652;line-height:1.5">{card.description}</div>
  <div style="margin-top:10px;color:#0a8f62">{card.url}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _candidate_card(decision: Decision, form_catalog: FormCatalog) -> FormCardView | None:
    from chat_record_analyzer.replay import card_from_decision

    return card_from_decision(decision, form_catalog)


def _existing_card(message: ChatMessage, form_catalog: FormCatalog) -> FormCardView | None:
    from chat_record_analyzer.replay import card_from_message

    return card_from_message(message, form_catalog)


if __name__ == "__main__":
    main()
