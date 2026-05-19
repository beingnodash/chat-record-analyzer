# AGENTS.md

## 项目目标

本项目是一个 stand-alone POC，用于验证 AI agent 是否能从企业微信外部群聊天存档文本中稳定判断：

- 是否应该介入群聊
- 为什么介入
- 应该生成什么话术
- 是否应该选择并发送配置好的表单 URL

当前不对接企业微信接口，不构建真实表单系统，不处理实时同步频率。

## 技术栈

- Python 3.12+
- Streamlit
- uv
- 默认离线可跑，使用 mock/规则路径
- 后续可通过 DeepSeek OpenAI-compatible API 接入真实 LLM

## 当前阶段

项目按 `Concepts -> PRD -> Blueprint -> Implementation Stages` 推进。

当前已完成 Stage 1 baseline：

- canonical JSONL 聊天文本格式
- 表单 catalog
- 聊天解析
- 轻量决策引擎
- rubric 评分
- CLI
- Streamlit UI
- 单元测试

当前 Stage 2 baseline 已建立：

- 12 个海外基建样本
- 17 个批量评估点
- Streamlit 批量稳定性报告
- CLI/模块化批量评估入口

当前 Stage 3 baseline 已建立：

- Streamlit 三视图：单点分析、群聊回放、批量稳定性报告
- 每个 `chatseq` 的 prefix 决策时间线
- 表单卡片预览
- DeepSeek/Mock 话术生成开关，默认 Mock

当前 Stage 4 目标：

- 使用 `.env` 支持本地 DeepSeek 配置
- 让 LLM 受控增强话术、语义理解和复盘解释
- 保持规则决策、表单 catalog 和批量评估作为安全边界

## 工程约束

- 优先保持实现轻量、可解释、易测试。
- 不确定时默认不介入，避免 bot 过度打扰。
- 表单来自 `data/forms.json`，不要让模型自由生成真实表单 URL。
- 输入样本优先使用 append-only JSONL，每行一条带元数据消息。
- 不提交真实 API key；DeepSeek 只通过环境变量或 Streamlit Secrets 启用。
- LLM 可增强表达和解释，但不可越权决定是否发送或生成真实表单链接。
- LLM 失败、超时或输出不可解析时，必须回退到规则/Mock 结果。
- 新功能应优先补测试，再实现。
- 修改决策逻辑时，必须确认泰国港口照明 golden case 仍通过。

## 常用命令

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m chat_record_analyzer data/samples/thailand_port_lighting.jsonl --chatseq 6
PYTHONPATH=src python3 -m chat_record_analyzer.evaluate data/evaluation_cases.json --format markdown
uv run streamlit run app/streamlit_app.py
```
