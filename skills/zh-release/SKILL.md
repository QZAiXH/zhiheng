---
name: zh-release
description: Prepare and execute software artifact publication, deployment, or rollback through a project's existing release entry points. Use when the requested endpoint is a published version or a target environment; verify actual versions, proactively handle cross-version data migrations, and retain recovery evidence.
---

# Release, deployment, and rollback

Reach the requested publication or environment state through the project's actual workflow. Commit, PR/MR, merge, and ordinary local delivery belong to [zh-deliver](../zh-deliver/SKILL.md). Use an existing release mechanism; a missing mechanism is a concrete setup dependency rather than permission to build a general deployment platform.

## Establish the release basis

Read [task-protocol](../zh/references/task-protocol.md) for assignment identity, endpoint, authorization, and return ownership; [knowledge](../zh/references/knowledge.md) for the release knowledge entry; and [verification](../zh/references/verification.md) for candidate/evidence identity.

Read [project release knowledge](references/project-release.md) when locating, checking, or updating release facts. Obtain the accepted candidate and artifact identity, acceptance evidence, actual current target state, intended environment/services, current workflow/configuration entry points, and applicable recovery conditions. Reuse valid authorization; investigate discoverable facts before asking the user. An ambiguous target or a new consequential downtime/data-loss choice requires a concrete reviewable decision before affected execution.

This step ends when the candidate and target are unambiguous, evidence applies to the candidate, the existing execution entry and responsible executor are identified, and prerequisites for the requested branch are known.

## Choose the endpoint

| Request | Work and completion target |
|---|---|
| Release preparation only | Produce the executable plan, candidate/evidence mapping, data-impact assessment, checks, and recovery conditions; leave execution clearly unperformed. |
| Artifact publication | Build/distribute through the existing entry; verify the requested artifact location, exact version/digest, and retrievability. Deployment is required only if part of the endpoint. |
| Deployment | Execute the accepted release sequence; verify the actual target's running version, service state, required business paths, and applicable data conditions. |
| Rollback or recovery | Inspect actual application and data state, choose the valid recovery path, execute within authorization, and verify restored service and data conditions. Returning an application version alone does not settle data recovery. |

## Execute with data awareness

1. For deployment or recovery, actively read [data-change](../zh/references/data-change.md) and [cross-version migration and recovery](references/migration-recovery.md). Compare the **actual deployed version to the candidate across all intervening changes**, then reconcile actual database migration history and data state. Inspect schema, model, persistence behavior, stored-data semantics, seed/dictionary data, indexes, and constraints. Record a data-impact conclusion with its evidence even when migration is unnecessary. For artifact-only publication, inspect the artifact's build and distribution inputs for data-related effects and record the applicable scope; obtain deployment and database baselines when the requested publication itself runs data operations.
2. When the branch performs migration or deployment, establish order from actual compatibility and the existing workflow. Name the one migration entry/executor and reconcile pipeline, startup, and multi-instance behavior to avoid duplicate actions. Resolve unknown deployed or database baselines before affected mutation.
3. Check the prerequisites of the requested branch, isolated rehearsal evidence for applicable migrations, preservation checks, and usable recovery conditions. Prepare missing artifacts and investigate gaps within scope. Read [host](../zh/references/host.md) when tool/delegation/session capabilities affect execution; do not claim unsupported cancellation or independent verification.
4. Run only the requested authorized branch using the existing entry. Record command/workflow run, candidate, target, responsible executor, actual results, completed migration steps/batches, and remaining work in this release's task record. A trigger acknowledgment is an in-progress result; observe the run and actual endpoint.
5. Verify the requested artifact or environment plus applicable migration state, retained data/relationships, and business results. Bind evidence to the actual version, configuration, inputs, and target. A mandatory failed or unrun check leaves the affected release incomplete.
6. On failure or interruption, read [change-recovery](../zh/references/change-recovery.md). Preserve evidence and reconcile live state before retry. Follow the migration resource's partial-success/recovery branches; continue when there is new evidence or a verifiable correction, and route repeated unexplained failure to [zh-debug](../zh-debug/SKILL.md).

## Return and completion

Return the requested endpoint and actual result, accepted candidate and observed versions, project release knowledge version, full change span, data-impact basis, performed/pending migrations and batches, execution and business-check evidence, recovery outcome if applicable, remaining gaps, and next action. Write reusable verified discoveries back through the project knowledge entry within scope; keep per-release logs and versions in the task.

Completion is branch-specific: preparation delivers a reviewable plan; publication verifies the artifact; deployment verifies the requested target; recovery verifies the restored application **and applicable data state**. A local build, Git tag, successful pipeline stage, or service health check alone is insufficient when the endpoint requires more. For an interrupted release, use [zh-resume](../zh-resume/SKILL.md) to preserve a resumable checkpoint; the coordinator accepts current results against the task's effective basis.

## Basis

This release procedure is independently written from the package design's release-knowledge and data-change requirements. Its project-specific commands are discovered from the project, not provided by an upstream runtime.
