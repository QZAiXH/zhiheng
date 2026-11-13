# Design it twice

Read this when a meaningful interface decision has plausible alternatives. The purpose is to challenge the first shape using genuinely different contracts, rather than polish several names for the same interface. The method draws on John Ousterhout; this procedure is independently adapted from Matt Pocock's implementation.

## Frame one shared problem

Record the current callers, operation to support, effective domain vocabulary, accepted constraints, invariants, failure and ordering requirements, and dependency categories from [deepening](deepening.md). A short code sketch can make the problem concrete; label it illustrative rather than an accepted design.

State what is open and what is fixed. A comparison cannot meaningfully select between proposals if they solve different requirements or quietly discard constraints.

## Produce distinct candidates

Use at least two materially different shapes when comparison is warranted. A broader design may benefit from three or more perspectives, such as:

- Minimal caller knowledge: a small number of high-value operations that hide coordination.
- Common-path simplicity: the frequent operation is straightforward, with explicit handling of exceptional paths.
- Variation at a real seam: transport or storage changes through justified adapters without exposing internal mechanisms.
- Flexibility: support actual multiple use cases, while making its additional contract cost visible.

Read [host](../../zh/references/host.md) before independent delegation. When available and authorized, give designers separate contexts and distinct emphases but the same raw constraints, relevant paths, and domain/architecture vocabulary. Do not supply a favored answer as an evaluation conclusion. If independent contexts are unavailable, construct alternatives sequentially and label that execution mode; do not claim independent review.

Each candidate supplies:

1. A concrete interface sketch: types, operations, inputs/results, invariants, sequencing, errors, and relevant configuration.
2. An actual caller example for the same scenario, including a meaningful failure or edge case.
3. What complexity stays behind the interface and where each rule lives.
4. Dependency/adapter strategy and actual test surface.
5. Trade-offs, transition cost, and constraints that are difficult to satisfy.

## Compare and recommend

Check all candidates against the fixed constraints before ranking them. Compare caller knowledge, depth, locality, seam placement, behavior verification, actual flexibility needs, and migration cost. Use concrete call sites and scenarios rather than scoring aesthetic preferences.

Explain why the recommendation is stronger. A hybrid is useful only if it remains one coherent contract and still passes the same scenarios. Resolve significant module-boundary or main-stack choices through the user decision boundary; do not mark a candidate accepted merely because the comparison favors it.

## Completion

Return the candidates, common scenarios, comparison evidence, recommendation, decision status, and resulting structural checks. A comparison-only assignment ends here. A finalized architecture assignment additionally records the effective choice and its specification/transition consequences. If no candidate satisfies the constraints, name the conflicting requirements and prepare the smallest decision needed to continue.

See [source and license](upstream.md) for the pinned upstream material and full notice.
