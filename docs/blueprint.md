# Blueprint

## Architecture

POC 采用轻量混合架构：

- Parser：读取 canonical JSONL，校验基础字段。
- Session State：按 `chatseq` 截取 append-only 会话。
- Decision Engine：用规则提取商机、需求、能力、资料意愿和已发送动作。
- Form Catalog：从配置文件选择匹配表单。
- Rubric Evaluator：对触发时机、证据、价值、打扰风险、表单匹配打分。
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

### Stage 3: 低保真群聊回放

最多 5 个 tranches：

1. Streamlit chatbot 回放。
2. 每个 `chatseq` 的决策时间线。
3. 表单卡片样式预览。
4. DeepSeek API 真实调用开关。
5. 演示部署配置。
