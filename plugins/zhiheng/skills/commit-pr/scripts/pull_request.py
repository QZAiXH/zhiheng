"""Publish one ticket branch or capture check evidence for one GitHub PR."""

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit


class Unverified(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Unverified(message)


def run(*args, allowed=(0,), input_text=None):
    result = subprocess.run(
        args, input=input_text, capture_output=True, text=True, timeout=90, check=False
    )
    # Some Git diagnostics include a credential-bearing remote URL.
    require(result.returncode in allowed, f"{args[0]} {args[1]} exited {result.returncode}")
    return result


def git(*args):
    return run("git", *args).stdout.strip()


def api(host, endpoint, *, pages=False, data=None):
    args = ["gh", "api", "--hostname", host]
    if pages:
        args += ["--paginate", "--slurp"]
    if data is not None:
        args += ["--method", "POST", "--input", "-"]
    response = json.loads(
        run(*args, endpoint, input_text=json.dumps(data) if data is not None else None).stdout
    )
    if pages:
        require(isinstance(response, list) and response, "Paginated GitHub response is incomplete")
    return response


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{40}", value),
            "Expected a full GitHub commit SHA")
    return value


def repo_name(value):
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value),
            "Expected an OWNER/REPO GitHub repository")
    return value


def git_remote(host, repo, remote):
    urls = git("remote", "get-url", "--push", "--all", "--", remote).splitlines()
    require(len(urls) == 1, "Choose a remote with one push URL")
    url = urls[0]
    parsed = urlsplit(url)
    if parsed.scheme in {"https", "ssh"}:
        remote_host, path = parsed.hostname, parsed.path.lstrip("/")
    else:
        match = re.fullmatch(r"(?:[^@/]+@)?([^:/]+):(.+)", url)
        require(match, "Use an explicit GitHub HTTPS or SSH remote")
        remote_host, path = match.groups()
    require(remote_host == host and path.removesuffix(".git").lower() == repo.lower(),
            "Push URL does not identify the specified head repository")
    return url


def remote_head(url, ref):
    result = run("git", "ls-remote", "--refs", "--exit-code", "--", url, ref, allowed=(0, 2))
    if result.returncode == 2:
        return ""
    oid, observed = result.stdout.strip().split("\t")
    require(observed == ref, "Unexpected Git ref in remote lookup")
    return sha(oid)


def pr_side(pr, side):
    ref = pr[side]
    return ref["repo"]["full_name"].lower(), ref["ref"]


def related(body, issue, base_repo, host):
    body = body or ""
    url_pattern = rf"(?<![\w/]){re.escape(issue)}(?![\w/-]|\.\w)"
    match = re.fullmatch(
        rf"https://{re.escape(host)}/([\w.-]+/[\w.-]+)/issues/([1-9][0-9]*)",
        issue, re.IGNORECASE,
    )
    if re.search(url_pattern, body, re.IGNORECASE if match else 0):
        return True
    if not match:
        return False
    issue_repo, number = match.groups()
    shorthand = re.escape(issue_repo) + "#" + number
    if issue_repo.lower() == base_repo.lower():
        shorthand = rf"(?:{shorthand}|#{number})"
    return bool(re.search(rf"(?<![\w/.-]){shorthand}(?![\w/])", body, re.IGNORECASE))


def check_issue(args):
    require(":" in args.issue and not any(c.isspace() for c in args.issue),
            "Supply a fully qualified, single-line origin ticket locator")


def github_ref(host, repo, branch):
    ref = "refs/heads/" + branch
    data = api(host, f"repos/{repo}/git/ref/heads/{quote(branch, safe='')}")
    require(data["ref"] == ref and data["object"]["type"] == "commit", "Unexpected GitHub ref")
    return sha(data["object"]["sha"])


