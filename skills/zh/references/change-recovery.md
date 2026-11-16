# New Instructions, Evidence Invalidation, and Recovery

For coordinated work, perform authoritative revisions and consolidation under the [context isolation contract](host.md#context-isolation-contract). A delegated worker records affected gaps and material dispositions in its own return for the coordinator.

Answer progress questions briefly and continue the original task. When instructions supplement or correct the current objective, identify affected slices and update the authoritative requirements and revisions, dependencies, and acceptance criteria. When instructions explicitly replace, pause, or cancel work, stop the corresponding previous dispatches and preserve other valid work. Prepare options and their impacts for critical unresolved tradeoffs.

Handle dispatched actions through the notification, cancellation, or wait interfaces the host actually supports. Verify message receipt, process termination, and external effects separately. Cancelling a tool call does not mean the task status is `已取消`. When an executor from an earlier dispatch returns, compare the versions actually used with the current sources and record which parts can be reused, need further verification, or must be redone. Reassess evidence applicability when relevant artifacts or check conditions change; comparing revision numbers alone is insufficient.

When resuming, cross-check the current revisions, dependencies, outputs, in-flight actions, and evidence accessibility against the main task entry point, plan, checkpoint, and actual files and environment. A checkpoint is a historical snapshot and does not override the current authoritative state. Use `snapshot` and `compare` to capture and compare the declared scope; verify external state through the project's actual entry points as well. Schedule the next step after reassessment, and keep the work incomplete while required checks remain unsatisfied.

## Closure

At implementation completion, delivery, or handoff, account for every material group created by this task, including scratch areas, operating-system temporary files, helper scripts, bundles, backups, and observations. Use the project's run convention, otherwise `.harness/runs/<task-id>/<run-id>/`. Assign dispositions from actual contents and checks:

- **Reusable knowledge:** consolidate through [knowledge](knowledge.md). Keep hypotheses in task material.
- **Task evidence:** retain what acceptance, diagnosis, replay, or recovery requires, including relevant original failures, final results, artifact versions, and necessary reproducer inputs. Move or copy it to an accessible retained location, update references, and check content and reachability before removing temporary originals. A passing summary alone does not replace required raw evidence.
- **Disposable execution material:** after consolidation and evidence retention, remove the remainder whose ownership is clear, that is not in active use, and that has no necessary references. Required evidence must be preserved; reproducible bundles and obsolete scratch backups need not all be archived.

Closure passes when every group has an inspected disposition and the resulting files and references agree with it. Report retained evidence, removed groups, and reasons and locations for retained working state. A compact final report suffices for short tasks.

A delegated return identifies materials and owners still needed for acceptance. Preserve shared workspaces, active material, other tasks' files, uncertain ownership, paused work, and failures awaiting investigation. Read-only assessments return gaps to the executor. Process termination, environment deletion, and unrelated cleanup retain their separate authorization boundaries.
