# Independent review

Use this shared procedure for `Do` and `Check`. `Do` runs the full review of a single independently delivered ticket after implementation and tests. `Check` verifies and reuses that evidence and runs the full review of a multi-ticket delivery after integration. Every full review covers `Standards` and `Spec` once.

## 1. Pin the delivery and collect originals

Resolve the agreed comparison base and delivered head to immutable commits in the delivery repository. If the recorded comparison uses three-dot semantics, resolve the recorded fixed point and delivered head and pin their merge base as `base`. Use `git diff <base> <head>` and `git log <base>..<head> --oneline`. Use the same SHAs for both axes. Read code and versioned sources at their recorded revisions. Keep the intended comparison pending if a revision cannot be resolved or the diff is unexpectedly empty.

Collect these inputs with exact locations, versions, and applicable scope.

- The repository or read-only checkout, `base` and `head`, diff and commit list, target delivery version, and the specific scope assigned to the reviewer.
- The original ticket body and approved decision comments, relevant parent spec and child criteria, and the acceptance examples with their starting states, operations, and expected outcomes. Pin the source revision or retain a dated snapshot of mutable tracker text.
- The approved standards applicable to the reviewed revision and paths, including `CODING_STANDARDS.md`, `CONTRIBUTING.md`, and local instructions where present. Record the exact clauses and revisions for the coverage they govern.
- The applicable original business or engineering decisions. Identify the canonical Git path, clause and revision, approved tracker record, or project knowledge URI with its effective version and confirmation source. Read the original and check scope and supersession using the shared knowledge procedure. [Project knowledge](../../plan-feature/references/project-knowledge.md)
- The actual test commands or operations, environment, tested artifact revision, and original results such as exit codes, logs, or receipts. Give reviewers pointers to the raw outputs.

When a standards URI is out of scope, superseded, or conflicts with the Git clause at the reviewed revision, use that revision's applicable Git source for the finding. Include the outdated URI and the current clause in the reviewer brief when already known. Apply the current Git source even if it is the only applicable record the reviewer can read.

Record unavailable required inputs and the coverage they hold pending. If the repository has no documented standards, record where you looked. Apply the repository's rules when they govern a hunk and label any code-smell findings as judgments, with the relevant hunk.

## 2. Match evidence and select review scope

Match each saved axis report and check result against the actual delivery. Verify the comparison base, reviewed head, delivery version, standards and their source revisions, spec and decision sources and versions, examples and their versions, and the scope covered. Check that the raw evidence and report are accessible and that the session record demonstrates independence. Carry forward matching evidence, including reviews from before model routing with unverified model fields.

Use a full review for the first review of the delivery. Where a full review already exists, compare the old and new delivery diffs and source scopes. Select only the added, affected, or missing coverage. Include changed code and its impacted callers or contracts, changed rules, criteria and examples, and test conditions where they affect a result. A newly agreed example on the same code can require a `Spec` recheck while the existing `Standards` evidence still applies.

Map each reused result to the current criterion, example, or hunk and explain why the change leaves its coverage valid. Keep its original observed base, head, sources, and result. Record new coverage at the new pins. An interrupted review can resume with the missing axis or coverage while retaining independently verified results.

## 3. Dispatch with independent context

For each required axis, start a fresh reviewer session with **`fork_context=false`** or the runtime's explicit no-history equivalent on the actual dispatch call. In a routed delivery, [double-loop](../../double-loop/references/dispatch.md) owns the launch and role-specific pair. Run the two axes in parallel when both are required and concurrent slots are available. With limited concurrency, run them sequentially in separate fresh sessions with the same context setting. If a fresh session with explicit context isolation is unavailable, record `pending independent review` for its scope and continue other checks.

Give each reviewer only its brief, the pinned revision and scope, and read-only access to the relevant original inputs from step 1. Use precise source locations or raw excerpts when a ticket thread also contains development discussion or earlier reports. Keep development conversation, the implementer's narrative and self-assessment, coordinator hypotheses, and all reviewer conclusions out of reviewer inputs. Collect the reports in separate outputs visible to the coordinator. Keep each reviewer isolated from the other reviewer's session and report, including during sequential dispatch.

- **Standards.** Inspect the assigned diff against the applicable repository rules. Cite the rule source and affected path and hunk for each violation. Use actual tooling results for rules the project already checks mechanically. Record examined paths and rules, findings, and any coverage gap. For each outdated URI, add a pending knowledge update to the report with the exact URI, reason it is inapplicable, and the applicable Git clause and revision. Return that item to `Act` for reconciliation.
- **Spec.** Trace the delivered behavior to the original ticket or parent spec, including applicable child criteria, approved decisions, and examples. Cite the specific clause or example and the observed behavior for omissions, partial or incorrect behavior, and scope additions. Record checked clauses and examples and any coverage gap. Mark spec coverage pending when its authoritative source is unavailable.

Receive and retain the original reports before summarizing their findings under separate `Standards` and `Spec` headings. Record an incomplete or failed session as pending for its uncovered scope.

## 4. Return reusable review evidence

Attach the following to the handoff reachable from the original ticket, or return it in the `Check` report when the tracker is read-only.

- Repository, ticket and parent references, target version, fixed `base` and reviewed `head`, and the diff and commit-list commands.
- Each axis and its full or affected scope. Record the exact standards, spec, decisions, and example sources and versions, their covered paths, clauses and criteria, and the applicable rule URIs.
- Each session identifier, actual dispatch parameters including its explicit no-history setting, initial assignment or its pointer, and dispatch and return records showing whether execution was parallel or sequential. Retain the separate original reports, findings with source and hunk or result, and relevant raw test evidence with the tested revision.
- Carried-forward results with their original evidence pointers and reason for reuse, newly reviewed coverage with its new pins, and any unresolved findings or pending coverage with the next action.
