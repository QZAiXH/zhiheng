# Project knowledge in planning and delivery

Use the ordinary project identity, bound resource root and operations in the project's knowledge guide (usually `docs/agents/project-knowledge.md`). Plan, Do and independent reviewers read under that same binding. Keep the original ticket as the progress record.

## Find the decision for this release

For a known URI, `read` it directly. Otherwise `find` using the business scenario and target release, with `target_uri` limited to the project and `level: [2]`. Then `read` the relevant originals. Check the object, trigger, conditions, confirmation source, effective version and supersession. Search rank alone cannot select a rule. When changing an existing rule, also check for later decisions in scope.

Use an explicitly confirmed delivery range as written. When a decision names no version, use the next regular delivery in the schedule at the time of confirmation, including one already in development. Write that delivery target in the original knowledge body, using its iteration or delivery ticket if it has no version number yet. Apply the decision from that delivery onward until superseded or withdrawn. Maintenance hotfixes for earlier releases use their existing rule unless the decision owner explicitly approves a backport covering that release and scenario. Read that approval together with the new decision. If the target at confirmation cannot be established, keep the affected criterion open until it can be resolved.

For example, with `v1.8` already in development as the next regular release, an unversioned decision applies to `v1.8`. A `v1.7` hotfix follows its previous rule until a confirmed `v1.7` backport covers the scenario.

Git owns the project's glossary, model documents and accepted ADRs. Read the clause at the applicable path and revision, for example with `git show <revision>:<path>`. A ticket owner's confirmed business decision can also be authoritative in its own right. If only older material is available, mark the specific criterion that lacks an applicable decision. If two effective decisions disagree for the same input, show both sources and outcomes to the decision owner.

## Recover a missing or stale rule reference

