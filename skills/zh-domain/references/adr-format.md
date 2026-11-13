# Architecture and domain decision records

Read this when an accepted choice needs enduring rationale. It is a self-contained format usable for domain and architecture decisions.

## Decide whether a record earns its place

An ADR is useful when all three hold:

1. Reversing the choice has a meaningful cost.
2. A future reader would find the result surprising without its context.
3. Real alternatives existed and the choice reflects a trade-off.

Examples include data ownership across contexts, a non-obvious permission boundary, a persistence or integration strategy, a main technology choice with significant switching cost, or a deliberate architectural constraint. Ordinary reversible implementation details belong in the task or code as appropriate.

An explicit project requirement for a decision record still applies. Creating the record does not grant approval: consequential choices need the effective user decision, and an undecided choice must remain proposed.

## Location and numbering

Use the existing decision authority, including context-specific ADR directories when present. Without a suitable convention, use `docs/adr/`. Create the directory only with the first actual record. Follow the project's existing numbering; otherwise inspect existing files and reserve the next unused sequential name such as `0007-order-ownership.md`. Coordinate concurrent numbering through the task owner instead of overwriting another record.

## Minimum useful record

```markdown
# Order ownership belongs to Ordering

Accepted order amendments must preserve the original commitment history.
Ordering owns that history; Billing references an order identity and accepted revision.
This preserves one authority for amendments while allowing independent settlement records.
```

Include context, the decision and its scope, and why it was selected. A paragraph is enough when it carries those facts. Link the effective requirement or user decision and the affected domain/architecture sources.

Add sections only when needed:

- Status: proposed, accepted, deprecated, or superseded with a replacement reference.
- Alternatives: rejected options whose rationale would otherwise be lost.
- Consequences: non-obvious compatibility, migration, operational, or verification effects.
- Constraints: external obligations or limitations that are not apparent from code.

The project's decision-status vocabulary is separate from the task protocol's Chinese task states. Do not invent task status values to match ADR examples.

## Revision and completion

Keep accepted historical rationale. A changed decision records the new basis and replacement relation; update project indexes and affected task references within scope. A pending proposal must not be cited downstream as accepted.

The record is ready when its accepted/proposed status is clear, scope and rationale are explicit, the supporting decision is traceable, and any migration or dependent-contract consequences are discoverable. For a consequential undecided choice, return the prepared alternatives to the decision owner.

Method adapted from Matt Pocock's `domain-modeling/ADR-FORMAT.md`; see [source and license](upstream.md).
