# Independent review

Run one full independent `Standards` and `Spec` review per delivery. For a single independently delivered ticket, run it after `Do` tests. For tickets delivered together, run it in `Check` after integration. Use the same coverage checks at the `Do` handoff, in outer `Check` and before recording acceptance.

## 1. Pin the delivery and collect originals

Resolve the agreed comparison base and delivered head to immutable commits in the delivery repository. If the recorded comparison uses three-dot semantics, resolve the recorded fixed point and delivered head and pin their merge base as `base`. Resolve the head from the actual artifact being handed off or accepted, including the containing integration commit when applicable. At each gate regenerate the complete diff from the repository root with `git diff --no-ext-diff --no-textconv --ignore-submodules=none --binary --full-index <base> <head>` and inventory the paths with `git diff --name-status --find-renames --ignore-submodules=none <base> <head>`. Record the commit list with `git log <base>..<head> --oneline`. Use the same SHAs for both axes. Include additions, deletions, both sides of renames, tests and non-code paths. Resolve delivery changes outside the pinned commits before using the diff as evidence. Keep the affected coverage pending when a pin is unavailable or the diff is unexpectedly empty.

Collect these inputs with exact locations, versions, and applicable scope.

- The repository or read-only checkout, `base` and `head`, diff and commit list, target delivery version, and the specific scope assigned to the reviewer.
- The original ticket body and approved decision comments, linked parent spec and child criteria, and their acceptance examples with starting states, operations and expected outcomes. Use the spec recovery order below when a required source is missing.
- The approved standards applicable to the reviewed revision and paths, including `CODING_STANDARDS.md`, `CONTRIBUTING.md`, and local instructions where present. Record the exact clauses and revisions for the coverage they govern.
- The applicable original business or engineering decisions. Identify the canonical Git path, clause and revision, approved tracker record, or project knowledge URI with its effective version and confirmation source. Read the original and check scope and supersession using the shared knowledge procedure. [Project knowledge](../../plan-feature/references/project-knowledge.md)
- The actual test commands or operations, environment, tested artifact revision, and original results such as exit codes, logs, or receipts. Give reviewers pointers to the raw outputs.

### Recover the originating spec

Start with the original ticket and its saved handoff. For missing spec coverage, try these sources in order:

1. Read the full pinned commit messages with `git log --format=%B <base>..<head>` and fetch referenced issues and discussions through the configured tracker. Follow confirmed parent and spec links.
2. Open a spec path supplied by the user.
3. Look under `docs/`, `specs/` and the project's `.scratch/` for a spec matching the feature, scope and target version.

Verify each candidate covers the missing clauses and agrees with the original ticket and its approved decisions. Pin the source revision or retain a dated snapshot of mutable text. Record the exact source and clauses on the original ticket through its writer and reopen the link. For read-only work, include the source and proposed update in the report. If no authoritative source covers a requirement, record the search and request the missing source. Return that `Spec` coverage as pending for `Act`. Continue `Standards` and any verifiable `Spec` scope.

### Check rules and input gaps

When a standards URI is out of scope, superseded, or conflicts with the Git clause at the reviewed revision, use that revision's applicable Git source for the finding. Include the outdated URI and the current clause in the reviewer brief when already known. Apply the current Git source even if it is the only applicable record the reviewer can read.

Record unavailable required inputs and the coverage they hold pending. If the repository has no documented standards, record where you looked. Apply the repository's rules when they govern a hunk and label any code-smell findings as judgments, with the relevant hunk.

## 2. Match evidence and select review scope

Open the separate original reports and raw evidence from the original ticket and its linked handoffs. In a read-only run, use that same entry point for saved evidence and include any new originals with the report. Verify independence from the session record. Qualifying historical reviews may carry forward with unavailable model fields marked unverified.

