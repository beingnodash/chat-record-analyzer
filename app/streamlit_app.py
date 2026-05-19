from __future__ import annotations

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
from chat_record_analyzer.parser import load_messages, messages_until, parse_jsonl


SAMPLE_DIR = ROOT / "data" / "samples"


st.set_page_config(page_title="企微群聊 AI 介入决策 POC", layout="wide")
st.title("企微群聊 AI 介入决策 POC")

sample_paths = sorted(SAMPLE_DIR.glob("*.jsonl"))
sample_names = [path.name for path in sample_paths]
single_tab, batch_tab = st.tabs(["单会话分析", "批量稳定性报告"])

with single_tab:
    with st.sidebar:
        st.header("输入")
        selected_sample = st.selectbox(
            "选择样本",
            sample_names,
            index=sample_names.index("thailand_port_lighting.jsonl") if "thailand_port_lighting.jsonl" in sample_names else 0,
        )
        uploaded = st.file_uploader("或上传 JSONL", type=["jsonl", "txt"])
        show_json = st.checkbox("显示原始 JSON", value=True)

    if uploaded:
        messages = parse_jsonl(uploaded.read().decode("utf-8"))
    else:
        messages = load_messages(SAMPLE_DIR / selected_sample)

    max_seq = max(message.chatseq for message in messages)
    chatseq = st.slider("分析到 chatseq", min_value=1, max_value=max_seq, value=max_seq)
    visible_messages = messages_until(messages, chatseq)
    decision = analyze_session(visible_messages, form_catalog=FormCatalog.load())

    left, right = st.columns([1.05, 1])

    with left:
        st.subheader("群聊回放")
        for message in visible_messages:
            label = f"{message.chatseq}｜{message.display_name}｜{message.role}｜{message.timestamp}"
            with st.chat_message("assistant" if message.role == "bot" else "user"):
                st.caption(label)
                st.write(message.content)

    with right:
        st.subheader("AI 决策")
        st.metric("是否建议发送", "是" if decision.should_send else "否", f"confidence {decision.confidence:.2f}")
        st.write(f"动作类型：`{decision.action_type}`")
        st.write(f"判断依据：{decision.rationale}")
        if decision.evidence_chatseqs:
            st.write("证据 chatseq：", ", ".join(str(seq) for seq in decision.evidence_chatseqs))
        if decision.draft_message:
            st.text_area("候选话术", decision.draft_message, height=180)
        if decision.form_url:
            st.link_button("打开候选表单", decision.form_url)

        st.subheader("Rubric")
        st.json(decision.rubric_scores.to_dict())
        if show_json:
            st.subheader("结构化输出")
            st.json(decision.to_dict())

with batch_tab:
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
