# Behavioral Tests

Read this reference when choosing assertions or deciding whether a test would catch a real regression.

## Observe a contract

Test a public operation and the result available to its caller. For example, create a record through the public write operation and retrieve it through the public read operation; assert its required content. A test of the number of calls to an internal repository constrains implementation rather than that behavior.

Choose a boundary wide enough to exercise the actual interaction. A bug involving two concurrent callers needs a check that includes both callers and their shared conditions. A single-caller test can supplement that check but cannot replace it.

Use the project's domain vocabulary in names. Each test should communicate one coherent behavior, although verifying that behavior can require several related assertions. Include significant failure and permission paths required by the specification.

## Make the expected result independent

An accepted worked example can define an expected total of `42`. Recomputing the expected value with the same algorithm as the implementation can repeat its defect. Derive expectations from requirements, independently verified examples, or explicitly reviewed fixtures.

Snapshots are useful when their content has a meaningful review standard. Refresh them only after inspecting the behavioral change. A test that merely asserts its own fixture or constant provides no evidence about production behavior.

## Observe the red result

Run the test before the implementation change. Its failure must name the missing or wrong outcome under investigation. A broken import, unavailable database, or unrelated assertion establishes a setup gap instead.

When a regression test is added after a fix already exists, use an authorized isolated before-fix version or a reversible, inspected mutation to establish sensitivity. Restore the intended version and rerun; record this as regression validation rather than inventing a test-first history.

## Separate acceptance dimensions

Public API checks establish behavioral contracts. Dedicated migration checks may also inspect rows, indexes, constraints, counts, or preserved identifiers directly because data preservation is their explicit contract. Structural checks can inspect dependency direction or schema shape when the spec requires those structures. Name the criterion each check serves.

Method source: Matt Pocock's selected TDD `tests.md` and `SKILL.md`, version 1.3.2. The stage entry retains the upstream license notice.
