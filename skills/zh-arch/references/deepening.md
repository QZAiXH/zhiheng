# Deepening modules

Read this for a shallow cluster, scattered business rules, or a dependency/test seam that makes callers carry implementation complexity. The working vocabulary is defined in [zh-arch](../SKILL.md).

## Find a useful responsibility

Trace an actual operation through callers and helper modules. Identify repeated coordination, ordering constraints, knowledge of storage or transport, and rules duplicated across call sites. Propose a module that hides that complexity behind a coherent contract. A smaller method count is useful only when callers also need less knowledge to use it correctly.

Describe the external interface separately from internal seams. Keep internal adapters private when only the module needs to know about them. Use dependency injection where behavior actually varies or isolation is needed; avoid creating a port merely because a class has a dependency.

## Classify dependencies

| Dependency | Design and verification strategy |
|---|---|
| In-process computation or memory state | Consolidate behavior when cohesive; test through the public contract with real internal logic. No adapter is needed solely for a pure calculation. |
| Locally substitutable storage or I/O | Check that an appropriate substitute exists and matches the contract relevant to this task. Keep the seam internal where possible and exercise the module with that substitute; verify important differences against the actual dependency. |
| Remote service owned by the project or organization | Define a focused port where transport must vary; keep business decisions in the module. Use the actual network adapter in production and a justified in-memory/test adapter for logic checks, with integration/contract checks for transport assumptions. |
| Uncontrolled external service | Inject a focused port, use a mock adapter for controlled responses and failure cases, and verify important external assumptions with authoritative documentation or an authorized contract/integration check. |

A production adapter and a justified test adapter establish real variation. One adapter is a reason to question an extra abstraction, not a mechanical ban on a needed boundary. Do not expose storage-shaped methods if the caller's business operation can be expressed directly.

## Compare the old and new shape

For each affected caller, write its required knowledge before and after the change. Include legal ordering, transaction ownership, failure handling, and required configuration. Identify which complexities become local and which still cross the interface. If deleting the proposed wrapper would remove only forwarding code, justify it through a concrete current requirement or simplify it.

Record allowed dependency direction and who owns each invariant. A module should accept required dependencies through a suitable construction/operation boundary rather than secretly creating an uncontrolled external connection. Prefer explicit input/results for pure decisions; isolate necessary effects behind real seams.

## Verification and transition

Map existing behavior and regression checks to the proposed contract. Add or adapt checks that exercise observable outcomes through that interface, including relevant failure and ordering behavior. Keep justified integration checks where an in-memory substitute cannot establish actual dependency behavior.

Move behavior incrementally when a single replacement would obscure failures. Once replacement checks demonstrably cover the relevant behaviors, remove tests made obsolete by the removed implementation. Do not delete still-useful coverage merely because it is named a unit test. Internal refactoring should normally leave contract-level expectations unchanged.

Return a transition sequence, real test entry points, and precise structural checks: public surface, allowed imports/dependencies, invariant ownership, and the locations that must change. Where no executable structural check exists, provide a bounded review procedure with concrete files and prohibited dependency relationships.

## Completion

A deepening proposal is ready when the caller benefit is visible, dependency categories and seams are justified, behavior preservation has a real checking path, and the intended structure can be independently reviewed. Significant changed boundaries still require the effective user decision before implementation.

Method adapted from Matt Pocock's `codebase-design/DEEPENING.md`; deep-module concepts draw on John Ousterhout and seams on Michael Feathers. See [source and license](upstream.md).
