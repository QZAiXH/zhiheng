# Checkpoint and reconciliation procedure

Read this when creating a handoff or restarting work. Field meanings and authoritative ownership come from [task-protocol](../../zh/references/task-protocol.md); this resource adds recovery-specific content rather than defining another schema.

## Write a usable checkpoint

Use the project's established task location. Otherwise use `docs/tasks/<task-id>/checkpoint.md`, linked from the task entry. Create it only when transfer, interruption, or recovery needs it. Reference the current records instead of copying full specifications, plans, ADRs, or diffs.

A checkpoint must let the next executor find:

| Recovery concern | Required content |
|---|---|
| Authority | Main task entry and plan location, task/slice identity, checkpoint's actual requirement revision and source versions. Mark these as snapshot values. |
| Intent | Current stage, scope, requested endpoint, effective confirmations, unresolved decisions, and what the next session is expected to do. |
| Actual work | Artifact/workspace paths, committed and relevant uncommitted/untracked changes, content identities, integrated versus pending outputs, and ownership. |
| Checks | Actual commands/inputs/environment, results and raw evidence links, what remains unrun, and which evidence might no longer apply. |
| Live conditions | Running jobs/processes, delegated work, locks, partially performed external effects, environment/access needs, existing authorization and actual limits. |
| Continuation | Remaining dependency graph, first executable action and its prerequisites, concrete blockers and unblock actions, relevant package stages and why they apply. |
| Preservation | Required evidence/artifacts retained or transferred, recipient access checks, cleanup performed and material deliberately retained. |

Keep secrets and unnecessary personal data out of the document. Record credential acquisition references and access requirements instead. Local absolute paths may be necessary to locate a workspace, but cross-machine handoff also needs transferred content or a recipient-accessible locator with version identity.

## Reconcile on re-entry

1. Locate the authoritative main task entry and plan. Read current state and effective requirements, not just same-named files in a stale worktree. Compare checkpoint identity, requirement revision, and source versions with those current records. Unknown record formats require a compatible read/migration path before affected writes.
2. Inspect actual files and artifacts, including relevant uncommitted/untracked content. Check integration state, candidate returns, running tools/processes, and accessible evidence. Preserve user-owned changes and other tasks' materials. A process identifier or old “running” note is only a lookup clue; observe actual state.
3. Compare evidence with current requirements, check rules, artifact content, inputs/configuration/dependencies, and environment. Reuse checks whose basis is unchanged; recheck affected items. Changed content does not invalidate unrelated evidence automatically.
4. For each item, return one of: reusable under the effective basis, needs a specified recheck, needs rework, or superseded with its replacement reference. These are reconciliation conclusions, not extra task-state enum values. Preserve the original result and its actual basis.
5. Identify the first dependency-satisfied action within current authorization and write scope. The coordinator updates authority and acceptance after examining actual outputs; the executor then proceeds or returns the concrete blocking condition. A checkpoint does not grant fresh permission or impose a new budget.

This pass ends only when relevant recorded claims agree with inspected reality or their discrepancy is explicitly accounted for.

## Handle changed and late results

If a return used an older requirement revision, compare actual changes in requirements and sources. Preserve compatible parts and require checks or rework for affected parts. Never relabel old evidence with a new revision to make it appear current. The coordinator records the current acceptance conclusion and reusable subset.

If new instructions conflict with dispatched work, read [change-recovery](../../zh/references/change-recovery.md) and [host](../../zh/references/host.md). Stop new conflicting dispatch, communicate the new basis through an actual supported interface, and account for in-flight actions. Record attempted notification/stop and observed acknowledgment or absence of it. Reconcile effects of possibly continuing work before starting a conflicting mutation.

An explicit pause applies only to the instructed scope; retain a recovery position. A status question gets an answer and work continues. A cancellation or replacement preserves its actual effects and reusable material; rollback is a separate authorized action. Use the protocol's existing Chinese status values, including `已暂停`, `已取消`, and `已取代`, only through the authoritative owner.

## Specialized recovery

- For publication/migration, observe actual running versions, ledger, data, completed batches, workers/locks, and compatibility before using [migration recovery](../../zh-release/references/migration-recovery.md).
- For skill maintenance, preserve the effective baseline and candidate, exact inputs and evaluation conditions, raw comparison evidence, known regressions, adoption conclusion, and rollback locator. An interrupted evaluation leaves the last accepted version effective unless current authority explicitly says otherwise. Read [improvement](../../zh/references/improvement.md).
- For cross-machine or workspace transfer, verify the recipient can read required records, artifacts, and raw evidence with their content identity. Recheck environment-dependent results after restoring tools/configuration through their actual authority.

## Preserve before cleanup

Use [change-recovery](../../zh/references/change-recovery.md) for the lifecycle decision. Transfer necessary evidence out of expiring temporary storage and update links; verify the destination before removing the source. Keep diagnostic/recovery material for paused, blocked, or failed work when still needed. Only clearly attributable, unused, unreferenced disposable material whose necessary contents were retained is eligible for authorized cleanup.

Completion requires a reachable durable entry, a checked effective basis, accounted-for actual artifacts and live effects, an explicit evidence applicability conclusion, and an executable next step or concrete unblock condition. Finishing this recovery pass does not mark the underlying delivery complete.
