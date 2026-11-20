# Local Markdown tickets

Each feature has a `.scratch/<feature-slug>/` directory. Its parent spec is `spec.md`. Create one implementation ticket at `issues/<NN>-<slug>.md` per slice. Number new tickets in dependency order, starting at `01`. Keep existing ticket numbers stable. In a linked worktree, use the agreed task worktree or committed ticket revision so both loops reach the same file.

Read the ticket and its parent spec before starting. Record the goal, target version, observable acceptance criteria and any `Blocked by:` ticket references. A `Status:` line near the top holds the current project state. Append progress, decisions, test commands and actual results under the literal `## Comments` heading. Outer acceptance appends the decision there and updates `Status:`. Retain the spec, tickets and evidence they reference after closure.

If a caller supplies a number that occurs under several features, resolve the feature before writing. Give the full repository-relative path when handing off the ticket.
