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

下一阶段重点是 Stage 3：

- 低保真群聊回放
- 每个 `chatseq` 的决策时间线
- 表单卡片样式预览

## 工程约束

- 优先保持实现轻量、可解释、易测试。
- 不确定时默认不介入，避免 bot 过度打扰。
- 表单来自 `data/forms.json`，不要让模型自由生成真实表单 URL。
- 输入样本优先使用 append-only JSONL，每行一条带元数据消息。
- 新功能应优先补测试，再实现。
- 修改决策逻辑时，必须确认泰国港口照明 golden case 仍通过。

## 常用命令

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m chat_record_analyzer data/samples/thailand_port_lighting.jsonl --chatseq 6
PYTHONPATH=src python3 -m chat_record_analyzer.evaluate data/evaluation_cases.json --format markdown
uv run streamlit run app/streamlit_app.py
```
