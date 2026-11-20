---
name: double-loop
description: "Route a ticket completion, development-only, or new acceptance report request through the configured dual-loop project. Use when the effective project instructions enable double-loop or the user names it. Answer explanations and summaries directly."
---

# Route dual-loop delivery

The current session owns dispatch and stage transitions. Each assigned session executes one bounded stage or review. Keep the original tracker record as the checkpoint and use the user's language for handoffs and reports.

## Resolve the next stage

Open the project's effective `AGENTS.md` or `CLAUDE.md`, its [model routing table](../setup-harness/model-routing.md), and the original ticket via its tracker guide. Read the latest applicable checkpoint and linked originals. Use the ticket's target release, actual revision and evidence to identify the stage.

| Request or checkpoint | Next action |
| --- | --- |
| Finish a ticket with decisions or acceptance criteria still open | Assign `plan-feature`. Advance ready work to `Do` after the plan handoff. |
| Finish a ready ticket or repair an agreed behavior | Assign `implement-ticket`. Advance the tested and reviewed handoff to `Check`. |
| Finish a ticket with an existing delivery | Assign `accept-delivery` at that artifact. Follow its `Check` and `Act` disposition. |
| Only develop | Assign ready `Do` work and its required single-ticket review, then stop at the development handoff. Return any consequential decision needed to start. |
| Only produce an acceptance report | Assign `accept-delivery` in report-only mode on the delivered revision. Carry that mode into every review. Stop with the report and any pending items. |
| Explain material, summarize an existing report, or verify an already closed ticket's result | Read the original material and answer directly. |

Give precedence to an explicitly named skill and its stopping point. First-time `$setup-harness` runs in the current session. Once configured, route a commissioned setup update through the `setup-harness` row. If a required configuration value is missing, identify the cell and use setup to resolve it with the user. Preserve existing approvals. After resolving the checkpoint, dispatch the selected stage to perform its checks and return the handoff.

## Dispatch and verify each assignment

1. Classify this assignment as `simple`, `regular` or `complex` using the project's confirmed examples. Write one sentence linking the actual scope to an example. Look up the exact `model` and `reasoning_effort` for this role at that level. Repeat the judgment for each stage, slice and review axis.
2. Use the [stage and dispatch procedure](references/dispatch.md) to give a fresh session the bounded task, actual working path and fixed inputs. Pass the exact `model`, `reasoning_effort` and `fork_context=false` on the spawn call. Use the documented no-history field for a runtime exposing that equivalent. Check availability for the selected cell. Preserve requested and observed values separately.
3. Receive the status, revisions, scope, original evidence and next action. Open the original evidence and verify the pins before advancing. The route owns stage transitions, parallel slice launches and all independent reviewer launches. A worker returns the inputs required for a new assignment to this session.

For an isolated single-ticket delivery, coordinate one full `Standards` and `Spec` review after `Do` tests. For a set delivered together, coordinate one full review on the pinned integration revision in `Check`. Reuse matching review evidence and dispatch only affected or missing scope on returns. Retain qualifying historical reviews that predate model routing and mark their unavailable model fields unverified. Keep distinct original axis reports and pass the verified results to `Check`. [Independent review](../accept-delivery/references/independent-review.md)

## Continue, stop or resume

On a verified implementation defect, dispatch a `Do` repair with the affected scope, original evidence and fixed revision, then resume `Check` on the repair. When a business decision is needed, return the conflicting sources and affected criteria to `Plan`. For a completion request, keep dispatching the next ready stage until verified closure or a concrete dependency prevents progress. Keep independently ready work moving. Use [accept-delivery](../accept-delivery/SKILL.md) for closure and preserve the user's stopping point.

If the specified pair or fresh-session dispatch is unavailable, the current session records the paused assignment with its required pair, failure evidence and resume point. Keep the stage with that assignment and continue independent assignments. When the pair becomes available, resume it with the same pair. A report-only run returns the waiting reason and evidence with the report and uses disposable execution outputs for any writable checks.
