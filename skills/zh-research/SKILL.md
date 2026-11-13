---
name: zh-research
description: Investigate a bounded factual question using primary sources and save traceable findings. Use for repository behavior, official documentation, API or dependency facts, and evidence needed by a design decision; keep recommendations separate from user decisions.
---

# Research

Answer a specific factual question and make the answer reusable by the next stage. Research does not itself approve a design or implement the proposed solution.

## Frame and investigate

1. Obtain the question, affected version and environment, scope, intended consumer, available sources, and expected output. Resolve facts discoverable in the environment directly. If ambiguity would produce materially different research, identify that ambiguity before investigating the dependent branch.
2. Read [knowledge](../zh/references/knowledge.md) to find existing authoritative material. When working from a tracked assignment, read [task-protocol](../zh/references/task-protocol.md) and bind findings to its actual revision and sources.
3. Select the investigation branch below. Read [host](../zh/references/host.md) before background delegation; give an independent investigator the raw question, relevant sources, output scope, and current basis. Keep working on independent questions. If delegation is unavailable, perform the bounded research sequentially and report that execution mode.
4. Follow each decision-relevant claim to the source that owns it. Record versions, paths or URLs, relevant locations, access date for mutable sources, and the observation or short excerpt supporting the claim. Distinguish documentation, executable behavior, and inference.
5. Compare the results with the original question. Resolve material contradictions by version, environment, or a small authorized experiment; preserve unresolved contradictions with their consequences. End when each requested question has a supported answer or a concrete evidence gap and follow-up.

| Question | Evidence and branch completion |
|---|---|
| How does this repository work? | Inspect the actual call path, configuration, tests, and relevant execution entry; cite file locations and content version. Separate current behavior from intended behavior. |
| What does a library, API, platform, or standard support? | Use official documentation, specifications, first-party APIs, or source at the relevant version. Verify mutable claims against current primary sources when current behavior is requested. |
| Should an existing dependency be adopted? | Compare requirement fit, maintenance activity, license, runtime/framework compatibility, and relevant security information; identify what remains unknown. Offer a recommendation with evidence. |
| Does a technical hypothesis hold? | Use a minimal isolated experiment within authorized scope. Record exact input, command/tool, environment, observed result, and limits of the experiment. Read [verification](../zh/references/verification.md) for evidence binding. |
| The answer depends on business policy or a significant trade-off | Return factual alternatives to [zh-discuss](../zh-discuss/SKILL.md); do not turn an investigator's preference into an accepted decision. |
| Feedback concerns a recurring skill failure | Read [improvement](../zh/references/improvement.md); gather original requests, skill versions, environments, repeat cases, and counterexamples before attributing cause. |

## Findings artifact

Use the project's existing research location; otherwise keep a focused note with the task, linked from its entry. A short request can return a short answer without creating an unnecessary record. Within the note, include:

- The question, scope, requested versions, and actual investigation basis.
- A direct answer with claim-local source references and an explicit distinction between facts and inferences.
- Reproduction details for experiments, conflicting evidence, unknowns, and the effect of each unknown on the pending decision.
- A recommendation only where requested or useful, with the next action and the decision owner.

Use one authoritative findings note per investigation; update references rather than copying it into specifications. Preserve necessary raw evidence in an accessible task location. Read [change-recovery](../zh/references/change-recovery.md) when a changed question or source version affects returned findings; identify which conclusions still apply.

## Return and completion

Return the findings location, actual basis and revision, supported answers, uncertainty, evidence links, and any decision or investigation dependency. Research is complete when all requested questions are covered and source claims can be checked. An unavailable source yields a documented gap and an alternative investigation path; mandatory unanswered questions remain unresolved. Do not report an unrun experiment as evidence or mark the parent implementation complete.

## Method provenance

Independently adapted from Matt Pocock's `research`: primary-source investigation and a reusable findings artifact are retained; fixed background tooling and repository assumptions are replaced with actual host capability and project knowledge conventions. See [source and license](references/upstream.md). No upstream skill is called at runtime.
