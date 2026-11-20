# Specs and tickets

## Use the project's tracker

Follow the issue-tracker guide linked from the project's instructions. Update the original ticket and retain its history. A discussion stays in the conversation. If the destination is undecided or a write is unavailable, provide the finished draft and identify where it still needs to be recorded.

- **Local Markdown.** Follow the existing layout. The setup default is `.scratch/<feature-slug>/spec.md` for a parent and `issues/<NN>-<slug>.md` below the same directory for each implementation ticket. Number new tickets in dependency order from `01`, keeping existing numbers stable. Keep `Status:` near the top, use `Blocked by:` for real ticket references and append decisions, evidence and handoffs under `## Comments`. Give the full repository-relative ticket path in the agreed worktree.
- **GitHub or GitLab.** Use the selected repository, tracker states and labels. Reuse the original issue and any existing parent. Link children in both directions using repository-qualified references and native blocking relationships where supported. After an authorized write, reopen the issue and links. If the response was lost, check for the existing issue or comment before retrying.

## Describe a checkable result

A small ticket can be a paragraph and an example. Use the project's spec format for shared decisions. Capture the actor, current behavior and source, desired outcome, scope, release or iteration, and relevant model or API decisions with confirmation and rationale. Cite Git decisions by path, section and revision and verified knowledge by its original URI.

For each acceptance example give the starting state, action, expected observable result and an existing test command or reproducible operation through the actual entry point. Include a boundary, compatibility case or structural check when it distinguishes two possible implementations. For a shared contract, trace the **same input** from one participant through the others to the final observable outcome. Put that check in the parent and link to it from the affected tickets.

For example, if a librarian changes the pickup branch for a reservation, check the reader's view after the change. A reservation that started third in line should still have its original ID and position and show the new branch. Each screen can work on its own even if the change loses the reservation's position.

## Split only when the work needs it

Propose slices around independently demonstrable or verifiable outcomes. For each, state what it delivers, its acceptance example and check, the parent clause, and which prerequisite must be integrated before work can start. Explain what the dependent ticket needs from that prerequisite. A shared parent or adjacent ticket number alone creates no dependency.

Show the proposed breakdown and blocking edges to the user. If they have already approved this split, use that approval. Record the confirmed tickets in the chosen tracker and link them from the original. Identify the tickets ready now and the reason each remaining ticket must wait. For a repository-wide migration that cannot land in behavioral slices, add the compatible structure first, migrate callers in verifiable batches, then remove the old structure after every dependent batch has landed.

Keep the shared decision in the parent. Each child carries its own deliverable and an actionable check. For a long-running decision index, link each open question to the answer it needs or the tickets it affects. A resolved question supplies a decision. An implementation ticket completes when its behavior has been verified.

## Leave a recoverable handoff

From the original ticket a receiver can find the scope ready for development, outstanding decisions and owners, prerequisites, approved design, individual and integrated checks, and the next action. Label checks as observed or pending and pin existing evidence to the version actually examined. Append later decisions with the clauses and ticket examples they change. Retain the sources that explain previous results.

## Pause and resume at an existing limit

When the user, project or runtime already sets a budget or time limit, check it at stage boundaries and save progress before starting work that could exhaust it. Reachable checkpoints matter when a hard stop leaves no final turn. At the limit, pause the affected action and record completed items, pinned artifacts and original evidence, the obstacle or remaining checks, and the first concrete next action on the original ticket. Use a durable evidence pointer when the checkpoint refers to a temporary output.

On resumption, read that checkpoint from the original ticket and confirm the restored allowance and target revision. Continue at the saved next action and reuse observed results whose inputs, sources, revision and conditions still apply. Keep discussion and report-only work within their existing access scope. Return the checkpoint in the response or designated report when the tracker is read-only.
