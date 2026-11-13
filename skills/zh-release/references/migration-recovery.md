# Cross-version migration and recovery

Read this before release mutation and when recovering an interrupted deployment or data operation. Use the shared [data-change](../../zh/references/data-change.md) protocol for cross-stage semantics and [change-recovery](../../zh/references/change-recovery.md) for revisions, in-flight work, evidence, and lifecycle handling.

## Establish two real baselines

1. Observe the application's deployed version for the actual target and services. Resolve it to the candidate comparison basis. A remembered tag or the local previous commit is insufficient if it does not identify the running version.
2. Observe the target database's actual schema/migration history and relevant data state. Check migration ledger integrity, tool-specific lock/checksum/failure state, and any operations performed outside that ledger.
3. Compare every change between that deployed basis and the candidate, including intervening releases not yet deployed here. Where the candidate includes uncommitted/untracked inputs, include their actual content identity.

For rolling or multi-service deployments, account for every concurrently relevant version. If application or data baseline is unknown, investigate through read-only entries and block mutations that depend on that unknown; continue independent preparation.

## Determine data impact proactively

Inspect migrations, ORM/schema definitions, persistence code, ownership/retention rules, and changed business meanings. Cover structure, stored-value conversion, backfill, initialization/dictionary data, indexes, and constraints. “No migration file” does not settle whether existing data needs transformation.

For each impact, identify affected data, preservation requirements, candidate compatibility, operation/tool, dependencies, expected volume/locking/downtime implications where relevant, and actual result checks. If no migration is necessary, record the inspected change span and why existing data remains valid.

## Plan and rehearse the real sequence

Use the project's established migration tool. Determine ordering from compatibility and actual execution behavior; do not impose one universal “migrate then deploy” order. An expand–deploy-compatible-code–backfill–contract sequence is appropriate only when it satisfies the real coexistence and recovery requirements.

For each step record its entry and executor, precondition, observable completion, failure/partial-success state, and valid re-entry action. Reconcile pipeline jobs, application startup, and multiple instances so the intended operation has one responsible owner or a verified tool-managed concurrency mechanism.

Before affected execution, use applicable isolated rehearsal evidence that checks retained records and relationships, conversions/backfill, constraints, and the intended recovery path. Establish the tool's actual transactional, repeat-run, and resume behavior rather than assuming idempotence. Fixed checks should identify incomplete or wrong results, not merely successful process exit.

Within an effective release authorization, investigate and execute accepted ordinary migration arrangements. For an undecided deletion, irreversible conversion, downtime, or data-loss trade-off, prepare the concrete sequence, impact, alternatives, and recovery limits for the user before the affected step.

## Partial success and re-entry

| Observed state | Next action |
|---|---|
| Migration succeeded; deployment failed | Preserve the migration result, check old-application compatibility with the new data/schema, then choose a supported deployment retry or recovery path. Do not rerun the migration just because the application failed. |
| Deployment succeeded; required migration/backfill is incomplete | Keep release acceptance incomplete. Inspect actual batches, ledger and records; run only the remaining valid operations in dependency order, then recheck business and preservation conditions. |
| A migration command failed | Determine actual committed effects and tool failure state. Repair or resume using its verified method; avoid blindly replaying a non-idempotent operation. |
| The process stopped after some batches | Reconcile checkpoint markers with actual processed records, locks and any still-running worker. Continue from the verified state, preserving completed batches and avoiding duplicate effects. |
| The command timed out or its result is unknown | Inspect the workflow/job/process and target state before another mutation; a lost response does not establish that the operation failed. |
| New requirements invalidate the current sequence | Stop conflicting dispatch, account for in-flight effects, preserve evidence, revise the affected plan through the coordinator, and reassess compatibility and recovery. |

Each attempt records actual entry/run, target, input/candidate identity, step or batch, tool state, observations, and next action. Never edit migration history to claim success without the corresponding verified target state.

## Application rollback and data recovery

Choose from actual compatibility and recoverability:

- **Application version rollback**: use when the prior application remains valid against the actual schema/data. Verify its running identity and required business behavior afterward.
- **Forward repair**: use a reviewed compatible correction when reversal would be invalid or more damaging; verify the repaired data and new running result.
- **Data restoration or reverse migration**: use only with an applicable, authorized recovery method and verified usable source. Account for writes made after the recovery point and dependent systems; make any unresolved data-loss choice explicit before action.

Keep the failed release outcome and recovery outcome distinct. A successful recovery does not make the original candidate deployment successful. Reconfirm version, service state, migration state, preserved data/relationships, and required business paths after recovery.

## Completion and handoff

Migration-related release work completes only when required steps and batches are verified, preserved data and intended business results satisfy the effective criteria, the target runs the requested version, and necessary recovery evidence is accessible. Mandatory failed/unrun checks remain open.

For handoff, record actual versions, migration ledger state, completed batches, remaining steps, process/lock state, compatibility conditions, applicable recovery option, evidence locations, and the first safe next action. Re-entry begins by observing those facts again, not by replaying a remembered command list.
