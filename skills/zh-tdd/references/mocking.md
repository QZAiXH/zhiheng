# Boundary Doubles

Read this reference when a test depends on an external system or uncontrolled input.

Prefer real in-process components and an isolated test database when those exercise the required behavior reliably. Substitute external APIs, clocks, random sources, or filesystem boundaries when a real dependency would make the test unsafe, nondeterministic, or needlessly expensive. Preserve the contract relevant to the test.

Keep internal collaborators real when possible. A mock of the implementation's own call graph often passes while the user outcome is broken. Observe the public result instead of asserting an internal call count or order, unless that interaction is itself an explicit external contract.

Pass a boundary dependency through an existing injection point or small adapter when substitution is needed. Prefer a specific operation such as `paymentClient.charge(request)` to a generic fake request engine with extensive conditional behavior. Add only the interface required for the current behavior.

A fake proves behavior under its modeled responses. Keep fixtures aligned with the actual external contract, and add an appropriate isolated integration or contract check when external compatibility is part of acceptance. For migration behavior, use the actual database engine and migration tool when their semantics determine the outcome.

Pin time and random seeds when they influence the result. Use per-test data or filesystem locations, and clean only resources attributable to the test. Document a remaining external dependency as an execution condition rather than replacing it with a fake that removes the failure being tested.

Method source: Matt Pocock's selected TDD `mocking.md`, version 1.3.2. The stage entry retains the upstream license notice.
