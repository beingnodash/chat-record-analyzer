# Stage 2 Tranches

## Tranche 1

定义 `data/evaluation_cases.json`，为每个评估点声明样本、`chatseq`、期望动作、表单和话术关键词。

## Tranche 2

将样本集扩充到 12 个海外基建场景，覆盖港口、铁路、能源、水务、物流、园区、桥梁和隧道。

## Tranche 3

实现批量评估模块 `chat_record_analyzer.evaluate`，计算总体准确率、正例召回、误触发率、动作准确率、表单准确率和话术关键词匹配率。

## Tranche 4

在 Streamlit 中新增“批量稳定性报告”视图，展示指标、评估明细、失败复盘和 Markdown 报告下载。

## Tranche 5

补充回归测试并建立当前 baseline：17 个评估点全部通过，整体状态 PASS。

## Stage 2 通过线

- 总体准确率 >= 80%
- 正例召回 >= 80%
- 误触发率 <= 20%

