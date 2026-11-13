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

For a slice dispatch, set both `slice_id` and `slice_revision` from the authoritative plan. A return keeps the revisions and source versions actually used, even after the current task changes. For a task without slices, leave both null. Add the record path to the task's `records` list.

Record expected outputs, check entry points, execution conditions, and the delegate.

# Return

Record the sources actually used, outputs and their fingerprints, raw check evidence, and unresolved issues. The return is for the coordinator to verify.
