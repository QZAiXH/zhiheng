# Publish or reuse a GitHub PR

Read this only for an authorized GitHub PR delivery. Start from the verified task commit or range in [the skill](../SKILL.md).

1. Resolve the GitHub host, base code repository and target branch from the ticket and project. Independently resolve the remote's push URL, head repository and task branch. The tracker can live in another repository or service. Use its original ticket URL or an unambiguous project-qualified local ticket locator. Check the whole branch range against the intended target, including commits already on the remote task branch.
2. Follow the repository's PR template. Give the PR a focused title and explain why the change is needed, what changed, how it was verified, and any relevant compatibility or migration impact. Link the original ticket using a reference such as `Related to <issue URL>` so the delivery workflow retains control of closure. [Help others review your changes](https://docs.github.com/en/pull-requests/concepts/helping-others-review-your-changes)
3. Before writing, read the exact remote head with `git ls-remote --refs` against the verified push endpoint. List matching PRs in the base repository with the [List pull requests API](https://docs.github.com/en/rest/pulls/pulls#list-pull-requests), using all states and the head owner and branch. Get the exact candidate by number. Request `Accept: application/vnd.github.full+json` for both reads and verify the head, base and ticket against their full identities and the visible text or link destination in `body_html`. Reuse the matching open PR and preserve its body. If the PR number was lost, check the entire all-state list for the task head and original ticket, including closed PRs whose targets changed. Resolve a conflicting, ambiguous, retargeted, closed or merged PR before another write.
4. If necessary, push only the verified commit to the explicit task ref. For an existing ref, establish that the observed tip belongs to this delivery and verify it is an ancestor of the intended commit with `git merge-base --is-ancestor`. Use `--force-with-lease=<exact-ref>:<observed-oid>` after this check. For a new ref, use the same explicit lease with an empty expected OID to require that the ref is still absent. On a lease rejection, read back the state and reconcile before any retry. Read back the remote ref and the matching PR before proceeding. If the branch is published and a PR is still absent, create it with an explicit base repository, base branch and head, using `gh pr create --repo … --base … --head … --title … --body-file …` or the Create pull request API. With a fork, pass the head owner and branch and identify the head repository when the API needs it.
5. After any ambiguous push or create result, reconcile the remote ref and PR before retrying. If the write took effect, use the readback. If conflicting state appeared or the readback is incomplete, preserve the observed state for recovery. Before reporting publication, verify the exact open PR and the remote ref both show the intended SHA. Record the PR URL and number, base and head repositories and branches, original ticket, and full SHA. Leave the PR open for the user.

For a repeatable publish and readback using Git and `gh api`, run this from the verified linked worktree with Python 3.9+ and an authenticated `gh`. Set `skill_dir` to the absolute path of this skill. Use the repository's existing Git/PR conventions when preparing the message and body.

```sh
python3 -B "$skill_dir/scripts/pull_request.py" publish \
  --repo "$base_repo" --base "$base_branch" \
  --head-repo "$head_repo" --branch "$task_branch" --head "$delivery_sha" \
  --remote "$push_remote" --issue "$issue_url" \
  --title "$title" --body-file "$body_file"
```

The helper renders drafts through the [GitHub Markdown API](https://docs.github.com/en/rest/markdown/markdown#render-a-markdown-document) in GFM mode with the base repository as context. It preserves the template, adds a visible reference only when needed, and waits when required rendering is unavailable.

Use `--host` for GitHub Enterprise, `--pr` when a PR number is recorded, and `--previous-head` only for a verified earlier delivery tip without a PR. A PR number or GitHub CLI exit status alone is insufficient publication evidence. If the helper cannot identify a valid custom remote or an existing link, verify the identities using the native procedure above. [git push](https://git-scm.com/docs/git-push) · [gh pr create](https://cli.github.com/manual/gh_pr_create) · [GitHub pull request templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)

Continue with [Verify checks on the current PR](pr-checks.md) when the delivery stage calls for CI/CD verification.
