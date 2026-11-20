# Stage assignments and dispatch evidence

## Prepare the assignment

Give the session the original ticket and applicable stage skill, actual repository or worktree path, target version, approved scope, fixed revisions and source pointers, permitted effects, checks and required handoff. State that the caller owns further dispatch. The worker returns its result or request for another assignment. Carry report-only access through all dependent assignments. Use a temporary copy or disposable output when a check requires writable state.

| Role | Assignment and handoff |
| --- | --- |
| `plan-feature` | Confirm or recover the goal, applicable decisions, acceptance and dependencies. Return the original decision or ready-ticket pointers, or the specific decision needed. |
| `implement-ticket` | Implement, test and hand back pins and raw evidence. For a single delivery, return the review brief before `Check`. For combined work, return the ready slices and dependency evidence to the route. Use the [integration procedure](../../implement-ticket/references/parallel-implementation.md). |
| `implementation-slice` | Implement and test the fixed slice in its own worktree. Return the containing commit and tests. The route controls shared integration and tracker state for concurrent slices. |
| `accept-delivery` | Verify the existing delivery and review evidence. Return any missing or affected review briefs, repair work or business decision to the route. In completion mode, record `Act` and close only once the evidence permits it. |
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
