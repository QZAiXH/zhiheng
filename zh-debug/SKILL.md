---
name: zh-debug
description: Diagnose failures and performance regressions using symptom-specific reproduction, falsifiable hypotheses, and regression evidence; implement a fix only within the requested scope.
---

# 诊断与修复

输入是原始症状、期望、相关环境与授权范围。单纯诊断可以阅读、复现和缩小问题，不先建开发 worktree；实际改产品代码前按 [工作区规则](../zh/references/workspaces.md) 建立任务工作区。独立调用不隐式获得提交或合并权限。

先构造能捕获用户所述症状的反馈：现有失败测试、真实请求、带固定输入的 CLI、界面操作或重放记录均可。记录已运行命令、实际输出和环境，避免把“没有崩溃”当作症状消失。性能问题先测基线；间歇问题记录频率和采样条件，不伪称确定性。

缩小仍能保留症状的场景。按证据提出可证伪假设，明确哪个观察能区分原因；按需要比较多个解释，不固定要求假设数量。用针对性探针验证，避免同时改变多项条件造成因果混淆。

复现困难时说明已经尝试什么及缺失证据，可继续有依据的只读分析，但把结论标为假设。需要额外环境、数据或外部影响时按实际授权处理，不无限循环，也不凭推测宣称根因已确认。

在范围内修复，并按 [验证策略](../zh-implement/references/verification.md) 检查原始场景和适当回归，保留既有接口契约；无关既有失败只归因记录，本次回归可修。复杂修复交执行子 agent，主会话只调查、协调和核证；缺委派能力按 [委派规则](../zh/references/delegation.md) 处理。清除本任务临时探针，保留需要交接的证据；输出原始故障、根因依据、实际修复、回归结果与限制。发现涉及范围外修复或新业务取舍时交外层说明证据和影响并修订计划。按 [记录规则](../zh/references/records.md) 回传候选发现；修复后的独立验收由 [zh-review](../zh-review/SKILL.md) 完成。
