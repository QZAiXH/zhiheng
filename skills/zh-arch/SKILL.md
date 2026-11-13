---
name: zh-arch
description: Design or revise module responsibilities, interfaces, dependencies, and structural constraints. Use for significant boundaries or technology choices, shallow-module deepening, test seams, or comparison of alternative interfaces; produce checkable architecture decisions rather than implementing a redesign automatically.
---

# Architecture design

Design a structure that satisfies the current task and gives implementation and review a concrete structural acceptance basis. Obtain the goal, domain model, effective decisions, present code/dependency structure, relevant callers, existing tests, and write scope. Read [knowledge](../zh/references/knowledge.md) for project authority and [task-protocol](../zh/references/task-protocol.md) for tracked assignments.

## Working vocabulary

- **Module**: behavior behind an interface, at any useful scale.
- **Interface**: all the caller must know, including types, invariants, ordering, error modes, configuration, and relevant performance constraints.
- **Implementation**: the hidden mechanisms that fulfill the interface.
- **Seam**: a place where behavior can be varied without editing its caller; an **adapter** supplies a concrete behavior at that seam.
- **Depth**: useful behavior obtained for the interface the caller must learn. **Locality**: how strongly changes, knowledge, and verification stay in one place.

These are architecture terms; preserve the project's own business vocabulary. Depth is judged through caller effort and change locality, rather than a ratio of code lines.

## Inspect, design, and compare

1. Trace affected callers, dependencies, persistence, and tests. Separate observed structure from the desired structure. End discovery with the current responsibility/dependency map, binding constraints, actual test entry points, and the structural problem to solve.
2. Define the smallest useful module contract: inputs/results, invariant and error ownership, state or transaction boundaries, dependency direction, and what remains hidden. Ask what complexity would reappear in callers if the module were removed; pure pass-through layers need a concrete justification.
3. Select methods conditionally. For a cluster of shallow modules or dependency/test-seam problems, read [deepening](references/deepening.md). For a consequential interface with plausible competing shapes, read [design it twice](references/design-it-twice.md). A narrow change within an accepted design can go directly to its contract and checks.
4. Compare suitable options against actual callers, behavior preservation, depth, locality, dependency management, testability, and transition cost. Recommend one and expose the consequential trade-off. Important module boundaries and the main stack require the user's confirmation, unless already validly confirmed; [zh-discuss](../zh-discuss/SKILL.md) handles that decision frontier.
5. Define structural acceptance: which module owns each rule, which dependencies are allowed, the public contract, relevant file/package locations under the framework's native layout, and executable checks or a precise review procedure. Map each structural constraint to its verification entry. A functional test alone does not establish architecture conformance.

## Conditional consequences

- For persistence or stored-data semantics, read [data-change](../zh/references/data-change.md); include migration, compatibility, data preservation, and recovery constraints. For deployment topology or release-order changes, inspect the existing release knowledge through [knowledge](../zh/references/knowledge.md) and identify the required update.
- For existing-code reorganization, give an incremental transition with behavior/contract regression checks and integration boundaries. Keep old coverage until replacement coverage demonstrates that it preserves the relevant behaviors; remove only tests and code made obsolete by the accepted change.
- For an enduring non-obvious trade-off, use the self-contained [ADR format](../zh-domain/references/adr-format.md) at the project's authoritative decision location. Ordinary implementation choices need no ceremonial ADR.
- For parallel alternative design or a required independent review, read [host](../zh/references/host.md). Capability gaps change the execution method and claimed verification, not the acceptance criteria.
- For changed requirements or evidence, read [change-recovery](../zh/references/change-recovery.md); return affected contracts and checks for revision rather than overwriting the old basis.

## Return and completion

Return the current/target structure, module contracts, dependency map, alternatives and rationale, confirmed decisions, transition/data implications, structural checks, unresolved dependencies, and specification handoff. Use existing architecture sources; create only the material needed by this task.

Architecture design is complete when a downstream implementer and an independent reviewer can determine both required behavior and required structure, every consequential choice needed for finalization is confirmed, and remaining dependencies are explicit. A comparison-only assignment can end with recommendations; it does not silently accept a candidate. If a crucial contract cannot be established, return its concrete missing fact or decision and continue unaffected design work.

## Method provenance

Independently adapted from Matt Pocock's `codebase-design`, `DEEPENING.md`, and `DESIGN-IT-TWICE.md`. Deep modules and “Design It Twice” draw on John Ousterhout; seams draw on Michael Feathers. See [source and license](references/upstream.md). The included methods require no upstream runtime.
