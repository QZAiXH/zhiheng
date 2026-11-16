---
name: zh
description: Coordinate a complete software development task, or continue, adjust, or resume work across stages; select executable slices and verify returned results and the local delivery target. For a standalone stage such as research, review, or acceptance, use the corresponding zh stage skill.
---

# Task Coordination

Find requirements and task records through the project's existing entry points. When ongoing tracking is needed and no convention exists, use the [task protocol](references/task-protocol.md) and [template](assets/templates/task.md) to create a local entry point in `docs/tasks/<task-id>/`. Before executing coordinated work, apply the [context isolation contract](references/host.md#context-isolation-contract). Brief implementation requests still need a separate execution context; a versioned compact dispatch/return can replace a full task tree. Read-only consultation and separately invoked stage skills keep their commissioned scope.

1. Confirm the effective requirements, applicable decisions, project facts, delivery target, and authorization. Identify blocking dependencies and the executable frontier of the current task. Refine only slices that can be handed off soon. When project information is insufficient, fill the gaps needed for the current scope using the [knowledge rules](references/knowledge.md).
2. Select the needed stage entry points: onboarding with `zh-init`, discussion with `zh-discuss`, specification with `zh-spec`, planning with `zh-plan`, implementation with `zh-implement`, review with `zh-review`, acceptance with `zh-verify`, and delivery with `zh-deliver`. The outer coordinator dispatches bounded work under the context contract. Related execution stages may share a worker assignment; independent review and the outer acceptance decision retain their required boundaries.
3. Pin the task and slice revisions, source versions, workspace, write scope, expected outputs, and check entry points when dispatching work. The executor returns actual outputs and evidence within the assigned scope. The coordinator checks both the current requirements and the actual artifacts using [verification and acceptance](references/verification.md), then updates the authoritative state. Handle stale evidence, task changes, and in-flight actions using [change and recovery](references/change-recovery.md).
4. Resolve required check failures and rerun affected checks. Repeated attempts without progress return to diagnosis or planning. Prepare options and impacts for decisions requiring user confirmation. Advance when the affected checks pass and required decisions are effective.
5. For executed work, including brief requests, read and perform [closure](references/change-recovery.md#closure). Record `已完成` when the agreed endpoint and closure checks pass; use `zh-resume` for unfinished handoffs.

When work spans code, models, persistence, or release versions, proactively identify migrations using [data changes](references/data-change.md). When maintaining this skill package, consolidate repeated feedback and comparative evaluations using the [improvement loop](references/improvement.md). For delegation, notification, or cancellation, verify the actual interfaces and effects using [host adaptation](references/host.md).

**Completion criteria:** Every accepted slice has outputs, required checks, and an acceptance basis under the current requirements. Overall integration and closure meet the commissioned endpoint. Otherwise, retain the actual state, gaps, and next steps.
