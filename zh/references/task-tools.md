# Git task helper

`zh/scripts/task.py` is a small stdlib CLI for worktree registration, review
identity, local fast-forward delivery, and recovery. It does not infer user
authorization, judge acceptance criteria, or create an independent reviewer.
Use the host's actual authorization and an independent review session before
recording a passing review.

Run it with `python3`. Each mutation supports `--dry-run`; `status` is read only.
Output is JSON and errors go to stderr with exit code 2. `--repo` can point to
any worktree in the repository. `--id` is a local, safe task key.

```sh
python3 zh/scripts/task.py create --repo /project --id fix-123 \
  --target main --branch feat/fix-123 --worktree /project-fix-123
python3 zh/scripts/task.py adopt --repo /project --id existing \
  --target main --branch feat/existing --worktree /project-existing
python3 zh/scripts/task.py status --repo /project --id fix-123
python3 zh/scripts/task.py review --repo /project --id fix-123 \
  --result pass --evidence /path/to/independent-review.txt
python3 zh/scripts/task.py finish --repo /project --id fix-123 \
  --check 'python3 -m unittest discover -s tests'
```

`create` branches from the checked-out target and creates a sibling worktree by
default. `adopt` registers an already checked-out task branch/worktree without
moving either branch; use it for a task started before this helper was present.
Both write `state.json` and an editable `task.md` under the common Git directory
at `zh/tasks/<id>/`. Fill the Markdown record with the goal, scope, authorization
basis, acceptance criteria, evidence pointers, decisions, open issues, and next
step. The helper updates only its marked status block and retains the rest.
Records and check logs survive worktree removal. `status` reconciles recorded
state with live branch commits and worktree status; inspect both on recovery.

`review` records an external review result, copies its evidence into the common
Git task directory, and binds that copy's SHA-256 to the exact candidate and
target commits. The original evidence path is retained as provenance. Record
`--result fail` for failed
acceptance. The helper requires a clean candidate worktree at this point but
does not interpret evidence text. A later candidate commit, target advance, or
changed/missing archived review evidence blocks delivery. Integrate target changes into
the task branch, resolve conflicts, run affected checks, then obtain and record
new review evidence. A passing review must come from the actual independent
reviewer, not from the implementer calling this command alone.

`finish` requires a passing review, unchanged target and candidate commits,
no tracked or untracked target changes, no tracked or untracked candidate
changes, and a fast-forward path. It allows unrelated ignored target files and
uses Git's `--no-overwrite-ignore` option to reject a merge that would replace
one. It merges in the target's checked-out worktree, checks the resulting
commit, and runs `--check` there. The check
command is executed by the shell from the target directory. Its output and exit
code are recorded in the task's `checks/` folder. Completion requires the target
to remain at the reviewed commit without tracked or untracked changes after the check; a successful check
log can be reused on retry only while its hash, target commit, and clean target
state still match. Supply another `--check` to rerun a failed or invalid check.
There is no automatic semantic reuse of pre-merge checks.

With `--keep-worktree`, `finish` stops after the merge and valid integration
check. This supports a later local installation or handoff step before cleanup;
run `finish` again without that flag to remove the worktree. Cleanup refuses
tracked, untracked, and ignored files, since ignored files may contain user
data. Move or classify them manually and retry. The task branch is retained.
No force removal, stash, branch deletion, push, or release occurs.

The record tracks `merge_intent` and `cleanup_intent` before those Git actions.
On retry, the helper recognizes a completed merge or worktree removal only if
the expected commit and branch state still match. A failed check or blocked
cleanup leaves the task record and worktree for recovery. A repeated completed
`finish` is idempotent. If another actor changes either worktree during delivery,
stop and inspect live Git state before seeking new review or retrying.

If a post-merge check fails only because of the environment, correct that cause
within the existing authorization and retry `finish --check ...`. If the failure
requires new code, the helper deliberately does not replace a review after its
candidate has merged. Preserve that task's record, failed check, and worktree;
create a follow-up task from the actual target commit for the repair. Carry the
existing authorized scope and link the original task, explicitly preserving or
transferring any unfinished repair changes. Obtain independent acceptance of
the repaired candidate and deliver the follow-up normally. After its integration
checks pass, record that it resolves the original failure and apply
[zh-finish cleanup rules](../../zh-finish/SKILL.md) to the old worktree using
native Git. Do not reset either task's machine state, rerun the original stale
merge, or mark the failed original check as passed.
