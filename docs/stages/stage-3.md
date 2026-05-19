# Stage 3 Tranches

## Tranche 1

新增回放 view-model 层，按每个 `chatseq` 生成 prefix 决策时间线、候选 bot 消息和表单卡片数据。

## Tranche 2

将 Streamlit 主界面整理为三个视图：单点分析、群聊回放、批量稳定性报告。

## Tranche 3

实现表单卡片预览和 DeepSeek/Mock 话术生成开关。无 `DEEPSEEK_API_KEY` 时自动回退 Mock。

## Tranche 4

补充 Stage 3 回归测试，覆盖 timeline、关键触发点、卡片 view-model 和 DeepSeek fallback。

## Tranche 5

补充 README、AGENTS 和 Streamlit Cloud 配置说明。

## Stage 3 Baseline

- 低保真群聊回放已支持逐 `chatseq` 播放。
- 决策时间线可展示每条消息后的 action、confidence 和是否建议发送。
- 表单卡片只来自 `data/forms.json` 或存档中的 card 消息。
- DeepSeek 仅在显式选择且环境变量存在时启用。
