---
name: zh-verify
description: Assess actual artifacts against current completion criteria, checks, and review evidence, returning an itemized acceptance result. Use to accept existing work or verify a commissioned stage; distinguish completing the assessment from the assessed work passing.
---

# Acceptance Verification

Determine whether the actual result meets the current assignment's completion conditions and delivery boundary. A standalone verification request delivers an assessment; it does not automatically repair the product or perform the next delivery action.

## Establish the acceptance basis

Obtain the authoritative task and optional slice, current requirement revisions and adopted sources, commissioned stage and endpoint, actual artifacts and environment, required checks, review records, and evidence access.

Read [verification](../zh/references/verification.md) before assessing evidence and completion. When recording a persistent assessment or delegated return, read [task-protocol](../zh/references/task-protocol.md) and use the [verification template](../zh/assets/templates/verification.md) for a separate `verification.md` only when needed. Read [knowledge](../zh/references/knowledge.md) when resolving conflicting authorities or writing back verified reusable facts.

## Evaluate each condition

1. Enumerate the current observable completion conditions. Include applicable behavior, UI, architecture, data, independent review, integration, and requested delivery-state obligations. A single-stage assignment is judged at that stage's endpoint.
2. Bind the assessed artifacts to actual content: resolved commits plus relevant uncommitted and untracked changes, or a non-Git scoped manifest and fingerprints. Include relevant inputs, configuration, dependencies, test data, and runtime versions or environment identity. A commit alone can miss the actual tested state.
3. Inspect whether each existing check and review still applies to the current requirement and artifacts. Reuse valid evidence. Read [change-recovery](../zh/references/change-recovery.md) when requirements, integration, code, test rules, or environments changed; identify the affected scope for recheck.
4. Run missing required checks that are within the assignment's authorization. Investigate and repair test-tool or environment prerequisites within that authorization, or use an equivalent method preserving the criterion. Record the actual command or operation, input conditions, result, and raw evidence location.
5. Proactively inspect actual code, relevant models, persistence semantics, and migration artifacts for data impact. Read [data-change](../zh/references/data-change.md) when data is involved. Use suitable isolated samples to check retained data, transformations, backfills, initialization, constraints, compatibility, retry and partial completion, and recovery. Record a supported no-migration conclusion when appropriate.
6. Confirm required independent Standards and Spec review covers the actual result, including fixes and integration. Read [host](../zh/references/host.md) when an independent context must be obtained; missing mandatory independence remains an unmet condition. Tool success cannot substitute for a semantic or independent review obligation.
7. Verify the actual endpoint: local artifacts, a requested platform state, or an explicitly commissioned runtime result. For a deployed result, inspect the actual environment and required business path; for a stage-only assessment, do not advance to deployment.

## Results and return

For each criterion, return `通过`, `失败`, `未执行`, or `不适用`, with the assessed source and artifact identity, method, evidence, scope, and any remaining condition. Justify `不适用` from the assignment's actual scope. Separate existing problems from newly introduced defects and explain their acceptance impact.

The assessed work passes only when every mandatory applicable condition and the commissioned endpoint are satisfied. Missing or stale evidence, required checks not run, and unresolved mandatory findings keep that result incomplete. File existence and a worker's reported status are evidence inputs, not acceptance by themselves.

The verification assignment itself can be delivered with a failing assessment if the requested criteria have been evaluated and gaps are explicit. Return the assessment location or compact result, blockers, necessary repair or evidence work, and the next executable step. A coordinator records acceptance and current state in their authoritative location; the verification report retains its historical result.

For a generic skill improvement, read [improvement](../zh/references/improvement.md). Compare old and candidate versions under comparable inputs and conditions, include affected old scenarios and neighboring discovery requests, and use independent execution with the original request and necessary raw artifacts. Keep expected judgments on the evaluation side. Unexplained regressions prevent adoption of the candidate.

This entry is independently authored from the project's accepted acceptance and evidence requirements; it is separate from the upstream two-axis review method.
