---
name: plan-feature
description: "Plan a requested feature or architecture change, triage an original ticket for readiness, split an agreed spec, or resolve a decision returned by delivery."
---

# Requirements and design

Own outer-loop `Plan` through ticket breakdown and acceptance design. A fresh delivery session should be able to start from the original ticket. Keep a discussion-only request in the conversation. Record authorized decisions as they are made. In a routed delivery, send tracker updates to the coordinator for writing and readback.

Write specs, tickets, diagrams, knowledge bodies and handoffs in the user's conversation language. An explicit deliverable language overrides that default for the named artifacts. Preserve code identifiers, commands, URIs and fixed tracker or protocol fields.

## Choose the planning work

Start at the project's `AGENTS.md` or `CLAUDE.md`. For an explicit development request from chat, use [ticket intake](references/ticket-and-spec.md#resolve-the-original-ticket) before writing or handing off. Read the original ticket, its comments, linked decisions and target release when a ticket exists. Honor any existing [task budget and checkpoint](references/ticket-and-spec.md#pause-and-resume-at-an-existing-limit). Check the relevant implementation or tests for current behavior. Before asking a business question, designing a model or writing acceptance criteria, look up the applicable decision for that scenario and version. For a project bound to OpenViking, use its ordinary project identity and the [knowledge procedure](references/project-knowledge.md).

| Situation | Action and stopping point |
| --- | --- |
| Existing ticket | Verify the reported behavior through its normal entry point where possible. Search for an existing implementation using project terms. Identify what already works, what is ready to change, or the precise missing fact or decision. If the ticket already covers the change, hand it straight to delivery with its existing checks. |
| Architecture improvement without a chosen change | Inspect the named pain point, or use change history to locate frequently edited modules. Present plausible candidates with file or call-site evidence, what would move across which interface, and how tests would exercise it before and after. Let the user choose before developing a design. |
| Two plausible business outcomes | Use one input to show exactly how a user or caller would distinguish the outcomes. Read the applicable sources first. When they settle it, cite the decision and use the distinguishing example in acceptance. Otherwise use `grilling` to ask the decision owner the consequential question, with options and a reasoned recommendation. Use `domain-modeling` when the meaning, identity or ownership of an object is at issue. If a supporting skill is unavailable, perform the indicated step directly. |
| Decisions span sessions | Keep a decision index reachable from the original ticket. Record the destination, open questions and their dependencies, and links to confirmed answers, rationale and scope. Resume from an unanswered question whose prerequisites are settled. Delegate a factual uncertainty to research or use a prototype to observe a disputed behavior when useful. Close a decision ticket when its question has an evidenced answer. Track dispatchable implementation tickets separately. |
| Delivery returns a design question | Read the ticket's acceptance evidence and the [return to Plan procedure](../accept-delivery/SKILL.md). Reopen the particular decision and examples affected. Carry forward unaffected, ready work. |

## Review data-model changes before development

Show the user **every proposed change to the data model**, including a single field. Start from the current model document or executable schema. Show before and after, the affected fields, types and constraints, and how existing records will read or be backfilled. For a new table or a changed relationship, include a local ER diagram showing the relevant keys and cardinality.

Cite and show any earlier user-approved design that covers this exact change. Obtain the user's confirmation for the uncovered part before marking the affected implementation ready. Once confirmed, synchronize the project's existing model document. If the schema or migrations are the only model source, record the approved design in the ticket for implementation in `Do`.

## Hand off from the original ticket

For a small change, add only the missing example, decision or check to the ticket. When interfaces or tickets share a contract, synthesize a parent spec. When work needs separate deliveries, prepare the proposed split and capture the approval for the original ticket. Use the [spec and ticket guide](references/ticket-and-spec.md) for the tracker, dependency edges and integrated example.

Once the handoff is recorded, reopen the original ticket as the receiver would. Follow its links to the target version, accepted decisions, concrete inputs, expected outcomes and check entry points. In a routed delivery, the coordinator performs this readback for its writes. For a split, identify what can start now, what each blocked ticket awaits and which behavior must be checked after integration. Report actual observations and mark planned checks as pending.

For a maintainer-requested `retro`, take the original ticket, delivery revision and evidence to the [Act retrospective](../accept-delivery/references/retro.md). Carry adopted Git clauses, their verified knowledge URIs and their checks into affected follow-up tickets.

When assigned by [double-loop](../double-loop/SKILL.md), return proposed tracker updates, the verified planning handoff, ready work or the next decision to the coordinator for recording and dispatch. For direct invocation on an end-to-end request, continue straight to [implement-ticket](../implement-ticket/SKILL.md) when the work is ready, or to [accept-delivery](../accept-delivery/SKILL.md) when there is a delivery ready for `Check`. “Only develop” ends at the implementation handoff. “Only produce an acceptance report” goes to `Check` on the delivered revision. A planning-only request ends with the design or ready ticket.
