---
name: commit-pr
description: Commit one ticket from its assigned worktree, or publish that commit in a GitHub pull request. Use for explicit ticket commits and routed delivery checkpoints.
---

# Commit or publish a ticket

**Choose the mode.** For a direct request, follow the user's explicit mode. For routed delivery, read `local` or `github-pr` in the target project's tracker guide. Development-only means commit locally. If the mode is unresolved, resolve it before any remote write.

**Verify the scope.** In the assigned task worktree, match its root, branch and `HEAD` to the ticket's recorded path, branch and checkpoint. Confirm the starting revision is an ancestor of `HEAD`. Read the original ticket and the project's Git guidance, including CONTRIBUTING and commitlint when present. Check `git status` for work in progress, then review `git diff --cached`, `git diff` and `git log <starting-revision>..HEAD`. Resolve any in-progress Git operation or unexplained commit before continuing. Reuse a commit or range that already contains the reviewed delivery.

**Commit the reviewed change.** Stage explicit file paths or ticket hunks with `git add -p`. Run `git commit -F "$message_file"` only after confirming that the entire staged diff belongs to the ticket. If unrelated changes are staged in other files, leave them staged and use `git --literal-pathspecs commit --only -F "$message_file" -- <file>...` for complete tracked ticket files. Review both the index and worktree for those paths, including deletions. If selected paths contain unrelated hunks or new untracked files alongside a mixed index, resolve the scope with its owner before committing.

**Write a focused message.** Keep each commit reviewable as one logical change. Follow the repository's message conventions and keep its hooks, signing, and DCO requirements in effect. With no local format, a concise Conventional Commit such as `fix(delivery): verify the active PR head` is a suitable default. Explain the reason in the body when it adds context. Mark breaking changes with `!` or a `BREAKING CHANGE:` footer as applicable. [git commit](https://git-scm.com/docs/git-commit) · [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

**Verify and hand off.** Read back the commit and its paths with `git show HEAD`, and check the remaining index and worktree. For a local delivery, return the branch, full SHA, and observed verification results here. For an authorized PR delivery, follow [Publish or reuse a GitHub PR](references/github-pr.md). For a PR check or acceptance handoff, follow [Verify checks on the current PR](references/pr-checks.md).
