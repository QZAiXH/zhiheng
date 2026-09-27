---
name: zh
description: Coordinate development from scoped planning through worktree implementation, independent acceptance, local merge, and durable recovery. Use for end-to-end bug fixes, features, and refactors; discussion and routine local operations stay within their requested scope.
---

# zh：开发协作入口

按任务的不确定性、影响、依赖和可验证性决定流程深度。只读调查、启动已有项目、安装已声明依赖、运行配置和准备 mock 数据直接按授权处理；写临时文件本身不意味着产品开发。混合请求仅让实际开发部分进入以下流程。

用户请求和项目规范优先。沿用对话中已建立的范围、目标分支、模型偏好和授权，不要求固定确认用语、执行 JSON 或授权令牌。技能切换不代表模型或会话切换。这里管理外层进度；子技能只处理收到的任务，不另起外层流程。

## 从请求到交付

1. 读取适用 `AGENTS.md`、已有 `.zhiheng/PROJECT.md` 和与任务相关的决定。上下文不足时使用 [zh-context](../zh-context/SKILL.md)，不默认加载全套技能和历史。
2. 使用 [zh-plan](../zh-plan/SKILL.md) 调查并在对话直接展示相称的计划。小而明确且已授权的任务几行后继续；复杂或有关键未决事项时先解决并等待必要确认。用户已要求实施同一计划就继续，修订请求本身不是执行授权。
3. 开发前遵循 [工作区规则](references/workspaces.md) 确定目标分支及任务 worktree。非 Git 项目先明确建立或选择仓库。按 [任务记录](references/records.md) 保存范围、验收和恢复指针。
4. 使用 [zh-implement](../zh-implement/SKILL.md) 或 [zh-debug](../zh-debug/SKILL.md) 实施。小任务主会话执行；复杂任务按独立可验证的步骤委派，只推进依赖已满足的步骤。委派前按 [模型与上下文](references/delegation.md) 推荐实际可用配置，并将范围、原始材料和验收条件交给新上下文。
5. 使用 [zh-review](../zh-review/SKILL.md) 建立真实独立验收。未通过或无法验证时保留任务现场，反馈具体条件和证据。范围内继续修复并复查受影响部分；同样失败且无新证据时先诊断。返工可复用适用的执行会话；上下文混乱或边界改变再换会话。
6. 有效验收通过后使用 [zh-finish](../zh-finish/SKILL.md) 按本任务已约定的交付范围提交、本地合并、整合验证和清理。远端操作需单独的已有授权。最后报告实际结果和未完成事项。

执行期间更新已完成、进行中和阻塞步骤。范围、架构取舍或验收发生实质变化时展示变化、原因、影响，并只对需要的新决定取得确认。保留此前仍有效的决定；用户状态询问和会话恢复不会替换原任务。

没有独立新会话能力时，如实报告独立验收受阻，保留候选和证据，不能自行改称验收通过并交付。无须 Bubblewrap、快照回写、钩子或强制固定模型；宿主权限照常适用。

维护安装集合时读 [来源与改写](references/provenance.md)。Git/记录辅助工具按需读 [工具用法](references/task-tools.md)；它们仅检查机械一致性，不能证明自然语言授权或语义正确性。
