# Task worktrees

The coordinator owns worktree creation, recovery and release. Use one named local branch and one linked worktree for each single ticket, parallel slice and integration checkout. Run implementation, testing and local commits from the assigned worktree. Use the caller's checkout only to locate the repository and inspect its state. Keep its branch, index and files intact, including unrelated changes. Choose a unique absolute path outside existing checkouts.

## Create before editing

1. Resolve the approved starting commit with `git rev-parse --verify "<base>^{commit}"`. Use the ticket's agreed base for a single ticket or integration checkout, and the verified integration tip containing its prerequisites for a new slice. In a recorded repair, use the repair checkpoint and preserve the delivery comparison base.
2. Check `git worktree list --porcelain`, the local branch refs and the destination. Record the ticket or slice, planned absolute path, branch and starting commit on the original tracker record or its linked checkpoint. For local Markdown, use the established tracker location so the checkpoint remains accessible independently of the task checkout.
3. From the target repository, run `git worktree add -b "$branch" "$worktree" "$start"` for a new branch and path. Verify the new worktree and record the actual path, branch, starting commit and current commit before edits or dispatch. The coordinator owns the shared record and each worker verifies its assignment before writing.

From the assigned path, check `git rev-parse --show-toplevel`, `git rev-parse --path-format=absolute --git-common-dir`, `git symbolic-ref HEAD` and `git rev-parse HEAD`. Match the canonical path and repository, named branch and expected commit against the checkpoint and the worktree listing. The expected commit is the starting commit on creation and the verified checkpoint tip on resumption.

## Reuse or restore

Start with the tracker checkpoint, current branch ref, registered worktrees, and worker or integration state. Preserve the original starting commit and record the current verified tip separately.

- **Existing checkout.** Reuse the recorded checkout when its identity matches. Inspect staged, unstaged, untracked and ignored state. Preserve interrupted edits, finish or resume an active Git operation in place, and avoid a second writer. If the tip has advanced, reconcile the new commits with the checkpoint and task evidence before continuing. Apply the same checks after an interrupted creation or integration.
- **Released checkout.** If the recorded checkout has been released and the branch is available, verify that `refs/heads/$branch` resolves to the reconciled checkpoint commit. Run `git worktree add "$worktree" "$branch"` from the repository. Reuse the recorded path if it is free and unregistered. Otherwise choose and record a new unused path after verifying the old registration is gone. Verify the checkout at the expected tip before editing.
- **Missing branch.** If neither a registered checkout nor a local branch remains, choose a free, unregistered path and resolve the last verified checkpoint commit as a Git object and recreate the named branch there with `git worktree add -b "$branch" "$worktree" "$checkpoint"`. Use the original starting commit only when the checkpoint shows it was the last verified state. Verify and record the restored tip. If the required commit is unavailable, record its ID and the source needed to recover it.
- **Mismatch or missing registration target.** Reconcile a moved checkout, an unavailable volume, a branch in use elsewhere, or a path still registered despite being absent before writing. Verify an owned moved checkout before any targeted repair and record its actual path. If the path is confirmed absent, unlocked, inactive and the saved branch and evidence are intact, `git worktree remove "$worktree"` can clear that specific stale registration. Recheck the listing and branch before restoring. Preserve ambiguous paths, refs and checkpoints and record what is needed to resume. Use Git's normal safeguards and keep unrelated registrations intact.

Finish with the [evidence and cleanup procedure](../../accept-delivery/references/delivery-evidence.md#release-task-worktrees) for the requested stopping point.
