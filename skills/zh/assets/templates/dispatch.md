---
schema_version: 1
kind: dispatch
task_ref: README.md
slice_id: null
slice_revision: null
dispatch_id: D01
task_revision: 1
source_versions: {}
workspace: .
write_scope: []
---

# Dispatch Conditions

For a slice dispatch, set both `slice_id` and `slice_revision` from the authoritative plan. A return keeps the revisions and source versions actually used, even after the current task changes. For a task without slices, leave both null. The coordinator adds the record path to the task's `records` list when one exists. Brief work may use a compact versioned dispatch under the [context isolation contract](../../references/host.md#context-isolation-contract).

| Dispatch field | Actual value and host evidence |
|---|---|
| Bounded objective, completion criteria, dependencies | |
| Expected outputs/return path, checks, failure/retry destination | |
| Coordinator agent/session ID; worker/reviewer ID; parent relationship | |
| Host interface/version; actual model/reasoning (unknown if unexposed) | |
| Parent-history inheritance setting or verified fresh-session mechanism | |
| Workspace and permitted writes (frontmatter); outer state owner | |

# Return

| Return field | Actual value and raw evidence |
|---|---|
| Returning agent/session ID; adopted task/slice revisions and source versions | |
| Changed/output paths and fingerprints | |
| Check commands/methods, environment, results, and raw evidence paths | |
| Review status, unresolved conditions, proposed discoveries | |
| Retained/disposed materials, recovery condition and next action | |

Coordinator only: verify current inputs, actual outputs and checks, then record acceptance and the authoritative checkpoint. The worker writes its assigned return without updating overall records.
