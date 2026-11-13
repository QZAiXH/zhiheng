---
name: zh-resume
description: Create a durable handoff or resume interrupted work by reconciling effective requirements, actual artifacts, environment state, and evidence. Use for phase transfers, executor or machine changes, pauses, changed requirements, late delegated results, and partially completed release or migration work.
---

# Handoff and recovery

Preserve enough verified state for another executor to continue, or recover the next executable action from an existing checkpoint. A checkpoint is a historical snapshot; the authoritative task entry and actual state determine what is current.

## Obtain the recovery basis

Read [task-protocol](../zh/references/task-protocol.md), [change-recovery](../zh/references/change-recovery.md), and [verification](../zh/references/verification.md). Obtain the authoritative task/plan path in its main record workspace, effective task and optional slice revision, source versions, assignment and write scope, checkpoint if present, actual workspaces/artifacts, evidence locations, current endpoint, authorization, and actual resource limits. Read [checkpoint reconciliation](references/checkpoint-reconciliation.md) for the concrete handoff and re-entry procedure.

Identify whether the request is to prepare a handoff, explicitly pause, resume, reconcile changed requirements, or account for an executor's late return. Missing records are investigated from actual artifacts and sources; unsupported facts remain explicit gaps rather than reconstructed claims.

## Choose the recovery branch

| Condition | Action and exit condition |
|---|---|
| Phase transfer, context change, or new executor | Create/update a durable checkpoint referencing authoritative sources, actual artifacts, unfinished work, execution conditions, and the next action; verify recipient access. |
| Explicit pause or cancellation | Apply the specified scope through the coordinator; stop conflicting dispatch, account for in-flight operations using actual host capabilities, and preserve necessary state. Cancellation itself does not execute rollback. |
| Resume after interruption | Re-read current authority, inspect actual files/processes/environment and evidence, then reconcile them with the checkpoint. Reuse valid results and continue the first authorized executable action. |
| A new instruction changed requirements | Identify affected scope and revisions, preserve old acceptance history, and classify each artifact/evidence item as reusable, needing recheck, or needing rework against the effective basis. |
| An executor returns an older revision | Preserve the returned basis and actual outputs, compare with current sources, and return an acceptance recommendation. The old completion claim cannot update current progress by itself. |
| Workspaces or machines changed | Resolve the main task record location, transfer required durable artifacts/evidence, verify access and content identity, then update entry references and recheck environment-dependent results. |
| Publication or migration was partly executed | Read [data-change](../zh/references/data-change.md) and [migration recovery](../zh-release/references/migration-recovery.md); reconcile actual deployed version, migration ledger, data/batches, and remaining work before retry or recovery. |
| A skill improvement candidate was being evaluated | Read [improvement](../zh/references/improvement.md); preserve baseline/candidate versions, fixed inputs, counterexamples, comparison evidence, adoption status, and rollback basis. Resume evaluation without promoting an unaccepted candidate. |

Read [host](../zh/references/host.md) when notification, wait, stop, independent context, or process control is needed. Record the actual attempted operation and observed response. If stopping is unsupported or unverified, record the possibly continuing action and reconcile its effects before conflicting work resumes.

## Preserve, reconcile, and continue

Keep task status and acceptance ownership in the authoritative records. Executors write their assigned return/checkpoint artifact; the coordinator updates overall and slice state after reconciliation. Preserve relevant committed, uncommitted, and untracked work with content identity; use a file manifest when Git is unavailable.

Before cleanup or transfer, retain evidence needed for acceptance, diagnosis, replay, or recovery and update references. Read [knowledge](../zh/references/knowledge.md) before promoting verified reusable findings; hypotheses and raw returns remain task material. Clean only attributable temporary material meeting the shared lifecycle conditions, within authorization.

## Return and completion

For a handoff-only assignment, return the durable entry/checkpoint, verified accessible artifacts and evidence, unresolved conditions, and exact next action; do not execute unrequested downstream work. For resume, return the reconciliation outcome, reusable and invalidated evidence, effective basis, live conditions, next action taken, and remaining blockers, and continue the existing authorized task through its coordinator.

Handoff is complete when a fresh executor can locate the effective basis and safely identify the next action without relying on hidden conversation context. Recovery is complete when actual state is reconciled and the correct next action has resumed or a concrete blocking condition and unblock action is established. This says nothing about completion of the parent task; that still depends on its accepted endpoint and mandatory checks.

## Method provenance

Independently adapted from Matt Pocock's `handoff`, retaining concise references and sensitive-data redaction. Temporary-only storage and upstream invocation assumptions are replaced by durable project records, revision reconciliation, evidence preservation, and actual host capability. See [source and license](references/upstream.md).
