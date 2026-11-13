---
name: zh-tdd
description: Develop agreed behavior through a failing test and minimal implementation, one observable slice at a time. Use for explicit TDD, red-green development, or behavior suited to test-first implementation; deliver the commissioned tested behavior without expanding the surrounding workflow.
---

# Test-Driven Development

Use a red-to-green cycle to implement behavior at a meaningful public boundary. Each cycle learns from a real failure before adding the next behavior. A standalone TDD request ends with its commissioned tested result; committing, publishing, and unrelated planning require their own assignment.

## Choose the boundary

Read the effective behavior, allowed writes, accepted test boundaries, actual test runner and fixtures, and relevant domain vocabulary and decisions. Prefer an existing public interface that catches the required outcome. State what the chosen boundary catches and misses. Reuse accepted test decisions; select ordinary details within those constraints autonomously. If the interface choice changes an important module boundary or leaves required behavior unobservable, prepare that concrete design decision before proceeding.

When persistent identity or a delegated return is involved, read [task-protocol](../zh/references/task-protocol.md). When attaching failure or success evidence, read [verification](../zh/references/verification.md).

Read [behavioral tests](references/tests.md) when designing assertions or evaluating a weak test. Read [boundary doubles](references/mocking.md) when nondeterminism or external dependencies require substitution. These resources contain the stage's testing method; their use does not start another stage.

## Run one slice

1. Pick one required behavior at the selected boundary. Derive the expected result independently from the spec, an accepted example, or a known-good fixture.
2. Write its test, run it, and observe the intended failure before changing production behavior. Distinguish the missing behavior from setup, syntax, or unrelated failures; repair the test environment before trusting the red result.
3. Implement only enough to satisfy that behavior. Run the test and observe green, then check affected existing behavior. Avoid preparing an entire suite for imagined future interfaces before obtaining feedback from the first slice.
4. Repeat for the next required behavior. Preserve the failing and passing observations and identify the actual tested content and inputs. Use deterministic time, seeds, and isolated fixtures where needed.
5. After the relevant behavior is green, consider necessary cleanup separately from the red-to-green cycle. Preserve green checks during any refactor and route consequential structural changes through the applicable design and review process.

When the work touches persistence or stored-data meaning, proactively read [data-change](../zh/references/data-change.md). Use isolated migration and preservation fixtures where required. Public behavioral tests and direct data-integrity checks serve different acceptance criteria; record both when applicable.

## Check and return

Return the selected boundaries, behaviors covered, observed red and green results, actual changes, affected regression checks, and remaining gaps. The requested TDD result is complete only when the tests catch the intended missing behavior, the implementation passes them, and required affected checks hold.

When TDD changes business logic, data meaning, or architecture, use the applicable independent Standards and Spec review in [zh-review](../zh-review/SKILL.md) before final acceptance. A standalone TDD return may finish at the tested stage; record the pending review condition when final acceptance belongs to a later task.

If a suitable boundary or executable test setup is missing, investigate within authorization and report the concrete limitation and recovery condition. Do not substitute an unrelated passing unit test for the real behavior. Use [zh-debug](../zh-debug/SKILL.md) when the failure cause is unclear; read [change-recovery](../zh/references/change-recovery.md) when requirements or tested inputs change. For skill-evaluation work, read [improvement](../zh/references/improvement.md) and keep expected judgments on the evaluation side.

Method adapted from Matt Pocock's `skills/engineering/tdd/SKILL.md`, `tests.md`, and `mocking.md`, `mattpocock-skills` 1.3.2, commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. Changes: accepted-decision reuse, scoped delivery, real evidence, and explicit data-integrity criteria. Test methods below are independently rewritten in English.

<!-- Upstream license notice for adapted methods and accompanying stage resources.
MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
-->
