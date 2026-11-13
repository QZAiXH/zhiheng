---
name: zh-prototype
description: Build an interactive prototype or a focused experiment to answer a design question. Use for new pages, major operation flows, broad layout changes, uncertain state models, or logic that needs hands-on exploration; capture observations and approval before dependent business UI implementation.
---

# Prototype

Make the question testable with the smallest runnable artifact, then record what it established. Obtain the question, intended audience and scenarios, effective domain/architecture constraints, existing design system, allowed write scope, and required approval. Read [task-protocol](../zh/references/task-protocol.md) for tracked assignments and [knowledge](../zh/references/knowledge.md) for existing design authority.

## Select the experiment

| Question | Required reading and artifact |
|---|---|
| Does this business logic, state transition, or data shape represent the real cases? | Read [logic prototype](references/logic.md); normally create a self-contained interactive HTML file with visible state, free play, and guided scenarios. |
| How should this page or interaction be presented? | Read [UI prototype](references/ui.md); use the project's visual context and a runnable interactive surface. Compare structural variants when the design question benefits from alternatives. |
| A major workflow depends on both state and presentation | Combine the relevant portions of both resources around one question; keep state semantics distinguishable from presentation alternatives. |
| A narrow technical uncertainty needs an experiment rather than a visual surface | Create an isolated minimal sample with explicit input, expected observation, and real output; route pure documentation research to [zh-research](../zh-research/SKILL.md). |

Choose from the user's goal and actual context. When an unresolved ambiguity would change the artifact materially, resolve the design question first. For harmless details, state the assumption and proceed.

## Build and observe

1. State the question and success/failure observations in the artifact or its task note. Declare prototype status, basis version, sample-data boundaries, location, and startup method. This step is complete when the reviewer knows what the artifact can settle.
2. Build in a clearly designated task artifact area, isolated workspace, or prototype route following project conventions. Keep production business behavior unchanged during exploration. Reuse the real visual shell when useful; keep mutations simulated and persistent experiments isolated.
3. Exercise the main path and relevant edge/error/empty/permission states. Check startup and the actual interactions, not only source syntax. Read [verification](../zh/references/verification.md) when binding observations to the artifact. If an execution tool is unavailable, record precisely which interactions remain unverified.
4. Present the runnable location, scenarios, observed results, remaining assumptions, and the concrete choice to review. For new pages, major operation-flow changes, or broad layout changes, obtain approval of the actual artifact version before business UI implementation. Earlier approval remains valid only within its unchanged scope.
5. Record the answer, feedback, chosen variant or combination, applicable constraints, and artifact version. When feedback changes the model or requirement, read [change-recovery](../zh/references/change-recovery.md); update the question and recheck affected observations.

## Preserve and hand off

Retain the prototype and decision in a durable task location or an already authorized project artifact/branch. Read [change-recovery](../zh/references/change-recovery.md) before transfer or cleanup; confirm the next stage can access evidence. No automatic commit, branch publication, or production promotion is part of a prototype-only request.

Return the artifact and startup instructions, question and actual scenarios, observation/evidence references, user feedback and approval status, retained decisions, and implementation implications. Use [zh-domain](../zh-domain/SKILL.md) for newly exposed domain ambiguity and [zh-arch](../zh-arch/SKILL.md) for structural uncertainty; pass settled inputs to [zh-spec](../zh-spec/SKILL.md) only within the authorized workflow.

## Completion and failure

A prototype stage is complete when the requested experiment is runnable, relevant cases have recorded observations, the artifact is accessible, and the answer or unresolved decision is explicit. When the assignment includes design finalization, required user approval is also necessary. A runnable draft awaiting feedback can be delivered as such while the approval dependency remains open. A failed experiment can answer the question; a broken artifact with no valid observation cannot.

Business implementation subsequently uses normal implementation and verification standards, even if some experimental logic can be reused. For a local UI adjustment within accepted design, use that design and an appropriate check rather than requiring a new prototype cycle.

## Method provenance

Independently adapted from Matt Pocock's `prototype`, `LOGIC.md`, and `UI.md`. The two experiment shapes are retained; approval, artifact retention, and implementation handoff follow this package's task scope instead of unconditional commits or immediate production promotion. See [source and license](references/upstream.md).
