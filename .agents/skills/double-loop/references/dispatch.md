# Stage assignments and dispatch evidence

## Prepare the assignment

Give the session the original ticket and applicable stage skill, actual repository or worktree path, target version, approved scope, fixed revisions and source pointers, permitted effects, checks and required handoff. State that the coordinator owns further launches, shared tracker updates and integration. The worker returns its result, any proposed updates or a request for another assignment. Carry report-only access through all dependent assignments. Use a temporary copy or disposable output when a check requires writable state.

| Role | Assignment and handoff |
| --- | --- |
| `plan-feature` | Confirm or recover the goal, applicable decisions, acceptance and dependencies. Return the original decision or ready-ticket pointers, or the specific decision needed. |
| `implement-ticket` | Implement, test and hand back pins and raw evidence. For a single delivery, return the review brief before `Check`. For combined work, return the ready slices and dependency evidence to the route. Use the [integration procedure](../../implement-ticket/references/parallel-implementation.md). |
| `implementation-slice` | Implement and test the fixed slice in its own worktree. Return the containing commit and tests. The route controls shared integration and tracker state for concurrent slices. |
| `accept-delivery` | Verify the existing delivery and review evidence. Return any missing or affected review briefs, repair work or business decision to the route. Return the proposed `Act` disposition to the coordinator for recording and any closure. |
| `Standards`, `Spec` | Give each reviewer the [independent review inputs](../../accept-delivery/references/independent-review.md#1-pin-the-delivery-and-collect-originals) for its axis at the same base and head. Limit the brief and access to the fixed diff, requirements, rules, and original test evidence. Save separate reports. |
| `setup-harness` | Apply or preview the approved project setup update. Return the actual change, checks, and any decisions still needed. |

## Use and record the actual tool call

- Locate `spawn_agent` and the companion wait and close operations through the runtime's tool discovery when they are deferred.
- Provide the exact `model`, `reasoning_effort` and `fork_context: false` fields when the spawn schema exposes them. On Codex MultiAgentV2, the equivalent explicit field is `fork_turns: "none"`. Record the actual tool, arguments and isolation field used. Require a tool that supports both model overrides and explicit no-history startup.
- Check availability against the assigned pair and the current tool schema. If the schema accepts the approved pair and there is no runtime error for it, attempt that exact dispatch. Establish unavailability from the schema or actual error for the selected pair. Keep the route in the coordinator session when a launch is pending.
- Record each assignment's role, difficulty and reason, chosen pair, ticket, scope and pinned revisions. Retain the dispatch response, parent and child session identifiers, and completion or failure record. Capture the actual model, reasoning effort and fresh-session provenance from runtime metadata when available. A worker's self-description and a parent model setting are insufficient evidence of the child's actual settings. Mark unavailable metadata as unverified. Reconcile an observed mismatch before treating the run as fulfilling the assignment.
- Run independent ready assignments concurrently when capacity permits. Use distinct worktrees for concurrent edits and one writer per shared tracker or integration checkpoint. Close session slots once their results are retained.

In local Codex CLI rollouts, match the child to the parent via `session_meta.source.subagent.thread_spawn` and read the child's `turn_context` model and effort. Keep only the dispatch and execution evidence for these sessions.

Keep evidence on the original ticket or at a durable location linked from it. In report-only mode return it with the report using read-only Git, tracker and knowledge access. A paused assignment records the failed pair, observed error, last verified checkpoint and exact operation to resume. Check for a current session or result for the same assignment before retrying. Resume with the recorded pair and inputs. A change to scope or pins starts a new assignment with its own difficulty judgment.

## Budget and resume rework

Use this procedure when a verified failure returns a delivery to `Do`. The coordinator owns the count. In a direct completion, the current session keeps it. Start from the original ticket and its recorded comparison base, delivery, failed checks and prior rounds.

1. Use the existing rework budget. If none exists, record a finite number of rounds and the scope-based reason on the original ticket before the first repair. Recover the active round, used rounds and balance from the original checkpoint and its later entries across sessions, revisions and workers. Keep any existing user, project or runtime limit in force.
2. Resolve any active round or uncertain operation before reserving another. [Reconcile uncertain writes](../../plan-feature/references/ticket-and-spec.md#reconcile-uncertain-writes) and look up the session and result for the round. Resume its assignment or use its result. Retry the same round only after confirming the earlier launch did not start. Keep an unconfirmed launch pending under that round.
3. When another round is warranted and the budget allows it, append its number, affected criteria or findings, tested revision, expected and actual results, original evidence, next corrective action and balance after reserving it. Read back the checkpoint before dispatching with that round and its fixed inputs. If readback fails, keep the repair paused and return the pending record.
4. After the repair and affected `Check`, append the actual revision, criteria or findings, observed results, new evidence, next action and balance under that round. If interrupted, append the available evidence and keep the round active at its recovery point. Compare the material result and proposed correction to the trigger for the round and earlier attempts. If the same failure leads to the same next action, stop that rework for lack of progress. If no rounds remain and the failure persists, stop for budget exhaustion. Continue when evidence supports a different corrective action and the recorded budget allows it.
5. On a stop, record the blocker, last verified revision, original evidence and exact recovery condition. Resume from that record when new evidence or a resolved dependency enables progress and the budget allows another round. Extend an exhausted budget only with authorization. Keep the earlier rounds and their evidence. Continue unrelated work that can proceed independently.