- Reconcile each axis against the actual path inventory, reviewed base and head, and applicable source versions. Account for every path and hunk in `Standards` and map the behavioral effects and any paths with no spec impact to `Spec`. Account for every applicable criterion and example. A list of files from the implementer or a report summary is insufficient to establish coverage. Record any gaps.
- When only commit identifiers changed, compare the old and new base trees and the old and new head trees, for example with `git rev-parse <revision>^{tree}`, and verify the complete delivery diff, target version, applicable rules, decisions, spec, acceptance criteria and examples still match. Check any review or runtime condition that depends on commit metadata. Record the equivalence and reuse qualifying coverage at its original pins, linking it to the new head.
- When inputs changed, compare the prior and final delivery diffs and source scopes. Dispatch only the added, affected or missing coverage on the relevant axes. Include newly delivered paths, changed hunks and their callers, contracts and affected acceptance cases. Include changed rules, decisions, examples and relevant execution conditions. A new example can require a `Spec` recheck with `Standards` coverage carried forward. Resume interrupted work at the missing axis or scope.
- For a repair, link each original finding to a disposition on the current delivery. Send each open or affected finding's rule or criterion, code location or reproducer, and expected behavior for independent re-verification on its axis. Give the reviewer those inputs without the earlier conclusion. Record the observed result and original finding link in the coverage record. Carry forward unaffected dispositions with their evidence. Keep unresolved findings visible.

For each carried-forward result, map it to the current paths, rules or criteria and record why it still applies. Preserve its original base, head, sources and report. Record each new review at the actual pins. The combined coverage must account for the final diff and acceptance criteria, even when no single report covers them all.

## 3. Dispatch with independent context

For each required axis, start a fresh reviewer session with **`fork_context=false`** or the runtime's explicit no-history equivalent on the actual dispatch call. In a routed delivery, [double-loop](../../double-loop/references/dispatch.md) owns the launch and role-specific pair. Run the two axes in parallel when both are required and concurrent slots are available. With limited concurrency, run them sequentially in separate fresh sessions with the same context setting. If a fresh session with explicit context isolation is unavailable, record `pending independent review` for its scope and continue other checks.

Give each reviewer only its brief, the pinned revision and scope, and read-only access to the relevant original inputs from step 1. Use precise source locations or raw excerpts when a ticket thread also contains development discussion or earlier reports. Keep development conversation, the implementer's narrative and self-assessment, coordinator hypotheses, and all reviewer conclusions out of reviewer inputs. Collect the reports in separate outputs visible to the coordinator. Keep each reviewer isolated from the other reviewer's session and report, including during sequential dispatch.

- **Standards.** Inspect the assigned diff against the applicable repository rules. Cite the rule source and affected path and hunk for each violation. Use actual tooling results for rules the project already checks mechanically. Record examined paths and rules, findings, and any coverage gap. For each outdated URI, add a pending knowledge update to the report with the exact URI, reason it is inapplicable, and the applicable Git clause and revision. Return that item to `Act` for reconciliation.
- **Spec.** Trace the delivered behavior to the original ticket or parent spec, including applicable child criteria, approved decisions, and examples. Cite the specific clause or example and the observed behavior for omissions, partial or incorrect behavior, and scope additions. Record checked clauses and examples and any coverage gap. Mark spec coverage pending when its authoritative source is unavailable.

Receive and retain the original reports before summarizing their findings under separate `Standards` and `Spec` headings. Record an incomplete or failed session as pending for its uncovered scope.

## 4. Return reusable review evidence

Attach the following to the handoff reachable from the original ticket, or return it in the `Check` report when the tracker is read-only.

- Repository, ticket and parent references, target version, fixed `base` and reviewed `head`, and the diff, path inventory and commit-list commands.
- Each axis and its full or affected scope. Record the exact standards, spec, decisions, and example sources and versions, their covered paths, clauses and criteria, and the applicable rule URIs.
- Each session identifier, actual dispatch parameters including its explicit no-history setting, initial assignment or its pointer, and dispatch and return records showing whether execution was parallel or sequential. Retain the separate original reports, findings with source and hunk or result, and relevant raw test evidence with the tested revision.
- Final coverage for both axes, with pointers and reasons for reused results, newly reviewed coverage at its observed pins, each original finding's disposition, and the next action for unresolved findings or pending coverage.
