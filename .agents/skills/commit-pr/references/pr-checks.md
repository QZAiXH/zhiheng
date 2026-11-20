# Verify checks on the current PR

Use this from acceptance or when monitoring an authorized delivery PR. This procedure reads GitHub and returns evidence to the caller. The caller owns acceptance, tracker updates and rework.

## Bind the observation

1. Reopen the exact PR in the **base code repository** by its recorded number. Verify it is open, links the original ticket, targets the intended base branch, and has the recorded head repository, branch and full delivery SHA. Confirm the current head ref, including when it lives in a fork. If the PR has moved, hold the old evidence and verify the new delivery before checking it.
2. Establish what must run for this PR from project delivery rules, active branch rulesets and applicable classic branch protection, the workflow definitions and event, branch or path filters, and any project-specific external CI. Include expected checks even when GitHub has yet to display them. Compare with the exact PR's checks and status-checks box. A required status with an expected GitHub App must come from that app. If a check run and a legacy status share a required name, both must pass.
3. Use the current SHA GitHub evaluates. GitHub uses the test merge commit when it has applicable status evidence and otherwise uses the latest head. Read `mergeable` and `merge_commit_sha` from the open PR's REST response. Wait if mergeability is still being computed. Verify a test merge SHA against the PR's current head and base through its commit parents. A pending or failed check on this test merge cannot be replaced with a head success. Keep expected merge-triggered checks pending while they have yet to report. A check on another PR, an obsolete synthetic merge SHA, a previous head, or an ineligible Actions event cannot satisfy this PR. Reread PR identity, head, base and test merge after collecting evidence. If any changed, discard the observation and repeat. [GitHub required-check rules](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks) · [Get a pull request](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request)

## Read and decide

Start with `gh pr view <number> --repo <host/owner/repo>` and `gh pr checks <number> --repo <host/owner/repo> --json name,state,bucket,event,workflow,link`. Compare these results with the PR's checks/status-checks box. The CLI head rollup alone cannot establish a current test merge result or prove that expected checks have reported. When SHA or coverage is in doubt, use `gh api` for both `repos/<base-repo>/commits/<sha>/check-runs` and `repos/<base-repo>/commits/<sha>/status`, with pagination. Get active branch rules with `repos/<base-repo>/rules/branches/<branch>` and inspect classic protection separately. Access errors or invisible rules leave that evidence unresolved. Use workflow/run details or the exact PR UI if the commit APIs cannot establish that a result belongs to this PR, uses an eligible event, or came from the required integration. [gh pr checks](https://cli.github.com/manual/gh_pr_checks) · [Check runs](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference) · [Commit statuses](https://docs.github.com/en/rest/commits/statuses#get-the-combined-status-for-a-specific-reference) · [Active branch rules](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch)

For a repeatable SHA-bound readback, use the helper below with the same GitHub host and identities as the delivery. Set `skill_dir` to the absolute path of this skill. Pass `--expect` once per expected name and `--expect-merge` for an expected merge-triggered name. For each poll, supply the current verified delivery SHA and confirm the expected checks still apply.

```sh
python3 -B "$skill_dir/scripts/pull_request.py" checks \
  --repo "$base_repo" --base "$base_branch" --pr "$pr_number" \
  --head-repo "$head_repo" --branch "$task_branch" --head "$delivery_sha" \
  --issue "$issue_url" --expect "$expected_check"
```

The helper reports what the SHA APIs show and exits 0 for `passed` or `no-applicable-checks`, 1 for `failed`, and 2 for `waiting` or unverified evidence. Its classification is provisional when scope, expected sources or report completeness need GitHub UI, rules or workflow evidence. Use `--none '<observed basis>'` only after positively establishing that no checks apply to this PR. Current observations and named expectations take precedence over that option. No per-run input file is needed.

| Decision | Evidence |
| --- | --- |
| `passed` | Every applicable current check is present and has passed. GitHub permits successful, neutral and skipped check conclusions for required checks. Follow any stricter project acceptance criteria as well. |
| `failed` | An applicable current check failed or ended with an unacceptable conclusion. Identify the exact check and link, including cancellation or timeout where relevant. |
| `waiting` | An expected check is absent, queued or running, the PR snapshot is changing, or visibility, applicability or publisher evidence is unresolved. An empty list by itself belongs here. |
| `no-applicable-checks` | Authoritative project configuration and current PR evidence show that no remote checks apply. Save the reason and evidence, then apply the agreed local verification and acceptance. |

## Return evidence

Record the observation time, exact PR URL and number, base repository/branch/SHA, head repository/branch/full SHA, applicable test merge SHA, evaluated SHA, expected checks and their sources, observed check names, states and links, and the decision. Preserve the commands and raw results or accessible evidence links. For absence, include the relevant rules, workflows and project configuration and the agreed local results. For missing or inaccessible evidence, record what is still due.

On failure, return the affected checks to the repair stage. Reuse the same task branch and PR for a verified fix. Preserve earlier evidence under its original SHA and rerun the current checks. For waiting, poll read-only against the same PR. Reopen the current PR and check evidence again before any closure decision. A PR merge remains with the user.
