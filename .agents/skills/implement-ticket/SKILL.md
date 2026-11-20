---
name: implement-ticket
description: "Change code for a ready ticket, deliver approved dependent tickets, or repair a verified delivery defect. Use when asked to develop only or start an end-to-end delivery at Do."
---

# Implement tickets

Own `Do` from the original ticket to a tested revision and a recoverable handoff. Write ticket updates and reports in the user's language, preserving tracker fields, code identifiers, commands and URIs.

## Start or resume

Open the target repository's `AGENTS.md` or `CLAUDE.md` and its tracker guide. For a direct development request from chat, use [ticket intake](../plan-feature/references/ticket-and-spec.md#resolve-the-original-ticket). Read the original ticket, comments, linked spec and latest checkpoint. Resolve the target release, code baseline, approved scope, prerequisites and acceptance examples. Validate the actual revision and outputs before resuming from a recorded stage. Use the existing tracker and [ticket contract](../plan-feature/references/ticket-and-spec.md) for progress updates. When execution has an existing limit, follow [pause and resume](../plan-feature/references/ticket-and-spec.md#pause-and-resume-at-an-existing-limit).

- Ready work can start immediately. For a missing decision that changes the expected behavior, model or acceptance, take the affected example, sources and ticket to [plan-feature](../plan-feature/SKILL.md). Continue independent ready work. For behavior already agreed, implement or repair it from the evidence.
- Resume a delivery already handed off with [accept-delivery](../accept-delivery/SKILL.md) when the request includes acceptance. For a report-only request, use that skill in `Check` mode. A completed ticket with matching evidence needs only its recorded result.
- Read the applicable Git rules and business decisions for the target release. For a project with OpenViking, follow the [project knowledge procedure](../plan-feature/references/project-knowledge.md). Carry the original sources into the handoff. Missing evidence holds the specific affected criterion.

When assigned by [double-loop](../double-loop/SKILL.md), work within the assigned path and permissions. Return tested commits, fixed review inputs, proposed tracker updates and any requests for other stages. The coordinator owns dispatch, integration, external writes and the final `Do` handoff.

For a repair returned by acceptance, start at the recorded delivery, preserve its comparison base, and use the assigned [rework round](../double-loop/references/dispatch.md#budget-and-resume-rework). When coordinating directly, apply that procedure before starting the repair.

## Implement and test

For one ticket, work on the agreed branch or an isolated worktree if needed. Exercise the agreed scenarios at the test seams recorded on the original ticket. Reproduce reported defects, run focused checks during edits and verify the final revision through the project's normal entry points. Add coverage for the requested behavior. Preserve earlier supported data and behavior covered by the ticket. Record the tested commit, working directory, command, exit status or observed outcome and raw output. On a repair, reproduce the returned input and rerun the affected checks.

For tickets delivered together, follow [parallel implementation](references/parallel-implementation.md). It covers dependency validation, fresh worker sessions, isolated worktrees, integration and recovery. A shared contract that two tickets plan to change must be agreed or explicitly sequenced before parallel edits.

## Hand off the tested delivery

At the `Do` handoff, use the [independent review procedure](../accept-delivery/references/independent-review.md) to reconcile the reports reopened from the original ticket with the actual delivery. In a routed delivery the coordinator performs this check and dispatches any missing coverage. For a combined delivery, hand off the integrated revision with the full review due in `Check`.

Prepare the following handoff for the original ticket. When working directly, append it using the project's tracker convention.

- Scope, target release, resolved comparison base, actual delivery commit, and complete diff and path inventory. For a combined delivery, include the integration branch and each ticket's checkpoint and integrated commit.
- Actual commands, observed results and pointers to original output, tied to the revision tested.
- Applicable rule URIs and Git or ticket sources, and outstanding or failed criteria.
- Existing review evidence and coverage, open or affected findings, pending review, and the next action. Preserve earlier evidence with its original revision.

Hand back what actually emerged during execution for outer `Check`. Capture user preferences with the original source and scenario, verified discoveries with the observed revision or date and evidence, and decisions with their rationale and scope. Preserve actual attempts, checks, results and evidence pointers for a task that may be useful as an [Episode](../plan-feature/references/project-knowledge.md#publish-or-reuse-an-episode). Include the effective skill versions or fingerprints. Omit categories with no new information.

Keep unique originals available until the coordinator, or the current session in a direct delivery, completes the [evidence readback](../accept-delivery/references/delivery-evidence.md) from the ticket. For “only develop”, finish at this handoff and keep the ticket available for acceptance. On a direct end-to-end request, continue with [accept-delivery](../accept-delivery/SKILL.md). After a repair, provide the new revision, changed scope and affected evidence.
