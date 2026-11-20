---
name: implement-ticket
description: "Change code for a ready ticket, deliver approved dependent tickets, or repair a verified delivery defect. Use when asked to develop only or start an end-to-end delivery at Do."
---

# Implement tickets

Own `Do` from the original ticket to a tested revision and a recoverable handoff. Write ticket updates and reports in the user's language, preserving tracker fields, code identifiers, commands and URIs.

## Start or resume

Open the target repository's `AGENTS.md` or `CLAUDE.md` and its tracker guide. Read the original ticket, comments, linked spec and latest checkpoint. Resolve the target release, code baseline, approved scope, prerequisites and acceptance examples. Validate the actual revision and outputs before resuming from a recorded stage. Use the existing tracker and [ticket contract](../plan-feature/references/ticket-and-spec.md) for progress updates. When execution has an existing limit, follow [pause and resume](../plan-feature/references/ticket-and-spec.md#pause-and-resume-at-an-existing-limit).

- Ready work can start immediately. For a missing decision that changes the expected behavior, model or acceptance, take the affected example, sources and ticket to [plan-feature](../plan-feature/SKILL.md). Continue independent ready work. For behavior already agreed, implement or repair it from the evidence.
- Resume a delivery already handed off with [accept-delivery](../accept-delivery/SKILL.md) when the request includes acceptance. For a report-only request, use that skill in `Check` mode. A completed ticket with matching evidence needs only its recorded result.
- Read the applicable Git rules and business decisions for the target release. For a project with OpenViking, follow the [project knowledge procedure](../plan-feature/references/project-knowledge.md). Carry the original sources into the handoff. Missing evidence holds the specific affected criterion.

When assigned by [double-loop](../double-loop/SKILL.md), return work for other stages, parallel slices and review to that route for dispatch. For a single delivery, return the fixed review inputs after testing. The route obtains the review results before completing the `Do` handoff. A slice worker returns its tested commit and evidence to the route for integration.

## Implement and test

For one ticket, work on the agreed branch or an isolated worktree if needed. Reproduce reported defects and verify the ticket through the normal entry points. Use the project's tests and add coverage for the requested behavior. Preserve earlier supported data and behavior covered by the ticket. Record the tested commit, working directory, command, exit status or observed outcome and raw output. On a repair, reproduce the returned input and rerun the affected checks.

For tickets delivered together, follow [parallel implementation](references/parallel-implementation.md). It covers dependency validation, fresh worker sessions, isolated worktrees, integration and recovery. A shared contract that two tickets plan to change must be agreed or explicitly sequenced before parallel edits. On return from acceptance, start from the recorded delivered revision and repair the assigned scope, then integrate the repair and preserve the existing delivery's comparison base.

## Hand off the tested delivery

For an independently delivered ticket, obtain one full [independent review](../accept-delivery/references/independent-review.md) after implementation and testing. Carry the reports forward for outer `Check`. For several tickets delivered together, collect each slice's tests and hand off the integrated revision for its single full review in `Check`. On returned work, obtain independent review of the affected parts and retain evidence for unaffected coverage. Record `pending independent review` if the required isolation is unavailable.

Append to the original ticket using the project's tracker convention. Record:

- Scope, target release, resolved comparison base and actual delivery commit. For a combined delivery, include the integration branch and each ticket's checkpoint and integrated commit.
- Actual commands, observed results and pointers to original output, tied to the revision tested.
- Applicable rule URIs and Git or ticket sources, and outstanding or failed criteria.
- Review evidence already obtained, its coverage and pending review, and the next action. Preserve earlier evidence with its original revision.

Hand back what actually emerged during execution for outer `Check`. Capture user preferences with the original source and scenario, verified discoveries with the observed revision or date and evidence, and decisions with their rationale and scope. Preserve actual attempts, checks, results and evidence pointers for a task that may be useful as an [Episode](../plan-feature/references/project-knowledge.md#publish-or-reuse-an-episode). Include the effective skill versions or fingerprints. Omit categories with no new information.

Before giving up a worktree or other temporary location, move any unique evidence required by the ticket into its [durable evidence location](../accept-delivery/references/delivery-evidence.md). Reopen the ticket and open the linked originals from there. For “only develop”, finish at this handoff and keep the ticket available for acceptance. Return a routed completion or repair handoff to the route. On a direct end-to-end request, continue with [accept-delivery](../accept-delivery/SKILL.md). After a repair, provide the new revision, changed scope and affected evidence.
