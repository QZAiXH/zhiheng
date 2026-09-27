---
name: zh-implement
description: Implement an authorized, bounded development change in a task worktree and return concrete changes, checks, and acceptance coverage. Use existing verification proportionate to risk; TDD is optional.
---

# 实现任务

接收目标、已授权范围、验收条件、项目规则、任务 worktree/分支/基线和依赖。独立调用时先明确这些必要信息并按 [工作区规则](../zh/references/workspaces.md) 建立任务 worktree；是否提交或交付取决于本次授权，不能隐式启动整套开发和合并。

收到外层交接后直接处理分配的范围，不启动另一套控制器、不重复确认。小任务可由主会话执行；复杂任务由执行子 agent 实施，主会话按 [委派规则](../zh/references/delegation.md) 协调与核证，不代做开发、修复或实现测试。

页面与交互任务按需读 [前端预览与验收](references/frontend-preview.md)，先区分当前交接是原型还是正式实现。该参考统一维护预览适用范围、简化条件、用户确认、浏览器检查及恢复证据。原型回传不能写成正式功能完成；进入正式实现需有对应设计依据和开发授权。

开始前确定如何证明完成，复用项目既有工具链和相关规范。逐个完成可验证步骤，观察反馈再调整。测试方式和何时编写测试按 [验证策略](references/verification.md) 判断，不强制 TDD、无意义覆盖率或每次全量测试。

失败区分本次引入的问题、无关既有失败和环境阻塞；按 [验证策略](references/verification.md) 归因。范围内修复本次回归并重跑受影响检查；无关既有失败记录证据，不因测试变红顺便修复。既有公开接口的状态码、错误 reason、授权与行为契约应保留，不能为统一错误类型而修改旧断言消化差异。确需范围外变更时回传外层说明证据与影响，取得所需决定，不静默扩大实现；相同失败无新证据先诊断。

结果回传：实际改动、检查命令/输出/环境、逐条件覆盖、未运行或失败、阻塞/偏差、带来源的新发现。记录规则见 [任务交接](../zh/references/records.md)。结果必须对应实际候选版本；“实现完成”不是独立验收。候选交 [zh-review](../zh-review/SKILL.md)；只执行本步骤的委派在回传后结束，由外层安排验收和交付。
