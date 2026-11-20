---
name: accept-delivery
description: "Run acceptance checks on a delivered ticket or integrated spec, produce a new acceptance report, close an accepted delivery, or run a maintainer-requested delivery retrospective. Summarize an existing report directly when that is the request."
---

# Accept delivery

Verify delivery in outer-loop `Check`. A completion request continues through `Act`. In a routed delivery, return the evidence and proposed disposition to the coordinator for writes, dispatch and any closure. For an acceptance report only, use read-only Git, PR, tracker and project knowledge access throughout `Check`, including reviews. Use an isolated copy or disposable test output for checks that need writable state. Return the report in the requested channel and leave project worktrees and tracker state intact.

Write reports, tracker notes, and handoffs in the user's language unless the user requests another output language. Preserve identifiers, commands, URIs, and fixed tracker fields.

A maintainer's request to run `retro` on a delivery starts from the named ticket and its actual evidence. Use the [retrospective procedure](references/retro.md) within that request's scope.

## 1. Resume from the original ticket

Read the project's instructions, the original ticket and its comments, the approved spec and examples, and the saved `Do` handoff. For an existing execution limit, use [pause and resume](../plan-feature/references/ticket-and-spec.md#pause-and-resume-at-an-existing-limit) within the request's access scope. For a split delivery, read the parent spec and linked children. Verify that each required child landed in the pinned integration revision using the recorded merge or equivalent integration evidence.

Recover the `Do` checkpoint for this delivery from the original ticket. It carries the delivered scope, target version, comparison base and delivered head, actual commands and results with raw evidence pointers, applicable rule URIs, unmet acceptance criteria, independent review reports or their pending status, findings with evidence, and the next stage. Recover missing facts from the original sources and mark any remaining gaps against the affected criteria.

Read the project's delivery choice from its tracker guide. Match the recorded local branch and full commit to the delivered artifact. For `github-pr`, also match the code repository, PR, base and head to that artifact. For writable completion, the coordinator uses [commit-pr](../commit-pr/SKILL.md) to publish or recover the linked PR if still needed. A report-only run records the observed state and any missing evidence.

If an earlier `Check` passed and left only an approved Episode pending, match the current delivery and review coverage using step 2. Open the original acceptance evidence. Carry forward verified business results where the criteria and conditions still apply, and complete only any affected or missing checks before resuming synchronization.

Resolve business decisions for the target version. Read known rule URIs and verify their applicability, confirmation source, and supersession. Use the shared procedure for project-scoped discovery and source verification. [Project knowledge](../plan-feature/references/project-knowledge.md)

## 2. Check the independent review

Start from the original ticket and reopen both axis reports and the raw evidence. Use the [independent review procedure](references/independent-review.md) to reconcile their coverage and original findings against the actual delivery diff and applicable criteria. Use the procedure for first review, equivalent revisions, and affected rechecks. Keep unresolved findings and pending coverage visible in the report.

When assigned by [double-loop](../double-loop/SKILL.md), return the fixed inputs for missing or affected review coverage to the coordinator and continue acceptance checks that can run independently.

## 3. Verify acceptance through real entry points

Run the agreed acceptance examples on the pinned delivery through the project's actual entry points. Once the required slices are integrated, run the parent spec's cross-ticket examples on the combined artifact and trace the same input to its final observable outcome. On a recheck, run added or affected checks and carry forward earlier results whose code, applicable rules, examples, and execution conditions still apply.

For `github-pr`, check [CI/CD on the current PR revision](../commit-pr/references/pr-checks.md). Record which checks apply, their run or status evidence and the observed head. Keep an expected check open while it is missing or pending. A confirmed absence of applicable remote checks needs its basis and passing agreed local checks on that delivery. Reuse this evidence in `Act` after verifying the PR still identifies the same revision and result.

For each criterion, record the source and expected result and pin the delivery and environment. For a check with an observation, include the starting state and input, command or operation, observed result, and original evidence pointer. Use these result values:

