---
name: zh-implement
description: Implement an authorized, bounded development change in a task worktree and return concrete changes, checks, and acceptance coverage. Use existing verification proportionate to risk; TDD is optional.
---

# 实现任务

接收目标、已授权范围、验收条件、项目规则、任务 worktree/分支/基线和依赖。独立调用时先明确这些必要信息并按 [工作区规则](../zh/references/workspaces.md) 建立任务 worktree；是否提交或交付取决于本次授权，不能隐式启动整套开发和合并。

收到外层交接后直接处理分配的范围，不启动另一套控制器、不重复确认。小任务可由主会话执行；需要委派时按 [委派规则](../zh/references/delegation.md)，保留执行边界。

开始前确定如何证明完成，复用项目既有工具链和相关规范。逐个完成可验证步骤，观察反馈再调整。测试方式和何时编写测试按 [验证策略](references/verification.md) 判断，不强制 TDD、无意义覆盖率或每次全量测试。

失败区分实现问题、既有失败和环境阻塞。范围内修复并重跑受影响检查；相同失败无新证据先诊断。发现改变需求或架构取舍的必要性时回传外层修订计划，不静默扩大实现。

结果回传：实际改动、检查命令/输出/环境、逐条件覆盖、未运行或失败、阻塞/偏差、带来源的新发现。记录规则见 [任务交接](../zh/references/records.md)。结果必须对应实际候选版本；“实现完成”不是独立验收。候选交 [zh-review](../zh-review/SKILL.md)；只执行本步骤的委派在回传后结束，由外层安排验收和交付。
