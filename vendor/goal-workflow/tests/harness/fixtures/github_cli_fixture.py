"""TEST ONLY: simulated gh/network transports and narrow simulation-scope injection.

No credentials or network are used. Every Git object/ref/hook operation delegates
an absolute native Git executable. This is not installable production code and
never produces a live/ready capability receipt. See test_github_cli_e2e.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, unquote

URL = "https://github.com/fixture/arithmetic.git"
REPOSITORY = "fixture/arithmetic"


def context():
    base = Path(os.environ["HARNESS_GITHUB_FIXTURE_ROOT"]).resolve()
    assert base.is_relative_to(Path(tempfile.gettempdir()).resolve())
    assert base.name.startswith("harness-cli-e2e-")
    assert (base / "SIMULATED_GITHUB_ONLY").read_text() == "no-network; no-model; simulation-only\n"
    bare = base / "remote.git"
    assert bare.is_dir() and not bare.is_symlink()
    native = Path(os.environ["HARNESS_GITHUB_FIXTURE_NATIVE_GIT"])
    assert native.is_absolute() and native.is_file()
    return base, bare, str(native)


def audit(kind, **data):
    base, _, _ = context()
    with (base / "transport-audit.jsonl").open("a") as stream:
        stream.write(json.dumps(dict(kind=kind, simulation=True, **data), sort_keys=True) + "\n")


def native_git(*args, bare=False, **kwargs):
    _, remote, executable = context()
    prefix = [executable, "--git-dir=" + str(remote)] if bare else [executable]
    return subprocess.run(prefix + list(args), check=True, text=True, capture_output=True, **kwargs).stdout.strip()


def git_shim():
    base, bare, native = context()
    args = sys.argv[1:]
    os.environ["GIT_ALLOW_PROTOCOL"] = "file"  # OS child defense: network transports cannot run
    commands = {"push", "fetch", "ls-remote", "clone", "pull", "submodule"}
    # Account for Git's global options. No arbitrary network transport is allowed.
    index = 0
    while index < len(args):
        if args[index] in ("-c", "-C", "--git-dir", "--work-tree"):
            index += 2
        elif args[index].startswith("-"):
            index += 1
        else:
            break
    command = args[index] if index < len(args) else ""
    if command in commands:
        if command == "ls-remote" and "--get-url" in args:
            pass  # Native URL expansion remains real and is inspected by product.
        else:
            if command not in ("push", "fetch", "ls-remote"):
                raise SystemExit("fixture refuses unimplemented network command")
            # Product fetch uses named remote; source transport uses exact URL.
            if "origin" in args[index + 1:]:
                assert native_git(*args[:index], "remote", "get-url", "origin") == URL
                args = [str(bare) if arg == "origin" else arg for arg in args]
                if command == "fetch":
                    # Explicit bare destination, never multivalued url overrides.
                    # Preserve the remote-tracking ref plus FETCH_HEAD semantics.
                    args = ["main:refs/remotes/origin/main" if arg == "main" else arg for arg in args]
            elif URL in args[index + 1:]:
                args = [str(bare) if arg == URL else arg for arg in args]
            else:
                raise SystemExit("fixture refuses every unapproved transport destination")
            if str(bare) not in args or any("://" in arg for arg in args):
                raise SystemExit("fixture refuses transport argv without its unique absolute bare destination")
            audit("git-transport", command=command, original_argv=sys.argv[1:], mapped_remote=str(bare),
                  actual_argv=args, allowed_protocols="file")
    os.execv(native, [native, *args])


def load_state():
    base, _, _ = context()
    return json.loads((base / "platform.json").read_text())


def save_state(state):
    base, _, _ = context()
    target = base / "platform.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True))
    temporary.replace(target)


def pr_record(state, number):
    return state["prs"][str(number)]


def run_ci(pr):
    """Simulated scheduling/status protocol, actual committed business tests."""
    base, bare, _ = context()
    sha = pr["merge_commit_sha"]
    folder = base / ("simulated-ci-" + str(pr["number"]))
    native_git("worktree", "add", "--detach", str(folder), sha, bare=True)
    result = subprocess.run([sys.executable, "tests/run_business.py"], cwd=folder,
                            capture_output=True, text=True, env=os.environ.copy())
    (base / ("simulated-ci-" + str(pr["number"]) + ".log")).write_text(result.stdout + result.stderr)
    audit("native-business-test", sha=sha, exit_code=result.returncode)
    return result.returncode == 0


def create_pr(state, args):
    def option(flag):
        return args[args.index(flag) + 1]
    assert option("--repo") == REPOSITORY
    head_label, target = option("--head"), option("--base")
    owner, branch = head_label.split(":", 1)
    assert owner == "fixture" and target == "main"
    head = native_git("rev-parse", "refs/heads/" + branch, bare=True)
    base = native_git("rev-parse", "refs/heads/" + target, bare=True)
    # Native merge-tree proves the actual combination; no caller evidence file is read.
    tree = native_git("merge-tree", "--write-tree", base, head, bare=True).splitlines()[0]
    candidate = native_git("commit-tree", tree, "-p", base, "-p", head, "-m", "SIMULATED GitHub test-merge", bare=True)
    number = state["next_pr"]
    state["next_pr"] += 1
    pr = {"number": number, "head": {"sha": head, "ref": branch, "label": head_label, "repo": {"full_name": REPOSITORY}},
          "base": {"sha": base, "ref": target}, "state": "open", "merged": False,
          "draft": "--draft" in args, "merge_commit_sha": candidate,
          "html_url": "https://github.com/" + REPOSITORY + "/pull/" + str(number)}
    pr["ci_success"] = run_ci(pr)
    pr["pending_queries"] = 3
    state["prs"][str(number)] = pr
    return pr


def merge_pr(state, number, expected=None, manual=False):
    pr = pr_record(state, number)
    assert not pr["merged"]
    assert not pr["draft"], "SIMULATED GitHub refuses draft merge; mark ready explicitly"
    assert expected in (None, pr["head"]["sha"])
    assert pr["ci_success"] and pr["pending_queries"] == 0
    assert state["rules"] == "strict" or manual
    target = native_git("rev-parse", "refs/heads/main", bare=True)
    assert target == pr["base"]["sha"], "stale base"
    tree = native_git("rev-parse", pr["merge_commit_sha"] + "^{tree}", bare=True)
    delivered = native_git("commit-tree", tree, "-p", target, "-m", "SIMULATED GitHub squash delivery", bare=True)
    native_git("update-ref", "refs/heads/main", delivered, target, bare=True)
    pr.update(merged=True, state="closed", merge_commit_sha=delivered)
    audit("manual-merge" if manual else "merge", number=number, delivered_sha=delivered)
    return pr


def gh_shim():
    args = sys.argv[1:]
    audit("gh", argv=args)
    if args == ["--version"]:
        print("gh version SIMULATED-E2E-TRANSPORT (no network)")
        return
    if args[:2] == ["auth", "status"]:
        print("SIMULATED authenticated fixture identity; no credential access")
        return
    state = load_state()
    if args[:2] == ["pr", "create"]:
        pr = create_pr(state, args)
        save_state(state)
        print(pr["html_url"])
        return
    if args[:2] == ["pr", "ready"]:
        number = args[2]
        pr_record(state, number)["draft"] = False
        save_state(state)
        print("SIMULATED PR marked ready")
        return
    if args[:2] == ["pr", "merge"]:
        assert "--auto" in args and "--squash" in args and "--match-head-commit" in args
        merge_pr(state, args[2], args[args.index("--match-head-commit") + 1])
        save_state(state)
        print("SIMULATED auto-merge fulfilled")
        return
    assert args and args[0] == "api", "unimplemented simulated gh command"
    endpoint = next(arg for arg in args if arg == "user" or arg.startswith("repos/"))
    method = args[args.index("--method") + 1] if "--method" in args else "GET"
    path, _, query = endpoint.partition("?")
    query = parse_qs(query)
    prefix = "repos/" + REPOSITORY
    assert endpoint == "user" or path == prefix or path.startswith(prefix + "/")
    relative = unquote(path.removeprefix(prefix + "/"))
    if endpoint == "user":
        result = {"login": "SIMULATED-fixture", "id": 1}
    elif path == prefix:
        result = {"full_name": REPOSITORY, "private": state["private"], "permissions": {"pull": True, "push": True}, "archived": False, "disabled": False}
    elif relative == "branches/main":
        result = {"name": "main", "commit": {"sha": native_git("rev-parse", "refs/heads/main", bare=True)}}
    elif relative == "git/ref/heads/main":
        result = {"object": {"sha": native_git("rev-parse", "refs/heads/main", bare=True)}}
    elif relative.startswith("git/commits/"):
        sha = relative.split("/")[-1]
        result = {"sha": sha, "tree": {"sha": native_git("rev-parse", sha + "^{tree}", bare=True)}}
    elif relative == "issues":
        result = [row for row in state["issues"].values() if row["state"] == "open"]
    elif relative.startswith("issues/"):
        bits = relative.split("/")
        issue = state["issues"][bits[1]]
        if len(bits) == 2:
            if method == "PATCH":
                assert "state=closed" in args and "state_reason=completed" in args
                issue.update(state="closed", state_reason="completed")
            result = issue
        elif bits[2:] == ["dependencies", "blocked_by"]:
            result = [state["issues"][str(dep)] for dep in issue["dependencies"]]
        elif bits[2:] == ["comments"]:
            comments = state["comments"].setdefault(bits[1], [])
            if method == "POST":
                body = next(arg[5:] for arg in args if arg.startswith("body="))
                comments.append({"id": len(comments) + 1, "body": body,
                                 "html_url": "https://github.com/" + REPOSITORY + "/issues/" + bits[1] + "#issuecomment-1"})
                result = comments[-1]
            else:
                result = comments
        else:
            raise AssertionError(relative)
    elif relative == "pulls":
        result = list(state["prs"].values())
        if "head" in query:
            result = [pr for pr in result if pr["head"]["label"] == query["head"][0] and pr["base"]["ref"] == query["base"][0]]
        elif query.get("state") == ["open"]:
            result = [pr for pr in result if pr["state"] == "open"]
    elif relative.startswith("pulls/"):
        result = pr_record(state, relative.split("/")[-1])
    elif relative.startswith("commits/") and relative.endswith("/check-runs"):
        sha = relative.split("/")[1]
        pr = next((pr for pr in state["prs"].values() if sha == pr["merge_commit_sha"] or sha == pr.get("checked_sha")), None)
        rows = []
        if pr is not None:
            pending = pr["pending_queries"] > 0
            pr["pending_queries"] = max(0, pr["pending_queries"] - 1)
            pr["checked_sha"] = sha
            rows.append({"id": pr["number"], "head_sha": sha, "name": "business", "status": "in_progress" if pending else "completed",
                         "conclusion": None if pending else "success" if pr["ci_success"] else "failure",
                         "html_url": pr["html_url"] + "/checks"})
        result = {"check_runs": rows}
    elif relative.startswith("commits/") and relative.endswith("/statuses"):
        result = []
    elif relative == "actions/workflows":
        result = {"workflows": []}
    elif relative == "rules/branches/main":
        if state["rules"] == "inaccessible":
            print("SIMULATED private plan HTTP 403 rules unavailable", file=sys.stderr)
            raise SystemExit(1)
        result = [{"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": True,
                    "required_status_checks": [{"context": "business"}]}}] if state["rules"] == "strict" else []
    elif relative.startswith("compare/"):
        old, new = relative.removeprefix("compare/").split("...")
        native_git("merge-base", "--is-ancestor", old, new, bare=True)
        result = {"status": "identical" if old == new else "ahead", "base_commit": {"sha": old}}
    else:
        raise AssertionError("unimplemented simulated endpoint " + endpoint)
    save_state(state)
    if "--slurp" in args:
        result = [result]
    print(json.dumps(result))


def fixture_cli():
    """Inject only remote fixture scope and explicit simulation delivery opt-in."""
    from harness import capabilities, cli
    from harness.state import Blocked
    original_require = capabilities.require_capabilities

    def isolated_scope(controller):
        base, bare, _ = context()
        if controller.root != base / "repo" or not controller.root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise Blocked("test simulation scope requires its exact temporary repository")
        if controller.git("remote").splitlines() != ["origin"]:
            raise Blocked("test simulation scope requires one isolated mapped remote")
        for args in (("remote", "get-url", "--all", "origin"), ("remote", "get-url", "--push", "--all", "origin")):
            if controller.git(*args).splitlines() != [URL]:
                raise Blocked("test simulation remote must match exact fixture URL")
        if (controller.root / ".harness-simulation").read_text().strip() != "isolated-harness-fixture":
            raise Blocked("fixture marker missing")
        if controller.git("show", "HEAD:.harness-simulation").strip() != "isolated-harness-fixture":
            raise Blocked("fixture marker must be committed")
        for tool in ("git", "gh"):
            executable = base / "bin" / tool
            if not executable.is_file() or executable.is_symlink() or executable.read_bytes() != Path(__file__).read_bytes():
                raise Blocked("test transport is not the concrete fixture-only executable")
        if not bare.is_relative_to(base) or not (bare / "HEAD").is_file():
            raise Blocked("test bare remote not isolated")
        audit("simulation-scope", repository=str(controller.root))

    def simulation_delivery(controller, config, **options):
        # No receipt is rewritten. The real checker verifies its integrity,
        # exact runtime/config/host/native tool bindings and raw evidence hashes.
        if options.get("delivery"):
            options["simulate_delivery"] = True
            audit("simulation-delivery-opt-in", mode=config["mode"])
        return original_require(controller, config, **options)

    capabilities.simulation_scope = isolated_scope
    cli.require_capabilities = simulation_delivery
    audit("cli-injection", argv=sys.argv[1:], boundaries=["isolated_remote_simulation_scope", "explicit_simulate_delivery_opt_in"])
    raise SystemExit(cli.main(sys.argv[1:]))


if __name__ == "__main__":
    mode = Path(sys.argv[0]).name
    if mode == "git":
        git_shim()
    elif mode == "gh":
        gh_shim()
    elif mode == "fixture_cli.py":
        fixture_cli()
    else:
        raise SystemExit("test-only helper must be copied under a supported fixture executable name")
