"""Run an isolated TDD task that needs assertion and boundary-double guidance."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = os.environ.get("ZH_EVAL_RUN_ID", "")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", RUN_ID):
    raise SystemExit("Set ZH_EVAL_RUN_ID to a new simple run name")
OUTPUT = ROOT / "docs/evidence/i03-tdd-followup/runs" / RUN_ID
OUTPUT.mkdir(parents=True, exist_ok=False)
shutil.copy2(Path(__file__), OUTPUT / "runner.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory(prefix="zh-i03-tdd-") as temporary:
    base = Path(temporary).resolve()
    home, codex_home, project = (base / name for name in ("home", "codex-home", "project"))
    home.mkdir()
    codex_home.mkdir()
    project.mkdir()
    (codex_home / "auth.json").symlink_to(Path.home() / ".codex/auth.json")
    shutil.copytree(ROOT / "skills", project / ".agents/skills")
    source_hashes = {p.relative_to(project).as_posix(): sha(p)
                     for p in (project / ".agents/skills").rglob("*") if p.is_file()}
    inputs = {
        "SPEC.md": (
            "# Accepted behavior\n"
            "`receipt.save_value(store, key, value)` calls the external persistence boundary "
            "`store.write(key, value)` exactly once. On success it returns `value`. "
            "If `store.write` raises `OSError`, the same error propagates and the function "
            "must not return a success value. Use standard library unittest. "
            "The project has no real storage configuration; a small recording/failing "
            "test double can observe the boundary. Do not change storage APIs or add dependencies.\n"
        ),
        "receipt.py": (
            "def save_value(store, key, value):\n"
            "    try:\n"
            "        store.write(key, value)\n"
            "    except OSError:\n"
            "        pass\n"
            "    return value\n"
        ),
    }
    for name, text in inputs.items():
        (project / name).write_text(text)
    prompt = (
        "$zh-tdd Implement the accepted SPEC.md behavior in receipt.py using a real "
        "red-to-green cycle. Design assertions from the independent expected behavior. "
        "The external store.write boundary needs a recording and failure-capable test "
        "double. Run the relevant tests before and after the minimal fix and return "
        "the observed evidence and any required review handoff. Work only in this project.\n"
    )
    (OUTPUT / "request.txt").write_text(prompt)
    (OUTPUT / "inputs.json").write_text(json.dumps({
        "files": inputs, "installed_skill_files_sha256": source_hashes,
    }, indent=2, ensure_ascii=False) + "\n")
    policy = base / "boundary.sb"
    policy.write_text(
        '(version 1)\n(allow default)\n'
        '(deny file-read* (subpath "/Users/bys/.codex/memories") '
        '(subpath "/Users/bys/.agents/skills") '
        '(subpath "/Users/bys/Documents/my/test/zhiheng") '
        f'(subpath "{ROOT}"))\n'
        '(deny file-write*)\n'
        f'(allow file-write* (subpath "{base}"))\n'
        '(allow file-write-data (literal "/dev/null") (literal "/dev/tty"))\n'
    )
    env = os.environ.copy()
    env.update({"HOME": str(home), "CODEX_HOME": str(codex_home)})
    command = [
        "/usr/bin/sandbox-exec", "-f", str(policy), shutil.which("codex"),
        "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
        "--skip-git-repo-check", "--sandbox", "danger-full-access", "--json",
        "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"',
        "-c", 'model_provider="openai"', "-c", 'approval_policy="never"',
        "-c", 'features.skip_host_skill_discovery=true', "-c", 'web_search="disabled"',
        "-c", 'allow_login_shell=false', "-C", str(project), "-",
    ]
    for feature in ("plugins", "remote_plugin", "plugin_discovery_prefetch", "plugin_sharing",
                    "recommended_plugins", "apps", "hooks", "memories", "shell_snapshot",
                    "skill_mcp_dependency_install", "multi_agent", "daemon_auto_start",
                    "system_proxy_fallback"):
        command[command.index("-C"):command.index("-C")] = ["--disable", feature]
    (OUTPUT / "launch.json").write_text(json.dumps({
        "argv": command, "cwd": str(project),
        "environment_overrides": {"HOME": str(home), "CODEX_HOME": str(codex_home)},
        "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
        "runner_sha256": sha(OUTPUT / "runner.py"),
        "outer_boundary": "macOS sandbox-exec limits reads and writes; CLI sandbox uses danger-full-access inside it",
        "requested_model": "gpt-6.1-sol", "requested_reasoning": "high",
        "actual_server_model": "not exposed by CLI event stream",
    }, indent=2) + "\n")
    try:
        run = subprocess.run(command, input=prompt, env=env, capture_output=True,
                             text=True, timeout=360)
    except subprocess.TimeoutExpired as exc:
        (OUTPUT / "events.jsonl").write_bytes(exc.stdout or b"")
        (OUTPUT / "stderr.log").write_bytes(exc.stderr or b"")
        (OUTPUT / "result.json").write_text('{"exit":"timeout"}\n')
        raise SystemExit(1)
    (OUTPUT / "events.jsonl").write_text(run.stdout)
    (OUTPUT / "stderr.log").write_text(run.stderr)
    final_files = {p.relative_to(project).as_posix(): sha(p)
                   for p in project.rglob("*") if p.is_file() and ".agents" not in p.parts
                   and "__pycache__" not in p.parts}
    for name in final_files:
        target = OUTPUT / "project" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project / name, target)
    events = [json.loads(line) for line in run.stdout.splitlines()]
    completed = [item["item"] for item in events if item.get("type") == "item.completed"]
    reads = {name: [] for name in ("zh-tdd/SKILL.md", "zh-tdd/references/tests.md",
                                  "zh-tdd/references/mocking.md")}
    for index, item in enumerate(completed):
        if item.get("type") != "command_execution" or item.get("exit_code") != 0:
            continue
        for name in reads:
            source = project / ".agents/skills" / name
            if name in item.get("command", "") and source.read_text() in item.get("aggregated_output", ""):
                reads[name].append(index)
    check = subprocess.run(["python3", "-B", "-m", "unittest", "discover", "-v"],
                           cwd=project, capture_output=True, text=True)
    (OUTPUT / "parent-tests.stdout").write_text(check.stdout)
    (OUTPUT / "parent-tests.stderr").write_text(check.stderr)
    report = {"exit": run.returncode, "resource_full_reads": reads,
              "final_files_sha256": final_files, "parent_test_exit": check.returncode,
              "parent_test_output": check.stdout + check.stderr,
              "spec_unchanged": sha(project / "SPEC.md") == hashlib.sha256(inputs["SPEC.md"].encode()).hexdigest()}
    (OUTPUT / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: report[key] for key in ("exit", "resource_full_reads",
          "parent_test_exit", "spec_unchanged")}, ensure_ascii=False))
    raise SystemExit(0 if run.returncode == 0 and check.returncode == 0
                     and all(reads.values()) and report["spec_unchanged"] else 1)
