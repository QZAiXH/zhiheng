# GitHub Issues

The selected tracker is `<host>/<owner>/<repo>`. Substitute the confirmed target in this guide. Use that target explicitly, including from forks and worktrees. Check it with `gh repo view <host>/<owner>/<repo> --json nameWithOwner,url` when access is available.

- Publish the parent spec and each implementation ticket as separate issues with `gh issue create -R <host>/<owner>/<repo> --title '<title>' --body-file <file>`. Record the returned issue URL.
- Find candidates across open and closed issues with `gh issue list -R <host>/<owner>/<repo> --state all --search '<goal or scenario terms>'`. Check recent issues in the same tracker when retrying a create. Read each candidate and its discussion with `gh issue view <number> -R <host>/<owner>/<repo> --json number,title,body,labels,comments,state,url` and follow its linked parent.
- Link each slice to its parent. Use native sub-issues and blocking dependencies when supported by the selected repository and CLI. Otherwise put `Part of #<parent>` and `Blocked by: #<number>` in the child body. Use a full issue URL for cross-repository references.
- Append evidence or the acceptance decision with `gh issue comment <number> -R <host>/<owner>/<repo> --body-file <file>`. Outer acceptance posts the conclusion before `gh issue close <number> -R <host>/<owner>/<repo>`. A follow-up on a closed ticket still goes through `gh issue comment`.
- When triage is adopted, use `gh issue edit <number> -R <host>/<owner>/<repo> --add-label '<label>'` or `--remove-label '<label>'` with the agreed vocabulary.

PRs as a request surface: no. Preserve a project's existing opt-in. When enabled, read the PR body, conversation and diff with the corresponding `gh pr` commands against the same explicit repository.
