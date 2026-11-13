---
name: zh
description: Coordinate a complete software development task, or continue, adjust, or resume work across stages; select executable slices and verify returned results and the local delivery target. For a standalone stage such as research, review, or acceptance, use the corresponding zh stage skill.
---

# Task Coordination

Find requirements and task records through the project's existing entry points. When ongoing tracking is needed and no convention exists, use the [task protocol](references/task-protocol.md) and [template](assets/templates/task.md) to create a local entry point in `docs/tasks/<task-id>/`. Complete brief requests that need no handoff directly.

1. Confirm the effective requirements, applicable decisions, project facts, delivery target, and authorization. Identify blocking dependencies and the executable frontier of the current task. Refine only slices that can be handed off soon. When project information is insufficient, fill the gaps needed for the current scope using the [knowledge rules](references/knowledge.md).
2. Use this package's stage entry points for the current work: onboarding with `zh-init`, discussion with `zh-discuss`, specification with `zh-spec`, planning with `zh-plan`, implementation with `zh-implement`, review with `zh-review`, acceptance with `zh-verify`, and delivery with `zh-deliver`. Use other stages as the task requires. One executor may handle several stages in sequence; give independent review a separate context as required by the effective requirements.
3. Pin the task and slice revisions, source versions, workspace, write scope, expected outputs, and check entry points when dispatching work. The executor returns actual outputs and evidence within the assigned scope. The coordinator checks both the current requirements and the actual artifacts using [verification and acceptance](references/verification.md), then updates the authoritative state. Handle stale evidence, task changes, and in-flight actions using [change and recovery](references/change-recovery.md).
4. When a required check fails, fix the issue and rerun the affected checks. Repeated attempts without progress call for diagnosis or a plan adjustment. For decisions that require user confirmation, prepare options and their impacts for the user to confirm. Record `已完成` only when the agreed delivery target is reached; leave a checkpoint for `zh-resume` when handing off.

When work spans code, models, persistence, or release versions, proactively identify migrations using [data changes](references/data-change.md). When maintaining this skill package, consolidate repeated feedback and comparative evaluations using the [improvement loop](references/improvement.md). For delegation, notification, or cancellation, verify the actual interfaces and effects using [host adaptation](references/host.md).

**Completion criteria:** Every accepted slice has outputs, required checks, and an acceptance basis under the current requirements. Overall integration conditions and the agreed delivery target are verifiable. Otherwise, retain the actual state, gaps, and next steps.
