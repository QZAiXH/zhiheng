---
name: zh-domain
description: Develop or revise domain terminology, entity relationships, lifecycle rules, permissions, and data ownership. Use when the business model is changing or ambiguous, when editing a glossary, or when recording a consequential domain decision; ordinary glossary lookup does not require modeling.
---

# Domain modeling

Produce a precise domain model that can constrain specifications and implementation. Obtain the current scenario, effective decisions, existing model and glossary, relevant code and persistence model, and authorized documentation scope.

## Locate the model

Read [knowledge](../zh/references/knowledge.md) for authoritative sources and writeback. Follow an existing context/glossary map first; use established project locations. Without suitable existing locations, use `docs/domain/` for domain material and `docs/adr/` for accepted decisions, creating files only when there is actual content. Read [task-protocol](../zh/references/task-protocol.md) when consuming or returning tracked work.

Completion of discovery means the relevant contexts, model owners, code/persistence entry points, accepted decisions, and remaining factual gaps are identifiable. A complete project knowledge base is not a prerequisite.

## Model through scenarios

1. Identify overloaded or conflicting words. Compare their use in existing knowledge, actual code, and the user's intended behavior. Propose a canonical business term; separate current behavior from the target when they differ.
2. Exercise concrete scenarios: normal creation/use, partial operations, repeated requests, cancellation, historical records, cross-context references, ownership changes, and visibility versus edit/create rights where applicable. Only select cases that can change this model's meaning.
3. Record entities and identities, relationship cardinality, lifecycle and legal transitions, invariants, ownership, retention, and permission consequences at the depth needed by this task. Keep the business glossary distinct from implementation mappings and detailed behavior rules.
4. Follow the applicable branches below. Finish a modeling round when each implicated term and relationship is either resolved against scenarios or tied to an explicit decision dependency.

| Condition | Action |
|---|---|
| A term is resolved | Read [glossary format](references/glossary-format.md); write the confirmed definition promptly in the authoritative glossary within the allowed scope. |
| One word has different meanings in distinct contexts | Keep context-qualified definitions and document translation/ownership at the context boundary rather than forcing one global meaning. |
| Business meaning, permissions, ownership, or core relationships require a choice | Prepare alternatives and consequences for [zh-discuss](../zh-discuss/SKILL.md), then obtain the user's decision before dependent implementation. Reuse existing confirmation when still applicable. |
| A decision is costly to reverse, non-obvious, and based on a real trade-off | Read [ADR format](references/adr-format.md); record its accepted scope and rationale, or label it proposed until decided. |
| Persistent structure, data meaning, ownership, retention, or constraints may change | Read [data-change](../zh/references/data-change.md). Inspect storage/model/migration history and record a data-impact conclusion with evidence, including backfill, compatibility, validation, and recovery needs. A semantic change can need migration without a new SQL file. |
| The model is difficult to assess on paper | Request a scoped logic experiment from [zh-prototype](../zh-prototype/SKILL.md), retaining the original decision question. |
| A changed instruction invalidates part of the model | Read [change-recovery](../zh/references/change-recovery.md); preserve old decisions and identify affected requirements, migration work, and evidence for the coordinator. |

## Return and completion

Return context and glossary references, the model and invariants, scenario outcomes, accepted decisions with their source, current-versus-target differences, data impact and its evidence, unresolved dependencies, and downstream specification/architecture constraints. Write verified reusable knowledge to its existing source; return proposed writeback when outside the allowed scope.

Modeling is complete when the requested domain questions are traceable, scenario boundaries are explicit, consequential choices are confirmed where finalization was requested, and data implications are carried forward. A glossary file alone is insufficient. If an essential decision is missing, return the exact blocked relationship and continue independent modeling. Domain work does not authorize schema changes or migrations by itself.

## Method provenance

The glossary discipline and selective ADR method are independently adapted from Matt Pocock's `domain-modeling`, `GLOSSARY-FORMAT.md`, and `ADR-FORMAT.md`. Project locations, decision authority, and proactive data-impact handling follow this package's design. See [source and license](references/upstream.md); both format resources are self-contained.
