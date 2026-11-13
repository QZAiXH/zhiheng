---
name: zh-discuss
description: Resolve open requirements and design decisions through evidence-based discussion. Use when goals, business rules, permissions, ownership, core relationships, major module boundaries, or the main technology stack need a decision; return confirmed inputs for specification rather than starting implementation.
---

# Requirements and design discussion

Turn the current decision frontier into confirmed requirements and explicit remaining dependencies. A request for one discussion stage ends with that stage's findings; a wider authorized task returns them to its coordinator for progression.

## Establish the decision basis

Obtain the user's goal, current stage and endpoint, existing confirmations, relevant project sources, and permitted documentation scope. When reading or returning tracked work, read [task-protocol](../zh/references/task-protocol.md); when locating or updating sources, read [knowledge](../zh/references/knowledge.md). Follow their record ownership rather than creating another task-status ledger.

Separate observed behavior, intended behavior, accepted decisions, and hypotheses. Investigate facts in code, configuration, documentation, and available environments before making them questions for the user. This step is complete when each open item is classified as a fact to investigate, a user decision, or an implementation detail within an accepted choice.

## Work the decision tree

1. Map decisions and their prerequisites. The current **frontier** contains only decisions whose prerequisites are already settled. Investigations still running leave their dependent questions off this frontier.
2. Investigate factual gaps. For a bounded external question, use [zh-research](../zh-research/SKILL.md); for changing terminology, relationships, permissions, or ownership, use [zh-domain](../zh-domain/SKILL.md); for significant module or stack choices, use [zh-arch](../zh-arch/SKILL.md). Read [host](../zh/references/host.md) before delegating; sequential investigation is valid when parallel capability is unavailable.
3. Present the ready frontier as numbered questions. Each question gives the concrete alternatives, their material effects, and one supported recommendation. Phrase an unambiguous “yes” as accepting that recommendation. Wait for answers to decisions that govern subsequent work; continue independent investigations meanwhile.
4. Record each explicit answer with its source and scope, then recompute the frontier. Reuse prior valid confirmations. Clear user instructions become effective requirements directly; ask only about remaining consequential choices.
5. Choose the next branch using the table below. Finish when every decision needed by this stage is resolved or has an explicit unresolved dependency and next action.

| Condition | Action and exit condition |
|---|---|
| Business meaning, permissions, ownership, core entity relationships, important module boundaries, or main stack remain undecided | Prepare a reviewable choice with evidence and effects, then obtain the user's decision before dependent implementation. |
| A new page, major operation flow, or broad layout change needs confirmation | Use [zh-prototype](../zh-prototype/SKILL.md); record the approved artifact version and feedback before business UI implementation. |
| A local UI adjustment fits the accepted design | Preserve that design and specify an appropriate check; a new prototype round is unnecessary. |
| The user only wants exploration | Return options, recommendations, unresolved questions, and evidence; label proposals as proposals. |
| Requirements and required prototypes are already confirmed | Synthesize their references for [zh-spec](../zh-spec/SKILL.md), without repeating the interview. Invoke it only within the current assignment. |
| The project is new | Carry confirmed stack, constraints, and first runnable outcome to [zh-init](../zh-init/SKILL.md); do not create a scaffold during discussion alone. |
| A new instruction changes current requirements | Read [change-recovery](../zh/references/change-recovery.md), identify affected decisions and artifacts, and return the revision impact to the coordinator. |
| Repeated usage feedback suggests a generic skill change | Read [improvement](../zh/references/improvement.md); discuss the maintenance task's goals and acceptance criteria, preserving original feedback and counterexamples. |

## Return and completion

Return confirmed requirements and their sources, retained constraints, considered alternatives and rationale, unresolved items with dependencies, prototype/architecture/domain references, and the next executable stage. Save durable decisions in the existing authoritative location within the authorized scope; keep hypotheses in task notes.

Discussion is complete when the requested questions have a traceable answer or explicit pending condition. Design finalization additionally requires the consequential user decisions and applicable prototype approval. Missing decisions block their dependent work; they do not justify marking an entire development request complete. If progress repeats without new evidence, narrow the question or hand the specific gap to the coordinator.

## Method provenance

Independently adapted from Matt Pocock's `grilling`; the composition of discussion and domain work also draws on `grill-with-docs`. The decision frontier is retained; unconditional interviewing and upstream tool invocation are replaced by scoped decisions, reusable confirmations, and this package's stages. See [source and license](references/upstream.md) for the pinned source and full notice. No upstream installation is required.