1. Start with the scenario and target release or Git revision from the original ticket or the confirmed standalone setup or refresh scope. Use either for read-only recovery and preview. Follow the effective project entry and knowledge guide to their live Git links and exact rule URIs. For an established project with an empty store or missing, renamed or stale references, also inspect the related Git history of the entry and guides. Use `git log --follow -- <path>` for known paths and `git log --all -S '<URI, rule term or managed block marker>'` to locate earlier references when a path disappeared. Open deleted or renamed entries with `git show <revision>:<old-path>`. Follow the referenced sources and open the confirmed tickets and their linked decisions, including decisions that replace or withdraw the rule. Treat historical references as leads to check against the target.
2. Resolve the applicable version and scenario from the target Git source and confirmed decisions. Track the ruling clause, its Git path, section and revision or confirmation ticket, and any confirmed supersession, retirement or backport. If a rule still applies, use the confirmed source and restore its current verified reference as needed. For a replacement, point the current entry to the clause effective for the target release. For a retirement, remove its active reference for that scope and preserve its Git or ticket history and any earlier release it still covers.
3. Preview the effective entry or guide changes with those sources. If the applicable original is missing from OpenViking, point to the confirmed Git clause or ticket decision while proposing the exact body and URI for any required restoration. With approval, follow [checkpoint, write and recover](#checkpoint-write-and-recover). Confirm the restored URI by exact readback before using it as a verified reference. Reopen the repaired entry and guide and follow their links. Record the resolution on the original ticket or standalone refresh record. If the scope, source or write authority is insufficient, record the affected reference, write or criterion and what would resolve it. Continue independent checks.

## Record what has been confirmed

| Material | Action |
| --- | --- |
| Ticket-specific choice, open question, check or experiment | Record the evidence, affected criterion and next action on the original ticket. An inner-loop discovery goes to outer `Check` with its observed version and evidence. |
| Agreed terminology, model or architectural tradeoff | Update the project's existing Git source under its conventions. Reserve an ADR for a consequential choice whose rationale future readers need. Cite the file, section and revision. If the change exists only in the working tree, retain the pending Git reference on the ticket until a containing revision exists. |
| Confirmed rule reusable by another task | In Plan, write at confirmation. For a discovery from Do, write after outer `Check` verifies the evidence and obtains any required business confirmation. Use a stable URI under the bound project's `knowledge/` and record the conclusion, scope, applicable version, rationale and confirmation source. A rule grounded in Git cites the containing revision. Reuse a verified equivalent record. |
| Completed factual research | `write` the full Markdown report under the project's `research/`, including the question, applicable version or date, primary sources and outstanding facts. Link its verified URI with a short conclusion on the ticket. Record a later design choice with its own confirmation. |
| Reusable task experience | Publish a verified, approved [Episode](#publish-or-reuse-an-episode) during `Act`. |

Use the project's existing client or the [native HTTP procedure](../../setup-harness/openviking.md#put-daily-use-in-the-project-guide) under the ordinary project identity. For every approved write, follow the checkpoint and readback steps below, including research and corrections.

## Correct a rule and trace its impact

| Finding | Treatment |
| --- | --- |
| The stored text misquotes its authoritative source | Check the original at its revision. Correct the transcription at the same URI and read it back. Record the correction and its source. |
| An authorized decision changes business meaning | Give the new decision a new versioned URI. Include its effective scope and the URI it supersedes. After verifying it, update the previous record's applicability and forward reference while preserving its historical text and source. Read back the updated record. |
| Implementation differs from an accepted rule | Preserve the rule. Record expected and observed behavior, the tested revision and the reproducing check as a deviation for delivery. |

For a correction or replacement, update the current ticket and trace known open tickets through the shared spec, references to the URI or clause, and tracker links. Name each affected ticket, its specific acceptance item and the recheck it needs. Preserve earlier evidence with its version. An unresolved decision holds only the criteria that depend on it.

<a id="recover-an-uncertain-write"></a>

## Checkpoint, write and recover

1. **Before any write**, leave the exact intended URI, target release or Git revision, confirmation source, and complete approved UTF-8 body on the original ticket or in a linked durable attachment. For standalone setup or refresh, reuse the confirmed decision record if it supplies the full checkpoint, or save the checkpoint in the configured tracker. Require approval and a linked, writable result destination. Keep that write pending if either is missing. Preserve an approved source file byte for byte as a linked attachment. Reopen the checkpoint and open the body as the next owner would. A digest can verify the original when the attachment moves. Keep one submission owner per URI at a time.
2. Read the exact URI before submitting a new record or resuming an uncertain write. If the full UTF-8 body matches, finish with zero writes. If an authenticated native `404` confirms this resource is missing, proceed to step 3. For a separately authorized correction, verify the current text and reconcile its scope before proceeding to step 3. A different body or other error leaves the checkpoint pending for reconciliation.
3. For the write authorized in step 2, load `content` directly from the approved UTF-8 bytes and verify outgoing bytes against the original and any recorded digest. Preserve line endings and the final newline. Submit `uri`, `content`, `mode: "replace"`, `processing_mode: "vectors_only"` and `wait: true` once. Read the **same URI** and compare the full body with the checkpoint. Link the verified URI from the ticket or the authorized result record linked to the checkpoint. Reopen that record. Record indexing separately and check discovery when the handoff depends on `find`.
4. When readback cannot confirm the intended body, preserve the original and record the observed error, pending synchronization and exact next action. Resume at step 2. Hold the affected criterion and continue independent work using verified sources.

## Publish or reuse an Episode

During `Check`, verify the handoff's preferences, findings and decisions against their original sources. For a case approved for reuse, `Act` writes a concise factual record to a stable URI under this project's `episodes/`. Use the original ticket and delivery revision to identify the case and retain its chosen URI on the ticket for retries. Include the task goal and starting context, actual attempts, commands or checks and observed outcomes, evidence links, and the skill versions or fingerprints in effect. Include verified preferences, findings or decisions when they explain what happened. Check that the original evidence opens from its durable location.

Use [checkpoint, write and recover](#checkpoint-write-and-recover) and link the Episode to the original ticket after exact readback. For a new ticket with a similar problem, use its known URI or `find` in the project's `episodes/` by scenario, then `read` the original and open the evidence. Check scope and revision before applying the lesson. A case can inform a decision, and an applicable rule still comes from its authoritative source.
