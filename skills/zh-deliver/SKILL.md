---
name: zh-deliver
description: Deliver accepted work to its agreed local or Git/platform endpoint, assembling reachable artifacts, evidence, and usage notes. Use for local handoff, an authorized commit, PR/MR, or merge; hand release or deployment work to zh-release when that endpoint is commissioned.
---

# Delivery

Make the commissioned endpoint concrete and verifiable. Determine it from the user's explicit request, then the applicable project workflow, then the default of local changes, required verification, and a result report. Reuse existing authorization for the selected endpoint.

## Inputs and conditional rules

Obtain the accepted requirement and artifact versions, verification and review results, current workspace state, agreed endpoint, applicable workflow, output locations, and remaining conditions.

- When consuming a persistent task or recording delivery, read [task-protocol](../zh/references/task-protocol.md). Use the [verification template](../zh/assets/templates/verification.md) or [checkpoint template](../zh/assets/templates/checkpoint.md) only when creating the corresponding artifact.
- When checking evidence applicability, read [verification](../zh/references/verification.md).
- When preparing knowledge writeback or a release handoff, read [knowledge](../zh/references/knowledge.md).
- When requirements changed, the work was integrated, or materials need retention or cleanup, read [change-recovery](../zh/references/change-recovery.md).
- When the delivered change affects stored data, read [data-change](../zh/references/data-change.md).
- When delivering an adopted skill improvement, read [improvement](../zh/references/improvement.md).
- When relying on host-specific loading, delegation, or process control, read [host](../zh/references/host.md).

Read rules directly; a standalone delivery request does not launch the entire development sequence.

## Prepare the result

1. Inspect the actual final changes and delivery location, including relevant uncommitted and untracked files. Match the final artifact identity to current requirements and acceptance evidence. Recheck affected conditions when integration or packaging changes the tested result.
2. Assemble the changes, necessary usage or run instructions, required evidence, and remaining issues. Record checks not run as such. Distinguish accepted implementation from any remaining delivery action.
3. Reconcile data impact proactively with actual model, persistence, and migration changes. Carry the migration artifacts, applicable baseline, execution order and owner, compatibility and recovery conditions, isolated rehearsal results, and remaining environment checks into the handoff. Investigate clues even when no migration file exists.
4. Write back verified reusable facts and accepted decisions within the project's authorized knowledge scope. Keep task-specific versions and run results in task evidence. Before cross-session or cross-machine handoff, ensure the recipient can access the required artifacts and evidence.

## Reach the commissioned endpoint

- **Local delivery:** leave the final changes and necessary evidence at the agreed locations and report how to inspect or use them. A Git repository or remote tracker is not required.
- **Commit:** when requested or required by the applicable authorized workflow, inspect and stage only attributable changes, follow the project's commit conventions, create the commit, and verify its identity and contents. Preserve unrelated user work.
- **PR/MR:** when commissioned, use the project's available platform and existing conventions. Prepare a concrete description of the problem, resulting behavior, verification, and material remaining conditions; create or update the requested proposal and verify its actual target, content, and state. Local task identity remains authoritative for task progress.
- **Merge:** when commissioned, verify the intended source and destination, applicable checks, and actual merge result. Reevaluate affected evidence after conflict resolution or integration. A proposal being created does not establish that it was merged.
- **Release or deployment:** pass accepted version, project release knowledge, actual target, complete relevant change scope, data impact and migration requirements, and evidence to this package's `zh-release` entry. If the overall assignment includes that endpoint, coordinate it through completion and inspect the returned actual artifact or environment state. A release-preparation-only request ends at the requested preparation artifact. Do not infer a tag name or substitute a local tag for a requested environment change.

Use existing project tooling and authorized interfaces. When a required condition is missing, investigate or repair within authorization and continue unaffected work. Return the concrete missing condition and any needed decision when the endpoint cannot yet be reached.

## Close and return

Preserve required verification, diagnosis, and recovery evidence before cleaning attributable temporary materials. Clean only items whose ownership, active use, and remaining references have been checked under the shared lifecycle rules.

Return the delivered locations and versions, actual endpoint state and platform links when applicable, verification summary, data and migration handoff, retained evidence, cleanup result, and remaining work. Delivery is complete only when the agreed endpoint and its mandatory conditions are met. The coordinator records current acceptance and overall state; individual returned or merged slices still require integrated completion checks.

This entry is independently authored from the project's accepted delivery requirements. It does not incorporate or translate the upstream `pr` skill.
