# Stage 4 Tranches

## Tranche 1

加入 `.env` 支持，使用 `python-dotenv` 读取本地 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL` 和可选 `DEEPSEEK_BASE_URL`。已有环境变量和 Streamlit Secrets 优先，不被 `.env` 覆盖。

## Tranche 2

增强话术自然化能力。规则仍负责决定动作、证据和表单；LLM 只润色候选话术，失败时返回规则 fallback。

## Tranche 3

增加复杂语义理解辅助，输出结构化 semantic signals：项目机会、信息缺口、资料意愿、时间窗口、摘要和证据 `chatseq`。

## Tranche 4

增加复盘解释增强，把证据消息、规则判断和业务语境合成为更适合 PM/业务方阅读的解释。

## Tranche 5

增加 LLM 相关测试和评估样本，确认 Stage 2 批量稳定性报告不回退。后续可用产品/干系人语言更新 `status_quo_for_PM.md`。

## LLM 增强复盘

- 新增 `data/llm_evaluation_cases.json`，独立评估话术自然化、复杂语义理解和复盘解释。
- 新增 `data/llm_snapshots/`，保存真实 DeepSeek 输出快照，默认离线复盘。
- 新增 CLI：`python -m chat_record_analyzer.llm_evaluate data/llm_evaluation_cases.json --source snapshots --format markdown`。
- 可用 `--source deepseek --write-snapshots` 显式刷新快照。

## Stage 4 通过线

- 无 `.env` 或无 key 时仍可稳定使用 Mock。
- DeepSeek 配置存在时可显式启用。
- LLM 失败、超时或输出不可解析时不影响规则决策。
- Stage 2 批量评估仍为 PASS。
- LLM 增强报告达到通过线：语义信号、解释覆盖、话术关键词/克制性均 >= 80%。

## 当前 baseline

- Stage 2 批量稳定性报告：17/17 PASS。
- Stage 4 LLM 增强复盘：10/10 PASS。
- 当前快照指标：语义信号 100%，解释覆盖 100%，话术关键词/克制性 100%。
- Streamlit 已包含四个视图：单点分析、群聊回放、批量稳定性报告、LLM 增强复盘。
