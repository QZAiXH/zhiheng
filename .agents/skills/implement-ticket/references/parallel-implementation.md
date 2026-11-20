# Implement a set of tickets

## Establish the integration branch

Read the parent spec, child tickets and blocking links. Verify that each link resolves and the prerequisites form an acyclic graph. Keep an unknown dependency or a conflicting shared interface pending until resolved. Continue dispatching the independent, ready work.

Reuse the recorded integration branch on resumption. Otherwise create it at the agreed base in a clean checkout and record its starting commit on the parent. Keep the coordinator as the sole writer of the integration branch and shared tracker state. Read existing stage and merge evidence before retrying.

## Dispatch each ready ticket

A ticket is ready when all prerequisites are present in the integration tip, its applicable decisions and checks are available, and it has no active implementer. Start independent ready tickets together up to the available capacity. With A and B ready and C blocked only by A, merge a passing A and dispatch C from the resulting tip while B is still in progress.

In a routed delivery, hand the dependency frontier and worktree inputs to [double-loop](../../double-loop/SKILL.md). The route dispatches `implementation-slice` workers with the confirmed pairs and coordinates integration.

For each dispatch:

1. Resolve the integration tip to a commit and create a distinct branch and worktree at that commit. For example, use `git worktree add -b <ticket-branch> <worktree> <integration-tip>`. Verify `HEAD` and the worktree's branch. A worker checks the same values before editing.
2. Launch a fresh session with `fork_context=false` in Codex when exposed. Give it the absolute worktree path, start commit, ticket and parent pointers, accepted sources, relevant prerequisite commits, check entry points and expected handoff. In a runtime without a working-directory argument, tell the worker to run commands in that path explicitly. If the runtime cannot give a fresh session with a separate worktree, record that the dispatch is pending and resume the available work.
3. Have the worker implement and test the slice on its branch and return the [tested delivery handoff](../SKILL.md#hand-off-the-tested-delivery). Leave integration and shared tracker updates to the coordinator. Save the dispatch and handoff on the parent or linked evidence, including ticket ID, session ID, worktree, starting commit, and start and completion times.

## Integrate a ready result and check the next frontier

Confirm the worker's commit belongs to its worktree and the required slice checks passed. Merge its changes on the integration branch in one coordinator action and run checks for any interacting changes on the resulting revision. Record both the worker commit and the containing integration revision. With a merge, confirm containment with `git merge-base --is-ancestor <worker-commit> <integration-tip>`. For a project using squash or cherry-pick, verify the resulting change and record the corresponding integration commit before unlocking dependents. A worker's reported completion alone leaves its dependents pending.

Save the finished worker's handoff and release its session slot. Recompute eligibility after each successful integration and dispatch the newly ready tickets as soon as capacity permits. If the merge or its checks fail, retain the source revisions, record the conflict or failing check and repair it within the accepted scope. Keep dependents pending and use the last verified tip for independently ready work. Resume interrupted work from the verified integration branch, active sessions and tracker evidence.

When all slices are integrated, pin the parent delivery commit and link the parent-level examples. Hand off the combined revision and child evidence to outer `Check`. Preserve unique originals and follow the [evidence and cleanup procedure](../../accept-delivery/references/delivery-evidence.md) before releasing a clean disposable worktree. Reopen the parent and affected child links after cleanup.
