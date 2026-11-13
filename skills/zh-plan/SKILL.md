---
name: zh-plan
description: Turn an effective specification into locally managed, verifiable work slices with real blocking dependencies and an executable frontier. Use for implementation planning, staged migrations, or wide refactors; return the plan without starting implementation unless commissioned.
---

# Verifiable Work Plan

Produce a task graph whose next executable work can be handed to a fresh executor. A standalone planning request ends with the plan and its readiness, not completed code.

## Establish authority

Obtain the effective spec and decisions, current project and test entrypoints, delivery target, allowed writes, existing budget limits, and unresolved dependencies. Inspect the affected code enough to choose actual verification boundaries.

Read [task-protocol](../zh/references/task-protocol.md) when creating or revising a persistent plan or dispatchable slice. Use the [plan template](../zh/assets/templates/plan.md) and [slice template](../zh/assets/templates/slice.md) for separate artifacts; keep a simple single-unit plan in the task entry when sufficient. Read [knowledge](../zh/references/knowledge.md) when resolving authoritative constraints, and [verification](../zh/references/verification.md) when assigning check and evidence obligations.

## Build the graph

1. Start with observable results. Prefer narrow vertical slices that connect the layers actually needed for a complete behavior, including its checks. Size each ready slice so a fresh context can understand and finish it from the supplied pointers.
2. Create a prerequisite task only when its artifact or decision genuinely gates other work: for example a missing investigation, an accepted contract, setup, or migration preparation. Make its own result and check explicit. Greenfield plans connect `zh-init` to the first commissioned feature and its verification.
3. Give each ready slice a goal, write boundary, source versions, observable completion conditions, actual check command or operation, required inputs, deliverables, and delivery target. Record missing test conditions as explicit dependencies rather than supplying an invented command.
4. Add only real blocking edges. Check that IDs and references resolve, all dependencies exist, and the graph has no cycle. Identify the frontier whose blockers are accepted and whose required execution conditions are satisfied; an executor's returned claim alone does not satisfy a blocker.
5. Evaluate parallelism separately from graph readiness. Separate outputs, authorized workspaces, available host capabilities, and integration prerequisites must support it. Use an allowed sequential path when independent work cannot be isolated. Read [host](../zh/references/host.md) before relying on delegation or isolation semantics.
6. Plan integration and cross-slice acceptance. Integration that changes tested content needs affected checks and review again. Individual completed slices do not establish the overall delivery result.
7. Detail the immediate frontier and retain later outcomes and known dependencies. Refine distant work as evidence and decisions arrive. Present granularity, blocking edges, and verification boundaries for review; reuse existing approval and proceed within an already authorized implementation assignment. Do not introduce an automatic approval gate for ordinary sequencing.

## Conditional plans

- **Persistence or data meaning:** proactively inspect the relevant spec, models, and persistence paths, then read [data-change](../zh/references/data-change.md). Plan required migration artifacts, existing-data conversion, compatibility, isolated rehearsal, preservation and constraint checks, execution ownership, and recovery. Derive ordering from actual compatibility and project tooling. Record evidence when no migration is needed.
- **Wide mechanical refactor:** expand with a compatible new form, migrate callers in verifiable batches, then contract after callers have moved. If intermediate batches cannot pass alone, state that limitation and make them dependencies of an explicit integration-and-verification slice. Preserve behavior and structural acceptance throughout the applicable transition.
- **Changed requirements or interrupted execution:** read [change-recovery](../zh/references/change-recovery.md), update affected revisions and edges, and reassess returned work and evidence. Retain unaffected work.
- **Generic skill improvement:** read [improvement](../zh/references/improvement.md). Include representative feedback cases, old-versus-candidate comparisons, affected regressions, independent evaluation, and version adoption as verifiable results.

## Completion and return

Return the local plan, slice and source identities, graph and frontier, check entrypoints, integration conditions, and open decisions. Persist status and revision in their protocol-defined authority rather than duplicating them in slice details.

Planning is complete when the graph is coherent, the next ready slice is executable from its inputs, and blocked work has specific unblock conditions. A requested fully executable plan remains incomplete while mandatory inputs are missing. Return the concrete gap and continue any independent planning that remains useful.

Method adapted from Matt Pocock's `skills/engineering/to-tickets/SKILL.md`, `mattpocock-skills` 1.3.2, commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. Changes: local graph authority, actual test entrypoints, progressive planning, proportionate approval, and accepted-result dependencies. No upstream tracker setup is required.

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