def publish(args):
    head, head_repo = sha(args.head), repo_name(args.head_repo)
    base_repo = repo_name(args.repo)
    check_issue(args)
    require(git("rev-parse", "--show-toplevel") == str(Path.cwd()),
            "Run publish from the root of the task worktree")
    require(Path(git("rev-parse", "--git-dir")).resolve() !=
            Path(git("rev-parse", "--git-common-dir")).resolve(), "Use a linked task worktree")
    branch = args.branch
    ref = "refs/heads/" + branch
    git("check-ref-format", ref)
    require((base_repo.lower(), args.base) != (head_repo.lower(), branch),
            "The push destination must differ from the PR base")

    def local_head():
        require(git("symbolic-ref", "HEAD") == ref and git("rev-parse", "HEAD") == head,
                "Task branch or local HEAD changed")

    local_head()
    url = git_remote(args.host, head_repo, args.remote)
    endpoint = f"repos/{base_repo}/pulls"
    head_label = head_repo.split("/")[0] + ":" + branch
    query = urlencode({"state": "all", "head": head_label, "per_page": 100})
    head_side, base_side = (head_repo.lower(), branch), (base_repo.lower(), args.base)

    def check_pr(pr):
        require(pr["state"] == "open" and not pr.get("merged"), "Recorded PR is closed or merged")
        require(pr_side(pr, "head") == head_side and pr_side(pr, "base") == base_side,
                "PR repository or branch changed")
        require(related(pr["body"], args.issue, base_repo, args.host),
                "PR does not link the original ticket")
        return pr

    def observe(expected_number):
        tip = remote_head(url, ref)
        pages = api(args.host, endpoint + "?" + query, pages=True)
        matches = []
        for page in pages:
            for pr in page:
                if pr["head"]["repo"] and pr_side(pr, "head") == head_side:
                    if pr["state"] == "open" or pr_side(pr, "base") == base_side:
                        matches.append(pr["number"])
        if expected_number is not None:
            pr = check_pr(api(args.host, f"{endpoint}/{expected_number}"))
            require(pr["number"] == expected_number and set(matches) <= {expected_number},
                    "Conflicting PR for the task branch")
            return tip, pr
        require(len(matches) <= 1, "Multiple PRs for the task branch require reconciliation")
        return tip, check_pr(api(args.host, f"{endpoint}/{matches[0]}")) if matches else None

    def write(operation):
        try:
            operation()
            return None
        except (Unverified, subprocess.TimeoutExpired, OSError, ValueError) as error:
            return str(error) if isinstance(error, Unverified) else type(error).__name__

    github_ref(args.host, base_repo, args.base)
    tip, pr = observe(args.pr)
    if pr is None:
        require(args.title and args.body_file, "Provide a PR title and body file to open a PR")
        body = Path(args.body_file).read_text(encoding="utf-8")
        if not related(body, args.issue, base_repo, args.host):
            body = f"{body.rstrip()}\n\nRefs {args.issue}\n"
    number = pr["number"] if pr else None
    recovery = []
    if tip != head:
        require(not pr or (tip and pr["head"]["sha"] == tip),
                "PR head differs from the remote branch. Recheck before updating.")
        if tip:
            require(pr or (args.previous_head and sha(args.previous_head) == tip),
                    "Existing branch tip is not a verified prior delivery")
            git("merge-base", "--is-ancestor", tip, head)
        local_head()
        require(remote_head(url, ref) == tip, "Remote branch changed before push. Recheck.")
        error = write(lambda: git("push", "--porcelain", "--no-follow-tags", "--recurse-submodules=no",
                                  "--", url, f"{head}:{ref}"))
        tip, pr = observe(number)
        require(tip == head, f"Remote head was not confirmed after push ({error or 'unverified'}).")
        if error:
            recovery.append(error)
    if pr is None:
        # Read both identities again before the independent GitHub write.
        local_head()
        tip, pr = observe(number)
        require(tip == head, "Remote head changed before PR creation")
        if pr is None:
            data = {"title": args.title, "body": body, "base": args.base, "head": head_label}
            if head_repo.lower() != base_repo.lower():
                data["head_repo"] = head_repo.split("/")[1]
            error = write(lambda: api(args.host, endpoint, data=data))
            tip, pr = observe(number)
            require(tip == head and pr, f"PR creation was not confirmed ({error or 'unverified'}).")
            if error:
                recovery.append(error)
    local_head()
    require(pr["head"]["sha"] == head and remote_head(url, ref) == head,
            "PR and remote branch do not both report the intended head. Recheck.")
    return {
        "pr": pr["html_url"], "number": pr["number"], "head": head, "base": args.base,
        "head_repo": head_repo, "head_branch": branch, "issue": args.issue,
        "base_repo": base_repo, "recovered_writes": recovery,
    }


def snapshot(args):
    pr = api(args.host, f"repos/{args.repo}/pulls/{args.pr}")
    require(pr["number"] == args.pr and pr_side(pr, "base") == (args.repo.lower(), args.base),
            "Wrong PR number, base repository, or target branch")
    require(pr["state"] == "open" and pr["merged"] is False, "PR is no longer open")
    require(pr_side(pr, "head") == (args.head_repo.lower(), args.branch),
            "PR head repository or branch changed")
    require(pr["head"]["sha"] == args.head, "PR head changed or does not match the delivery")
    require(related(pr["body"], args.issue, args.repo, args.host), "PR does not link the original ticket")
    require(github_ref(args.host, args.head_repo, args.branch) == args.head, "PR head is changing")
    base = sha(pr["base"]["sha"])
    require(github_ref(args.host, args.repo, args.base) == base, "PR base is changing")
    mergeable = pr["mergeable"]
    require(isinstance(mergeable, bool), "GitHub is computing the current test merge")
    merge = sha(pr["merge_commit_sha"]) if mergeable else None
    return {"base_sha": base, "merge_sha": merge, "pr": pr["html_url"]}


