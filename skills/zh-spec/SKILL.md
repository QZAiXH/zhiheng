---
name: zh-spec
description: Synthesize accepted requirements, decisions, models, and prototype feedback into an executable local specification with observable acceptance criteria. Use when discussion is ready to become a spec; surface consequential gaps without restarting settled interviews or implementing the feature.
---

# Executable Specification

Turn the available decisions into a specification an implementer and an independent evaluator can use. A standalone request delivers the specification and its readiness assessment; it does not automatically schedule or implement the work.

## Inputs and conditional rules

Obtain the current goal, scope, original requirement sources, accepted decisions, relevant project facts, and requested delivery boundary. Follow explicit source paths and versions. Reuse valid confirmations rather than asking the user to repeat the discussion.

- When reading or writing a persistent task, read [task-protocol](../zh/references/task-protocol.md). When creating a separate spec, use the [spec template](../zh/assets/templates/spec.md) and link it from the task entry; a short spec may remain in that entry.
- When consolidating sources or updating project knowledge, read [knowledge](../zh/references/knowledge.md). Keep current implementation facts separate from target requirements.
- When identifying persistence or data semantics, read [data-change](../zh/references/data-change.md), including how to support a no-migration conclusion.
- When defining checks and evidence, read [verification](../zh/references/verification.md).
- When replacing requirements or assessing old artifacts, read [change-recovery](../zh/references/change-recovery.md). For a skill-maintenance specification, also read [improvement](../zh/references/improvement.md).

Read shared resources directly, without starting an overall coordination workflow.

## Synthesize

1. Inspect the affected implementation and existing test boundaries enough to make the specification executable. Use the project's domain vocabulary and accepted ADRs. Identify contradictions between sources, implementation, and intended behavior.
2. Express the user problem and intended outcome, included and excluded behavior, actors and permissions, significant states and failure paths, and relevant compatibility constraints. Include only scenarios that affect the current assignment.
3. Preserve accepted business definitions, data ownership, entity relationships, stack, module boundaries, contracts, and prototype decisions. Retain compact prototype-derived state or schema fragments when they communicate an accepted decision more precisely than prose. Point to implementation locations where needed for execution; avoid caching incidental details.
4. Map each required outcome to an observable acceptance criterion and a real check boundary. Prefer existing public interfaces and the highest useful boundary. State input conditions, expected results, and evidence needed; distinguish business, UI, and structural acceptance when they differ. Surface a consequential new test-boundary decision with its coverage and limitations; ordinary choices inside accepted constraints proceed autonomously.
5. Proactively assess schema changes, existing-data conversion or backfill, initialization or dictionary data, indexes, constraints, and changed persistence meaning. Specify the needed compatibility transition, migration artifacts, rehearsal, preservation checks, and recovery conditions. Absence of a migration file is only a clue.
6. List unresolved dependencies with the behavior they block and the decision or evidence needed. If a key business, permission, ownership, entity, architecture, or stack choice is still open, prepare a concrete option and its impact for the appropriate decision step. For a new page, main flow, or broad layout change, carry the accepted interactive prototype as an implementation prerequisite.
7. Save the authoritative specification locally and retain links to adopted external inputs and their versions. Keep requirements in one authority; a tracker is an optional correspondence, not the execution record.

## Completion and return

Return the spec location or compact spec, adopted source versions, acceptance-to-check mapping, data impact conclusion, readiness, and any blocking dependency. Ready portions can move to `zh-plan`; unresolved portions remain explicitly gated. A spec containing unresolved critical choices is not implementation-ready merely because it has been written.

The stage is delivered when the requested requirements are faithfully synthesized and the readiness boundary is explicit. If the assignment specifically requires an implementation-ready spec, outstanding mandatory decisions or checks keep that result incomplete. Do not silently replace an accepted requirement to make the spec appear ready.

Method adapted from Matt Pocock's `skills/engineering/to-spec/SKILL.md`, `mattpocock-skills` 1.3.2, commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. Changes: local authority, proportionate scenarios, accepted-decision reuse, active data impact, and stage-scoped delivery. No upstream installation is required.

<!-- Upstream license notice for adapted methods and accompanying stage resources.
MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
-->
