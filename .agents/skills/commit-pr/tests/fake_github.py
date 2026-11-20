"""Controlled gh api and SSH responses backed by fixture Git refs."""

import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


root = Path(os.environ["DELIVERY_FIXTURE"])
state_path = root / "github.json"


def ref(repo, branch):
    return subprocess.check_output(
        ["git", "--git-dir", root / f"{repo.split('/')[0]}.git", "rev-parse", "--verify",
         "refs/heads/" + branch], text=True
    ).strip()


def github():
    state = json.loads(state_path.read_text())
    url = urlsplit(sys.argv[-1])
    parts = unquote(url.path).split("/")
    target = "/".join(parts[1:3])
    endpoint = "/".join(parts[3:])
    assert sys.argv[1:4] == ["api", "--hostname", "github.com"]
    assert target in {"Code/app", "Fork/app"}
    if endpoint.startswith("git/ref/heads/"):
        branch = endpoint.removeprefix("git/ref/heads/")
        return {"ref": f"refs/heads/{branch}", "object": {"type": "commit", "sha": ref(target, branch)}}
    if endpoint.startswith("rules/branches/"):
        assert target == "Code/app" and endpoint == "rules/branches/main"
        if state.get("rules_inaccessible"):
            sys.exit(1)
        rules = state.get("rules", [])
        return [rules] if "--slurp" in sys.argv else rules
    if endpoint.startswith("branches/"):
        assert target == "Code/app"
        classic = state.get("classic", {})
        if endpoint.endswith("/protection/required_status_checks"):
            return state.get("classic_status_details", classic["required_status_checks"])
        if endpoint.endswith("/protection"):
            if classic == "inaccessible":
                print('{"message":"Not Found"}')
                print("gh: Not Found (HTTP 404)", file=sys.stderr)
                sys.exit(1)
            if not classic:
                print('{"message":"Branch not protected"}')
                print("gh: Branch not protected (HTTP 404)", file=sys.stderr)
                sys.exit(1)
            return classic
        assert endpoint == "branches/main"
        return {"name": "main", "commit": {"sha": ref(target, "main")},
                "protected": bool(classic or state.get("rules"))}
    if endpoint == "pulls" and "POST" in sys.argv:
        payload = json.load(sys.stdin)
        state["creates"] += 1
        prior = state["pr"]
        assert not prior or prior["state"] == "closed"
        if prior:
            state["retired_pr"] = prior
        assert payload["head"] == "Fork:task/20"
        assert payload["head_repo"] == "app"
        assert payload["base"] == "main"
        state["pr"] = {"number": 42 if prior else 41, "title": payload["title"],
                       "body": payload["body"], "base": payload["base"], "state": "open"}
        state_path.write_text(json.dumps(state))
        if state.get("lost_create"):
            sys.exit(22)
        return pull(state["pr"], state)
    pr = state["pr"]
    candidates = [item for item in (state.get("retired_pr"), pr) if item]
    if endpoint == "pulls":
        assert parse_qs(url.query)["head"] == ["Fork:task/20"]
        assert parse_qs(url.query)["state"] == ["all"]
        return [[pull(item, state) for item in candidates]]
    if endpoint.startswith("pulls/"):
        number = int(endpoint.removeprefix("pulls/"))
        return pull(next(item for item in candidates if item["number"] == number), state)
    revision, _, suffix = endpoint.removeprefix("commits/").partition("/")
    if not suffix:
        current = pull(pr, state)
        parents = [current["base"]["sha"], current["head"]["sha"]]
        if state.get("stale_merge"):
            parents[1] = "deadbeef" * 5
        return {"sha": revision, "parents": [{"sha": parent} for parent in parents]}
    spec = state["checks"].get(revision, {})
    if suffix == "check-runs":
        if state.get("move_base_during_checks"):
            # Move once after the first snapshot. The second read must discard it.
            subprocess.check_call(["git", "--git-dir", root / "Code.git", "update-ref",
                                   "refs/heads/main", state.pop("move_base_during_checks")])
            state_path.write_text(json.dumps(state))
        runs = spec.get("check", [])
        if isinstance(runs, dict):
            runs = [(name, outcome, 5) for name, outcome in runs.items()]
        rows = [{"id": index, "name": name, "head_sha": revision,
                 "status": "queued" if outcome == "pending" else "completed",
                 "conclusion": None if outcome == "pending" else outcome,
                 "app": {"id": app_id}, "details_url": f"https://example.org/checks/{index}"}
                for index, (name, outcome, app_id) in enumerate(runs, 1)]
        return [{"total_count": len(rows), "check_runs": rows}]
    assert suffix == "status"
    statuses = [{"id": index, "context": name, "state": outcome, "creator": {"login": "ci[bot]"}}
                for index, (name, outcome) in enumerate(spec.get("status", {}).items(), 1)]
    return [{"sha": revision, "total_count": len(statuses), "statuses": statuses}]


def pull(pr, state):
    base, head = ref("Code/app", pr["base"]), ref("Fork/app", "task/20")
    merge = hashlib.sha1((base + head).encode()).hexdigest()
    number = pr["number"]
    return {
        "number": number, "html_url": f"https://github.com/Code/app/pull/{number}",
        "title": pr["title"], "body": pr["body"],
        "base": {"sha": base, "ref": pr["base"], "repo": {"full_name": "Code/app"}},
        "head": {"sha": head, "ref": "task/20", "repo": {"full_name": "Fork/app"}},
        "state": pr["state"], "merged": False, "mergeable": state.get("mergeable", True),
        "merge_commit_sha": merge,
    }


def ssh():
    command, path = shlex.split(sys.argv[-1])
    assert command in {"git-upload-pack", "git-receive-pack"}
    assert path in {"Code/app.git", "Fork/app.git"}
    state = json.loads(state_path.read_text())
    repo = root / f"{path.split('/')[0]}.git"
    if command == "git-receive-pack" and state.get("race_tip"):
        subprocess.check_call(["git", "--git-dir", repo, "update-ref",
                               "refs/heads/task/20", state["race_tip"]])
    result = subprocess.call([command, repo])
    if command == "git-receive-pack" and state.get("lost_push"):
        return 23
    return result


if Path(sys.argv[0]).name == "gh":
    print(json.dumps(github()))
else:
    sys.exit(ssh())
