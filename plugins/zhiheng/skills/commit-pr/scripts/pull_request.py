"""Publish one ticket branch or capture check evidence for one GitHub PR."""

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlencode, urljoin, urlsplit


FULL_PR = "application/vnd.github.full+json"


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


def api(host, endpoint, *, pages=False, data=None, accept=None, allow_unprotected=False):
    args = ["gh", "api", "--hostname", host]
    if accept:
        args += ["--header", f"Accept: {accept}"]
    if pages:
        args += ["--paginate", "--slurp"]
    if data is not None:
        args += ["--method", "POST", "--input", "-"]
    result = run(*args, endpoint, allowed=(0, 1) if allow_unprotected else (0,),
                 input_text=json.dumps(data) if data is not None else None)
    if result.returncode:
        require("gh: Branch not protected (HTTP 404)" in result.stderr.splitlines(),
                "Classic branch protection is unverified")
        return None
    if accept == "text/html":
        return result.stdout
    response = json.loads(result.stdout)
    require(response is not None, "GitHub response is empty")
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


class VisibleReferences(HTMLParser):
    _blocks = set("address article aside blockquote br dd div dl dt figcaption figure footer "
                  "h1 h2 h3 h4 h5 h6 header hr li main ol p pre section table tbody td th "
                  "thead tr ul".split())
    _void = set("area base br col embed hr img input link meta param source track wbr".split())
    _ignored = {"code", "head", "noscript", "pre", "script", "style", "template", "title"}
    _hidden_style = re.compile(
        r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*(?:hidden|collapse))"
        r"\s*(?:!\s*important\s*)?(?:;|$)", re.IGNORECASE
    )

    def __init__(self):
        super().__init__()
        self.text = []
        self.links = set()
        self.anchor = None
        self.ignored = []

    def handle_starttag(self, tag, attrs):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.append(tag)
            return
        attrs = dict(attrs)
        if tag in self._blocks:
            self.text.append("\n")
        if (tag in self._ignored or "hidden" in attrs or
                (attrs.get("aria-hidden") or "").lower() == "true" or
                self._hidden_style.search(attrs.get("style") or "")):
            if tag not in self._void:
                self.ignored.append(tag)
            if tag == "code":
                self.text.append("@")
        elif tag == "a" and attrs.get("href") is not None:
            # The destination is authoritative, even if the label names another issue.
            self.anchor = attrs["href"].strip()
            self.text.append("@")
        elif tag == "img" and self.anchor is not None and (attrs.get("src") or attrs.get("alt")):
            self.links.add(self.anchor)

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag in self._blocks:
            self.text.append("\n")
        if tag == "a":
            self.anchor = None

    def handle_data(self, data):
        if not self.ignored:
            if self.anchor is None:
                self.text.append(data)
            elif data.strip():
                self.links.add(self.anchor)


