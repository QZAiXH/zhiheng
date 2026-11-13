---
name: zh-implement
description: Implement an effective local specification or assigned work slice, including features, refactors, and migration preparation, with relevant checks and a reviewable result. Use for authorized coding work; preserve the commissioned scope and delivery target.
---

# Implementation

Implement the assigned result against its current requirements. A standalone slice request ends at that slice's required implementation and checks. A broader implementation assignment can consume the authorized ready frontier; it does not imply permission to publish or deploy.

## Bind the work

Obtain the authoritative task entry, optional slice and dispatch identity, requirement revisions and source versions, executor workspace, allowed writes, completion conditions, check entrypoints, and delivery target. Inspect actual files and user changes before editing.

When consuming a persistent task or returning delegated work, read [task-protocol](../zh/references/task-protocol.md). Read [knowledge](../zh/references/knowledge.md) for affected project constraints and factual writeback, and [verification](../zh/references/verification.md) before binding checks to actual artifacts. Use the [dispatch/return template](../zh/assets/templates/dispatch.md) only when creating a needed execution record.

## Execute the ready work

1. Verify that dependencies are accepted and required decisions are effective. Read the authoritative main-workspace entry rather than trusting an old task copy in an isolated checkout. Inspect the affected domain language, ADRs, interfaces, and existing tests.
2. Choose the smallest change that satisfies the current criteria. Follow the project's framework-native layout and mature existing components. Keep business behavior, UI decisions, and architectural constraints visible as separate obligations when needed.
3. For behavior suited to test-first development or an explicit TDD request, use this package's [zh-tdd](../zh-tdd/SKILL.md) at the accepted boundary. For an unclear defect or repeated failure without new information, use [zh-debug](../zh-debug/SKILL.md). These methods stay inside the current assignment.
4. Implement and check incrementally. Use the actual affected tests, type and build checks, and behavioral or structural observations required by the project. A refactor preserves externally required behavior while satisfying accepted structural changes. Add meaningful tests for new behavior; choose checks proportionate to a reversible, low-impact edit rather than mirroring implementation details.
5. Inspect data impact proactively from both the effective requirements and actual changes. For models, persistence behavior, schema, data meaning, or migration clues, read [data-change](../zh/references/data-change.md). Prepare migration or data-processing artifacts using existing tools; check preservation, conversion, constraints, repeat runs, partial completion, retry, and relevant application-version coexistence. Rehearse in an authorized isolated environment. Return execution order, ownership, verification, and recovery requirements to downstream stages; runtime migration uses its applicable environment authorization.
6. Respect accepted decisions. If implementation requires a new key business definition, permission or ownership rule, core entity relationship, important module boundary, or main stack, prepare the concrete choice and impact before the affected change. New pages, main-flow changes, and broad layout changes require an accepted interactive prototype first. Continue unaffected work.
7. For an authorized multi-slice assignment, integrate accepted results in dependency order and reevaluate the frontier. Read [host](../zh/references/host.md) before delegation, isolation, notification, or stopping a worker. Delegate bounded writes and current source pointers; use the authorized sequential path when isolation is unavailable.

## Review and return

Business logic, permission, data structure, and architecture changes require independent Standards and Spec review through [zh-review](../zh-review/SKILL.md). Local low-impact edits use applicable checks and self-review. Fix in-scope defects with new evidence, then recheck affected behavior and review findings. Integration changes may invalidate earlier evidence.

Return actual changes, adopted requirement versions, workspace and artifact identity including relevant uncommitted and untracked content, check results and evidence, review status, data impact and migration artifacts, remaining conditions, and next steps. A delegated executor returns its result; the coordinator accepts it against current authority. An independently invoked agent can also perform the coordinating role within its assignment.

Implementation is complete when the commissioned result and required checks and reviews hold for the actual artifacts. Mandatory failures or unexecuted checks keep the affected result incomplete. For missing tools or dependencies, investigate and repair within authorization or use an equivalent route that preserves the criteria. Read [change-recovery](../zh/references/change-recovery.md) for requirement changes, interruption, stale returns, or evidence invalidation; preserve a recoverable result when a concrete blocker remains.

For an explicitly scoped skill-maintenance task, read [improvement](../zh/references/improvement.md): make an evidence-backed generic correction and preserve comparable evaluation and regression results. Business-task implementation alone does not authorize generic skill edits.

Method adapted from Matt Pocock's `skills/engineering/implement/SKILL.md` and `skills/engineering/implement-spec/SKILL.md`, `mattpocock-skills` 1.3.2, commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. Changes: local authority, optional isolation, current-result acceptance, active migration preparation, and commissioned delivery instead of unconditional commits or platform actions.

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
