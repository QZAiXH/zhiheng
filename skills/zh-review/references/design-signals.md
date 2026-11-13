# Qualitative Design Signals

Read this reference when the Standards axis needs maintainability judgment beyond documented mechanical rules. These are heuristic concerns, not automatic violations. Report only a concrete instance in the reviewed scope, with its consequence and a proportionate alternative. Project standards and accepted design decisions take precedence.

| Signal | What to investigate | Possible correction |
| --- | --- | --- |
| Unclear naming | A name hides the operation or domain concept the caller needs to understand. | Use the domain term or clarify the responsibility. |
| Duplicated logic | The same rule has multiple implementations that can diverge. | Share that rule at its natural owner. |
| Feature envy | A method primarily interprets another module's data. | Move the responsibility toward the data owner. |
| Traveling data groups | The same related values repeatedly cross boundaries together. | Consider a coherent value or request type. |
| Primitive obsession | A primitive representation repeatedly obscures a real domain invariant. | Represent that invariant where it is enforced. |
| Repeated branching | The same discriminator drives parallel branch trees in several places. | Centralize the varying behavior when that simplifies the current requirement. |
| Scattered change | One rule requires edits across many unrelated modules. | Gather ownership of that rule. |
| Divergent responsibilities | One module changes for multiple unrelated reasons. | Separate responsibilities along actual dependencies. |
| Speculative generality | A hook, parameter, or abstraction exists only for an imagined requirement. | Remove the unused generality. |
| Navigation chains | Callers traverse internal object relationships to perform one operation. | Expose the relevant operation at an appropriate boundary. |
| Empty delegation | An intermediate layer delegates without providing a useful contract or policy. | Simplify the route while preserving necessary boundaries. |
| Misfit inheritance | A subtype rejects substantial inherited behavior. | Consider a narrower contract or composition. |

Avoid turning a small review into a general redesign. A concern earns a finding when the current change produces an identifiable maintenance or correctness cost. Suggested restructuring remains subject to the assignment's scope and accepted module boundaries.

Method source: the smell baseline in Matt Pocock's selected `code-review/SKILL.md`, version 1.3.2, which attributes these concepts to Martin Fowler, *Refactoring*, chapter 3. Descriptions here are rewritten and remain judgment calls. The stage entry retains the upstream license notice.
