---
name: commit-pr
description: Commit one ticket from its assigned worktree, or publish that commit in a GitHub pull request. Use for explicit ticket commits and routed delivery checkpoints.
---

# Commit or publish a ticket

**Choose the mode.** For a direct request, follow the user's explicit mode. For routed delivery, read `local` or `github-pr` in the target project's tracker guide. Development-only means commit locally. If the mode is unresolved, resolve it before any remote write.

**Verify the scope.** In the assigned task worktree, match its root, branch and `HEAD` to the ticket's recorded path, branch and checkpoint. Confirm the starting revision is an ancestor of `HEAD`. Read the original ticket and the project's Git guidance, including CONTRIBUTING and commitlint when present. Check `git status` for work in progress, then review `git diff --cached`, `git diff` and `git log <starting-revision>..HEAD`. Resolve any in-progress Git operation or unexplained commit before continuing. Reuse a commit or range that already contains the reviewed delivery.

**Prepare the commit message.** Set `message_file` to a temporary file outside the worktree. Write the complete message and verify the file before staging or committing. Follow the repository's message conventions, hooks, signing, and DCO requirements. With no local format, use a concise Conventional Commit such as `fix(delivery): verify the active PR head`. Explain the reason in the body when useful. Mark breaking changes with `!` or a `BREAKING CHANGE:` footer when applicable. [git commit](https://git-scm.com/docs/git-commit) · [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

**Commit the reviewed change.** Stage explicit paths or ticket hunks with `git add -p`. Confirm that the entire staged diff belongs to the ticket before running `git commit -F "$message_file"`. If unrelated edits are staged in other paths, review the index and worktree for the intended paths, including deletions. For a new file that belongs entirely to the ticket, stage it with `git add -- <new-file>`. Immediately run `git --literal-pathspecs commit --only -F "$message_file" -- <file>...` with the explicitly reviewed complete paths, including that new file. If a selected path mixes ticket and unrelated hunks, commit only after isolating the ticket hunks without losing either set.

**Verify and hand off.** Read back the commit and its paths with `git show HEAD`, and check the remaining index and worktree. For a local delivery, return the branch, full SHA, and observed verification results here. For an authorized PR delivery, follow [Publish or reuse a GitHub PR](references/github-pr.md). For a PR check or acceptance handoff, follow [Verify checks on the current PR](references/pr-checks.md).
