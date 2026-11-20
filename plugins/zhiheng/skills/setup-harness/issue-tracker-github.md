# GitHub Issues

The selected tracker is `<host>/<owner>/<repo>`. Substitute the confirmed target in this guide. Use that target explicitly, including from forks and worktrees. Check it with `gh repo view <host>/<owner>/<repo> --json nameWithOwner,url` when access is available.

- Publish the parent spec and each implementation ticket as separate issues with `gh issue create -R <host>/<owner>/<repo> --title '<title>' --body-file <file>`. Record the returned issue URL.
- Search open and closed issues by goal or scenario with `gh api --hostname '<host>' --paginate --slurp --method GET search/issues -f 'q=repo:<owner>/<repo> is:issue <goal or scenario terms>' -F per_page=100`. Check all pages against the reported `total_count`. An error, `incomplete_results`, a count mismatch or reaching the 1,000-result search limit leaves absence unverified.
- For incomplete searches or a lost create response, also check the repository listing with `gh api --hostname '<host>' --paginate --method GET 'repos/<owner>/<repo>/issues' -f state=all -f sort=created -f direction=desc -F per_page=100 --jq '.[] | select(has("pull_request") | not)'`. Match the goal and scenario in the returned records, including recent creates that search may not yet show. Keep intake or retry pending if the check cannot establish absence.
- Read each candidate and its discussion with `gh issue view <number> -R <host>/<owner>/<repo> --json number,title,body,labels,comments,state,url` and follow its linked parent.
- Link each slice to its parent. Use native sub-issues and blocking dependencies when supported by the selected repository and CLI. Otherwise put `Part of #<parent>` and `Blocked by: #<number>` in the child body. Use a full issue URL for cross-repository references.
- Append evidence or the acceptance decision with `gh issue comment <number> -R <host>/<owner>/<repo> --body-file <file>`. Outer acceptance posts the conclusion before `gh issue close <number> -R <host>/<owner>/<repo>`. A follow-up on a closed ticket still goes through `gh issue comment`.
- When triage is adopted, use `gh issue edit <number> -R <host>/<owner>/<repo> --add-label '<label>'` or `--remove-label '<label>'` with the agreed vocabulary.

PRs as a request surface: no. Preserve a project's existing opt-in. When enabled, read the PR body, conversation and diff with the corresponding `gh pr` commands against the same explicit repository.