| Result | Evidence required |
| --- | --- |
| `pass` | The observed result matches the expectation and its original evidence is readable. |
| `fail` | The observed result differs from the expectation. Record the reproducer and return path. |
| `not_run` | The check has no verifiable result for this delivery. Name the missing condition or evidence and the exact entry point for running or recovering the check. |
| `not_applicable` | The check's applicability condition is absent from this delivery. Cite the source of that condition and the relevant scope evidence. For a migration check, a pinned copy-only diff and a check that applies only to migrations can establish this. |

Treat historical `pending` as awaiting verification until the applicable raw evidence is available or the check can be run. Missing evidence or an unavailable environment belongs under `not_run`. If applicability itself is unknown, record how to establish it and keep the result open. Continue independent checks. Verify the actual preferences, discoveries and decisions in the `Do` handoff against their sources before handing them to `Act`.

Return the original ticket and target version, pinned base and head, separate `Standards` and `Spec` results with their coverage and evidence, per-criterion observations, and the next action for each open item. Include the parent acceptance conclusion for an integrated delivery. In report-only mode, stop here. In a routed completion, send the report and proposed disposition to the coordinator.

## 4. Act on the evidence

The coordinator in a routed delivery, or the current session in a direct completion, applies the disposition. Persist its checkpoint on the original ticket with the pinned delivery, criterion results, evidence and next action. Include affected children and criteria for an integrated delivery. Use [tracker readback](../plan-feature/references/ticket-and-spec.md#reconcile-uncertain-writes). If a write is unavailable, return the record with the pending update.

- **Implementation diverges from an agreed rule.** Use the [rework budget and checkpoint](../double-loop/references/dispatch.md#budget-and-resume-rework) before dispatch. Include the tested revision, rule source, failing input, expected and observed results, reproducer, and affected criteria. Resume independent review and affected real-entry checks from the saved repair handoff on its actual new revision.
- **A goal, model, or rule requires a decision.** Return the original ticket, target version, conflicting sources or new scenario, concrete outcomes for the same input, decision owner, and affected tickets and criteria to `Plan`. Resume the dependent work after the owner confirms a decision. [Plan feature](../plan-feature/SKILL.md)
- **Evidence remains missing.** Continue evidence collection where possible. Keep dependent criteria open and record what is needed to resume.
- **Candidate for acceptance.** Resolve the final revision and verify [complete review coverage](references/independent-review.md) and dispositions of original findings on it. All applicable required criteria must be `pass`, each `not_applicable` must have a scope basis, and blocking findings must be resolved. A changed delivery, incomplete review, missing original or required `fail`, `not_run` or unresolved legacy `pending` keeps the affected ticket open until verified.

Apply the project's delivery condition to that same revision before closing the original ticket.

- **`local`.** Record the retained task branch, full delivery commit, agreed verification results and acceptance. Reopen the commit through the branch so the user can integrate it later.
- **`github-pr`.** Verify that the linked PR is open in the code repository and that [the applicable checks](../commit-pr/references/pr-checks.md) pass for the accepted revision, or that their confirmed absence and the passing local verification are recorded. Reconcile the PR head and checks again immediately before closing. A failed check goes through the repair procedure on the same PR. After a push, verify the new commit, affected review and checks. Continue waiting for expected checks during completion. If interrupted, save the PR, head, pending checks and next observation on the ticket. Leave the PR open for the user to merge.

Once the applicable gates and the Episode rule below are satisfied, record the decision and follow [evidence readback and worktree cleanup](references/delivery-evidence.md). Reopen the delivery branch, checks and review reports from the ticket after cleanup, then close and verify the recorded status and links. For an integrated delivery, record the parent result and apply the same gate to each delivered child.

Keep ticket-specific evidence on the ticket. Publish only verified, authorized material using the [project knowledge procedure](../plan-feature/references/project-knowledge.md), including an approved [Episode](../plan-feature/references/project-knowledge.md#publish-or-reuse-an-episode). If business acceptance passed and the sole remaining item is that Episode, keep the original ticket open with “business acceptance passed, Episode pending sync” (`业务验收通过、经验待同步` in Chinese). Keep its checkpoint and evidence reachable. After exact readback at the same URI and confirmation of its durable verification receipt from the original ticket, resume the closure gate against the current delivery.

When the maintainer requests `retro`, apply the [retrospective procedure](references/retro.md) to the verified delivery evidence and link the decisions and resulting work from the original ticket.