def related(html, issue, base_repo, host):
    require(isinstance(html, str) and (not html.strip() or html.lstrip().startswith("<")),
            "GitHub rendered PR body is unavailable")
    body = VisibleReferences()
    body.feed(html)
    body.close()

    github_issue = re.fullmatch(
        rf"https://{re.escape(host)}/([\w.-]+/[\w.-]+)/issues/([1-9][0-9]*)",
        issue, re.IGNORECASE,
    )
    shorthand = set()
    if github_issue:
        issue_repo, number = github_issue.groups()
        shorthand.add(f"{issue_repo.lower()}#{number}")
        if issue_repo.lower() == base_repo.lower():
            shorthand.add(f"#{number}")

    def matches(value, *, link=False):
        if not github_issue:
            return value == issue or (issue.startswith(("https://", "http://"))
                                      and value.startswith((issue + "#", issue + "?")))
        try:
            url = urlsplit(urljoin(f"https://{host}/{base_repo}/pull/", value) if link else value)
        except ValueError:
            return False
        return (url.scheme == "https" and url.netloc.lower() == host.lower() and
                url.path.lower() == f"/{issue_repo.lower()}/issues/{number}")

    if any(matches(link, link=True) for link in body.links):
        return True
    # Keep URL fragments attached to their hosts when scanning unlinked text.
    for token in re.findall(r"""[^\s<>"'“”‘’]+""", "".join(body.text)):
        value = token.strip(".,;!?()[]{}:，。；！？（）【】")
        if matches(token) or matches(value) or value.lower() in shorthand:
            return True
    return False


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
        target = pr["base"]["ref"]
        require(pr["state"] == "open" and not pr.get("merged"),
                f"PR #{pr['number']} is closed or merged (target {target}, expected {args.base})")
        require(pr_side(pr, "head") == head_side and pr_side(pr, "base") == base_side,
                "PR repository or branch changed")
        require(related(pr.get("body_html"), args.issue, base_repo, args.host),
                "PR does not link the original ticket")
        return pr

    def observe(expected_number):
        tip = remote_head(url, ref)
        pages = api(args.host, endpoint + "?" + query, pages=True, accept=FULL_PR)
        matches = []
        for page in pages:
            for pr in page:
                if pr["head"]["repo"] and pr_side(pr, "head") == head_side:
                    if (pr["state"] == "open" or pr_side(pr, "base") == base_side
                            or related(pr.get("body_html"), args.issue, base_repo, args.host)):
                        matches.append(pr["number"])
        if expected_number is None:
            require(len(matches) <= 1, "Multiple PRs for the task branch require reconciliation")
            if not matches:
                return tip, None
            expected_number = matches[0]
        pr = check_pr(api(args.host, f"{endpoint}/{expected_number}", accept=FULL_PR))
        require(pr["number"] == expected_number and set(matches) <= {expected_number},
                "Conflicting PR for the task branch")
        return tip, pr

    def write(operation):
        try:
            return operation(), None
        except (Unverified, subprocess.TimeoutExpired, OSError, ValueError) as error:
            return None, str(error) if isinstance(error, Unverified) else type(error).__name__

    github_ref(args.host, base_repo, args.base)
    tip, pr = observe(args.pr)
    if pr is None:
        require(args.title and args.body_file, "Provide a PR title and body file to open a PR")
        body = Path(args.body_file).read_bytes().decode("utf-8")

        def draft_links(markdown):
            html = api(args.host, "markdown", accept="text/html",
                       data={"text": markdown, "mode": "gfm", "context": base_repo})
            return related(html, args.issue, base_repo, args.host)

        if not draft_links(body):
            reference = f"Refs {args.issue}\n"
            separator = "\n" if body.endswith("\n") else "\n\n"
            appended = body + separator + reference
            # Unclosed template markup may hide an appended line.
            if draft_links(appended):
                body = appended
            else:
                body = reference + "\n" + body
                require(draft_links(body), "GitHub did not render the original ticket in the PR draft")

        if tip != head:
            # The PR list may have changed while GitHub rendered the draft.
            current_tip, pr = observe(args.pr)
            require(current_tip == tip, "Remote branch changed while rendering the PR draft. Recheck.")
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
        _, error = write(lambda: git(
            "push", "--porcelain", "--no-follow-tags", "--recurse-submodules=no",
            f"--force-with-lease={ref}:{tip}", "--", url, f"{head}:{ref}",
        ))
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
            def created_number():
                response = api(args.host, endpoint, data=data)
                require(isinstance(response, dict) and type(response.get("number")) is int
                        and response["number"] > 0, "Create pull request response has no valid PR number")
                return response["number"]

            number, error = write(created_number)
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
    pr = api(args.host, f"repos/{args.repo}/pulls/{args.pr}", accept=FULL_PR)
    require(pr["number"] == args.pr and pr_side(pr, "base") == (args.repo.lower(), args.base),
            "Wrong PR number, base repository, or target branch")
    require(pr["state"] == "open" and pr["merged"] is False, "PR is no longer open")
    require(pr_side(pr, "head") == (args.head_repo.lower(), args.branch),
            "PR head repository or branch changed")
    require(pr["head"]["sha"] == args.head, "PR head changed or does not match the delivery")
    require(related(pr.get("body_html"), args.issue, args.repo, args.host), "PR does not link the original ticket")
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
                "id": f"check:{row['id']}", "name": row["name"], "kind": "check",
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
                "id": f"status:{row['id']}", "name": row["context"], "kind": "status",
                "creator": (row.get("creator") or {}).get("login"),
                "state": row["state"], "url": row.get("target_url"),
            })
    require(len(contexts) == total, "Combined status is incomplete")
    return records


