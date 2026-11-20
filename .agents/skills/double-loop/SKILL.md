---
name: double-loop
description: "Route requests to implement or finish work from chat or a ticket, or to produce a new acceptance report. Use when project instructions enable double-loop or the user names it. Answer explanations and summaries directly."
---

# Route dual-loop delivery

The current session coordinates delivery. It owns dispatch, integration, tracker writes, and stage transitions. Each assigned session executes one bounded stage or review and returns evidence or proposed updates. Keep the original tracker record as the checkpoint and use the user's language for handoffs and reports.

## Resolve the next stage

Open the project's effective `AGENTS.md` or `CLAUDE.md`. Determine the requested mode and stopping point before any write. Read the [ticket intake procedure](../plan-feature/references/ticket-and-spec.md#resolve-the-original-ticket) for an explicit development request from chat or a referenced ticket. Pin the one original tracker record before dispatch. Use its target release, actual delivery revision, latest applicable checkpoint, and linked originals to identify the stage.

| Request or checkpoint | Next action |
| --- | --- |
| Develop or finish work with decisions or acceptance criteria still open | Assign `plan-feature`. Advance ready work to `Do` after the plan handoff. |
| Develop a ready request or repair an agreed behavior | Assign `implement-ticket`. Advance the tested and reviewed handoff to `Check`. |
| Finish a ticket with an existing delivery | Assign `accept-delivery` at that artifact. Follow its `Check` and `Act` disposition. |
| Only develop | Assign ready `Do` work or verify the local delivery commit, required review and development handoff. Leave the ticket open and run handoff cleanup. |
| Only produce an acceptance report | Resolve the existing ticket and delivery using read-only access. Assign `accept-delivery` in report-only mode, carry that mode into every review, and stop with the report and any pending items. |
| Discuss requirements or design | Keep the discussion in chat. Use `plan-feature` for decisions and examples. Record decisions only when authorized and stop at the requested planning point. |
| Explain material, summarize an existing report, or verify an already closed ticket's result | Read the original material and answer directly. |

Give precedence to an explicitly named skill and its stopping point. First-time `$setup-harness` runs in the current session. Once configured, route a commissioned setup update through the `setup-harness` row. If a required configuration value is missing, identify the cell and use setup to resolve it with the user. Preserve existing approvals. After resolving the checkpoint, dispatch the selected stage to perform its checks and return the handoff.

For completion, read the delivery choice in the project's issue-tracker guide. A GitHub issue can be delivered locally or through a PR. Resolve a missing choice with [setup-harness](../setup-harness/SKILL.md) before publishing or closing. A development-only request already supplies its stopping point. Apply report-only access before any workspace, commit or PR operation.

## Dispatch and verify each assignment

1. Read the project's [model routing table](../setup-harness/model-routing.md). Classify this assignment as `simple`, `regular` or `complex` using the project's confirmed examples. Write one sentence linking the actual scope to an example. Look up the exact `model` and `reasoning_effort` for this role at that level. Repeat the judgment for each stage, slice and review axis.
2. Before a development or repair assignment edits files, create or recover its [task branch and worktree](../implement-ticket/SKILL.md#start-or-resume) and checkpoint them on the original ticket. Do the same for the coordinator's integration worktree. Use the [stage and dispatch procedure](references/dispatch.md) to give a fresh session the bounded task, actual path and fixed inputs. Pass the exact `model`, `reasoning_effort` and `fork_context=false` on the spawn call. Use the documented no-history field for a runtime exposing that equivalent. Check availability for the selected cell. Preserve requested and observed values separately.
3. Receive the status, revisions, scope, original evidence and next action. Verify the pins and publish authorized checkpoints on the original ticket. For a writable delivery, start from that ticket and reopen the linked originals before advancing.

Use the [independent review procedure](../accept-delivery/references/independent-review.md) to determine timing, initial scope and any recheck. At the `Do` handoff and in `Check`, reconcile both axis reports and their coverage with the actual delivery. For a set delivered together, record the full review as due on the integrated revision in `Check`. Preserve separate original reports on the ticket.

## Continue, stop or resume

Use [commit-pr](../commit-pr/SKILL.md) for the ticket-scoped commit. For `github-pr` completion, publish or recover the PR for the tested delivery in the code repository and record its URL and head on the original ticket. An integrated set shares its delivery PR. For `local` delivery or development only, retain the local task branch and commit. For development only, reopen the handoff and its required review, then apply the [worktree cleanup procedure](../accept-delivery/references/delivery-evidence.md).

Use the [rework procedure](references/dispatch.md#budget-and-resume-rework) to recover any active round from the original ticket, reserve a warranted repair, and record its result through the affected `Check`. When a business decision is needed, return the conflicting sources and affected criteria to `Plan`. In completion mode, apply the [Act disposition and closure gate](../accept-delivery/SKILL.md#4-act-on-the-evidence) in the coordinator session, including the recorded delivery choice. Advance ready work until verified closure, a recorded stop condition, or the user's stopping point. Keep independently ready work moving.

If the specified pair or fresh-session dispatch is unavailable, the current session records the paused assignment with its required pair, failure evidence and resume point. Keep the stage with that assignment and continue independent assignments. When the pair becomes available, resume it with the same pair. A report-only run returns the waiting reason and evidence with the report and uses disposable execution outputs for any writable checks.
