"""Observe implicit zh-review loading for a natural review request."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
CASE = os.environ.get("ZH_EVAL_CASE", "review")
if CASE not in {"review", "neighbor"}:
    raise SystemExit("ZH_EVAL_CASE must be review or neighbor")
RUN_ID = os.environ.get("ZH_EVAL_RUN_ID")
if not RUN_ID or "/" in RUN_ID or RUN_ID.startswith("."):
    raise SystemExit("Set ZH_EVAL_RUN_ID to a new simple run name")
OUTPUT = ROOT / ("docs/evidence/i07/controlled-auto-review" if CASE == "review"
                 else "docs/evidence/i07/controlled-auto-neighbor") / RUN_ID
OUTPUT.mkdir(parents=True, exist_ok=False)
shutil.copy2(Path(__file__), OUTPUT / "runner.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory(prefix="zh-i07-auto-review-") as temporary:
    base = Path(temporary).resolve()
    home, codex_home, project = (base / name for name in ("home", "codex-home", "project"))
    home.mkdir()
    codex_home.mkdir()
    project.mkdir()
    (codex_home / "auth.json").symlink_to(Path.home() / ".codex/auth.json")
    for name in (("zh", "zh-review") if CASE == "review" else
                 tuple(path.name for path in (ROOT / "skills").iterdir() if (path / "SKILL.md").is_file())):
        shutil.copytree(ROOT / "skills" / name, project / ".agents/skills" / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    inputs = {
        "AGENTS.md": "Review against the accepted local specification. Report precise findings with evidence. Do not edit on a review-only request.\n",
        "spec.md": "# Addition\n`add(a, b)` returns the arithmetic sum of two integers, including negative inputs. New behavior needs a regression test.\n",
        "calc.py": "def add(a: int, b: int) -> int:\n    return a - b\n",
    } if CASE == "review" else {}
    for name, text in inputs.items():
        (project / name).write_text(text)
    prompt = ("Review calc.py against spec.md and the local project standards. Report findings only; do not edit.\n"
              if CASE == "review" else "Translate this sentence into English: 今天下雨。\n")
    (OUTPUT / "request.txt").write_text(prompt)
    (OUTPUT / "inputs.json").write_text(json.dumps({
        "files": inputs,
        "installed_skill_files_sha256": {
            p.relative_to(project).as_posix(): sha(p)
            for p in (project / ".agents/skills").rglob("*") if p.is_file()
        },
    }, indent=2, ensure_ascii=False) + "\n")
    policy = base / "boundary.sb"
    policy.write_text(
        '(version 1)\n(allow default)\n'
        '(deny file-read* (subpath "/Users/bys/.codex/memories") '
        '(subpath "/Users/bys/.agents/skills") '
        '(subpath "/Users/bys/Documents/my/test/zhiheng") '
        f'(subpath "{ROOT}"))\n'
        '(deny file-write*)\n'
        f'(allow file-write* (subpath "{base}/codex-home") '
        f'(subpath "{base}/home"))\n'
        '(allow file-write-data (literal "/dev/null") (literal "/dev/tty"))\n'
    )
    probes = []
    for label, path, operation, allowed in (
        ("denied-memory", Path("/Users/bys/.codex/memories/MEMORY.md"), "read", False),
        ("denied-old-target", Path("/Users/bys/Documents/my/test/zhiheng/.git/HEAD"), "read", False),
        ("denied-staging", ROOT / "README.md", "read", False),
        ("allowed-input", project / ("spec.md" if CASE == "review"
                                      else ".agents/skills/zh/SKILL.md"), "read", True),
        ("denied-project-write", project / "boundary-probe", "write", False),
        ("allowed-host-write", codex_home / "boundary-probe", "write", True),
    ):
        code = ("from pathlib import Path; import sys; "
                "Path(sys.argv[1]).read_bytes()" if operation == "read" else
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('probe')")
        argv = ["/usr/bin/sandbox-exec", "-f", str(policy), "python3", "-c", code, str(path)]
        check = subprocess.run(argv, capture_output=True, text=True)
        probes.append({"label": label, "argv": argv, "path_exists_before": path.is_file()
                       if operation == "read" else None, "exit": check.returncode,
                       "stdout": check.stdout, "stderr": check.stderr, "expected_allowed": allowed})
        if operation == "write" and allowed and path.exists():
            path.unlink()
        if (check.returncode == 0) != allowed:
            raise RuntimeError(f"Boundary probe mismatch: {label}")
    (OUTPUT / "boundary.json").write_text(json.dumps(probes, indent=2) + "\n")
    env = os.environ.copy()
    env.update({"HOME": str(home), "CODEX_HOME": str(codex_home)})
    command = [
        "/usr/bin/sandbox-exec", "-f", str(policy), shutil.which("codex"),
        "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
        "--skip-git-repo-check", "--sandbox", "danger-full-access", "--json",
        "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"',
        "-c", 'model_provider="openai"', "-c", 'approval_policy="never"',
        "-c", 'features.skip_host_skill_discovery=true', "-c", 'web_search="disabled"',
        "-c", 'allow_login_shell=false',
    ]
    for feature in ("plugins", "remote_plugin", "plugin_discovery_prefetch", "plugin_sharing",
                    "recommended_plugins", "apps", "hooks", "memories", "shell_snapshot",
                    "skill_mcp_dependency_install", "multi_agent", "daemon_auto_start",
                    "system_proxy_fallback"):
        command += ["--disable", feature]
    command += ["-C", str(project), "-"]
    (OUTPUT / "launch.json").write_text(json.dumps({
        "argv": command, "cwd": str(project),
        "environment_overrides": {"HOME": str(home), "CODEX_HOME": str(codex_home)},
        "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
        "runner_sha256": sha(OUTPUT / "runner.py"),
        "requested_model": "gpt-6.1-sol", "requested_reasoning": "high",
        "actual_server_model": "not exposed by CLI event stream",
    }, indent=2) + "\n")
    try:
        run = subprocess.run(command, input=prompt, env=env, capture_output=True,
                             text=True, timeout=240)
    except subprocess.TimeoutExpired as exc:
        (OUTPUT / "events.jsonl").write_bytes(exc.stdout or b"")
        (OUTPUT / "stderr.log").write_bytes(exc.stderr or b"")
        (OUTPUT / "result.json").write_text('{"exit":"timeout"}\n')
        raise SystemExit(1)
    (OUTPUT / "events.jsonl").write_text(run.stdout)
    (OUTPUT / "stderr.log").write_text(run.stderr)
    events = [json.loads(line) for line in run.stdout.splitlines()]
    completed = [event["item"] for event in events if event.get("type") == "item.completed"]
    skill = project / ".agents/skills/zh-review/SKILL.md"
    loaded = any(item.get("type") == "command_execution" and item.get("exit_code") == 0
                 and "zh-review/SKILL.md" in item.get("command", "")
                 and skill.read_text() in item.get("aggregated_output", "") for item in completed)
    skill_reads = [item.get("command") for item in completed
                   if item.get("type") == "command_execution"
                   and "/SKILL.md" in item.get("command", "")]
    final = [item["text"] for item in completed if item.get("type") == "agent_message"]
    preserved = all(sha(project / name) == hashlib.sha256(text.encode()).hexdigest()
                    for name, text in inputs.items())
    output = {"case": CASE, "exit": run.returncode, "loaded_zh_review": loaded,
              "skill_read_commands": skill_reads, "inputs_preserved": preserved,
              "final": final[-1] if final else None}
    (OUTPUT / "result.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: output[key] for key in ("exit", "loaded_zh_review", "inputs_preserved")}))
    observed = loaded if CASE == "review" else not skill_reads and bool(final) and "rain" in final[-1].lower()
    raise SystemExit(0 if run.returncode == 0 and observed and preserved else 1)
