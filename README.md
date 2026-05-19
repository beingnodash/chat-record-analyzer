# 企业微信群聊 AI 介入决策 POC

这是一个 stand-alone `python + streamlit + uv` POC，用来验证 AI 侧能否从 append-only 企业微信聊天存档文本中稳定判断：

- 是否应该介入群聊
- 为什么介入
- 介入话术是什么
- 是否应该选择并发送配置好的表单 URL

默认离线可运行，使用规则与 Mock LLM 风格的可解释决策。配置 `DEEPSEEK_API_KEY` 后，可在 Streamlit 中显式切换到 DeepSeek OpenAI-compatible API 润色话术。

## 快速开始

```bash
uv sync --extra dev
uv run python -m unittest discover -s tests
uv run chat-record-analyzer data/samples/thailand_port_lighting.jsonl --chatseq 6
uv run chat-record-analyzer data/samples/thailand_port_lighting.jsonl --chatseq 6 --draft-mode deepseek
uv run python -m chat_record_analyzer.evaluate data/evaluation_cases.json --format markdown
uv run streamlit run app/streamlit_app.py
```

如果不想安装依赖，核心测试也可以直接运行：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m chat_record_analyzer data/samples/thailand_port_lighting.jsonl --chatseq 6
PYTHONPATH=src python3 -m chat_record_analyzer.evaluate data/evaluation_cases.json --format markdown
```

## DeepSeek 与 `.env`

本地开发可在项目根目录创建 `.env`：

```bash
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-chat
```

`.env` 不会覆盖已经存在的环境变量。Streamlit Cloud 仍建议使用 Secrets。

LLM 在本 POC 中是受控增强层：可以润色话术、辅助输出语义信号和业务解释，但不能绕过表单 catalog，也不能单独决定是否发送。

## Streamlit Cloud

部署入口：

```bash
streamlit run app/streamlit_app.py
```

必需依赖见 `requirements.txt`。默认不需要任何 secrets；如需启用 DeepSeek，在 Streamlit Cloud Secrets 中配置：

```toml
DEEPSEEK_API_KEY = "..."
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"
```

本地可参考 `.streamlit/secrets.toml.example`，不要提交真实 key。

## Canonical 输入格式

POC 使用 JSONL 作为 append-only 存档文本。每行是一条消息，包含：

```json
{"session_id":"wxext-thailand-port-001","chatseq":1,"timestamp":"2026-05-20T09:18:00+08:00","user_id":"bot-sisi","display_name":"思丝","role":"bot","org":"企微机器人","message_type":"card","content":"..."}
```

## 目录

- `app/streamlit_app.py`：业务演示 UI
- `src/chat_record_analyzer/replay.py`：低保真群聊回放 view-model
- `src/chat_record_analyzer/enhancements.py`：LLM 受控增强能力
- `src/chat_record_analyzer/`：解析、决策、表单选择、rubric 评估、CLI
- `data/forms.json`：表单 catalog
- `data/samples/`：多主题样本
- `data/evaluation_cases.json`：批量评估 manifest
- `docs/`：Concepts、PRD、Blueprint、Implementation Stages
- `tests/`：TDD 风格核心回归测试
