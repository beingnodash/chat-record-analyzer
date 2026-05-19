# Blueprint

## Architecture

POC 采用轻量混合架构：

- Parser：读取 canonical JSONL，校验基础字段。
- Session State：按 `chatseq` 截取 append-only 会话。
- Decision Engine：用规则提取商机、需求、能力、资料意愿和已发送动作。
- Form Catalog：从配置文件选择匹配表单。
- Rubric Evaluator：对触发时机、证据、价值、打扰风险、表单匹配打分。
- Env Loader：加载 `.env`、环境变量和 Streamlit Secrets，真实 key 不进入代码库。
- LLM Enhancement Layer：在规则决策之外增强话术、语义信号和业务解释。
- Prompt Contracts：LLM prompt 必须有明确输入、输出和 fallback，不允许模型自由生成真实表单 URL。
- Fallback Policy：DeepSeek 失败、超时或输出不可解析时，保留规则决策和 Mock 结果。
- LLM Snapshot Evaluation：真实 DeepSeek 输出可保存为固定快照，用人工 rubric 做离线复盘。
- Streamlit UI：展示聊天回放、结构化决策和评分。

## Stages

### Stage 1: 纯文本分析

最多 5 个 tranches：

1. 项目骨架、docs、canonical JSONL 样本。
2. parser、models、form catalog。
3. decision engine 与 mock/规则决策。
4. rubric evaluator 与 CLI。
5. tests 与 Streamlit 第一版 UI。

### Stage 2: 拓展性样本

最多 5 个 tranches：

1. 增加海外基建多主题样本。
2. 增加短/中/长对话样本。
3. 增加不同角色数量样本。
4. 批量评估报告。
5. 回归阈值和失败样本复盘。

当前 Stage 2 baseline：

- 12 个海外基建场景。
- 17 个 manifest 评估点。
- 批量评估入口：`python -m chat_record_analyzer.evaluate data/evaluation_cases.json --format markdown`。
- 通过线：总体准确率 >= 80%，正例召回 >= 80%，误触发率 <= 20%。

### Stage 3: 低保真群聊回放

最多 5 个 tranches：

1. Streamlit chatbot 回放。
2. 每个 `chatseq` 的决策时间线。
3. 表单卡片样式预览。
4. DeepSeek API 真实调用开关。
5. 演示部署配置。

当前 Stage 3 baseline：

- Streamlit 三视图：单点分析、群聊回放、批量稳定性报告。
- 群聊回放按每个 `chatseq` 生成 prefix 决策时间线。
- 表单卡片预览基于 `data/forms.json` 和会话存档 card。
- DeepSeek 开关通过 `DEEPSEEK_API_KEY` 等环境变量启用，无 key 自动回退 Mock。

### Stage 4: LLM 受控增强

最多 5 个 tranches：

1. `.env` 支持与 DeepSeek 连通性验证。
2. 话术自然化增强，保留规则 fallback。
3. 复杂语义理解辅助，输出结构化 semantic signals。
4. 复盘解释增强，把证据、规则和 LLM 解读合成业务可读说明。
5. LLM 评估样本、回归测试和 PM 状态更新。

Stage 4 约束：

- LLM 可增强表达和解释，但不越权决定真实表单 URL。
- 核心发送决策仍需通过规则、表单 catalog 和批量评估约束。
- 所有 LLM 能力必须能在无 key 或调用失败时稳定回退。

当前 Stage 4 baseline：

- `.env`、环境变量和 Streamlit Secrets 均可用于 DeepSeek 配置，真实 key 不进入代码库。
- LLM 受控增强覆盖话术润色、semantic signals 和业务解释。
- LLM 增强评估集包含 10 个关键复盘点，默认读取固定 DeepSeek 快照。
- LLM 增强复盘入口：`python -m chat_record_analyzer.llm_evaluate data/llm_evaluation_cases.json --source snapshots --format markdown`。
- 当前快照 baseline：10/10 通过，语义信号、解释覆盖、话术关键词/克制性均为 100%。
