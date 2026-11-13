---
name: zh-debug
description: Diagnose unclear defects, performance regressions, or repeated failures using a symptom-specific reproduction loop and falsifiable hypotheses. Use for debugging; include a minimal fix and regression checks when repair is commissioned, and stop at findings for diagnosis-only requests.
---

# Defect Diagnosis and Repair

Establish a feedback signal for the reported symptom, use evidence to isolate its cause, and perform the commissioned correction. Distinguish a diagnosis request from a repair request before changing product behavior.

## Inputs and rules

Obtain the expected and observed behavior, affected version and environment, available evidence, reproduction conditions, authorized writes, and requested endpoint. Read relevant project vocabulary and accepted decisions. Show only necessary, redacted command output; retain credentials in their normal secure source.

Read [task-protocol](../zh/references/task-protocol.md) when tracking an investigation or returning delegated findings, and [verification](../zh/references/verification.md) when recording baseline, failure, or regression evidence. Read [diagnosis loop](references/diagnosis-loop.md) before constructing the reproduction and consult its relevant branches during the investigation.

## Investigate

1. Build and actually run a symptom-specific feedback loop. Prefer an automated test, request, CLI fixture, browser assertion, replay, or minimal harness that can distinguish the reported failure from the expected result. Pin relevant inputs. For intermittent behavior, measure and improve reproduction frequency; for performance, establish a comparable baseline and measurement method.
2. Confirm the loop observes the user's actual symptom. Minimize the case one input or condition at a time while preserving that failure. Necessary code inspection and data collection can support construction of the loop; avoid claiming a cause before testing its prediction.
3. Rank plausible, falsifiable hypotheses. State the observation each predicts and run discriminating probes one variable at a time. Share consequential new findings without waiting for approval on routine experiments. Prefer focused debugger observations, traces, plans, or tagged temporary instrumentation to indiscriminate logging.
4. Continue when there is new evidence, a concrete hypothesis, or a verifiable correction. If the same action fails without new information, narrow the loop, change the probe, or revise the plan. Respect actual user, project, and host limits rather than inventing a fixed retry quota.
5. If reproduction remains unavailable, preserve attempted conditions and actual observations, distinguish hypotheses from findings, and identify the smallest missing environment, artifact, or access. Investigate and repair authorized prerequisites and continue unaffected work; return a specific unblock request when external input is required.

## Repair branch

When repair is commissioned, turn the minimized case into a failing regression check at a boundary that reaches the real bug pattern, then apply the smallest supported correction. Use [zh-tdd](../zh-tdd/SKILL.md) where that method fits. Rerun the original scenario and affected checks. If no adequate regression boundary exists, document the missing protection and its acceptance impact rather than adding a shallow substitute.

Proactively inspect whether the defect or fix changes persistence, schema, or existing-data meaning. When applicable, read [data-change](../zh/references/data-change.md), prepare and rehearse required migration or recovery artifacts, and verify preserved data. A proposed irreversible transformation or new ownership rule requires its concrete decision before execution.

## Completion and return

Return the observed symptom, executable reproduction or precise remaining gap, adopted source and artifact versions, tested hypotheses, supported cause and repair path, and evidence. Diagnosis-only work ends at the requested findings; an unresolved investigation reports what remains unresolved. A repair is complete when the original symptom is corrected and required regression and affected checks pass, with required independent review satisfied.

Remove attributable temporary instrumentation after preserving needed evidence. Read [change-recovery](../zh/references/change-recovery.md) for requirement changes, interruption, or cleanup and retention. Read [host](../zh/references/host.md) when an investigation depends on delegation, waiting, or stopping a process. For generic skill failures, read [improvement](../zh/references/improvement.md), separate project and tool causes from skill causes, and return evidence to the maintenance task.

Method adapted from Matt Pocock's `skills/engineering/diagnosing-bugs/SKILL.md` and `scripts/hitl-loop.template.sh`, `mattpocock-skills` 1.3.2, commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. Changes: diagnosis-only delivery, evidence-led continuation, proportionate loops, scoped repair, and an optional output template for human-only reproduction.

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