def observed_checks(host, repo, revision):
    endpoint = f"repos/{repo}/commits/{revision}"
    records = []
    total = 0
    for page in api(host, endpoint + "/check-runs?filter=latest&per_page=100", pages=True):
        total = max(total, page["total_count"])
        for row in page["check_runs"]:
            require(row["head_sha"] == revision, "Check-run head SHA mismatch")
            records.append({
                "id": f"check:{row['id']}", "name": row["name"],
                "app_id": (row.get("app") or {}).get("id"),
                "state": row["conclusion"] if row["status"] == "completed" else "pending",
                "url": row.get("details_url"), "suite_id": (row.get("check_suite") or {}).get("id"),
            })
    require(len(records) == total, "Check-run list is incomplete")
    contexts = set()
    total = 0
    for page in api(host, endpoint + "/status?per_page=100", pages=True):
        require(page["sha"] == revision, "Combined status SHA mismatch")
        total = max(total, page["total_count"])
        for row in page["statuses"]:
            require(row["context"] not in contexts, "Combined status changed during pagination")
            contexts.add(row["context"])
            records.append({
                "id": f"status:{row['id']}", "name": row["context"],
                "creator": (row.get("creator") or {}).get("login"),
                "state": row["state"], "url": row.get("target_url"),
            })
    require(len(contexts) == total, "Combined status is incomplete")
    return records


def decide(report, expect, expect_merge, none):
    scope, observed = report["scope"], report["observations"]
    head, merge = scope["head"], scope["merge_sha"]
    effective = merge if observed.get(merge) else head
    report["effective_sha"] = effective
    current = observed[effective]
    missing = sorted(set(expect) - {row["name"] for row in current})
    missing_merge = sorted(set(expect_merge) - {row["name"] for row in observed.get(merge, [])})
    report["missing"] = {"effective": missing, "merge": missing_merge}
    failed = {"action_required", "cancelled", "error", "failure", "stale",
              "startup_failure", "timed_out"}
    passed = {"success", "neutral", "skipped"}
    if any(row["state"] in failed for row in current):
        return "failed", "A check on the effective SHA has a non-passing conclusion"
    if missing or missing_merge or any(row["state"] not in passed for row in current):
        return "waiting", "An expected check is missing or a current check is pending"
    if current:
        return "passed", "All observed effective-SHA results and named expectations passed"
    if none and none.strip() and not expect and not expect_merge:
        return "no-applicable-checks", none
    return "waiting", "No current check has reported and absence is unverified"


def checks(args):
    check_issue(args)
    scope = {
        "head": sha(args.head), "number": args.pr, "base_branch": args.base,
        "repository": repo_name(args.repo), "host": args.host,
        "head_repository": repo_name(args.head_repo), "head_branch": args.branch, "issue": args.issue,
    }
    before = snapshot(args)
    scope.update(before)
    report = {"scope": scope, "observed_at": datetime.now(timezone.utc).isoformat()}
    merge = before["merge_sha"]
    if merge:
        commit = api(args.host, f"repos/{args.repo}/commits/{merge}")
        require(commit["sha"] == merge and
                [parent["sha"] for parent in commit["parents"]] == [before["base_sha"], args.head],
                "Test merge commit does not bind the current base and head")
    revisions = [args.head, merge] if merge else [args.head]
    report["observations"] = {rev: observed_checks(args.host, args.repo, rev) for rev in revisions}
    require(snapshot(args) == before, "PR changed during check collection. Discard the observation.")
    report["expected"] = {"effective": args.expect, "merge": args.expect_merge}
    report["state"], report["reason"] = decide(report, args.expect, args.expect_merge, args.none)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    delivery = modes.add_parser("publish")
    read = modes.add_parser("checks")
    for sub in (delivery, read):
        sub.add_argument("--host", default="github.com")
        sub.add_argument("--repo", required=True, help="Base GitHub OWNER/REPO")
        sub.add_argument("--base", required=True, help="Base branch")
        sub.add_argument("--head-repo", required=True, help="Head GitHub OWNER/REPO")
        sub.add_argument("--branch", required=True, help="Task branch")
        sub.add_argument("--head", required=True, help="Full delivery SHA")
        sub.add_argument("--pr", type=int, required=sub is read, help="Recorded PR number")
        sub.add_argument("--issue", required=True, help="Original ticket URL or namespaced locator")
    delivery.add_argument("--remote", required=True)
    delivery.add_argument("--previous-head", help="Verified prior task SHA when a branch has no PR yet")
    delivery.add_argument("--title")
    delivery.add_argument("--body-file")
    read.add_argument("--expect", action="append", default=[], help="Expected check name; repeat as needed")
    read.add_argument("--expect-merge", action="append", default=[], help="Check expected on the test merge SHA")
    read.add_argument("--none", help="Observed evidence that no remote checks apply")
    args = parser.parse_args()
    try:
        require(re.fullmatch(r"[A-Za-z0-9.-]+", args.host), "Use an explicit GitHub host")
        require(args.pr is None or args.pr > 0, "Use a positive PR number")
        report = publish(args) if args.mode == "publish" else checks(args)
    except (Unverified, subprocess.TimeoutExpired, OSError, ValueError, KeyError, TypeError) as error:
        reason = str(error) if isinstance(error, Unverified) else type(error).__name__
        print(json.dumps({"state": "waiting", "reason": reason, "host": args.host,
                          "repository": args.repo, "head": args.head, "number": args.pr}))
        return 2
    print(json.dumps(report, indent=2))
    return {"failed": 1, "waiting": 2}.get(report.get("state"), 0)


if __name__ == "__main__":
    raise SystemExit(main())
