---
name: accept-delivery
description: "Run acceptance checks on a delivered ticket or integrated spec, produce a new acceptance report, close an accepted delivery, or run a maintainer-requested delivery retrospective. Summarize an existing report directly when that is the request."
---

# Accept delivery

Own outer-loop `Check` and `Act`. A request to complete delivery continues through `Act`. For an acceptance report only, use read-only access to Git, the tracker, and project knowledge throughout `Check`. Use an isolated copy or disposable test output for checks that need writable state, then return the report in the requested channel. A development-only request ends at `Do`. Its single-ticket review uses the shared review procedure directly.

Write reports, tracker notes, and handoffs in the user's language unless the user requests another output language. Preserve identifiers, commands, URIs, and fixed tracker fields.

A maintainer's request to run `retro` on a delivery starts from the named ticket and its actual evidence. Use the [retrospective procedure](references/retro.md) within that request's scope.

## 1. Resume from the original ticket

Read the project's instructions, the original ticket and its comments, the approved spec and examples, and the saved `Do` handoff. For an existing execution limit, use [pause and resume](../plan-feature/references/ticket-and-spec.md#pause-and-resume-at-an-existing-limit) within the request's access scope. For a split delivery, read the parent spec and linked children. Verify that each required child landed in the pinned integration revision using the recorded merge or equivalent integration evidence.

Recover the `Do` checkpoint for this delivery from the original ticket. It carries the delivered scope, target version, comparison base and delivered head, actual commands and results with raw evidence pointers, applicable rule URIs, unmet acceptance criteria, independent review reports or their pending status, findings with evidence, and the next stage. Recover missing facts from the original sources and mark any remaining gaps against the affected criteria.

If an earlier `Check` passed and left only an approved Episode pending, compare the current delivery, criteria and conditions against that checkpoint and open the original evidence. When all pins and conditions match and the required originals are readable, carry forward the observed business results. Go directly to [Act](#4-act-on-the-evidence) to resume synchronization, or stop with the checkpoint in report-only mode. If anything relevant changed or an original is unavailable, complete the affected `Check` coverage first.

Resolve business decisions for the target version. Read known rule URIs and verify their applicability, confirmation source, and supersession. Use the shared procedure for project-scoped discovery and source verification. [Project knowledge](../plan-feature/references/project-knowledge.md)

## 2. Check the independent review

Use the shared procedure to match the recorded reviews to the fixed base and delivered head, the standards, spec, decisions and examples at their applicable versions, and the required coverage. Use it for dispatch, reuse, and affected rechecks. [Independent review](references/independent-review.md)

When assigned by [double-loop](../double-loop/SKILL.md), return the fixed inputs for needed review coverage to that route and continue independent acceptance checks. For a defect or business decision, return the corresponding `Act` disposition and exact input evidence to the route for dispatch. In report-only mode return the disposition with the report.

- **One independently delivered ticket.** Reuse the full `Standards` and `Spec` review from `Do` once its evidence checks out. Obtain any missing independent coverage through the shared procedure.
- **Several tickets delivered together.** Once all required slices have landed, use one full independent `Standards` and `Spec` review of the integrated commit against the agreed base and parent spec. Keep slice results as supporting evidence for the integrated review.

On resumption, carry forward matching results and review only added, affected, or missing coverage. Keep unresolved findings and pending independent review visible in the acceptance report.

## 3. Verify acceptance through real entry points

Run the agreed acceptance examples on the pinned delivery through the project's actual entry points. Once the required slices are integrated, run the parent spec's cross-ticket examples on the combined artifact and trace the same input to its final observable outcome. On a recheck, run added or affected checks and carry forward earlier results whose code, applicable rules, examples, and execution conditions still apply.

For each criterion, record the source and expected result and pin the delivery and environment. For a check with an observation, include the starting state and input, command or operation, observed result, and original evidence pointer. Use these result values:

| Result | Evidence required |
| --- | --- |
| `pass` | The observed result matches the expectation and its original evidence is readable. |
| `fail` | The observed result differs from the expectation. Record the reproducer and return path. |
| `not_run` | The check has no verifiable result for this delivery. Name the missing condition or evidence and the exact entry point for running or recovering the check. |
| `not_applicable` | The check's applicability condition is absent from this delivery. Cite the source of that condition and the relevant scope evidence. For a migration check, a pinned copy-only diff and a check that applies only to migrations can establish this. |

Treat historical `pending` as awaiting verification until the applicable raw evidence is available or the check can be run. Missing evidence or an unavailable environment belongs under `not_run`. If applicability itself is unknown, record how to establish it and keep the result open. Continue independent checks. Verify the actual preferences, discoveries and decisions in the `Do` handoff against their sources before handing them to `Act`.

Return the original ticket and target version, pinned base and head, separate `Standards` and `Spec` results with their coverage and evidence, per-criterion observations, and the next action for each open item. Include the parent acceptance conclusion for an integrated delivery. In report-only mode, stop here.

## 4. Act on the evidence

Before handing off, append the acceptance checkpoint to the original ticket with the pinned delivery, criterion results, evidence, disposition and next action. Include the affected child tickets and criteria for an integrated delivery. Check for an existing update before retrying an uncertain tracker write. If a write is unavailable, return the completed record and identify the pending update. [Specs and tickets](../plan-feature/references/ticket-and-spec.md)

- **Implementation diverges from an agreed rule.** Automatically return the affected scope to `Do` with the tested revision, rule source, failing input, expected and observed results, reproducer, and affected criteria. Resume `Check` from the saved repair handoff on its new head. Use the shared procedure to reuse matching review evidence and fill any remaining affected review coverage. Rerun the affected real-entry checks. If the same failure recurs, use the new evidence to diagnose it or record the concrete blocker before another attempt. [Implement ticket](../implement-ticket/SKILL.md)
- **A goal, model, or rule requires a decision.** Return the original ticket, target version, conflicting sources or new scenario, concrete outcomes for the same input, decision owner, and affected tickets and criteria to `Plan`. Resume the dependent work after the owner confirms a decision. [Plan feature](../plan-feature/SKILL.md)
- **Evidence remains missing.** Continue evidence collection where possible. Keep dependent criteria open and record what is needed to resume.
- **Review is complete and every applicable required criterion is `pass`.** Verify the scope basis for each `not_applicable` result. Required `fail`, `not_run`, and unresolved legacy `pending` results keep the ticket open. Resolve blocking findings and verify the reports, outputs and reproducer from their final locations on the original tracker records. Follow the [evidence and cleanup procedure](references/delivery-evidence.md) and the Episode closure rule below. For an integrated delivery, record the overall result on the parent and close the affected children when their evidence is reachable. Reopen the records to verify status and links.

Keep ticket-specific evidence on the ticket. Publish only verified, authorized material using the [project knowledge procedure](../plan-feature/references/project-knowledge.md), including an approved [Episode](../plan-feature/references/project-knowledge.md#publish-or-reuse-an-episode). If business acceptance passed and the sole remaining item is that Episode, keep the original ticket open with “business acceptance passed, Episode pending sync” (`业务验收通过、经验待同步` in Chinese). Keep its checkpoint and evidence reachable. After exact readback at the same URI, link it and proceed with closure using still-applicable acceptance results.

When the maintainer requests `retro`, apply the [retrospective procedure](references/retro.md) to the verified delivery evidence and link the decisions and resulting work from the original ticket.