def branch_requirements(args, base_sha):
    branch = quote(args.base, safe="")
    repo = f"repos/{args.repo}"
    requirements = []

    def read(endpoint, description, **options):
        try:
            return api(args.host, endpoint, **options)
        except (Unverified, subprocess.TimeoutExpired, OSError, ValueError):
            raise Unverified(f"Could not read {description}; rule visibility is unverified") from None

    def add(rows, app_key, source):
        require(isinstance(rows, list), f"Invalid {source} status check rules")
        for row in rows:
            name, app_id = row["context"], row.get(app_key)
            require(isinstance(name, str) and name and
                    (app_id is None or (type(app_id) is int and (app_id == -1 or app_id > 0))),
                    f"Invalid {source} status check identity")
            requirements.append({"name": name, "app_id": None if app_id == -1 else app_id,
                                 "source": source})

    pages = read(f"{repo}/rules/branches/{branch}?per_page=100", "active branch rules", pages=True)
    for page in pages:
        require(isinstance(page, list), "Invalid active branch rules response")
        for rule in page:
            if rule["type"] == "required_status_checks":
                add(rule["parameters"]["required_status_checks"], "integration_id", "ruleset")
            require(rule["type"] != "workflows", "Required ruleset workflows need PR-specific verification")

    branch_endpoint = f"{repo}/branches/{branch}"
    metadata = read(branch_endpoint, "base branch protection metadata")
    require(metadata["name"] == args.base and metadata["commit"]["sha"] == base_sha
            and isinstance(metadata["protected"], bool), "Base branch protection metadata is unverified")
    if metadata["protected"]:
        classic = read(branch_endpoint + "/protection", "classic branch protection",
                       allow_unprotected=True)
        require(classic is None or isinstance(classic, dict), "Invalid classic branch protection")
        protection = (classic or {}).get("required_status_checks")
        if protection is not None:
            contexts = protection["contexts"]
            require(isinstance(contexts, list), "Invalid classic status check contexts")
            rows = protection.get("checks")
            if rows is None and contexts:
                details = read(branch_endpoint + "/protection/required_status_checks",
                               "classic status check sources")
                rows = details.get("checks") if isinstance(details, dict) else None
            rows = [] if rows is None else rows
            require(isinstance(rows, list) and all("app_id" in row for row in rows)
                    and set(contexts) <= {row["context"] for row in rows},
                    "Could not verify classic status check sources")
            add(rows, "app_id", "classic")
    return requirements


def decide(report, args):
    scope, observed = report["scope"], report["observations"]
    head, merge = scope["head"], scope["merge_sha"]
    effective = merge if observed.get(merge) else head
    report["effective_sha"] = effective
    current = observed[effective]
    names = {row["name"] for row in current}
    expected = report["expected"]
    expected_kinds = {"check": set(expected["check"]), "status": set(expected["status"])}
    kinds = {}
    for rows in observed.values():
        for row in rows:
            kinds.setdefault(row["name"], set()).add(row["kind"])
    for name in expected["effective"]:
        if len(kinds.get(name, ())) > 1:
            for kind in kinds[name]:
                expected_kinds[kind].add(name)

    missing = {
        "effective": sorted(set(expected["effective"]) - names),
        "merge": sorted(set(expected["merge"]) - {row["name"] for row in observed.get(merge, [])}),
        "required": [],
    }
    for kind, wanted in expected_kinds.items():
        missing[kind] = sorted(wanted - {row["name"] for row in current if row["kind"] == kind})

    for requirement in report["requirements"]:
        name, app_id = requirement["name"], requirement["app_id"]
        required_kinds = kinds.get(name, set()) | {
            kind for kind, wanted in expected_kinds.items() if name in wanted
        }
        for kind in sorted(required_kinds or {"any"}):
            if not any(row["name"] == name and kind in ("any", row["kind"]) and
                       (app_id is None or row.get("app_id") == app_id) for row in current):
                item = {"name": name, "kind": kind, "app_id": app_id}
                if item not in missing["required"]:
                    missing["required"].append(item)
    report["missing"] = missing

    failed = {"action_required", "cancelled", "error", "failure", "stale",
              "startup_failure", "timed_out"}
    passed = {"success", "neutral", "skipped"}
    if any(row["state"] in failed for row in current):
        return "failed", "A check on the effective SHA has a non-passing conclusion"
    if any(missing.values()):
        return "waiting", "An expected check kind or publisher is missing or unverified"
    if any(row["state"] not in passed for row in current):
        return "waiting", "A current check is pending"
    if current:
        return "passed", "Current checks and verified branch requirements passed"
    if args.none and args.none.strip():
        return "no-applicable-checks", args.none
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
    rule_error = None
    try:
        report["requirements"] = branch_requirements(args, before["base_sha"])
    except (Unverified, KeyError, TypeError) as error:
        rule_error = str(error) if isinstance(error, Unverified) else "Invalid branch rule evidence"
    require(snapshot(args) == before, "PR changed during check collection. Discard the observation.")
    report["expected"] = {"effective": args.expect, "merge": args.expect_merge,
                          "check": args.expect_check, "status": args.expect_status}
    if rule_error:
        report.update(state="waiting", reason=rule_error)
    else:
        report["state"], report["reason"] = decide(report, args)
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
    read.add_argument("--expect-check", action="append", default=[], help="Expected check run on the effective SHA")
    read.add_argument("--expect-status", action="append", default=[], help="Expected legacy status on the effective SHA")
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
