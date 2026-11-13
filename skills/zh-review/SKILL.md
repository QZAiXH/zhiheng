---
name: zh-review
description: Review a defined change against documented project standards and effective requirements in independent Standards and Spec contexts. Use for branch, patch, work-in-progress, or required implementation review; report findings and rechecks separately from acceptance.
---

# Independent Two-Axis Review

Review the actual assigned artifacts on two separate axes. Standards asks whether the change follows applicable project rules; Spec asks whether it satisfies effective requirements and accepted decisions. Keep both conclusions visible. A review assignment delivers findings and coverage, even when the reviewed change fails.

## Pin inputs

Obtain the exact review scope, effective spec and decision versions, project standards, prior findings, and report write location. Read [task-protocol](../zh/references/task-protocol.md) for persistent or delegated review and [verification](../zh/references/verification.md) for artifact identity, evidence scope, and recheck applicability.

For a branch, resolve the requested fixed point and comparison semantics. Use merge-base comparison when the assignment is changes introduced since the common ancestor; use direct comparison when the requested endpoints require it. Record the resolved baseline, candidate identity, actual diff method, and affected commits. Include relevant working-tree, staged, and untracked changes for a work-in-progress review. For non-Git work, use explicit before/after material or a scoped file manifest and content fingerprints.

Investigate a missing baseline or source through task records and project facts. Ask only for unresolved information that changes the review. An empty scope gets an explicit no-change result; unavailable comparison inputs get a concrete coverage gap.

## Prepare independent contexts

Read [host](../zh/references/host.md) before using independent execution. Give each axis a fresh context separate from the implementer's conclusions and from the other axis. Parallelize when supported; sequential execution in separate contexts also preserves independence. Supply the original requirements, actual artifact access, relevant standards, source versions, bounded report writes, and check entrypoints. Supply prior findings only for a requested recheck.

Business logic, permissions, data structure, and architecture changes require this independent review. If the host lacks the necessary independent context, investigate available authorized alternatives, return the missing capability, and keep required independent review unmet. A local low-impact self-check may be reported as such, without relabeling it independent review.

## Standards axis

Locate applicable instructions, coding and contribution standards, architectural rules, domain vocabulary, and accepted ADRs. Include `CODING_STANDARDS.md` and `CONTRIBUTING.md` when present. Follow project authority when rules conflict.

Inspect changed code and affected context for violations with concrete consequences and source locations. For qualitative maintainability judgment, read [design signals](references/design-signals.md). Separate documented violations from labeled design concerns; documented project choices override generic heuristics. Reuse valid tool results for mechanical rules and investigate their failures rather than duplicating lint output.

## Spec axis

Compare original requirements and effective accepted decisions with the actual behavior and structure. Identify missing or partial requirements, incorrect implementations, unrequested expansion, and unmet test or prototype prerequisites. Cover business meaning, permissions and ownership, entity relationships, module and framework constraints, UI decisions, and compatibility where they apply.

Proactively cross-check relevant models, persistence code, business semantics, and migration artifacts. Read [data-change](../zh/references/data-change.md) for data-affecting changes and investigate absent migration artifacts rather than assuming no migration is needed. Check preservation, conversion, constraints, compatibility, execution and retry ownership, and recovery evidence. When the spec is unavailable, report the Spec axis as `未执行` with its missing input; do not infer the intended feature solely from its implementation.

## Return and recheck

For each finding, return the axis, artifact location, violated requirement or rule and its source, observed consequence, severity and rationale, suggested correction, and necessary recheck. Keep Standards and Spec reports separate, with finding counts and coverage gaps for each. Return a justified no-findings result when appropriate.

A review request does not implicitly authorize product repairs. Route findings to the responsible executor; when correction and recheck are commissioned, inspect the corrected actual artifacts and rerun affected observations. Record resolved, remaining, and newly introduced findings. Read [change-recovery](../zh/references/change-recovery.md) when sources or artifacts change and reassess old review coverage.

The review stage is delivered when both requested axes have traceable reports or explicit missing conditions. The reviewed change's readiness remains a separate result; a missing mandatory axis prevents full review completion. Acceptance belongs to [zh-verify](../zh-verify/SKILL.md). For skill-maintenance review, read [improvement](../zh/references/improvement.md) and assess case quality, comparison validity, regressions, and adoption evidence.

Method adapted from Matt Pocock's `skills/engineering/code-review/SKILL.md`, `mattpocock-skills` 1.3.2, commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. Changes: local requirements, actual WIP/non-Git artifacts, host-verified independence, data impact, and separate review-task delivery and reviewed-result readiness. Design-signal attribution is retained in its reference.

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
